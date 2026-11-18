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
    （按「基础源单字热度」打分降序），三档构建据此做配额截断

用法:
    python scripts/merge.py                       # 读 cache/，写 msp_full.txt + CHANGELOG.md
    python scripts/merge.py --no-extended         # 只合并基础源
    python scripts/merge.py --strict-ext          # 扩展源缺失也视为失败（CI 可选）
    python scripts/merge.py --emit-freq-tiers     # 额外输出旧的 msp_freq*.txt（仅调试用）
"""

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.format_spec import normalize_pinyin, utf16_units  # noqa: E402
from crawler.scel_parser import ScelParseError  # noqa: E402

CJK_RE = None  # 延迟编译，避免顶层 import re 之外的副作用
EXT_MIN_UNITS = 2
EXT_MAX_UNITS = 6

# 基本汉字区（CJK Unified Ideographs）。扩展区（A 区 U+3400-U+4DBF、B 区
# U+20000 起）里的生僻字在日常输入里几乎不会被用到，热度打分时按 0 处理。
BASIC_CJK_MIN = 0x4E00
BASIC_CJK_MAX = 0x9FFF

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
    """用 crawler/scel_parser.py 解析一个 .scel，返回 [(词, 拼音, 词频)]。

    解析失败时抛出 ScelParseError（不静默返回空列表），由调用方决定
    是跳过该文件还是终止构建。
    """
    from crawler.scel_parser import ScelParseError, ScelParser

    parser = ScelParser()
    try:
        parser.load(str(path))
    except ScelParseError:
        raise
    except Exception as exc:
        raise ScelParseError(f'{path.name} 解析失败: {exc}') from exc
    return list(parser.entries)


def merge(entries_list):
    """合并基础源，返回 [(词, 拼音, 词频, 'base')]，按词频降序。

    去重键是 **(词, 拼音)** 而不是单独的词：同一个词的不同合法读音都要保留
    （例如「银行」yin'hang 与 yin'xing），否则多音词会被暴力折叠成一个读音。

    词频仍按「词」聚合取各源最大值，与旧实现完全一致——因此只有一个读音的
    词条，其拼音、词频与排序位置都不受影响，档位截断结果保持稳定。
    """
    word_freq = {}       # 词 -> 各源最大词频（含无拼音的纯词频表）
    word_pinyins = {}    # 词 -> {归一化拼音: (原始拼音, 该组合的最大词频)}
    for entries in entries_list:
        for word, pinyin, freq in entries:
            if word not in word_freq or freq > word_freq[word]:
                word_freq[word] = freq
            if pinyin:
                # 去重键用归一化拼音（与 builder 的 normalize_pinyin 同一套规则），
                # 否则「yinhang」与「yin hang」会被当成两个读音，最后在 builder
                # 里归一化成同一个 code 而被判成重复词条。
                key = normalize_pinyin(pinyin)
                if not key:
                    continue
                bucket = word_pinyins.setdefault(word, {})
                if key not in bucket or freq > bucket[key][1]:
                    bucket[key] = (pinyin, freq)

    rows = []
    for word, freq in word_freq.items():
        pinyins = word_pinyins.get(word)
        if not pinyins:
            # 所有源都没有拼音（纯词频表），后续 write_full 会剔除
            rows.append((word, '', freq))
        else:
            for original, _ in pinyins.values():
                rows.append((word, original, freq))
    # 稳定排序：同词频保持首次出现顺序，与旧实现一致
    rows.sort(key=lambda x: x[2], reverse=True)
    return [(word, pinyin, freq, 'base') for word, pinyin, freq in rows]


def build_char_weight(entries_list) -> dict:
    """统计基础源里每个汉字的「热度权重」。

    扩展源（维基/萌娘/SCEL）没有可比词频（上游一律给 1），没法直接按质量
    排序。这里用「这个字在基础源里出现得多频繁」当作质量代理：常用字组成的
    专有名词（蘑菇云、明日方舟）应该排在生僻字组成的词条（㐵作、㑎姓）前面。

    权重取词频的对数（log1p）后按出现次数累加——高频词贡献大，但不会让单个
    超高频词把某个字彻底垄断。只统计基本汉字区（U+4E00-U+9FFF），
    其它区段的字权重恒为 0，视为生僻字。
    """
    weight = {}
    for entries in entries_list:
        for entry in entries:
            # 兼容 (词, 拼音, 词频) 与 (词, 拼音, 词频, 来源) 两种形状
            word, freq = entry[0], entry[2]
            if freq <= 0:
                continue
            gain = math.log1p(freq)
            for ch in word:
                if BASIC_CJK_MIN <= ord(ch) <= BASIC_CJK_MAX:
                    weight[ch] = weight.get(ch, 0.0) + gain
    return weight


class BigramModel:
    """用基础源词频训练出来的二元语法模型。

    只靠「单字有多常见」判断不了质量：「人一」「了一」「子一」这类碎片用的全
    是最高频的字，单字权重反而最高，必须靠「这些字能不能组成词」来区分。
    基础源本身就是 260 万条中文词，用它统计相邻字共现就是一个现成的语言模型。

    打分 = 平均每个字的 log 概率（越接近 0 越像正常词），并按词长微调：
    2~3 字最优，4 字次之，更长的轻微扣分。
    """

    # 二元切分的插值系数：0.7 * 一元 + 0.3 * 二元。
    # 一元保证没见过的搭配也有合理下限，二元负责区分「成词」与「不成词」。
    LAMBDA = 0.7

    def __init__(self):
        self.total = 0
        self.char_count = {}
        self.bigram_count = {}

    @staticmethod
    def _key(a: str, b: str) -> int:
        # 用 int 当 key 比 tuple 省一半内存（约 90 万条二元组时差别很明显）
        return (ord(a) << 16) | ord(b)

    def add_word(self, word: str) -> None:
        if len(word) < 1:
            return
        self.total += 1
        for ch in set(word):
            self.char_count[ch] = self.char_count.get(ch, 0) + 1
        for pair in set(zip(word, word[1:])):
            key = self._key(pair[0], pair[1])
            self.bigram_count[key] = self.bigram_count.get(key, 0) + 1

    def mean_log_prob(self, word: str) -> float:
        """返回平均每个字的 log 概率；越接近 0 越像正常词。"""
        if not self.total or len(word) < 2:
            return -99.0
        total = float(self.total)
        p_first = self.char_count.get(word[0], 0) / total
        acc = math.log(max(p_first, 1e-12))
        for i in range(len(word) - 1):
            a, b = word[i], word[i + 1]
            p_uni = self.char_count.get(b, 0) / total
            denom = max(self.char_count.get(a, 0), 1)
            p_bi = self.bigram_count.get(self._key(a, b), 0) / denom
            p = self.LAMBDA * p_uni + (1.0 - self.LAMBDA) * p_bi
            acc += math.log(max(p, 1e-12))
        return acc / len(word)


def build_bigram_model(entries_list) -> BigramModel:
    """用基础源词条训练二元语法模型。"""
    model = BigramModel()
    for entries in entries_list:
        for entry in entries:
            word = entry[0]
            freq = entry[2]
            if freq <= 0 or not word:
                continue
            model.add_word(word)
    return model


# 词长偏好：2~3 字最优，4 字次之，更长轻微扣分
LENGTH_FACTOR = {2: 1.0, 3: 1.0, 4: 0.95, 5: 0.85}

# 判定为「生僻/无效」的兜底分，必须小于任何正常词条
INVALID_SCORE = -1e9

# 同拼音竞争惩罚系数：如果基础源里同拼音的词条已经很多，扩展词即使分高也
# 挤不进候选前 9 位（候选位上限 9），属于浪费配额，因此要扣分。
PY_SATURATION_PENALTY = 0.5


def extended_score(word: str, char_weight: dict, bigram: BigramModel = None) -> tuple:
    """给扩展源词条打分（越大越优先），返回 (主分, 次分)。

    * 含非基本汉字区字符，或含在基础源里从未出现过的字 → 垫底
      （不删除，full 档仍会收录，lite/standard 优先取高分词）。
    * 主分 = 二元语法的平均 log 概率 + 词长系数；没有 bigram 时退化为
      最小单字权重 × 词长系数。
    * 次分 = 最小单字权重（木桶效应：只要有一个字罕见，整词就靠后）。
    """
    if not word:
        return (INVALID_SCORE, 0.0)
    weights = []
    for ch in word:
        if not (BASIC_CJK_MIN <= ord(ch) <= BASIC_CJK_MAX):
            return (INVALID_SCORE, 0.0)
        weights.append(char_weight.get(ch, 0.0))
    if not weights or min(weights) <= 0.0:
        return (INVALID_SCORE, 0.0)
    n = len(weights)
    length_factor = LENGTH_FACTOR.get(n, 0.7)
    min_weight = min(weights)
    if bigram is not None:
        primary = bigram.mean_log_prob(word) + math.log(length_factor)
    else:
        primary = min_weight * length_factor
    return (primary, min_weight)


def merge_extended(base_merged, ext_entries, char_weight=None, bigram=None):
    """把扩展源并入基础结果。

    去重键同样是 (词, 拼音)：基础源已有的读音不再重复引入，但扩展源提供的
    **另一个**合法读音会被保留（例如基础源只有 yin'hang，扩展源补充 yin'xing）。

    排序按「基础源训练出的质量打分」降序（见 extended_score），不再按 Unicode
    码点升序——后者会让 CJK 扩展区的生僻字、以及「一X」「丁X」这类排在
    码点最前面的词霸占配额。

    另外对「同拼音已经有大量基础词条」的扩展词扣分：候选位上限是 9，
    基础词会先占满前 9 位，这类扩展词在输入法里根本轮不到显示，
    留着只是浪费配额。
    """
    char_weight = char_weight or {}
    # 同样用归一化拼音做键：基础源的「yinhang」与扩展源的「yin hang」是同一个读音
    existing = {(item[0], normalize_pinyin(item[1])) for item in base_merged}
    pinyin_count = {}
    for item in base_merged:
        code = normalize_pinyin(item[1])
        if code:
            pinyin_count[code] = pinyin_count.get(code, 0) + 1
    ext_words = {}
    for word, pinyin, freq, source in ext_entries:
        key = (word, normalize_pinyin(pinyin))
        if not key[1] or key in existing or key in ext_words:
            continue
        ext_words[key] = (pinyin, freq, source)

    scored = []
    for (word, _norm), (pinyin, freq, source) in ext_words.items():
        primary, secondary = extended_score(word, char_weight, bigram)
        if primary > INVALID_SCORE / 2:
            saturation = math.log(1 + pinyin_count.get(normalize_pinyin(pinyin), 0))
            primary -= PY_SATURATION_PENALTY * saturation
        scored.append(((primary, secondary), word, pinyin, freq, source))
    # 得分降序；同分再按词长、词、拼音稳定排序，保证每次构建结果可复现
    scored.sort(key=lambda item: (-item[0][0], -item[0][1],
                                  len(item[1]), item[1], item[2]))
    return base_merged + [(word, pinyin, freq, source)
                          for _score, word, pinyin, freq, source in scored]


def sha256_of_file(path: Path) -> str:
    """计算文件 SHA-256（分块读取，支持大文件）。"""
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now_iso() -> str:
    """当前 UTC 时间（秒级 ISO-8601）。"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def write_merge_metadata(output_dir: Path, cache_dir: Path,
                          source_files: List[str], merged_count: int,
                          usable_count: int,
                          extended_files: List[str] = None) -> Path:
    """写出 msp_full.txt 的溯源元数据。

    记录每个上游源文件的 SHA-256 与大小，以及合并产物本身的 SHA-256，
    保证「这份词库是由哪些上游文件、在什么时间、经过什么处理得到的」可追溯。
    """
    sources = []
    for name in source_files:
        path = cache_dir / name
        if not path.exists() or path.stat().st_size == 0:
            continue
        stat = path.stat()
        sources.append({
            'file': name,
            'size_bytes': stat.st_size,
            'sha256': sha256_of_file(path),
            'modified_at': datetime.fromtimestamp(
                stat.st_mtime, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        })

    # 扩展源（萌娘/维基/SCEL）同样登记，保证上游动态数据可追溯
    for name in (extended_files or []):
        path = cache_dir / name
        if not path.exists() or path.stat().st_size == 0:
            continue
        stat = path.stat()
        sources.append({
            'file': name,
            'size_bytes': stat.st_size,
            'sha256': sha256_of_file(path),
            'modified_at': datetime.fromtimestamp(
                stat.st_mtime, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'kind': 'extended',
        })

    output = output_dir / 'msp_full.txt'
    payload = {
        'format': 'msp-dict-merge-metadata/1',
        'generated_at': utc_now_iso(),
        'cache_dir': str(cache_dir),
        'merged_entries': merged_count,
        'writable_entries': usable_count,
        'sources': sources,
        'output': {
            'file': output.name,
            'size_bytes': output.stat().st_size if output.exists() else 0,
            'sha256': sha256_of_file(output) if output.exists() else '',
        },
    }
    path = output_dir / 'msp_full.meta.json'
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding='utf-8')
    return path


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
        f.write('- `msp_lite.dat` — 核心主力档（≤ 20 万条，剔除单字；扩展源 ≤15%）\n')
        f.write('- `msp_standard.dat` — 全能进阶档（≤ 80 万条，含单字；扩展源 ≤35%）\n')
        f.write('- `msp_full.dat` — 全量档（不截断，仅供存档/转其他输入法）\n')
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
        try:
            raw = parse_scel_file(scel)
        except ScelParseError as exc:
            # 损坏的 .scel 不能静默跳过：明确告警并继续处理其它文件
            print(f'\n⚠️  {scel.name} 解析失败，已跳过: {exc}')
            continue
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
    used_source_files = [fn for fn in FILES
                         if fn in source_counts and source_counts[fn] > 0]

    # 基础源单字热度：用于给没有可比词频的扩展源排序
    char_weight = build_char_weight(all_entries)
    bigram = build_bigram_model(all_entries)

    ext_stats = {}
    ext_counts = {}
    if not args.no_extended:
        ext_entries, ext_stats, ext_missing = load_extended(cache_dir, args.strict_ext)
        if ext_missing:
            if args.strict_ext:
                print(f'\n错误: --strict-ext 要求扩展源齐全，缺少: '
                      f'{", ".join(ext_missing)}', file=sys.stderr)
                print('先执行: python scripts/download_frost.py --strict-ext',
                      file=sys.stderr)
                return 1
            print(f'ℹ️  扩展源缺失 {len(ext_missing)} 个，已降级为仅基础源')
        merged = merge_extended(merged, ext_entries, char_weight, bigram)
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

    used_extended = [name for name, _, _ in EXTENDED_FILES]
    used_extended += [p.name for p in sorted(cache_dir.glob(SCEL_GLOB))]
    meta_path = write_merge_metadata(output_dir, cache_dir, used_source_files,
                                     len(merged), usable_count, used_extended)
    print(f'溯源元数据已写入: {meta_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
