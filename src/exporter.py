"""
微软拼音词库导出器

支持多种导出格式 (TXT/CSV/JSON)
"""

import csv
import json
from typing import List
from .parser import MSPinyinParser


class Exporter:
    """词库导出器"""

    def __init__(self, parser: MSPinyinParser):
        self.parser = parser
        self.entries = parser.entries

    def export_txt(self, output_path: str) -> int:
        """导出为纯文本格式 (每行: 词条\t拼音)"""
        count = 0
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in self.entries:
                f.write(f"{entry.text}\t{entry.pinyin}\n")
                count += 1
        return count

    def export_csv(self, output_path: str) -> int:
        """导出为 CSV 格式 (text, pinyin, rank)"""
        count = 0
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['text', 'pinyin', 'rank'])
            for entry in self.entries:
                writer.writerow([entry.text, entry.pinyin, entry.rank])
                count += 1
        return count

    def export_json(self, output_path: str) -> int:
        """导出为 JSON 格式"""
        data = [
            {
                'text': entry.text,
                'pinyin': entry.pinyin,
                'rank': entry.rank,
            }
            for entry in self.entries
        ]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return len(data)

    def get_stats(self) -> dict:
        """获取词库统计信息"""
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
            'has_pinyin': sum(1 for e in self.entries if e.pinyin),
            'no_pinyin': sum(1 for e in self.entries if not e.pinyin),
        }


def main():
    """测试导出器"""
    import sys

    if len(sys.argv) < 2:
        print("用法: python exporter.py <mschxudp.dat> [output_dir]")
        sys.exit(1)

    parser = MSPinyinParser()
    parser.load(sys.argv[1])

    exporter = Exporter(parser)

    output_dir = sys.argv[2] if len(sys.argv) > 2 else '.'

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
