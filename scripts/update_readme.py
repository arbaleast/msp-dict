#!/usr/bin/env python3
"""
自动更新 README.md 的构建统计（CI 在 build_releases.py 之后运行）。

数据来源:
  1. build_summary.json（首选，由 scripts/build_releases.py 生成）
  2. 退回直接解析 msp_*.dat

更新内容:
  * <!-- STATS:START --> ... <!-- STATS:END --> 之间的三档下载表
  * hero 文案与徽章里的「万条」数字
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

SCENES = {
    'msp_lite.dat': 'Windows 10/11 直接导入（推荐）',
    'msp_standard.dat': '进阶用户；管理页会明显卡顿',
    'msp_full.dat': '存档 / 转 Rime 等，Windows 无法完整导入',
    'msp_win10.dat': '兼容旧链接（= msp_lite.dat）',
}


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"~{size_bytes / (1024 * 1024):.0f} MB"


def load_stats(root: Path) -> dict:
    """返回 {文件名: {'count': int, 'size': int}}。"""
    summary_path = root / 'build_summary.json'
    stats = {}
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        for item in summary.get('profiles', []):
            stats[item['file']] = {'count': item['entries'], 'size': item['size_bytes']}
        if 'msp_lite.dat' in stats:
            stats['msp_win10.dat'] = dict(stats['msp_lite.dat'])
        return stats

    for filename in ['msp_lite.dat', 'msp_standard.dat', 'msp_full.dat', 'msp_win10.dat']:
        path = root / filename
        if not path.exists():
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
        content = re.sub(
            r'> 让你的输入法更懂你——[^\n]*',
            f'> 让你的输入法更懂你——{wan}万+ 条有效词条，三档可选，半月自动更新',
            content,
        )
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
