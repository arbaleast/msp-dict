"""Canary 诊断构建与物理偏移校验测试。

覆盖：
1. 正式产物 0 探针，且不会被 --with-canary 覆盖；
2. Canary 产物精确包含探针，总数不突破 Profile 上限；
3. 探针不被去重逻辑误删，Offset Table 仍单调、Rank 仍合法；
4. 篡改字节 / 缺失探针 / 改 Rank / SHA256 不符时 check-canary 准确拦截；
5. 相同输入重复构建满足二进制确定性。
"""

import json
import os
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.builder_win10 import Win10MSPinyinBuilder  # noqa: E402
from src.canary import (  # noqa: E402
    CANARY_SOURCE_RANK,
    DEFAULT_PROBES,
    CanaryProbe,
    build_manifest,
    locate_probes,
    resolve_probes,
)
from src.format_spec import (  # noqa: E402
    ENTRY_HANZI_OFFSET_BASE,
    ENTRY_HEAD_BASE,
    ENTRY_MAGIC,
    OFF_PHRASE_COUNT,
    OFF_PHRASE_START,
    PHRASE_OFFSET_START,
)
from src.validator import CanaryChecker  # noqa: E402


def run_cli(*args):
    env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
    return subprocess.run(
        [sys.executable, '-m', 'src.cli', *args],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8', env=env,
    )


def write_source(path, rows):
    """写 TSV 源文件：词条\\t拼音\\t词频（按词频降序）。"""
    with open(path, 'w', encoding='utf-8') as f:
        for word, code, freq in rows:
            f.write(f'{word}\t{code}\t{freq}\n')
    return path


def sample_rows(count=300):
    """构造一批互不冲突的词条（拼音唯一，避免同音候选位互相挤占）。"""
    rows = []
    for i in range(count):
        rows.append((f'词{i}', f'ci{i}', 100000 - i))
    return rows


def read_records(data):
    """按物理顺序解析记录，返回 [(index, byte_offset, code, word, position)]。"""
    count = struct.unpack_from('<I', data, OFF_PHRASE_COUNT)[0]
    phrase_start = struct.unpack_from('<I', data, OFF_PHRASE_START)[0]
    offsets = [struct.unpack_from('<I', data, PHRASE_OFFSET_START + i * 4)[0]
               for i in range(count)]
    records = []
    for index, offset in enumerate(offsets):
        start = phrase_start + offset
        hanzi_offset = struct.unpack_from('<H', data, start + 4)[0]
        position = data[start + 6]
        code = data[start + ENTRY_HEAD_BASE:start + hanzi_offset - 2].decode('utf-16-le')
        records.append((index, start, code, position))
    return records, offsets


