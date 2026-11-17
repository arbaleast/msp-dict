"""
微软拼音用户词库解析器 (mschxudp 格式 ✅)

格式来自 imewlconverter Win10MsPinyin.cs / MsChxUdpExporterBase.cs，
字段布局与常量统一定义在 src/format_spec.py。

Header (0x40 bytes):
  0x00: proto 'mschxudp' (8 bytes)
  0x08: unknown 0x00600002 (4 bytes)
  0x0C: version 1 (4 bytes)
  0x10: phrase_offset_start = 0x40 (4 bytes)
  0x14: phrase_start = 0x40 + phrase_count * 4 (4 bytes)
  0x18: phrase_end = 文件总大小 (4 bytes)
  0x1C: phrase_count (4 bytes)
  0x20: timestamp (8 bytes)
  0x28: reserved 0 (24 bytes)

Phrase entry:
  magic (4 bytes, 0x00100010)
  hanzi_offset (2 bytes) = 18 + 拼音 UTF-16LE 字节数
  candidate position (1 byte)，同编码候选序号，1 起
  0x06 (1 byte)
  unknown (4 bytes, 0x00000000)
  unknown (4 bytes, 2000-01-01 纪元秒)
  pinyin (UTF-16LE)
  split (2 bytes, 0x0000)
  word (UTF-16LE)
  terminator (2 bytes, 0x0000)
"""

import struct
from dataclasses import dataclass
from typing import List, Optional

from .format_spec import (
    ENTRY_HANZI_OFFSET_BASE,
    ENTRY_HEAD_BASE,
    ENTRY_MAGIC,
    HEADER_SIZE,
    MAGIC,
    MAX_CODE_UNITS,
    OFF_PHRASE_COUNT,
    OFF_PHRASE_END,
    OFF_PHRASE_OFFSET_START,
    OFF_PHRASE_START,
)


class MSPinyinFormatError(ValueError):
    """mschxudp 解析错误。

    Attributes:
        category: 'format'（签名/协议头不对）或 'corruption'（截断/偏移越界/未对齐）
    """

    def __init__(self, message: str, category: str = 'format'):
        super().__init__(message)
        self.category = category


@dataclass
class DictEntry:
    """词库条目"""
    text: str              # 中文文本
    pinyin: str            # 拼音字符串（无空格，如 "zhongguo"）
    offset: int = 0        # 词条在文件中的偏移量
    rank: int = 1          # 候选序号（同一拼音下 1 起）


