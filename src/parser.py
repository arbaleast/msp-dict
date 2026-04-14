"""
微软拼音用户词库解析器

格式: 每个词条固定 60 字节
- 4 字节: 固定值 0x00000000
- 4 字节: 文本长度 (uint32 LE)
- 8 字节: 拼音编码
- 变长: UTF-16LE 文本 + 0x0000
"""

import struct
from dataclasses import dataclass
from typing import List, Tuple, Optional
import io


@dataclass
class PinyinEntry:
    """拼音表条目"""
    offset: int
    full_pinyin: str      # 完整拼音 (如 "yi", "wan", "zi")
    shengmu: str           # 声母
    yunmu: str             # 韵母
    tones: int             # 声调


@dataclass
class DictEntry:
    """词库条目"""
    offset: int            # 文件中的偏移量
    text: str              # 中文文本
    pinyin_code: bytes     # 原始拼音编码 (8 字节)
    
    def __repr__(self):
        return f"DictEntry(text='{self.text}', offset=0x{self.offset:x})"


class MSPinyinParser:
    """微软拼音词库解析器"""
    
    ENTRY_SIZE = 60        # 每个词条固定 60 字节
    HEADER_SIZE = 0x400    # 文件头 1024 字节
    DATA_START = 0x13fc    # 数据区开始偏移
    
    def __init__(self, filepath: str = None):
        self.filepath = filepath
        self.data = None
        self.entries: List[DictEntry] = []
        
    def load(self, filepath: str) -> None:
        """加载词库文件"""
        self.filepath = filepath
        with open(filepath, 'rb') as f:
            self.data = f.read()
        self._parse()
        
    def _parse(self) -> None:
        """解析所有词条"""
        self.entries = []
        offset = self.DATA_START
        
        consecutive_invalid = 0
        max_consecutive_invalid = 10  # 连续10个无效词条才停止
        
        while offset + self.ENTRY_SIZE <= len(self.data):
            entry = self._parse_entry(offset)
            if entry is None:
                consecutive_invalid += 1
                if consecutive_invalid >= max_consecutive_invalid:
                    break
            else:
                consecutive_invalid = 0
                self.entries.append(entry)
            offset += self.ENTRY_SIZE
            
    def _parse_entry(self, offset: int) -> Optional[DictEntry]:
        """解析单个词条"""
        # 检查固定值
        fixed = struct.unpack('<I', self.data[offset:offset+4])[0]
        if fixed != 0:
            return None
            
        # 获取文本长度
        text_len = struct.unpack('<I', self.data[offset+4:offset+8])[0]
        if text_len < 1 or text_len > 50:
            return None
            
        # 获取拼音编码
        pinyin_code = self.data[offset+8:offset+16]
        
        # 获取文本
        text_offset = offset + 16
        text_bytes = self.data[text_offset:text_offset + text_len * 2]
        try:
            text = text_bytes.decode('utf-16-le', errors='replace')
            text = text.replace('\x00', '').strip()
            if not text or len(text) != text_len:
                return None
        except:
            return None
            
        return DictEntry(
            offset=offset,
            text=text,
            pinyin_code=pinyin_code
        )
        
    def get_entry_count(self) -> int:
        """获取词条数量"""
        return len(self.entries)
        
    def get_all_texts(self) -> List[str]:
        """获取所有词条文本"""
        return [e.text for e in self.entries]
        
    def find_by_text(self, text: str) -> Optional[DictEntry]:
        """根据文本查找词条"""
        for entry in self.entries:
            if entry.text == text:
                return entry
        return None
        
    def export_text(self, output_path: str) -> None:
        """导出为文本格式"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in self.entries:
                f.write(f"{entry.text}\n")
                
    def export_with_pinyin(self, output_path: str) -> None:
        """导出为文本格式 (带拼音)"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in self.entries:
                pinyin_hex = entry.pinyin_code.hex()
                f.write(f"{entry.text}\t{pinyin_hex}\n")
                
    def get_file_size(self) -> int:
        """获取词库文件大小"""
        if self.data:
            return len(self.data)
        return 0


def main():
    """测试解析器"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python parser.py <dat_file>")
        sys.exit(1)
        
    parser = MSPinyinParser()
    parser.load(sys.argv[1])
    
    print(f"文件: {sys.argv[1]}")
    print(f"文件大小: {parser.get_file_size()} bytes")
    print(f"词条数量: {parser.get_entry_count()}")
    print()
    
    print("前 10 个词条:")
    for i, entry in enumerate(parser.entries[:10]):
        print(f"  {i+1}. {entry}")
        
    print()
    print("后 10 个词条:")
    for i, entry in enumerate(parser.entries[-10:]):
        print(f"  {len(parser.entries)-9+i}. {entry}")


if __name__ == '__main__':
    main()
