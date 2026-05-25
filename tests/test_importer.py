"""
测试 src/importer.py 模块

验证各种导入格式和 RimeConverter 功能。
BatchImporter 的基本导入功能已在 src/test_win10_format.py 中覆盖。
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.parser import MSPinyinParser
from src.editor import MSPinyinEditor
from src.importer import BatchImporter, RimeConverter, PinyinConverter
from src.builder_win10 import Win10MSPinyinBuilder


class TestRimeConverter:
    """Rime 格式转换器测试"""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_detect_rime_format(self):
        """检测 Rime 格式"""
        filepath = os.path.join(self.tmpdir, 'rime_dict.yaml')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("""---
name: test
version: "1.0"
---
中国\tzhongguo
北京\tbeijing
""")
        fmt = RimeConverter.detect_format(filepath)
        assert fmt == 'rime', f"期望 rime，实际: {fmt}"

    def test_detect_csv_format(self):
        """检测 CSV 格式"""
        filepath = os.path.join(self.tmpdir, 'test.csv')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("""text,pinyin,rank
中国,zhongguo,1
北京,beijing,2
""")
        fmt = RimeConverter.detect_format(filepath)
        assert fmt == 'csv', f"期望 csv，实际: {fmt}"

    def test_detect_tsv_format(self):
        """检测 TSV 格式"""
        filepath = os.path.join(self.tmpdir, 'test.tsv')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("中国\tzhongguo\n北京\tbeijing\n")
        fmt = RimeConverter.detect_format(filepath)
        assert fmt == 'tsv', f"期望 tsv，实际: {fmt}"

    def test_detect_txt_format(self):
        """检测纯文本格式"""
        filepath = os.path.join(self.tmpdir, 'test.txt')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("中国\n北京\n上海\n")
        fmt = RimeConverter.detect_format(filepath)
        assert fmt == 'txt', f"期望 txt，实际: {fmt}"

    def test_detect_empty_file(self):
        """检测空文件格式"""
        filepath = os.path.join(self.tmpdir, 'empty.txt')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("")
        fmt = RimeConverter.detect_format(filepath)
        assert fmt == 'txt', f"期望 txt，实际: {fmt}"

    def test_parse_rime_dict(self):
        """解析 Rime 词库"""
        filepath = os.path.join(self.tmpdir, 'rime_dict.txt')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("""# Rime 词库
# 注释行
---
中国\tzhongguo
北京\tbeijing
机器学习\tjiqixuexi
""")
        entries = RimeConverter.parse_rime_dict(filepath)
        assert len(entries) == 3
        assert entries[0] == ("中国", "zhongguo")
        assert entries[1] == ("北京", "beijing")

    def test_generate_rime_dict(self):
        """生成 Rime 词库"""
        output = os.path.join(self.tmpdir, 'output.yaml')
        entries = [
            ("中国", "zhongguo"),
            ("北京", "beijing"),
            ("人工智能", "rengongzhineng"),
        ]
        count = RimeConverter.generate_rime_dict(entries, output, include_pinyin=True)
        assert count == 3

        with open(output, 'r', encoding='utf-8') as f:
            content = f.read()
        assert '中国\tzhongguo' in content
        assert '北京\tbeijing' in content
        assert '# 来源: MSPinyin Dict' in content

    def test_generate_rime_dict_no_pinyin(self):
        """生成 Rime 词库（不含拼音）"""
        output = os.path.join(self.tmpdir, 'output_nopy.txt')
        entries = [("中国", "zhongguo"), ("北京", "")]
        count = RimeConverter.generate_rime_dict(entries, output, include_pinyin=False)
        assert count == 2

        with open(output, 'r', encoding='utf-8') as f:
            content = f.read()
        # 不含拼音时只写词条
        assert '中国\tzhongguo' not in content
        assert '中国' in content


class TestBatchImporterExtended:
    """批量导入器扩展测试"""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.datfile = os.path.join(self.tmpdir, 'test.dat')
        self.builder = Win10MSPinyinBuilder()
        self.builder.add_word("测试", "ceshi", 1)
        self.builder.save(self.datfile)

        self.editor = MSPinyinEditor()
        self.editor.load(self.datfile)
        self.importer = BatchImporter(self.editor)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_import_csv_basic(self):
        """CSV 批量导入"""
        csv_file = os.path.join(self.tmpdir, 'import.csv')
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write("text,pinyin,rank\n")
            f.write("中国,zhongguo,1\n")
            f.write("北京,beijing,2\n")

        imported, skipped, errors = self.importer.import_csv(csv_file)
        assert imported == 2, f"期望导入 2，实际: {imported}"
        assert skipped == 0
        assert errors == 0

    def test_import_csv_with_dup(self):
        """CSV 导入含重复词条"""
        csv_file = os.path.join(self.tmpdir, 'dup.csv')
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write("text,pinyin\n")
            f.write("测试,ceshi\n")  # 已存在
            f.write("新词条,xincitiao\n")

        imported, skipped, errors = self.importer.import_csv(csv_file)
        assert imported == 1, f"期望导入 1，实际: {imported}"
        assert skipped >= 1  # "测试" 已存在

    def test_import_rime_basic(self):
        """Rime 格式批量导入"""
        rime_file = os.path.join(self.tmpdir, 'rime.txt')
        with open(rime_file, 'w', encoding='utf-8') as f:
            f.write("""中国\tzhongguo
