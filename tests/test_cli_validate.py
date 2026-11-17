"""CLI 集成测试：validate 子命令与三档 build（Issue #3）。"""

import json
import os
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from src.parser import MSPinyinParser  # noqa: E402


def run_cli(*args):
    return subprocess.run(
        [sys.executable, '-m', 'src.cli', *args],
        cwd=ROOT, capture_output=True, text=True,
    )


def make_dat(path, words):
    from src.builder_win10 import Win10MSPinyinBuilder
    builder = Win10MSPinyinBuilder(timestamp=1600000000)
    for word, code in words:
        builder.add_word(word, code, 1)
    path.write_bytes(builder.build())
    return path


class TestValidateCommand:
    def test_valid_file_exit_zero(self, tmp_path):
        path = make_dat(tmp_path / "ok.dat", [("中国", "zhongguo")])

        result = run_cli('validate', str(path))

        assert result.returncode == 0
        assert '结论: 格式合法' in result.stdout
        assert '【文件格式错误】' not in result.stdout

    def test_bad_magic_exit_two_and_clear_category(self, tmp_path):
        path = tmp_path / "bad.dat"
        path.write_bytes(b'not a pinyin dat file' + b'\x00' * 64)

        result = run_cli('validate', str(path))

        assert result.returncode == 2
        assert '【文件格式错误】' in result.stdout
        assert '协议标识不是' in result.stdout

    def test_corrupted_file_exit_three(self, tmp_path):
        path = make_dat(tmp_path / "trunc.dat", [("中国", "zhongguo"), ("北京", "beijing")])
        data = path.read_bytes()
        path.write_bytes(data[:-2])

        result = run_cli('validate', str(path))

        assert result.returncode == 3
        assert '【文件已损坏】' in result.stdout
        assert '截断' in result.stdout

    def test_illegal_position_exit_four(self, tmp_path):
        path = make_dat(tmp_path / "pos.dat", [("中国", "zhongguo")])
        data = bytearray(path.read_bytes())
        phrase_start = struct.unpack_from('<I', data, 20)[0]
        data[phrase_start + 6] = 200
        path.write_bytes(data)

        result = run_cli('validate', str(path))

        assert result.returncode == 4
        assert '【候选位置/内容违规】' in result.stdout
        assert '候选序号 200 非法' in result.stdout

    def test_json_output(self, tmp_path):
        path = make_dat(tmp_path / "ok.dat", [("中国", "zhongguo")])

        result = run_cli('validate', str(path), '--json')

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload['exit_code'] == 0
        assert payload['phrase_count'] == 1
        assert payload['issues'] == []


class TestBuildCommand:
    def test_lite_profile_drops_single_char(self, tmp_path):
        source = tmp_path / "input.txt"
        source.write_text("的\tde\t900\n中国\tzhongguo\t500\n北京\tbeijing\t300\n",
                          encoding='utf-8')
        output = tmp_path / "lite.dat"

        result = run_cli('build', str(source), '-o', str(output),
                         '--profile', 'lite', '--timestamp', '1600000000')

        assert result.returncode == 0
        assert '剔除单字' in result.stdout
        parser = MSPinyinParser()
        assert parser.load(str(output)) == 2
        assert sorted(parser.get_all_texts()) == ["中国", "北京"]

    def test_full_profile_keeps_single_char(self, tmp_path):
        source = tmp_path / "input.txt"
        source.write_text("的\tde\t900\n中国\tzhongguo\t500\n", encoding='utf-8')
        output = tmp_path / "full.dat"

        result = run_cli('build', str(source), '-o', str(output),
                         '--profile', 'full', '--timestamp', '1600000000')

        assert result.returncode == 0
        parser = MSPinyinParser()
        assert parser.load(str(output)) == 2
        assert sorted(parser.get_all_texts()) == ["中国", "的"]

    def test_build_reports_cleaning_and_writes_timestamp(self, tmp_path):
        source = tmp_path / "input.txt"
        source.write_text("中国\tzhongguo3\t500\n北京\tbeijing\t300\n", encoding='utf-8')
        output = tmp_path / "out.dat"

        result = run_cli('build', str(source), '-o', str(output),
                         '--profile', 'lite', '--timestamp', '1600000000')

        assert result.returncode == 0
        assert '非法拼音字符=1' in result.stdout
        data = output.read_bytes()
        assert struct.unpack_from('<Q', data, 32)[0] == 1600000000
        assert struct.unpack_from('<I', data, 28)[0] == 1
