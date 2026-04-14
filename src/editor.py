"""
微软拼音词库编辑器

支持添加/删除词条，使用重建模式确保词库格式正确
"""

import struct
from typing import List, Optional, Tuple
from .parser import MSPinyinParser, DictEntry


class MSPinyinEditor(MSPinyinParser):
    """微软拼音词库编辑器"""
    
    def __init__(self, filepath: str = None):
        super().__init__(filepath)
        self._pending_entries: List[Tuple[str, bytes]] = []  # 待添加的词条
        self._removed_texts: set = set()  # 待删除的词条
        
    def add_entry(self, text: str, pinyin_code: bytes = None) -> bool:
        """
        添加新词条 (标记待添加，保存时重建)
        
        Args:
            text: 中文文本
            pinyin_code: 拼音编码 (8 字节)，如果为 None 则使用默认值
            
        Returns:
            是否添加成功
        """
        if self.data is None:
            return False
            
        # 检查是否已存在
        if self.find_by_text(text):
            return False
            
        # 如果没有提供拼音编码，使用默认编码
        if pinyin_code is None:
            pinyin_code = b'\x00' * 8
            
        # 添加到待添加列表（不修改 self.entries，保存时再合并）
        self._pending_entries.append((text, pinyin_code))
        
        return True
        
    def remove_entry(self, text: str) -> bool:
        """
        删除词条 (标记待删除，保存时重建)
        
        Args:
            text: 要删除的文本
            
        Returns:
            是否删除成功
        """
        if self.data is None:
            return False
            
        entry = self.find_by_text(text)
        if entry is None:
            return False
            
        # 添加到待删除列表（不修改 self.entries，保存时再过滤）
        self._removed_texts.add(text)
        
        return True
        
    def save(self, filepath: str = None) -> None:
        """
        保存词库文件 (自动重建)
        
        Args:
            filepath: 保存路径，如果为 None 则覆盖原文件
        """
        if filepath is None:
            filepath = self.filepath
            
        # 过滤掉待删除的词条
        valid_entries = [e for e in self.entries if e.text not in self._removed_texts]
        
        # 合并待添加的词条（使用原始顺序：现有词条 + 新词条）
        for text, pinyin_code in self._pending_entries:
            temp_entry = DictEntry(
                offset=0,
                text=text,
                pinyin_code=pinyin_code
            )
            valid_entries.append(temp_entry)
            
        # 保留文件头
        header = self.data[:self.DATA_START]
        
        # 重建数据区
        new_data = bytearray()
        for entry in valid_entries:
            text_bytes = entry.text.encode('utf-16-le')
            text_len = len(entry.text)
            
            e = bytearray(self.ENTRY_SIZE)
            struct.pack_into('<I', e, 0, 0)
            struct.pack_into('<I', e, 4, text_len)
            e[8:16] = entry.pinyin_code
            e[16:16 + text_len * 2] = text_bytes
            
            new_data += bytes(e)
            
        self.data = header + bytes(new_data)
        
        # 写入文件
        with open(filepath, 'wb') as f:
            f.write(self.data)
            
        # 清空待处理列表
        self._pending_entries.clear()
        self._removed_texts.clear()
        
        # 重新加载以确保一致性
        self._parse()
        
    def rebuild(self) -> None:
        """
        重建词库文件 (重新组织数据结构)
        """
        if self.data is None:
            return
            
        valid_entries = [e for e in self.entries if e.text not in self._removed_texts]
            
        # 保留文件头
        header = self.data[:self.DATA_START]
        
        # 重建数据区
        new_data = bytearray()
        for entry in valid_entries:
            text_bytes = entry.text.encode('utf-16-le')
            text_len = len(entry.text)
            
            e = bytearray(self.ENTRY_SIZE)
            struct.pack_into('<I', e, 0, 0)
            struct.pack_into('<I', e, 4, text_len)
            e[8:16] = entry.pinyin_code
            e[16:16 + text_len * 2] = text_bytes
            
            new_data += bytes(e)
            
        self.data = header + bytes(new_data)


def main():
    """测试编辑器"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python editor.py <dat_file>")
        sys.exit(1)
        
    editor = MSPinyinEditor()
    editor.load(sys.argv[1])
    
    print(f"文件: {sys.argv[1]}")
    print(f"词条数量: {editor.get_entry_count()}")
    
    # 测试查找
    entry = editor.find_by_text("黑客")
    if entry:
        print(f"找到: {entry}")
    else:
        print("未找到 '黑客'")


if __name__ == '__main__':
    main()
