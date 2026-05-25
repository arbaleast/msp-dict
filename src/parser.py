"""
微软拼音用户词库解析器 (mschxudp 格式 ✅)

格式来自 imewlconverter Win10MsPinyin.cs:
  https://github.com/studyzy/imewlconverter

Header (0x40 bytes):
  0x00: proto 'mschxudp' (8 bytes)
  0x08: unknown 0x00600002 (4 bytes)
  0x0C: version 1 (4 bytes)
  0x10: phrase_offset_start = 0x40 (4 bytes)
  0x14: phrase_start = 0x40 + phrase_count * 4 (4 bytes)
  0x18: phrase_end (4 bytes, filled after build)
  0x1C: phrase_count (4 bytes)
  0x20: timestamp (8 bytes)
  0x28: reserved 0 (24 bytes)

Phrase entry:
  magic (4 bytes, 0x00100010)
  hanzi_offset (2 bytes) = 18 + pinyin_char_len * 2
  rank (1 byte)
  0x06 (1 byte)
  unknown (4 bytes, 0x00000000)
  unknown (4 bytes, 0xE679CD20)
  pinyin (pinyin_char_len * 2 bytes UTF-16LE)
  split (2 bytes, 0x0000)
  word (word_char_len * 2 bytes UTF-16LE)
  terminator (2 bytes, 0x0000)

注意: 旧版 parser.py 使用的 60 字节固定格式已被验证为错误的。
     此文件为 mschxudp 格式的重新实现。
"""

import struct
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DictEntry:
    """词库条目"""
    text: str              # 中文文本
    pinyin: str            # 拼音字符串（无空格，如 "zhongguo"）
    offset: int = 0        # 词条在文件中的偏移量
    rank: int = 1          # 词频排名


