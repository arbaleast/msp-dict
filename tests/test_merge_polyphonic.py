"""Phase C：多音字去重、词源溯源元数据、profile 语义与跨平台路径的回归测试。"""

import importlib.util
import math
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


merge_mod = _load('merge_phase_c', ROOT / 'scripts' / 'merge.py')
download_mod = _load('download_frost_phase_c', ROOT / 'scripts' / 'download_frost.py')


# --------------------------------------------------------------------------
# 任务 1：多音字不能被暴力去重
# --------------------------------------------------------------------------

def test_merge_keeps_both_pronunciations_of_same_word():
    """同一个词的不同合法读音必须都保留（银行 yin'hang / yin'xing）。"""
    entries = [[('银行', "yin'xing", 300), ('银行', "yin'hang", 5000)]]
    merged = merge_mod.merge(entries)
    readings = sorted(p for w, p, _, _ in merged if w == '银行')
    assert readings == ["yin'hang", "yin'xing"]
    # 两行共用该词的最大词频（保持与旧实现一致的排序优先级）
    freqs = {f for w, _, f, _ in merged if w == '银行'}
    assert freqs == {5000}


def test_merge_single_pronunciation_output_unchanged():
    """只有一个读音的词条，输出与旧实现完全一致（拼音、词频、顺序）。"""
    entries = [[('中国', 'zhongguo', 100), ('北京', 'beijing', 200)]]
    merged = merge_mod.merge(entries)
    assert merged == [
        ('北京', 'beijing', 200, 'base'),
        ('中国', 'zhongguo', 100, 'base'),
    ]


def test_merge_prefers_first_nonempty_pinyin_and_max_freq():
    """纯词频表（无拼音）与带拼音的源合并时，拼音取自带拼音的源，词频取最大值。"""
    entries = [
        [('测试', '', 9000)],          # 只有词频
        [('测试', 'ce shi', 300)],     # 带拼音
    ]
    merged = merge_mod.merge(entries)
    assert merged == [('测试', 'ce shi', 9000, 'base')]


def test_merge_keeps_word_without_pinyin_as_empty():
    """所有源都没有拼音时，仍保留空拼音行（后续 write_full 会剔除）。"""
    entries = [[('纯词频', '', 500)]]
    merged = merge_mod.merge(entries)
    assert merged == [('纯词频', '', 500, 'base')]


def test_merge_extended_adds_alternate_pronunciation():
    """扩展源可以补充基础源没有的另一个读音，但不会重复同一个读音。"""
    base = [('银行', "yin'hang", 5000, 'base')]
    ext = [
        ('银行', "yin'xing", 300, 'wiki'),
        ('银行', "yin'hang", 400, 'wiki'),   # 与基础源重复，应被丢弃
        ('蓝鸟', 'lan niao', 200, 'wiki'),
    ]
    merged = merge_mod.merge_extended(base, ext)
    assert ('银行', "yin'xing", 300, 'wiki') in merged
    assert merged.count(('银行', "yin'hang", 5000, 'base')) == 1
    assert sum(1 for w, p, _, _ in merged if w == '银行' and p == "yin'hang") == 1
    assert ('蓝鸟', 'lan niao', 200, 'wiki') in merged


def test_merge_extended_preserves_ordering_of_new_entries():
    """扩展源内部按词长、字典序稳定排序。"""
    base = [('基础', 'ji chu', 10, 'base')]
    ext = [('长城', 'chang cheng', 5, 'wiki'), ('国内', 'gui nei', 5, 'wiki')]
    merged = merge_mod.merge_extended(base, ext)
    assert [w for w, _, _, _ in merged] == ['基础', '国内', '长城']


# --------------------------------------------------------------------------
# 任务 2：溯源元数据
# --------------------------------------------------------------------------

def test_download_source_metadata_records_url_hash_and_time(tmp_path):
    cache = tmp_path / 'cache'
    cache.mkdir()
    payload = b'hello rime\n'
    (cache / 'a.txt').write_bytes(payload)

    import hashlib
    record = download_mod.describe_source(cache / 'a.txt', 'https://example.com/a.txt', 'downloaded')
    assert record['file'] == 'a.txt'
    assert record['url'] == 'https://example.com/a.txt'
    assert record['status'] == 'downloaded'
    assert record['size_bytes'] == len(payload)
    assert record['sha256'] == hashlib.sha256(payload).hexdigest()
    assert len(record['fetched_at']) == 20 and record['fetched_at'].endswith('Z')

    path = download_mod.write_source_metadata(cache, [record])
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['format'] == 'msp-dict-source-metadata/1'
    assert data['sources'][0]['file'] == 'a.txt'
    assert 'sha256' in data['sources'][0]
    assert 'fetched_at' in data['sources'][0]


