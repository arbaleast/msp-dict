# MSPinyin Dict 修复建议方案

> 基于 [`docs/code-quality-analysis.md`](docs/code-quality-analysis.md) 的评估结果，按优先级给出可执行的修复方案

---

## 目录

- [P0 — 立即修复（核心格式错误）](#p0--立即修复核心格式错误)
- [P1 — 架构整合](#p1--架构整合)
- [P2 — 代码质量提升](#p2--代码质量提升)
- [P3 — 测试与文档](#p3--测试与文档)
- [修复路线图](#修复路线图)

---

## P0 — 立即修复（核心格式错误）

### P0-1. 废弃 60 字节固定格式，统一使用 `mschxudp` 格式

**问题：** [`parser.py`](src/parser.py:41-43) 和 [`builder.py`](src/builder.py:16-18) 使用的 `ENTRY_SIZE=60` 固定格式已被 [`builder.py`](src/builder.py:4-6) 自述"验证为错误的"。而 [`builder_win10.py`](src/builder_win10.py) 实现了正确的 `mschxudp` 格式。

**修复步骤：**

#### 步骤 1 — 将 `Win10MSPinyinParser` 重命名为 `MSPinyinParser` 并替换旧实现

修改 [`src/parser.py`](src/parser.py)：

```python
"""
微软拼音用户词库解析器 (mschxudp 格式)

格式来自 imewlconverter Win10MsPinyin.cs:

Header (0x40 bytes):
  0x00: proto 'mschxudp' (8 bytes)
  0x08: unknown 0x00600002 (4 bytes)
  0x0C: version 1 (4 bytes)
  0x10: phrase_offset_start = 0x40 (4 bytes)
  0x14: phrase_start = 0x40 + phrase_count * 4 (4 bytes)
  0x18: phrase_end (4 bytes)
  0x1C: phrase_count (4 bytes)
  0x20: timestamp (8 bytes)
  0x28: reserved 0 (24 bytes)
"""

import struct
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class DictEntry:
    """词库条目"""
    text: str              # 中文文本
    pinyin: str            # 拼音字符串（无空格）
    offset: int = 0        # 词条在文件中的偏移
    rank: int = 1          # 词频排名


class MSPinyinParser:
    """微软拼音用户词库解析器 (mschxudp 格式)"""

    MAGIC = b'mschxudp'

    def __init__(self, filepath: str = None):
        self.filepath = filepath
        self.raw_data: bytes = b''
        self.entries: List[DictEntry] = []
        self.phrase_count = 0

    def load(self, filepath: str) -> int:
        """加载词库文件，返回词条数"""
        self.filepath = filepath
        with open(filepath, 'rb') as f:
            self.raw_data = f.read()

        data = self.raw_data

        # 验证协议头
        if data[0:8] != self.MAGIC:
            raise ValueError(f"无效的 mschxudp 格式: {data[0:8]}")

        # 读取文件头
        phrase_offset_start = struct.unpack('<I', data[16:20])[0]
        phrase_start = struct.unpack('<I', data[20:24])[0]
        phrase_end = struct.unpack('<I', data[24:28])[0]
        phrase_count = struct.unpack('<I', data[28:32])[0]
        self.phrase_count = phrase_count

        # 读取偏移表
        offsets = []
        for i in range(phrase_count):
            off = struct.unpack('<I', data[phrase_offset_start + i * 4:
                                         phrase_offset_start + i * 4 + 4])[0]
            offsets.append(off)
        offsets.append(phrase_end - phrase_start)

        # 读取词条
        self.entries = []
        for i in range(phrase_count):
            pos = phrase_start + offsets[i]
            next_pos = phrase_start + offsets[i + 1]
            entry = self._read_phrase(data, pos, next_pos - pos)
            self.entries.append(entry)

        return phrase_count

    def _read_phrase(self, data: bytes, start: int, entry_size: int) -> DictEntry:
        """读取单个词条"""
        magic = struct.unpack('<I', data[start:start + 4])[0]
        hanzi_offset = struct.unpack('<H', data[start + 4:start + 6])[0]
        rank = data[start + 6]
        unknown_flag = data[start + 7]

        # 拼音长度 = (hanzi_offset - 18) // 2
        pinyin_char_len = (hanzi_offset - 18) // 2
        pinyin_byte_len = pinyin_char_len * 2

        # 拼音开始位置（跳过固定字段：magic+hanoff+rank+flag+unk1+unk2 = 16字节）
        pinyin_start = start + 16
        pinyin_bytes = data[pinyin_start:pinyin_start + pinyin_byte_len]
        pinyin_str = pinyin_bytes.decode('utf-16-le', errors='replace')
        pinyin_str = pinyin_str.replace('\x00', '')

        # 文本开始 = 拼音结束 + 2 (null terminator)
        word_start = pinyin_start + pinyin_byte_len + 2
        word_byte_len = entry_size - (word_start - start) - 2  # -2 for final null
        word_bytes = data[word_start:word_start + word_byte_len]
        word = word_bytes.decode('utf-16-le', errors='replace')
        word = word.replace('\x00', '')

        return DictEntry(
            text=word,
            pinyin=pinyin_str,
            offset=start,
            rank=rank,
        )

    def get_entry_count(self) -> int:
        return len(self.entries)

    def get_all_texts(self) -> List[str]:
        return [e.text for e in self.entries]

    def find_by_text(self, text: str):
        for entry in self.entries:
            if entry.text == text:
                return entry
        return None

    def get_file_size(self) -> int:
        return len(self.raw_data)
```

#### 步骤 2 — 重写 [`src/editor.py`](src/editor.py) 使用新格式

```python
"""
微软拼音词库编辑器 (mschxudp 格式)

支持添加/删除词条，使用重建模式确保词库格式正确
"""

import struct
from typing import List, Tuple, Optional
from .parser import MSPinyinParser, DictEntry
from datetime import datetime


class MSPinyinEditor(MSPinyinParser):
    """微软拼音词库编辑器 (mschxudp 格式)"""

    HEADER_SIZE = 0x40

    def __init__(self, filepath: str = None):
        super().__init__(filepath)
        self._pending_add: List[Tuple[str, str, int]] = []  # (text, pinyin, rank)
        self._pending_remove: set = set()

    def add_entry(self, text: str, pinyin: str = '', rank: int = 1) -> bool:
        """添加词条"""
        if self.raw_data and self.find_by_text(text):
            return False
        self._pending_add.append((text, pinyin, rank))
        return True

    def remove_entry(self, text: str) -> bool:
        """删除词条"""
        if not self.raw_data:
            return False
        if not self.find_by_text(text):
            return False
        self._pending_remove.add(text)
        return True

    def save(self, filepath: str = None) -> None:
        """保存词库（重建模式）"""
        if filepath is None:
            filepath = self.filepath

        # 收集有效词条：过滤 + 新增
        merged = [e for e in self.entries if e.text not in self._pending_remove]
        for text, pinyin, rank in self._pending_add:
            merged.append(DictEntry(text=text, pinyin=pinyin, rank=rank))

        data = self._build_raw(merged)
        with open(filepath, 'wb') as f:
            f.write(data)

        self.raw_data = data
        self._pending_add.clear()
        self._pending_remove.clear()
        # 重新解析
        self.entries = []
        self._rebuild_entries()

    def _build_raw(self, entries: List[DictEntry]) -> bytes:
        """构建 mschxudp 二进制数据"""
        count = len(entries)

        # 计算每个词条大小和累积偏移
        offsets = []
        current = 0
        for e in entries:
            pinyin_bytes = e.pinyin.encode('utf-16-le')
            word_bytes = e.text.encode('utf-16-le')
            entry_size = 4 + 2 + 1 + 1 + 4 + 4 + len(pinyin_bytes) + 2 + len(word_bytes) + 2
            offsets.append(current)
            current += entry_size

        phrase_start = self.HEADER_SIZE + count * 4
        phrase_end = phrase_start + current

        # 构建头部
        header = bytearray(self.HEADER_SIZE)
        header[0:8] = b'mschxudp'
        struct.pack_into('<I', header, 8,  0x00600002)
        struct.pack_into('<I', header, 12, 1)
        struct.pack_into('<I', header, 16, self.HEADER_SIZE)  # phrase_offset_start
        struct.pack_into('<I', header, 20, phrase_start)
        struct.pack_into('<I', header, 24, phrase_end)
        struct.pack_into('<I', header, 28, count)
        struct.pack_into('<Q', header, 32, int(datetime.now().timestamp()))

        # 偏移表
        offset_table = b''.join(struct.pack('<I', off) for off in offsets)

        # 词条数据
        parts = []
        for e in entries:
            pinyin_bytes = e.pinyin.encode('utf-16-le')
            word_bytes = e.text.encode('utf-16-le')
            hanzi_offset = 18 + len(pinyin_bytes)

            entry = b''
            entry += struct.pack('<I', 0x00100010)
            entry += struct.pack('<H', hanzi_offset)
            entry += bytes([e.rank & 0xFF, 0x06])
            entry += struct.pack('<I', 0x00000000)
            entry += struct.pack('<I', 0xE679CD20)
            entry += pinyin_bytes
            entry += struct.pack('<H', 0)
            entry += word_bytes
            entry += struct.pack('<H', 0)
            parts.append(entry)

        return bytes(header) + offset_table + b''.join(parts)

    def _rebuild_entries(self) -> None:
        """从 self.raw_data 重建 self.entries"""
        # 与 MSPinyinParser.load 相同的解析逻辑
        data = self.raw_data
        if len(data) < self.HEADER_SIZE:
            return

        phrase_start = struct.unpack('<I', data[20:24])[0]
        phrase_end = struct.unpack('<I', data[24:28])[0]
        phrase_count = struct.unpack('<I', data[28:32])[0]

        offset_base = struct.unpack('<I', data[16:20])[0]
        offsets = []
        for i in range(phrase_count):
            off = struct.unpack('<I', data[offset_base + i * 4:
                                         offset_base + i * 4 + 4])[0]
            offsets.append(off)
        offsets.append(phrase_end - phrase_start)

        self.entries = []
        for i in range(phrase_count):
            pos = phrase_start + offsets[i]
            size = offsets[i + 1] - offsets[i]
            self.entries.append(self._read_phrase(data, pos, size))
```

**注意：** 上述代码实现了 `parse → edit → save → re-parse` 完整闭环，`_build_raw` 和 `_read_phrase` 互为逆操作。

---

### P0-2. 修复 `cli.py` 导入路径问题

**问题：** [`src/cli.py:14`](src/cli.py:14) 使用 `sys.path.insert(0, ...)` 运行时修改路径，且导入语句使用绝对导入（`from parser import ...`），与 [`__init__.py`](src/__init__.py:12-14) 的相对导入（`from .parser import ...`）不一致。

**修复：** 移除 `sys.path` hack，改为正确的相对导入：

```python
#!/usr/bin/env python3
"""
微软拼音词库 CLI 工具

Usage:
    python -m src.cli <command> [options]
"""

import argparse
import sys
import os

from .parser import MSPinyinParser
from .editor import MSPinyinEditor
from .exporter import Exporter
from .importer import BatchImporter, RimeConverter
from .converter import BidirectionalConverter
```

调用方式也从 `python src/cli.py parse ...` 改为 `python -m src.cli parse ...`。

---

### P0-3. 统一 SPEC.md 与 plan.md 的格式描述

**问题：** [`SPEC.md`](SPEC.md) 说 `0x000-0x0FF (256B 文件头)`, [`plan.md`](plan.md) 说 `0x000-0x3FF (1024B 文件头)`, 代码中用的是 `0x400`。

**修复方向（二选一）：**

| 文档 | 原内容 | 应修改为 |
|------|--------|----------|
| [`SPEC.md`](SPEC.md) | `0x000-0x0FF: 文件头` | 改为 `mschxudp` 格式文档 |
| [`plan.md`](plan.md) | `0x000-0x3FF: 文件头` | 同上 |
| 新增规范文件 | — | 统一为 `mschxudp` 格式的精确规格 |

---

### P0-4. 获取完整的拼音编码算法

**问题：** [`importer.py:39-49`](src/importer.py:39-49) 的 `pinyin_to_code` 是占位符实现，[`converter.py:19-67`](src/converter.py:19-67) 的拼音映射表只覆盖 ~100 个词汇。

**修复方案：**

1. **集成 imewlconverter 的拼音转换逻辑**：开源项目 [imewlconverter](https://github.com/studyzy/imewlconverter) 的 `Win10MsPinyin.cs` 中有完整的拼音→编码转换实现
2. **使用 pypinyin 库**：作为中间方案

```python
# 方案 A: 使用 pypinyin 库
# pip install pypinyin
from pypinyin import pinyin, Style

def get_pinyin_string(text: str) -> str:
    """获取汉字文本的无空格拼音字符串"""
    result = pinyin(text, style=Style.NORMAL, errors='default')
    return ''.join([item[0] for item in result])

# 方案 B: 集成 imewlconverter 的编码算法
# 参考 Win10MsPinyin.GetMSPinyinCode 的实现
def pinyin_to_code(pinyin_str: str) -> bytes:
    """将拼音字符串转换为 mschxudp 内部编码"""
    # 需要反向工程微软拼音的编码算法
    # 初步已知：每个拼音字母对应一个 2 字节编码
    # 参考: https://github.com/studyzy/imewlconverter
    pass
```

---

## P1 — 架构整合

### P1-1. 将 Win10 格式构建集成到 CLI

**问题：** [`builder_win10.py`](src/builder_win10.py) 的 Win10 格式是正确格式，但完全未被集成到 [`cli.py`](src/cli.py) 的命令体系中。

**修复：** 在 CLI 中添加 `build-win10` 子命令：

```python
def cmd_build_win10(args):
    """构建 Win10 mschxudp 格式词库"""
    from .builder_win10 import Win10MSPinyinBuilder

    builder = Win10MSPinyinBuilder()
    count = 0
    with open(args.input, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                builder.add_word(parts[0], parts[1].replace(' ', ''), rank=1)
                count += 1
    builder.save(args.output)
    print(f"构建完成: {count} 词条 → {args.output}")
```

### P1-2. 添加 `parse-win10` 命令

```python
def cmd_parse_win10(args):
    """解析 Win10 mschxudp 格式词库"""
    from .builder_win10 import Win10MSPinyinParser

    parser = Win10MSPinyinParser()
    count = parser.load(args.file)
    print(f"文件: {args.file}")
    print(f"词条数量: {count}")
    for word, pinyin in parser.words[:20]:
        print(f"  {word}: {pinyin}")
```

---

## P2 — 代码质量提升

### P2-1. 合并 `editor.py:save()` 与 `editor.py:rebuild()`

**问题：** 两个方法有几乎完全相同的重建逻辑，只是 `save()` 最后会写文件并 `_parse()`，而 `rebuild()` 只更新 `self.data`。

**修复：** 让 `rebuild()` 调用 `save()` 的内部逻辑，或者将重建逻辑提取为私有方法 `_rebuild_data()`：

```python
def _rebuild_data(self) -> bytes:
    """重建数据区（核心逻辑）"""
    valid = [e for e in self.entries if e.text not in self._removed_texts]
    for text, pinyin_code in self._pending_entries:
        valid.append(DictEntry(offset=0, text=text, pinyin_code=pinyin_code))

    header = self.data[:self.DATA_START]
    new_data = bytearray()
    for entry in valid:
        text_bytes = entry.text.encode('utf-16-le')
        text_len = len(entry.text)
        e = bytearray(self.ENTRY_SIZE)
        struct.pack_into('<I', e, 0, 0)
        struct.pack_into('<I', e, 4, text_len)
        e[8:16] = entry.pinyin_code
        e[16:16 + text_len * 2] = text_bytes
        new_data += bytes(e)
    return header + bytes(new_data)

def save(self, filepath=None):
    self.data = self._rebuild_data()
    with open(filepath or self.filepath, 'wb') as f:
        f.write(self.data)
    self._parse()

def rebuild(self):
    self.data = self._rebuild_data()
```

### P2-2. 消除 `importer.py` 中的重复拼音处理逻辑

**问题：** `import_rime()` 和 `import_csv()` 中的拼音转换（[`importer.py:168-170`](src/importer.py:168-170), [`224-228`](src/importer.py:224-228)）完全相同。

**修复：** 提取为共享方法：

```python
def _normalize_and_encode_pinyin(self, pinyin: Optional[str]) -> Optional[bytes]:
    """规范化并编码拼音"""
    if not pinyin:
        return None
    normalized = self.pinyin_converter.normalize_pinyin(pinyin)
    return self.pinyin_converter.pinyin_to_code(normalized)
```

### P2-3. 移除死代码

| 文件 | 应移除内容 | 说明 |
|------|-----------|------|
| [`parser.py:13-14`](src/parser.py:13-14) | `import io` | 未使用 |
| [`parser.py:17-24`](src/parser.py:17-24) | `PinyinEntry` 数据类 | 定义了但全程未使用 |
| [`builder_win10.py:110-111`](src/builder_win10.py:110-111) | `print(f"已保存: ...")` 中的 `size` 变量 | 仅在 **main** 中有意义 |

### P2-4. 替换魔法数字为具名常量

```python
# 现有问题代码 (builder_win10.py:71,91,95)
header[8:12] = struct.pack('<I', 0x00600002)  # 这是什么？
entry += struct.pack('<I', 0x00100010)          # 这又是什么？
entry += struct.pack('<I', 0xE679CD20)          # 魔数来源不明

# 修复: 添加注释
# 0x00600002: imewlconverter 中固定的版本/标志组合
# 0x00100010: 词条 magic 标识，所有有效词条以此开头
# 0xE679CD20: 固定魔数，imewlconverter 原样保留
```

### P2-5. 扩展 Unicode 汉字范围

**问题：** [`importer.py:251`](src/importer.py:251) 的正则 `[\u4e00-\u9fff]` 不包含扩展区汉字。

**修复：**

```python
# 扩展 Unicode 汉字范围
CJK_UNIFIED_IDEOGRAPHS = (
    '\u4e00-\u9fff'     # 基本区 (20,992 字)
    '\u3400-\u4dbf'     # 扩展A区 (6,592 字)
    '\U00020000-\U0002a6df'  # 扩展B区 (42,720 字)
    '\U0002a700-\U0002b73f'  # 扩展C区 (4,154 字)
    '\U0002b740-\U0002b81f'  # 扩展D区 (222 字)
    '\U0002b820-\U0002ceaf'  # 扩展E区 (5,762 字)
    '\U0002ceb0-\U0002ebef'  # 扩展F区 (7,473 字)
    '\U00030000-\U0003134f'  # 扩展G区 (4,939 字)
    '\U00031350-\U000323af'  # 扩展H区 (4,192 字)
)
CHINESE_PATTERN = re.compile(f'^[{CJK_UNIFIED_IDEOGRAPHS}]+$')
```

---

## P3 — 测试与文档

### P3-1. 添加基本单元测试

创建 [`src/test_win10_format.py`](src/test_win10_format.py)：

```python
"""Win10 mschxudp 格式的构建→解析双向测试"""

import unittest
import os
import tempfile
from .builder_win10 import Win10MSPinyinBuilder, Win10MSPinyinParser


class TestWin10Format(unittest.TestCase):
    """测试 mschxudp 格式的构建→解析一致性"""

    def setUp(self):
        self.tmpfile = tempfile.mktemp(suffix='.dat')

    def tearDown(self):
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def test_build_and_parse_roundtrip(self):
        """构建一组词条→保存→解析→验证文本和拼音"""
        builder = Win10MSPinyinBuilder()
        test_data = [
            ("中国", "zhongguo", 1),
            ("北京", "beijing", 2),
            ("上海", "shanghai", 3),
            ("人工智能", "rengongzhineng", 1),
            ("算法", "suanfa", 5),
        ]
        for word, py, rank in test_data:
            builder.add_word(word, py, rank)
        builder.save(self.tmpfile)

        parser = Win10MSPinyinParser()
        count = parser.load(self.tmpfile)

        self.assertEqual(count, len(test_data))
        for (word, py, _), (parsed_word, parsed_py) in zip(test_data, parser.words):
            self.assertEqual(word, parsed_word)
            self.assertEqual(py, parsed_py)

    def test_empty_build(self):
        """空词库构建测试"""
        builder = Win10MSPinyinBuilder()
        builder.save(self.tmpfile)

        parser = Win10MSPinyinParser()
        count = parser.load(self.tmpfile)
        self.assertEqual(count, 0)

    def test_large_entry(self):
        """较长词汇的构建解析测试"""
        builder = Win10MSPinyinBuilder()
        builder.add_word("中华人民共和国", "zhonghuarenmingongheguo", 1)
        builder.save(self.tmpfile)

        parser = Win10MSPinyinParser()
        count = parser.load(self.tmpfile)
        self.assertEqual(count, 1)
        self.assertEqual(parser.words[0][0], "中华人民共和国")
        self.assertEqual(parser.words[0][1], "zhonghuarenmingongheguo")
```

### P3-2. 整合到 CI 流程

在 `.github/workflows/` 中添加测试步骤：

```yaml
# 在 weekly-build.yml 中添加
- name: Run unit tests
  run: |
    python -m pytest src/ -v
```

---

## 修复路线图

```
时间线                         工作量          依赖
─────────────────────────────────────────────────────────
Week 1: P0 修复               ★★★★★ 3-5天
  ├─ P0-1 格式统一             3天           无
  ├─ P0-2 CLI导入路径          0.5天         无
  ├─ P0-3 规格文档统一         0.5天         P0-1
  └─ P0-4 拼音编码算法         1-2天         P0-1

Week 2: P1 架构整合             ★★★ 2-3天
  ├─ P1-1 CLI Win10构建命令    1天           P0-1
  └─ P1-2 CLI Win10解析命令    0.5天         P0-1

Week 3: P2 代码质量提升         ★★ 1-2天
  ├─ P2-1 合并重复代码         0.5天         无
  ├─ P2-2 提取共享方法         0.5天         无
  ├─ P2-3 移除死代码           0.5天         无
  ├─ P2-4 魔法数字注释         0.5天         无
  └─ P2-5 Unicode扩展          0.5天         无

Week 4: P3 测试与文档           ★★ 1-2天
  ├─ P3-1 单元测试             1天           P0-1
  └─ P3-2 CI集成               0.5天         P3-1
─────────────────────────────────────────────────────────

总计: ~8-12 人日
```

---

## 关键决策点

在开始修复前需要确定的几个问题：

| # | 决策 | 选项 | 建议 |
|---|------|------|------|
| D1 | 是否继续支持旧 60 字节格式 | A) 完全废弃 B) 保留 parser 只读 | **A)** 代码已自述格式错误，保留只会误导 |
| D2 | 拼音编码来源 | A) pypinyin B) imewlconverter 移植 C) 自建映射 | **B)** 与 mschxudp 格式来源一致，兼容性最好 |
| D3 | 包命名方式 | A) `src.xxx` B) 改为 `mspinyin.xxx` | **B)** `src` 不是合法包名，应改为 `mspinyin` |
| D4 | 测试框架 | A) unittest B) pytest | **B)** 社区主流，断言更简洁 |
