"""SCEL（搜狗细胞词库）解析器测试。

样本是**真实二进制**结构（tests/fixtures/valid_mock.scel，由
tests/fixtures/make_scel_fixture.py 生成），不是用纯文本伪装成 .scel。
"""

import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crawler.scel_parser import (  # noqa: E402
    ScelEntry,
    ScelParseError,
    ScelParser,
)

FIXTURE = ROOT / 'tests' / 'fixtures' / 'valid_mock.scel'


@pytest.fixture(scope='module')
def fixture_bytes() -> bytes:
    assert FIXTURE.exists(), (
        '缺少 SCEL 样本，请先运行: python tests/fixtures/make_scel_fixture.py')
    return FIXTURE.read_bytes()


class TestValidScel:
    """有效 SCEL 文件能解析出真实拼音。"""

    def test_fixture_exists_and_has_real_binary_header(self, fixture_bytes):
        assert FIXTURE.exists()
        assert len(fixture_bytes) > 0x1544
        # 魔数：@ \x15 \x00 \x00 + "DCS"
        assert fixture_bytes[:8] == b'@\x15\x00\x00DCS\x01'
        assert fixture_bytes[8:12] == struct.pack('<I', 1)

    def test_parses_entries_with_real_pinyin(self, fixture_bytes):
        parser = ScelParser()
        entries = parser.parse_bytes(fixture_bytes)

        assert len(entries) == 6
        mapping = {(e.word, e.pinyin) for e in entries}
        assert ('中国', "zhong'guo") in mapping
        assert ('测试', "ce'shi") in mapping
        assert ('阿房宫', "a'fang'gong") in mapping

    def test_pinyin_is_never_placeholder(self, fixture_bytes):
        parser = ScelParser()
        for entry in parser.parse_bytes(fixture_bytes):
            assert entry.pinyin, '拼音不得为空'
            assert entry.pinyin != 'xx', '不得使用占位符 xx'
            assert all(c.isascii() and (c.isalpha() or c == "'") for c in entry.pinyin)

    def test_same_pinyin_group_kept_together(self, fixture_bytes):
        parser = ScelParser()
        entries = parser.parse_bytes(fixture_bytes)
        same = [e for e in entries if e.pinyin == "ce'shi"]
        assert {e.word for e in same} == {'测试', '测验'}

    def test_polyphonic_word_keeps_both_readings(self, fixture_bytes):
        parser = ScelParser()
        entries = parser.parse_bytes(fixture_bytes)
        yinhang = sorted(e.pinyin for e in entries if e.word == '银行')
        assert yinhang == ["yin'hang", "yin'xing"], '多音词必须保留全部读音'

    def test_reads_dictionary_name(self, fixture_bytes):
        parser = ScelParser()
        parser.parse_bytes(fixture_bytes)
        assert parser.name == '测试细胞词库'

    def test_load_returns_entry_count(self):
        parser = ScelParser()
        assert parser.load(str(FIXTURE)) == 6
        assert all(isinstance(e, ScelEntry) for e in parser.entries)

    def test_entries_are_triples_compatible_with_merge(self, fixture_bytes):
        """scripts/merge.py 按 (词, 拼音, 词频) 三元组解包。"""
        parser = ScelParser()
        for word, pinyin, freq in parser.entries:
            assert isinstance(word, str) and word
            assert isinstance(pinyin, str) and pinyin
            assert isinstance(freq, int)


class TestCorruptScel:
    """损坏文件必须抛出明确异常，而不是静默返回空或崩溃。"""

    def test_empty_file_raises(self, tmp_path):
        empty = tmp_path / 'empty.scel'
        empty.write_bytes(b'')
        with pytest.raises(ScelParseError) as exc:
            ScelParser().load(str(empty))
        assert '过短' in str(exc.value)

    def test_text_file_raises_magic_error(self, tmp_path):
        fake = tmp_path / 'fake.scel'
        fake.write_bytes(b'not a scel file' * 400)
        with pytest.raises(ScelParseError) as exc:
            ScelParser().load(str(fake))
        assert '魔数' in str(exc.value)

    def test_truncated_file_raises(self, tmp_path, fixture_bytes):
        truncated = tmp_path / 'truncated.scel'
        truncated.write_bytes(fixture_bytes[:len(fixture_bytes) // 2])
        with pytest.raises(ScelParseError):
            ScelParser().load(str(truncated))

    def test_truncated_pinyin_table_raises(self, tmp_path, fixture_bytes):
        broken = tmp_path / 'broken_table.scel'
        broken.write_bytes(fixture_bytes[:0x1540 + 2])
        with pytest.raises(ScelParseError):
            ScelParser().load(str(broken))

    def test_absurd_dict_len_raises(self, tmp_path, fixture_bytes):
        data = bytearray(fixture_bytes)
        struct.pack_into('<I', data, 0x120, 99_999_999)
        broken = tmp_path / 'absurd.scel'
        broken.write_bytes(bytes(data))
        with pytest.raises(ScelParseError) as exc:
            ScelParser().load(str(broken))
        assert '词条组数异常' in str(exc.value)

    def test_absurd_py_count_raises(self, tmp_path, fixture_bytes):
        data = bytearray(fixture_bytes)
        struct.pack_into('<I', data, 0x1540, 88_888_888)
        broken = tmp_path / 'absurd_py.scel'
        broken.write_bytes(bytes(data))
        with pytest.raises(ScelParseError) as exc:
            ScelParser().load(str(broken))
        assert '拼音表条目数异常' in str(exc.value)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ScelParseError):
            ScelParser().load(str(tmp_path / 'nope.scel'))

    def test_bad_magic_variant_is_rejected(self, tmp_path):
        data = bytearray(FIXTURE.read_bytes())
        data[0:4] = b'@@@@'
        bad = tmp_path / 'badmagic.scel'
        bad.write_bytes(bytes(data))
        with pytest.raises(ScelParseError):
            ScelParser().load(str(bad))
