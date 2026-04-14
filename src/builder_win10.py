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
from typing import List, Tuple

class Win10MSPinyinBuilder:
    HEADER_SIZE = 0x40
    PHRASE_OFFSET_START = 0x40
    
    def __init__(self):
        self.words: List[Tuple[str, str]] = []  # (word, pinyin_str)
    
    def add_word(self, word: str, pinyin_str: str, rank: int = 1):
        """添加词条（pinyin_str 为无空格字符串）"""
        self.words.append((word, pinyin_str, rank))
    
    def build(self) -> bytes:
        """构建二进制数据"""
        phrase_count = len(self.words)
        
        # 计算每个词条的大小和累积偏移
        phrase_offsets = []
        current_offset = 0
        for word, pinyin_str, rank in self.words:
            pinyin_char_len = len(pinyin_str)  # 字符数，不是字节数
            word_char_len = len(word)
            
            # hanzi_offset = 8(magic+hanoff) + 8(unknown) + pinyin_bytes + 2(split)
            # = 18 + pinyin_char_len * 2
            hanzi_offset = 18 + pinyin_char_len * 2
            
            # 词条大小 = 4(magic) + 2(hanoff) + 1(rank) + 1(x06) + 4(unknown) + 4(unknown2) + pinyin_bytes + 2(split) + word_bytes + 2(term)
            entry_size = 4 + 2 + 1 + 1 + 4 + 4 + pinyin_char_len * 2 + 2 + word_char_len * 2 + 2
            phrase_offsets.append(current_offset)
            current_offset += entry_size
        
        phrase_start = self.PHRASE_OFFSET_START + phrase_count * 4
        phrase_end = phrase_start + current_offset
        
        # 构建 header
        header = bytearray(self.HEADER_SIZE)
        header[0:8] = b'mschxudp'
        struct.pack_into('<I', header, 8, 0x00600002)
        struct.pack_into('<I', header, 12, 1)  # version
        struct.pack_into('<I', header, 16, self.PHRASE_OFFSET_START)  # phrase_offset_start
        struct.pack_into('<I', header, 20, phrase_start)   # phrase_start
        struct.pack_into('<I', header, 24, phrase_end)      # phrase_end
        struct.pack_into('<I', header, 28, phrase_count)     # phrase_count
        struct.pack_into('<Q', header, 32, 0)  # timestamp
        
        # 构建 offset 表
        offset_table = b''.join(struct.pack('<I', off) for off in phrase_offsets)
        
        # 构建词条
        phrases = b''
        for word, pinyin_str, rank in self.words:
            pinyin_char_len = len(pinyin_str)
            word_char_len = len(word)
            pinyin_utf16 = pinyin_str.encode('utf-16-le')
            word_utf16 = word.encode('utf-16-le')
            hanzi_offset = 18 + pinyin_char_len * 2
            
            entry = b''
            entry += struct.pack('<I', 0x00100010)  # magic
            entry += struct.pack('<H', hanzi_offset)
            entry += bytes([rank & 0xFF, 0x06])     # rank + x06
            entry += struct.pack('<I', 0x00000000)   # unknown
            entry += struct.pack('<I', 0xE679CD20)   # unknown (关键！)
            entry += pinyin_utf16                    # pinyin (可变长)
            entry += struct.pack('<H', 0)            # split
            entry += word_utf16                      # word
            entry += struct.pack('<H', 0)            # terminator
            phrases += entry
        
        return bytes(header) + offset_table + phrases
    
    def save(self, filepath: str):
        """保存到文件"""
        data = self.build()
        with open(filepath, 'wb') as f:
            f.write(data)
        
        size = os.path.getsize(filepath)
        print(f"已保存: {filepath} ({len(self.words)} 词条, {size / 1024 / 1024:.1f} MB)")


class Win10MSPinyinParser:
    """解析 Win10 微软拼音词库"""
    
    def __init__(self):
        self.words: List[Tuple[str, str]] = []
    
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
        
        print(f"Proto: mschxudp, Phrases: {phrase_count}, Start: 0x{phrase_start:x}, End: 0x{phrase_end:x}")
        
        # 读取 offset 表
        offsets = []
        for i in range(phrase_count):
            off = struct.unpack('<I', data[phrase_offset_start + i * 4:phrase_offset_start + i * 4 + 4])[0]
            offsets.append(off)
        offsets.append(phrase_end - phrase_start)
        
        # 读取词条
        self.words = []
        for i in range(phrase_count):
            pos = phrase_start + offsets[i]
            next_pos = phrase_start + offsets[i + 1]
            
            word, pinyin_str = self._read_phrase(data, pos, next_pos)
            self.words.append((word, pinyin_str))
        
        return phrase_count
    
    def _read_phrase(self, data: bytes, start: int, end: int) -> Tuple[str, str]:
        """读取单个词条"""
        magic = struct.unpack('<I', data[start:start + 4])[0]
        hanzi_offset = struct.unpack('<H', data[start + 4:start + 6])[0]
        rank = data[start + 6]
        
        # pinyin 字符数 = (hanzi_offset - 18) / 2
        pinyin_char_len = (hanzi_offset - 18) // 2
        pinyin_byte_len = pinyin_char_len * 2
        
        # pinyin 从 start + 16 开始
        pinyin_start = start + 16
        pinyin_bytes = data[pinyin_start:pinyin_start + pinyin_byte_len]
        pinyin_str = pinyin_bytes.decode('utf-16-le', errors='ignore')
        
        # word 从 pinyin_start + pinyin_byte_len + 2 (split) 开始
        word_start = pinyin_start + pinyin_byte_len + 2
        word_len = end - word_start - 2
        word_bytes = data[word_start:word_start + word_len]
        word = word_bytes.decode('utf-16-le', errors='ignore')
        
        return word, pinyin_str


if __name__ == '__main__':
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
    for word, py in parser.words:
        print(f"  {word}: {py}")
