"""
数据源抓取器

SogouFetcher 需要 python-dotenv（读取 SOGOU_COOKIE），属于可选依赖组 `crawler`。
为避免基础环境缺少该依赖时整个 crawler CLI 无法启动，这里改用惰性导入：
只有真正访问 SogouFetcher 时才会 import .sogou。
"""

from typing import TYPE_CHECKING

from .github import GitHubFetcher
from .wikipedia import WikipediaFetcher
from .bilibili import BilibiliFetcher
from .moegirl import MoegirlFetcher
from .wikidata import WikidataFetcher
from .zhihu import ZhihuFetcher

if TYPE_CHECKING:  # pragma: no cover - 仅供类型检查
    from .sogou import SogouFetcher

__all__ = [
    'GitHubFetcher', 'WikipediaFetcher', 'BilibiliFetcher',
    'MoegirlFetcher', 'WikidataFetcher', 'ZhihuFetcher', 'SogouFetcher',
]


def __getattr__(name):
    """惰性导入 SogouFetcher（依赖可选的 python-dotenv）。"""
    if name == 'SogouFetcher':
        try:
            from .sogou import SogouFetcher as _SogouFetcher
        except ImportError as exc:  # 明确报错，而不是静默失败
            raise ImportError(
                'SogouFetcher 需要可选依赖 python-dotenv，请先安装: '
                'pip install "msp-dict[crawler]"'
            ) from exc
        globals()['SogouFetcher'] = _SogouFetcher
        return _SogouFetcher
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