class MSPinyinParser:
    """微软拼音用户词库解析器 (mschxudp 格式)"""

    MAGIC = b'mschxudp'
    HEADER_SIZE = 0x40      # 文件头固定大小 (64 字节)

    # ---- 文件头偏移常量 (来源: imewlconverter Win10MsPinyin.cs) ----
    _OFF_PROTO = 0          # 协议标识起始 (8 bytes)
    _OFF_FLAG = 8           # 固定标志 0x00600002 (4 bytes)
    _OFF_VERSION = 12       # 版本号 (4 bytes)
    _OFF_PHRASE_OFFSET_START = 16  # 偏移表起始位置 (4 bytes)
    _OFF_PHRASE_START = 20  # 词条数据起始位置 (4 bytes)
    _OFF_PHRASE_END = 24    # 词条数据结束位置 (4 bytes)
    _OFF_PHRASE_COUNT = 28  # 词条数量 (4 bytes)
    _OFF_TIMESTAMP = 32     # Unix 时间戳 (8 bytes)
    # 0x28 ~ 0x3F: 保留字段 (24 bytes)

    # ---- 词条内部偏移常量 ----
    _ENTRY_MAGIC = 0x00100010   # 词条魔数 (来源: mschxudp 格式规范)
    _ENTRY_HEAD_BASE = 18       # 词条固定头大小 = 4+2+1+1+4+4
    _ENTRY_PINYIN_START = 16    # 拼音数据在词条内的起始偏移 = 4(magic)+2(hanzi_off)+1(rank)+1(flag)+4(unk1)+4(unk2)
    _MAX_PINYIN_LEN = 100       # 拼音长度合理性上限（防止畸形数据导致内存异常）

    def __init__(self, filepath: str = None):
        self.filepath = filepath
        self.raw_data: bytes = b''
        self.entries: List[DictEntry] = []
        self.phrase_count = 0

    def load(self, filepath: str) -> int:
        """加载词库文件，返回词条数

        Args:
            filepath: 词库文件路径

        Returns:
            解析到的词条数量

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式无效
        """
        self.filepath = filepath
        with open(filepath, 'rb') as f:
            self.raw_data = f.read()

        data = self.raw_data
        if len(data) < self.HEADER_SIZE:
            raise ValueError(f"文件太小 ({len(data)} 字节)，不足以包含 mschxudp 文件头")

        # 验证协议头
        proto = data[0:8]
        if proto != self.MAGIC:
            raise ValueError(
                f"无效的协议标识: {proto!r}，期望 'mschxudp'\n"
                f"提示: 旧版 60 字节固定格式已被弃用，请使用 mschxudp 格式词库"
            )

        # 读取文件头字段
        # 偏移表起始 = header[16:20], 词条起始 = header[20:24], 词条结束 = header[24:28], 词条数 = header[28:32]
        phrase_offset_start = struct.unpack('<I', data[16:20])[0]
        phrase_start = struct.unpack('<I', data[20:24])[0]
        phrase_end = struct.unpack('<I', data[24:28])[0]
        phrase_count = struct.unpack('<I', data[28:32])[0]
        self.phrase_count = phrase_count

        # 读取偏移表（每个词条对应一个 4 字节偏移量）
        offsets = []
        for i in range(phrase_count):
            off = struct.unpack(
                '<I',
                data[phrase_offset_start + i * 4:
                     phrase_offset_start + i * 4 + 4]
            )[0]
            offsets.append(off)
        # 添加哨兵值：最后一个词条的结束位置
        offsets.append(phrase_end - phrase_start)

        # 读取每个词条
        self.entries = []
        for i in range(phrase_count):
            pos = phrase_start + offsets[i]
            entry_size = offsets[i + 1] - offsets[i]
            entry = self._read_phrase(data, pos, entry_size)
            if entry is not None:
                self.entries.append(entry)

        return phrase_count

    def _read_phrase(self, data: bytes, start: int, entry_size: int) -> Optional[DictEntry]:
        """读取单个词条，返回 DictEntry；格式错误时返回 None"""
        try:
            # 校验 magic 值 (0x00100010 = mschxudp 词条固定魔数, 来源: imewlconverter Win10MsPinyin.cs)
            magic = struct.unpack('<I', data[start:start + 4])[0]
            if magic != self._ENTRY_MAGIC:
                return None

            hanzi_offset = struct.unpack('<H', data[start + 4:start + 6])[0]
            rank = data[start + 6]

            # 拼音字符数 = (hanzi_offset - _ENTRY_HEAD_BASE) // 2
            # _ENTRY_HEAD_BASE(18) = 固定头大小: 4(magic) + 2(hanzi_offset) + 1(rank) + 1(flag=0x06) + 4(unk1) + 4(unk2)
            pinyin_char_len = (hanzi_offset - self._ENTRY_HEAD_BASE) // 2
            if pinyin_char_len < 0 or pinyin_char_len > self._MAX_PINYIN_LEN:
                return None
            pinyin_byte_len = pinyin_char_len * 2  # UTF-16LE: 每字符 2 字节

            # 拼音内容从 start + _ENTRY_PINYIN_START 开始
            # _ENTRY_PINYIN_START(16) = 4(magic) + 2(hanzi_offset) + 1(rank) + 1(flag) + 4(unk1) + 4(unk2)
            pinyin_start = start + self._ENTRY_PINYIN_START
            pinyin_bytes = data[pinyin_start:pinyin_start + pinyin_byte_len]
            pinyin_str = pinyin_bytes.decode('utf-16-le', errors='replace')
            pinyin_str = pinyin_str.replace('\x00', '')

            # 文本从拼音结束 + 2 (null terminator / split 分隔符 0x0000) 开始
            word_start = pinyin_start + pinyin_byte_len + 2  # +2 跳过 null 分隔
            word_byte_len = entry_size - (word_start - start) - 2  # -2 减去末尾 null terminator
            if word_byte_len < 0:
                return None
            word_bytes = data[word_start:word_start + word_byte_len]
            word = word_bytes.decode('utf-16-le', errors='replace')
            word = word.replace('\x00', '')

            if not word:
                return None

            return DictEntry(
                text=word,
                pinyin=pinyin_str,
                offset=start,
                rank=rank,
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
    print()

    print("前 10 个词条:")
    for i, entry in enumerate(parser.entries[:10]):
        print(f"  {i + 1}. {entry.text}  [{entry.pinyin}] (rank={entry.rank})")

    print()
    print("后 10 个词条:")
    for i, entry in enumerate(parser.entries[-10:]):
        idx = len(parser.entries) - 9 + i
        print(f"  {idx}. {entry.text}  [{entry.pinyin}] (rank={entry.rank})")


if __name__ == '__main__':
    main()
