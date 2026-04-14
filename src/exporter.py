"""
微软拼音词库导出器

支持多种导出格式
"""

import csv
import json
from typing import List, Dict
from .parser import MSPinyinParser, DictEntry


class Exporter:
    """词库导出器"""
    
    def __init__(self, parser: MSPinyinParser):
        self.parser = parser
        self.entries = parser.entries
        
    def export_txt(self, output_path: str) -> int:
        """
        导出为纯文本格式 (每行一个词条)
        
        Returns:
            导出的词条数量
        """
        count = 0
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in self.entries:
                f.write(entry.text + '\n')
                count += 1
        return count
        
    def export_csv(self, output_path: str) -> int:
        """
        导出为 CSV 格式 (文本,拼音编码)
        
        Returns:
            导出的词条数量
        """
        count = 0
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['text', 'pinyin_hex'])
            for entry in self.entries:
                writer.writerow([entry.text, entry.pinyin_code.hex()])
                count += 1
        return count
        
    def export_json(self, output_path: str) -> int:
        """
        导出为 JSON 格式
        
        Returns:
            导出的词条数量
        """
        data = []
        for entry in self.entries:
            data.append({
                'text': entry.text,
                'pinyin_hex': entry.pinyin_code.hex(),
                'offset': entry.offset
            })
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        return len(data)
        
    def export_rime(self, output_path: str, pinyin_dict: Dict[str, str] = None) -> int:
        """
        导出为 Rime 格式
        
        Args:
            output_path: 输出文件路径
            pinyin_dict: 拼音映射字典，如果为 None 则只输出词条
            
        Returns:
            导出的词条数量
        """
        count = 0
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in self.entries:
                if pinyin_dict and entry.text in pinyin_dict:
                    pinyin = pinyin_dict[entry.text]
                    f.write(f"{entry.text}\t{pinyin}\n")
                else:
                    f.write(f"{entry.text}\n")
                count += 1
        return count
        
    def get_stats(self) -> Dict:
        """
        获取词库统计信息
        
        Returns:
            统计信息字典
        """
        texts = [e.text for e in self.entries]
        lengths = [len(t) for t in texts]
        
        return {
            'total_entries': len(self.entries),
            'file_size': self.parser.get_file_size(),
            'avg_length': sum(lengths) / len(lengths) if lengths else 0,
            'max_length': max(lengths) if lengths else 0,
            'min_length': min(lengths) if lengths else 0,
            'single_char': sum(1 for l in lengths if l == 1),
            'double_char': sum(1 for l in lengths if l == 2),
            'triple_char': sum(1 for l in lengths if l == 3),
            'quad_char': sum(1 for l in lengths if l == 4),
            'longer': sum(1 for l in lengths if l > 4),
        }


def main():
    """测试导出器"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python exporter.py <dat_file> [output_dir]")
        sys.exit(1)
        
    parser = MSPinyinParser()
    parser.load(sys.argv[1])
    
    exporter = Exporter(parser)
    
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
    
    # 导出各种格式
    print(f"导出 TXT...")
    count = exporter.export_txt(f"{output_dir}/dict.txt")
    print(f"  导出 {count} 个词条")
    
    print(f"导出 CSV...")
    count = exporter.export_csv(f"{output_dir}/dict.csv")
    print(f"  导出 {count} 个词条")
    
    print(f"导出 JSON...")
    count = exporter.export_json(f"{output_dir}/dict.json")
    print(f"  导出 {count} 个词条")
    
    print(f"\n统计信息:")
    stats = exporter.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == '__main__':
    main()
