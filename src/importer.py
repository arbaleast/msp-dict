"""
微软拼音词库批量导入器

支持从多种格式批量导入词条：
- TXT: 每行一个词条
- CSV: 文本,拼音 格式
- Rime: 词条\t拼音 格式
"""

import csv
import re
from typing import List, Tuple, Optional, Dict
from pathlib import Path


class PinyinConverter:
    """拼音转换器 - 将拼音字符串转换为 MSPinyin 内部编码"""
    
    # 声母表
    SHENGMU = [
        'b', 'p', 'm', 'f', 'd', 't', 'n', 'l', 'g', 'k', 'h',
        'j', 'q', 'x', 'zh', 'ch', 'sh', 'r', 'z', 'c', 's', 'y', 'w'
    ]
    
    # 声调表 (GBK 编码的声调字符)
    TONES = ['ā', 'á', 'ǎ', 'à', 'a']
    
    @staticmethod
    def pinyin_to_code(pinyin: str) -> bytes:
        """
        将拼音字符串转换为 MSPinyin 内部编码
        
        Args:
            pinyin: 拼音字符串，如 "yi", "wan", "zi"
            
        Returns:
            8 字节的拼音编码
        """
        # 这是一个占位符实现
        # 实际的编码算法需要反向工程微软拼音的编码
        # 目前使用简单的基于字符串的编码
        code = bytearray(8)
        
        # 计算拼音的简单哈希
        pinyin_bytes = pinyin.encode('gbk')
        for i, b in enumerate(pinyin_bytes[:8]):
            code[i] = b
            
        return bytes(code)
    
    @staticmethod
    def normalize_pinyin(pinyin: str) -> str:
        """
        规范化拼音字符串
        
        - 去除空格
        - 转换为小写
        - 移除声调标记
        """
        # 去除空格
        pinyin = pinyin.replace(' ', '').lower()
        
        # 移除声调标记 (á, à, etc.)
        # 这是一个简化实现
        tone_map = {
            'ā': 'a', 'á': 'a', 'ǎ': 'a', 'à': 'a',
            'ē': 'e', 'é': 'e', 'ě': 'e', 'è': 'e',
            'ī': 'i', 'í': 'i', 'ǐ': 'i', 'ì': 'i',
            'ō': 'o', 'ó': 'o', 'ǒ': 'o', 'ò': 'o',
            'ū': 'u', 'ú': 'u', 'ǔ': 'u', 'ù': 'u',
            'ǖ': 'ü', 'ǘ': 'ü', 'ǚ': 'ü', 'ǜ': 'ü',
        }
        for k, v in tone_map.items():
            pinyin = pinyin.replace(k, v)
            
        return pinyin


