"""
知乎热榜抓取器

从知乎热榜/热搜提取关键词
"""

import json
import re
import subprocess
from typing import List, Set


class ZhihuFetcher:
    """知乎热榜关键词抓取器"""

    # 知乎热榜 API
    API_HOT_LIST = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"

    # 知乎热搜 API
    API_HOT_SEARCH = "https://api.zhihu.com/topstory/hot-lists/total"

    def __init__(self, proxy: str = ""):
        """
        初始化知乎抓取器

        Args:
            proxy: 代理地址（可选）
        """
        self.proxy = proxy
        self.curl_cmd = ['curl', '-s']
        if proxy:
            self.curl_cmd.extend(['--proxy', proxy])
        self.headers = [
            '--header', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--header', 'Accept: application/json',
            '--header', 'Referer: https://www.zhihu.com/',
        ]

    def fetch(self, limit: int = 50) -> List[str]:
        """
        抓取知乎热榜标题中的关键词

        Args:
            limit: 抓取数量

        Returns:
            关键词列表
        """
        try:
            url = f"{self.API_HOT_LIST}?limit={limit}"
            result = subprocess.run(
                self.curl_cmd + self.headers + [url],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                print(f"[Zhihu] curl failed: {result.stderr}")
                return []

            return self._extract_keywords(result.stdout)

        except Exception as e:
            print(f"[Zhihu] Error: {e}")
            return []

    def fetch_search_hot(self) -> List[str]:
        """
        抓取知乎搜索热词

        Returns:
            热词列表
        """
        try:
            result = subprocess.run(
                self.curl_cmd + self.headers + [self.API_HOT_SEARCH],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return []

            return self._extract_search_keywords(result.stdout)

        except Exception as e:
            print(f"[Zhihu] Search Hot Error: {e}")
            return []

    def _extract_keywords(self, json_str: str) -> List[str]:
        """
        从热榜 JSON 响应中提取关键词

        Args:
            json_str: API 返回的 JSON 字符串

        Returns:
            关键词列表
        """
        try:
            data = json.loads(json_str)
            data_list = data.get('data', [])

            keywords = []
            for item in data_list:
                # 获取标题
                title = item.get('title', '')
                if not title:
                    continue

                # 从标题提取关键词
                extracted = self._extract_keywords_from_title(title)
                keywords.extend(extracted)

            # 去重
            return list(set(keywords))

        except json.JSONDecodeError as e:
            print(f"[Zhihu] JSON parse error: {e}")
            return []

    def _extract_search_keywords(self, json_str: str) -> List[str]:
        """
        从热搜 JSON 响应中提取关键词

        Args:
            json_str: API 返回的 JSON 字符串

        Returns:
            关键词列表
        """
        try:
            data = json.loads(json_str)
            data_list = data.get('data', [])

            keywords = []
            for item in data_list:
                # 热搜词直接使用
                query = item.get('query', '')
                if query and self._is_valid_keyword(query):
                    keywords.append(query)

            return list(set(keywords))

        except json.JSONDecodeError:
            return []

    def _extract_keywords_from_title(self, title: str) -> List[str]:
        """
        从标题中提取关键词

        处理策略：
        1. 移除疑问前缀（如何看待、如何评价等）
        2. 按标点/空格分割
        3. 短段（2-5字）直接验证
        4. 长段按中英文交界拆分
        5. 停止词过滤

        Args:
            title: 问题标题

        Returns:
            关键词列表
        """
        keywords = []

        # 1. 移除疑问前缀
        cleaned = self._remove_question_prefix(title)
        if not cleaned:
            return []

        # 2. 按标点和空格分割
        segments = re.split(r'[,，、。\s]+', cleaned)

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            # 移除首尾标点
            segment = segment.strip('，。！？、""''（）()【】[]')

            if not segment:
                continue

            # 3. 短段直接验证（2-15字）
            if 2 <= len(segment) <= 15:
                if self._is_valid_keyword(segment):
                    keywords.append(segment)
                continue

            # 4. 长段按中英文交界拆分
            if len(segment) > 15:
                sub_segments = self._split_by_boundary(segment)
                for sub in sub_segments:
                    if self._is_valid_keyword(sub):
                        keywords.append(sub)

        return keywords

    def _remove_question_prefix(self, text: str) -> str:
        """
        移除疑问前缀

        Args:
            text: 原始文本

        Returns:
            处理后的文本
        """
        # 常见疑问前缀模式
        prefixes = [
            r'^如何看待',
            r'^如何评价',
            r'^为什么',
            r'^有哪些',
            r'^怎么',
            r'^怎样',
            r'^如何',
            r'^是否',
            r'^有没有',
            r'^是不是',
            r'^该不该',
            r'^能不能',
            r'^是不是',
            r'^有什么',
            r'^为什么',
            r'^如何看',
            r'^你见过',
            r'^你觉得',
            r'^你知道',
        ]

        for prefix in prefixes:
            text = re.sub(prefix, '', text)

        return text.strip()

    def _split_by_boundary(self, text: str) -> List[str]:
        """
        按中英文交界拆分文本

        Args:
            text: 长文本

        Returns:
            拆分后的片段
        """
        # 在中英文交界处添加分隔符
        # 英文->中文 或 中文->英文
        split_text = re.sub(r'([a-zA-Z])([\u4e00-\u9fff])', r'\1 \2', text)
        split_text = re.sub(r'([\u4e00-\u9fff])([a-zA-Z])', r'\1 \2', text)

        # 按空格分割
        segments = split_text.split()

        result = []
        for seg in segments:
            seg = seg.strip()
            # 只保留中文字符为主的片段
            chinese_chars = sum(1 for c in seg if '\u4e00' <= c <= '\u9fff')
            if chinese_chars >= len(seg) * 0.5:
                result.append(seg)

        return result

    def _is_valid_keyword(self, keyword: str) -> bool:
        """
        检查关键词是否有效

        Args:
            keyword: 关键词

        Returns:
            是否有效
        """
        # 长度限制：2-15 字
        if len(keyword) < 2 or len(keyword) > 15:
            return False

        # 必须有中文字符
        chinese_chars = sum(1 for c in keyword if '\u4e00' <= c <= '\u9fff')
        if chinese_chars == 0:
            return False

        # 过滤纯英文/数字
        if re.match(r'^[a-zA-Z0-9\s]+$', keyword):
            return False

        # 停止词过滤
        stop_words = {
            '的', '了', '是', '在', '有', '和', '与', '或', '但', '而',
            '一个', '一些', '什么', '这个', '那个', '这些', '那些',
            '我', '你', '他', '她', '它', '我们', '你们', '他们',
            '可以', '应该', '能够', '会', '能', '要', '想', '让',
            '被', '把', '给', '对', '从', '到', '向', '往',
            '很', '太', '更', '最', '非常', '特别', '比较',
            '也', '都', '还', '又', '再', '已', '已经', '曾', '曾经',
            '不', '没', '无', '非', '别', '请', '吗', '呢', '吧', '啊',
        }
        if keyword in stop_words:
            return False

        # 不能是纯标点
        if re.match(r'^[\s，。！？、""''（）()【】\[\]]+$', keyword):
            return False

        return True


def main():
    """测试知乎抓取器"""
    fetcher = ZhihuFetcher()

    print("Testing Zhihu fetcher...")
    print("-" * 40)

    # 测试热榜关键词
    print("\n[Fetcher] Fetching hot list keywords...")
    keywords = fetcher.fetch(limit=50)
    print(f"Got {len(keywords)} keywords from hot list")

    # 测试热搜词
    print("\n[Fetcher] Fetching search hot...")
    search_hot = fetcher.fetch_search_hot()
    print(f"Got {len(search_hot)} keywords from search hot")

    # 合并去重
    all_keywords = list(set(keywords + search_hot))
    print(f"\nTotal unique keywords: {len(all_keywords)}")
    print("\nFirst 30 keywords:")
    for kw in all_keywords[:30]:
        print(f"  - {kw}")

    # 测试关键词提取
    print("\n" + "-" * 40)
    print("Keyword extraction examples:")
    test_titles = [
        "如何看待 ChatGPT 的发展？",
        "有哪些值得一看的电影？",
        "为什么年轻人不愿意生孩子了？",
        "如何评价《三体》电视剧？",
        "Python 和 JavaScript 哪个更适合入门？",
    ]
    for title in test_titles:
        keywords = fetcher._extract_keywords_from_title(title)
        print(f"  '{title}' -> {keywords}")


if __name__ == '__main__':
    main()
