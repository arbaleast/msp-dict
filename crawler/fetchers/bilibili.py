"""
B站热词抓取器

抓取B站热门内容的高频词汇
"""

import re
import json
import subprocess
from typing import List, Optional


class BilibiliFetcher:
    """B站热词抓取器"""
    
    # B站搜索热词 API
    API_URL = "https://api.bilibili.com/x/v2/search/hot"
    
    def __init__(self, proxy: str = ""):
        self.proxy = proxy
        self.curl_cmd = ['curl', '-s', '--max-time', '20']
        if proxy:
            self.curl_cmd.extend(['--proxy', proxy])
        self.headers = [
            '--header', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--header', 'Referer: https://www.bilibili.com/'
        ]
        
    def fetch(self, limit: int = 50) -> List[str]:
        """
        抓取B站搜索热词
        
        Args:
            limit: 抓取数量
            
        Returns:
            热词列表
        """
        try:
            result = subprocess.run(
                self.curl_cmd + self.headers + [self.API_URL],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"[Bilibili] curl failed: {result.stderr}")
                return []
                
            return self._extract_keywords(result.stdout)
            
        except Exception as e:
            print(f"[Bilibili] Error: {e}")
            return []
            
    def _extract_keywords(self, json_str: str) -> List[str]:
        """
        从 JSON 响应中提取热词
        
        Args:
            json_str: API 返回的 JSON 字符串
            
        Returns:
            热词列表
        """
        try:
            data = json.loads(json_str)
            # B站 API 结构
            content_list = data.get('data', {}).get('list', [])
            
            keywords = []
            for item in content_list:
                keyword = item.get('keyword', '')
                if keyword and self._is_valid_keyword(keyword):
                    keywords.append(keyword)
                    
            return keywords
            
        except json.JSONDecodeError as e:
            print(f"[Bilibili] JSON parse error: {e}")
            return []
            
    def _is_valid_keyword(self, keyword: str) -> bool:
        """
        检查热词是否有效
        
        Args:
            keyword: 热词
            
        Returns:
            是否有效
        """
        # 长度限制
        if len(keyword) < 2 or len(keyword) > 15:
            return False
            
        # 过滤纯英文/数字
        if re.match(r'^[a-zA-Z0-9]+$', keyword):
            return False
            
        return True
        
    def fetch_trending(self) -> List[str]:
        """
        抓取B站排行榜热词
        
        Returns:
            热词列表
        """
        # 尝试 B站 热搜 API
        trending_url = "https://api.bilibili.com/x/web-interface/ranking/v2"
        
        try:
            result = subprocess.run(
                self.curl_cmd + self.headers + [trending_url],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return []
                
            return self._extract_from_ranking(result.stdout)
            
        except Exception as e:
            print(f"[Bilibili] Trending Error: {e}")
            return []
            
    def _extract_from_ranking(self, json_str: str) -> List[str]:
        """
        从排行榜响应中提取关键词
        
        Args:
            json_str: API 返回的 JSON 字符串
            
        Returns:
            热词列表
        """
        try:
            data = json.loads(json_str)
            video_list = data.get('data', {}).get('list', [])
            
            keywords = []
            for video in video_list:
                # 提取标题中的高频词
                title = video.get('title', '')
                tname = video.get('tname', '')  # 分类名
                
                if title:
                    # 简单分词：按标点和空格分割
                    words = re.split(r'[\s,，、.]+', title)
                    for word in words:
                        word = word.strip()
                        if self._is_valid_keyword(word):
                            keywords.append(word)
                            
                if tname and self._is_valid_keyword(tname):
                    keywords.append(tname)
                    
            return list(set(keywords))
            
        except json.JSONDecodeError:
            return []


def main():
    """测试B站抓取器"""
    fetcher = BilibiliFetcher()
    
    print("Testing Bilibili fetcher...")
    print("-" * 40)
    
    # 测试搜索热词
    print("\n[Fetcher] Fetching search hot keywords...")
    keywords = fetcher.fetch(limit=50)
    print(f"Got {len(keywords)} keywords from search hot")
    
    # 测试排行榜
    print("\n[Fetcher] Fetching trending videos...")
    trending = fetcher.fetch_trending()
    print(f"Got {len(trending)} keywords from trending")
    
    # 合并去重
    all_keywords = list(set(keywords + trending))
    print(f"\nTotal unique keywords: {len(all_keywords)}")
    print("\nFirst 30 keywords:")
    for kw in all_keywords[:30]:
        print(f"  - {kw}")


if __name__ == '__main__':
    main()
