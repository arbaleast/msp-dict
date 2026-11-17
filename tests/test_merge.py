"""合并脚本测试：来源标记、基础源优先、扩展源清洗。"""

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


def test_parse_extended_dict_skips_header():
    content = "---\nname: zhwiki\nsort: by_weight\n...\n中国\tzhong guo\n北京\tbei jing\n"

    entries = merge_module.parse_extended_dict(content)

    assert entries == [("中国", "zhong guo", 1), ("北京", "bei jing", 1)]


def test_clean_extended_filters_noise():
    clean = merge_module.clean_extended

    assert clean("中国", "zhong guo") == "zhongguo"
    assert clean("旅行", "lü xing") == "lvxing"          # ü -> v
    assert clean("中国", "zhong guo") is not None
    assert clean("ABC模式", "abcmoshi") is None         # 含英文
    assert clean("中国", "zhong1") is None               # 数字
    assert clean("中", "zhong") is None                  # 单字
    assert clean("一二三四五六七", "yi") is None          # 超过 6 字
    assert clean("中国", "zhong guo") != "zhong guo"


def test_merge_returns_base_source_and_sorts_by_frequency():
    merged = merge_module.merge([
        [("中国", "", 50)],
        [("中国", "zhongguo", 10)],
        [("中国", "zhongguo", 99)],
        [("北京", "beijing", 200)],
    ])

    assert merged == [("北京", "beijing", 200, "base"), ("中国", "zhongguo", 99, "base")]


def test_merge_extended_never_overrides_base_and_sorts_short_first():
    base = [("中国", "zhongguo", 99, "base")]
    ext = [
        ("中华人民共和国", "zhonghuarenmingongheguo", 1, "wiki"),
        ("初音未来", "chuyinweilai", 1, "moegirl"),
        ("中国", "zhongguo", 1, "wiki"),        # 与基础源重复，必须丢弃
    ]

    merged = merge_module.merge_extended(base, ext)

    assert merged[0] == ("中国", "zhongguo", 99, "base")
    # 词长过滤在 clean_extended 完成；merge_extended 只负责去重与稳定排序
    assert [item[0] for item in merged] == ["中国", "初音未来", "中华人民共和国"]
    assert merged[1][3] == "moegirl"


def test_write_full_drops_empty_pinyin_and_zero_frequency(tmp_path):
    merged = [
        ("中国", "zhongguo", 500, "base"),
        ("腾讯词", "", 100, "base"),
        ("零频词", "lingpin", 0, "base"),
        ("初音未来", "chuyinweilai", 1, "moegirl"),
    ]

    count = merge_module.write_full(merged, tmp_path)

    assert count == 2
    assert (tmp_path / 'msp_full.txt').read_text(encoding='utf-8') == (
        "中国\tzhongguo\t500\tbase\n"
        "初音未来\tchuyinweilai\t1\tmoegirl\n"
    )
