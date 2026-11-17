"""
构建器格式合规性测试（Issue #3）

断言依据 imewlconverter MsChxUdpExporterBase.cs 的字段语义：
  * +0x06 是同一拼音下的候选序号（1 起，UI 只展示 1~9），不是词频
  * +0x0C 是 2000-01-01 纪元秒
  * 词条区起始 = 0x40 + 4×词条数，结束 = 文件大小，保留区全 0
"""

import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.builder_win10 import Win10MSPinyinBuilder
from src.format_spec import EPOCH_2000_UNIX
from src.parser import MSPinyinParser
from tests.dat_helpers import iter_records


def build(entries, timestamp=1600000000):
    builder = Win10MSPinyinBuilder(timestamp=timestamp)
    for word, code, freq in entries:
        builder.add_word(word, code, freq)
    return builder, builder.build()


class TestCandidatePositions:
    def test_frequency_is_not_written_as_position(self):
        """词频 31450 不能变成候选位 218（31450 & 0xFF）"""
        _, data = build([("人工智能", "rengongzhineng", 31450)])
        records = iter_records(data)

        assert len(records) == 1
        assert records[0]['position'] == 1
        assert records[0]['word'] == "人工智能"

    def test_same_pinyin_positions_are_sequential_and_ordered_by_freq(self):
        _, data = build([
            ("阿", "a", 50),
            ("啊", "a", 100),
            ("吖", "a", 10),
        ])
        records = iter_records(data)

        assert [r['word'] for r in records] == ["啊", "阿", "吖"]
        assert [r['position'] for r in records] == [1, 2, 3]

    def test_different_pinyin_restarts_at_one(self):
        _, data = build([
            ("啊", "a", 100),
            ("阿", "a", 50),
            ("斤", "jin", 10),
            ("今", "jin", 20),
        ])
        records = iter_records(data)

        assert [r['code'] for r in records] == ["a", "a", "jin", "jin"]
        assert [r['position'] for r in records] == [1, 2, 1, 2]

    def test_more_than_nine_same_pinyin_are_dropped(self):
        entries = [(f"字{i}", "a", 100 - i) for i in range(12)]
        builder, data = build(entries)
        records = iter_records(data)

        assert len(records) == 9
        assert [r['position'] for r in records] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
        assert builder.stats.reasons['candidate_overflow'] == 3


class TestTimestamps:
    def test_header_and_record_timestamps(self):
        _, data = build([("中国", "zhongguo", 1)], timestamp=1600000000)

        header_ts = struct.unpack_from('<Q', data, 32)[0]
        assert header_ts == 1600000000
        assert iter_records(data)[0]['record_ts'] == 1600000000 - EPOCH_2000_UNIX

    def test_reserved_header_bytes_are_zero(self):
        _, data = build([("中国", "zhongguo", 1)])

        assert data[0x28:0x40] == b'\x00' * 24

    def test_deterministic_output(self):
        entries = [("中国", "zhongguo", 1), ("北京", "beijing", 2)]
        _, first = build(entries, timestamp=1600000000)
        _, second = build(entries, timestamp=1600000000)

        assert first == second


class TestHeaderLayout:
    def test_offsets_point_at_records_and_end_matches_file_size(self):
        _, data = build([
            ("中国", "zhongguo", 1),
            ("北京", "beijing", 2),
            ("上海", "shanghai", 3),
        ])

        count = struct.unpack_from('<I', data, 28)[0]
        phrase_start = struct.unpack_from('<I', data, 20)[0]
        phrase_end = struct.unpack_from('<I', data, 24)[0]

        assert count == 3
        assert phrase_start == 0x40 + 4 * 3
        assert phrase_end == len(data)
        assert [struct.unpack_from('<I', data, 0x40 + i * 4)[0] for i in range(3)] == [0, 38, 78]

    def test_empty_dictionary_header(self):
        _, data = build([])

        assert len(data) == 0x40
        assert struct.unpack_from('<I', data, 20)[0] == 0x40
        assert struct.unpack_from('<I', data, 24)[0] == 0x40
        assert struct.unpack_from('<I', data, 28)[0] == 0


class TestUtf16Offsets:
    def test_surrogate_pair_word_uses_byte_lengths(self):
        """生僻字 𠀀(U+20000) 是 4 字节 UTF-16LE，偏移必须按字节计算"""
        word = "𠀀"
        _, data = build([(word, "yu", 1)])
        record = iter_records(data)[0]

        # hanzi_offset 只与拼音有关：18 + 2×2
        assert record['hanzi_offset'] == 22
        # 记录大小 = 16 头 + 4 拼音 + 2 分隔 + 4 词 + 2 结尾
        assert record['size'] == 28
        assert record['word'] == word

    def test_roundtrip_via_parser_keeps_surrogate_word(self, tmp_path):
        builder = Win10MSPinyinBuilder(timestamp=1600000000)
        builder.add_word("𠀀𠀁", "yuyu", 5)
        path = tmp_path / "surrogate.dat"
        path.write_bytes(builder.build())

        parser = MSPinyinParser()
        assert parser.load(str(path)) == 1
        assert parser.entries[0].text == "𠀀𠀁"
        assert parser.entries[0].pinyin == "yuyu"


