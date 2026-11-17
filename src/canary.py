"""
Canary 诊断探针：验证 .dat 词库是否真的被 Windows 微软拼音加载。

零污染设计
----------
* 正式产物（``msp_lite.dat`` / ``msp_standard.dat`` / ``msp_full.dat``）**永远不含探针**；
  探针只存在于独立的 ``msp_lite_canary.dat`` + ``msp_lite_canary.json``。
* 探针在普通词条完成筛选/去重/截断之后注入，随后走与普通词条**完全相同**的
  二进制序列化与 Offset Table 生成路径。
* 构建后立即**回读二进制文件**，确认探针的真实物理索引与字节偏移；
  绝不凭内存列表顺序假定写入成功（DAT 记录按拼音字典序重排，内存顺序≠物理顺序）。

探针选取
--------
默认使用「首尾双探针」，均为合法汉语拼音音节组合，避免被微软拼音的全拼切分器
忽略而造成假阴性：

  * 全拼探针   ``cikutanzhen`` → ``词库探针已生效``（拼音字典序靠前）
  * 尾部探针   ``zuiweitan``  → ``词库尾部已生效``（拼音字典序靠后）

可用 CLI 参数 ``--canary-pinyin`` / ``--canary-word`` 覆盖（成对给出，可多组）。
"""

import hashlib
import json
import struct
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .format_spec import (
    ENTRY_HEAD_BASE,
    ENTRY_MAGIC,
    HEADER_SIZE,
    MAGIC,
    OFF_PHRASE_COUNT,
    OFF_PHRASE_END,
    OFF_PHRASE_START,
    PHRASE_OFFSET_START,
    is_valid_pinyin,
    normalize_pinyin,
)

MANIFEST_FORMAT = 'msp-dict-canary-manifest/1'

# 探针使用的来源词频：取极大值，保证同一拼音下探针排在第一位、拿到候选位 1。
# 注意这只是「排序用词频」，最终写入候选序号字段的仍是 1~9 的候选位。
CANARY_SOURCE_RANK = 2 ** 31 - 1


@dataclass(frozen=True)
class CanaryProbe:
    """一个探针：拼音 + 候选词。"""

    pinyin: str
    word: str

    @property
    def key(self) -> Tuple[str, str]:
        return (self.pinyin, self.word)


DEFAULT_PROBES: Tuple[CanaryProbe, ...] = (
    CanaryProbe(pinyin='cikutanzhen', word='词库探针已生效'),
    CanaryProbe(pinyin='zuiweitan', word='词库尾部已生效'),
)


def resolve_probes(pinyins: Optional[Iterable[str]] = None,
                   words: Optional[Iterable[str]] = None) -> List[CanaryProbe]:
    """解析探针定义。

    Args:
        pinyins: 自定义拼音列表（None/空表示用默认探针）
        words: 与 pinyins 一一对应的候选词

    Returns:
        规范化后的探针列表

    Raises:
        ValueError: 数量不匹配、拼音非法或词条为空
    """
    pinyin_list = [p for p in (pinyins or []) if p is not None]
    word_list = [w for w in (words or []) if w is not None]

    if not pinyin_list and not word_list:
        return list(DEFAULT_PROBES)

    if len(pinyin_list) != len(word_list):
        raise ValueError(
            f'--canary-pinyin 与 --canary-word 必须成对给出（当前 {len(pinyin_list)} vs {len(word_list)}）'
        )

    probes: List[CanaryProbe] = []
    for pinyin, word in zip(pinyin_list, word_list):
        code = normalize_pinyin(pinyin)
        if not is_valid_pinyin(code):
            raise ValueError(f'探针拼音非法: {pinyin!r}（只允许 a-z 与 \'）')
        if not (word or '').strip():
            raise ValueError(f'探针词条为空: {word!r}')
        probes.append(CanaryProbe(pinyin=code, word=word.strip()))

    if not probes:
        raise ValueError('没有可用的探针定义')
    return probes


