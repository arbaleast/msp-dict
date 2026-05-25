"""
测试 mschxudp 格式的构建→解析→编辑→导出完整循环

使用 pytest 运行:
    python -m pytest src/test_win10_format.py -v
"""

import os
import sys
import tempfile
import struct

# 确保可以导入 src 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.parser import MSPinyinParser, DictEntry
from src.editor import MSPinyinEditor
from src.exporter import Exporter
from src.importer import BatchImporter, RimeConverter, PinyinConverter
from src.builder_win10 import Win10MSPinyinBuilder, Win10MSPinyinParser


class TestMSchxudpFormat:
    """测试 mschxudp 格式完整闭环"""

    def setup_method(self):
        self.tmpfile = tempfile.mktemp(suffix='_test.dat')

    def teardown_method(self):
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def test_01_build_and_parse_roundtrip(self):
        """构建→解析 闭环: 验证文本和拼音保持一致性"""
        builder = Win10MSPinyinBuilder()
        test_data = [
            ("中国", "zhongguo", 1),
            ("北京", "beijing", 2),
            ("上海", "shanghai", 3),
            ("人工智能", "rengongzhineng", 1),
            ("机器学习", "jiqixuexi", 5),
            ("深度学习", "shenduxuexi", 3),
            ("数据分析", "shujufenxi", 2),
        ]
        for word, py, rank in test_data:
            builder.add_word(word, py, rank)
        builder.save(self.tmpfile)

        # 使用新版 parser 解析
        parser = MSPinyinParser()
        count = parser.load(self.tmpfile)

        assert count == len(test_data), f"词条数不匹配: {count} != {len(test_data)}"

        # 验证每个词条
        parsed_map = {e.text: e for e in parser.entries}
        for word, py, rank in test_data:
            assert word in parsed_map, f"缺少词条: {word}"
            assert parsed_map[word].pinyin == py, f"拼音不匹配: {word}: {parsed_map[word].pinyin} != {py}"

        print(f"[PASS] 构建->解析闭环通过: {count} 词条")

    def test_02_parse_empty_dict(self):
        """空词库解析测试"""
        builder = Win10MSPinyinBuilder()
        builder.save(self.tmpfile)

        parser = MSPinyinParser()
        count = parser.load(self.tmpfile)
        assert count == 0, f"空词库应返回 0，实际: {count}"
        print("[PASS] 空词库解析通过")

    def test_03_editor_add_and_remove(self):
        """编辑器添加/删除词条测试"""
        # 构建初始词库
        builder = Win10MSPinyinBuilder()
        builder.add_word("测试", "ceshi", 1)
        builder.add_word("词库", "ciku", 2)
        builder.add_word("编辑器", "bianjiqi", 3)
        builder.save(self.tmpfile)

        # 编辑
        editor = MSPinyinEditor()
        editor.load(self.tmpfile)
        assert editor.get_entry_count() == 3

        # 添加新词条
        assert editor.add_entry("机器学习", "jiqixuexi", 1)
        assert editor.add_entry("深度学习", "shenduxuexi", 2)
        assert not editor.add_entry("测试", "ceshi", 5)  # 重复应失败

        # 删除
        assert editor.remove_entry("词库")
        assert not editor.remove_entry("不存在")  # 不存在应失败

        # 保存
        editor.save(self.tmpfile)
        assert editor.get_entry_count() == 4  # 3 - 1 + 2 = 4

        # 验证结果
        texts = set(editor.get_all_texts())
        expected = {"测试", "编辑器", "机器学习", "深度学习"}
        assert texts == expected, f"词条不匹配: {texts} != {expected}"

        print(f"[PASS] 编辑器添加/删除通过: {texts}")

    def test_04_export_txt(self):
        """导出 TXT 测试"""
        # 构建词库
        builder = Win10MSPinyinBuilder()
        builder.add_word("中国", "zhongguo", 1)
        builder.save(self.tmpfile)

        parser = MSPinyinParser()
        parser.load(self.tmpfile)

        exporter = Exporter(parser)
        txt_file = self.tmpfile + '.txt'
        count = exporter.export_txt(txt_file)
        assert count == 1

        # 验证内容
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        assert '中国' in content
        assert 'zhongguo' in content

        os.remove(txt_file)
        print("[PASS] 导出 TXT 通过")

    def test_05_export_csv(self):
        """导出 CSV 测试"""
        builder = Win10MSPinyinBuilder()
        builder.add_word("北京", "beijing", 2)
        builder.save(self.tmpfile)

        parser = MSPinyinParser()
        parser.load(self.tmpfile)

        exporter = Exporter(parser)
        csv_file = self.tmpfile + '.csv'
        count = exporter.export_csv(csv_file)
        assert count == 1

        import csv
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == ['text', 'pinyin', 'rank']
            row = next(reader)
            assert row[0] == '北京'
            assert row[1] == 'beijing'

        os.remove(csv_file)
        print("[PASS] 导出 CSV 通过")

    def test_06_large_entry(self):
        """较长词汇构建解析测试"""
        builder = Win10MSPinyinBuilder()
        long_text = "中华人民共和国"
        long_pinyin = "zhonghuarenmingongheguo"
        builder.add_word(long_text, long_pinyin, 1)
        builder.save(self.tmpfile)

        parser = MSPinyinParser()
        count = parser.load(self.tmpfile)
        assert count == 1
        assert parser.entries[0].text == long_text
        assert parser.entries[0].pinyin == long_pinyin
        print(f"[PASS] 长词条测试通过: {long_text}")

    def test_07_invalid_file(self):
        """无效文件处理测试"""
        parser = MSPinyinParser()
        # 创建一个非 mschxudp 文件
        with open(self.tmpfile, 'wb') as f:
            f.write(b'invalid data')

        try:
            parser.load(self.tmpfile)
            assert False, "应抛出 ValueError"
        except ValueError as e:
            assert 'mschxudp' in str(e).lower() or '无效' in str(e), f"错误消息不明确: {e}"

        print("[PASS] 无效文件处理通过")

    def test_08_rime_format_detection(self):
        """Rime 格式检测测试"""
        rime_file = self.tmpfile + '.rime'
        with open(rime_file, 'w', encoding='utf-8') as f:
            f.write("""---
name: test
version: "1.0"
---
中国\tzhongguo
北京\tbeijing
""")

        fmt = RimeConverter.detect_format(rime_file)
        assert fmt == 'rime', f"格式检测错误: {fmt}"
        os.remove(rime_file)
        print("[PASS] Rime 格式检测通过")


