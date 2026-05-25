"""
数据源抓取器
"""

from .github import GitHubFetcher
from .wikipedia import WikipediaFetcher
from .bilibili import BilibiliFetcher
from .moegirl import MoegirlFetcher
from .wikidata import WikidataFetcher

__all__ = [
    'GitHubFetcher', 'WikipediaFetcher', 'BilibiliFetcher',
    'MoegirlFetcher', 'WikidataFetcher',
]
