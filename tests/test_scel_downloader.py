"""搜狗 SCEL 下载器的原子下载与内容校验测试。"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    'scel_downloader', ROOT / 'crawler' / 'scel_downloader.py')
scel_downloader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scel_downloader)


class _FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code


class _FakeSession:
    """只实现 download_dict 用到的那几个方法。"""

    def __init__(self, content: bytes, status_code: int = 200, url: str = 'http://x'):
        self.content = content
        self.status_code = status_code
        self.url = url
        self.headers = {}

    def get(self, url, **kwargs):
        return _FakeResponse(self.content, self.status_code)

    def update(self, *args, **kwargs):
        pass


def _valid_scel_bytes() -> bytes:
    """用仓库里的 fixture 生成器造一个合法 SCEL。"""
    sys.path.insert(0, str(ROOT / 'tests' / 'fixtures'))
    from make_scel_fixture import build_scel
    return build_scel()


def _make_downloader(tmp_path, session):
    downloader = scel_downloader.SogouCellDownloader(str(tmp_path))
    downloader.session = session
    downloader.get_dict_download_url = lambda dict_id: session.url
    return downloader


def test_download_dict_writes_valid_file(tmp_path):
    payload = _valid_scel_bytes()
    downloader = _make_downloader(tmp_path, _FakeSession(payload))

    filepath = downloader.download_dict('123', '测试词库')

    assert filepath is not None
    assert Path(filepath).exists()
    assert Path(filepath).read_bytes() == payload
    # 不留 .part 残片
    assert not list(tmp_path.glob('*.part'))


def test_download_dict_rejects_invalid_payload_and_cleans_part(tmp_path):
    """非法内容（HTML 错误页/文本）必须被拒绝，且不留残片。"""
    downloader = _make_downloader(tmp_path, _FakeSession(b'<html>404 not found</html>' * 10))

    filepath = downloader.download_dict('123', '坏词库')

    assert filepath is None
    assert not list(tmp_path.glob('*.part'))
    assert not list(tmp_path.glob('*.scel'))


def test_download_dict_rejects_non_200_status(tmp_path):
    payload = _valid_scel_bytes()
    downloader = _make_downloader(tmp_path, _FakeSession(payload, status_code=503))

    filepath = downloader.download_dict('123', '错误状态')

    assert filepath is None
    assert not list(tmp_path.glob('*.part'))
    assert not list(tmp_path.glob('*.scel'))


def test_download_dict_does_not_overwrite_existing_file_on_failure(tmp_path):
    """失败时不能破坏已有的完整缓存文件。"""
    existing = tmp_path / '已有词库.scel'
    existing.write_bytes(_valid_scel_bytes())

    downloader = _make_downloader(tmp_path, _FakeSession(b'garbage' * 100))
    filepath = downloader.download_dict('123', '已有词库')

    assert filepath is None
    assert existing.exists()
    assert existing.read_bytes() == _valid_scel_bytes()


def test_is_valid_scel_rejects_short_and_text():
    downloader = scel_downloader.SogouCellDownloader.__new__(
        scel_downloader.SogouCellDownloader)

    assert downloader._is_valid_scel(b'') is False
    assert downloader._is_valid_scel(b'hello world' * 20) is False
    assert downloader._is_valid_scel(b'@' + b'\x15\x00\x00' + b'DCS\x01' + b'\x00' * 100) is True
