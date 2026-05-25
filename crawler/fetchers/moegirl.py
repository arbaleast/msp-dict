"""
萌娘百科抓取器

抓取萌娘百科（https://zh.moegirl.org.cn）词条标题。
萌娘百科是二次元/ACG 领域的百科全书，包含大量动漫、游戏、虚拟主播等专有名词。

抓取策略：
  1. 通过 ACG 相关主题搜索词条（opensearch API）
  2. 通过随机页面 API 获取词条（兜底方案）
"""

import json
import time
import subprocess
from typing import List


class MoegirlFetcher:
    """萌娘百科词条抓取器"""

    # 萌娘百科 MediaWiki API
    API_URL = "https://zh.moegirl.org.cn/api.php"

    # ACG 相关搜索主题（覆盖动漫、游戏、虚拟主播、角色、声优等方向）
    ACG_TOPICS = [
        # 动漫作品
        "动漫", "动画", "新番", "番剧", "漫画",
        # 游戏
        "游戏", "手游", "角色扮演", "动作游戏", "冒险游戏",
        # 虚拟主播/VTuber
        "虚拟主播", "VTuber", "VUP", "虚拟偶像",
        # 角色与声优
        "角色", "声优", "配音演员", "主角", "女主角",
        # ACG 文化
        "萌", "二次元", "同人", "轻小说", "galgame",
        # 著名系列
        "原神", "崩坏", "明日方舟", "碧蓝航线", "Fate",
        "东方Project", "VOCALOID", "初音未来", "LoveLive",
        # 动画工作室/导演
        "京都动画", "吉卜力", "新海诚", "宮崎駿",
    ]

    def __init__(self, proxy: str = ""):
        """
        Args:
            proxy: 代理地址（留空则不使用代理，萌娘百科在中国可直接访问）
        """
        self.proxy = proxy
        if proxy:
            self.curl_cmd = ['curl', '-s', '--proxy', proxy,
                             '-H', 'User-Agent: Mozilla/5.0']
        else:
            self.curl_cmd = ['curl', '-s',
                             '-H', 'User-Agent: Mozilla/5.0']
        # 请求间隔（秒），避免触发反爬
        self.request_delay = 1.0

    def fetch(self, limit: int = 50) -> List[str]:
        """
        抓取萌娘百科词条

        依次尝试：
          1. 通过 ACG 主题搜索词条（opensearch）
          2. 通过随机页面 API 获取词条（兜底）

        Args:
            limit: 抓取数量

        Returns:
            词条标题列表
        """
        all_titles = []

        # 方法1：通过 ACG 主题搜索
        per_topic = max(1, limit // len(self.ACG_TOPICS))
        for topic in self.ACG_TOPICS:
            titles = self._search_topic(topic, limit=per_topic)
            if titles:
                print(f"[Moegirl] Got {len(titles)} titles from topic '{topic}'")
            all_titles.extend(titles)
            time.sleep(self.request_delay)

            if len(all_titles) >= limit:
                break

        # 方法2：如果搜索到的数量不足，补充随机页面
        if len(all_titles) < limit:
            remaining = limit - len(all_titles)
            print(f"[Moegirl] Fetching {remaining} random pages as supplement...")
            random_titles = self._fetch_random_pages(remaining)
            all_titles.extend(random_titles)

        # 去重、过滤并截取
        seen = set()
        result = []
        for title in all_titles:
            title = title.strip()
            if title not in seen and self._is_valid_title(title):
                seen.add(title)
                result.append(title)
                if len(result) >= limit:
                    break

        print(f"[Moegirl] Total valid titles: {len(result)}")
        return result

    def _search_topic(self, topic: str, limit: int = 10) -> List[str]:
        """
        通过 opensearch API 搜索主题相关词条

        Args:
            topic: 搜索主题
            limit: 数量

        Returns:
            词条标题列表
        """
        # opensearch 返回格式：[searchTerm, [title1, title2, ...], [desc1, desc2, ...], [url1, url2, ...]]
        from urllib.parse import quote
        encoded_topic = quote(topic, safe='')
        url = (
            f"{self.API_URL}"
            f"?action=opensearch"
            f"&search={encoded_topic}"
            f"&limit={limit}"
            f"&namespace=0"
            f"&format=json"
        )

        try:
            result = subprocess.run(
                self.curl_cmd + [url],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=15
            )

            if result.returncode != 0:
                print(f"[Moegirl] curl failed for '{topic}': {result.stderr}")
                return []

            return self._parse_opensearch(result.stdout)

        except subprocess.TimeoutExpired:
            print(f"[Moegirl] Timeout searching '{topic}'")
            return []
        except Exception as e:
            print(f"[Moegirl] Error searching '{topic}': {e}")
            return []

    def _fetch_random_pages(self, limit: int = 10) -> List[str]:
        """
        通过随机页面 API 获取词条（兜底方案）

        使用 MediaWiki 的 random 列表接口：
        action=query&list=random&rnnamespace=0&rnlimit=max

        Args:
            limit: 数量

        Returns:
            词条标题列表
        """
        # API 单次最多返回 500 条
        rnlimit = min(limit, 500)
        url = (
            f"{self.API_URL}"
            f"?action=query"
            f"&list=random"
            f"&rnnamespace=0"
            f"&rnlimit={rnlimit}"
            f"&format=json"
        )

        try:
            result = subprocess.run(
                self.curl_cmd + [url],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=15
            )

            if result.returncode != 0:
                return []

            return self._parse_random_pages(result.stdout)

        except Exception as e:
            print(f"[Moegirl] Error fetching random pages: {e}")
            return []

    def _parse_opensearch(self, json_str: str) -> List[str]:
        """
        解析 opensearch API 响应

        opensearch 返回格式：[query, [titles...], [descriptions...], [urls...]]
        标题列表在索引 1 处。

        Args:
            json_str: JSON 字符串

        Returns:
            词条标题列表
        """
        try:
            data = json.loads(json_str)
            if isinstance(data, list) and len(data) >= 2:
                return data[1]  # 第二个元素是标题列表
            return []
        except json.JSONDecodeError as e:
            print(f"[Moegirl] JSON parse error: {e}")
            return []

    def _parse_random_pages(self, json_str: str) -> List[str]:
        """
        解析随机页面 API 响应

        Args:
            json_str: JSON 字符串

        Returns:
            词条标题列表
        """
        try:
            data = json.loads(json_str)
            pages = data.get('query', {}).get('random', [])
            return [page.get('title', '') for page in pages if page.get('title')]
        except json.JSONDecodeError as e:
            print(f"[Moegirl] JSON parse error: {e}")
            return []

    def _is_valid_title(self, title: str) -> bool:
        """
        检查词条标题是否有效

        Args:
            title: 词条标题

        Returns:
            是否有效
        """
        # 跳过特殊页面（包含特殊字符的标题）
        skip_patterns = ['(', ')', ':', '[', ']', '{', '}', '/', '\\', '<', '>']
        for pattern in skip_patterns:
            if pattern in title:
                return False

        # 跳过 MediaWiki 系统页面
        if title.startswith('MediaWiki:') or title.startswith('Special:'):
            return False

        # 长度限制
        if len(title) < 2 or len(title) > 25:
            return False

        # 跳过纯数字标题
        if title.replace(' ', '').replace('-', '').isdigit():
            return False

        # 必须至少包含一个中文字符
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in title)
        if not has_chinese:
            return False

        return True


def main():
    """测试萌娘百科抓取器"""
    # 萌娘百科在中国可直接访问，留空 proxy 即可
    fetcher = MoegirlFetcher()

    print("Testing Moegirl fetcher...")
    print("=" * 40)

    titles = fetcher.fetch(limit=50)
    print(f"\nTotal valid titles: {len(titles)}")
    print("\nFirst 30 titles:")
    for t in titles[:30]:
        print(f"  - {t}")


if __name__ == '__main__':
    main()