def test_merge_metadata_records_sources_and_output_hash(tmp_path):
    cache = tmp_path / 'cache'
    cache.mkdir()
    (cache / 'src.txt').write_text('词\tce shi\t10\n', encoding='utf-8')
    out = tmp_path / 'out'
    out.mkdir()
    (out / 'msp_full.txt').write_text('测试\tce shi\t10\tbase\n', encoding='utf-8')

    path = merge_mod.write_merge_metadata(out, cache, ['src.txt'], 1, 1)
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['format'] == 'msp-dict-merge-metadata/1'
    assert data['merged_entries'] == 1
    assert data['writable_entries'] == 1
    assert data['sources'][0]['file'] == 'src.txt'
    assert len(data['sources'][0]['sha256']) == 64
    assert len(data['output']['sha256']) == 64
    assert data['output']['size_bytes'] > 0


def test_merge_metadata_includes_extended_sources(tmp_path):
    cache = tmp_path / 'cache'
    cache.mkdir()
    (cache / 'base.txt').write_text('a\tb\t1\n', encoding='utf-8')
    (cache / 'ext-wiki.txt').write_text('c\td\t2\n', encoding='utf-8')
    out = tmp_path / 'out'
    out.mkdir()
    (out / 'msp_full.txt').write_text('测试\tce shi\t10\tbase\n', encoding='utf-8')

    path = merge_mod.write_merge_metadata(out, cache, ['base.txt'], 1, 1,
                                          ['ext-wiki.txt'])
    data = json.loads(path.read_text(encoding='utf-8'))
    ext = [s for s in data['sources'] if s.get('kind') == 'extended']
    assert len(ext) == 1
    assert ext[0]['file'] == 'ext-wiki.txt'
    assert len(ext[0]['sha256']) == 64


def test_crawler_save_words_writes_metadata(tmp_path):
    from crawler.pipeline import save_words

    out = tmp_path / 'words.txt'
    meta = save_words(['测试', '词条'], str(out), {'wikipedia': ['测试', '词条']})
    data = json.loads(meta.read_text(encoding='utf-8'))
    assert data['format'] == 'msp-dict-crawler-metadata/1'
    assert data['output']['entry_count'] == 2
    assert len(data['output']['sha256']) == 64
    assert data['sources'][0]['name'] == 'wikipedia'
    assert data['sources'][0]['entry_count'] == 2


# --------------------------------------------------------------------------
# 任务 3：profile 语义 + 跨平台路径
# --------------------------------------------------------------------------

def test_profile_exposes_coverage_scale_not_windows_importable():
    from src.profiles import PROFILES, get_profile

    lite = get_profile('lite')
    standard = get_profile('standard')
    full = get_profile('full')

    # 档位按覆盖规模划分
    assert lite.limit == 200000
    assert standard.limit == 800000
    assert full.limit is None
    assert lite.exclude_single is True
    assert standard.exclude_single is False
    assert lite.extended_ratio == 0.15
    assert standard.extended_ratio == 0.35

    # 旧的「可直接导入 Windows」表述与参考阈值都不得复活：
    # 它们既没有实机依据，也已经和当前档位策略不符
    assert not hasattr(lite, 'windows_importable')
    assert 'windows_importable' not in PROFILES['lite'].__dict__
    assert not hasattr(lite, 'within_reference_import_limit')
    import src.profiles as profiles_mod
    assert not hasattr(profiles_mod, 'REFERENCE_IMPORT_LIMIT')


def test_default_mspinyin_dict_is_platform_aware():
    from crawler import schedule

    if os.name == 'nt':
        assert 'InputMethod' in str(schedule.MSPINYIN_DICT)
    else:
        # 非 Windows 不能拼出 AppData 这种无意义的路径
        assert 'AppData' not in str(schedule.MSPINYIN_DICT)
        assert schedule.MSPINYIN_DICT.name == 'custom_phrase.dat'


def test_no_cron_hint_mentions_platform_specific_solution():
    from crawler import schedule

    hint = schedule.no_cron_hint('/tmp/x.dat')
    if os.name == 'nt':
        assert '任务计划程序' in hint
    else:
        assert 'cron' in hint.lower()
    assert '/tmp/x.dat' in hint


# --------------------------------------------------------------------------
# 任务 4：Validator 固定字段 / 保留字节
# --------------------------------------------------------------------------

def _build_sample() -> bytes:
    from src.builder_win10 import Win10MSPinyinBuilder

    builder = Win10MSPinyinBuilder(timestamp=1600000000)
    builder.add_word('测试', 'ce shi', 1)
    return builder.build()


