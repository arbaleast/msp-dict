"""README 统计更新脚本与新版文档的契约测试。

CI 每次构建后都会运行 scripts/update_readme.py 刷新下载表、hero 文案与构建日期；
这里守住「能更新」与「幂等」两条，避免 README 改版后正则静默失配。
"""

import importlib.util
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    'update_readme_script', ROOT / 'scripts' / 'update_readme.py')
update_readme = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(update_readme)

STATS = {
    'msp_lite.dat': {'count': 19_992, 'size': 890_290},
    'msp_standard.dat': {'count': 49_202, 'size': 2_235_096},
    'msp_full.dat': {'count': 1_015_471, 'size': 54_992_528},
    'msp_win10.dat': {'count': 19_992, 'size': 890_290},
}


def test_render_stats_block_is_fixed_table():
    block = update_readme.render_stats_block(STATS)

    assert '| 文件 | 词条数 | 大小 | 适用场景 |' in block
    assert '| **msp_lite.dat** | 19,992 | 869 KB | 日常高频主力档，日常使用首选 |' in block
    assert '| msp_standard.dat | 49,202 | ~2 MB | 专业与百科扩充档，覆盖面更广 |' in block
    assert '| msp_full.dat | 1,015,471 | ~52 MB | 全量归档档，用于存档 / 转其他输入法 |' in block
    assert '| msp_win10.dat | 19,992 | 869 KB | 兼容副本（= msp_lite.dat） |' in block
    assert block.startswith(update_readme.STATS_START)
    assert block.endswith(update_readme.STATS_END)


def test_update_readme_rewrites_stats_and_is_idempotent(tmp_path):
    readme = tmp_path / 'README.md'
    shutil.copyfile(ROOT / 'README.md', readme)

    changed = {
        'msp_lite.dat': {'count': 12_345, 'size': 512_000},
        'msp_standard.dat': {'count': 45_678, 'size': 3_000_000},
        'msp_full.dat': {'count': 999_999, 'size': 40_000_000},
        'msp_win10.dat': {'count': 12_345, 'size': 512_000},
    }
    assert update_readme.update_readme(readme, changed) is True
    first = readme.read_text(encoding='utf-8')

    assert '| **msp_lite.dat** | 12,345 | 500 KB | 日常高频主力档，日常使用首选 |' in first
    assert '| msp_standard.dat | 45,678 | ~3 MB |' in first
    assert '| msp_full.dat | 999,999 | ~38 MB |' in first
    assert first.count(update_readme.STATS_START) == 1
    assert '<strong>99万+</strong> 条有效词条' in first   # 居中头部宣传语随全量词条数变化
    assert '词条-99万+-blue' in first            # 顶部徽章同步
    assert '<!-- BUILD_DATE:' in first

    # 同一份数据再跑一次不应再产生改动（CI 每次构建都会刷新，必须幂等）
    assert update_readme.update_readme(readme, changed) is False
    assert readme.read_text(encoding='utf-8') == first


def test_tagline_block_is_rewritten_not_duplicated(tmp_path):
    """宣传语区块必须被整体替换，而不是追加出第二份。"""
    readme = tmp_path / 'README.md'
    shutil.copyfile(ROOT / 'README.md', readme)

    changed = dict(STATS)
    changed['msp_full.dat'] = {'count': 2_000_000, 'size': 40_000_000}
    assert update_readme.update_readme(readme, changed) is True
    text = readme.read_text(encoding='utf-8')

    assert text.count(update_readme.TAGLINE_START) == 1
    assert text.count(update_readme.TAGLINE_END) == 1
    assert '<strong>200万+</strong>' in text
