"""
GitHub 抓取器

使用 GitHub API 获取热门项目
"""

import json
import subprocess
from typing import List, Optional


class GitHubFetcher:
    """GitHub 高星项目名抓取器"""
    
    # GitHub Search API
    SEARCH_API = "https://api.github.com/search/repositories"
    
    def __init__(self, proxy: str = "http://localhost:7893"):
        self.proxy = proxy
        self.curl_cmd = ['curl', '-s', '--proxy', proxy]
        
    def fetch(self, limit: int = 50) -> List[str]:
        """
        抓取 GitHub 高星项目名
        
        Args:
            limit: 抓取数量
            
        Returns:
            项目名列表
        """
        # 按 stars 排序，获取最近更新的热门项目
        query = "stars:>10000+pushed:>2025-01-01"
        url = f"{self.SEARCH_API}?q={query}&sort=stars&order=desc&per_page={min(limit, 100)}"
        
        try:
            result = subprocess.run(
                self.curl_cmd + [url],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"[GitHub] curl failed: {result.stderr}")
                return []
                
            return self._extract_names(result.stdout)
            
        except Exception as e:
            print(f"[GitHub] Error: {e}")
            return []
            
    def fetch_by_language(self, language: str, limit: int = 30) -> List[str]:
        """
        按语言抓取项目
        
        Args:
            language: 编程语言 (python/go/javascript/typescript/java/rust)
            limit: 抓取数量
            
        Returns:
            项目名列表
        """
        query = f"language:{language}+stars:>5000+pushed:>2025-01-01"
        url = f"{self.SEARCH_API}?q={query}&sort=stars&order=desc&per_page={min(limit, 100)}"
        
        try:
            result = subprocess.run(
                self.curl_cmd + [url],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"[GitHub] curl failed: {result.stderr}")
                return []
                
            return self._extract_names(result.stdout)
            
        except Exception as e:
            print(f"[GitHub] Error: {e}")
            return []
            
    def fetch_all_languages(self) -> List[str]:
        """
        抓取多种语言的项目名
        
        Returns:
            所有项目名列表
        """
        languages = ['Python', 'Go', 'JavaScript', 'TypeScript', 'Java', 'Rust']
        all_projects = []
        
        for lang in languages:
            print(f"[GitHub] Fetching {lang}...")
            projects = self.fetch_by_language(lang, limit=30)
            all_projects.extend(projects)
            print(f"[GitHub] Got {len(projects)} projects from {lang}")
            
        return list(set(all_projects))
        
    def _extract_names(self, json_str: str) -> List[str]:
        """
        从 JSON 响应中提取项目名
        
        Args:
            json_str: API 返回的 JSON 字符串
            
        Returns:
            项目名列表
        """
        try:
            data = json.loads(json_str)
            items = data.get('items', [])
            
            names = []
            for item in items:
                name = item.get('name', '')
                if name and self._is_valid_name(name):
                    names.append(name)
                    
            return names
            
        except json.JSONDecodeError as e:
            print(f"[GitHub] JSON parse error: {e}")
            return []
            
    def _is_valid_name(self, name: str) -> bool:
        """
        检查项目名是否有效
        
        Args:
            name: 项目名
            
        Returns:
            是否有效
        """
        if len(name) < 2 or len(name) > 50:
            return False
        # 允许字母、数字、点、减号、下划线
        return name.replace('.', '').replace('-', '').replace('_', '').isalnum()


def main():
    """测试 GitHub 抓取器"""
    fetcher = GitHubFetcher()
    
    print("Testing GitHub fetcher...")
    print("-" * 40)
    
    # 测试通用抓取
    projects = fetcher.fetch(limit=20)
    print(f"\nGeneral: {len(projects)} projects")
    for p in projects[:10]:
        print(f"  - {p}")
    
    print()
    
    # 测试按语言抓取
    all_projects = fetcher.fetch_all_languages()
    print(f"\nTotal unique projects: {len(all_projects)}")


if __name__ == '__main__':
    main()