# ----------------------------------------------------------------------
class TestCanaryBuild:
    def test_normal_build_contains_no_probe(self, tmp_path):
        source = write_source(tmp_path / "src.txt", sample_rows(50))
        output = tmp_path / "msp_lite.dat"

        result = run_cli('build', str(source), '-o', str(output), '--profile', 'lite',
                         '--timestamp', '1600000000')

        assert result.returncode == 0
        data = output.read_bytes()
        words = data.decode('utf-16-le', errors='ignore')
        for probe in DEFAULT_PROBES:
            assert probe.pinyin not in words
            assert probe.word not in words
        assert not (tmp_path / "msp_lite.json").exists()

    def test_with_canary_does_not_touch_normal_product(self, tmp_path):
        source = write_source(tmp_path / "src.txt", sample_rows(50))
        normal = tmp_path / "msp_lite.dat"

        assert run_cli('build', str(source), '-o', str(normal), '--profile', 'lite',
                       '--timestamp', '1600000000').returncode == 0
        before = normal.read_bytes()

        canary = tmp_path / "msp_lite_canary.dat"
        result = run_cli('build', str(source), '-o', str(canary), '--profile', 'lite',
                         '--with-canary', '--timestamp', '1600000000')

        assert result.returncode == 0
        assert canary.exists()
        # 正式产物字节不变
        assert normal.read_bytes() == before
        assert normal.read_bytes() != canary.read_bytes()

    def test_canary_contains_exactly_the_probes(self, tmp_path):
        source = write_source(tmp_path / "src.txt", sample_rows(50))
        canary = tmp_path / "msp_lite_canary.dat"
        manifest_path = tmp_path / "msp_lite_canary.json"

        result = run_cli('build', str(source), '-o', str(canary), '--profile', 'lite',
                         '--with-canary', '--timestamp', '1600000000')

        assert result.returncode == 0
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))

        assert manifest['canary_entry_count'] == 2
        assert manifest['total_entry_count'] == manifest['normal_entry_count'] + 2
        assert {p['pinyin'] for p in manifest['probes']} == {'cikutanzhen', 'zuiweitan'}

        located = locate_probes(canary.read_bytes(), list(DEFAULT_PROBES))
        assert all(item['found'] for item in located)
        # 探针拿到候选位 1
        assert all(item['rank'] == 1 for item in located)

    def test_canary_respects_profile_limit(self, tmp_path):
        source = write_source(tmp_path / "src.txt", sample_rows(500))
        canary = tmp_path / "msp_lite_canary.dat"

        assert run_cli('build', str(source), '-o', str(canary), '--profile', 'lite',
                       '--with-canary', '--timestamp', '1600000000').returncode == 0

        manifest = json.loads(
            (tmp_path / "msp_lite_canary.json").read_text(encoding='utf-8'))
        assert manifest['total_entry_count'] <= 20000

    def test_probes_survive_dedup_and_keep_offsets_monotonic(self, tmp_path):
        """探针与普通词条同拼音时也不能被去重/候选位逻辑误删。"""
        source = write_source(tmp_path / "src.txt", [
            ('普通词', 'cikutanzhen', 5000),
            ('另一个词', 'cikutanzhen', 4000),
            ('普通尾词', 'zuiweitan', 3000),
        ])
        canary = tmp_path / "msp_lite_canary.dat"

        assert run_cli('build', str(source), '-o', str(canary), '--profile', 'lite',
                       '--with-canary', '--timestamp', '1600000000').returncode == 0

        data = canary.read_bytes()
        records, offsets = read_records(data)

        # Offset Table 严格单调递增
        assert offsets == sorted(offsets)
        assert len(set(offsets)) == len(offsets)
        # 候选位全部合法
        assert all(1 <= r[3] <= 9 for r in records)
        # 探针都在，且拿到候选位 1（词频极大值 → 同拼音排第一）
        located = locate_probes(data, list(DEFAULT_PROBES))
        assert all(item['found'] for item in located)
        assert all(item['rank'] == 1 for item in located)

    def test_repeated_build_is_binary_deterministic(self, tmp_path):
        source = write_source(tmp_path / "src.txt", sample_rows(120))
        first = tmp_path / "a_canary.dat"
        second = tmp_path / "b_canary.dat"

        for output in (first, second):
            assert run_cli('build', str(source), '-o', str(output), '--profile', 'lite',
                           '--with-canary', '--timestamp', '1600000000').returncode == 0

        assert first.read_bytes() == second.read_bytes()

    def test_custom_probes_are_supported(self, tmp_path):
        source = write_source(tmp_path / "src.txt", sample_rows(20))
        canary = tmp_path / "c_canary.dat"

        result = run_cli('build', str(source), '-o', str(canary), '--profile', 'lite',
                         '--with-canary',
                         '--canary-pinyin', 'ceshitandou',
                         '--canary-word', '测试探针词',
                         '--timestamp', '1600000000')

        assert result.returncode == 0
        manifest = json.loads(
            (tmp_path / "c_canary.json").read_text(encoding='utf-8'))
        assert manifest['probes'][0]['pinyin'] == 'ceshitandou'
        assert manifest['probes'][0]['word'] == '测试探针词'

    def test_mismatched_probe_arguments_are_rejected(self, tmp_path):
        source = write_source(tmp_path / "src.txt", sample_rows(20))

        result = run_cli('build', str(source), '-o', str(tmp_path / "x.dat"),
                         '--profile', 'lite', '--with-canary',
                         '--canary-pinyin', 'abc')

        assert result.returncode == 2
        assert '成对' in result.stdout


