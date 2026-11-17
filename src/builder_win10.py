"""
微软拼音 Win10 用户词库格式 (mschxudp) 构建器

格式说明见 src/format_spec.py（常量与字段布局的唯一事实来源）。

与旧实现的关键差异（Issue #3）:
  * 记录 +0x06 是「同一编码下的候选序号」，从 1 起，微软拼音 UI 只展示 1~9；
    旧实现写的是原始词频 `rank & 0xFF`，会产生 0 或 >9 的非法值，Windows 拒绝导入
    或让短语管理界面异常。
  * 记录 +0x0C 是 2000-01-01 纪元秒，不再是固定的 0xE679CD20。
  * 构建前统一清洗：空拼音、非法拼音字符、超长编码/词条、孤立代理项、
    控制字符、重复 (编码, 词) 全部拦截并计数，不再写出畸形记录。
"""

import logging
import os
import struct
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .format_spec import (
    ENTRY_FLAG,
    ENTRY_HANZI_OFFSET_BASE,
    ENTRY_HEAD_BASE,
    ENTRY_MAGIC,
    ENTRY_SPLIT,
    EPOCH_2000_UNIX,
    HEADER_FLAG,
    HEADER_SIZE,
    HEADER_VERSION,
    MAX_CANDIDATE_POSITION,
    MAX_CODE_UNITS,
    MAX_IMPORT_ENTRIES,
    MAX_WORD_UNITS,
    OFF_FLAG,
    OFF_PHRASE_COUNT,
    OFF_PHRASE_END,
    OFF_PHRASE_OFFSET_START,
    OFF_PHRASE_START,
    OFF_TIMESTAMP,
    OFF_VERSION,
    PHRASE_OFFSET_START,
    has_forbidden_char,
    has_unpaired_surrogate,
    is_valid_pinyin,
    normalize_pinyin,
    utf16_units,
)

logger = logging.getLogger(__name__)

# 跳过原因 -> 中文说明（用于 CLI/CI 输出）
REASON_LABELS = {
    'empty_word': '空词条',
    'empty_pinyin': '空拼音',
    'invalid_pinyin': '非法拼音字符',
    'code_too_long': '拼音超长(>32)',
    'word_too_long': '词条超长(>64)',
    'illegal_char': '含控制字符/NUL',
    'unpaired_surrogate': '孤立 UTF-16 代理项',
    'duplicate': '重复(拼音+词)',
    'candidate_overflow': '同音候选超过 9 个',
    'invalid_position': '候选位不在 1~9',
    'duplicate_position': '同拼音候选位重复',
}


@dataclass
class BuildStats:
    """构建统计：`skipped` 为因格式/内容问题被拦截的词条数。"""

    accepted: int = 0
    skipped: int = 0
    truncated: int = 0
    reasons: Dict[str, int] = field(default_factory=dict)

    def note(self, reason: str, count: int = 1) -> None:
        self.reasons[reason] = self.reasons.get(reason, 0) + count
        if reason != 'duplicate':
            self.skipped += count

    def merge(self, other: 'BuildStats') -> None:
        self.accepted += other.accepted
        self.skipped += other.skipped
        self.truncated += other.truncated
        for key, value in other.reasons.items():
            self.reasons[key] = self.reasons.get(key, 0) + value

    def summary(self) -> str:
        parts = [f"接收 {self.accepted:,} 条"]
        if self.skipped:
            parts.append(f"拦截 {self.skipped:,} 条")
        if self.truncated:
            parts.append(f"超出上限 {self.truncated:,} 条")
        for reason, count in sorted(self.reasons.items(), key=lambda kv: -kv[1]):
            label = REASON_LABELS.get(reason, reason)
            parts.append(f"{label}={count:,}")
        return '，'.join(parts)

    def to_dict(self) -> dict:
        return {
            'accepted': self.accepted,
            'skipped': self.skipped,
            'truncated': self.truncated,
            'reasons': dict(self.reasons),
        }


