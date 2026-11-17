"""
搜狗细胞词库 (.scel) 解析器

二进制布局（已对照上游 imewlconverter 的 SougouScelImporter 与真实 .scel 样本核实）::

    0x0000  魔数          40 15 00 00 "DCS" 01      （旧格式为 40 00 00 00）
    0x0008  版本          u32
    0x0120  词条组数      u32   dict_len
    0x0124  展开词条数    u32
    0x0130  词库名        UTF-16LE, NUL 结尾
    0x1540  拼音表条目数  u32   py_count
    0x1544  拼音表        py_count × (索引 u16, 字节长度 u16, UTF-16LE 拼音)
    之后    词条数据      dict_len 组，每组:
                             同音词数 u16
                             拼音索引字节数 u16（偶数）
                             拼音索引 u16 × N
                             同音词数 × (词条字节长度 u16, UTF-16LE 词条, 12 字节未知)

与上游实现的差异：拼音索引按「表中的真实索引」查表（上游假定索引连续），
无法解析的音节会记录到 errors 而不是静默丢弃整组。

参考：
- https://github.com/studyzy/imewlconverter (src/ImeWlConverter.Formats/SougouScel)
- https://github.com/KaixuanZhou/PyScel
"""

import struct
from typing import List, NamedTuple, Optional, Tuple


class ScelParseError(Exception):
    """SCEL 文件结构损坏或格式不合法时抛出。"""


# 兼容别名，便于外部按 ParseError 引用
ParseError = ScelParseError


class ScelEntry(NamedTuple):
    """一条 SCEL 词条。兼容旧的 (词, 拼音, 词频) 元组用法。"""

    word: str
    pinyin: str
    freq: int


