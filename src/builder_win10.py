"""
微软拼音 Win10 用户词库格式 (mschxudp)

格式来自 imewlconverter Win10MsPinyin.cs:

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
"""

import struct
import os
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class Win10MSPinyinBuilder:
    """构建 Win10 微软拼音词库二进制数据 (mschxudp 格式)

    格式参考: imewlconverter Win10MsPinyin.cs
    """

    # ---- 文件头常量 ----
    HEADER_SIZE = 0x40              # 文件头固定大小 (64 字节)
    HEADER_FLAG = 0x00600002        # 文件头偏移 0x08 处的固定标志 (来源: imewlconverter)
    HEADER_VERSION = 1              # 版本号 (偏移 0x0C)
    PHRASE_OFFSET_START = 0x40      # 偏移表起始位置 = 头部大小

    # ---- 词条内部常量 ----
    ENTRY_MAGIC = 0x00100010        # 词条魔数 (来源: mschxudp 格式规范)
    ENTRY_UNK1 = 0x00000000         # 词条内偏移 0x08 处的未知字段, 固定为 0
    ENTRY_UNK2 = 0xE679CD20         # 词条内偏移 0x0C 处的未知字段, 固定魔数 (来源: imewlconverter)
    ENTRY_FLAG = 0x06               # rank 后的固定标志字节
    ENTRY_HEAD_BASE = 16            # 固定头大小 = 4(magic) + 2(hanzi_offset) + 1(rank) + 1(flag) + 4(unk1) + 4(unk2)
    ENTRY_SPLIT = 0                 # 拼音与汉字之间的 null 分隔符值
    # hanzi_offset = 固定头(16) + pinyin_bytes + split(2) = 18 + pinyin_bytes
    ENTRY_HANZI_OFFSET_BASE = 18

    def __init__(self, timestamp: int = 0):
        """初始化构建器

        Args:
            timestamp: 文件头中的 Unix 时间戳 (8 字节), 默认 0
        """
        self.words: List[Tuple[str, str, int]] = []  # (word, pinyin_str, rank)
        self.timestamp = timestamp

    def add_word(self, word: str, pinyin_str: str, rank: int = 1):
        """添加词条（pinyin_str 为无空格字符串）
        
        注意: word 和 pinyin_str 需要先转换为 UTF-16LE 字节来获取准确的字节长度
        """
        # 转换为 UTF-16LE 以正确处理 surrogate pairs (如生僻字)
        word_utf16 = word.encode('utf-16-le')
        pinyin_utf16 = pinyin_str.encode('utf-16-le')
        self.words.append((word, pinyin_str, rank, word_utf16, pinyin_utf16))

    def build(self) -> bytes:
        """构建二进制数据"""
        phrase_count = len(self.words)

        # 计算每个词条的大小和累积偏移（使用 UTF-16LE 字节长度）
        phrase_offsets = []
        current_offset = 0
        for word, pinyin_str, rank, word_utf16, pinyin_utf16 in self.words:
            pinyin_byte_len = len(pinyin_utf16)  # UTF-16LE 字节长度
            word_byte_len = len(word_utf16)      # UTF-16LE 字节长度

            # hanzi_offset = 固定头(16) + pinyin_bytes + split(2) = 18 + pinyin_bytes
            # Windows 用 hanzi_offset 来定位汉字起始位置
            hanzi_offset = self.ENTRY_HANZI_OFFSET_BASE + pinyin_byte_len

            # 词条大小 = 固定头(16) + pinyin_bytes + split(2) + word_bytes + term(2)
            entry_size = self.ENTRY_HEAD_BASE + pinyin_byte_len + 2 + word_byte_len + 2
            
            # 存储当前偏移（词条相对于 phrase_start 的位置）
            phrase_offsets.append(current_offset)
            current_offset += entry_size

        phrase_start = self.PHRASE_OFFSET_START + phrase_count * 4
        phrase_end = phrase_start + current_offset

        # 构建 header (0x40 bytes)
        header = bytearray(self.HEADER_SIZE)
        header[0:8] = b'mschxudp'
        struct.pack_into('<I', header, 8,  self.HEADER_FLAG)     # 固定标志 (来源: imewlconverter)
        struct.pack_into('<I', header, 12, self.HEADER_VERSION)   # 版本号固定为 1
        struct.pack_into('<I', header, 16, self.PHRASE_OFFSET_START)  # phrase_offset_start
        struct.pack_into('<I', header, 20, phrase_start)                # phrase_start
        struct.pack_into('<I', header, 24, phrase_end)                   # phrase_end
        struct.pack_into('<I', header, 28, phrase_count)                 # phrase_count
        struct.pack_into('<Q', header, 32, self.timestamp)  # timestamp

        # 构建 offset 表
        offset_table = b''.join(struct.pack('<I', off) for off in phrase_offsets)

        # 构建词条（用 list 最后 join，避免 phrases += entry 的 O(n²) 问题）
        phrase_parts = []
        for word, pinyin_str, rank, word_utf16, pinyin_utf16 in self.words:
            pinyin_byte_len = len(pinyin_utf16)
            hanzi_offset = self.ENTRY_HANZI_OFFSET_BASE + pinyin_byte_len

            entry  = struct.pack('<I', self.ENTRY_MAGIC)   # 词条魔数
            entry += struct.pack('<H', hanzi_offset)
            entry += bytes([rank & 0xFF, self.ENTRY_FLAG])  # rank + 固定标志字节
            entry += struct.pack('<I', self.ENTRY_UNK1)     # 未知字段 (固定为 0)
            entry += struct.pack('<I', self.ENTRY_UNK2)     # 未知字段 (固定魔数)
            entry += pinyin_utf16
            entry += struct.pack('<H', self.ENTRY_SPLIT)     # null 分隔符
            entry += word_utf16
            entry += struct.pack('<H', self.ENTRY_SPLIT)     # null terminator
            phrase_parts.append(entry)

        return bytes(header) + offset_table + b''.join(phrase_parts)

    def save(self, filepath: str):
        """保存到文件"""
        data = self.build()
        with open(filepath, 'wb') as f:
            f.write(data)

        size = os.path.getsize(filepath)
        logger.info("已保存: %s (%d 词条, %.1f MB)", filepath, len(self.words), size / 1024 / 1024)