class BatchImporter:
    """批量导入器"""
    
    def __init__(self, editor):
        self.editor = editor
        self.pinyin_converter = PinyinConverter()
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0
        
    def import_txt(self, filepath: str, pinyin_mode: str = 'auto') -> Tuple[int, int, int]:
        """
        从 TXT 文件批量导入
        
        Args:
            filepath: TXT 文件路径
            pinyin_mode: 拼音模式
                - 'auto': 自动生成拼音编码
                - 'skip': 跳过（需要外部提供拼音）
                
        Returns:
            (成功数, 跳过数, 错误数)
        """
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                text = line.strip()
                
                if not text:
                    continue
                    
                # 过滤掉包含非中文的词条
                if not self._is_valid_chinese(text):
                    self.skipped_count += 1
                    continue
                    
                # 尝试添加词条
                try:
                    if self.editor.add_entry(text):
                        self.imported_count += 1
                    else:
                        self.skipped_count += 1  # 已存在
                except Exception as e:
                    self.error_count += 1
                    print(f"Error at line {line_num}: {e}")
                    
        return (self.imported_count, self.skipped_count, self.error_count)
        
    def import_csv(self, filepath: str, text_col: int = 0, pinyin_col: int = 1) -> Tuple[int, int, int]:
        """
        从 CSV 文件批量导入
        
        Args:
            filepath: CSV 文件路径
            text_col: 文本列索引
            pinyin_col: 拼音列索引
                
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
                pinyin = row[pinyin_col].strip() if pinyin_col < len(row) else None
                
                if not text:
                    continue
                    
                # 过滤非中文
                if not self._is_valid_chinese(text):
                    self.skipped_count += 1
                    continue
                    
                # 转换拼音
                pinyin_code = None
                if pinyin:
                    normalized = self.pinyin_converter.normalize_pinyin(pinyin)
                    pinyin_code = self.pinyin_converter.pinyin_to_code(normalized)
                    
                try:
                    if self.editor.add_entry(text, pinyin_code):
                        self.imported_count += 1
                    else:
                        self.skipped_count += 1
                except Exception as e:
                    self.error_count += 1
                    print(f"Error at row {row_num}: {e}")
                    
        return (self.imported_count, self.skipped_count, self.error_count)
        
    def import_rime(self, filepath: str) -> Tuple[int, int, int]:
        """
        从 Rime 词库格式批量导入
        
        Rime 格式: 词条\t拼音
        
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
                
                if not line or line.startswith('#'):
                    continue
                    
                # Rime 格式: 词条\t拼音
                parts = line.split('\t')
                
                if len(parts) < 1:
                    continue
                    
                text = parts[0].strip()
                pinyin = parts[1].strip() if len(parts) > 1 else None
                
                if not text:
                    continue
                    
                # 过滤非中文
                if not self._is_valid_chinese(text):
                    self.skipped_count += 1
                    continue
                    
                # 转换拼音
                pinyin_code = None
                if pinyin:
                    normalized = self.pinyin_converter.normalize_pinyin(pinyin)
                    pinyin_code = self.pinyin_converter.pinyin_to_code(normalized)
                    
                try:
                    if self.editor.add_entry(text, pinyin_code):
                        self.imported_count += 1
                    else:
                        self.skipped_count += 1
                except Exception as e:
                    self.error_count += 1
                    print(f"Error at line {line_num}: {e}")
                    
        return (self.imported_count, self.skipped_count, self.error_count)
        
    def _is_valid_chinese(self, text: str) -> bool:
        """
        检查文本是否有效（中文或英文项目名）
        
        Args:
            text: 要检查的文本
            
        Returns:
            是否有效
        """
        # 中文字符 Unicode 范围
        chinese_pattern = re.compile(r'^[\u4e00-\u9fff]+$')
        
        # 纯中文 - OK
        if chinese_pattern.match(text):
            return True
            
        # 英文项目名 (字母、数字、点、减号、下划线)
        english_pattern = re.compile(r'^[a-zA-Z0-9._-]+$')
        if english_pattern.match(text):
            return True
            
        # 混合型: 至少有一个中文
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        return chinese_chars >= 1
        
    def get_stats(self) -> Dict[str, int]:
        """获取导入统计"""
        return {
            'imported': self.imported_count,
            'skipped': self.skipped_count,
            'errors': self.error_count,
            'total': self.imported_count + self.skipped_count + self.error_count
        }


class RimeConverter:
    """Rime 词库格式转换器"""
    
    # Rime 拼音方案特征
    RIME_MARKER = '---'
    
    @staticmethod
    def detect_format(filepath: str) -> str:
        """
        检测文件格式
        
        Returns:
            'rime', 'csv', 'txt', 或 'unknown'
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                first_lines = [f.readline() for _ in range(10)]
                
            # 检测 Rime 格式
            if any('---' in line for line in first_lines):
                return 'rime'
                
            # 检测 CSV 格式
            if any(',' in line and '\t' not in line for line in first_lines):
                return 'csv'
                
            # 检测 TSV 格式
            if any('\t' in line for line in first_lines):
                return 'tsv'
                
            return 'txt'
        except:
            return 'unknown'
            
    @staticmethod
    def parse_rime_dict(filepath: str) -> List[Tuple[str, str]]:
        """
        解析 Rime 词库文件
        
        Args:
            filepath: Rime 词库文件路径
            
        Returns:
            [(词条, 拼音), ...] 列表
        """
        entries = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # 跳过注释和元数据
                if not line or line.startswith('#') or line.startswith('---'):
                    continue
                    
                # Rime 格式: 词条\t拼音
                parts = line.split('\t')
                if len(parts) >= 2:
                    text = parts[0].strip()
                    pinyin = parts[1].strip()
                    entries.append((text, pinyin))
                elif len(parts) == 1:
                    text = parts[0].strip()
                    entries.append((text, ''))
                    
        return entries
        
    @staticmethod
    def generate_rime_dict(entries: List[Tuple[str, str]], output_path: str, 
                          include_pinyin: bool = True) -> int:
        """
        生成 Rime 词库文件
        
        Args:
            entries: [(词条, 拼音), ...] 列表
            output_path: 输出文件路径
            include_pinyin: 是否包含拼音
            
        Returns:
            写入的词条数量
        """
        count = 0
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # 写入 Rime 格式头
            f.write("""# Rime 词库
# 格式: 词条\t拼音

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
        print("Usage: python importer.py <dat_file> <import_file>")
        sys.exit(1)
        
    from editor import MSPinyinEditor
    
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
