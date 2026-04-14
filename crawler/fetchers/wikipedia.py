"""
维基百科抓取器

使用英文维基百科 API（中文维基 API 暂时不可用）
"""

import json
import subprocess
from typing import List


class WikipediaFetcher:
    """维基百科词条抓取器"""
    
    # 英文维基百科 API
    API_URL = "https://en.wikipedia.org/w/api.php"
    
    # 中文相关搜索词（用于获取中文相关词条）
    CHINA_TOPICS = [
        "China", "Chinese", "Beijing", "Shanghai", "Hong Kong",
        "Taiwan", "Mandarin", "Peking", "Qing", "Ming",
        "Confucius", "Taoism", "Buddhism", "Chinese_cuisine",
        "Chinese_history", "Chinese_culture", "Chinese_language"
    ]
    
    def __init__(self, proxy: str = "http://localhost:7893"):
        self.proxy = proxy
        self.curl_cmd = ['curl', '-s', '--proxy', proxy, '-H', 'User-Agent: Mozilla/5.0']
        
    def fetch(self, limit: int = 50) -> List[str]:
        """
        抓取维基百科词条（通过搜索中文相关主题）
        
        Args:
            limit: 抓取数量
            
        Returns:
            词条标题列表
        """
        all_titles = []
        
        for topic in self.CHINA_TOPICS:
            titles = self._search_topic(topic, limit=limit // len(self.CHINA_TOPICS))
            all_titles.extend(titles)
            
        # 去重
        unique_titles = list(set(all_titles))
        
        # 过滤
        valid_titles = [t for t in unique_titles if self._is_valid_title(t)]
        
        return valid_titles[:limit]
        
    def _search_topic(self, topic: str, limit: int = 10) -> List[str]:
        """
        搜索特定主题的词条
        
        Args:
            topic: 搜索主题
            limit: 数量
            
        Returns:
            词条标题列表
        """
        url = f"{self.API_URL}?action=opensearch&search={topic}&limit={limit}&namespace=0&format=json"
        
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
