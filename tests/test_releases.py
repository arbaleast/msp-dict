"""三档发布脚本测试：lite/standard/full + msp_win10.dat 兼容副本。"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from src.parser import MSPinyinParser  # noqa: E402


def run_releases(source, output_dir, *extra):
    env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
    return subprocess.run(
        [sys.executable, 'scripts/build_releases.py',
         '--input', str(source), '--output-dir', str(output_dir),
         '--timestamp', '1600000000', *extra],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8', env=env,
    )


def test_three_tiers_and_compat_copy(tmp_path):
    source = tmp_path / "msp_full.txt"
    source.write_text(
        "的\tde\t900\n"
        "中国\tzhongguo\t500\n"
        "北京\tbeijing\t300\n",
        encoding='utf-8',
    )
    output_dir = tmp_path / "dist"

    result = run_releases(source, output_dir)

    assert result.returncode == 0, result.stderr
    for name in ('msp_lite.dat', 'msp_standard.dat', 'msp_full.dat', 'msp_win10.dat'):
        assert (output_dir / name).exists(), name

    # 旧链接兼容：msp_win10.dat 与 msp_lite.dat 字节一致
    assert (output_dir / 'msp_win10.dat').read_bytes() == (output_dir / 'msp_lite.dat').read_bytes()

    lite = MSPinyinParser()
    assert lite.load(str(output_dir / 'msp_lite.dat')) == 2
    assert sorted(lite.get_all_texts()) == ["中国", "北京"]

    standard = MSPinyinParser()
    assert standard.load(str(output_dir / 'msp_standard.dat')) == 3
    assert sorted(standard.get_all_texts()) == ["中国", "北京", "的"]

    summary = json.loads((output_dir / 'build_summary.json').read_text(encoding='utf-8'))
    by_name = {p['profile']: p for p in summary['profiles']}
    assert by_name['lite']['entries'] == 2
    assert by_name['standard']['entries'] == 3
    assert by_name['full']['entries'] == 3
    assert by_name['lite']['windows_importable'] is True
    assert by_name['full']['windows_importable'] is False
    assert all(p['validation']['exit_code'] == 0 for p in summary['profiles'])


def test_single_profile_only_builds_requested_tier(tmp_path):
    source = tmp_path / "msp_full.txt"
    lines = [f"词{chr(0x4e00 + i)}\tci{chr(97 + i)}\t{1000 - i}\n" for i in range(20)]
    source.write_text(''.join(lines), encoding='utf-8')
    output_dir = tmp_path / "dist"

    env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
    result = subprocess.run(
        [sys.executable, 'scripts/build_releases.py',
         '--input', str(source), '--output-dir', str(output_dir),
         '--profiles', 'lite', '--timestamp', '1600000000'],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8', env=env,
    )

    assert result.returncode == 0, result.stderr
    parser = MSPinyinParser()
    assert parser.load(str(output_dir / 'msp_lite.dat')) == 20
    assert not (output_dir / 'msp_standard.dat').exists()
    assert (output_dir / 'msp_win10.dat').exists()
