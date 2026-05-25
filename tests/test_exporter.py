"""
测试 src/exporter.py 模块

验证导出功能（JSON 导出、统计信息等）。
TXT/CSV 导出基本功能已在 src/test_win10_format.py 中覆盖。
"""

import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.parser import MSPinyinParser
from src.exporter import Exporter
from src.builder_win10 import Win10MSPinyinBuilder


class TestExporterEdgeCases:
    """导出器边界条件测试"""

    def setup_method(self):
        self.tmpfile = tempfile.mktemp(suffix='_test_exp.dat')
        self.builder = Win10MSPinyinBuilder()
        self.builder.add_word("中国", "zhongguo", 1)
        self.builder.add_word("北京", "beijing", 2)
        self.builder.add_word("上海", "shanghai", 3)
        self.builder.save(self.tmpfile)

        self.parser = MSPinyinParser()
        self.parser.load(self.tmpfile)
        self.exporter = Exporter(self.parser)

    def teardown_method(self):
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def test_export_json(self):
        """导出 JSON 格式"""
        output = self.tmpfile + '.json'
        count = self.exporter.export_json(output)
        assert count == 3

        with open(output, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert len(data) == 3
        assert data[0]['text'] == '中国'
        assert data[0]['pinyin'] == 'zhongguo'
        assert data[0]['rank'] == 1

        os.remove(output)

    def test_export_json_empty(self):
        """导出空词库 JSON"""
        empty_file = tempfile.mktemp(suffix='_empty.dat')
        empty_builder = Win10MSPinyinBuilder()
        empty_builder.save(empty_file)

        empty_parser = MSPinyinParser()
        empty_parser.load(empty_file)

        exporter = Exporter(empty_parser)
        output = empty_file + '.json'
        count = exporter.export_json(output)
        assert count == 0

        with open(output, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data == []

        os.remove(output)
        os.remove(empty_file)

    def test_get_stats(self):
        """获取统计信息"""
        stats = self.exporter.get_stats()
        assert stats['total_entries'] == 3
        assert stats['file_size'] > 0
        assert stats['avg_length'] == 2.0  # 都是双字词
        assert stats['max_length'] == 2
        assert stats['min_length'] == 2
        assert stats['double_char'] == 3
        assert stats['single_char'] == 0
        assert stats['has_pinyin'] == 3
        assert stats['no_pinyin'] == 0

    def test_get_stats_with_mixed_lengths(self):
        """混合长度词条的统计信息"""
        builder2 = Win10MSPinyinBuilder()
        builder2.add_word("测试", "ceshi", 1)           # 2字
        builder2.add_word("人工智能", "rengongzhineng", 1)  # 4字
        builder2.add_word("大语言模型", "dayuyanmoxing", 1) # 5字
        builder2.add_word("", "", 1)                        # 空词（应被过滤或正确处理）

        f2 = tempfile.mktemp(suffix='_mix.dat')
        builder2.save(f2)

        p2 = MSPinyinParser()
        p2.load(f2)

        exporter2 = Exporter(p2)
        stats = exporter2.get_stats()

        # 只有有效词条会计入统计
        assert stats['total_entries'] >= 2  # 至少2个有效词条
        assert stats['has_pinyin'] >= 2

        os.remove(f2)

    def test_export_txt_with_special_chars(self):
        """导出包含特殊字符的词条"""
        builder3 = Win10MSPinyinBuilder()
        builder3.add_word("C++", "c", 1)
        builder3.add_word(".NET", "dotnet", 2)
        builder3.add_word("Hello World", "helloworld", 3)

        f3 = tempfile.mktemp(suffix='_special.dat')
        builder3.save(f3)

        p3 = MSPinyinParser()
        p3.load(f3)

        exporter3 = Exporter(p3)
        txt_out = f3 + '.txt'
        count = exporter3.export_txt(txt_out)
        assert count > 0

        with open(txt_out, 'r', encoding='utf-8') as f:
            content = f.read()
        assert '\t' in content  # 确保制表符分隔

        os.remove(txt_out)
        os.remove(f3)

    def test_export_csv_with_empty_exporter(self):
        """空词库的 CSV 导出"""
        empty_file = tempfile.mktemp(suffix='_empty_exp.dat')
        empty_builder = Win10MSPinyinBuilder()
        empty_builder.save(empty_file)

        empty_parser = MSPinyinParser()
        empty_parser.load(empty_file)

        exporter = Exporter(empty_parser)
        csv_out = empty_file + '.csv'
        count = exporter.export_csv(csv_out)
        assert count == 0

        # CSV 仍应有表头
        with open(csv_out, 'r', encoding='utf-8') as f:
            import csv
            reader = csv.reader(f)
            header = next(reader)
            assert header == ['text', 'pinyin', 'rank']

        os.remove(csv_out)
        os.remove(empty_file)