class Win10MSPinyinBuilder:
    """构建 Win10 微软拼音词库二进制数据 (mschxudp 格式)

    格式参考: imewlconverter Win10MsPinyin.cs / MsChxUdpExporterBase.cs
    """

    HEADER_SIZE = HEADER_SIZE
    HEADER_FLAG = HEADER_FLAG
    HEADER_VERSION = HEADER_VERSION
    PHRASE_OFFSET_START = PHRASE_OFFSET_START

    ENTRY_MAGIC = ENTRY_MAGIC
    ENTRY_FLAG = ENTRY_FLAG
    ENTRY_HEAD_BASE = ENTRY_HEAD_BASE
    ENTRY_HANZI_OFFSET_BASE = ENTRY_HANZI_OFFSET_BASE
    ENTRY_SPLIT = ENTRY_SPLIT

    MAX_CANDIDATE_POSITION = MAX_CANDIDATE_POSITION

    def __init__(self, timestamp: int = 0, rank_mode: str = 'frequency'):
        """初始化构建器

        Args:
            timestamp: 写入文件头的 Unix 时间戳（秒）。为 0 时使用当前时间；
                记录内的 2000 纪元时间戳由它推导。
            rank_mode:
                - ``frequency``（默认）：`rank` 是来源词频，同拼音内按词频降序
                  重新分配候选位 1~9；
                - ``position``：`rank` 已经是 1~9 的候选位，原样保留、按位排序，
                  越界/重复会被拦截（供编辑器与手工 1~9 输入使用）。
        """
        if rank_mode not in ('frequency', 'position'):
            raise ValueError(f"未知 rank_mode: {rank_mode!r}")
        self.words: List[Tuple[str, str, int, str]] = []  # (word, pinyin_str, rank, source)
        self.timestamp = timestamp
        self.rank_mode = rank_mode
        self.stats = BuildStats()

    def add_word(self, word: str, pinyin_str: str, rank: int = 1,
                 source: str = 'base'):
        """添加词条（pinyin_str 为无空格字符串）。

        `rank` 的含义由 `rank_mode` 决定：默认是来源词频（只用于同音排序与
        三档筛选，不会写进候选序号字段）；`position` 模式下则是 1~9 的候选位。
        """
        self.words.append((word, pinyin_str, rank,
                           (source or 'base').strip() or 'base'))

    def add_from_text_file(self, filepath: str, min_freq: int = None,
                           exclude_single: bool = False,
                           max_word_units: int = None,
                           limit: int = None,
                           extended_ratio: float = None,
                           extended_max_word_units: int = 6,
                           extended_min_word_units: int = 2) -> int:
        """从 TSV 文本批量添加词条，格式 `词条\\t拼音\\t词频[\\t来源]`。

        第 4 列是来源标记（`base` / `moegirl` / `wiki` / `sogou`），缺省视为
        `base`。给了 `limit` 与 `extended_ratio` 时按配额选词：扩展源最多占
        `limit * extended_ratio` 个名额，其余留给基础源；某一侧数量不足时由另一侧补足。

        这里的筛选是选词策略（不算违规），格式清洗仍统一在 build() 中执行。
        """
        base_rows: List[Tuple[str, str, int, str]] = []
        ext_rows: List[Tuple[str, str, int, str]] = []

        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n\r')
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                word = parts[0].strip()
                if not word:
                    continue
                pinyin = parts[1].strip().replace(' ', '') if len(parts) >= 2 else ''
                freq = 1
                if len(parts) >= 3:
                    try:
                        freq = int(parts[2])
                    except ValueError:
                        freq = 1
                source = parts[3].strip() if len(parts) >= 4 else 'base'
                if not source:
                    source = 'base'

                if min_freq is not None and freq < min_freq:
                    continue

                units = utf16_units(word)
                if source == 'base':
                    if exclude_single and units < 2:
                        continue
                    if max_word_units is not None and units > max_word_units:
                        continue
                    base_rows.append((word, pinyin, freq, source))
                else:
                    if units < extended_min_word_units or units > extended_max_word_units:
                        continue
                    ext_rows.append((word, pinyin, freq, source))

        if limit is None:
            selected = base_rows + ext_rows
        else:
            ext_cap = int(limit * extended_ratio) if extended_ratio else 0
            ext_selected = ext_rows[:ext_cap]
            base_selected = base_rows[:limit - len(ext_selected)]
            if len(base_selected) < limit - len(ext_selected):
                # 基础源不足，用扩展源补足剩余名额
                ext_selected = ext_rows[:limit - len(base_selected)]
            selected = base_selected + ext_selected

        self.words.extend(selected)
        return len(selected)

    # ------------------------------------------------------------------
    # 清洗 / 排序 / 候选序号分配
    # ------------------------------------------------------------------
    def _prepare_entries(self) -> List[Tuple[str, str, int, bytes, bytes, int]]:
        """清洗、去重、排序，返回 (word, code, rank, word_utf16, code_utf16, position)。"""
        stats = BuildStats()
        # (code, word) -> (rank, source)；frequency 模式保留最高词频，position 模式保留首个候选位
        best: Dict[Tuple[str, str], Tuple[int, str]] = {}
        for word, pinyin, rank, source in self.words:
            word = (word or '').strip()
            code = normalize_pinyin(pinyin)

            if not word:
                stats.note('empty_word')
                continue
            if not code:
                stats.note('empty_pinyin')
                continue
            if has_unpaired_surrogate(word) or has_unpaired_surrogate(code):
                stats.note('unpaired_surrogate')
                continue
            if has_forbidden_char(word) or has_forbidden_char(code):
                stats.note('illegal_char')
                continue
            if not is_valid_pinyin(code):
                stats.note('invalid_pinyin')
                continue
            if utf16_units(code) > MAX_CODE_UNITS:
                stats.note('code_too_long')
                continue
            if utf16_units(word) > MAX_WORD_UNITS:
                stats.note('word_too_long')
                continue

            key = (code, word)
            if key in best:
                stats.note('duplicate')
                old_rank, old_source = best[key]
                if self.rank_mode == 'frequency' and rank > old_rank:
                    best[key] = (rank, old_source)
                continue
            best[key] = (rank, source)

        if self.rank_mode == 'position':
            result = self._assign_explicit_positions(best, stats)
        else:
            result = self._assign_frequency_positions(best, stats)

        stats.accepted = len(result)
        self.stats = stats
        return result

    @staticmethod
    def _encode_entry(code: str, word: str, rank: int,
                      position: int) -> Tuple[str, str, int, bytes, bytes, int]:
        return (word, code, rank, word.encode('utf-16-le'), code.encode('utf-16-le'), position)

    def _assign_frequency_positions(self, best, stats):
        """按拼音聚簇，同拼音内词频高者在前，依次分配 1~9。"""
        prepared = sorted(
            ((code, word, freq, source)
             for (code, word), (freq, source) in best.items()),
            # 同一拼音内：基础源永远排在扩展源前面，扩展源不得挤占第 1 候选位
            key=lambda item: (item[0], 0 if item[3] == 'base' else 1,
                              -item[2], len(item[1]), item[1]),
        )
        result = []
        current_code = None
        position = 0
        for code, word, freq, source in prepared:
            if code != current_code:
                current_code = code
                position = 0
            position += 1
            if position > MAX_CANDIDATE_POSITION:
                stats.note('candidate_overflow')
                continue
            result.append(self._encode_entry(code, word, freq, position))
        return result

    def _assign_explicit_positions(self, best, stats):
        """候选位已由调用方给出（1~9），原样保留并按位排序。

        同一 (拼音, 候选位) 冲突时保留先加入的词条（`best` 保持插入顺序）。
        """
        accepted = []
        used = set()
        for (code, word), (position, source) in best.items():
            if position < 1:
                stats.note('invalid_position')
                continue
            if position > MAX_CANDIDATE_POSITION:
                stats.note('candidate_overflow')
                continue
            if (code, position) in used:
                stats.note('duplicate_position')
                continue
            used.add((code, position))
            accepted.append((code, word, position))

        accepted.sort(key=lambda item: (item[0], item[2], len(item[1]), item[1]))
        return [self._encode_entry(code, word, position, position)
                for code, word, position in accepted]

    # ------------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------------
    def build(self) -> bytes:
        """构建二进制数据；`self.stats` 记录接收/拦截统计。"""
        entries = self._prepare_entries()
        phrase_count = len(entries)

        file_timestamp = self.timestamp or int(time.time())
        record_timestamp = max(0, file_timestamp - EPOCH_2000_UNIX) & 0xFFFFFFFF

        offsets: List[int] = []
        current_offset = 0
        for _, _, _, word_utf16, code_utf16, _ in entries:
            offsets.append(current_offset)
            current_offset += ENTRY_HEAD_BASE + len(code_utf16) + 2 + len(word_utf16) + 2

        phrase_start = PHRASE_OFFSET_START + phrase_count * 4
        phrase_end = phrase_start + current_offset

        header = bytearray(HEADER_SIZE)
        header[0:8] = b'mschxudp'
        struct.pack_into('<I', header, OFF_FLAG, HEADER_FLAG)
        struct.pack_into('<I', header, OFF_VERSION, HEADER_VERSION)
        struct.pack_into('<I', header, OFF_PHRASE_OFFSET_START, PHRASE_OFFSET_START)
        struct.pack_into('<I', header, OFF_PHRASE_START, phrase_start)
        struct.pack_into('<I', header, OFF_PHRASE_END, phrase_end)
        struct.pack_into('<I', header, OFF_PHRASE_COUNT, phrase_count)
        struct.pack_into('<Q', header, OFF_TIMESTAMP, file_timestamp)

        offset_table = b''.join(struct.pack('<I', off) for off in offsets)

        phrase_parts = []
        for _, _, _, word_utf16, code_utf16, position in entries:
            hanzi_offset = ENTRY_HANZI_OFFSET_BASE + len(code_utf16)

            entry = struct.pack('<I', ENTRY_MAGIC)
            entry += struct.pack('<H', hanzi_offset)
            entry += bytes([position, ENTRY_FLAG])
            entry += struct.pack('<I', 0)                 # +0x08 固定 0
            entry += struct.pack('<I', record_timestamp)  # +0x0C 2000 纪元秒
            entry += code_utf16
            entry += struct.pack('<H', ENTRY_SPLIT)
            entry += word_utf16
            entry += struct.pack('<H', ENTRY_SPLIT)
            phrase_parts.append(entry)

        return bytes(header) + offset_table + b''.join(phrase_parts)

    def save(self, filepath: str):
        """保存到文件"""
        data = self.build()
        with open(filepath, 'wb') as f:
            f.write(data)

        size = os.path.getsize(filepath)
        logger.info("已保存: %s (%d 词条, %.1f MB)", filepath, self.stats.accepted, size / 1024 / 1024)
        if self.stats.accepted > MAX_IMPORT_ENTRIES:
            logger.warning(
                "词条数 %d 超过微软拼音 %d 条上限，Windows 无法完整导入（可作为存档或转其他输入法）",
                self.stats.accepted, MAX_IMPORT_ENTRIES,
            )


class Win10MSPinyinParser:
    """兼容旧接口：委托给 src.parser.MSPinyinParser。"""

    def __init__(self):
        self.words: List[Tuple[str, str, int]] = []

    def load(self, filepath: str) -> int:
        from .parser import MSPinyinParser

        parser = MSPinyinParser()
        count = parser.load(filepath)
        self.words = [(e.text, e.pinyin, e.rank) for e in parser.entries]
        return count


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    builder = Win10MSPinyinBuilder()
    for word, py in [("中国", "zhongguo"), ("北京", "beijing"), ("上海", "shanghai")]:
        builder.add_word(word, py, rank=1)

    builder.save('/tmp/test_win10_fixed.dat')
    parser = Win10MSPinyinParser()
    count = parser.load('/tmp/test_win10_fixed.dat')
    print(f"\n解析结果: {count} 词条")
    for word, py, rank in parser.words:
        print(f"  {word}: {py} (候选位={rank})")