# ----------------------------------------------------------------------
class TestCheckCanary:
    def _build(self, tmp_path):
        source = write_source(tmp_path / "src.txt", sample_rows(80))
        canary = tmp_path / "msp_lite_canary.dat"
        assert run_cli('build', str(source), '-o', str(canary), '--profile', 'lite',
                       '--with-canary', '--timestamp', '1600000000').returncode == 0
        manifest_path = tmp_path / "msp_lite_canary.json"
        return canary, manifest_path

    def test_all_auto_dimensions_pass(self, tmp_path):
        canary, manifest_path = self._build(tmp_path)

        report = CanaryChecker().check(str(canary), str(manifest_path))

        assert report.dimension('STRUCT').status == 'PASS'
        assert report.dimension('CANARY').status == 'PASS'
        assert report.dimension('MANIFEST').status == 'PASS'
        # Windows 维度必须保持「待实机验证」，不能被 Python 校验顶替
        assert report.dimension('WINDOWS').status == 'PENDING'
        assert report.exit_code == 0
        assert '不代表 Windows' in report.dimension('WINDOWS').detail

    def test_cli_exit_zero_and_reports_four_dimensions(self, tmp_path):
        canary, manifest_path = self._build(tmp_path)

        result = run_cli('check-canary', str(canary), '--manifest', str(manifest_path))

        assert result.returncode == 0
        for dim in ('[STRUCT]', '[CANARY]', '[MANIFEST]', '[WINDOWS]'):
            assert dim in result.stdout

    def test_tampered_bytes_fail_manifest_dimension(self, tmp_path):
        canary, manifest_path = self._build(tmp_path)

        data = bytearray(canary.read_bytes())
        data[-1] ^= 0xFF          # 改最后一个字节 → SHA256 变化
        canary.write_bytes(bytes(data))

        report = CanaryChecker().check(str(canary), str(manifest_path))

        assert report.dimension('MANIFEST').status == 'FAIL'
        assert report.exit_code == 1

    def test_missing_probe_is_detected(self, tmp_path):
        canary, manifest_path = self._build(tmp_path)

        # 用不含探针的文件冒充
        builder = Win10MSPinyinBuilder(timestamp=1600000000)
        builder.add_word('普通词', 'putongci', 100)
        canary.write_bytes(builder.build())

        report = CanaryChecker().check(str(canary), str(manifest_path))

        assert report.dimension('CANARY').status == 'FAIL'
        assert report.exit_code == 1

    def test_manifest_rank_mismatch_is_detected(self, tmp_path):
        canary, manifest_path = self._build(tmp_path)

        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['probes'][0]['rank'] = 7
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')

        report = CanaryChecker().check(str(canary), str(manifest_path))

        assert report.dimension('CANARY').status == 'FAIL'
        assert report.exit_code == 1

    def test_manifest_offset_mismatch_is_detected(self, tmp_path):
        canary, manifest_path = self._build(tmp_path)

        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['probes'][0]['byte_offset'] += 16
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')

        report = CanaryChecker().check(str(canary), str(manifest_path))

        assert report.dimension('CANARY').status == 'FAIL'

    def test_missing_manifest_fails_manifest_dimension(self, tmp_path):
        canary, _ = self._build(tmp_path)

        report = CanaryChecker().check(str(canary), str(tmp_path / "nope.json"))

        assert report.dimension('MANIFEST').status == 'FAIL'
        assert report.exit_code == 1

    def test_json_output_shape(self, tmp_path):
        canary, manifest_path = self._build(tmp_path)

        result = run_cli('check-canary', str(canary), '--manifest', str(manifest_path),
                         '--json')

        payload = json.loads(result.stdout)
        assert payload['ok'] is True
        assert [d['name'] for d in payload['dimensions']] == [
            'STRUCT', 'CANARY', 'MANIFEST', 'WINDOWS']


