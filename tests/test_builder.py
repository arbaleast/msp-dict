"""
测试 src/builder_win10.py 模块

验证 Win10MSPinyinBuilder 的构建功能。
"""
import os
import sys
import tempfile
import struct

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.builder_win10 import Win10MSPinyinBuilder
from src.parser import MSPinyinParser


class TestWin10Builder:
    """Win10 构建器测试"""

    def setup_method(self):
        self.tmpfile = tempfile.mktemp(suffix='_builder_test.dat')

    def teardown_method(self):
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def test_build_empty(self):
        """构建空词库"""
        builder = Win10MSPinyinBuilder()
        data = builder.build()
        assert len(data) > 0
        assert data[0:8] == b'mschxudp'

    def test_build_and_verify_header(self):
        """构建并验证文件头"""
        builder = Win10MSPinyinBuilder(timestamp=1234567890)
        builder.add_word("中国", "zhongguo", 1)
        data = builder.build()

        # 验证协议标识
        assert data[0:8] == b'mschxudp'

        # 验证标志字段
        flag = struct.unpack('<I', data[8:12])[0]
        assert flag == 0x00600002

        # 验证版本号
        version = struct.unpack('<I', data[12:16])[0]
        assert version == 1

        # 验证词条数
        count = struct.unpack('<I', data[28:32])[0]
        assert count == 1

        # 验证时间戳
        ts = struct.unpack('<Q', data[32:40])[0]
        assert ts == 1234567890

    def test_build_multiple_words(self):
        """构建多个词条"""
        builder = Win10MSPinyinBuilder()
        words = [
            ("中国", "zhongguo", 1),
            ("北京", "beijing", 2),
            ("上海", "shanghai", 3),
            ("测试", "ceshi", 4),
        ]
        for word, py, rank in words:
            builder.add_word(word, py, rank)

        data = builder.build()
        count = struct.unpack('<I', data[28:32])[0]
        assert count == 4

        # 解析验证
        builder.save(self.tmpfile)
        parser = MSPinyinParser()
        parser.load(self.tmpfile)
        assert parser.get_entry_count() == 4

    def test_build_with_custom_timestamp(self):
        """带自定义时间戳构建"""
        builder = Win10MSPinyinBuilder(timestamp=9999999999)
        builder.add_word("测试", "ceshi", 1)
        data = builder.build()

        ts = struct.unpack('<Q', data[32:40])[0]
        assert ts == 9999999999

    def test_save_and_load_consistency(self):
        """保存和加载的一致性"""
        builder = Win10MSPinyinBuilder()
        builder.add_word("人工智能", "rengongzhineng", 5)
        builder.add_word("机器学习", "jiqixuexi", 3)
        builder.save(self.tmpfile)

        # 读取验证
        with open(self.tmpfile, 'rb') as f:
            data = f.read()

        # 重新构建应产生相同大小
        builder2 = Win10MSPinyinBuilder()
        builder2.add_word("人工智能", "rengongzhineng", 5)
        builder2.add_word("机器学习", "jiqixuexi", 3)
        data2 = builder2.build()

        assert len(data) == len(data2)
