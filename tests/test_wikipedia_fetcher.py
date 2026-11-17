"""Wikipedia 抓取器的数量上限回归测试。

Phase 0 审计确认：原实现用 ``limit // len(SEARCH_TOPICS)``（127 个主题）
分配单主题配额，导致 limit < 127 时每主题配额为 0，fetch() 恒返回空列表。
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crawler.fetchers.wikipedia import WikipediaFetcher  # noqa: E402


@pytest.fixture
def fake_fetcher(monkeypatch):
    """用可控的假数据替代真实网络请求。"""
    fetcher = WikipediaFetcher()

    def fake_search(topic: str, limit: int):
        # 每个主题产出 limit 条唯一标题（带主题前缀便于去重检查）
        return [f'{topic}词条{i}' for i in range(limit)]

    monkeypatch.setattr(fetcher, '_search_topic', fake_search)
    return fetcher


class TestLimitAllocation:
    def test_zero_limit_returns_empty(self, fake_fetcher):
        assert fake_fetcher.fetch(0) == []

    def test_negative_limit_returns_empty(self, fake_fetcher):
        assert fake_fetcher.fetch(-5) == []

    @pytest.mark.parametrize('limit', [1, 5, 20, 50, 100, 127, 200])
    def test_returns_at_least_one_when_limit_small(self, fake_fetcher, limit):
        """小 limit 也不能返回空（旧实现 limit<127 恒空）。"""
        result = fake_fetcher.fetch(limit)
        assert len(result) == limit, f'limit={limit} 实际返回 {len(result)}'

    def test_never_exceeds_limit(self, fake_fetcher):
        for limit in (1, 10, 50, 127, 300):
            assert len(fake_fetcher.fetch(limit)) <= limit

    def test_results_are_deduplicated(self, fake_fetcher):
        result = fake_fetcher.fetch(200)
        assert len(result) == len(set(result))

    def test_order_is_stable(self, fake_fetcher):
        """去重必须保序，不能像 list(set(...)) 那样随机。"""
        first = fake_fetcher.fetch(50)
        second = fake_fetcher.fetch(50)
        assert first == second

    def test_per_topic_quota_is_never_zero(self, fake_fetcher, monkeypatch):
        """旧实现 limit // 127 == 0 是空结果的根因，必须被杜绝。"""
        quotas = []

        def spy(topic: str, limit: int):
            quotas.append(limit)
            return [f'{topic}词条{i}' for i in range(limit)]

        monkeypatch.setattr(fake_fetcher, '_search_topic', spy)
        fake_fetcher.fetch(10)

        assert quotas, '必须发起请求'
        assert all(q > 0 for q in quotas), f'存在零配额: {quotas}'
        assert sum(quotas) <= 10 + len(quotas), '配额总量不应远超 limit'
