"""
微软拼音词库编辑器 (mschxudp 格式 ✅)

支持添加/删除词条，使用重建模式确保词库格式正确。

注意: 旧版 editor.py 继承自 60 字节固定格式的 MSPinyinParser，
     该格式已被验证为错误的。此文件为 mschxudp 格式的重新实现。
"""

import struct
from typing import List, Tuple
from datetime import datetime
from .parser import MSPinyinParser, DictEntry
from .builder_win10 import Win10MSPinyinBuilder


class MSPinyinEditor(MSPinyinParser):
    """微软拼音词库编辑器 (mschxudp 格式)"""

    HEADER_SIZE = 0x40

    def __init__(self, filepath: str = None):
        super().__init__(filepath)
        # 待添加的词条: (text, pinyin, rank)
        self._pending_add: List[Tuple[str, str, int]] = []
        # 待删除的词条文本
        self._pending_remove: set = set()

    def add_entry(self, text: str, pinyin: str = '', rank: int = 1) -> bool:
        """添加新词条（标记待添加，保存时重建）

        Args:
            text: 中文文本
            pinyin: 拼音字符串（无空格，如 "zhongguo"）
            rank: 词频排名，值越小越靠前

        Returns:
            是否添加成功（已存在的词条返回 False）
        """
        # 首次使用前必须加载文件
        if not self.raw_data:
            return False

        # 检查是否已存在（包括待添加列表）
        if self.find_by_text(text):
            return False
        for t, _, _ in self._pending_add:
            if t == text:
                return False

        self._pending_add.append((text, pinyin, rank))
        return True

    def remove_entry(self, text: str) -> bool:
        """删除词条（标记待删除，保存时重建）

        Args:
            text: 要删除的文本

        Returns:
            是否删除成功（不存在的词条返回 False）
        """
        if not self.raw_data:
            return False

        entry = self.find_by_text(text)
        if entry is None:
            return False

        self._pending_remove.add(text)
        return True

    def save(self, filepath: str = None) -> None:
        """保存词库文件（自动重建模式）

        Args:
            filepath: 保存路径，为 None 则覆盖原文件
        """
        if filepath is None:
            filepath = self.filepath
        if filepath is None:
            raise ValueError("未指定保存路径")

        # 构建新的二进制数据（复用 Win10MSPinyinBuilder 避免重复逻辑）
        data = self._build_data()
        with open(filepath, 'wb') as f:
            f.write(data)

        # 更新内部状态
        self.raw_data = data
        self._pending_add.clear()
        self._pending_remove.clear()

        # 重新解析以保持一致
        self._reload_entries()

    def _collect_entries(self) -> List[DictEntry]:
        """收集最终词条列表：过滤已删除 + 合并新增"""
        merged = [e for e in self.entries if e.text not in self._pending_remove]
        for text, pinyin, rank in self._pending_add:
            merged.append(DictEntry(
                text=text,
                pinyin=pinyin,
                rank=rank,
            ))
        return merged

    def _build_data(self) -> bytes:
        """构建 mschxudp 格式的完整二进制数据

        完全委托给 Win10MSPinyinBuilder 进行构建,
        消除与 builder_win10.py 之间所有重复的序列化逻辑。
        """
        entries = self._collect_entries()
        builder = Win10MSPinyinBuilder(timestamp=int(datetime.now().timestamp()))
        for e in entries:
            builder.add_word(e.text, e.pinyin, e.rank)
        return builder.build()

    def _reload_entries(self) -> None:
        """从 self.raw_data 重新构建 self.entries"""
        self.entries = []
        data = self.raw_data
        if len(data) < self.HEADER_SIZE:
            return

        # 复用与 MSPinyinParser.load 相同的解析逻辑
        phrase_start = struct.unpack('<I', data[20:24])[0]
        phrase_end = struct.unpack('<I', data[24:28])[0]
        phrase_count = struct.unpack('<I', data[28:32])[0]

        offset_base = struct.unpack('<I', data[16:20])[0]
        offsets = []
        for i in range(phrase_count):
            off = struct.unpack(
                '<I',
                data[offset_base + i * 4: offset_base + i * 4 + 4]
            )[0]
            offsets.append(off)
        offsets.append(phrase_end - phrase_start)

        for i in range(phrase_count):
            pos = phrase_start + offsets[i]
            size = offsets[i + 1] - offsets[i]
            entry = self._read_phrase(data, pos, size)
            if entry is not None:
                self.entries.append(entry)

    def get_stats(self) -> dict:
        """获取词库统计信息"""
        texts = [e.text for e in self.entries]
        lengths = [len(t) for t in texts]

        return {
            'total_entries': len(self.entries),
            'pending_add': len(self._pending_add),
            'pending_remove': len(self._pending_remove),
            'file_size': self.get_file_size(),
            'avg_length': sum(lengths) / len(lengths) if lengths else 0,
            'max_length': max(lengths) if lengths else 0,
            'single_char': sum(1 for l in lengths if l == 1),
            'double_char': sum(1 for l in lengths if l == 2),
            'triple_char': sum(1 for l in lengths if l == 3),
            'quad_char': sum(1 for l in lengths if l == 4),
            'longer': sum(1 for l in lengths if l > 4),
        }


def main():
    """测试编辑器"""
    import sys
    import tempfile
    import os

    # 创建一个测试词库
    from .builder_win10 import Win10MSPinyinBuilder

    builder = Win10MSPinyinBuilder()
    builder.add_word("测试", "ceshi", rank=1)
    builder.add_word("词库", "ciku", rank=2)
    builder.add_word("编辑器", "bianjiqi", rank=3)

    tmpfile = tempfile.mktemp(suffix='_test_editor.dat')
    builder.save(tmpfile)

    print(f"测试文件: {tmpfile}")

    # 测试编辑
    editor = MSPinyinEditor()
    count = editor.load(tmpfile)
    print(f"加载词条数: {count}")

    # 添加新词条
    assert editor.add_entry("机器学习", "jiqixuexi", rank=1), "添加失败"
    assert editor.add_entry("深度学习", "shenduxuexi", rank=2), "添加失败"
    assert not editor.add_entry("测试", "ceshi", rank=5), "重复添加应返回 False"

    # 删除词条
    assert editor.remove_entry("词库"), "删除失败"
    assert not editor.remove_entry("不存在"), "删除不存在的词条应返回 False"

    # 保存并重新加载
    output = tmpfile + '_modified.dat'
    editor.save(output)

    # 验证
    from .parser import MSPinyinParser
    verifier = MSPinyinParser()
    vcount = verifier.load(output)

    print(f"修改后词条数: {vcount}")
    for entry in verifier.entries:
        print(f"  {entry.text}  [{entry.pinyin}] (rank={entry.rank})")

    expected = {"测试", "编辑器", "机器学习", "深度学习"}
    actual = set(verifier.get_all_texts())
    assert actual == expected, f"词条不匹配: expected={expected}, actual={actual}"
    print(f"✅ 编辑验证通过: {actual}")

    # 清理
    os.remove(tmpfile)
    os.remove(output)


if __name__ == '__main__':
    main()
