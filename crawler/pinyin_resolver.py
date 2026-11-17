"""采集词条的拼音补全。

爬虫抓到的只是纯词条（没有拼音），而 mschxudp 记录**必须**带合法拼音，
否则构建器会直接丢弃。本模块负责在采集结果进入 DAT 之前补全拼音：

1. 若安装了可选依赖 ``pypinyin``，用它逐字转拼音；
2. 若没有安装、或转换失败，词条会被列入 unresolved，交由调用方单独输出，
   **绝不会**用空串或占位符（如 ``xx``）伪造拼音。

安装可选依赖::

    pip install "msp-dict[crawler]"
"""

from typing import Dict, Iterable, List, Tuple

# 与 src.format_spec 一致的拼音约束：小写 a-z + 内部音节分隔符 '
try:
    from src.format_spec import is_valid_pinyin, normalize_pinyin
except ImportError:  # pragma: no cover - 仅在脱离仓库根目录运行时
    def is_valid_pinyin(pinyin: str) -> bool:
        if not pinyin or len(pinyin) > 64:
            return False
        if pinyin[0] == pinyin[-1] == "'" or "''" in pinyin:
            return False
        return all(c.isascii() and c.isalpha() for c in pinyin if c != "'")

    def normalize_pinyin(pinyin: str) -> str:
        return (pinyin or '').replace(' ', '').lower()


def pypinyin_available() -> bool:
    """当前环境是否可用 pypinyin。"""
    try:
        import pypinyin  # noqa: F401
    except ImportError:
        return False
    return True


def resolve_pinyin(words: Iterable[str]) -> Tuple[Dict[str, str], List[str]]:
    """为词条补全拼音。

    Args:
        words: 纯词条列表

    Returns:
        ``({词条: 拼音}, 无法解析的词条列表)``。
        没有装 pypinyin 时，第一项为空、第二项是全部词条。
    """
    word_list = [w for w in words if w]
    if not word_list:
        return {}, []

    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        return {}, list(word_list)

    resolved: Dict[str, str] = {}
    unresolved: List[str] = []
    for word in word_list:
        try:
            syllables = lazy_pinyin(word, errors='ignore')
        except Exception:  # pragma: no cover - pypinyin 内部异常
            unresolved.append(word)
            continue
        pinyin = normalize_pinyin(''.join(syllables))
        if not pinyin or not is_valid_pinyin(pinyin):
            unresolved.append(word)
            continue
        resolved[word] = pinyin

    return resolved, unresolved