class TestCleaning:
    def test_empty_pinyin_is_dropped(self):
        builder, data = build([("中国", "", 1), ("北京", "beijing", 2)])

        assert iter_records(data)[0]['word'] == "北京"
        assert builder.stats.reasons['empty_pinyin'] == 1
        assert builder.stats.accepted == 1

    def test_invalid_pinyin_characters_are_dropped(self):
        builder, data = build([
            ("词一", "ci1", 1),
            ("词二", "ci#", 2),
            ("词三", "ci shi", 3),
        ])

        assert [r['code'] for r in iter_records(data)] == ["cishi"]
        assert builder.stats.reasons['invalid_pinyin'] == 2

    def test_tone_marks_and_uppercase_are_normalized(self):
        _, data = build([("中国", "ZhōngGuó", 1)])

        assert iter_records(data)[0]['code'] == "zhongguo"

    def test_u_umlaut_becomes_v(self):
        _, data = build([("旅游", "lǚyóu", 1)])

        assert iter_records(data)[0]['code'] == "lvyou"

    def test_overlong_word_is_dropped(self):
        builder, data = build([("字" * 65, "zi", 1), ("字" * 64, "zi", 2)])

        assert [len(r['word']) for r in iter_records(data)] == [64]
        assert builder.stats.reasons['word_too_long'] == 1

    def test_overlong_code_is_dropped(self):
        builder, data = build([("词", "a" * 33, 1), ("词二", "a" * 32, 2)])

        assert [len(r['code']) for r in iter_records(data)] == [32]
        assert builder.stats.reasons['code_too_long'] == 1

    def test_unpaired_surrogate_is_dropped(self):
        builder, data = build([("坏\ud800词", "huaici", 1), ("好词", "haoci", 2)])

        assert [r['word'] for r in iter_records(data)] == ["好词"]
        assert builder.stats.reasons['unpaired_surrogate'] == 1

    def test_nul_character_is_dropped(self):
        builder, data = build([("中\x00国", "zhongguo", 1)])

        assert iter_records(data) == []
        assert builder.stats.reasons['illegal_char'] == 1

    def test_duplicate_pair_keeps_one_entry(self):
        builder, data = build([
            ("中国", "zhongguo", 10),
            ("中国", "zhongguo", 99),
        ])

        records = iter_records(data)
        assert len(records) == 1
        assert records[0]['word'] == "中国"
        assert builder.stats.reasons['duplicate'] == 1

    def test_output_is_sorted_by_pinyin(self):
        _, data = build([
            ("中国", "zhongguo", 1),
            ("北京", "beijing", 2),
            ("上海", "shanghai", 3),
        ])

        assert [r['code'] for r in iter_records(data)] == ["beijing", "shanghai", "zhongguo"]


class TestRankModes:
    def test_position_mode_preserves_given_positions(self):
        builder = Win10MSPinyinBuilder(timestamp=1600000000, rank_mode='position')
        builder.add_word("阿", "a", 5)
        builder.add_word("啊", "a", 3)
        builder.add_word("吖", "a", 9)
        records = iter_records(builder.build())

        assert [r['word'] for r in records] == ["啊", "阿", "吖"]
        assert [r['position'] for r in records] == [3, 5, 9]

    def test_position_mode_rejects_out_of_range(self):
        builder = Win10MSPinyinBuilder(timestamp=1600000000, rank_mode='position')
        builder.add_word("零", "a", 0)
        builder.add_word("超", "a", 10)
        builder.add_word("好", "a", 1)
        records = iter_records(builder.build())

        assert [r['word'] for r in records] == ["好"]
        assert builder.stats.reasons['invalid_position'] == 1
        assert builder.stats.reasons['candidate_overflow'] == 1

    def test_position_mode_rejects_duplicate_position_for_same_code(self):
        builder = Win10MSPinyinBuilder(timestamp=1600000000, rank_mode='position')
        builder.add_word("甲", "a", 2)
        builder.add_word("乙", "a", 2)
        records = iter_records(builder.build())

        assert [r['word'] for r in records] == ["甲"]
        assert builder.stats.reasons['duplicate_position'] == 1


class TestFrequencyToPositionMapping:
    def test_high_frequency_never_wraps_to_zero(self):
        builder = Win10MSPinyinBuilder(timestamp=1600000000)
        builder.add_word("甲", "a", 256)     # 256 & 0xFF == 0 的旧 bug
        builder.add_word("乙", "a", 65536)   # 65536 & 0xFF == 0
        builder.add_word("丙", "a", 999999999)
        records = iter_records(builder.build())

        assert [r['position'] for r in records] == [1, 2, 3]
        assert [r['word'] for r in records] == ["丙", "乙", "甲"]
