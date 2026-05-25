"""
测试 crawler/pipeline.py 模块

验证 Pipeline 的数据处理流程：去重、过滤、统计。
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawler.pipeline import Pipeline, load_existing_words, save_words


class TestPipeline:
    """词条处理管道测试"""

    def setup_method(self):
        self.pipeline = Pipeline()

    def test_process_basic(self):
        """基本处理流程"""
        sources = {
            'source1': ['人工智能', '机器学习', '深度学习'],
            'source2': ['人工智能', '北京', '上海'],  # 人工智能是重复
        }
        result = self.pipeline.process(sources, existing_words=set())
        stats = self.pipeline.get_stats()

        # input_total = 3(source1) + 3(source2) = 6
        assert stats['input_total'] == 6, f"期望 6，实际: {stats['input_total']}"
        # 去重后: 5 个词条, 均通过长度和字符过滤
        assert len(result) == 5, f"期望 5 个词条，实际: {len(result)}"
        # 注意：'deep learning' 包含英文，通过了 VALID_PATTERN 检查
        # "深度学习" 是纯中文，没问题

    def test_process_with_existing(self):
        """与已有词库去重"""
        sources = {
            'src1': ['人工智能', '机器学习', '新词条', '新词汇'],
        }
        existing = {'人工智能', '机器学习'}
        result = self.pipeline.process(sources, existing)
        stats = self.pipeline.get_stats()

        assert stats['input_total'] == 4
        assert stats['existing_filtered'] == 2
        assert stats['output_total'] == 2
        assert '新词条' in result
        assert '新词汇' in result

    def test_process_empty_sources(self):
        """空数据源处理"""
        sources = {}
        result = self.pipeline.process(sources)
        stats = self.pipeline.get_stats()
        assert stats['input_total'] == 0
        assert stats['output_total'] == 0
        assert result == []

    def test_process_duplicates(self):
        """同一数据源内重复词条"""
        sources = {
            'src1': ['人工智能', '人工智能', '人工智能', '机器学习'],
        }
        result = self.pipeline.process(sources)
        stats = self.pipeline.get_stats()

        # 去重: 4 -> 2
        assert stats['input_total'] == 4
        assert stats['duplicates_removed'] == 2
        assert stats['output_total'] == 2

    def test_filter_by_length(self):
        """按长度过滤"""
        words = ['a', 'ab', 'abc', 'abcd', '工具', '人工智能', '大语言模型' * 10]
        filtered = self.pipeline.filter_by_length(words, min_len=2, max_len=5)
        assert all(2 <= len(w) <= 5 for w in filtered)

    def test_filter_by_chinese_ratio(self):
        """按中文比例过滤"""
        words = ['人工智能', 'AI工具', 'OpenAI', 'test123', '全中文']
        # min_ratio=0.5: 至少一半是中文
        filtered = self.pipeline.filter_by_chinese_ratio(words, min_ratio=0.5)
        assert '人工智能' in filtered
        assert 'AI工具' in filtered  # 3中2 = 66% > 50%
        assert 'test123' not in filtered  # 0% 中文
        assert 'OpenAI' not in filtered  # 0% 中文

    def test_is_valid_word(self):
        """验证有效词条判断"""
        assert self.pipeline._is_valid_word('人工智能') is True
        assert self.pipeline._is_valid_word('AI工具') is True
        assert self.pipeline._is_valid_word('OpenAI') is True
        assert self.pipeline._is_valid_word('test123') is True
        assert self.pipeline._is_valid_word('Hello World') is False  # 含空格
        assert self.pipeline._is_valid_word('') is False  # 空字符串
        assert self.pipeline._is_valid_word('@@invalid') is False  # 特殊字符

    def test_process_no_existing_param(self):
        """不传 existing_words 时处理"""
        sources = {
            'test': ['词条1', '词条2', '词条3'],
        }
        result = self.pipeline.process(sources)
        assert len(result) == 3

    def test_get_stats_independence(self):
        """统计信息副本独立性"""
        sources = {'s': ['人工智能', '机器学习', '深度学习']}
        self.pipeline.process(sources)

        stats = self.pipeline.get_stats()
        original_output_total = stats['output_total']
        stats['output_total'] = 999

        # 原始对象不应被修改
        assert self.pipeline.stats['output_total'] == original_output_total, \
            f"期望 {original_output_total}，实际: {self.pipeline.stats['output_total']}"

    def test_print_stats(self):
        """打印统计信息（验证不崩溃）"""
        sources = {'s': ['测试', '词条']}
        self.pipeline.process(sources)

        # 验证 print_stats 不会抛出异常
        import io
        import sys as _sys
        captured = io.StringIO()
        old_stdout = _sys.stdout
        _sys.stdout = captured
        try:
            self.pipeline.print_stats()
        finally:
            _sys.stdout = old_stdout

        output = captured.getvalue()
        assert 'Input total' in output
        assert 'Output total' in output


class TestPipelineFunctions:
    """管道工具函数测试"""

    def setup_method(self):
        self.tmpfile = tempfile.mktemp(suffix='_pipeline_test.txt')

    def teardown_method(self):
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def test_save_and_load_words(self):
        """保存和加载词条"""
        words = ['人工智能', '机器学习', '深度学习']
        save_words(words, self.tmpfile)

        with open(self.tmpfile, 'r', encoding='utf-8') as f:
            content = f.read()
        assert '人工智能' in content
        assert '机器学习' in content

    def test_save_empty_words(self):
        """保存空词条列表"""
        save_words([], self.tmpfile)
        with open(self.tmpfile, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == ''

    def test_load_existing_words_invalid_file(self):
        """加载不存在的文件应返回空集合"""
        result = load_existing_words('/nonexistent/file.dat')
        assert result == set()