class TestPinyinConverter:
    """拼音转换器测试"""

    def test_normalize_remove_spaces(self):
        assert PinyinConverter.normalize_pinyin("ni hao") == "nihao"

    def test_normalize_lowercase(self):
        assert PinyinConverter.normalize_pinyin("ZhongGuo") == "zhongguo"

    def test_normalize_tone_marks(self):
        assert PinyinConverter.normalize_pinyin("wǒ ài nǐ") == "woaini"

    def test_normalize_mixed(self):
        result = PinyinConverter.normalize_pinyin("  Wǒ  Ài  Nǐ  ")
        assert result == "woaini"

    def test_is_valid_pinyin(self):
        assert PinyinConverter.is_valid_pinyin("zhongguo")
        assert PinyinConverter.is_valid_pinyin("beijing")
        assert not PinyinConverter.is_valid_pinyin("")
        assert not PinyinConverter.is_valid_pinyin("ni hao")  # 有空格


class TestImporter:
    """导入器测试"""

    def setup_method(self):
        self.tmpfile = tempfile.mktemp(suffix='_importer.dat')
        self.txtfile = tempfile.mktemp(suffix='_import.txt')

        # 构建初始词库
        builder = Win10MSPinyinBuilder()
        builder.add_word("测试", "ceshi", 1)
        builder.save(self.tmpfile)

    def teardown_method(self):
        for f in [self.tmpfile, self.txtfile]:
            if os.path.exists(f):
                os.remove(f)

    def test_import_txt(self):
        """TXT 导入测试"""
        with open(self.txtfile, 'w', encoding='utf-8') as f:
            f.write("机器学习\tjiqixuexi\n")
            f.write("深度学习\n")  # 无拼音

        editor = MSPinyinEditor()
        editor.load(self.tmpfile)
        initial_count = editor.get_entry_count()

        importer = BatchImporter(editor)
        result = importer.import_txt(self.txtfile)

        assert importer.imported_count == 2, f"应导入 2 条，实际: {importer.imported_count}"
        assert importer.skipped_count == 0, f"应跳过 0 条，实际: {importer.skipped_count}"

        print(f"[PASS] TXT 导入测试通过: {result}")


if __name__ == '__main__':
    # 运行所有测试
    import traceback

    test_classes = [
        TestMSchxudpFormat,
        TestPinyinConverter,
        TestImporter,
    ]

    passed = 0
    failed = 0

    for cls in test_classes:
        instance = cls()
        # 安全调用 setup_method（部分类可能没有）
        setup = getattr(instance, 'setup_method', None)
        if callable(setup):
            setup()
        teardown = getattr(instance, 'teardown_method', None)
        for method_name in dir(cls):
            if method_name.startswith('test_'):
                method = getattr(instance, method_name)
                try:
                    method()
                    passed += 1
                except Exception as e:
                    # 使用 ASCII-safe 输出，避免 Windows GBK 编码错误
                    msg = f"[FAIL] {cls.__name__}.{method_name}: {e}"
                    try:
                        print(msg)
                    except UnicodeEncodeError:
                        print(msg.encode('ascii', errors='replace').decode('ascii'))
                    traceback.print_exc()
                    failed += 1
        # 安全调用 teardown_method
        if callable(teardown):
            teardown()

    try:
        print(f"\n{'=' * 40}")
        print(f"测试结果: {passed} 通过, {failed} 失败")
        print(f"{'=' * 40}")
    except UnicodeEncodeError:
        print(f"\n{'=' * 40}")
        print(f"[SUMMARY] {passed} passed, {failed} failed")
        print(f"{'=' * 40}")
    sys.exit(0 if failed == 0 else 1)
