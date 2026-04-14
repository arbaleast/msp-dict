"""
数据源抓取器
"""

from .github import GitHubFetcher
from .wikipedia import WikipediaFetcher
from .bilibili import BilibiliFetcher

__all__ = ['GitHubFetcher', 'WikipediaFetcher', 'BilibiliFetcher']
