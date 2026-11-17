#!/usr/bin/env python3
"""
合并 Rime 词库与扩展词源，输出按来源分层的全量文本 msp_full.txt。

基础源（必需）:
  rime-ice / rime-frost（cache/rime-*.txt）

扩展源（可选，缺失只告警）:
  萌娘百科  cache/ext-moegirl.dict.yaml
  中文维基  cache/ext-zhwiki.dict.yaml
  搜狗 SCEL cache/scel/*.scel（需自行准备，解析复用 crawler/scel_parser.py）

规则:
  * 同一词条保留最高词频；已有拼音优先于空拼音；基础源优先于扩展源
  * 只有词频、没有拼音的行（rime-ice tencent 等）无法写入 mschxudp，直接剔除
  * 扩展源强过滤：纯中文、2~6 字、拼音可规范化为小写 a-z + '
  * 输出 `词条\\t拼音\\t词频\\t来源`，基础源在前（按词频降序），扩展源在后
    （按词长、词典序），三档构建据此做配额截断

用法:
    python scripts/merge.py                       # 读 cache/，写 msp_full.txt + CHANGELOG.md
    python scripts/merge.py --no-extended         # 只合并基础源
    python scripts/merge.py --strict-ext          # 扩展源缺失也视为失败（CI 可选）
    python scripts/merge.py --emit-freq-tiers     # 额外输出旧的 msp_freq*.txt（仅调试用）
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.format_spec import normalize_pinyin, utf16_units  # noqa: E402

CJK_RE = None  # 延迟编译，避免顶层 import re 之外的副作用
EXT_MIN_UNITS = 2
EXT_MAX_UNITS = 6

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

# 上游文件超过 jsDelivr 单文件 20MB 限制（HTTP 403），任何镜像都拿不到；
# 缺失时只告警，不让整条流水线失败。其余文件缺失一律报错退出。
OPTIONAL_FILES = {'rime-frost_composite.txt'}

# (文件名, 来源标记, 显示名)
EXTENDED_FILES = [
    ('ext-moegirl.dict.yaml', 'moegirl', '萌娘百科'),
    ('ext-zhwiki.dict.yaml', 'wiki', '中文维基百科'),
]

SCEL_GLOB = 'scel/*.scel'


def _cjk_re():
    global CJK_RE
    if CJK_RE is None:
        import re
        CJK_RE = re.compile(r'^[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+$')
    return CJK_RE


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
        if line.startswith('#') or line.startswith('---'):
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


def parse_extended_dict(content: str):
    """解析 fcitx5/rime 导出的扩展词典。

    格式：`---` 头、`...` 之后是正文，每行 `词条\\t拼音（音节用空格分隔）`，
    一般没有词频列（词频记为 1，由构建阶段的配额与基础源优先生效）。
    """
    entries = []
    in_body = False
    for line in content.splitlines():
        if not in_body:
            if line.strip() == '...':
                in_body = True
            continue
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            continue
        word = parts[0].strip()
        pinyin = parts[1].strip()
        if word and pinyin:
            entries.append((word, pinyin, 1))
    return entries


def clean_extended(word: str, pinyin: str):
    """扩展源强过滤：纯中文、2~6 字、拼音合法；返回规范化拼音或 None。"""
    word = (word or '').strip()
    if not word or not _cjk_re().match(word):
        return None
    units = utf16_units(word)
    if units < EXT_MIN_UNITS or units > EXT_MAX_UNITS:
        return None
    code = normalize_pinyin(pinyin)
    if not code or not all(c.isascii() and (c.islower() or c == "'") for c in code):
        return None
    if code.startswith("'") or code.endswith("'") or "''" in code:
        return None
    return code


def parse_scel_file(path: Path):
    """用 crawler/scel_parser.py 解析一个 .scel，返回 [(词, 拼音, 词频)]。"""
    try:
        from crawler.scel_parser import ScelParser
    except ImportError:
        return []
    parser = ScelParser()
    try:
        parser.load(str(path))
    except Exception:
        return []
    return list(parser.entries)


def merge(entries_list):
    """合并基础源，返回 [(词, 拼音, 词频, 'base')]，按词频降序。"""
    word_data = {}
    for entries in entries_list:
        for word, pinyin, freq in entries:
            if word in word_data:
                old_pinyin, old_freq = word_data[word]
                word_data[word] = (old_pinyin if old_pinyin else pinyin,
                                   max(old_freq, freq))
            else:
                word_data[word] = (pinyin, freq)
    ordered = sorted(word_data.items(), key=lambda x: x[1][1], reverse=True)
    return [(word, pinyin, freq, 'base') for word, (pinyin, freq) in ordered]


def merge_extended(base_merged, ext_entries):
    """把扩展源并入基础结果：同词以基础源为准，扩展源按词长/字典序稳定排序。"""
    existing = {item[0] for item in base_merged}
    ext_words = {}
    for word, pinyin, freq, source in ext_entries:
        if word in existing or word in ext_words:
            continue
        ext_words[word] = (pinyin, freq, source)
    ordered = sorted(ext_words.items(), key=lambda x: (utf16_units(x[0]), x[0]))
    return base_merged + [(word, pinyin, freq, source)
                          for word, (pinyin, freq, source) in ordered]


def write_full(merged, output_dir: Path) -> int:
    """写入有拼音且词频 >= 1 的词条（含来源列）。"""
    count = 0
    with open(output_dir / 'msp_full.txt', 'w', encoding='utf-8') as f:
        for word, pinyin, freq, source in merged:
            if not pinyin or freq < 1:
                continue
            f.write(f'{word}\t{pinyin}\t{freq}\t{source}\n')
            count += 1
    return count


def write_freq_tiers(merged, output_dir: Path) -> None:
    for min_freq, suffix in [(10, 'freq10'), (50, 'freq50'),
                             (100, 'freq100'), (500, 'freq500')]:
        out = output_dir / f'msp_{suffix}.txt'
        count = 0
        with open(out, 'w', encoding='utf-8') as f:
            for word, pinyin, freq, source in merged:
                if freq >= min_freq:
                    f.write(f'{word}\t{pinyin}\t{freq}\t{source}\n')
                    count += 1
        print(f'已生成 {out.name}: {count:,} 条')


def write_changelog(merged, usable_count, no_pinyin_count, source_counts,
                    output_dir: Path, ext_stats=None, ext_counts=None):
    ext_stats = ext_stats or {}
    ext_counts = ext_counts or {}
    by_source = {}
    for _, _, _, source in merged:
        by_source[source] = by_source.get(source, 0) + 1

    freq100_count = sum(1 for _, _, f, _ in merged if f >= 100)
    freq500_count = sum(1 for _, _, f, _ in merged if f >= 500)
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
        if ext_stats:
            f.write('\n- **扩展源**（可选，构建时按档位配额截断）\n')
            for source, item in ext_stats.items():
                f.write(f'  - {item["label"]}：原始 {item["raw"]:,} 条，'
                        f'清洗后 {item["clean"]:,} 条，去重后入选 {ext_counts.get(source, 0):,} 条\n')
        f.write('\n## 下载文件\n\n')
        f.write('- `msp_lite.dat` — 精简版（推荐 Windows 10/11 直接导入，≤ 2 万条；'
                '扩展源 ≤12%）\n')
        f.write('- `msp_standard.dat` — 标准版（约 5 万条，管理界面会卡顿；扩展源 ≤22%）\n')
        f.write('- `msp_full.dat` — 完整版（约百万条，仅供存档/转其他输入法）\n')
        f.write('- `msp_win10.dat` — 兼容旧链接，等同 `msp_lite.dat`\n')


def load_extended(cache_dir: Path, strict: bool):
    """载入扩展源，返回 (entries, stats, missing)。"""
    entries = []
    stats = {}
    missing = []

    for filename, source, label in EXTENDED_FILES:
        path = cache_dir / filename
        if not path.exists() or path.stat().st_size == 0:
            missing.append(filename)
            print(f'{filename}: MISSING（扩展源，缺失时仅告警）')
            continue
        raw = parse_extended_dict(path.read_text(encoding='utf-8', errors='replace'))
        kept = 0
        for word, pinyin, freq in raw:
            code = clean_extended(word, pinyin)
            if code is None:
                continue
            entries.append((word, code, freq, source))
            kept += 1
        stats[source] = {'label': label, 'raw': len(raw), 'clean': kept}
        print(f'{filename}: 原始 {len(raw):>9,} 条，清洗后 {kept:>9,} 条')
        del path

    scel_files = sorted(cache_dir.glob(SCEL_GLOB))
    scel_total = 0
    for scel in scel_files:
        raw = parse_scel_file(scel)
        kept = 0
        for word, pinyin, freq in raw:
            code = clean_extended(word, pinyin)
            if code is None:
                continue
            entries.append((word, code, max(1, int(freq or 1)), 'sogou'))
            kept += 1
        scel_total += kept
        print(f'{scel.name}: 原始 {len(raw):>9,} 条，清洗后 {kept:>9,} 条')
    if scel_total:
        stats['sogou'] = {'label': f'搜狗细胞词库（{len(scel_files)} 个 .scel）',
                          'raw': scel_total, 'clean': scel_total}

    return entries, stats, missing


def main() -> int:
    parser = argparse.ArgumentParser(description='合并 Rime 词库为 msp_full.txt')
    parser.add_argument('--cache', default=str(ROOT / 'cache'), help='缓存目录')
    parser.add_argument('--output', default=str(ROOT), help='输出目录')
    parser.add_argument('--emit-freq-tiers', action='store_true',
                        help='额外输出旧的 msp_freq*.txt（仅调试用）')
    parser.add_argument('--no-extended', action='store_true',
                        help='不合并扩展源（萌娘/维基/SCEL）')
    parser.add_argument('--strict-ext', action='store_true',
                        help='扩展源缺失时直接失败（默认只告警）')
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
    missing_optional = []
    for fn in FILES:
        path = cache_dir / fn
        # 0 字节文件视为缺失：下载失败（curl -f / 403）可能留下空文件
        if not path.exists() or path.stat().st_size == 0:
            if fn in OPTIONAL_FILES:
                missing_optional.append(fn)
                print(f'{fn}: MISSING（可选源，上游超过 20MB 限制，跳过）')
            else:
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
    if missing_optional:
        print(f'ℹ️  跳过 {len(missing_optional)} 个可选源: {", ".join(missing_optional)}')
    if not all_entries:
        print('错误: 没有可用的源文件，拒绝产出空词库。', file=sys.stderr)
        return 1

    merged = merge(all_entries)

    ext_stats = {}
    ext_counts = {}
    if not args.no_extended:
        ext_entries, ext_stats, ext_missing = load_extended(cache_dir, args.strict_ext)
        if ext_missing:
            if args.strict_ext:
                print(f'\n错误: --strict-ext 要求扩展源齐全，缺少: '
                      f'{", ".join(ext_missing)}', file=sys.stderr)
                print('先执行: python scripts/download_frost.py --with-extended', file=sys.stderr)
                return 1
            print(f'ℹ️  扩展源缺失 {len(ext_missing)} 个，已降级为仅基础源')
        merged = merge_extended(merged, ext_entries)
        for _, _, _, source in merged:
            ext_counts[source] = ext_counts.get(source, 0) + 1

    no_pinyin = sum(1 for _, p, _, _ in merged if not p)
    zero_freq = sum(1 for _, p, f, _ in merged if p and f < 1)
    usable_count = write_full(merged, output_dir)
    size_mb = os.path.getsize(output_dir / 'msp_full.txt') / 1024 / 1024

    print(f'\n去重后: {len(merged):,} 条')
    print(f'可写入 DAT（有拼音）: {usable_count:,} 条  ({size_mb:.1f}MB)')
    if no_pinyin:
        print(f'⚠️  剔除无拼音词条: {no_pinyin:,} 条（纯词频表无法写入 mschxudp）')
    if zero_freq:
        print(f'剔除无词频词条: {zero_freq:,} 条（freq < 1）')
    for source, item in ext_stats.items():
        print(f'扩展源 {source}: 原始 {item["raw"]:,} → 清洗 {item["clean"]:,} '
              f'→ 去重后 {ext_counts.get(source, 0):,}')

    if args.emit_freq_tiers:
        write_freq_tiers(merged, output_dir)

    write_changelog(merged, usable_count, no_pinyin, source_counts, output_dir,
                    ext_stats, ext_counts)
    print('CHANGELOG.md 已生成')
    return 0


if __name__ == '__main__':
    sys.exit(main())
