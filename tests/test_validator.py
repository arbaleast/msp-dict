"""校验器测试：四类问题必须被区分报告（Issue #3）。"""

import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.builder_win10 import Win10MSPinyinBuilder
from src.format_spec import HEADER_FLAG, HEADER_SIZE
from src.validator import DatValidator

NOW = 1600000000


def _valid_dat(tmp_path, name="valid.dat", entries=None, timestamp=NOW):
    entries = entries or [("中国", "zhongguo", 1), ("北京", "beijing", 2)]
    builder = Win10MSPinyinBuilder(timestamp=timestamp)
    for word, code, freq in entries:
        builder.add_word(word, code, freq)
    path = tmp_path / name
    path.write_bytes(builder.build())
    return path


def _raw_dat(records):
    """按规范手工拼一个 DAT：records = [(code, word, position, record_ts), ...]"""
    phrases = []
    offsets = []
    offset = 0
    for code, word, position, record_ts in records:
        code_bytes = code.encode('utf-16-le')
        word_bytes = word.encode('utf-16-le')
        entry = struct.pack('<IHBBII', 0x00100010, 18 + len(code_bytes),
                            position, 0x06, 0, record_ts)
        entry += code_bytes + b'\x00\x00' + word_bytes + b'\x00\x00'
        offsets.append(offset)
        offset += len(entry)
        phrases.append(entry)

    phrase_start = HEADER_SIZE + 4 * len(phrases)
    phrase_end = phrase_start + sum(len(p) for p in phrases)
    header = bytearray(HEADER_SIZE)
    header[0:8] = b'mschxudp'
    struct.pack_into('<I', header, 8, HEADER_FLAG)
    struct.pack_into('<I', header, 12, 1)
    struct.pack_into('<I', header, 16, HEADER_SIZE)
    struct.pack_into('<I', header, 20, phrase_start)
    struct.pack_into('<I', header, 24, phrase_end)
    struct.pack_into('<I', header, 28, len(phrases))
    struct.pack_into('<Q', header, 32, NOW)
    table = b''.join(struct.pack('<I', off) for off in offsets)
    return bytes(header) + table + b''.join(phrases)


class TestFormatErrors:
    def test_valid_file_passes(self, tmp_path):
        report = DatValidator(now=NOW).validate(str(_valid_dat(tmp_path)))

        assert report.exit_code == 0
        assert report.issues == []
        assert report.verdict == '格式合法，未发现阻断导入的问题'

    def test_too_small_is_format_error(self, tmp_path):
        path = tmp_path / "small.dat"
        path.write_bytes(b'mschxudp')

        report = DatValidator(now=NOW).validate(str(path))

        assert report.exit_code == 2
        assert [i.code for i in report.issues] == ['too_small']

    def test_wrong_magic_is_format_error(self, tmp_path):
        data = bytearray(_valid_dat(tmp_path).read_bytes())
        data[0:8] = b'notadat!'
        path = tmp_path / "magic.dat"
        path.write_bytes(data)

        report = DatValidator(now=NOW).validate(str(path))

        assert report.exit_code == 2
        assert report.issues_in('format')[0].code == 'bad_magic'

    def test_wrong_version_is_format_error(self, tmp_path):
        data = bytearray(_valid_dat(tmp_path).read_bytes())
        struct.pack_into('<I', data, 12, 2)
        path = tmp_path / "version.dat"
        path.write_bytes(data)

        report = DatValidator(now=NOW).validate(str(path))

        assert report.exit_code == 2
        assert 'bad_version' in [i.code for i in report.issues]


