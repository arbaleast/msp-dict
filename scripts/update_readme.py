#!/usr/bin/env python3
"""
自动更新 README.md 统计信息

在 CI 构建完成后运行，解析生成的 DAT 文件并更新 README 中的词条数和文件大小。
"""

import os
import re
import sys
from pathlib import Path

# 添加项目根目录到 path，以便导入 src.parser
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.parser import MSPinyinParser
except ImportError:
    MSPinyinParser = None


def format_size(size_bytes: int) -> str:
    """将字节数转换为人类可读的大小格式"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"~{size_bytes / (1024 * 1024):.0f} MB"


def get_dat_stats(filepath: str) -> dict:
    """获取 DAT 文件的统计信息"""
    if not os.path.exists(filepath):
        return {"exists": False, "count": None, "size": None, "size_str": "-"}

    size = os.path.getsize(filepath)
    size_str = format_size(size)

    count = None
    if MSPinyinParser:
        try:
            parser = MSPinyinParser()
            parser.load(filepath)
            count = parser.get_entry_count()
        except Exception as e:
            print(f"  Warning: Failed to parse {filepath}: {e}")

    return {
        "exists": True,
        "count": count,
        "size": size,
        "size_str": size_str,
    }


def update_readme(readme_path: str, stats: dict) -> bool:
    """更新 README.md 中的统计信息"""
    if not os.path.exists(readme_path):
        print(f"ERROR: README.md not found at {readme_path}")
        return False

    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 1. 更新 hero 区域的词条数（从完整版获取）
    if stats.get("full", {}).get("count"):
        full_count = stats["full"]["count"]
        # 替换 200万+ 为实际数字
        content = re.sub(
            r'🎯 微软拼音增强词库[^>]*>[^>]*>[^>]*—\d+万\+',
            f'🎯 微软拼音增强词库\n\n> 让你的输入法更懂你——{full_count // 10000}万+ 词条，半月自动更新，开箱即用',
            content
        )

    # 2. 更新词条数 badge
    if stats.get("full", {}).get("count"):
        full_count = stats["full"]["count"]
        content = re.sub(
            r'\[\!\[词条数\]\([^)]+\)\]\([^)]+\)',
            f'[![词条数](https://img.shields.io/badge/词条-{full_count // 10000}万+-blue)](https://github.com/arbaleast/msp-dict/releases)',
            content
        )

    # 3. 更新推荐版词条数（约27万 -> 实际数字）
    if stats.get("freq100", {}).get("count"):
        freq100_count = stats["freq100"]["count"]
        content = re.sub(
            r'\|\s*\[?\*?msp_win10\.dat\*?\]?[^|]*⭐[^|]*\|\s*~?\d+万',
            f'| [**msp_win10.dat**](https://github.com/arbaleast/msp-dict/releases/latest) ⭐ | {freq100_count:,}',
            content
        )

    # 4. 更新推荐版文件大小
    if stats.get("freq100", {}).get("size_str"):
        size_str = stats["freq100"]["size_str"]
        # 匹配 "Win10 DAT 推荐下载" 那行的末尾大小
        content = re.sub(
            r'(\| \[\*\*?msp_win10\.dat\*\*?\]?[^|]*⭐[^|]*\| [^|]*\| [^|]*\| )~\d+ MB',
            f'\\g<1>' + size_str,
            content
        )

    # 5. 更新完整版词条数
    if stats.get("full", {}).get("count"):
        full_count = stats["full"]["count"]
        full_size = stats.get("full", {}).get("size_str", "-")
        content = re.sub(
            r'\|\s*\[?msp_full\.dat\]?[^|]*\| 完整版[^|]*\| [^|]*\|',
            f'| [msp_full.dat](https://github.com/arbaleast/msp-dict/releases/latest) | {full_count:,} 词条 | 完整版（最全） | {full_size} |',
            content
        )

    # 6. 更新最后构建日期
    from datetime import date
    today = date.today().isoformat()
    content = re.sub(
        r'<!--\s*BUILD_DATE:\s*\d{4}-\d{2}-\d{2}\s*-->',
        f'<!-- BUILD_DATE: {today} -->',
        content
    )

    if content != original:
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    """主函数"""
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    readme_path = project_root / "README.md"

    print("=== README 统计更新工具 ===\n")

    # 需要统计的文件
    files = {
        "full": "msp_full.dat",
        "freq10": "msp_freq10.dat",
        "freq50": "msp_freq50.dat",
        "freq100": "msp_freq100.dat",
        "freq500": "msp_freq500.dat",
    }

    stats = {}
    print("📊 解析 DAT 文件统计:")
    for key, filename in files.items():
        filepath = project_root / filename
        stat = get_dat_stats(str(filepath))
        stats[key] = stat
        if stat["exists"]:
            count_str = f"{stat['count']:,}" if stat['count'] else "N/A"
            print(f"  {filename}: {count_str} 词条, {stat['size_str']}")
        else:
            print(f"  {filename}: 不存在")

    print()

    # 更新 README
    if update_readme(str(readme_path), stats):
        print("✅ README.md 已更新")
    else:
        print("ℹ️  README.md 无需更新")

    print()


if __name__ == "__main__":
    main()
