"""
微软拼音用户词库管理工具 (mschxudp 格式)

Usage:
    from src import MSPinyinParser

    parser = MSPinyinParser()
    parser.load('custom_phrase.dat')
    print(f"词条数量: {parser.get_entry_count()}")
"""

from .parser import MSPinyinParser, DictEntry
from .editor import MSPinyinEditor

__all__ = ['MSPinyinParser', 'MSPinyinEditor', 'DictEntry']
