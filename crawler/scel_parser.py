"""
搜狗细胞词库 (.scel) 解析器

Scel 格式参考:
- https://github.com/studyzy/imewlconverter
- https://github.com/KaixuanZhou/PyScel

主要结构:
1. 文件头 (0x200 字节)
2. 拼音表 (GBK 编码的拼音字符串)
3. 词条区 (汉字 + 拼音索引)
"""

import struct
from typing import List, Tuple, Optional


class ScelParser:
    """搜狗细胞词库 (.scel) 解析器"""
    
    # 文件头偏移量
    H_OFFSET = 0x0        # 0x40 0x00 0x00 0x00 开头
    H_NAME = 0x200        # 词库名称 (GBK)
    H_CATEGORY = 0x304    # 分类 (GBK)
    H_DESC = 0x408        # 描述 (GBK)
    
    # 词条区偏移
    F_PHRASE_COUNT = 0x1c  # 词条总数
    F_PHRASE_START = 0x24  # 词条区起始偏移
    
    def __init__(self, filepath: str = None):
        self.filepath = filepath
        self.name = ""
        self.category = ""
        self.description = ""
        self.entries: List[Tuple[str, str, int]] = []  # [(word, pinyin, freq), ...]
    
    def load(self, filepath: str) -> int:
        """加载 scel 文件，返回词条数"""
        self.filepath = filepath
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # 解析文件头
        self._parse_header(data)
        
        # 解析词条
        self.entries = self._parse_phrases(data)
        
        return len(self.entries)
    
    def _parse_header(self, data: bytes) -> None:
        """解析文件头"""
        try:
            # 词库名称 (GBK, 0x200 偏移)
            self.name = self._read_gbk_string(data, self.H_NAME, 0x100)
            # 分类
            self.category = self._read_gbk_string(data, self.H_CATEGORY, 0x100)
            # 描述
            self.description = self._read_gbk_string(data, self.H_DESC, 0x200)
        except Exception:
            pass
    
    def _read_gbk_string(self, data: bytes, start: int, max_len: int) -> str:
        """读取 GBK 编码字符串"""
        end = start
        while end < min(start + max_len, len(data)) and data[end:end+2] != b'\x00\x00':
            end += 2
        try:
            return data[start:end].decode('gbk', errors='replace').rstrip('\x00')
        except Exception:
            return ""
    
    def _parse_phrases(self, data: bytes) -> List[Tuple[str, str, int]]:
        """解析词条区"""
        entries = []
        
        try:
            phrase_count = struct.unpack('<I', data[self.F_PHRASE_COUNT:self.F_PHRASE_COUNT + 4])[0]
            phrase_start = struct.unpack('<I', data[self.F_PHRASE_START:self.F_PHRASE_START + 4])[0]
            
            pos = phrase_start
            
            for _ in range(phrase_count):
                if pos >= len(data) - 4:
                    break
                    
                # 读取词条信息
                try:
                    entry = self._read_phrase_entry(data, pos)
                    if entry:
                        word, pinyin, freq, next_pos = entry
                        if word and pinyin:
                            entries.append((word, pinyin, freq))
                        pos = next_pos
                    else:
                        break
                except Exception:
                    break
                    
        except Exception as e:
            print(f"词条解析错误: {e}")
        
        return entries
    
    def _read_phrase_entry(self, data: bytes, pos: int) -> Optional[Tuple[str, str, int, int]]:
        """读取单个词条"""
        # 词条头部结构
        head_size = 8  # 简化处理
        
        if pos + head_size > len(data):
            return None
        
        # 尝试解析词条
        # 格式: [未知][汉字数][拼音信息偏移][词频][未知]...
        
        try:
            # 跳过一些固定头部字节来定位
            # 实际位置需要根据具体格式调整
            
            # 简化：直接搜索汉字内容
            # 搜狗细胞词库词条格式大致为:
            # [word_len:2][word:2*word_len][pinyin_index:4][freq:4]
            
            word_count = struct.unpack('<H', data[pos:pos + 2])[0]
            
            # 验证汉字数合理性 (1-50)
            if word_count < 1 or word_count > 50:
                return None
            
            # 读取汉字
            word_start = pos + 2
            word_end = word_start + word_count * 2
            if word_end > len(data):
                return None
            
            word = data[word_start:word_end].decode('gbk', errors='replace')
            
            # 跳过词条结构到下一个词条
            # 需要根据实际格式调整
            entry_size = 2 + word_count * 2 + 4 + 4 + 2  # 估算
            
            return (word, "", 1, pos + entry_size)
            
        except Exception:
            return None
    
    def get_entries(self) -> List[Tuple[str, str, int]]:
        """获取所有词条"""
        return self.entries
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'entry_count': len(self.entries)
        }


def main():
    """测试解析器"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python scel_parser.py <file.scel>")
        sys.exit(1)
    
    parser = ScelParser()
    try:
        count = parser.load(sys.argv[1])
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
    
    stats = parser.get_stats()
    print(f"词库: {stats['name']}")
    print(f"分类: {stats['category']}")
    print(f"词条数: {stats['entry_count']}")
    
    entries = parser.get_entries()
    if entries:
        print("\n前 10 个词条:")
        for i, (word, pinyin, freq) in enumerate(entries[:10]):
            print(f"  {i+1}. {word} [{pinyin}] (freq={freq})")


if __name__ == '__main__':
    main()
