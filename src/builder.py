"""
微软拼音 DAT 词库构建器

从文本词库构建 DAT 二进制格式
"""

import struct
from typing import List, Tuple


class DATBuilder:
    """DAT 词库构建器"""
    
    ENTRY_SIZE = 60  # 每个词条固定 60 字节
    HEADER_SIZE = 0x400  # 文件头 1024 字节
    DATA_START = 0x13fc  # 数据区开始偏移 (20 * 60 = 0x4B0 from 0x1000... actually need to check)
    
    # 标准 DAT 文件头 (256 字节 from 0x00)
    HEADER_MAGIC = bytes.fromhex('55aa88800200600055aa55aa00200000')
    
    def __init__(self):
        self.entries: List[Tuple[str, bytes]] = []  # (文本, 拼音编码)
        
    def add_word(self, text: str, pinyin_code: bytes = None) -> None:
        """添加词条"""
        if pinyin_code is None:
            pinyin_code = b'\x00' * 8
        self.entries.append((text, pinyin_code))
        
    def add_words_from_txt(self, filepath: str, encoding: str = 'utf-8') -> int:
        """
        从 txt 文件批量添加词条
        
        Args:
            filepath: txt 文件路径
            encoding: 文件编码
            
        Returns:
            添加的词条数量
        """
        count = 0
        with open(filepath, 'r', encoding=encoding) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # 支持 "词语\t词频" 格式或纯词语格式
                parts = line.split('\t')
                text = parts[0].strip()
                if text:
                    self.add_word(text)
                    count += 1
        return count
        
    def build(self) -> bytes:
        """
        构建 DAT 文件内容
        
        Returns:
            DAT 文件内容
        """
        # 构建文件头 (256 字节)
        header = bytearray(self.HEADER_SIZE)
        
        # 写入魔数
        header[0:16] = self.HEADER_MAGIC
        
        # 数据区从 0x13fc 开始 (5120 字节偏移)
        # 需要 padding 0x13fc - 0x400 = 0xffc 字节
        data_start = 0x13fc
        data = bytearray()
        
        # 写入词条
        for text, pinyin_code in self.entries:
            text_bytes = text.encode('utf-16-le')
            text_len = len(text)
            
            # 词条结构 (60 字节):
            # +0x00: 4 字节 固定值 0x00000000
            # +0x04: 4 字节 文本长度
            # +0x08: 8 字节 拼音编码
            # +0x10: 变长 UTF-16LE 文本
            
            entry = bytearray(self.ENTRY_SIZE)
            struct.pack_into('<I', entry, 0, 0)  # 固定值
            struct.pack_into('<I', entry, 4, text_len)  # 文本长度
            entry[8:16] = pinyin_code  # 拼音编码 (8字节)
            
            # 文本 (从偏移 16 开始)
            text_offset = 16
            entry[text_offset:text_offset + text_len * 2] = text_bytes
            
            data += bytes(entry)
            
        # 合并: header(0x400) + padding(0xffc) + data
        padding = data_start - self.HEADER_SIZE  # 0xffc bytes
        result = bytes(header) + b'\x00' * padding + bytes(data)
        return result
        
    def save(self, filepath: str) -> None:
        """保存为 DAT 文件"""
        data = self.build()
        with open(filepath, 'wb') as f:
            f.write(data)


def txt_to_dat(txt_path: str, dat_path: str) -> int:
    """
    将 txt 词库转换为 dat 格式
    
    Args:
        txt_path: txt 文件路径 (词语\t词频 或 纯词语)
        dat_path: 输出 dat 文件路径
        
    Returns:
        转换的词条数量
    """
    builder = DATBuilder()
    count = builder.add_words_from_txt(txt_path)
    builder.save(dat_path)
    return count


def merge_to_dat(txt_files: List[str], dat_path: str) -> int:
    """
    合并多个 txt 文件并输出 dat
    
    Args:
        txt_files: txt 文件列表
        dat_path: 输出 dat 文件路径
        
    Returns:
        总词条数量
    """
    builder = DATBuilder()
    total = 0
    
    for txt_path in txt_files:
        try:
            count = builder.add_words_from_txt(txt_path)
            total += count
            print(f"  Added {count} from {txt_path}")
        except Exception as e:
            print(f"  Error reading {txt_path}: {e}")
            
    builder.save(dat_path)
    return total


def main():
    """测试构建器"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python builder.py <input.txt> <output.dat>")
        sys.exit(1)
        
    txt_path = sys.argv[1]
    dat_path = sys.argv[2]
    
    print(f"Converting {txt_path} to {dat_path}...")
    count = txt_to_dat(txt_path, dat_path)
    print(f"Done! {count} words converted.")
    
    # 验证
    from parser import MSPinyinParser
    parser = MSPinyinParser()
    parser.load(dat_path)
    print(f"Verified: {parser.get_entry_count()} entries in {dat_path}")


if __name__ == '__main__':
    main()
