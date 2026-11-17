"""合并脚本测试：无拼音/无词频词条不能进入 msp_full.txt。"""

import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

spec = importlib.util.spec_from_file_location('msp_merge', os.path.join(ROOT, 'scripts', 'merge.py'))
merge_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merge_module)


def test_parse_rime_three_columns():
    entries = merge_module.parse_rime("中国\tzhong guo\t31450\n北京\tbei jing\t100\n")

    assert entries == [("中国", "zhong guo", 31450), ("北京", "bei jing", 100)]


def test_parse_rime_word_pinyin_only():
    entries = merge_module.parse_rime("中国\tzhongguo\n")

    assert entries == [("中国", "zhongguo", 1)]


def test_parse_rime_word_frequency_only():
    entries = merge_module.parse_rime("〇〇八\t100\n")

    assert entries == [("〇〇八", "", 100)]


def test_merge_prefers_pinyin_and_max_frequency():
    merged = merge_module.merge([
        [("中国", "", 50)],
        [("中国", "zhongguo", 10)],
        [("中国", "zhongguo", 99)],
    ])

    assert merged == [("中国", ("zhongguo", 99))]


def test_write_full_drops_empty_pinyin_and_zero_frequency(tmp_path):
    merged = [
        ("中国", ("zhongguo", 500)),
        ("腾讯词", ("", 100)),
        ("零频词", ("lingpin", 0)),
    ]

    count = merge_module.write_full(merged, tmp_path)

    assert count == 1
    assert (tmp_path / 'msp_full.txt').read_text(encoding='utf-8') == "中国\tzhongguo\t500\n"