def test_validator_flags_dirty_header_reserved_area(tmp_path):
    from src.validator import DatValidator

    data = bytearray(_build_sample())
    data[0x30] = 0x01          # 保留区 0x28~0x3F 之一
    path = tmp_path / 'dirty_header.dat'
    path.write_bytes(bytes(data))

    report = DatValidator().validate(str(path))
    codes = {issue.code for issue in report.issues}
    assert 'dirty_reserved' in codes
    issue = next(i for i in report.issues if i.code == 'dirty_reserved')
    assert issue.severity == 'error'
    assert issue.category == 'format'
    assert report.exit_code != 0


def test_validator_flags_dirty_entry_reserved_bytes(tmp_path):
    from src.validator import DatValidator

    import struct
    data = bytearray(_build_sample())
    count = struct.unpack_from('<I', data, 28)[0]
    record_start = 0x40 + 4 * count      # 偏移表之后才是记录区
    data[record_start + 8] = 0xFF        # 首条记录 +0x08 保留字节
    path = tmp_path / 'dirty_entry.dat'
    path.write_bytes(bytes(data))

    report = DatValidator().validate(str(path))
    codes = {issue.code for issue in report.issues}
    assert 'dirty_entry_reserved' in codes
    issue = next(i for i in report.issues if i.code == 'dirty_entry_reserved')
    assert issue.severity == 'error'


def test_validator_flags_nonzero_timestamp_high_word(tmp_path):
    from src.validator import DatValidator

    data = bytearray(_build_sample())
    data[0x24] = 0x01          # u64 时间戳高位
    path = tmp_path / 'dirty_ts.dat'
    path.write_bytes(bytes(data))

    report = DatValidator().validate(str(path))
    codes = {issue.code for issue in report.issues}
    assert 'dirty_timestamp_high' in codes


def test_clean_sample_has_no_fixed_field_issues(tmp_path):
    from src.validator import DatValidator

    path = tmp_path / 'clean.dat'
    path.write_bytes(_build_sample())
    report = DatValidator().validate(str(path))
    codes = {issue.code for issue in report.issues}
    assert 'dirty_reserved' not in codes
    assert 'dirty_entry_reserved' not in codes
    assert 'dirty_timestamp_high' not in codes
    assert report.exit_code == 0


# --------------------------------------------------------------------------
# 任务 5：高危操作必须有备份指引（恢复教程已迁到 docs/RECOVERY.md）
# --------------------------------------------------------------------------

def test_recovery_doc_requires_backup_before_deletion():
    text = (ROOT / 'docs' / 'RECOVERY.md').read_text(encoding='utf-8')
    assert '第 0 步：必须先备份' in text
    assert 'msp-backup' in text
    assert 'xcopy' in text
    # 删除动作必须出现在备份步骤之后
    backup_at = text.index('msp-backup')
    delete_at = text.index('第 2 步：清理异常词库文件')
    assert backup_at < delete_at
    # 备份章节之前必须有醒目的高危警告
    warning_at = text.index('严重警告')
    assert warning_at < backup_at
    # 必须写明哪些文件会被删掉、删掉的后果，以及回滚方式
    for token in ('ChsPinyinUDP.lex', 'ChsPinyinEUDL.dat', 'ChsPinyinUDL.dat',
                  '自学习', '回滚'):
        assert token in text, f'恢复指引缺少 {token}'
    # 禁止建议删掉整个 InputMethod 目录
    assert '绝对不要删除整个 `InputMethod` 目录' in text


def test_readme_links_to_recovery_instead_of_inlining_it():
    """README 保持极简：只留一句警告 + 一个链接，不内联恢复步骤。"""
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert 'docs/RECOVERY.md' in readme
    # 备份命令与逐文件删除表必须待在 RECOVERY.md，不能回到 README
    for inlined in ('xcopy', 'msp-backup', '第 2 步：清理异常词库文件'):
        assert inlined not in readme, f'README 又内联了恢复细节: {inlined}'
    # 但仍要保留「先备份、再动手」的提醒
    assert '备份' in readme


def test_readme_links_to_development_instead_of_inlining_it():
    """开发者内容（安装/脚本参数/格式）必须外链到 docs/DEVELOPMENT.md。"""
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert 'docs/DEVELOPMENT.md' in readme
    for inlined in ('pip install', '--with-canary', 'download_frost.py'):
        assert inlined not in readme, f'README 又内联了开发者内容: {inlined}'


