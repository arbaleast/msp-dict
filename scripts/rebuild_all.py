#!/usr/bin/env python3
"""
重建所有 DAT 文件（添加按拼音排序功能）

Usage:
    python scripts/rebuild_all.py

此脚本使用 src/builder_win10.py 中的 Win10MSPinyinBuilder 类
来重建所有 msp_*.dat 文件，确保词条按拼音字母顺序排序。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.builder_win10 import Win10MSPinyinBuilder


def build_dat(input_txt: str, output_dat: str):
    """从 TXT 文件构建 DAT 文件（带排序）"""
    print(f"\n处理: {input_txt} -> {output_dat}")
    
    builder = Win10MSPinyinBuilder()
    count = 0
    error_count = 0
    
    with open(input_txt, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('\t')
            word = parts[0].strip()
            if not word:
                continue
            
            # 拼音: 移除空格
            pinyin = ''
            rank = 1
            if len(parts) >= 2:
                pinyin = parts[1].strip().replace(' ', '')
            if len(parts) >= 3:
                try:
                    rank = int(parts[2])
                except ValueError:
                    rank = 1
            
            try:
                builder.add_word(word, pinyin, rank)
                count += 1
            except Exception as e:
                if error_count < 10:  # 只显示前 10 个错误
                    print(f"  第 {line_num} 行错误: {e}")
                error_count += 1
            
            # 进度显示
            if count % 500000 == 0:
                print(f"  已处理 {count:,} 词条...")
    
    print(f"  成功: {count:,} 词条, 错误: {error_count}")
    
    # 保存
    builder.save(output_dat)
    size_mb = os.path.getsize(output_dat) / 1024 / 1024
    print(f"  已保存: {output_dat} ({size_mb:.1f} MB)")
    
    return count


def main():
    print("=" * 60)
    print("重建所有 DAT 文件（添加按拼音排序）")
    print("=" * 60)
    
    output_dir = project_root / 'output'
    
    # 需要重建的文件
    files = [
        ('msp_full.txt', 'msp_full.dat'),
        ('msp_freq10.txt', 'msp_freq10.dat'),
        ('msp_freq50.txt', 'msp_freq50.dat'),
        ('msp_freq100.txt', 'msp_freq100.dat'),
        ('msp_freq500.txt', 'msp_freq500.dat'),
    ]
    
    total_entries = 0
    
    for txt_file, dat_file in files:
        txt_path = output_dir / txt_file
        dat_path = output_dir / dat_file
        
        if not txt_path.exists():
            print(f"\n跳过 (不存在): {txt_path}")
            continue
        
        count = build_dat(str(txt_path), str(dat_path))
        total_entries += count
    
    print("\n" + "=" * 60)
    print(f"全部完成！共处理 {total_entries:,} 词条")
    print("=" * 60)


if __name__ == '__main__':
    main()
