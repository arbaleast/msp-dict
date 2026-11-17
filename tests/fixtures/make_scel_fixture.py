#!/usr/bin/env python3
"""生成一个最小但结构合法的搜狗细胞词库 (.scel) 测试样本。

产物：``tests/fixtures/valid_mock.scel``

结构严格对齐真实 .scel（已用上游 imewlconverter 测试样本「诗词名句大全.scel」
核对）：魔数 ``@\\x15\\x00\\x00DCS\\x01``、词条组数在 0x120、拼音表条目数在
0x1540、拼音表在 0x1544，其后是「同音词数 / 拼音索引字节数 / 拼音索引 /
词条（UTF-16LE + 12 字节尾字段）」结构的词条数据。

样本内容覆盖三种情况：
- 普通词条（中国、测试、阿房宫）
- 同音词组（测试 / 测验 共享同一拼音）
- 多音词（银行 出现两次，分别 yin'hang 与 yin'xing）

直接运行即可重新生成::

    python tests/fixtures/make_scel_fixture.py
"""

import struct
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

# 真实 .scel 魔数共 8 字节：40 15 00 00 44 43 53 01
MAGIC = b'@\x15\x00\x00DCS\x01'
OFFSET_DICT_LEN = 0x120
OFFSET_EXPANDED_LEN = 0x124
OFFSET_NAME = 0x130
OFFSET_PY_COUNT = 0x1540
OFFSET_PY_TABLE = 0x1544
WORD_TRAILER = b'\x00' * 12

# (词条, 音节列表)；同音词用同一组表示
GROUPS: Sequence[Tuple[str, Sequence[str]]] = (
    ('中国', ('zhong', 'guo')),
    ('测试', ('ce', 'shi')),
    ('阿房宫', ('a', 'fang', 'gong')),
)
# 同一组内的同音词
SAME_PINYIN_GROUP: Tuple[str, Sequence[str], Sequence[str]] = (
    'ce', ('ce', 'shi'), ('测验',),
)
# 多音词：同一个词在不同组里出现
POLYPHONIC: Sequence[Tuple[str, Sequence[str]]] = (
    ('银行', ('yin', 'hang')),
    ('银行', ('yin', 'xing')),
)


def _build_pinyin_table() -> Tuple[Dict[str, int], List[str]]:
    """收集所有音节并按首次出现顺序编号（索引必须从 0 连续递增）。"""
    order: List[str] = []
    seen = set()

    def add(syllable: str) -> None:
        if syllable not in seen:
            seen.add(syllable)
            order.append(syllable)

    for _word, syllables in GROUPS:
        for s in syllables:
            add(s)
    for s in SAME_PINYIN_GROUP[1]:
        add(s)
    for _word, syllables in POLYPHONIC:
        for s in syllables:
            add(s)

    return {s: i for i, s in enumerate(order)}, order


def _encode_py_table(pin_map: Dict[str, int]) -> bytes:
    out = bytearray()
    for syllable, idx in sorted(pin_map.items(), key=lambda kv: kv[1]):
        raw = syllable.encode('utf-16le')
        out += struct.pack('<HH', idx, len(raw))
        out += raw
    return bytes(out)


def _encode_group(syllables: Sequence[str], words: Sequence[str],
                  pin_map: Dict[str, int]) -> bytes:
    indices = b''.join(struct.pack('<H', pin_map[s]) for s in syllables)
    out = bytearray()
    out += struct.pack('<HH', len(words), len(indices))
    out += indices
    for word in words:
        raw = word.encode('utf-16le')
        out += struct.pack('<H', len(raw))
        out += raw
        out += WORD_TRAILER
    return bytes(out)


def build_scel(name: str = '测试细胞词库') -> bytes:
    """构造完整的 .scel 字节流。"""
    pin_map, _order = _build_pinyin_table()

    body = bytearray()
    for word, syllables in GROUPS:
        body += _encode_group(syllables, [word], pin_map)
    body += _encode_group(SAME_PINYIN_GROUP[1], SAME_PINYIN_GROUP[2], pin_map)
    for word, syllables in POLYPHONIC:
        body += _encode_group(syllables, [word], pin_map)

    group_count = len(GROUPS) + 1 + len(POLYPHONIC)
    word_count = len(GROUPS) + len(SAME_PINYIN_GROUP[2]) + len(POLYPHONIC)

    data = bytearray()
    data += MAGIC
    data += struct.pack('<I', 1)          # 版本 @0x08
    data += b'\x00' * (OFFSET_DICT_LEN - len(data))
    data += struct.pack('<I', group_count)          # 词条组数 @0x120
    data += struct.pack('<I', word_count)           # 展开词条数 @0x124
    data += b'\x00' * (OFFSET_NAME - len(data))     # 对齐到 0x130
    data += name.encode('utf-16le') + b'\x00\x00'   # 词库名 @0x130
    data += b'\x00' * (OFFSET_PY_COUNT - len(data))
    data += struct.pack('<I', len(pin_map))         # 拼音表条目数 @0x1540
    data += _encode_py_table(pin_map)               # 拼音表 @0x1544
    data += body
    return bytes(data)


def main() -> int:
    target = Path(__file__).parent / 'valid_mock.scel'
    payload = build_scel()
    target.write_bytes(payload)
    print(f'已生成 {target}（{len(payload)} 字节）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
