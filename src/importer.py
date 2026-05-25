"""
微软拼音词库批量导入器 (mschxudp 格式)

支持从多种格式批量导入词条:
- TXT: 每行一个词条
- CSV: 文本,拼音 格式
- Rime: 词条\t拼音 格式
"""

import csv
import re
from typing import List, Tuple, Optional, Dict
from pathlib import Path


class PinyinConverter:
    """拼音转换器 - 处理拼音字符串的规范化"""

    # 声调字符映射表
    TONE_MAP = {
        'ā': 'a', 'á': 'a', 'ǎ': 'a', 'à': 'a',
        'ē': 'e', 'é': 'e', 'ě': 'e', 'è': 'e',
        'ī': 'i', 'í': 'i', 'ǐ': 'i', 'ì': 'i',
        'ō': 'o', 'ó': 'o', 'ǒ': 'o', 'ò': 'o',
        'ū': 'u', 'ú': 'u', 'ǔ': 'u', 'ù': 'u',
        'ǖ': 'ü', 'ǘ': 'ü', 'ǚ': 'ü', 'ǜ': 'ü',
        'Ā': 'a', 'Á': 'a', 'Ǎ': 'a', 'À': 'a',
        'Ē': 'e', 'É': 'e', 'Ě': 'e', 'È': 'e',
        'Ī': 'i', 'Í': 'i', 'Ǐ': 'i', 'Ì': 'i',
        'Ō': 'o', 'Ó': 'o', 'Ǒ': 'o', 'Ò': 'o',
        'Ū': 'u', 'Ú': 'u', 'Ǔ': 'u', 'Ù': 'u',
        'Ǖ': 'ü', 'Ǘ': 'ü', 'Ǚ': 'ü', 'Ǜ': 'ü',
    }

    @staticmethod
    def normalize_pinyin(pinyin: str) -> str:
        """规范化拼音字符串:
        - 去除空格
        - 转换为小写
        - 移除声调标记 (ā → a, á → a, ...)

        Args:
            pinyin: 原始拼音字符串

        Returns:
            规范化后的无空格拼音字符串
        """
        # 先去掉空格
        pinyin = pinyin.replace(' ', '').lower()

        # 移除声调标记
        for k, v in PinyinConverter.TONE_MAP.items():
            pinyin = pinyin.replace(k.lower(), v)

        return pinyin

    @staticmethod
    def is_valid_pinyin(pinyin: str) -> bool:
        """检查拼音字符串是否有效（仅含字母）"""
        return bool(re.match(r'^[a-z]+$', pinyin))


class BatchImporter:
    """批量导入器"""

    def __init__(self, editor):
        self.editor = editor
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def _add_entry(self, text: str, pinyin_str: str = '', rank: int = 1) -> bool:
        """通用添加词条方法

        Args:
            text: 中文文本
            pinyin_str: 拼音字符串（可含空格，会被自动规范化）
            rank: 词频排名

        Returns:
            是否添加成功
        """
        # 规范化拼音
        if pinyin_str:
            pinyin_str = PinyinConverter.normalize_pinyin(pinyin_str)

        # 调用 editor 的 add_entry (text, pinyin, rank)
        return self.editor.add_entry(text, pinyin_str, rank)

    def _is_valid_chinese(self, text: str) -> bool:
        """检查文本是否有效

        支持的文本类型:
        - 纯中文: 所有字符都在 Unicode CJK 范围内
        - 纯英文项目名: 字母、数字、点、减号、下划线
        - 混合型: 至少包含一个中文字符

        注意: 包含扩展区汉字 (\u3400-\u4dbf 等) 也视为有效
        """
        # 中文字符 Unicode 范围（包含扩展区）
        CJK_PATTERN = re.compile(
            r'[\u4e00-\u9fff'        # 基本区
            r'\u3400-\u4dbf'         # 扩展A区
            r'\uf900-\ufaff'         # 兼容区
            r']'
        )
        ENGLISH_PATTERN = re.compile(r'^[a-zA-Z0-9._\-\s]+$')

        # 纯英文 - 可以导入
        if ENGLISH_PATTERN.match(text):
            return True

        # 至少包含一个中文
        return bool(CJK_PATTERN.search(text))

    def import_txt(self, filepath: str) -> Tuple[int, int, int]:
        """从 TXT 文件批量导入

        格式: 每行一个词条，可选制表符分隔拼音

        示例:
            中国\tzhongguo
            北京

        Args:
            filepath: TXT 文件路径

        Returns:
            (成功数, 跳过数, 错误数)
        """
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0

        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                parts = line.split('\t')
                text = parts[0].strip()
                pinyin = parts[1].strip() if len(parts) > 1 else ''

                if not text:
                    continue

                if not self._is_valid_chinese(text):
                    self.skipped_count += 1
                    continue

                try:
                    if self._add_entry(text, pinyin):
                        self.imported_count += 1
                    else:
                        self.skipped_count += 1  # 已存在
                except Exception as e:
                    self.error_count += 1
                    print(f"第 {line_num} 行错误: {e}")

        return (self.imported_count, self.skipped_count, self.error_count)

    def import_csv(self, filepath: str, text_col: int = 0,
                   pinyin_col: int = 1) -> Tuple[int, int, int]:
        """从 CSV 文件批量导入

        Args:
            filepath: CSV 文件路径
            text_col: 文本列索引（默认 0）
            pinyin_col: 拼音列索引（默认 1）

        Returns:
            (成功数, 跳过数, 错误数)
        """
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0

        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # 跳过表头

            for row_num, row in enumerate(reader, 1):
                if len(row) <= max(text_col, pinyin_col):
                    self.error_count += 1
                    continue

                text = row[text_col].strip()
                pinyin = row[pinyin_col].strip() if pinyin_col < len(row) else ''

                if not text:
                    continue

                if not self._is_valid_chinese(text):
                    self.skipped_count += 1
                    continue

                try:
                    if self._add_entry(text, pinyin):
                        self.imported_count += 1
                    else:
                        self.skipped_count += 1
                except Exception as e:
                    self.error_count += 1
                    print(f"第 {row_num} 行错误: {e}")

        return (self.imported_count, self.skipped_count, self.error_count)

    def import_rime(self, filepath: str) -> Tuple[int, int, int]:
        """从 Rime 词库格式批量导入

        Rime 格式:
            词条\t拼音\t词频（可选）
            词条\t拼音

        跳过以 # 或 --- 开头的行

        Args:
            filepath: Rime 词库文件路径

        Returns:
            (成功数, 跳过数, 错误数)
        """
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0

        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('---'):
                    continue

                parts = line.split('\t')
                text = parts[0].strip()
                pinyin = parts[1].strip() if len(parts) > 1 else ''

                # Rime 有时带词频: 词条\t拼音\t词频
                rank = 1
                if len(parts) >= 3 and parts[2].strip().isdigit():
                    rank = int(parts[2].strip())

                if not text:
                    continue

                if not self._is_valid_chinese(text):
                    self.skipped_count += 1
                    continue

                try:
                    if self._add_entry(text, pinyin, rank):
                        self.imported_count += 1
                    else:
                        self.skipped_count += 1
                except Exception as e:
                    self.error_count += 1
                    print(f"第 {line_num} 行错误: {e}")

        return (self.imported_count, self.skipped_count, self.error_count)

    def get_stats(self) -> Dict[str, int]:
        """获取导入统计"""
        return {
            'imported': self.imported_count,
            'skipped': self.skipped_count,
            'errors': self.error_count,
            'total': self.imported_count + self.skipped_count + self.error_count,
        }


