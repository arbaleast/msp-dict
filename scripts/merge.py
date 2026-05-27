import os
import datetime

def parse_rime(content):
    """解析 Rime 格式：词\t拼音\t词频"""
    entries = []
    for line in content.splitlines():
        line = line.strip()
        if not line: continue
        if line.startswith('#') or line.startswith('---') \
           or line.startswith('name:') or line.startswith('version:') or line.startswith('sort:'):
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
            pinyin_candidate = parts[1].strip()
            if pinyin_candidate and not any(c.isdigit() for c in pinyin_candidate):
                if word and ord(word[0]) >= 0x4E00:
                    entries.append((word, pinyin_candidate, 1))
            else:
                try:
                    freq = int(pinyin_candidate)
                except ValueError:
                    continue
                if word and freq >= 0:
                    entries.append((word, '', freq))
    return entries

def merge(entries_list):
    """合并去重，返回 [(word, pinyin, freq), ...] 按词频降序"""
    word_data = {}
    for entries in entries_list:
        for word, pinyin, freq in entries:
            if word in word_data:
                old_pinyin, old_freq = word_data[word]
                word_data[word] = (old_pinyin if old_pinyin else pinyin, max(old_freq, freq))
            else:
                word_data[word] = (pinyin, freq)
    return sorted(word_data.items(), key=lambda x: x[1][1], reverse=True)

files = [
    'rime-ice_base.txt', 'rime-ice_ext.txt', 'rime-ice_tencent.txt',
    'rime-ice_8105.txt', 'rime-ice_others.txt',
    'rime-frost_base.txt', 'rime-frost_ext.txt',
    # rime-frost tencent 跳过（29MB > 25MB GitHub限制，且rime-ice tencent已覆盖）
    'rime-frost_8105.txt', 'rime-frost_others.txt',
    # 搜狗细胞词库（21个）
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

all_entries = []
for fn in files:
    path = os.path.join('cache', fn)
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            entries = parse_rime(f.read())
            all_entries.append(entries)
            size_kb = os.path.getsize(path) // 1024
            print(f'{fn}: {len(entries):>8,} 条  ({size_kb:>6}KB)')
    else:
        print(f'{fn}: MISSING')

merged = merge(all_entries)
print(f'\n去重后: {len(merged):,} 条')

# 生成各词频等级文本文件
for min_freq, suffix in [(1,'full'), (10,'freq10'), (50,'freq50'), (100,'freq100'), (500,'freq500')]:
    out = f'msp_{suffix}.txt'
    count = 0
    with open(out, 'w', encoding='utf-8') as f:
        for word_data in merged:
            word = word_data[0]
            pinyin, freq = word_data[1]
            if freq >= min_freq:
                f.write(f'{word}\t{pinyin}\t{freq}\n')
                count += 1
    size_mb = os.path.getsize(out) / 1024 / 1024
    print(f'已生成 {out}: {count:,} 条  ({size_mb:.1f}MB)')

# 分类统计
rime_ice_files = [f for f in files if f.startswith('rime-ice')]
rime_frost_files = [f for f in files if f.startswith('rime-frost')]
source_counts = {}
for fn in files:
    path = os.path.join('cache', fn)
    if os.path.exists(path):
        with open(path, encoding='utf-8') as cf:
            source_counts[fn] = len(parse_rime(cf.read()))

def src_total(file_list):
    return sum(source_counts.get(f, 0) for f in file_list)

freq100_count = sum(1 for _, (_, f) in merged if f >= 100)
freq500_count = sum(1 for _, (_, f) in merged if f >= 500)

with open('CHANGELOG.md', 'w') as f:
    f.write(f'## 词库统计\n\n')
    f.write(f'| 指标 | 数值 |\n')
    f.write(f'|------|------|\n')
    f.write(f'| 去重后总词条 | {len(merged):,} |\n')
    f.write(f'| 词频 ≥ 100 | {freq100_count:,} |\n')
    f.write(f'| 词频 ≥ 500 | {freq500_count:,} |\n')
    f.write(f'\n## 数据来源\n\n')
    f.write(f'- **rime-ice** (雾凇拼音) — {src_total(rime_ice_files):,} 条\n')
    for fn in rime_ice_files:
        if fn in source_counts:
            f.write(f'  - {fn}: {source_counts[fn]:,} 条\n')
    f.write(f'\n- **rime-frost** (白霜拼音) — {src_total(rime_frost_files):,} 条\n')
    for fn in rime_frost_files:
        if fn in source_counts and source_counts[fn] > 0:
            short_name = fn.replace('rime-frost_', '')
            f.write(f'  - {short_name}: {source_counts[fn]:,} 条\n')
    f.write(f'\n## 下载文件\n\n')
    f.write(f'- `msp_full.dat` — 完整版\n')
    f.write(f'- `msp_freq10.dat` — 词频 ≥ 10\n')
    f.write(f'- `msp_freq50.dat` — 词频 ≥ 50\n')
    f.write(f'- `msp_freq100.dat` — 词频 ≥ 100\n')
    f.write(f'- `msp_freq500.dat` — 词频 ≥ 500\n')
print('CHANGELOG.md 已生成')
