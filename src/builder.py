"""
微软拼音 DAT 词库构建器 ⚠️ 格式未验证

警告：此模块使用的固定 60 字节格式已被验证为错误的。
微软拼音用户词库的真实格式是变长编码，而非固定长度。
保留此文件仅供研究参考，不应用于生成实际的 DAT 文件。
"""

import struct
from typing import List, Tuple


class DATBuilder:
    """DAT 词库构建器"""
    
    ENTRY_SIZE = 60  # 每个词条固定 60 字节
    HEADER_SIZE = 0x400  # 文件头 1024 字节
    DATA_START = 0x13fc  # 数据区开始偏移 (5120 字节)
    
    # 标准 DAT 文件头
    HEADER_MAGIC = bytes.fromhex('55aa88800200600055aa55aa00200000')
    
    def __init__(self):
        self.entries: List[Tuple[str, bytes]] = []  # (文本, 拼音编码)
        
    def add_word(self, text: str, pinyin_code: bytes = None) -> None:
        """添加词条"""
        if pinyin_code is None:
            pinyin_code = b'\x00' * 8
        self.entries.append((text, pinyin_code))
        
    def add_words_from_txt(self, filepath: str, encoding: str = 'utf-8') -> int:
        """从 txt 文件批量添加词条"""
        count = 0
        with open(filepath, 'r', encoding=encoding) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t')
                text = parts[0].strip()
                if text:
                    self.add_word(text)
                    count += 1
        return count
        
    def build(self) -> bytes:
        """构建 DAT 文件内容"""
        header = bytearray(self.HEADER_SIZE)
        header[0:16] = self.HEADER_MAGIC
        
        data_start = 0x13fc
        data = bytearray()
        
        for text, pinyin_code in self.entries:
            text_bytes = text.encode('utf-16-le')
            text_len = len(text)  # 字符数
            
            # 跳过超过 22 字符的词条（60字节 entry 限制，44字节文本空间）
            # 辅助平面字符在 UTF-16 中占 2 个 code units
            if len(text_bytes) // 2 > 22:
                continue
            
            entry = bytearray(self.ENTRY_SIZE)
            struct.pack_into('<I', entry, 0, 0)  # 固定值
            struct.pack_into('<I', entry, 4, text_len)  # 文本长度（字符数）
            entry[8:16] = pinyin_code  # 拼音编码 (8字节)
            
            # 文本 (从偏移 16 开始，UTF-16LE 编码，以 0x0000 结尾)
            text_offset = 16
            entry[text_offset:text_offset + len(text_bytes)] = text_bytes
            # null terminator
            entry[text_offset + len(text_bytes):text_offset + len(text_bytes) + 2] = b'\x00\x00'
            
            data += bytes(entry)
            
        # 合并: header(0x400) + padding(0xffc) + data
        padding = data_start - self.HEADER_SIZE
        result = bytes(header) + b'\x00' * padding + bytes(data)
        return result
        
    def save(self, filepath: str) -> None:
        """保存为 DAT 文件"""
        data = self.build()
        with open(filepath, 'wb') as f:
            f.write(data)


def txt_to_dat(txt_path: str, dat_path: str) -> int:
    """将 txt 词库转换为 dat 格式"""
    builder = DATBuilder()
    count = builder.add_words_from_txt(txt_path)
    builder.save(dat_path)
    return count