class Win10MSPinyinParser:
    """解析 Win10 微软拼音词库"""

    def __init__(self):
        self.words: List[Tuple[str, str, int]] = []  # (word, pinyin_str, rank)

    def load(self, filepath: str) -> int:
        """加载词库，返回词条数"""
        with open(filepath, 'rb') as f:
            data = f.read()

        # 检查 proto
        proto = data[0:8]
        if proto != b'mschxudp':
            raise ValueError(f"Invalid proto: {proto}")

        # 读取 header
        phrase_offset_start = struct.unpack('<I', data[16:20])[0]
        phrase_start = struct.unpack('<I', data[20:24])[0]
        phrase_end = struct.unpack('<I', data[24:28])[0]
        phrase_count = struct.unpack('<I', data[28:32])[0]

        logger.info("Proto: mschxudp, Phrases: %d, Start: 0x%x, End: 0x%x", phrase_count, phrase_start, phrase_end)

        # 读取 offset 表
        offsets = []
        for i in range(phrase_count):
            off = struct.unpack('<I', data[phrase_offset_start + i * 4:phrase_offset_start + i * 4 + 4])[0]
            offsets.append(off)
        # 最后一个 offset = phrase_end 相对于 phrase_start 的偏移
        offsets.append(phrase_end - phrase_start)

        # 读取词条
        self.words = []
        for i in range(phrase_count):
            pos = phrase_start + offsets[i]
            next_pos = phrase_start + offsets[i + 1]

            word, pinyin_str, rank = self._read_phrase(data, pos, next_pos)
            self.words.append((word, pinyin_str, rank))

        return phrase_count

    def _read_phrase(self, data: bytes, start: int, end: int) -> Tuple[str, str, int]:
        """读取单个词条，返回 (word, pinyin, rank)"""
        magic = struct.unpack('<I', data[start:start + 4])[0]
        hanzi_offset = struct.unpack('<H', data[start + 4:start + 6])[0]
        rank = data[start + 6]

        # hanzi_offset = 18 + pinyin_byte_len (指向汉字起始位置，跳过 split)
        # 所以 pinyin_byte_len = hanzi_offset - 18
        pinyin_byte_len = hanzi_offset - Win10MSPinyinBuilder.ENTRY_HANZI_OFFSET_BASE
        pinyin_char_len = pinyin_byte_len // 2

        # pinyin 从 start + 16 开始
        # 16 = 4(magic) + 2(hanzi_offset) + 1(rank) + 1(flag) + 4(unk1) + 4(unk2)
        pinyin_start = start + 16
        pinyin_bytes = data[pinyin_start:pinyin_start + pinyin_byte_len]
        pinyin_str = pinyin_bytes.decode('utf-16-le', errors='ignore')

        # word 从 pinyin_start + pinyin_byte_len + 2 (split) 开始
        word_start = pinyin_start + pinyin_byte_len + 2
        word_len = end - word_start - 2  # -2 减去末尾 null terminator
        word_bytes = data[word_start:word_start + word_len]
        word = word_bytes.decode('utf-16-le', errors='ignore')

        return word, pinyin_str, rank


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    builder = Win10MSPinyinBuilder()

    # 测试数据
    test_words = [
        ("中国", "zhongguo"),
        ("北京", "beijing"),
        ("上海", "shanghai"),
    ]

    for word, py in test_words:
        builder.add_word(word, py, rank=1)

    # 保存测试
    builder.save('/tmp/test_win10_fixed.dat')

    # 验证解析
    parser = Win10MSPinyinParser()
    count = parser.load('/tmp/test_win10_fixed.dat')
    print(f"\n解析结果: {count} 词条")
    for word, py, rank in parser.words:
        print(f"  {word}: {py} (rank={rank})")