# ----------------------------------------------------------------------
class TestCanaryHelpers:
    def test_resolve_probes_defaults(self):
        probes = resolve_probes(None, None)

        assert len(probes) == len(DEFAULT_PROBES)
        assert probes[0].pinyin == 'cikutanzhen'
        assert probes[1].pinyin == 'zuiweitan'

    def test_resolve_probes_normalizes_and_validates(self):
        probes = resolve_probes(['  CI KU TAN ZHEN '], [' 探针词 '])

        assert probes[0].pinyin == 'ciku tanzhen'.replace(' ', '')
        assert probes[0].word == '探针词'

    def test_resolve_probes_rejects_invalid_pinyin(self):
        try:
            resolve_probes(['ci1'], ['词'])
        except ValueError as exc:
            assert '非法' in str(exc)
        else:
            assert False, '非法拼音应被拒绝'

    def test_manifest_counts_follow_the_file(self, tmp_path):
        source = write_source(tmp_path / "src.txt", sample_rows(30))
        canary = tmp_path / "c.dat"
        builder = Win10MSPinyinBuilder(timestamp=1600000000)
        builder.add_word('普通词', 'putongci', 100)
        for probe in DEFAULT_PROBES:
            builder.add_word(probe.word, probe.pinyin, CANARY_SOURCE_RANK)
        data = builder.build()
        canary.write_bytes(data)

        located = locate_probes(data, list(DEFAULT_PROBES))
        manifest = build_manifest(profile='lite', dat_path=canary, data=data,
                                  selected_entry_count=31, located=located)

        assert manifest['total_entry_count'] == 3
        assert manifest['canary_entry_count'] == 2
        assert manifest['normal_entry_count'] == 1


# ----------------------------------------------------------------------
class TestCanaryOnlyReleaseMode:
    """scripts/build_releases.py --canary-only：只产探针文件，不碰正式产物。"""

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, 'scripts/build_releases.py', *args],
            cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
            env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'},
        )

    def test_canary_only_does_not_touch_formal_products(self, tmp_path):
        source = write_source(tmp_path / "src.txt", sample_rows(40))
        out = tmp_path / "dist"

        formal = self._run('--input', str(source), '--output-dir', str(out),
                            '--profiles', 'lite', '--timestamp', '1600000000')
        assert formal.returncode == 0
        before = (out / "msp_lite.dat").read_bytes()
        summary_before = (out / "build_summary.json").read_text(encoding='utf-8')

        canary = self._run('--input', str(source), '--output-dir', str(out),
                           '--profiles', 'lite', '--with-canary', '--canary-only',
                           '--summary', 'build_summary_canary.json',
                           '--timestamp', '1600000000')
        assert canary.returncode == 0

        # 正式产物与正式摘要都没被改写
        assert (out / "msp_lite.dat").read_bytes() == before
        assert (out / "build_summary.json").read_text(encoding='utf-8') == summary_before
        # 探针产物独立存在
        assert (out / "msp_lite_canary.dat").exists()
        assert (out / "msp_lite_canary.json").exists()
        assert (out / "build_summary_canary.json").exists()

    def test_canary_only_requires_with_canary(self, tmp_path):
        source = write_source(tmp_path / "src.txt", sample_rows(10))

        result = self._run('--input', str(source), '--output-dir', str(tmp_path / "d"),
                            '--canary-only')

        assert result.returncode == 1
        assert '--with-canary' in result.stderr
