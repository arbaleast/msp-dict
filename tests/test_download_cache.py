"""下载缓存的原子性与脚本参数一致性测试。

要求：
- 下载必须先写 .part，校验通过才原子重命名；
- 中断/失败不得留下残片，也不得破坏已有完整缓存；
- 0 字节的残片缓存必须被识别为无效并重新下载；
- 脚本之间打印的命令提示必须与真实 argparse 参数一致。
"""

import argparse
import importlib.util
import sys
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


download_frost = _load('download_frost_script', 'scripts/download_frost.py')
merge_script = _load('merge_script', 'scripts/merge.py')


# --------------------------------------------------------------------------
# download_frost：原子下载
# --------------------------------------------------------------------------

def test_download_one_uses_part_file_then_renames(tmp_path, monkeypatch):
    """成功下载：先写 .part，再原子重命名成正式文件。"""
    target = tmp_path / 'word.txt'
    seen = {}

    def fake_urlretrieve(url, filename):
        seen['path'] = Path(filename)
        Path(filename).write_bytes(b'x' * 100)

    monkeypatch.setattr(download_frost.urllib.request, 'urlretrieve', fake_urlretrieve)

    assert download_frost.download_one('http://example/x', target, retries=1) is True
    assert target.exists()
    assert target.read_bytes() == b'x' * 100
    # 下载期间落在 .part 上
    assert seen['path'].name == 'word.txt.part'
    # 完成后 .part 不应残留
    assert not (tmp_path / 'word.txt.part').exists()


def test_download_one_cleans_part_on_failure(tmp_path, monkeypatch):
    """下载抛异常：不能留下 .part 残片，也不能生成正式文件。"""
    target = tmp_path / 'word.txt'

    def boom(url, filename):
        Path(filename).write_bytes(b'partial')
        raise OSError('connection reset')

    monkeypatch.setattr(download_frost.urllib.request, 'urlretrieve', boom)
    monkeypatch.setattr(download_frost.time, 'sleep', lambda _s: None)

    assert download_frost.download_one('http://example/x', target, retries=2) is False
    assert not target.exists()
    assert not (tmp_path / 'word.txt.part').exists()


def test_download_one_rejects_empty_result(tmp_path, monkeypatch):
    target = tmp_path / 'word.txt'

    def empty(url, filename):
        Path(filename).write_bytes(b'')

    monkeypatch.setattr(download_frost.urllib.request, 'urlretrieve', empty)
    monkeypatch.setattr(download_frost.time, 'sleep', lambda _s: None)

    assert download_frost.download_one('http://example/x', target, retries=1) is False
    assert not target.exists()
    assert not (tmp_path / 'word.txt.part').exists()


def test_download_one_keeps_existing_cache_on_failure(tmp_path, monkeypatch):
    """重新下载失败时，原有的完整缓存不能被破坏。"""
    target = tmp_path / 'word.txt'
    target.write_bytes(b'good old data')

    def boom(url, filename):
        raise OSError('network down')

    monkeypatch.setattr(download_frost.urllib.request, 'urlretrieve', boom)
    monkeypatch.setattr(download_frost.time, 'sleep', lambda _s: None)

    assert download_frost.download_one('http://example/x', target, retries=1) is False
    assert target.read_bytes() == b'good old data'


def test_is_usable_cache_rejects_zero_byte(tmp_path):
    empty = tmp_path / 'empty.txt'
    empty.write_bytes(b'')
    good = tmp_path / 'good.txt'
    good.write_bytes(b'data')

    assert download_frost.is_usable_cache(empty) is False
    assert download_frost.is_usable_cache(good) is True
    assert download_frost.is_usable_cache(tmp_path / 'missing.txt') is False


def test_stale_part_file_is_not_treated_as_cache(tmp_path):
    part = tmp_path / 'word.txt.part'
    part.write_bytes(b'x' * 10)

    assert download_frost.is_usable_cache(part) is False


# --------------------------------------------------------------------------
# 参数提示与 argparse 一致
# --------------------------------------------------------------------------