class MSPinyinParser:
    """微软拼音用户词库解析器 (mschxudp 格式)"""

    MAGIC = MAGIC
    HEADER_SIZE = HEADER_SIZE

    _ENTRY_MAGIC = ENTRY_MAGIC
    _ENTRY_HEAD_BASE = ENTRY_HANZI_OFFSET_BASE  # 18 = 固定头 16 + 拼音后分隔符 2
    _ENTRY_PINYIN_START = ENTRY_HEAD_BASE       # 16
    _MAX_PINYIN_LEN = MAX_CODE_UNITS            # 拼音长度上限（UTF-16 单元）

    def __init__(self, filepath: str = None):
        self.filepath = filepath
        self.raw_data: bytes = b''
        self.entries: List[DictEntry] = []
        self.phrase_count = 0
        self.warnings: List[str] = []
        self.invalid_entries = 0

    def load(self, filepath: str, strict: bool = False) -> int:
        """加载词库文件，返回词条数。

        Args:
            filepath: 词库文件路径
            strict: True 时对结构问题直接抛 MSPinyinFormatError；
                False 时尽量跳过坏词条，把问题记入 self.warnings / invalid_entries

        Raises:
            FileNotFoundError: 文件不存在
            MSPinyinFormatError: 文件格式错误（category='format'）
                或文件已损坏（category='corruption'）
        """
        self.filepath = filepath
        with open(filepath, 'rb') as f:
            data = f.read()

        return self.parse_bytes(data, strict=strict)

    def parse_bytes(self, data: bytes, strict: bool = False) -> int:
        """解析内存中的词库数据（load 与编辑器重建共用）。"""
        self.raw_data = data
        self.warnings = []
        self.invalid_entries = 0

        if len(data) < self.HEADER_SIZE:
            raise MSPinyinFormatError(
                f"文件太小 ({len(data)} 字节)，不足以包含 {self.HEADER_SIZE} 字节的 mschxudp 文件头",
                category='format',
            )

        proto = data[0:8]
        if proto != self.MAGIC:
            raise MSPinyinFormatError(
                f"无效的协议标识: {proto!r}，期望 'mschxudp'\n"
                f"提示: 旧版 60 字节固定格式已被弃用，请使用 mschxudp 格式词库",
                category='format',
            )

        phrase_offset_start = struct.unpack('<I', data[OFF_PHRASE_OFFSET_START:OFF_PHRASE_OFFSET_START + 4])[0]
        phrase_start = struct.unpack('<I', data[OFF_PHRASE_START:OFF_PHRASE_START + 4])[0]
        phrase_end = struct.unpack('<I', data[OFF_PHRASE_END:OFF_PHRASE_END + 4])[0]
        phrase_count = struct.unpack('<I', data[OFF_PHRASE_COUNT:OFF_PHRASE_COUNT + 4])[0]
        self.phrase_count = phrase_count

        # ---- 结构边界校验（对应 Windows/imewlconverter 的检查）----
        problem = None
        if phrase_offset_start < self.HEADER_SIZE:
            problem = f"偏移表起点异常: 0x{phrase_offset_start:x} < 0x40"
        elif phrase_count > (len(data) - self.HEADER_SIZE) // 4:
            problem = f"词条数 {phrase_count} 超出文件可容纳的偏移表大小"
        elif phrase_start < phrase_offset_start + 4 * phrase_count:
            problem = (f"词条区起点 0x{phrase_start:x} 落在偏移表内 "
                       f"(期望 >= 0x{phrase_offset_start + 4 * phrase_count:x})")
        elif phrase_end < phrase_start:
            problem = f"词条区结束 0x{phrase_end:x} 小于起点 0x{phrase_start:x}"
        elif phrase_end > len(data):
            problem = f"词条区结束 0x{phrase_end:x} 越界（文件仅 {len(data)} 字节）"

        if problem:
            if strict:
                raise MSPinyinFormatError(f"文件结构损坏: {problem}", category='corruption')
            self.warnings.append(f"文件结构损坏: {problem}")
            if phrase_count > (len(data) - self.HEADER_SIZE) // 4:
                raise MSPinyinFormatError(
                    f"文件结构损坏: {problem}", category='corruption'
                )

        if phrase_end != len(data):
            self.warnings.append(
                f"header.phrase_end (0x{phrase_end:x}) 与文件实际大小 (0x{len(data):x}) 不一致"
            )

        # ---- 偏移表 ----
        try:
            offsets = [
                struct.unpack('<I', data[phrase_offset_start + i * 4:
                                         phrase_offset_start + i * 4 + 4])[0]
                for i in range(phrase_count)
            ]
        except struct.error as exc:
            raise MSPinyinFormatError(
                f"偏移表被截断（无法读取第 {phrase_count} 项）", category='corruption'
            ) from exc

        # 哨兵：最后一条记录的结束位置
        offsets.append(phrase_end - phrase_start)

        if offsets and offsets[0] != 0:
            self.warnings.append(f"偏移表首项应为 0，实际 {offsets[0]}")
        for i in range(phrase_count):
            if offsets[i + 1] < offsets[i]:
                msg = f"偏移表非单调递增: 第 {i} 项 {offsets[i]} > 第 {i + 1} 项 {offsets[i + 1]}"
                if strict:
                    raise MSPinyinFormatError(f"文件结构损坏: {msg}", category='corruption')
                self.warnings.append(msg)
                break

        # ---- 词条 ----
        self.entries = []
        for i in range(phrase_count):
            pos = phrase_start + offsets[i]
            entry_size = offsets[i + 1] - offsets[i]
            if pos < 0 or pos + entry_size > len(data) or entry_size <= 0:
                self.invalid_entries += 1
                msg = f"第 {i} 条记录越界: offset={offsets[i]}, size={entry_size}"
                if strict:
                    raise MSPinyinFormatError(f"文件结构损坏: {msg}", category='corruption')
                self.warnings.append(msg)
                continue

            entry = self._read_phrase(data, pos, entry_size)
            if entry is None:
                self.invalid_entries += 1
                if strict:
                    raise MSPinyinFormatError(
                        f"文件结构损坏: 第 {i} 条记录无法解析（偏移 0x{pos:x}）",
                        category='corruption',
                    )
                continue
            self.entries.append(entry)

        return len(self.entries)

    def _read_phrase(self, data: bytes, start: int, entry_size: int) -> Optional[DictEntry]:
        """读取单个词条，返回 DictEntry；格式错误时返回 None"""
        if entry_size < self._ENTRY_HEAD_BASE + 4:
            return None
        try:
            magic = struct.unpack('<I', data[start:start + 4])[0]
            if magic != self._ENTRY_MAGIC:
                return None

            hanzi_offset = struct.unpack('<H', data[start + 4:start + 6])[0]
            position = data[start + 6]

            # 拼音以 UTF-16LE 存储：hanzi_offset 必须落在偶数字节且不小于固定头 + 分隔符
            if hanzi_offset < self._ENTRY_HEAD_BASE or hanzi_offset % 2 != 0:
                return None
            pinyin_byte_len = hanzi_offset - self._ENTRY_HEAD_BASE
            pinyin_units = pinyin_byte_len // 2
            if pinyin_units > self._MAX_PINYIN_LEN:
                return None

            pinyin_start = start + self._ENTRY_PINYIN_START
            if pinyin_start + pinyin_byte_len + 2 > start + entry_size:
                return None
            pinyin_bytes = data[pinyin_start:pinyin_start + pinyin_byte_len]
            # 拼音后的 0x0000 分隔符必须存在
            if data[pinyin_start + pinyin_byte_len:pinyin_start + pinyin_byte_len + 2] != b'\x00\x00':
                return None
            pinyin_str = pinyin_bytes.decode('utf-16-le')

            word_start = pinyin_start + pinyin_byte_len + 2
            word_byte_len = (start + entry_size) - word_start - 2
            if word_byte_len <= 0 or word_byte_len % 2 != 0:
                return None
            if data[start + entry_size - 2:start + entry_size] != b'\x00\x00':
                return None
            word = data[word_start:word_start + word_byte_len].decode('utf-16-le')
            if not word:
                return None

            return DictEntry(
                text=word,
                pinyin=pinyin_str,
                offset=start,
                rank=position,
            )
        except (struct.error, IndexError, UnicodeDecodeError):
            return None

    def get_entry_count(self) -> int:
        """获取词条数量"""
        return len(self.entries)

    def get_file_size(self) -> int:
        """获取词库文件大小"""
        return len(self.raw_data)

    def get_all_texts(self) -> List[str]:
        """获取所有词条文本"""
        return [e.text for e in self.entries]

    def find_by_text(self, text: str) -> Optional[DictEntry]:
        """根据文本查找词条

        Args:
            text: 要查找的文本

        Returns:
            匹配的 DictEntry，未找到时返回 None
        """
        for entry in self.entries:
            if entry.text == text:
                return entry
        return None


def main():
    """测试解析器"""
    import sys

    if len(sys.argv) < 2:
        print("用法: python parser.py <mschxudp.dat>")
        sys.exit(1)

    parser = MSPinyinParser()
    try:
        count = parser.load(sys.argv[1])
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)

    print(f"文件: {sys.argv[1]}")
    print(f"文件大小: {parser.get_file_size()} 字节")
    print(f"词条数量: {count}")
    if parser.invalid_entries:
        print(f"无法解析的词条: {parser.invalid_entries}")
    print()

    print("前 10 个词条:")
    for i, entry in enumerate(parser.entries[:10]):
        print(f"  {i + 1}. {entry.text}  [{entry.pinyin}] (候选位={entry.rank})")

    print()
    print("后 10 个词条:")
    for i, entry in enumerate(parser.entries[-10:]):
        idx = len(parser.entries) - 9 + i
        print(f"  {idx}. {entry.text}  [{entry.pinyin}] (候选位={entry.rank})")


if __name__ == '__main__':
    main()
