"""Canary Manifest 严格校验的边界测试。

manifest 来自外部（用户自建 / CI 产物），结构可能完全不可信：
顶层是数组/字符串/null、字段缺失、类型错误、计数不自洽……
任何一种都必须让校验器稳定返回 FAIL，**不能抛出未捕获异常**。
"""

import json

import pytest

from src.canary import MANIFEST_FORMAT, validate_manifest_schema
from src.validator import CanaryChecker


def _valid_manifest(dat_path):
    """用真实构建产物生成一份合法 manifest（保证测试基准是真实数据）。"""
    from src.builder_win10 import Win10MSPinyinBuilder
    from src.canary import build_manifest, locate_probes, CanaryProbe

    builder = Win10MSPinyinBuilder(timestamp=1700000000)
    builder.add_word('中国', 'zhongguo', 100)
    builder.add_word('北京', 'beijing', 50)
    builder.add_word('词库探针已生效', 'cikutanzhen', 2 ** 31 - 1)
    data = builder.build()

    located = locate_probes(data, [CanaryProbe('cikutanzhen', '词库探针已生效')])
    manifest = build_manifest(
        profile='lite', dat_path=dat_path, data=data,
        selected_entry_count=3, located=located)
    return data, manifest


@pytest.fixture()
def sample(tmp_path):
    dat_path = tmp_path / 'probe.dat'
    data, manifest = _valid_manifest(dat_path)
    dat_path.write_bytes(data)
    manifest_path = tmp_path / 'probe.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
    return dat_path, manifest_path, manifest


def _dimension(report, name):
    for dim in report.dimensions:
        if dim.name == name:
            return dim
    raise AssertionError(f'报告里没有 {name} 维度: {[d.name for d in report.dimensions]}')


def _write(tmp_path, payload):
    path = tmp_path / 'broken.json'
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    return path


# --------------------------------------------------------------------------
# schema 层：validate_manifest_schema
# --------------------------------------------------------------------------

@pytest.mark.parametrize('payload', [
    [],
    ['a'],
    'not-an-object',
    42,
    None,
    True,
])
def test_schema_rejects_non_object_top_level(payload):
    errors = validate_manifest_schema(payload)
    assert errors
    assert '顶层必须是 JSON 对象' in errors[0]


def test_schema_accepts_valid_manifest(sample):
    _, _, manifest = sample
    assert validate_manifest_schema(manifest) == []


@pytest.mark.parametrize('field', [
    'format', 'sha256', 'file_size',
    'normal_entry_count', 'canary_entry_count', 'total_entry_count', 'probes',
])
def test_schema_requires_every_field(sample, field):
    _, _, manifest = sample
    broken = {k: v for k, v in manifest.items() if k != field}
    errors = validate_manifest_schema(broken)
    assert any(f'缺少必填字段: {field}' in e for e in errors), errors


def test_schema_rejects_wrong_format(sample):
    _, _, manifest = sample
    broken = dict(manifest, format='msp-dict-canary-manifest/999')
    errors = validate_manifest_schema(broken)
    assert any('format 不正确' in e for e in errors)


@pytest.mark.parametrize('bad_sha', [
    'abc', '', 'Z' * 64, 'g' * 64, 12345,
])
def test_schema_rejects_bad_sha_format(sample, bad_sha):
    _, _, manifest = sample
    broken = dict(manifest, sha256=bad_sha)
    errors = validate_manifest_schema(broken)
    assert any('sha256' in e for e in errors), errors


@pytest.mark.parametrize('bad_size', ['big', -1, 1.5, True])
def test_schema_rejects_bad_file_size(sample, bad_size):
    _, _, manifest = sample
    broken = dict(manifest, file_size=bad_size)
    errors = validate_manifest_schema(broken)
    assert any('file_size' in e for e in errors), errors


def test_schema_rejects_inconsistent_counts(sample):
    _, _, manifest = sample
    broken = dict(manifest, normal_entry_count=manifest['normal_entry_count'] + 5)
    errors = validate_manifest_schema(broken)
    assert any('计数不自洽' in e for e in errors), errors


def test_schema_rejects_non_int_counts(sample):
    _, _, manifest = sample
    broken = dict(manifest, total_entry_count='many')
    errors = validate_manifest_schema(broken)
    assert any('total_entry_count 必须是非负整数' in e for e in errors), errors


@pytest.mark.parametrize('bad_probes', [
    'not-a-list', 123, {'pinyin': 'x'}, [1, 2, 3], ['x'],
])
def test_schema_rejects_bad_probes_structure(sample, bad_probes):
    _, _, manifest = sample
    broken = dict(manifest, probes=bad_probes)
    errors = validate_manifest_schema(broken)
    assert any('probes' in e for e in errors), errors


@pytest.mark.parametrize('missing_field', [
    'pinyin', 'word', 'rank', 'physical_index', 'byte_offset',
])
def test_schema_rejects_probe_missing_field(sample, missing_field):
    _, _, manifest = sample
    probe = dict(manifest['probes'][0])
    probe.pop(missing_field)
    broken = dict(manifest, probes=[probe])
    errors = validate_manifest_schema(broken)
    assert any(missing_field in e for e in errors), errors