北京\tbeijing\t2
"""
        )
        imported, skipped, errors = self.importer.import_rime(rime_file)
        assert imported == 2, f"期望导入 2，实际: {imported}"
        # "---" 分隔符行自动跳过，"name: test"含非法字符被跳过
        assert errors == 0

    def test_import_rime_with_freq(self):
        """Rime 格式导入含词频"""
        rime_file = os.path.join(self.tmpdir, 'rime_freq.txt')
        with open(rime_file, 'w', encoding='utf-8') as f:
            f.write("中国\tzhongguo\t5\n")
            f.write("北京\tbeijing\t3\n")

        imported, skipped, errors = self.importer.import_rime(rime_file)
        assert imported == 2

    def test_import_invalid_chinese(self):
        """无效中文词条应跳过"""
        txt_file = os.path.join(self.tmpdir, 'invalid.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("@@invalid\tblah\n")
            f.write("新词条_import\txincitiao\n")

        imported, skipped, errors = self.importer.import_txt(txt_file)
        assert imported == 1, f"期望导入 1，实际: {imported}"
        assert skipped == 1, f"期望跳过 1，实际: {skipped}"

    def test_import_empty_lines(self):
        """空行应被忽略"""
        txt_file = os.path.join(self.tmpdir, 'empty.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("\n\n")
            f.write("中国\tzhongguo\n")
            f.write("\n")

        imported, skipped, errors = self.importer.import_txt(txt_file)
        assert imported == 1

    def test_get_stats(self):
        """获取导入统计"""
        txt_file = os.path.join(self.tmpdir, 'stats.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("中国\tzhongguo\n")
            f.write("北京\tbeijing\n")

        self.importer.import_txt(txt_file)
        stats = self.importer.get_stats()
        assert stats['imported'] == 2
        assert stats['total'] == 2
        assert 'skipped' in stats
        assert 'errors' in stats


class TestPinyinConverterExtended:
    """拼音转换器扩展测试"""

    def test_normalize_with_numbers(self):
        """拼音含数字应保持不变"""
        result = PinyinConverter.normalize_pinyin("test123")
        assert result == "test123"

    def test_normalize_empty_string(self):
        """空字符串规范化"""
        result = PinyinConverter.normalize_pinyin("")
        assert result == ""

    def test_normalize_only_spaces(self):
        """仅空格规范化"""
        result = PinyinConverter.normalize_pinyin("   ")
        assert result == ""

    def test_is_valid_pinyin_with_numbers(self):
        """拼音验证：is_valid_pinyin 仅允许纯小写字母"""
        # is_valid_pinyin 正则要求 ^[a-z]+$，所以数字和特殊字符均无效
        assert not PinyinConverter.is_valid_pinyin("abc123")  # 含数字无效
        assert PinyinConverter.is_valid_pinyin("nihao")       # 纯小写字母有效
        assert not PinyinConverter.is_valid_pinyin("")        # 空字符串无效
        assert not PinyinConverter.is_valid_pinyin("abc def") # 含空格无效
        assert not PinyinConverter.is_valid_pinyin("abc-def") # 含连字符无效
