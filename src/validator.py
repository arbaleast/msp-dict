"""
mschxudp 词库校验器

把「Windows 导入失败」拆成四类可行动的问题，而不是笼统的「格式错误」：

  1. 文件格式错误（format）      —— 签名/协议头/版本不对，文件根本不是 mschxudp
  2. 文件已损坏（corruption）    —— 截断、偏移表越界/非递增、UTF-16LE 未对齐、分隔符缺失
  3. 候选位置/内容违规（content）—— 候选序号不在 1~9、拼音非法、词条超长、重复
  4. Windows UI 容量警告（ui）   —— 词条数超过微软拼音导入/设置页可承受规模

用法::

    from src.validator import DatValidator
    report = DatValidator().validate('msp_lite.dat')
    print(report.format_text())
    raise SystemExit(report.exit_code)
"""

import os
import struct
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .format_spec import (
    ENTRY_HANZI_OFFSET_BASE,
    ENTRY_HEAD_BASE,
    ENTRY_MAGIC,
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
    UI_FREEZE_ENTRIES,
    is_valid_pinyin,
    utf16_units,
)

CATEGORY_LABELS = {
    'format': '文件格式错误',
    'corruption': '文件已损坏',
    'content': '候选位置/内容违规',
    'ui': 'Windows 容量警告',
}

CATEGORY_ORDER = ['format', 'corruption', 'content', 'ui']


@dataclass
class Issue:
    category: str          # format | corruption | content | ui
    severity: str          # error | warning
    code: str
    message: str
    count: int = 0
    samples: List[str] = field(default_factory=list)

    def add(self, sample: Optional[str] = None, count: int = 1) -> None:
        self.count += count
        if sample and len(self.samples) < 5:
            self.samples.append(sample)


@dataclass
class ValidationReport:
    path: str
    file_size: int = 0
    phrase_count: int = 0
    parsed_entries: int = 0
    issues: List[Issue] = field(default_factory=list)
    stats: Dict[str, object] = field(default_factory=dict)

    def add_issue(self, category: str, severity: str, code: str,
                  message: str, sample: Optional[str] = None, count: int = 1) -> Issue:
        for issue in self.issues:
            if issue.code == code:
                issue.add(sample, count)
                return issue
        issue = Issue(category=category, severity=severity, code=code, message=message)
        issue.add(sample, count)
        self.issues.append(issue)
        return issue

    def issues_in(self, category: str) -> List[Issue]:
        return [i for i in self.issues if i.category == category]

    def has_errors(self, category: str = None) -> bool:
        return any(
            i.severity == 'error' and (category is None or i.category == category)
            for i in self.issues
        )

    @property
    def exit_code(self) -> int:
        """0=通过（可含警告）, 2=格式错误, 3=文件损坏, 4=内容违规。"""
        if self.has_errors('format'):
            return 2
        if self.has_errors('corruption'):
            return 3
        if self.has_errors('content'):
            return 4
        return 0

    @property
    def verdict(self) -> str:
        code = self.exit_code
        if code == 2:
            return '该文件不是有效的 mschxudp 词库，Windows 会提示「文件格式错误」'
        if code == 3:
            return '文件结构已损坏（截断/偏移越界/UTF-16LE 未对齐），Windows 会提示「文件已损坏」'
        if code == 4:
            return '文件结构可解析，但含 Windows 不接受的候选位置或内容，导入会失败或行为异常'
        if any(i.category == 'ui' for i in self.issues):
            return '格式合法，但词条数超过 Windows 设置页舒适区，导入后管理界面可能卡顿/假死'
        return '格式合法，未发现阻断导入的问题'

    def format_text(self, max_samples: int = 5) -> str:
        lines = []
        lines.append(f"文件: {self.path}")
        lines.append(f"大小: {self.file_size:,} 字节")
        lines.append(f"词条: {self.phrase_count:,} 条（成功解析 {self.parsed_entries:,} 条）")

        if self.stats:
            stat_parts = []
            if 'max_code_units' in self.stats:
                stat_parts.append(f"最长拼音 {self.stats['max_code_units']} 单元")
            if 'max_word_units' in self.stats:
                stat_parts.append(f"最长词条 {self.stats['max_word_units']} 单元")
            if 'single_char' in self.stats:
                stat_parts.append(f"单字词 {self.stats['single_char']:,}")
            if 'candidate_positions' in self.stats:
                dist = self.stats['candidate_positions']
                stat_parts.append(
                    '候选位分布 ' + ', '.join(f"{k}:{v:,}" for k, v in sorted(dist.items()))
                )
            if stat_parts:
                lines.append('统计: ' + '；'.join(stat_parts))

        for category in CATEGORY_ORDER:
            issues = self.issues_in(category)
            if not issues:
                continue
            lines.append('')
            lines.append(f"【{CATEGORY_LABELS[category]}】")
            for issue in issues:
                flag = '❌' if issue.severity == 'error' else '⚠️'
                lines.append(f"  {flag} {issue.message}（{issue.count:,} 处）")
                for sample in issue.samples[:max_samples]:
                    lines.append(f"      - {sample}")

        lines.append('')
        lines.append(f"结论: {self.verdict}")
        return '\n'.join(lines)


