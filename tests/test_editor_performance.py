"""编辑器批量导入复杂度测试（Phase 5）。

旧实现 add_entry 每条都要线性扫描「待添加列表」，批量导入是 O(N²)；
哈希索引后单条 O(1)，20 万条约数秒内完成。这里用真实文件走 BatchImporter，
同时校验索引与底层词条列表一致。
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.builder_win10 import Win10MSPinyinBuilder
from src.editor import MSPinyinEditor
from src.importer import BatchImporter
from src.parser import MSPinyinParser

BULK_SIZE = 200_000


def b26(n: int) -> str:
    """双射 26 进制，生成唯一合法拼音：a, b, ..., z, aa, ab, ..."""
    letters = []
    n += 1
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters.append(chr(ord('a') + rem))
    return ''.join(reversed(letters))


def make_editor(tmp_path):
    base = tmp_path / "base.dat"
    builder = Win10MSPinyinBuilder(timestamp=1600000000)
    builder.add_word("测试", "ceshi", 1)
    builder.save(str(base))

    editor = MSPinyinEditor()
    editor.load(str(base))
    return editor, base


def write_bulk(path, size):
    with open(path, 'w', encoding='utf-8') as f:
        for i in range(size):
            f.write(f"词{i}\t{b26(i)}\n")


def test_bulk_import_200k_is_sub_ten_seconds(tmp_path):
    editor, _ = make_editor(tmp_path)
    source = tmp_path / "bulk.txt"
    write_bulk(source, BULK_SIZE)

    importer = BatchImporter(editor)
    started = time.perf_counter()
    imported, skipped, errors = importer.import_txt(str(source))
    elapsed = time.perf_counter() - started

    assert imported == BULK_SIZE
    assert skipped == 0
    assert errors == 0
    assert editor.get_stats()['pending_add'] == BULK_SIZE
    assert elapsed < 10.0, f"20 万条导入耗时 {elapsed:.2f}s，超出 10s 预算"

    # 索引一致性：首、中、末条都能 O(1) 命中
    for text in ("词0", "词100000", f"词{BULK_SIZE - 1}"):
        assert editor.find_by_text(text) is not None


def test_save_and_reload_bulk_roundtrip(tmp_path):
    editor, _ = make_editor(tmp_path)
    source = tmp_path / "bulk.txt"
    write_bulk(source, 50_000)

    importer = BatchImporter(editor)
    imported, _, _ = importer.import_txt(str(source))
    assert imported == 50_000

    output = tmp_path / "bulk.dat"
    started = time.perf_counter()
    editor.save(str(output))
    elapsed = time.perf_counter() - started
    assert elapsed < 10.0, f"5 万条保存耗时 {elapsed:.2f}s，超出 10s 预算"

    parser = MSPinyinParser()
    # 基础词库原有 1 条「测试」+ 新导入 5 万条
    assert parser.load(str(output)) == 50_001
    assert parser.find_by_text("测试") is not None
    assert editor.get_stats()['pending_add'] == 0
    assert editor.get_stats()['pending_remove'] == 0
    assert editor.find_by_text("词49999") is not None
    assert editor.find_by_text("不存在的词条") is None


def test_index_tracks_add_remove_and_save(tmp_path):
    editor, _ = make_editor(tmp_path)

    assert editor.add_entry("新词", "xinci", 10) is True
    assert editor.add_entry("新词", "xinci", 20) is False  # 待添加重复
    assert editor.find_by_text("新词").rank == 10

    assert editor.remove_entry("测试") is True
    assert editor.remove_entry("测试") is False  # 已标记删除

    editor.save(str(tmp_path / "after.dat"))

    assert editor.find_by_text("新词") is not None
    assert editor.find_by_text("测试") is None
    assert editor.get_stats()['pending_add'] == 0
    assert editor.get_stats()['pending_remove'] == 0
