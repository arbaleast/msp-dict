"""三档词库发布策略（Issue #3）。

微软拼音的「用户自定义短语」在导入时由 Windows 一次性构建 UI 列表：
词条越多，设置页越卡；超过约 2 万条即无法完整导入。因此不再发布单一
"越大越全" 的 msp_win10.dat，而是按用途分三档：

  lite     精简版（默认推荐 Windows）  ≤ 20,000 条，剔除单字/长句
  standard 标准版（进阶用户）          ≤ 50,000 条
  full     完整版（存档 / 转其他输入法）全量，不保证 Windows 可导入

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
    windows_importable: bool      # 是否声明可直接导入 Windows
    extended_ratio: Optional[float] = None   # 扩展源（萌娘/维基/SCEL）最多占比
    extended_max_word_units: int = 6         # 扩展源词条最大字数
    extended_min_word_units: int = 2         # 扩展源词条最小字数

    def describe(self) -> str:
        limit = f"≤{self.limit:,} 条" if self.limit else "全量"
        return f"{self.label}（{limit}，{'剔除单字' if self.exclude_single else '含单字'}，词条≤{self.max_word_units} 字）"


PROFILES: Dict[str, Profile] = {
    'lite': Profile(
        name='lite',
        label='精简版',
        limit=20000,
        exclude_single=True,
        max_word_units=8,
        min_freq=0,
        windows_importable=True,
        extended_ratio=0.12,          # Lite：扩展源 ≤12%（约 2,400 条），其余留给 Frost/Ice
        extended_max_word_units=5,
    ),
    'standard': Profile(
        name='standard',
        label='标准版',
        limit=50000,
        exclude_single=False,
        max_word_units=16,
        min_freq=0,
        windows_importable=False,
        extended_ratio=0.22,          # Standard：扩展源 ≤22%（约 11,000 条）
        extended_max_word_units=5,
    ),
    'full': Profile(
        name='full',
        label='完整版',
        limit=None,
        exclude_single=False,
        max_word_units=64,
        min_freq=0,
        windows_importable=False,
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
