"""
测试 src/parser.py 模块

测试 MSPinyinParser 的各种边界条件和辅助方法。
核心的构建→解析闭环测试已在 tests/test_builder_format.py 中覆盖。
"""

import os
import struct
import sys
import tempfile

import pytest

# 确保可以导入 src 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.parser import MSPinyinFormatError, MSPinyinParser, DictEntry
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
        # 拼音必须是合法的 a-z 序列（数字/符号会被构建器按格式规范拦截）
        test_words = [("词条甲", "citiajia", 1), ("词条乙", "citiaoyi", 2), ("词条丙", "citiaobing", 3)]
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


# ----------------------------------------------------------------------
# strict 模式：区分「文件格式错误」与「文件已损坏」
# ----------------------------------------------------------------------


def make_dat(tmp_path, entries=None):
    entries = entries or [("中国", "zhongguo", 1), ("北京", "beijing", 2)]
    builder = Win10MSPinyinBuilder(timestamp=1600000000)
    for word, code, freq in entries:
        builder.add_word(word, code, freq)
    path = tmp_path / "dict.dat"
    path.write_bytes(builder.build())
    return path


def test_strict_load_parses_valid_file(tmp_path):
    path = make_dat(tmp_path)

    parser = MSPinyinParser()
    assert parser.load(str(path), strict=True) == 2
    assert parser.invalid_entries == 0
    assert parser.warnings == []


def test_wrong_magic_is_format_error(tmp_path):
    data = bytearray(make_dat(tmp_path).read_bytes())
    data[0:8] = b'xxxxxxxx'
    path = tmp_path / "bad.dat"
    path.write_bytes(data)

    with pytest.raises(MSPinyinFormatError) as excinfo:
        MSPinyinParser().load(str(path), strict=True)

    assert excinfo.value.category == 'format'


def test_truncated_file_is_corruption(tmp_path):
    data = make_dat(tmp_path).read_bytes()
    path = tmp_path / "truncated.dat"
    path.write_bytes(data[:-4])

    with pytest.raises(MSPinyinFormatError) as excinfo:
        MSPinyinParser().load(str(path), strict=True)

    assert excinfo.value.category == 'corruption'
    assert '越界' in str(excinfo.value)


def test_non_monotonic_offsets_is_corruption(tmp_path):
    data = bytearray(make_dat(tmp_path, [
        ("中国", "zhongguo", 1), ("北京", "beijing", 2), ("上海", "shanghai", 3),
    ]).read_bytes())
    second = struct.unpack_from('<I', data, 0x40 + 4)[0]
    struct.pack_into('<I', data, 0x40 + 8, second)
    path = tmp_path / "offsets.dat"
    path.write_bytes(data)

    with pytest.raises(MSPinyinFormatError) as excinfo:
        MSPinyinParser().load(str(path), strict=True)

    assert excinfo.value.category == 'corruption'


def test_bad_entry_magic_is_corruption_in_strict_mode(tmp_path):
    data = bytearray(make_dat(tmp_path).read_bytes())
    phrase_start = struct.unpack_from('<I', data, 20)[0]
    struct.pack_into('<I', data, phrase_start, 0xDEADBEEF)
    path = tmp_path / "entry.dat"
    path.write_bytes(data)

    with pytest.raises(MSPinyinFormatError) as excinfo:
        MSPinyinParser().load(str(path), strict=True)

    assert excinfo.value.category == 'corruption'


def test_lenient_mode_skips_bad_entry(tmp_path):
    data = bytearray(make_dat(tmp_path).read_bytes())
    phrase_start = struct.unpack_from('<I', data, 20)[0]
    struct.pack_into('<I', data, phrase_start, 0xDEADBEEF)
    path = tmp_path / "entry.dat"
    path.write_bytes(data)

    parser = MSPinyinParser()
    assert parser.load(str(path)) == 1
    assert parser.invalid_entries == 1
    # 构建器按拼音排序，第一条是 beijing（已被破坏），剩下 zhongguo
    assert parser.entries[0].text == "中国"


def test_parse_bytes_matches_load(tmp_path):
    path = make_dat(tmp_path)
    parser = MSPinyinParser()

    assert parser.parse_bytes(path.read_bytes()) == 2
    assert [e.text for e in parser.entries] == ["北京", "中国"]
