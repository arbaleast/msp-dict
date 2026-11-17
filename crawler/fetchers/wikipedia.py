"""
维基百科抓取器

使用中文维基百科 API 抓取热门词条
"""

import json
import subprocess
from typing import List, Tuple


class WikipediaFetcher:
    """维基百科词条抓取器"""
    
    # 中文维基百科 API
    API_URL = "https://zh.wikipedia.org/w/api.php"
    
    # 搜索主题词（中文维基搜索用中文词）
    SEARCH_TOPICS = [
        # 科技/互联网
        "科技", "互联网", "计算机", "人工智能", "手机", "软件", "网络", "电子", "通信",
        "数据", "算法", "编程", "游戏", "视频", "社交", "电商", "金融科技",
        # 生活/日常
        "生活", "健康", "美食", "旅游", "购物", "交通", "房产", "家居", "美容", "服装",
        "运动", "健身", "音乐", "电影", "电视", "阅读", "摄影", "旅行", "宠物",
        # 知识/文化
        "教育", "科学", "历史", "地理", "政治", "经济", "法律", "哲学", "心理",
        "语言", "文学", "艺术", "设计", "建筑", "摄影", "书法", "绘画", "雕塑",
        # 社会/人物
        "社会", "城市", "国家", "企业", "品牌", "人物", "明星", "网红", "主播",
        "科学家", "企业家", "艺术家", "作家", "运动员", "演员", "歌手",
        # 时事/热点
        "事件", "新闻", "政策", "国际", "环境", "气候", "能源", "医疗", "疫苗",
        "疫苗", "疫情", "口罩", "经济", "股市", "汇率", "房产", "投资",
        # 自然/科学
        "动物", "植物", "天气", "天文", "地理", "海洋", "山脉", "河流", "森林",
        "物理", "化学", "生物", "数学", "医学", "工程", "技术", "材料",
        # 娱乐/休闲
        "动漫", "游戏", "综艺", "选秀", "演唱会", "剧场版", "电视剧", "纪录片",
        "足球", "篮球", "网球", "奥运会", "世界杯", "马拉松", "电竞",
        # 数码/汽车
        "电脑", "相机", "耳机", "手表", "汽车", "电动车", "新能源", "电池",
    ]
    
    def __init__(self, proxy: str = ""):
        self.proxy = proxy
        self.curl_cmd = ['curl', '-s', '--max-time', '20',
                         '-H', 'User-Agent: Mozilla/5.0 (compatible; msp-dict/1.0)']
        if proxy:
            self.curl_cmd.extend(['--proxy', proxy])
        
    # 最多补齐轮次：过滤掉无效标题后仍要凑够 limit
    MAX_FILL_ROUNDS = 3

    def fetch(self, limit: int = 50) -> List[str]:
        """
        抓取维基百科词条（通过搜索中文相关主题）

        配额分配：按主题数均分 limit，余数分配给靠前的主题；当 limit 小于
        主题数时，只取靠前的 limit 个主题、每个至少 1 条，避免出现
        「每个主题配额为 0 导致返回空列表」的情况。标题若被有效性规则
        过滤掉，会在后续轮次向同一主题追加请求补齐缺口。

        Args:
            limit: 抓取数量上限（<=0 返回空列表）

        Returns:
            词条标题列表（去重、保序，长度不超过 limit）
        """
        if limit <= 0:
            return []

        topics = self.SEARCH_TOPICS
        total_topics = len(topics)

        if limit < total_topics:
            # 主题比配额还多：只用靠前的 limit 个主题，每个至少 1 条
            selected = topics[:limit]
            base, remainder = 1, 0
        else:
            selected = topics
            base, remainder = divmod(limit, total_topics)

        collected: List[str] = []
        seen = set()
        # 每个主题已经请求到的条数（用于增量补齐）
        received = {topic: 0 for topic in selected}

        def absorb(titles: List[str]) -> int:
            """把有效且未出现过的标题并入结果集，返回新增条数。"""
            added = 0
            for title in titles:
                if len(collected) >= limit:
                    break
                if title in seen or not self._is_valid_title(title):
                    continue
                seen.add(title)
                collected.append(title)
                added += 1
            return added

        for round_index in range(self.MAX_FILL_ROUNDS):
            if len(collected) >= limit:
                break
            for index, topic in enumerate(selected):
                if len(collected) >= limit:
                    break
                quota = base + (1 if index < remainder else 0)
                if quota <= 0:
                    quota = 1
                titles = self._search_topic(topic, limit=received[topic] + quota)
                new_titles = titles[received[topic]:]
                received[topic] = len(titles)
                absorb(new_titles)

        return collected[:limit]

    def _search_topic(self, topic: str, limit: int = 10) -> List[str]:
        """
        搜索特定主题的词条
        
        Args:
            topic: 搜索主题
            limit: 数量
            
        Returns:
            词条标题列表
        """
        from urllib.parse import quote
        encoded_topic = quote(topic, safe='')
        url = f"{self.API_URL}?action=opensearch&search={encoded_topic}&limit={limit}&namespace=0&format=json"
        
        try:
            result = subprocess.run(
                self.curl_cmd + [url],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode != 0:
                return []
                
            return self._parse_opensearch(result.stdout)
            
        except Exception as e:
            print(f"[Wikipedia] Error searching {topic}: {e}")
            return []
            
    def _parse_opensearch(self, json_str: str) -> List[str]:
        """
        解析 opensearch API 响应
        
        Args:
            json_str: JSON 字符串
            
        Returns:
            词条标题列表
        """
        try:
            data = json.loads(json_str)
            if len(data) >= 2:
                return data[1]  # 第二个元素是标题列表
            return []
        except json.JSONDecodeError:
            return []
            
    def _is_valid_title(self, title: str) -> bool:
        """
        检查词条标题是否有效
        
        Args:
            title: 词条标题
            
        Returns:
            是否有效
        """
        # 跳过特殊页面
        skip_patterns = ['(', ')', ':', '[', ']', '{', '}']
        for pattern in skip_patterns:
            if pattern in title:
                return False
                
        # 长度限制
        if len(title) < 2 or len(title) > 25:
            return False
            
        # 跳过纯数字
        if title.replace(' ', '').replace('-', '').isdigit():
            return False
            
        return True


def main():
    """测试维基百科抓取器"""
    fetcher = WikipediaFetcher()
    
    print("Testing Wikipedia fetcher...")
    print("-" * 40)
    
    titles = fetcher.fetch(limit=30)
    print(f"\nTotal valid titles: {len(titles)}")
    print("\nFirst 20 titles:")
    for t in titles[:20]:
        print(f"  - {t}")


if __name__ == '__main__':
    main()
