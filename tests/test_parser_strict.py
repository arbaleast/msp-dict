"""解析器 strict 模式测试：必须区分「格式错误」与「文件损坏」。"""

import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.builder_win10 import Win10MSPinyinBuilder
from src.parser import MSPinyinFormatError, MSPinyinParser


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