class ScelParser:
    """搜狗细胞词库 (.scel) 解析器"""

    # ---- 文件头 ----
    MAGIC_DCS = b'@\x15\x00\x00'
    MAGIC_LEGACY = b'@\x00\x00\x00'
    SIGNATURE = b'DCS'

    OFFSET_VERSION = 0x08
    OFFSET_DICT_LEN = 0x120
    OFFSET_EXPANDED_LEN = 0x124
    OFFSET_NAME = 0x130
    OFFSET_PY_COUNT = 0x1540
    OFFSET_PY_TABLE = 0x1544

    MIN_SIZE = OFFSET_PY_TABLE          # 至少要有到拼音表计数
    MAX_DICT_LEN = 5_000_000
    MAX_PY_COUNT = 200_000
    MAX_GROUP_SYLLABLES = 512
    MAX_SAME_PY = 100_000
    WORD_TRAILER_SIZE = 12              # 每个词条后的固定未知字段长度

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath
        self.name = ""
        self.category = ""
        self.description = ""
        self.entries: List[ScelEntry] = []
        self.errors: List[str] = []

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------
    def load(self, filepath: str) -> int:
        """加载 .scel 文件，返回解析出的词条数。

        Raises:
            ScelParseError: 文件过短、魔数不符、结构损坏等无法继续解析的情况。
        """
        self.filepath = filepath
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
        except OSError as exc:
            raise ScelParseError(f'无法读取 SCEL 文件 {filepath}: {exc}') from exc

        self.entries = self.parse_bytes(data)
        return len(self.entries)

    def parse_bytes(self, data: bytes) -> List[ScelEntry]:
        """解析 SCEL 字节流。

        Raises:
            ScelParseError: 结构级损坏（魔数、计数越界、截断等）。
        """
        self.errors = []
        self.name = ""
        self.category = ""
        self.description = ""

        if len(data) < self.MIN_SIZE:
            raise ScelParseError(
                f'SCEL 文件过短: {len(data)} 字节（至少需要 {self.MIN_SIZE} 字节）')
        if not self._check_magic(data):
            raise ScelParseError(
                'SCEL 魔数不正确: 期望 @\\x15\\x00\\x00 + DCS 或 @\\x00\\x00\\x00，'
                f'实际 {data[:10].hex(" ")}')

        dict_len = self._read_u32(data, self.OFFSET_DICT_LEN)
        py_count = self._read_u32(data, self.OFFSET_PY_COUNT)
        if dict_len > self.MAX_DICT_LEN:
            raise ScelParseError(f'SCEL 词条组数异常: {dict_len}')
        if py_count > self.MAX_PY_COUNT:
            raise ScelParseError(f'SCEL 拼音表条目数异常: {py_count}')

        self.name = self._read_utf16z(data, self.OFFSET_NAME)
        self.category = self._read_utf16z(data, self.OFFSET_NAME + 0x100)
        self.description = self._read_utf16z(data, self.OFFSET_NAME + 0x200)

        py_table, pos = self._read_py_table(data, py_count)
        entries = self._read_phrases(data, pos, dict_len, py_table)
        return entries

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    def _check_magic(self, data: bytes) -> bool:
        head = data[:10]
        if head.startswith(self.MAGIC_DCS):
            return self.SIGNATURE in head
        if head.startswith(self.MAGIC_LEGACY):
            return True
        return False

    @staticmethod
    def _read_u32(data: bytes, offset: int) -> int:
        if offset + 4 > len(data):
            raise ScelParseError(f'SCEL 文件在偏移 0x{offset:X} 处被截断')
        return struct.unpack_from('<I', data, offset)[0]

    def _read_utf16z(self, data: bytes, offset: int, max_chars: int = 128) -> str:
        """读取 NUL 结尾的 UTF-16LE 字符串；越界或解码失败返回空串。"""
        if offset >= len(data):
            return ''
        chunk = data[offset:offset + max_chars * 2]
        text = chunk.decode('utf-16le', errors='replace')
        return text.split('\x00', 1)[0].strip()

    def _read_py_table(self, data: bytes, py_count: int) -> Tuple[dict, int]:
        """读取拼音表，返回 ({索引: 拼音}, 词条数据起始偏移)。"""
        pos = self.OFFSET_PY_TABLE
        table: dict = {}
        for _ in range(py_count):
            if pos + 4 > len(data):
                raise ScelParseError(
                    f'SCEL 拼音表在偏移 0x{pos:X} 处被截断（声明 {py_count} 条）')
            idx, size = struct.unpack_from('<HH', data, pos)
            pos += 4
            if size % 2 or pos + size > len(data):
                raise ScelParseError(
                    f'SCEL 拼音表条目长度非法: idx={idx} size={size} @0x{pos:X}')
            raw = data[pos:pos + size]
            pos += size
            try:
                pinyin = raw.decode('utf-16le')
            except UnicodeDecodeError as exc:
                raise ScelParseError(
                    f'SCEL 拼音表条目解码失败: idx={idx}') from exc
            pinyin = pinyin.strip().lower()
            if pinyin:
                table[idx] = pinyin
        return table, pos

    def _resolve_syllables(self, indices: List[int], py_table: dict,
                           py_count: int) -> Optional[List[str]]:
        """把拼音索引列表解析成音节列表；无法解析时返回 None。"""
        syllables = []
        for idx in indices:
            pinyin = py_table.get(idx)
            if pinyin is None:
                # 上游的兼容规则：超出拼音表范围的索引代表 a~z 的单字母简写
                code = idx - py_count + ord('a')
                if 0 <= code <= ord('z') - ord('a'):
                    pinyin = chr(ord('a') + code)
                else:
                    self.errors.append(
                        f'拼音索引 {idx} 无法解析（拼音表 {py_count} 条）')
                    return None
            syllables.append(pinyin)
        return syllables

    def _read_phrases(self, data: bytes, pos: int, dict_len: int,
                      py_table: dict) -> List[ScelEntry]:
        """读取词条数据区。"""
        py_count = len(py_table)
        entries: List[ScelEntry] = []
        seen = set()

        for group_index in range(dict_len):
            if pos + 4 > len(data):
                raise ScelParseError(
                    f'SCEL 词条区在第 {group_index} 组（偏移 0x{pos:X}）处被截断')
            same_py, py_bytes = struct.unpack_from('<HH', data, pos)
            pos += 4

            if py_bytes % 2 or py_bytes // 2 > self.MAX_GROUP_SYLLABLES:
                raise ScelParseError(
                    f'SCEL 第 {group_index} 组拼音长度非法: {py_bytes}')
            if same_py > self.MAX_SAME_PY:
                raise ScelParseError(
                    f'SCEL 第 {group_index} 组同音词数异常: {same_py}')
            if pos + py_bytes > len(data):
                raise ScelParseError(
                    f'SCEL 第 {group_index} 组拼音索引被截断')

            indices = list(struct.unpack_from(f'<{py_bytes // 2}H', data, pos))
            pos += py_bytes

            syllables = self._resolve_syllables(indices, py_table, py_count)
            if syllables is None:
                # 整组无法解析：无法确定其长度，只能中止（保持偏移可信）
                raise ScelParseError(
                    f'SCEL 第 {group_index} 组拼音无法解析，文件结构不可信')

            pinyin = "'".join(syllables)
            for _ in range(same_py):
                if pos + 2 > len(data):
                    raise ScelParseError(
                        f'SCEL 第 {group_index} 组词条长度字段被截断')
                hz_bytes = struct.unpack_from('<H', data, pos)[0]
                pos += 2
                if hz_bytes % 2 or pos + hz_bytes > len(data):
                    raise ScelParseError(
                        f'SCEL 第 {group_index} 组词条长度非法: {hz_bytes}')
                raw = data[pos:pos + hz_bytes]
                pos += hz_bytes
                try:
                    word = raw.decode('utf-16le')
                except UnicodeDecodeError:
                    self.errors.append(
                        f'SCEL 第 {group_index} 组词条 UTF-16 解码失败，已跳过')
                    word = ''
                pos += self.WORD_TRAILER_SIZE
                if not word:
                    continue
                key = (word, pinyin)
                if key in seen:
                    continue
                seen.add(key)
                entries.append(ScelEntry(word=word, pinyin=pinyin, freq=1))

        return entries