def _script_parser(module):
    """拿到脚本真实的 argparse 参数集合。"""
    class _Recorder:
        def __init__(self):
            self.options = set()

        def add_argument(self, *args, **kwargs):
            for name in args:
                if name.startswith('--'):
                    self.options.add(name)
            return argparse.Namespace()

    # 重新执行模块级 argparse 定义：直接扫描源码里的 add_argument 调用
    import re
    source = Path(module.__file__).read_text(encoding='utf-8')
    return set(re.findall(r"add_argument\(\s*'(--[a-z0-9-]+)'", source))


def test_merge_hint_uses_real_download_frost_options():
    """merge.py 打印的恢复命令必须只包含 download_frost.py 真实支持的参数。"""
    source = Path(merge_script.__file__).read_text(encoding='utf-8')
    hints = re.findall(r'python scripts/download_frost\.py([^\'"\n]*)', source) \
        if (re := __import__('re')) else []

    supported = _script_parser(download_frost)

    for hint in hints:
        for option in hint.split():
            if option.startswith('--'):
                assert option in supported, \
                    f'提示里的 {option} 不是 download_frost.py 支持的参数'


def test_download_frost_supports_documented_options():
    supported = _script_parser(download_frost)
    assert {'--cache', '--force', '--retries', '--no-extended',
            '--extended-only', '--strict-ext'} <= supported


def test_merge_supports_documented_options():
    supported = _script_parser(merge_script)
    assert {'--cache', '--output', '--emit-freq-tiers',
            '--no-extended', '--strict-ext'} <= supported


def test_stale_with_extended_option_is_gone():
    """回归：曾经提示过不存在的 --with-extended。"""
    source = Path(merge_script.__file__).read_text(encoding='utf-8')
    assert '--with-extended' not in source


def test_mirror_urls_expand_to_three_sources():
    """每个文件都要有多个镜像：jsDelivr 会对 Actions 出口 IP 返回 403。"""
    mirrors = download_frost.mirror_urls(
        'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/food.dict.yaml')
    assert mirrors == [
        'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/food.dict.yaml',
        'https://fastly.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/food.dict.yaml',
        'https://raw.githubusercontent.com/gaboolic/rime-frost/master/cn_dicts_cell/food.dict.yaml',
    ]


def test_mirror_urls_keep_raw_origin_first():
    mirrors = download_frost.mirror_urls(
        'https://raw.githubusercontent.com/gaboolic/rime-frost/master/luna_pinyin.dict.yaml')
    assert mirrors[0].startswith('https://raw.githubusercontent.com/')
    assert any('fastly.jsdelivr.net' in m for m in mirrors)
    assert any('cdn.jsdelivr.net' in m for m in mirrors)


def test_mirror_urls_passthrough_unknown_scheme():
    assert download_frost.mirror_urls('https://example.invalid/x.txt') == \
        ['https://example.invalid/x.txt']


def test_download_one_falls_back_to_next_mirror(monkeypatch, tmp_path):
    """第一个镜像失败时必须自动换下一个镜像，而不是直接判定下载失败。"""
    calls = []

    def fake_urlretrieve(url, path):
        calls.append(url)
        if 'cdn.jsdelivr.net' in url:
            raise OSError('HTTP Error 403: Forbidden')
        Path(path).write_bytes(b'payload')

    monkeypatch.setattr(download_frost.urllib.request, 'urlretrieve', fake_urlretrieve)

    out = tmp_path / 'food.txt'
    assert download_frost.download_one(
        'https://cdn.jsdelivr.net/gh/o/r@main/p.txt', out, retries=2) is True
    assert out.read_bytes() == b'payload'
    assert not (tmp_path / 'food.txt.part').exists()
    assert any('fastly.jsdelivr.net' in c for c in calls)


def test_download_one_gives_up_after_all_mirrors(monkeypatch, tmp_path):
    calls = []

    def fake_urlretrieve(url, path):
        calls.append(url)
        raise OSError('boom')

    monkeypatch.setattr(download_frost.urllib.request, 'urlretrieve', fake_urlretrieve)
    monkeypatch.setattr(download_frost.time, 'sleep', lambda *_: None)

    out = tmp_path / 'x.txt'
    assert download_frost.download_one(
        'https://cdn.jsdelivr.net/gh/o/r@main/p.txt', out, retries=2) is False
    assert not out.exists()
    assert not (tmp_path / 'x.txt.part').exists()
