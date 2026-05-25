"""
测试 src/editor.py 模块

验证 MSPinyinEditor 的额外功能。
基础编辑功能已在 src/test_win10_format.py 中覆盖。
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.editor import MSPinyinEditor
from src.parser import MSPinyinParser
from src.builder_win10 import Win10MSPinyinBuilder


class TestEditorExtended:
    """编辑器扩展测试"""

    def setup_method(self):
        self.tmpfile = tempfile.mktemp(suffix='_editor_test.dat')

    def teardown_method(self):
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def test_get_stats(self):
        """获取编辑统计信息"""
        builder = Win10MSPinyinBuilder()
        builder.add_word("测试", "ceshi", 1)
        builder.add_word("词库编辑", "cikubianji", 2)
        builder.add_word("人工智能", "rengongzhineng", 3)
        builder.save(self.tmpfile)

        editor = MSPinyinEditor()
        editor.load(self.tmpfile)
        stats = editor.get_stats()

        assert stats['total_entries'] == 3
        assert stats['pending_add'] == 0
        assert stats['pending_remove'] == 0
        assert stats['file_size'] > 0
        assert stats['avg_length'] > 0
        assert stats['max_length'] >= 2
        assert stats['single_char'] >= 0

    def test_get_stats_with_pending_changes(self):
        """含待处理变更的统计信息"""
        builder = Win10MSPinyinBuilder()
        builder.add_word("测试", "ceshi", 1)
        builder.add_word("保存", "baocun", 2)
        builder.save(self.tmpfile)

        editor = MSPinyinEditor()
        editor.load(self.tmpfile)

        # 添加待处理变更
        editor.add_entry("新词条", "xincitiao", 3)
        editor.remove_entry("测试")

        stats = editor.get_stats()
        assert stats['pending_add'] == 1
        assert stats['pending_remove'] == 1

    def test_save_and_reload(self):
        """保存并重新加载验证一致性"""
        builder = Win10MSPinyinBuilder()
        builder.add_word("初始词条", "chukicitiao", 1)
        builder.save(self.tmpfile)

        # 编辑
        editor = MSPinyinEditor()
        editor.load(self.tmpfile)
        editor.add_entry("新词条", "xincitiao", 2)
        editor.remove_entry("初始词条")
        editor.save()

        # 重新解析验证
        parser = MSPinyinParser()
        parser.load(self.tmpfile)
        assert parser.get_entry_count() == 1
        assert parser.entries[0].text == "新词条"

    def test_save_to_new_path(self):
        """保存到新路径"""
        builder = Win10MSPinyinBuilder()
        builder.add_word("测试", "ceshi", 1)
        builder.save(self.tmpfile)

        editor = MSPinyinEditor()
        editor.load(self.tmpfile)
        editor.add_entry("新词条", "xincitiao", 2)

        new_path = self.tmpfile + '_new.dat'
        editor.save(new_path)

        # 验证新文件
        parser = MSPinyinParser()
        parser.load(new_path)
        assert parser.get_entry_count() == 2

        # 原始文件未修改
        parser2 = MSPinyinParser()
        parser2.load(self.tmpfile)
        assert parser2.get_entry_count() == 1

        if os.path.exists(new_path):
            os.remove(new_path)

    def test_editor_without_load(self):
        """未加载文件时操作应返回 False"""
        editor = MSPinyinEditor()
        assert editor.add_entry("测试", "ceshi", 1) is False
        assert editor.remove_entry("测试") is False

    def test_save_without_filepath(self):
        """未指定保存路径应抛出异常"""
        editor = MSPinyinEditor()
        try:
            editor.save()
            assert False, "应抛出 ValueError"
        except ValueError:
            pass

    def test_add_duplicate_in_pending(self):
        """待添加列表中重复应失败"""
        builder = Win10MSPinyinBuilder()
        builder.save(self.tmpfile)

        editor = MSPinyinEditor()
        editor.load(self.tmpfile)

        assert editor.add_entry("词条A", "citiáoA", 1) is True
        assert editor.add_entry("词条A", "citiáoA", 2) is False  # 重复