def iter_physical_records(data: bytes) -> Iterable[Dict[str, object]]:
    """按**文件物理顺序**产出记录。

    这是一条与构建器完全独立的读回路径：直接解析文件头、Offset Table 与记录，
    用于确认探针在最终文件里的真实位置。

    Yields:
        dict: index(物理序号) / byte_offset(文件内绝对偏移) / code / word / position
    """
    if len(data) < HEADER_SIZE or data[0:8] != MAGIC:
        return

    count = struct.unpack_from('<I', data, OFF_PHRASE_COUNT)[0]
    phrase_start = struct.unpack_from('<I', data, OFF_PHRASE_START)[0]
    phrase_end = struct.unpack_from('<I', data, OFF_PHRASE_END)[0]

    offsets: List[int] = []
    for i in range(count):
        base = PHRASE_OFFSET_START + i * 4
        if base + 4 > len(data):
            break
        offsets.append(struct.unpack_from('<I', data, base)[0])

    for index, offset in enumerate(offsets):
        start = phrase_start + offset
        if index + 1 < len(offsets):
            size = offsets[index + 1] - offset
        else:
            size = (phrase_end - phrase_start) - offset
        if size < ENTRY_HEAD_BASE + 4 or start + size > len(data):
            continue
        if struct.unpack_from('<I', data, start)[0] != ENTRY_MAGIC:
            continue

        hanzi_offset = struct.unpack_from('<H', data, start + 4)[0]
        position = data[start + 6]
        try:
            code = data[start + ENTRY_HEAD_BASE:start + hanzi_offset - 2].decode('utf-16-le')
            word = data[start + hanzi_offset:start + size - 2].decode('utf-16-le')
        except UnicodeDecodeError:
            continue

        yield {
            'index': index,
            'byte_offset': start,
            'code': code,
            'word': word,
            'position': position,
        }


def locate_probes(data: bytes, probes: Iterable[CanaryProbe]) -> List[Dict[str, object]]:
    """在二进制文件里回读探针的真实物理位置。

    Returns:
        每个探针一个 dict：pinyin / word / found / physical_index / byte_offset / rank
    """
    found: Dict[Tuple[str, str], Dict[str, object]] = {}
    for record in iter_physical_records(data):
        key = (str(record['code']), str(record['word']))
        if key not in found:
            found[key] = record

    located: List[Dict[str, object]] = []
    for probe in probes:
        record = found.get(probe.key)
        if record is None:
            located.append({
                'pinyin': probe.pinyin,
                'word': probe.word,
                'found': False,
                'physical_index': None,
                'byte_offset': None,
                'rank': None,
            })
        else:
            located.append({
                'pinyin': probe.pinyin,
                'word': probe.word,
                'found': True,
                'physical_index': record['index'],
                'byte_offset': record['byte_offset'],
                'rank': record['position'],
            })
    return located


def sha256_of(data: bytes) -> str:
    """文件的 SHA-256（十六进制）。"""
    return hashlib.sha256(data).hexdigest()


def build_manifest(*, profile: str, dat_path, data: bytes,
                   selected_entry_count: int, located: List[Dict[str, object]],
                   generated_at: Optional[str] = None) -> Dict[str, object]:
    """生成精简 manifest。

    词条计数一律以**最终文件里的实际记录数**为准（读取阶段选中的条数可能因
    清洗/候选位溢出被丢弃，用它做基准会让 manifest 与文件对不上）。

    记录 profile、词条计数、SHA-256，以及每个探针的拼音/词条/候选位/
    物理索引/字节偏移。
    """
    probes = []
    for item in located:
        probes.append({
            'pinyin': item['pinyin'],
            'word': item['word'],
            'rank': item['rank'],
            'physical_index': item['physical_index'],
            'byte_offset': item['byte_offset'],
        })

    total = sum(1 for _ in iter_physical_records(data))
    canary_count = sum(1 for item in located if item['found'])
    normal_count = max(0, total - canary_count)

    return {
        'format': MANIFEST_FORMAT,
        'profile': profile,
        'generated_at': generated_at,
        'dat_file': dat_path.name if hasattr(dat_path, 'name') else str(dat_path),
        'sha256': sha256_of(data),
        'file_size': len(data),
        'selected_entry_count': selected_entry_count,
        'normal_entry_count': normal_count,
        'canary_entry_count': canary_count,
        'total_entry_count': total,
        'probes': probes,
    }


def write_manifest(manifest_path, manifest: Dict[str, object]) -> None:
    """写出 manifest JSON。"""
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write('\n')


def read_manifest(manifest_path) -> Dict[str, object]:
    """读取 manifest JSON。"""
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)
