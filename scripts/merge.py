#!/usr/bin/env python3
"""
合并 rime-ice / rime-frost 词库，输出按词频降序的全量文本 msp_full.txt。

规则:
  * 同一词条保留最高词频；已有拼音优先于空拼音
  * 只有词频、没有拼音的行（rime-ice tencent 等）无法写入 mschxudp，
    合并阶段直接剔除并统计，避免下游生成 0 长度拼音的坏记录
  * 输出 `词条\\t拼音\\t词频`，按词频降序（三档构建按此顺序取前 N 条）

用法:
    python scripts/merge.py                       # 读 cache/，写 msp_full.txt + CHANGELOG.md
    python scripts/merge.py --emit-freq-tiers     # 额外输出旧的 msp_freq*.txt（仅调试用）
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

FILES = [
    'rime-ice_base.txt', 'rime-ice_ext.txt', 'rime-ice_tencent.txt',
    'rime-ice_8105.txt', 'rime-ice_others.txt',
    'rime-frost_base.txt', 'rime-frost_ext.txt',
    # rime-frost tencent 跳过（29MB > 25MB GitHub 限制，且 rime-ice tencent 已覆盖）
    'rime-frost_8105.txt', 'rime-frost_others.txt',
    # 搜狗细胞词库（21 个）
    'rime-frost_food.txt', 'rime-frost_idiom.txt', 'rime-frost_history.txt',
    'rime-frost_medication.txt', 'rime-frost_computer.txt',
    'rime-frost_sport.txt', 'rime-frost_geography.txt',
    'rime-frost_exthot.txt', 'rime-frost_game.txt', 'rime-frost_music.txt',
    'rime-frost_media.txt', 'rime-frost_animal.txt', 'rime-frost_chess.txt',
    'rime-frost_chess2.txt', 'rime-frost_composite.txt',
    'rime-frost_industry_product.txt', 'rime-frost_inputmethod.txt',
    'rime-frost_literature.txt', 'rime-frost_name.txt', 'rime-frost_name2.txt',
    'rime-frost_place.txt', 'rime-frost_shulihua.txt',
    # 朙月拼音
    'rime-frost_luna_pinyin.txt',
]


def parse_rime(content: str):
    """解析 Rime 文本，返回 [(词, 拼音, 词频), ...]。

    支持:
        词\\t拼音\\t词频     （标准）
        词\\t拼音            （无词频）
        词\\t词频            （纯词频表，拼音留空）
    """
    entries = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('#') or line.startswith('---') \
                or line.startswith('name:') or line.startswith('version:') \
                or line.startswith('sort:'):
            continue
        parts = line.split('\t')
        if len(parts) >= 3:
            word = parts[0].strip()
            pinyin = parts[1].strip()
            try:
                freq = int(parts[-1].strip())
            except ValueError:
                continue
            if word and freq >= 0:
                entries.append((word, pinyin, freq))
        elif len(parts) == 2:
            word = parts[0].strip()
            second = parts[1].strip()
            if second and not any(c.isdigit() for c in second):
                if word and ord(word[0]) >= 0x4E00:
                    entries.append((word, second, 1))
            else:
                try:
                    freq = int(second)
                except ValueError:
                    continue
                if word and freq >= 0:
                    entries.append((word, '', freq))
    return entries


def merge(entries_list):
    """合并去重，返回 {词: (拼音, 最高词频)}，按词频降序。"""
    word_data = {}
    for entries in entries_list:
        for word, pinyin, freq in entries:
            if word in word_data:
                old_pinyin, old_freq = word_data[word]
                word_data[word] = (old_pinyin if old_pinyin else pinyin,
                                   max(old_freq, freq))
            else:
                word_data[word] = (pinyin, freq)
    return sorted(word_data.items(), key=lambda x: x[1][1], reverse=True)


def write_full(merged, output_dir: Path) -> int:
    """写入有拼音且词频 >= 1 的词条（与旧版 CI 口径一致）。"""
    count = 0
    with open(output_dir / 'msp_full.txt', 'w', encoding='utf-8') as f:
        for word, (pinyin, freq) in merged:
            if not pinyin or freq < 1:
                continue
            f.write(f'{word}\t{pinyin}\t{freq}\n')
            count += 1
    return count


def write_freq_tiers(merged, output_dir: Path) -> None:
    for min_freq, suffix in [(10, 'freq10'), (50, 'freq50'),
                             (100, 'freq100'), (500, 'freq500')]:
        out = output_dir / f'msp_{suffix}.txt'
        count = 0
        with open(out, 'w', encoding='utf-8') as f:
            for word, (pinyin, freq) in merged:
                if freq >= min_freq:
                    f.write(f'{word}\t{pinyin}\t{freq}\n')
                    count += 1
        print(f'已生成 {out.name}: {count:,} 条')


def write_changelog(merged, usable_count, no_pinyin_count, source_counts, output_dir: Path):
    freq100_count = sum(1 for _, (_, f) in merged if f >= 100)
    freq500_count = sum(1 for _, (_, f) in merged if f >= 500)
    rime_ice_files = [f for f in FILES if f.startswith('rime-ice')]
    rime_frost_files = [f for f in FILES if f.startswith('rime-frost')]

    def src_total(file_list):
        return sum(source_counts.get(f, 0) for f in file_list)

    with open(output_dir / 'CHANGELOG.md', 'w', encoding='utf-8') as f:
        f.write('## 词库统计\n\n')
        f.write('| 指标 | 数值 |\n')
        f.write('|------|------|\n')
        f.write(f'| 去重后总词条 | {len(merged):,} |\n')
        f.write(f'| 可写入 DAT（有拼音） | {usable_count:,} |\n')
        f.write(f'| 无拼音剔除（纯词频表） | {no_pinyin_count:,} |\n')
        f.write(f'| 词频 ≥ 100 | {freq100_count:,} |\n')
        f.write(f'| 词频 ≥ 500 | {freq500_count:,} |\n')
        f.write('\n## 数据来源\n\n')
        f.write(f'- **rime-ice** (雾凇拼音) — {src_total(rime_ice_files):,} 条\n')
        for fn in rime_ice_files:
            if fn in source_counts:
                f.write(f'  - {fn}: {source_counts[fn]:,} 条\n')
        f.write(f'\n- **rime-frost** (白霜拼音) — {src_total(rime_frost_files):,} 条\n')
        for fn in rime_frost_files:
            if fn in source_counts and source_counts[fn] > 0:
                f.write(f'  - {fn.replace("rime-frost_", "")}: {source_counts[fn]:,} 条\n')
        f.write('\n## 下载文件\n\n')
        f.write('- `msp_lite.dat` — 精简版（推荐 Windows 10/11 直接导入，≤ 2 万条）\n')
        f.write('- `msp_standard.dat` — 标准版（约 5 万条，管理界面会卡顿）\n')
        f.write('- `msp_full.dat` — 完整版（约百万条，仅供存档/转其他输入法）\n')
        f.write('- `msp_win10.dat` — 兼容旧链接，等同 `msp_lite.dat`\n')


def main() -> int:
    parser = argparse.ArgumentParser(description='合并 Rime 词库为 msp_full.txt')
    parser.add_argument('--cache', default=str(ROOT / 'cache'), help='缓存目录')
    parser.add_argument('--output', default=str(ROOT), help='输出目录')
    parser.add_argument('--emit-freq-tiers', action='store_true',
                        help='额外输出旧的 msp_freq*.txt（仅调试用）')
    args = parser.parse_args()

    cache_dir = Path(args.cache)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not cache_dir.is_dir():
        print(f'错误: 缓存目录不存在: {cache_dir}\n'
              f'先执行: python scripts/download_frost.py', file=sys.stderr)
        return 1

    all_entries = []
    source_counts = {}
    missing = []
    for fn in FILES:
        path = cache_dir / fn
        if not path.exists():
            missing.append(fn)
            print(f'{fn}: MISSING')
            continue
        with open(path, encoding='utf-8') as f:
            entries = parse_rime(f.read())
        all_entries.append(entries)
        source_counts[fn] = len(entries)
        size_kb = os.path.getsize(path) // 1024
        print(f'{fn}: {len(entries):>8,} 条  ({size_kb:>6}KB)')

    if missing:
        print(f'\n错误: 缺少 {len(missing)} 个源文件，合并结果会严重不完整。', file=sys.stderr)
        print('先执行: python scripts/download_frost.py', file=sys.stderr)
        return 1
    if not all_entries:
        print('错误: 没有可用的源文件，拒绝产出空词库。', file=sys.stderr)
        return 1

    merged = merge(all_entries)
    no_pinyin = sum(1 for _, (p, _) in merged if not p)
    zero_freq = sum(1 for _, (p, f) in merged if p and f < 1)
    usable_count = write_full(merged, output_dir)
    size_mb = os.path.getsize(output_dir / 'msp_full.txt') / 1024 / 1024

    print(f'\n去重后: {len(merged):,} 条')
    print(f'可写入 DAT（有拼音）: {usable_count:,} 条  ({size_mb:.1f}MB)')
    if no_pinyin:
        print(f'⚠️  剔除无拼音词条: {no_pinyin:,} 条（纯词频表无法写入 mschxudp）')
    if zero_freq:
        print(f'剔除无词频词条: {zero_freq:,} 条（freq < 1）')

    if args.emit_freq_tiers:
        write_freq_tiers(merged, output_dir)

    write_changelog(merged, usable_count, no_pinyin, source_counts, output_dir)
    print('CHANGELOG.md 已生成')
    return 0


if __name__ == '__main__':
    sys.exit(main())
