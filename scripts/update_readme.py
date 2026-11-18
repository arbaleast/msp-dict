#!/usr/bin/env python3
"""
自动更新 README.md 的构建统计（CI 在 build_releases.py 之后运行）。

数据来源:
  1. build_summary.json（首选；仓库根缺失时回退 .tmp/dist/build_summary.json）
  2. 退回直接解析 msp_*.dat（仓库根优先，其次 .tmp/dist/）

更新内容:
  * <!-- STATS:START --> ... <!-- STATS:END --> 之间的四档下载表
  * <!-- TAGLINE:START --> ... <!-- TAGLINE:END --> 之间的宣传语词条数
  * 顶部徽章里的「万条」数字
  * <!-- BUILD_DATE: YYYY-MM-DD -->
"""

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    from src.parser import MSPinyinParser
except ImportError:  # pragma: no cover
    MSPinyinParser = None

STATS_START = '<!-- STATS:START -->'
STATS_END = '<!-- STATS:END -->'
TAGLINE_START = '<!-- TAGLINE:START -->'
TAGLINE_END = '<!-- TAGLINE:END -->'

SCENES = {
    'msp_lite.dat': '日常高频主力档，日常使用首选',
    'msp_standard.dat': '专业与百科扩充档，覆盖面更广',
    'msp_full.dat': '全量归档档，用于存档 / 转其他输入法',
    'msp_win10.dat': '兼容副本（= msp_lite.dat）',
}


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"~{size_bytes / (1024 * 1024):.0f} MB"


def load_stats(root: Path) -> dict:
    """返回 {文件名: {'count': int, 'size': int}}。

    优先读仓库根的 build_summary.json；本地默认构建写的是
    .tmp/dist/build_summary.json，因此按顺序回退。
    """
    summary_path = None
    for candidate in (root / 'build_summary.json',
                      root / '.tmp' / 'dist' / 'build_summary.json'):
        if candidate.exists():
            summary_path = candidate
            break

    stats = {}
    if summary_path is not None:
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        for item in summary.get('profiles', []):
            stats[item['file']] = {'count': item['entries'], 'size': item['size_bytes']}
        if 'msp_lite.dat' in stats:
            stats['msp_win10.dat'] = dict(stats['msp_lite.dat'])
        return stats

    search_dirs = [root, root / '.tmp' / 'dist']
    for filename in ['msp_lite.dat', 'msp_standard.dat', 'msp_full.dat', 'msp_win10.dat']:
        path = next((d / filename for d in search_dirs if (d / filename).exists()), None)
        if path is None:
            continue
        count = None
        if MSPinyinParser:
            try:
                parser = MSPinyinParser()
                parser.load(str(path))
                count = parser.get_entry_count()
            except Exception as exc:
                print(f"  Warning: 无法解析 {filename}: {exc}")
        stats[filename] = {'count': count, 'size': os.path.getsize(path)}
    return stats


def render_stats_block(stats: dict) -> str:
    lines = [
        STATS_START,
        '| 文件 | 词条数 | 大小 | 适用场景 |',
        '|:---|---:|---:|:---|',
    ]
    for filename in ['msp_lite.dat', 'msp_standard.dat', 'msp_full.dat', 'msp_win10.dat']:
        item = stats.get(filename)
        if not item:
            continue
        count = f"{item['count']:,}" if item.get('count') is not None else 'N/A'
        size = format_size(item['size'])
        name = f'**{filename}**' if filename == 'msp_lite.dat' else filename
        lines.append(f'| {name} | {count} | {size} | {SCENES[filename]} |')
    lines.append(STATS_END)
    return '\n'.join(lines)


def render_tagline_block(wan: int) -> str:
    """生成居中头部的宣传语区块。"""
    return '\n'.join([
        TAGLINE_START,
        f'<p><strong>{wan}万+</strong> 条有效词条 · 三档可选 · 每月自动更新</p>',
        TAGLINE_END,
    ])


def update_readme(readme_path: Path, stats: dict) -> bool:
    if not readme_path.exists():
        print(f'ERROR: README.md 不存在: {readme_path}')
        return False

    content = readme_path.read_text(encoding='utf-8')
    original = content

    if STATS_START in content and STATS_END in content:
        start = content.index(STATS_START)
        end = content.index(STATS_END) + len(STATS_END)
        content = content[:start] + render_stats_block(stats) + content[end:]

    full_count = stats.get('msp_full.dat', {}).get('count')
    if full_count:
        wan = full_count // 10000
        if TAGLINE_START in content and TAGLINE_END in content:
            start = content.index(TAGLINE_START)
            end = content.index(TAGLINE_END) + len(TAGLINE_END)
            content = content[:start] + render_tagline_block(wan) + content[end:]
        content = re.sub(
            r'\[!\[词条数\]\([^)]*\)\]\([^)]*\)',
            f'[![词条数](https://img.shields.io/badge/词条-{wan}万+-blue)]'
            f'(https://github.com/arbaleast/msp-dict/releases)',
            content,
        )

    content = re.sub(
        r'<!--\s*BUILD_DATE:\s*\d{4}-\d{2}-\d{2}\s*-->',
        f'<!-- BUILD_DATE: {date.today().isoformat()} -->',
        content,
    )

    if content != original:
        readme_path.write_text(content, encoding='utf-8')
        return True
    return False


def main() -> int:
    print('=== README 统计更新工具 ===\n')
    stats = load_stats(ROOT)
    if not stats:
        print('未找到任何 msp_*.dat 或 build_summary.json，跳过')
        return 1
    for filename, item in stats.items():
        count = f"{item['count']:,}" if item.get('count') is not None else 'N/A'
        print(f"  {filename}: {count} 条, {format_size(item['size'])}")

    updated = update_readme(ROOT / 'README.md', stats)
    print('\n✅ README.md 已更新' if updated else '\nℹ️  README.md 无需更新')
    return 0


if __name__ == '__main__':
    sys.exit(main())