# --------------------------------------------------------------------------
# 校验器层：畸形 manifest 不得让程序崩溃
# --------------------------------------------------------------------------

@pytest.mark.parametrize('payload', [
    [],
    ['probe'],
    'text',
    None,
    123,
])
def test_check_canary_survives_non_object_manifest(sample, tmp_path, payload):
    dat_path, _, _ = sample
    manifest_path = _write(tmp_path, payload)

    report = CanaryChecker().check(str(dat_path), str(manifest_path))

    manifest_dim = _dimension(report, 'MANIFEST')
    assert manifest_dim.status == 'FAIL'
    assert '顶层必须是 JSON 对象' in ' '.join(manifest_dim.lines)


def test_check_canary_survives_probe_as_string(sample, tmp_path):
    dat_path, _, manifest = sample
    manifest_path = _write(tmp_path, dict(manifest, probes='oops'))

    report = CanaryChecker().check(str(dat_path), str(manifest_path))

    assert _dimension(report, 'MANIFEST').status == 'FAIL'
    assert _dimension(report, 'CANARY').status == 'FAIL'


def test_check_canary_survives_probe_element_not_dict(sample, tmp_path):
    dat_path, _, manifest = sample
    manifest_path = _write(tmp_path, dict(manifest, probes=[1, 2]))

    report = CanaryChecker().check(str(dat_path), str(manifest_path))

    assert _dimension(report, 'MANIFEST').status == 'FAIL'


def test_check_canary_survives_string_counts(sample, tmp_path):
    dat_path, _, manifest = sample
    manifest_path = _write(tmp_path, dict(manifest, total_entry_count='3'))

    report = CanaryChecker().check(str(dat_path), str(manifest_path))

    assert _dimension(report, 'MANIFEST').status == 'FAIL'


def test_check_canary_detects_sha_mismatch(sample, tmp_path):
    dat_path, _, manifest = sample
    manifest_path = _write(tmp_path, dict(manifest, sha256='0' * 64))

    report = CanaryChecker().check(str(dat_path), str(manifest_path))

    dim = _dimension(report, 'MANIFEST')
    assert dim.status == 'FAIL'
    assert any('SHA256 不匹配' in d for d in dim.lines)


def test_check_canary_detects_size_mismatch(sample, tmp_path):
    dat_path, _, manifest = sample
    manifest_path = _write(tmp_path, dict(manifest, file_size=manifest['file_size'] + 1))

    report = CanaryChecker().check(str(dat_path), str(manifest_path))

    dim = _dimension(report, 'MANIFEST')
    assert dim.status == 'FAIL'
    assert any('文件大小不符' in d for d in dim.lines)


def test_check_canary_detects_count_mismatch(sample, tmp_path):
    dat_path, _, manifest = sample
    broken = dict(manifest)
    broken['normal_entry_count'] = manifest['normal_entry_count'] + 1
    broken['total_entry_count'] = manifest['total_entry_count'] + 1
    manifest_path = _write(tmp_path, broken)

    report = CanaryChecker().check(str(dat_path), str(manifest_path))

    dim = _dimension(report, 'MANIFEST')
    assert dim.status == 'FAIL'
    assert any('词条总数不符' in d for d in dim.lines)


def test_check_canary_detects_missing_sha(sample, tmp_path):
    dat_path, _, manifest = sample
    broken = {k: v for k, v in manifest.items() if k != 'sha256'}
    manifest_path = _write(tmp_path, broken)

    report = CanaryChecker().check(str(dat_path), str(manifest_path))

    dim = _dimension(report, 'MANIFEST')
    assert dim.status == 'FAIL'
    assert any('缺少必填字段: sha256' in d for d in dim.lines)


def test_check_canary_reports_missing_manifest(sample):
    dat_path, _, _ = sample

    report = CanaryChecker().check(str(dat_path), str(dat_path.parent / 'nope.json'))

    assert _dimension(report, 'MANIFEST').status == 'FAIL'
    assert _dimension(report, 'CANARY').status == 'FAIL'


def test_check_canary_reports_corrupt_json(sample, tmp_path):
    dat_path, _, _ = sample
    manifest_path = tmp_path / 'broken.json'
    manifest_path.write_text('{not json', encoding='utf-8')

    report = CanaryChecker().check(str(dat_path), str(manifest_path))

    assert _dimension(report, 'MANIFEST').status == 'FAIL'


def test_valid_manifest_passes_all_dimensions(sample):
    dat_path, manifest_path, _ = sample

    report = CanaryChecker().check(str(dat_path), str(manifest_path))

    assert _dimension(report, 'STRUCT').status == 'PASS'
    assert _dimension(report, 'CANARY').status == 'PASS'
    assert _dimension(report, 'MANIFEST').status == 'PASS'
    assert _dimension(report, 'WINDOWS').status == 'PENDING'
    assert report.ok