class RimeConverter:
    """Rime 词库格式转换器"""

    @staticmethod
    def detect_format(filepath: str) -> str:
        """检测文件格式

        Returns:
            'rime', 'csv', 'tsv', 'txt', 或 'unknown'
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                first_lines = [f.readline() for _ in range(10)]

            # 检测 Rime 格式（包含 --- 分隔符）
            if any('---' in line for line in first_lines):
                return 'rime'

            # 检测 CSV 格式（逗号分隔，无双引号时无制表符）
            if any(',' in line and '\t' not in line for line in first_lines if line.strip()):
                return 'csv'

            # 检测 TSV 格式（制表符分隔）
            if any('\t' in line for line in first_lines if line.strip()):
                return 'tsv'

            return 'txt'
        except Exception:
            return 'unknown'

    @staticmethod
    def parse_rime_dict(filepath: str) -> List[Tuple[str, str]]:
        """解析 Rime 词库文件

        Args:
            filepath: Rime 词库文件路径

        Returns:
            [(词条, 拼音), ...] 列表
        """
        entries = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('---'):
                    continue

                parts = line.split('\t')
                text = parts[0].strip()
                pinyin = parts[1].strip() if len(parts) >= 2 else ''

                if text:
                    entries.append((text, pinyin))
        return entries

    @staticmethod
    def generate_rime_dict(entries: List[Tuple[str, str]], output_path: str,
                           include_pinyin: bool = True) -> int:
        """生成 Rime 词库文件

        Args:
            entries: [(词条, 拼音), ...] 列表
            output_path: 输出文件路径
            include_pinyin: 是否包含拼音

        Returns:
            写入的词条数量
        """
        count = 0
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("""# Rime 词库
# 格式: 词条\t拼音
# 来源: MSPinyin Dict

""")
            for text, pinyin in entries:
                if include_pinyin and pinyin:
                    f.write(f"{text}\t{pinyin}\n")
                else:
                    f.write(f"{text}\n")
                count += 1
        return count


def main():
    """测试批量导入器"""
    import sys

    if len(sys.argv) < 3:
        print("用法: python importer.py <mschxudp.dat> <import_file>")
        sys.exit(1)

    from .editor import MSPinyinEditor

    dat_file = sys.argv[1]
    import_file = sys.argv[2]

    # 检测格式
    fmt = RimeConverter.detect_format(import_file)
    print(f"检测到格式: {fmt}")

    # 加载编辑器
    editor = MSPinyinEditor()
    editor.load(dat_file)

    print(f"当前词条数: {editor.get_entry_count()}")

    # 导入
    importer = BatchImporter(editor)

    if fmt == 'rime':
        result = importer.import_rime(import_file)
    elif fmt == 'csv':
        result = importer.import_csv(import_file)
    else:
        result = importer.import_txt(import_file)

    stats = importer.get_stats()
    print(f"\n导入结果:")
    print(f"  成功: {stats['imported']}")
    print(f"  跳过: {stats['skipped']}")
    print(f"  错误: {stats['errors']}")

    # 保存
    if stats['imported'] > 0:
        editor.save(dat_file)
        print(f"\n已保存到: {dat_file}")
        print(f"新词条数: {editor.get_entry_count()}")


if __name__ == '__main__':
    main()
