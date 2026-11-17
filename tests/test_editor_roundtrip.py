"""编辑器往返测试：同音候选顺序不能因重建而改变（候选位 ≠ 词频）。"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.builder_win10 import Win10MSPinyinBuilder
from src.editor import MSPinyinEditor
from src.parser import MSPinyinParser
from tests.dat_helpers import iter_records


def make_source(path):
    builder = Win10MSPinyinBuilder(timestamp=1600000000)
    builder.add_word("啊", "a", 300)
    builder.add_word("阿", "a", 200)
    builder.add_word("吖", "a", 100)
    builder.add_word("中国", "zhongguo", 50)
    path.write_bytes(builder.build())
    return path


def parse(path):
    parser = MSPinyinParser()
    parser.load(str(path))
    return [(e.text, e.pinyin, e.rank) for e in parser.entries]


def test_editor_save_preserves_same_pinyin_order(tmp_path):
    source = make_source(tmp_path / "source.dat")
    assert parse(source) == [("啊", "a", 1), ("阿", "a", 2), ("吖", "a", 3),
                             ("中国", "zhongguo", 1)]

    editor = MSPinyinEditor()
    editor.load(str(source))
    output = tmp_path / "saved.dat"
    editor.save(str(output))

    assert parse(output) == [("啊", "a", 1), ("阿", "a", 2), ("吖", "a", 3),
                             ("中国", "zhongguo", 1)]


def test_editor_appends_new_word_after_existing_candidates(tmp_path):
    source = make_source(tmp_path / "source.dat")
    editor = MSPinyinEditor()
    editor.load(str(source))

    assert editor.add_entry("嗄", "a", 1) is True
    output = tmp_path / "saved.dat"
    editor.save(str(output))

    entries = parse(output)
    assert [(text, pos) for text, code, pos in entries if code == "a"] == [
        ("啊", 1), ("阿", 2), ("吖", 3), ("嗄", 4),
    ]


def test_editor_renumbers_gaps_and_invalid_positions(tmp_path):
    # 模拟旧版产物：候选位乱序/重复/越界
    path = tmp_path / "legacy.dat"
    raw = bytearray(make_source(tmp_path / "ok.dat").read_bytes())
    records = iter_records(bytes(raw))
    phrase_start = int.from_bytes(raw[20:24], 'little')
    # 第一条（啊）改写为 9，第二条（阿）改写为 0
    raw[phrase_start + 6] = 9
    second = phrase_start + records[1]['size']
    raw[second + 6] = 0
    path.write_bytes(bytes(raw))

    editor = MSPinyinEditor()
    editor.load(str(path))
    output = tmp_path / "fixed.dat"
    editor.save(str(output))

    assert [(text, pos) for text, code, pos in parse(output) if code == "a"] == [
        ("阿", 1), ("吖", 2), ("啊", 3),
    ]
