"""
词条处理管道

去重、过滤、合并来自多个数据源的词条
"""

import re
from typing import List, Set, Dict
from pathlib import Path


class Pipeline:
    """词条处理管道"""

    # 中文字符 Unicode 范围 (CJK Unified Ideographs: U+4E00–U+9FFF)
    CHINESE_PATTERN = re.compile(r'^[\u4e00-\u9fff]+$')

    # 允许的字符模式（中文为主，可含少量英文/数字）
    VALID_PATTERN = re.compile(r'^[\u4e00-\u9fffa-zA-Z0-9._-]+$')

    # 默认过滤常量
    DEFAULT_MIN_LEN = 2        # 词条最小长度（短于 2 个字无意义）
    DEFAULT_MAX_LEN = 20       # 词条最大长度（过长词汇不适合输入法词库）
    DEFAULT_MIN_CHINESE_RATIO = 0.3  # 混合词条的最小中文字符比例

    def __init__(self):
        self.stats = {
            'input_total': 0,
            'chinese_filtered': 0,
            'length_filtered': 0,
            'duplicates_removed': 0,
            'existing_filtered': 0,
            'output_total': 0
        }

    def process(self, sources: Dict[str, List[str]], existing_words: Set[str] = None) -> List[str]:
        """
        处理多数据源的词条

        Args:
            sources: 数据源字典，{数据源名: [词条列表]}
            existing_words: 已有词条集合（用于去重）

        Returns:
            处理后的词条列表
        """
        existing_words = existing_words or set()

        all_words = []
        self.stats['input_total'] = sum(len(words) for words in sources.values())

        # 1. 合并所有数据源
        for source_name, words in sources.items():
            all_words.extend(words)

        # 2. 去重
        all_words = list(set(all_words))
        self.stats['duplicates_removed'] = self.stats['input_total'] - len(all_words)

        # 3. 过滤有效词条
        valid_words = []
        for word in all_words:
            word = word.strip()

            # 长度过滤
            if len(word) < self.DEFAULT_MIN_LEN or len(word) > self.DEFAULT_MAX_LEN:
                self.stats['length_filtered'] += 1
                continue

            # 字符过滤：必须有中文字符或英文项目名
            if not self._is_valid_word(word):
                self.stats['chinese_filtered'] += 1
                continue

            valid_words.append(word)

        # 4. 与已有词库去重
        final_words = []
        for word in valid_words:
            if word not in existing_words:
                final_words.append(word)
            else:
                self.stats['existing_filtered'] += 1

        self.stats['output_total'] = len(final_words)

        return final_words

    def _is_valid_word(self, word: str) -> bool:
        """
        检查词条是否有效

        Args:
            word: 词条

        Returns:
            是否有效
        """
        # 必须是有效字符组成
        if not self.VALID_PATTERN.match(word):
            return False

        # 至少包含中文字符或纯英文（项目名）
        has_chinese = bool(self.CHINESE_PATTERN.match(word))
        has_english = bool(re.match(r'^[a-zA-Z0-9._-]+$', word))

        # 纯中文或英文项目名都可以
        if has_chinese or has_english:
            return True

        # 混合型：必须有中文
        chinese_chars = sum(1 for c in word if '\u4e00' <= c <= '\u9fff')
        return chinese_chars >= 1

    def filter_by_length(self, words: List[str], min_len: int = None, max_len: int = None) -> List[str]:
        """
        按长度过滤词条

        Args:
            words: 词条列表
            min_len: 最小长度，默认使用 DEFAULT_MIN_LEN
            max_len: 最大长度，默认使用 DEFAULT_MAX_LEN

        Returns:
            过滤后的词条列表
        """
        min_len = min_len if min_len is not None else self.DEFAULT_MIN_LEN
        max_len = max_len if max_len is not None else self.DEFAULT_MAX_LEN
        return [w for w in words if min_len <= len(w) <= max_len]

    def filter_by_chinese_ratio(self, words: List[str], min_ratio: float = None) -> List[str]:
        """
        按中文比例过滤词条

        Args:
            words: 词条列表
            min_ratio: 最小中文字符比例，默认使用 DEFAULT_MIN_CHINESE_RATIO

        Returns:
            过滤后的词条列表
        """
        min_ratio = min_ratio if min_ratio is not None else self.DEFAULT_MIN_CHINESE_RATIO
        result = []
        for word in words:
            chinese_chars = sum(1 for c in word if '\u4e00' <= c <= '\u9fff')
            ratio = chinese_chars / len(word) if len(word) > 0 else 0
            if ratio >= min_ratio:
                result.append(word)
        return result

    def get_stats(self) -> Dict[str, int]:
        """
        获取处理统计

        Returns:
            统计信息字典
        """
        return self.stats.copy()

    def print_stats(self) -> None:
        """打印处理统计"""
        print("\n[Pipeline] Processing Statistics:")
        print(f"  Input total:        {self.stats['input_total']}")
        print(f"  Duplicates removed: {self.stats['duplicates_removed']}")
        print(f"  Length filtered:    {self.stats['length_filtered']}")
        print(f"  Chinese filtered:   {self.stats['chinese_filtered']}")
        print(f"  Existing filtered:  {self.stats['existing_filtered']}")
        print(f"  Output total:       {self.stats['output_total']}")


def load_existing_words(filepath: str) -> Set[str]:
    """
    从已有词库加载词条集合

    Args:
        filepath: 词库文件路径

    Returns:
        词条集合
    """
    # 注意: 必须使用完整的 src.parser 导入路径
    # 此文件在 crawler/ 目录下运行, 直接 from parser 会导致 ModuleNotFoundError
    from src.parser import MSPinyinParser

    try:
        parser = MSPinyinParser()
        parser.load(filepath)
        return {entry.text for entry in parser.entries}
    except Exception as e:
        print(f"[Pipeline] Warning: Failed to load existing words: {e}")
        return set()


def save_words(words: List[str], filepath: str) -> None:
    """
    保存词条到文件

    Args:
        words: 词条列表
        filepath: 输出文件路径
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        for word in words:
            f.write(f"{word}\n")


def main():
    """测试管道"""
    from crawler.fetchers import (
        GitHubFetcher, WikipediaFetcher, BilibiliFetcher,
        MoegirlFetcher, WikidataFetcher,
    )

    print("Testing Pipeline...")
    print("-" * 40)

    # 模拟数据源（覆盖所有抓取器）
    sources = {
        'github': ['llama.cpp', 'Qwen', 'LangChain', 'vue', 'react', '测试词条', '123'],
        'wikipedia': ['人工智能', '机器学习', '深度学习', 'Python', 'data123'],
        'bilibili': ['原神', 'B站', '弹幕', 'test123'],
        'moegirl': ['初音未来', '原神角色', '鬼灭之刃', '进击的巨人'],
        'wikidata': ['北京', '爱因斯坦', '莎士比亚', '月球', 'test'],
    }

    pipeline = Pipeline()

    # 模拟已有词库
    existing = {'人工智能', 'vue', 'react', '北京', '机器学习'}

    result = pipeline.process(sources, existing)

    pipeline.print_stats()

    print(f"\nFinal words ({len(result)}):")
    for w in result:
        print(f"  - {w}")


if __name__ == '__main__':
    main()
