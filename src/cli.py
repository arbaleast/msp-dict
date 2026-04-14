#!/usr/bin/env python3
"""
微软拼音词库 CLI 工具

Usage:
    python -m mspinyin.cli <command> [options]
"""

import argparse
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser import MSPinyinParser
from editor import MSPinyinEditor
from exporter import Exporter
from importer import BatchImporter, RimeConverter
from converter import BidirectionalConverter


def cmd_parse(args):
    """解析词库"""
    parser = MSPinyinParser()
    parser.load(args.file)
    
    print(f"文件: {args.file}")
    print(f"文件大小: {parser.get_file_size()} bytes")
    print(f"词条数量: {parser.get_entry_count()}")
    
    if args.verbose:
        exporter = Exporter(parser)
        stats = exporter.get_stats()
        print(f"\n统计:")
        print(f"  平均长度: {stats['avg_length']:.2f}")
        print(f"  单字词: {stats['single_char']}")
        print(f"  双字词: {stats['double_char']}")
        print(f"  三字词: {stats['triple_char']}")
        print(f"  四字词: {stats['quad_char']}")
        print(f"  四字以上: {stats['longer']}")
        
    if args.list:
        print(f"\n词条列表 (前 {min(20, len(parser.entries))} 条):")
        for i, entry in enumerate(parser.entries[:20]):
            print(f"  {i+1}. {entry.text}")


def cmd_export(args):
    """导出词库"""
    parser = MSPinyinParser()
    parser.load(args.file)
    
    exporter = Exporter(parser)
    
    if args.format == 'txt':
        count = exporter.export_txt(args.output)
        print(f"导出 {count} 个词条到 {args.output}")
    elif args.format == 'csv':
        count = exporter.export_csv(args.output)
        print(f"导出 {count} 个词条到 {args.output}")
    elif args.format == 'json':
        count = exporter.export_json(args.output)
        print(f"导出 {count} 个词条到 {args.output}")


def cmd_import(args):
    """批量导入词条"""
    editor = MSPinyinEditor()
    editor.load(args.file)
    
    print(f"导入前词条数: {editor.get_entry_count()}")
    
    # 检测格式
    fmt = RimeConverter.detect_format(args.input)
    print(f"检测到格式: {fmt}")
    
    importer = BatchImporter(editor)
    
    if fmt == 'rime' or fmt == 'tsv':
        result = importer.import_rime(args.input)
    elif fmt == 'csv':
        result = importer.import_csv(args.input)
    else:
        result = importer.import_txt(args.input)
        
    stats = importer.get_stats()
    print(f"\n导入结果:")
    print(f"  成功: {stats['imported']}")
    print(f"  跳过: {stats['skipped']}")
    print(f"  错误: {stats['errors']}")
    
    if stats['imported'] > 0:
        editor.save(args.file)
        print(f"\n已保存到: {args.file}")
        print(f"导入后词条数: {editor.get_entry_count()}")


def cmd_convert(args):
    """转换词库格式"""
    converter = BidirectionalConverter()
    
    if args.format == 'rime':
        print(f"转换 {args.input} → Rime 格式 {args.output}")
        count = converter.msp_to_rime(args.input, args.output)
        print(f"转换完成: {count} 词条")
    elif args.format == 'msp':
        print(f"转换 Rime 词库 {args.input} → 微软拼音格式 {args.output}")
        result = converter.rime_to_msp(args.input, args.output)
        print(f"转换完成: {result}")


def cmd_add(args):
    """添加词条"""
    editor = MSPinyinEditor()
    editor.load(args.file)
    
    if editor.add_entry(args.text):
        editor.save(args.file)
        print(f"添加词条: {args.text}")
    else:
        print(f"添加失败: {args.text} (可能已存在)")


def cmd_remove(args):
    """删除词条"""
    editor = MSPinyinEditor()
    editor.load(args.file)
    
    if editor.remove_entry(args.text):
        editor.save(args.file)
        print(f"删除词条: {args.text}")
    else:
        print(f"删除失败: {args.text} (未找到)")


def cmd_stats(args):
    """显示统计信息"""
    parser = MSPinyinParser()
    parser.load(args.file)
    
    exporter = Exporter(parser)
    stats = exporter.get_stats()
    
    print(f"文件: {args.file}")
    print(f"文件大小: {stats['file_size']} bytes")
    print(f"词条数量: {stats['total_entries']}")
    print(f"平均长度: {stats['avg_length']:.2f}")
    print(f"最大长度: {stats['max_length']}")
    print(f"单字词: {stats['single_char']}")
    print(f"双字词: {stats['double_char']}")
    print(f"三字词: {stats['triple_char']}")
    print(f"四字词: {stats['quad_char']}")
    print(f"四字以上: {stats['longer']}")


def main():
    parser = argparse.ArgumentParser(description='微软拼音词库管理工具')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # parse 命令
    parse_parser = subparsers.add_parser('parse', help='解析词库')
    parse_parser.add_argument('file', help='词库文件路径')
    parse_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parse_parser.add_argument('-l', '--list', action='store_true', help='列出词条')
    
    # export 命令
    export_parser = subparsers.add_parser('export', help='导出词库')
    export_parser.add_argument('file', help='词库文件路径')
    export_parser.add_argument('-o', '--output', default='dict.txt', help='输出文件')
    export_parser.add_argument('-f', '--format', choices=['txt', 'csv', 'json'], default='txt', help='输出格式')
    
    # import 命令
    import_parser = subparsers.add_parser('import', help='批量导入')
    import_parser.add_argument('file', help='词库文件路径')
    import_parser.add_argument('input', help='要导入的文件')
    
    # convert 命令
    convert_parser = subparsers.add_parser('convert', help='转换格式')
    convert_parser.add_argument('input', help='输入文件')
    convert_parser.add_argument('output', help='输出文件')
    convert_parser.add_argument('-f', '--format', choices=['rime', 'msp'], default='rime', help='目标格式')
    
    # add 命令
    add_parser = subparsers.add_parser('add', help='添加词条')
    add_parser.add_argument('file', help='词库文件路径')
    add_parser.add_argument('text', help='词条文本')
    
    # remove 命令
    remove_parser = subparsers.add_parser('remove', help='删除词条')
    remove_parser.add_argument('file', help='词库文件路径')
    remove_parser.add_argument('text', help='词条文本')
    
    # stats 命令
    stats_parser = subparsers.add_parser('stats', help='显示统计')
    stats_parser.add_argument('file', help='词库文件路径')
    
    args = parser.parse_args()
    
    if args.command == 'parse':
        cmd_parse(args)
    elif args.command == 'export':
        cmd_export(args)
    elif args.command == 'import':
        cmd_import(args)
    elif args.command == 'convert':
        cmd_convert(args)
    elif args.command == 'add':
        cmd_add(args)
    elif args.command == 'remove':
        cmd_remove(args)
    elif args.command == 'stats':
        cmd_stats(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
