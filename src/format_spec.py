"""
mschxudp（微软拼音 Win10/11 用户自定义短语）格式规范常量与通用校验。

本模块是构建器、解析器、校验器和发布脚本的唯一事实来源，避免各处常量漂移。

格式依据（2026-11 核对）:
  - imewlconverter: src/ImeWlConverter.Formats/Win10Ms/MsChxUdpExporterBase.cs
  - imewlconverter: src/ImeWlConverter.Formats/Win10Ms/MsChxUdpImporterBase.cs
  - Win10 1703 实测文件头（imewlconverter 注释中的 hexdump）

文件布局::

    Header (0x40 bytes)
      0x00  proto  'mschxudp' (8 bytes)
      0x08  unknown 0x00600002 (uint32)
      0x0C  version 1 (uint32)
      0x10  phrase_offset_start = 0x40 (uint32)
      0x14  phrase_start = 0x40 + phrase_count * 4 (uint32)
      0x18  phrase_end   = 文件总大小 (uint32)
      0x1C  phrase_count (uint32)
      0x20  timestamp (Unix 秒, uint64)
      0x28  保留, 必须全 0 (24 bytes)

    Offset Table (phrase_count * 4 bytes)
      每条记录相对 phrase_start 的偏移, 严格递增, 首项为 0

    记录区
      0x00  magic 0x00100010 (uint32)
      0x04  hanzi_offset (uint16) = 18 + 拼音 UTF-16LE 字节数
      0x06  候选序号 (uint8)  同一编码内从 1 起；微软拼音 UI 只展示 1~9
      0x07  固定 0x06
      0x08  uint32 0
      0x0C  uint32 2000-01-01 起的秒数（不是词频！）
      0x10  拼音 UTF-16LE（仅 a-z 与 '，最多 32 个 UTF-16 单元）
            + 0x0000 分隔
            词 UTF-16LE（1~64 个 UTF-16 单元）
            + 0x0000 结尾
"""

import re

# ---- 文件头 ----
MAGIC = b'mschxudp'
HEADER_SIZE = 0x40
HEADER_FLAG = 0x00600002
HEADER_VERSION = 1
PHRASE_OFFSET_START = HEADER_SIZE   # 偏移表紧接文件头

OFF_PROTO = 0
OFF_FLAG = 8
OFF_VERSION = 12
OFF_PHRASE_OFFSET_START = 16
OFF_PHRASE_START = 20
OFF_PHRASE_END = 24
OFF_PHRASE_COUNT = 28
OFF_TIMESTAMP = 32

# ---- 记录 ----
ENTRY_MAGIC = 0x00100010
ENTRY_HEAD_BASE = 16          # magic(4) + hanzi_offset(2) + position(1) + flag(1) + unk(4) + ts(4)
ENTRY_FLAG = 0x06
ENTRY_HANZI_OFFSET_BASE = 18  # = ENTRY_HEAD_BASE + 2（拼音后的 0x0000 分隔符）
ENTRY_SPLIT = 0x0000

# ---- 字段上限（来源: imewlconverter MsChxUdpExporterBase）----
MAX_CODE_UNITS = 32           # 拼音编码最多 32 个 UTF-16 单元
MAX_WORD_UNITS = 64           # 词条最多 64 个 UTF-16 单元
MAX_IMPORT_ENTRIES = 20000    # 微软拼音单次导入/用户词库上限，超出 Windows 侧无法容纳
MAX_CANDIDATE_POSITION = 9    # UI 候选框只有 9 个位置

# 词库规模分级（用于三档发布与 UI 卡死预警）
LITE_MAX_ENTRIES = 20000      # 精简版软上限
STANDARD_MAX_ENTRIES = 50000  # 标准版软上限
UI_WARN_ENTRIES = 20000       # 超过此值，UWP 设置页开始明显卡顿，且参考实现会截断
UI_FREEZE_ENTRIES = 50000     # 超过此值，设置页「用户自定义短语」可能假死

# 拼音：只允许小写字母与音节分隔符 '
PINYIN_PATTERN = re.compile(r"^[a-z']+$")

# 声调字符 -> 无调字母（ü 统一转 v，与微软拼音输入习惯一致）
TONE_MAP = {
    'ā': 'a', 'á': 'a', 'ǎ': 'a', 'à': 'a',
    'ē': 'e', 'é': 'e', 'ě': 'e', 'è': 'e',
    'ī': 'i', 'í': 'i', 'ǐ': 'i', 'ì': 'i',
    'ō': 'o', 'ó': 'o', 'ǒ': 'o', 'ò': 'o',
    'ū': 'u', 'ú': 'u', 'ǔ': 'u', 'ù': 'u',
    'ǖ': 'v', 'ǘ': 'v', 'ǚ': 'v', 'ǜ': 'v',
    'ü': 'v',
}

# 2000-01-01 00:00:00 UTC 的 Unix 秒
EPOCH_2000_UNIX = 946684800


def utf16_units(text: str) -> int:
    """字符串的 UTF-16 码元数量（BMP 字符 1, 代理对 2）。"""
    return len(text.encode('utf-16-le')) // 2


def has_unpaired_surrogate(text: str) -> bool:
    """是否含孤立代理项（无法编码为合法的 UTF-16LE）。"""
    try:
        text.encode('utf-16-le')
    except UnicodeEncodeError:
        return True
    return False


def has_forbidden_char(text: str) -> bool:
    """是否含 NUL 或其他控制字符（会破坏以 0x0000 分帧的记录）。"""
    return any(ord(ch) == 0 or ord(ch) < 0x20 or ord(ch) == 0x7F for ch in text)


def is_valid_pinyin(code: str) -> bool:
    """拼音编码是否合法：非空、仅 a-z 与 '、首尾与连续 ' 不合法。"""
    if not code or not PINYIN_PATTERN.match(code):
        return False
    if code.startswith("'") or code.endswith("'") or "''" in code:
        return False
    return True


def normalize_pinyin(pinyin: str) -> str:
    """规范化拼音：去空格、转小写、去声调、ü -> v。

    只做「把一个合法拼音写成规范形式」的转换，不做音节切分；
    无法转换的字符（数字、符号等）保留，交给 is_valid_pinyin 拦截。
    """
    pinyin = (pinyin or '').strip().replace(' ', '').lower()
    for tone, plain in TONE_MAP.items():
        pinyin = pinyin.replace(tone, plain)
    return pinyin
