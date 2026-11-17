"""扩展词源（萌娘百科 / 中文维基 / 搜狗细胞词库）接入的配额与清洗测试。"""

import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.builder_win10 import Win10MSPinyinBuilder  # noqa: E402
from tests.dat_helpers import iter_records  # noqa: E402

spec = importlib.util.spec_from_file_location('msp_merge', os.path.join(ROOT, 'scripts', 'merge.py'))
merge_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merge_module)


def _write_tsv(path, rows):
    lines = [f"{word}\t{pinyin}\t{freq}\t{source}" for word, pinyin, freq, source in rows]
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


def test_extended_quota_is_respected(tmp_path):
    def code(prefix, i):
        return f"{prefix}{chr(97 + i // 26)}{chr(97 + i % 26)}"

    rows = [(f"基础{chr(0x4e00 + i)}", code("jichu", i), 100 - i, "base")
            for i in range(200)]
    rows += [(f"扩展{chr(0x4e00 + i)}", code("kuozhan", i), 1, "moegirl")
             for i in range(50)]
    src = _write_tsv(tmp_path / 'all.txt', rows)

    builder = Win10MSPinyinBuilder(timestamp=1600000000)
    selected = builder.add_from_text_file(
        str(src), limit=100, extended_ratio=0.1,
        extended_max_word_units=8, extended_min_word_units=2)
    records = iter_records(builder.build())

    assert selected == 100
    assert len(records) == 100
    ext = [r for r in records if r['word'].startswith('扩展')]
    assert len(ext) == 10          # 100 * 0.1
    assert len(records) - len(ext) == 90


def test_extended_never_takes_first_candidate_over_base(tmp_path):
    rows = [
        ("中过", "zhongguo", 999, "wiki"),      # 扩展源词频极高
        ("中国", "zhongguo", 5, "base"),
    ]
    src = _write_tsv(tmp_path / 'rank.txt', rows)

    builder = Win10MSPinyinBuilder(timestamp=1600000000)
    builder.add_from_text_file(str(src))
    records = iter_records(builder.build())

    assert [r['word'] for r in records] == ["中国", "中过"]
    assert [r['position'] for r in records] == [1, 2]


def test_extended_long_words_are_filtered_by_profile_limit(tmp_path):
    rows = [
        ("中国", "zhongguo", 100, "base"),
        ("初音未来", "chuyinweilai", 1, "moegirl"),       # 4 字，保留
        ("中华人民共和国", "zhonghua", 1, "wiki"),         # 7 字，扩展源上限 5
    ]
    src = _write_tsv(tmp_path / 'len.txt', rows)

    builder = Win10MSPinyinBuilder(timestamp=1600000000)
    builder.add_from_text_file(str(src), extended_max_word_units=5)
    records = iter_records(builder.build())

    # 记录按拼音排序写出；7 字的扩展词条被 profile 上限拦截
    assert [r['word'] for r in records] == ["初音未来", "中国"]


def test_duplicate_word_prefers_base_source(tmp_path):
    rows = [
        ("中国", "zhongguo", 10, "base"),
        ("中国", "zhongguo", 999, "moegirl"),
    ]
    src = _write_tsv(tmp_path / 'dup.txt', rows)

    builder = Win10MSPinyinBuilder(timestamp=1600000000)
    builder.add_from_text_file(str(src))
    records = iter_records(builder.build())

    assert len(records) == 1
    assert records[0]['position'] == 1


def test_merge_file_keeps_source_column_and_dedupes(tmp_path):
    merged_path = tmp_path / 'msp_full.txt'
    merged = [
        ("中国", "zhongguo", 100, "base"),
        ("初音未来", "chuyinweilai", 1, "moegirl"),
    ]
    count = merge_module.write_full(merged, tmp_path)

    assert count == 2
    assert merged_path.read_text(encoding='utf-8') == (
        "中国\tzhongguo\t100\tbase\n"
        "初音未来\tchuyinweilai\t1\tmoegirl\n"
    )


def test_scel_parser_wrapper_returns_empty_on_bad_file(tmp_path):
    bad = tmp_path / 'bad.scel'
    bad.write_bytes(b'not a scel file')

    assert merge_module.parse_scel_file(bad) == []
