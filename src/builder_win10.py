"""
微软拼音 Win10 用户词库格式 (mschxudp)

格式分析来自 imewlconverter:
- Proto: 'mschxudp' (8 bytes)
- Header: 0x40 bytes
- Phrase offsets: array of uint32 from 0x40
- Phrase entries: 
  - magic (4 bytes) + hanzi_offset (2) + rank (1) + x06 (1) + unknown8 (8)
  - pinyin: hanzi_offset - 18 bytes (UTF-16LE)
  - split: 2 bytes (0x0000)
  - word: variable (UTF-16LE)
  - terminator: 2 bytes (0x0000)
"""

import struct
import os
from typing import List, Tuple

class Win10MSPinyinBuilder:
    HEADER_SIZE = 0x40
    PHRASE_OFFSET_START = 0x40
    PINYIN_FIXED_LEN = 8  # 拼音固定 8 字节，不足补零
    
    def __init__(self):
        self.words: List[Tuple[str, str]] = []  # (word, pinyin_str)
    
    def add_word(self, word: str, pinyin_str: str, rank: int = 1):
        """添加词条（pinyin_str 为无空格字符串）"""
        self.words.append((word, pinyin_str, rank))
    
    def build(self) -> bytes:
        """构建二进制数据"""
        phrase_count = len(self.words)
        
        # 计算每个词条的大小和累积偏移
        phrase_sizes = []
        phrase_offsets = []
        current_offset = 0
        for word, pinyin_str, rank in self.words:
            pinyin_utf16 = pinyin_str.encode('utf-16-le')[:self.PINYIN_FIXED_LEN]  # 截断到 8 字节
            word_utf16 = word.encode('utf-16-le')
            pinyin_len = len(pinyin_utf16)
            word_len = len(word_utf16)
            
            # hanzi_offset = 固定部分(16) + pinyin_len + split(2)
            # 但实际测试发现 hanzi_offset = 18 + pinyin_len (不是 16 + pinyin_len + 2)
            hanzi_offset = 18 + pinyin_len
            
            # 词条大小 = 4 (magic) + 2 (hanzi_off) + 1 (rank) + 1 (x06) + 8 (unknown8) + pinyin_len + 2 (split) + word_len + 2 (term)
            entry_size = 4 + 2 + 1 + 1 + 8 + pinyin_len + 2 + word_len + 2
            phrase_sizes.append(entry_size)
            phrase_offsets.append(current_offset)
            current_offset += entry_size
        
        phrase_start = self.PHRASE_OFFSET_START + phrase_count * 4  # offset table size
        phrase_end = phrase_start + current_offset
        
        # 构建 header
        header = bytearray(self.HEADER_SIZE)
        header[0:8] = b'mschxudp'
        struct.pack_into('<I', header, 8, 0x00600002)
        struct.pack_into('<I', header, 12, 1)  # version
        struct.pack_into('<I', header, 16, self.PHRASE_OFFSET_START)  # phrase_offset_start
        struct.pack_into('<I', header, 20, phrase_start)   # phrase_start
        struct.pack_into('<I', header, 24, phrase_end)    # phrase_end
        struct.pack_into('<I', header, 28, phrase_count)   # phrase_count
        struct.pack_into('<Q', header, 32, 0)  # timestamp
        
        # 构建 offset 表
        offset_table = bytearray()
        for off in phrase_offsets:
            offset_table += struct.pack('<I', off)
        
        # 构建词条数据
        phrases = bytearray()
        for word, pinyin_str, rank in self.words:
            pinyin_utf16 = pinyin_str.encode('utf-16-le')[:self.PINYIN_FIXED_LEN]  # 截断到 8 字节
            word_utf16 = word.encode('utf-16-le')
            pinyin_len = len(pinyin_utf16)
            word_len = len(word_utf16)
            hanzi_offset = 18 + pinyin_len
            
            entry = bytearray()
            entry += struct.pack('<I', 0x00100010)  # magic
            entry += struct.pack('<H', hanzi_offset)
            entry += bytes([rank & 0xFF, 0x06])  # rank + x06
            entry += struct.pack('<Q', 0)  # unknown8
            entry += pinyin_utf16  # pinyin (固定8字节，不足补零)
            entry += struct.pack('<H', 0)  # split
            entry += word_utf16  # word
            entry += struct.pack('<H', 0)  # terminator
            phrases += bytes(entry)
        
        return bytes(header) + bytes(offset_table) + bytes(phrases)
    
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
        offsets.append(phrase_end - phrase_start)  # 最后一个词的结束位置
        
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
        
        # pinyin 长度 = hanzi_offset - 18
        pinyin_len = hanzi_offset - 18
        
        # pinyin 从 start + 16 开始
        pinyin_start = start + 16
        pinyin_bytes = data[pinyin_start:pinyin_start + pinyin_len]
        pinyin_str = pinyin_bytes.decode('utf-16-le', errors='ignore')
        
        # word 从 pinyin_start + pinyin_len + 2 (split) 开始，到 end - 2 (terminator) 结束
        word_start = pinyin_start + pinyin_len + 2
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
    builder.save('/tmp/test_win10_v3.dat')
    
    # 验证解析
    parser = Win10MSPinyinParser()
    count = parser.load('/tmp/test_win10_v3.dat')
    print(f"\n解析结果: {count} 词条")
    for word, py in parser.words:
        print(f"  {word}: {py}")