@pytest.mark.parametrize('relative', ['README.md', 'docs/DEVELOPMENT.md',
                                      'docs/RECOVERY.md',
                                      'docs/CANARY_TESTING.md',
                                      'docs/ISSUE3_DIAGNOSIS.md'])
def test_docs_relative_links_resolve(relative):
    import re
    doc = ROOT / relative
    text = doc.read_text(encoding='utf-8')
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if target.startswith(('http://', 'https://', '#', 'mailto:')):
            continue
        path = target.split('#')[0]
        if path:
            assert (doc.parent / path).exists(), f'{relative} -> {target}'


# --------------------------------------------------------------------------
# 任务 1：扩展源按「基础源单字热度」排序
# --------------------------------------------------------------------------

def test_build_char_weight_accumulates_log_frequency():
    entries = [('中国', 'zhong guo', 1000, 'base'), ('中', 'zhong', 10, 'base')]
    weight = merge_mod.build_char_weight([entries])

    import math
    assert weight['中'] == pytest.approx(math.log1p(1000) + math.log1p(10))
    assert weight['国'] == pytest.approx(math.log1p(1000))
    assert 'x' not in weight


def test_build_char_weight_ignores_non_basic_cjk():
    entries = [('㐵作', 'a zuo', 500, 'base')]   # CJK 扩展 A 区
    weight = merge_mod.build_char_weight([entries])

    assert '㐵' not in weight
    assert weight['作'] == pytest.approx(math.log1p(500))


def test_extended_score_puts_rare_char_words_last():
    """含生僻字（基础源里从没出现过的字）的词条必须垫底，但不删除。"""
    char_weight = {'明': 100.0, '日': 100.0, '方': 100.0, '舟': 100.0, '菇': 0.0}

    good = merge_mod.extended_score('明日方舟', char_weight)
    bad = merge_mod.extended_score('香菇', char_weight)

    assert good[0] > merge_mod.INVALID_SCORE
    assert bad[0] == merge_mod.INVALID_SCORE


def test_extended_score_zeroes_outside_basic_cjk():
    """CJK 扩展区的字（U+4E00 之外）直接垫底。"""
    char_weight = {'作': 50.0}
    assert merge_mod.extended_score('㐵作', char_weight)[0] == merge_mod.INVALID_SCORE


def test_extended_score_uses_min_char_weight_as_tiebreaker():
    """木桶效应：最小字权重作为次分，罕见字会把整词拉到后面。"""
    char_weight = {'明': 100.0, '日': 100.0, '天': 1.0}
    score = merge_mod.extended_score('明天', char_weight)

    assert score[1] == pytest.approx(1.0)     # min(100, 1)
    assert score[0] > merge_mod.INVALID_SCORE


def test_extended_score_prefers_two_to_four_char_words():
    """词长系数让 2~3 字优先于 4 字，4 字优先于更长。"""
    char_weight = {c: 100.0 for c in '一二三四五六'}
    two = merge_mod.extended_score('一二', char_weight)
    four = merge_mod.extended_score('一二三四', char_weight)
    six = merge_mod.extended_score('一二三四五六', char_weight)

    assert two[0] >= four[0] > six[0]


def test_merge_extended_orders_by_score_not_unicode():
    """扩展源排序必须按质量打分，而不是 Unicode 码点升序。"""
    char_weight = {'明': 500.0, '日': 500.0, '方': 500.0, '舟': 500.0,
                   '㐵': 0.0, '作': 0.0}
    base = [('基础', 'ji chu', 10, 'base')]
    ext = [
        ('㐵作', 'a zuo', 1, 'wiki'),      # 码点最靠前，但含生僻字 → 应垫底
        ('明日方舟', 'ming ri fang zhou', 1, 'wiki'),
    ]

    merged = merge_mod.merge_extended(base, ext, char_weight)

    assert [w for w, _, _, _ in merged] == ['基础', '明日方舟', '㐵作']


def test_bigram_model_prefers_real_words_over_fragments():
    """二元语法模型要能区分「成词」与「不成词」。

    「中国」在基础源里高频且共现，「人一」只是两个高频字的拼接、不成词。
    只看单字权重时两者分数一样（都是最热的字），必须靠二元语法拉开差距。
    """
    base_entries = [[
        ('中国', 'zhong guo', 100000, 'base'),
        ('国人', 'guo ren', 50000, 'base'),
        ('人民', 'ren min', 50000, 'base'),
        ('一生', 'yi sheng', 20000, 'base'),
    ]]
    model = merge_mod.build_bigram_model(base_entries)
    char_weight = merge_mod.build_char_weight(base_entries)

    real = merge_mod.extended_score('中国', char_weight, model)
    fragment = merge_mod.extended_score('人一', char_weight, model)

    assert real[0] > fragment[0]
    assert fragment[0] > merge_mod.INVALID_SCORE