class DatValidator:
    """全量扫描 mschxudp 文件并分类报告问题。"""

    def __init__(self, now: int = None):
        self.now = now if now is not None else int(time.time())

    def validate(self, filepath: str) -> ValidationReport:
        report = ValidationReport(path=filepath)
        if not os.path.exists(filepath):
            report.add_issue('format', 'error', 'missing_file', f'文件不存在: {filepath}')
            return report

        report.file_size = os.path.getsize(filepath)
        with open(filepath, 'rb') as f:
            data = f.read()

        if len(data) < HEADER_SIZE:
            report.add_issue(
                'format', 'error', 'too_small',
                f'文件只有 {len(data)} 字节，不足 {HEADER_SIZE} 字节文件头',
            )
            return report

        if data[0:8] != b'mschxudp':
            report.add_issue(
                'format', 'error', 'bad_magic',
                f"协议标识不是 'mschxudp'（实际 {data[0:8]!r}），不是 Win10 微软拼音用户词库",
            )
            return report

        flag = struct.unpack_from('<I', data, OFF_FLAG)[0]
        version = struct.unpack_from('<I', data, OFF_VERSION)[0]
        offset_start = struct.unpack_from('<I', data, OFF_PHRASE_OFFSET_START)[0]
        phrase_start = struct.unpack_from('<I', data, OFF_PHRASE_START)[0]
        phrase_end = struct.unpack_from('<I', data, OFF_PHRASE_END)[0]
        phrase_count = struct.unpack_from('<I', data, OFF_PHRASE_COUNT)[0]
        file_timestamp = struct.unpack_from('<Q', data, OFF_TIMESTAMP)[0]
        report.phrase_count = phrase_count

        if flag != HEADER_FLAG:
            report.add_issue('format', 'error', 'bad_flag',
                             f'文件头标志 0x{flag:08x}，期望 0x{HEADER_FLAG:08x}')
        if version != HEADER_VERSION:
            report.add_issue('format', 'error', 'bad_version',
                             f'版本号 {version}，Windows 微软拼音支持版本 1')
        if offset_start != PHRASE_OFFSET_START:
            report.add_issue('format', 'error', 'bad_offset_start',
                             f'偏移表起点 0x{offset_start:x}，期望 0x{PHRASE_OFFSET_START:x}')
        if file_timestamp == 0:
            report.add_issue('format', 'warning', 'zero_timestamp',
                             '文件头时间戳为 0（部分旧版本可能忽略该字段）')

        if any(data[0x28:0x40]):
            report.add_issue('format', 'warning', 'dirty_reserved',
                             '保留区 0x28~0x3F 必须全 0，当前含非零字节')

        fatal = False
        if phrase_count > (len(data) - HEADER_SIZE) // 4:
            report.add_issue(
                'corruption', 'error', 'count_too_large',
                f'词条数 {phrase_count:,} 超过文件可容纳的偏移表大小（文件仅 {len(data):,} 字节）',
            )
            fatal = True
        if phrase_start != offset_start + 4 * phrase_count:
            report.add_issue(
                'corruption', 'error', 'bad_phrase_start',
                f'词条区起点 0x{phrase_start:x} != 偏移表起点 + 4×词条数（0x{offset_start + 4 * phrase_count:x}）',
            )
            fatal = fatal or phrase_start < offset_start + 4 * phrase_count
        if phrase_end > len(data):
            report.add_issue(
                'corruption', 'error', 'phrase_end_overflow',
                f'词条区结束 0x{phrase_end:x} 越过文件末尾（文件 0x{len(data):x}），文件被截断',
            )
            fatal = True
        elif phrase_end < len(data):
            report.add_issue(
                'corruption', 'warning', 'trailing_data',
                f'词条区结束 0x{phrase_end:x} 小于文件大小 0x{len(data):x}（尾部有 {len(data) - phrase_end} 字节多余数据）',
            )
        if phrase_end < phrase_start:
            report.add_issue('corruption', 'error', 'bad_phrase_end',
                             f'词条区结束 0x{phrase_end:x} 小于起点 0x{phrase_start:x}')
            fatal = True

        if fatal:
            return report

        if phrase_count == 0:
            report.add_issue('content', 'warning', 'empty_dictionary', '词库中没有词条')
            return report

        # ---- 偏移表 ----
        try:
            offsets = [
                struct.unpack_from('<I', data, offset_start + i * 4)[0]
                for i in range(phrase_count)
            ]
        except struct.error:
            report.add_issue('corruption', 'error', 'offset_table_truncated', '偏移表被截断')
            return report

        sentinel = phrase_end - phrase_start
        offsets.append(sentinel)

        if offsets[0] != 0:
            report.add_issue('corruption', 'error', 'first_offset_nonzero',
                             f'偏移表首项应为 0，实际 {offsets[0]}')
        for i in range(phrase_count):
            if offsets[i + 1] <= offsets[i]:
                report.add_issue(
                    'corruption', 'error', 'non_monotonic_offsets',
                    f'偏移表第 {i + 1} 项 ({offsets[i + 1]}) 未大于前一项 ({offsets[i]})，偏移表损坏',
                    sample=f'index={i} offsets={offsets[i]}→{offsets[i + 1]}',
                )
                fatal = True
                break
        if not fatal and offsets[-1] != sentinel:
            report.add_issue('corruption', 'warning', 'sentinel_mismatch',
                             f'最后一条记录结束偏移 {offsets[-1]} 与 phrase_end-phrase_start={sentinel} 不一致')

        if fatal:
            return report

        self._scan_entries(data, offsets, phrase_count, report)
        self._scan_scale(report)
        return report

    # ------------------------------------------------------------------
    def _scan_entries(self, data: bytes, offsets: List[int],
                      phrase_count: int, report: ValidationReport) -> None:
        phrase_start = struct.unpack_from('<I', data, OFF_PHRASE_START)[0]
        expected_position: Dict[str, int] = {}
        seen_pairs = set()
        now_epoch2000 = max(0, self.now - EPOCH_2000_UNIX)

        max_code_units = 0
        max_word_units = 0
        single_char = 0
        position_dist: Dict[int, int] = {}
        parsed = 0

        for index in range(phrase_count):
            start = phrase_start + offsets[index]
            size = offsets[index + 1] - offsets[index]
            sample_prefix = f'index={index}'

            if size < ENTRY_HEAD_BASE + 4:
                report.add_issue('corruption', 'error', 'entry_too_small',
                                 '记录长度小于固定头（偏移表损坏）', sample=f'{sample_prefix} size={size}')
                continue
            if start + size > len(data):
                report.add_issue('corruption', 'error', 'entry_out_of_bounds',
                                 '记录起点越过文件末尾（文件被截断）', sample=f'{sample_prefix} pos=0x{start:x}')
                continue

            magic = struct.unpack_from('<I', data, start)[0]
            if magic != ENTRY_MAGIC:
                report.add_issue('corruption', 'error', 'bad_entry_magic',
                                 f'记录魔数 0x{magic:08x}，期望 0x{ENTRY_MAGIC:08x}',
                                 sample=f'{sample_prefix} pos=0x{start:x}')
                continue

            hanzi_offset = struct.unpack_from('<H', data, start + 4)[0]
            position = data[start + 6]
            flag = data[start + 7]

            if flag != 0x06:
                report.add_issue('content', 'error', 'bad_entry_flag',
                                 f'记录 +0x07 固定字节为 0x{flag:02x}，期望 0x06',
                                 sample=sample_prefix)
            if hanzi_offset < ENTRY_HANZI_OFFSET_BASE or hanzi_offset % 2 != 0:
                report.add_issue('corruption', 'error', 'bad_hanzi_offset',
                                 f'hanzi_offset={hanzi_offset} 非法（应为 18 + 偶数）',
                                 sample=sample_prefix)
                continue

            code_units = (hanzi_offset - ENTRY_HANZI_OFFSET_BASE) // 2
            code_start = start + ENTRY_HEAD_BASE
            # hanzi_offset 指向词条（汉字）起点；拼音后的 0x0000 在 hanzi_offset-2 处
            word_start = start + hanzi_offset
            word_end = start + size - 2

            if word_end < word_start:
                report.add_issue('corruption', 'error', 'negative_word_length',
                                 '记录内词条长度为负（偏移与记录长度不匹配）', sample=sample_prefix)
                continue

            if data[start + hanzi_offset - 2:start + hanzi_offset] != b'\x00\x00':
                report.add_issue('corruption', 'error', 'missing_split',
                                 '拼音与词条之间缺少 0x0000 分隔符（UTF-16LE 未对齐或长度错误）',
                                 sample=sample_prefix)
                continue
            if data[start + size - 2:start + size] != b'\x00\x00':
                report.add_issue('corruption', 'error', 'missing_terminator',
                                 '记录末尾缺少 0x0000 终止符（记录长度与 hanzi_offset 不一致）',
                                 sample=sample_prefix)
                continue

            try:
                code = data[code_start:code_start + code_units * 2].decode('utf-16-le')
                word = data[word_start:word_end].decode('utf-16-le')
            except UnicodeDecodeError:
                report.add_issue('corruption', 'error', 'bad_utf16',
                                 '拼音/词条不是合法的 UTF-16LE（可能是奇数长度或孤立代理项）',
                                 sample=sample_prefix)
                continue

            parsed += 1
            code_len = utf16_units(code)
            word_len = utf16_units(word)
            max_code_units = max(max_code_units, code_len)
            max_word_units = max(max_word_units, word_len)
            if word_len == 1:
                single_char += 1

            sample = f"#{index} {word!r} [{code}] pos={position}"
            # ---- 候选位置 ----
            if position == 0:
                report.add_issue('content', 'error', 'zero_position',
                                 '候选序号为 0（旧版构建器把词频 & 0xFF 截断为 0；'
                                 '合法范围 1~9）', sample=sample)
            elif position > MAX_CANDIDATE_POSITION:
                report.add_issue('content', 'error', 'position_out_of_range',
                                 f'候选序号 {position} 非法（合法范围 1~'
                                 f'{MAX_CANDIDATE_POSITION}；旧版构建器直接写入词频 & 0xFF）',
                                 sample=sample)
            else:
                position_dist[position] = position_dist.get(position, 0) + 1
                expected = expected_position.get(code, 0) + 1
                expected_position[code] = expected
                if position != expected and expected <= MAX_CANDIDATE_POSITION:
                    report.add_issue('content', 'warning', 'position_sequence',
                                     f'同一拼音「{code}」的候选序号不连续（应为 {expected}，实际 {position}）',
                                     sample=sample)

            # ---- 拼音内容 ----
            if code_len == 0:
                report.add_issue('content', 'error', 'empty_pinyin', '拼音为空', sample=sample)
            elif not is_valid_pinyin(code):
                report.add_issue('content', 'error', 'invalid_pinyin',
                                 f'拼音含非法字符（只允许 a-z 与 \'）: {code!r}', sample=sample)
            elif code_len > MAX_CODE_UNITS:
                report.add_issue('content', 'error', 'code_too_long',
                                 f'拼音 {code_len} 个单元，超过 {MAX_CODE_UNITS} 上限', sample=sample)

            # ---- 词条内容 ----
            if word_len == 0:
                report.add_issue('content', 'error', 'empty_word', '词条为空', sample=sample)
            elif word_len > MAX_WORD_UNITS:
                report.add_issue('content', 'error', 'word_too_long',
                                 f'词条 {word_len} 个 UTF-16 单元，超过 {MAX_WORD_UNITS} 上限',
                                 sample=sample)
            if any(ord(ch) == 0 or ord(ch) < 0x20 for ch in word):
                report.add_issue('content', 'error', 'control_char',
                                 '词条含 NUL/控制字符', sample=sample)

            pair = (code, word)
            if pair in seen_pairs:
                report.add_issue('content', 'error', 'duplicate_entry',
                                 '同一 (拼音, 词) 重复出现，Windows 会显示重复候选',
                                 sample=sample)
            else:
                seen_pairs.add(pair)

            # ---- 记录时间戳（旧版固定 0xE679CD20 是未来的伪时间）----
            record_ts = struct.unpack_from('<I', data, start + 12)[0]
            if record_ts > now_epoch2000 + 86400 * 365:
                report.add_issue('content', 'warning', 'stale_timestamp',
                                 f'记录时间戳 {record_ts} 是未来时间（旧版构建器写死 0xE679CD20）',
                                 sample=sample)

        report.parsed_entries = parsed
        report.stats.update({
            'max_code_units': max_code_units,
            'max_word_units': max_word_units,
            'single_char': single_char,
            'candidate_positions': position_dist,
        })

    def _scan_scale(self, report: ValidationReport) -> None:
        count = report.phrase_count
        if count > UI_FREEZE_ENTRIES:
            report.add_issue(
                'ui', 'warning', 'ui_freeze_risk',
                f'词条数 {count:,} 超过 {UI_FREEZE_ENTRIES:,}，'
                f'设置页「用户自定义短语」极可能转圈/假死且无法清除',
            )
        elif count > MAX_IMPORT_ENTRIES:
            report.add_issue(
                'ui', 'warning', 'over_import_limit',
                f'词条数 {count:,} 超过参考实现 ({MAX_IMPORT_ENTRIES:,} 条) 与设置页舒适区，'
                f'导入可能被截断，且管理界面会明显卡顿',
            )
        if 0 < count <= MAX_IMPORT_ENTRIES:
            report.stats['within_windows_limit'] = True
