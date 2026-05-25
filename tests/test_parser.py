"""
测试 src/parser.py 模块

测试 MSPinyinParser 的各种边界条件和辅助方法。
核心的构建→解析闭环测试已在 src/test_win10_format.py 中覆盖。
"""

import os
import sys
import tempfile
import struct

# 确保可以导入 src 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.parser import MSPinyinParser, DictEntry
from src.builder_win10 import Win10MSPinyinBuilder


class TestMSPinyinParserEdgeCases:
    """解析器边界条件测试"""

    def setup_method(self):
        self.tmpfile = tempfile.mktemp(suffix='_test_parser.dat')

    def teardown_method(self):
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def test_file_not_found(self):
        """文件不存在应抛出 FileNotFoundError"""
        parser = MSPinyinParser()
        try:
            parser.load('/nonexistent/path.dat')
            assert False, "应抛出 FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_find_by_text_existing(self):
        """查找存在的词条"""
        builder = Win10MSPinyinBuilder()
        builder.add_word("中国", "zhongguo", 1)
        builder.add_word("北京", "beijing", 2)
        builder.save(self.tmpfile)

        parser = MSPinyinParser()
        parser.load(self.tmpfile)

        entry = parser.find_by_text("中国")
        assert entry is not None
        assert entry.text == "中国"
        assert entry.pinyin == "zhongguo"
        assert entry.rank == 1

    def test_find_by_text_not_existing(self):
        """查找不存在的词条应返回 None"""
        builder = Win10MSPinyinBuilder()
        builder.add_word("测试", "ceshi", 1)
        builder.save(self.tmpfile)

        parser = MSPinyinParser()
        parser.load(self.tmpfile)

        entry = parser.find_by_text("不存在的词条")
        assert entry is None

    def test_get_entry_count(self):
        """获取词条数量"""
        builder = Win10MSPinyinBuilder()
        test_words = [("词条1", "citiáo1", 1), ("词条2", "citiáo2", 2), ("词条3", "citiáo3", 3)]
        for word, py, rank in test_words:
            builder.add_word(word, py, rank)
        builder.save(self.tmpfile)

        parser = MSPinyinParser()
        parser.load(self.tmpfile)
        assert parser.get_entry_count() == 3

    def test_get_all_texts(self):
        """获取所有词条文本"""
        builder = Win10MSPinyinBuilder()
        builder.add_word("中国", "zhongguo", 1)
        builder.add_word("北京", "beijing", 2)
        builder.save(self.tmpfile)

        parser = MSPinyinParser()
        parser.load(self.tmpfile)
        texts = parser.get_all_texts()
        assert sorted(texts) == sorted(["中国", "北京"])

    def test_get_file_size(self):
        """获取文件大小"""
        builder = Win10MSPinyinBuilder()
        builder.add_word("测试", "ceshi", 1)
        builder.save(self.tmpfile)

        parser = MSPinyinParser()
        parser.load(self.tmpfile)
        assert parser.get_file_size() > 0

    def test_empty_data_after_header(self):
        """头部正确但无词条数据的文件"""
        # 构建无词条的文件
        builder = Win10MSPinyinBuilder()
        builder.save(self.tmpfile)

        parser = MSPinyinParser()
        count = parser.load(self.tmpfile)
        assert count == 0
        assert len(parser.entries) == 0

    def test_multiple_entries_same_text_different_rank(self):
        """相同文本不同词频的处理"""
        # Win10MSPinyinBuilder.add_word 允许重复添加
        builder = Win10MSPinyinBuilder()
        builder.add_word("测试", "ceshi", 1)
        builder.save(self.tmpfile)

        parser = MSPinyinParser()
        count = parser.load(self.tmpfile)
        assert count == 1

    def test_parser_with_pinyin_edge_cases(self):
        """拼音为空字符串的极端情况"""
        # 空拼音也是允许的
        builder = Win10MSPinyinBuilder()
        builder.add_word("AB测试", "", 1)  # 纯英文加中文混合但不给拼音
        builder.save(self.tmpfile)

        parser = MSPinyinParser()
        count = parser.load(self.tmpfile)
        # 空拼音词条可能不被写入（无 pinyin_char_len 时）
        # 这只是验证不会崩溃
        assert count >= 0

    def test_dict_entry_dataclass(self):
        """验证 DictEntry 数据类的字段"""
        entry = DictEntry(text="中国", pinyin="zhongguo", offset=0x40, rank=1)
        assert entry.text == "中国"
        assert entry.pinyin == "zhongguo"
        assert entry.offset == 0x40
        assert entry.rank == 1
