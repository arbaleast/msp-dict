"""三档词库发布策略。

三档按**覆盖规模**划分，而不是按 Windows 设置页的加载表现划分：

  lite     核心主力档  ≤ 200,000 条，剔除单字/长句，扩展源 ≤15%
  standard 全能进阶档  ≤ 800,000 条，含单字，扩展源 ≤35%
  full     全量档       不截断（220 万条以上），仅供存档或转其他输入法

每档只做「格式合法性清洗 + 去重」，选词策略由这里集中定义，CLI 与 CI 共用。
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class Profile:
    name: str
    label: str
    limit: Optional[int]          # 最多选取的词条数；None = 不限制
    exclude_single: bool          # 是否剔除单字词（微软拼音自带单字）
    max_word_units: int           # 词条最大 UTF-16 单元数（用于剔除长句）
    min_freq: int                 # 最低词频（来源词频，仅用于筛选）
    extended_ratio: Optional[float] = None   # 扩展源（萌娘/维基/SCEL）最多占比
    extended_max_word_units: int = 6         # 扩展源词条最大字数
    extended_min_word_units: int = 2         # 扩展源词条最小字数

    def describe(self) -> str:
        limit = f"≤{self.limit:,} 条" if self.limit else "全量"
        return f"{self.label}（{limit}，{'剔除单字' if self.exclude_single else '含单字'}，词条≤{self.max_word_units} 字）"


PROFILES: Dict[str, Profile] = {
    'lite': Profile(
        name='lite',
        label='核心主力档',
        limit=200000,
        exclude_single=True,
        max_word_units=8,
        min_freq=0,
        extended_ratio=0.15,          # 扩展源 ≤15%（约 30,000 条），其余留给 Frost/Ice
        extended_max_word_units=5,
    ),
    'standard': Profile(
        name='standard',
        label='全能进阶档',
        limit=800000,
        exclude_single=False,
        max_word_units=16,
        min_freq=0,
        extended_ratio=0.35,          # 扩展源 ≤35%（约 280,000 条）
        extended_max_word_units=5,
    ),
    'full': Profile(
        name='full',
        label='全量档',
        limit=None,
        exclude_single=False,
        max_word_units=64,
        min_freq=0,
    ),
}

DEFAULT_PROFILE = 'lite'


def get_profile(name: str) -> Profile:
    try:
        return PROFILES[name]
    except KeyError:
        raise ValueError(
            f"未知的 profile: {name!r}，可选: {', '.join(PROFILES)}"
        ) from None
