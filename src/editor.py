"""
微软拼音词库编辑器 (mschxudp 格式 ✅)

支持添加/删除词条，使用重建模式确保词库格式正确。

注意: 旧版 editor.py 继承自 60 字节固定格式的 MSPinyinParser，
     该格式已被验证为错误的。此文件为 mschxudp 格式的重新实现。
"""

import logging
from typing import Dict, List
from datetime import datetime
from .parser import MSPinyinParser, DictEntry
from .builder_win10 import Win10MSPinyinBuilder

logger = logging.getLogger(__name__)


class MSPinyinEditor(MSPinyinParser):
    """微软拼音词库编辑器 (mschxudp 格式)"""

    HEADER_SIZE = 0x40

    def __init__(self, filepath: str = None):
        super().__init__(filepath)
        # 已加载词条的哈希索引: text -> DictEntry（首次出现者优先）
        self._index: Dict[str, DictEntry] = {}
        # 待添加的词条: text -> DictEntry（dict 保序，等价于原列表顺序）
        self._pending_add: Dict[str, DictEntry] = {}
        # 待删除的词条文本
        self._pending_remove: set = set()
        # 最近一次保存时的构建统计（可用于提示被清洗拦截的词条）
        self.last_build_stats = None

    def add_entry(self, text: str, pinyin: str = '', rank: int = 1) -> bool:
        """添加新词条（标记待添加，保存时重建）

        通过哈希索引判断重复，单条 O(1)；批量导入整体 O(N)，不再随已加载
        词条数线性增长。

        Args:
            text: 中文文本
            pinyin: 拼音字符串（无空格，如 "zhongguo"）
            rank: 来源词频，构建器只用它决定同音候选顺序与三档筛选

        Returns:
            是否添加成功（已存在的词条返回 False）
        """
        # 首次使用前必须加载文件
        if not self.raw_data:
            return False

        # 检查是否已存在（已加载索引 + 待添加索引，均为 O(1)）
        if text in self._index or text in self._pending_add:
            return False

        self._pending_add[text] = DictEntry(text=text, pinyin=pinyin, rank=rank)
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

        # 只有已加载的词条可删除（与旧语义一致：待添加项不可撤销）
        if text not in self._index or text in self._pending_remove:
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

        if self.last_build_stats and self.last_build_stats.skipped:
            logger.warning("保存时拦截 %d 条不合规词条: %s",
                           self.last_build_stats.skipped,
                           self.last_build_stats.summary())

    def _collect_entries(self) -> List[DictEntry]:
        """收集最终词条列表：过滤已删除 + 合并新增（保持原有顺序语义）"""
        merged = [e for e in self.entries if e.text not in self._pending_remove]
        merged.extend(self._pending_add.values())
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
        data = builder.build()
        self.last_build_stats = builder.stats
        return data

    def parse_bytes(self, data: bytes, strict: bool = False) -> int:
        """解析后同步重建文本索引，保证 find_by_text/add_entry 与底层列表一致。"""
        count = super().parse_bytes(data, strict=strict)
        self._rebuild_index()
        return count

    def _rebuild_index(self) -> None:
        self._index = {}
        for entry in self.entries:
            # 同一文本重复出现时，find_by_text 旧实现返回第一条
            self._index.setdefault(entry.text, entry)

    def _reload_entries(self) -> None:
        """从 self.raw_data 重新构建 self.entries 与索引"""
        self.entries = []
        if self.raw_data:
            self.parse_bytes(self.raw_data)

    def find_by_text(self, text: str):
        """按文本查找词条（哈希索引，O(1)）"""
        entry = self._index.get(text)
        if entry is not None:
            return entry
        return self._pending_add.get(text)

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