class TestCorruption:
    def test_truncated_file(self, tmp_path):
        data = _valid_dat(tmp_path).read_bytes()
        path = tmp_path / "truncated.dat"
        path.write_bytes(data[:-4])

        report = DatValidator(now=NOW).validate(str(path))

        assert report.exit_code == 3
        assert 'phrase_end_overflow' in [i.code for i in report.issues]

    def test_non_monotonic_offsets(self, tmp_path):
        data = bytearray(_valid_dat(
            tmp_path, entries=[("中国", "zhongguo", 1), ("北京", "beijing", 2),
                               ("上海", "shanghai", 3)]).read_bytes())
        second = struct.unpack_from('<I', data, 0x40 + 4)[0]
        struct.pack_into('<I', data, 0x40 + 8, second)  # 第三项 <= 第二项
        path = tmp_path / "offsets.dat"
        path.write_bytes(data)

        report = DatValidator(now=NOW).validate(str(path))

        assert report.exit_code == 3
        assert 'non_monotonic_offsets' in [i.code for i in report.issues]

    def test_bad_entry_magic(self, tmp_path):
        data = bytearray(_valid_dat(tmp_path).read_bytes())
        phrase_start = struct.unpack_from('<I', data, 20)[0]
        struct.pack_into('<I', data, phrase_start, 0xDEADBEEF)
        path = tmp_path / "entrymagic.dat"
        path.write_bytes(data)

        report = DatValidator(now=NOW).validate(str(path))

        assert report.exit_code == 3
        assert 'bad_entry_magic' in [i.code for i in report.issues]


class TestContentViolations:
    def test_zero_candidate_position(self, tmp_path):
        data = bytearray(_valid_dat(tmp_path).read_bytes())
        phrase_start = struct.unpack_from('<I', data, 20)[0]
        data[phrase_start + 6] = 0  # 候选位 = 词频 & 0xFF == 0
        path = tmp_path / "pos0.dat"
        path.write_bytes(data)

        report = DatValidator(now=NOW).validate(str(path))

        assert report.exit_code == 4
        issue = [i for i in report.issues if i.code == 'zero_position'][0]
        assert issue.count == 1

    def test_position_above_nine(self, tmp_path):
        data = bytearray(_valid_dat(tmp_path).read_bytes())
        phrase_start = struct.unpack_from('<I', data, 20)[0]
        data[phrase_start + 6] = 218  # 31450 & 0xFF
        path = tmp_path / "pos218.dat"
        path.write_bytes(data)

        report = DatValidator(now=NOW).validate(str(path))

        assert report.exit_code == 4
        assert [i.code for i in report.issues] == ['position_out_of_range']

    def test_empty_pinyin_record(self, tmp_path):
        data = _raw_dat([("", "中国", 1, 100)])
        path = tmp_path / "emptycode.dat"
        path.write_bytes(data)

        report = DatValidator(now=NOW).validate(str(path))

        assert report.exit_code == 4
        assert [i.code for i in report.issues] == ['empty_pinyin']
        assert report.parsed_entries == 1

    def test_future_record_timestamp_is_warning_only(self, tmp_path):
        data = bytearray(_valid_dat(tmp_path).read_bytes())
        phrase_start = struct.unpack_from('<I', data, 20)[0]
        struct.pack_into('<I', data, phrase_start + 12, 0xE679CD20)
        path = tmp_path / "ts.dat"
        path.write_bytes(data)

        report = DatValidator(now=NOW).validate(str(path))

        assert report.exit_code == 0
        assert 'stale_timestamp' in [i.code for i in report.issues]


class TestScaleWarnings:
    def _unique_code(self, index: int) -> str:
        """双射 26 进制：a, b, ..., z, aa, ab, ...（保证互不相同）"""
        letters = []
        n = index + 1
        while n > 0:
            n, rem = divmod(n - 1, 26)
            letters.append(chr(ord('a') + rem))
        return ''.join(reversed(letters))

    def test_over_import_limit_warning(self, tmp_path):
        entries = [(f"词{i}", self._unique_code(i), 1) for i in range(20001)]
        path = _valid_dat(tmp_path, name="big.dat", entries=entries)

        report = DatValidator(now=NOW).validate(str(path))

        assert report.phrase_count == 20001
        assert report.exit_code == 0
        assert [i.code for i in report.issues] == ['over_import_limit']

    def test_freeze_risk_above_fifty_thousand(self, tmp_path):
        entries = [(f"词{i}", self._unique_code(i), 1) for i in range(50001)]
        path = _valid_dat(tmp_path, name="huge.dat", entries=entries)

        report = DatValidator(now=NOW).validate(str(path))

        assert report.exit_code == 0
        assert [i.code for i in report.issues] == ['ui_freeze_risk']