def test_bigram_model_is_length_normalised():
    """主分是「平均每字的 log 概率」，长词不会因为字多而系统性吃亏。"""
    base_entries = [[('中国', 'zhong guo', 1000, 'base'),
                     ('国人', 'guo ren', 1000, 'base'),
                     ('人民', 'ren min', 1000, 'base')]]
    model = merge_mod.build_bigram_model(base_entries)
    char_weight = merge_mod.build_char_weight(base_entries)

    two = merge_mod.extended_score('中国', char_weight, model)
    four = merge_mod.extended_score('中国人民', char_weight, model)

    assert four[0] > merge_mod.INVALID_SCORE
    assert abs(two[0] - four[0]) < 1.0     # 同一批字符，均值应当接近


def test_merge_extended_uses_bigram_model_when_provided():
    """传入 bigram 时排序应按二元语法分数，而不是单字权重。"""
    base_entries = [[
        ('中国', 'zhong guo', 100000, 'base'),
        ('国人', 'guo ren', 50000, 'base'),
    ]]
    char_weight = merge_mod.build_char_weight(base_entries)
    model = merge_mod.build_bigram_model(base_entries)
    base = [('基础', 'ji chu', 10, 'base'),
            ('中国', 'zhong guo', 100000, 'base')]
    ext = [
        ('中国', 'zhong guo', 1, 'wiki'),            # 与基础源同读音 → 会被去重
        ('一人', 'yi ren', 1, 'wiki'),
        ('中国国', 'zhong guo guo', 1, 'wiki'),
    ]

    merged = merge_mod.merge_extended(base, ext, char_weight, model)
    # '中国' 只应保留基础源那一条，扩展源的同读音被去重
    assert [row for row in merged if row[0] == '中国'] == [
        ('中国', 'zhong guo', 100000, 'base')]
    assert '中国国' in [w for w, _, _, _ in merged]
    # 成词的「中国国」应排在不成词的「一人」前面
    words = [w for w, _, _, _ in merged]
    assert words.index('中国国') < words.index('一人')


def test_merge_extended_is_deterministic_for_equal_scores():
    base = [('基础', 'ji chu', 10, 'base')]
    ext = [('长城', 'chang cheng', 5, 'wiki'), ('国内', 'gui nei', 5, 'wiki')]

    first = merge_mod.merge_extended(base, ext, {})
    second = merge_mod.merge_extended(base, list(reversed(ext)), {})

    assert first == second


def test_merge_extended_penalises_pinyin_already_covered_by_base():
    """同拼音的基础词条已经把候选位占满时，扩展词应排到后面。

    候选位上限是 9，基础源同拼音词条先占位，这类扩展词在输入法里根本
    轮不到显示，留着只是浪费 lite/standard 的配额。

    两条扩展词用同一个词（因此基础分完全相同），只有拼音不同：
    'jia yi' 已被基础源占用，'jia yi er' 没有，惩罚项应该只影响前者。
    """
    base = [('甲乙风', 'jia yi feng', 100, 'base'), ('丙丁', 'bing ding', 50, 'base')]
    base += [(f'加意{i}', 'jia yi', 90 - i, 'base') for i in range(5)]
    ext = [('甲乙', 'jia yi', 1, 'wiki'), ('甲乙', 'jia yi er', 1, 'wiki')]
    char_weight = merge_mod.build_char_weight([base])
    model = merge_mod.build_bigram_model([base])

    merged = merge_mod.merge_extended(base, ext, char_weight, model)
    rows = [(row[0], row[1]) for row in merged if row[0] == '甲乙']

    assert rows == [('甲乙', 'jia yi er'), ('甲乙', 'jia yi')]


def test_merge_extended_penalty_is_zero_without_base_competition():
    """基础源没有同拼音词条时，不产生竞争惩罚，排序仍由基础分决定。"""
    base = [('甲乙风', 'jia yi feng', 100, 'base')]
    ext = [('甲乙', 'jia yi', 1, 'wiki')]
    char_weight = merge_mod.build_char_weight([base])
    model = merge_mod.build_bigram_model([base])

    merged = merge_mod.merge_extended(base, ext, char_weight, model)

    assert ('甲乙', 'jia yi', 1, 'wiki') in merged


def test_merge_extended_penalty_factor_is_positive():
    """惩罚系数必须为正，否则等于没做竞争抑制。"""
    assert merge_mod.PY_SATURATION_PENALTY > 0
