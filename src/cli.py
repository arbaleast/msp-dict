#!/usr/bin/env python3
"""
微软拼音词库 CLI 工具 (mschxudp 格式)

Usage:
    python -m src.cli <command> [options]

Commands:
    parse       解析词库并显示统计信息
    export      导出词库为 TXT/CSV/JSON
    import      批量导入词条
    convert     格式转换 (rime/msp)
    add         添加单个词条
    remove      删除单个词条
    stats       显示统计信息
    build       从文本构建 mschxudp 格式词库（支持 lite/standard/full 三档）
    validate    校验 DAT 文件是否可被 Windows 微软拼音导入
"""

import argparse
import json
import os
import sys

from .parser import MSPinyinParser
from .editor import MSPinyinEditor
from .exporter import Exporter
from .importer import BatchImporter, RimeConverter
from .converter import BidirectionalConverter
from .builder_win10 import REASON_LABELS, Win10MSPinyinBuilder
from .format_spec import MAX_IMPORT_ENTRIES
from .profiles import PROFILES, get_profile
from .validator import DatValidator


def cmd_parse(args):
    """解析词库"""
    parser = MSPinyinParser()
    try:
        count = parser.load(args.file)
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)

    print(f"文件: {args.file}")
    print(f"文件大小: {parser.get_file_size()} 字节")
    print(f"词条数量: {count}")
    if parser.invalid_entries:
        print(f"⚠️  无法解析的词条: {parser.invalid_entries}")
    for warning in parser.warnings[:5]:
        print(f"⚠️  {warning}")

    if args.verbose:
        lengths = [len(e.text) for e in parser.entries]
        stats = {
            'avg_length': sum(lengths) / len(lengths) if lengths else 0,
            'single_char': sum(1 for l in lengths if l == 1),
            'double_char': sum(1 for l in lengths if l == 2),
            'triple_char': sum(1 for l in lengths if l == 3),
            'quad_char': sum(1 for l in lengths if l == 4),
            'longer': sum(1 for l in lengths if l > 4),
        }
        print(f"\n统计:")
        print(f"  平均长度: {stats['avg_length']:.2f}")
        print(f"  单字词: {stats['single_char']}")
        print(f"  双字词: {stats['double_char']}")
        print(f"  三字词: {stats['triple_char']}")
        print(f"  四字词: {stats['quad_char']}")
        print(f"  四字以上: {stats['longer']}")

    if args.list:
        limit = min(20, len(parser.entries))
        print(f"\n词条列表 (前 {limit} 条):")
        for i, entry in enumerate(parser.entries[:limit]):
            print(f"  {i + 1}. {entry.text}  [{entry.pinyin}]")


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

    if editor.add_entry(args.text, args.pinyin, args.rank):
        editor.save(args.file)
        stats = editor.last_build_stats
        if stats and stats.skipped:
            reasons = '，'.join(f"{REASON_LABELS.get(k, k)}={v}"
                                for k, v in stats.reasons.items() if k != 'duplicate')
            print(f"未写入: {args.text}（{reasons}）")
        else:
            print(f"添加词条: {args.text}  [{args.pinyin}] (候选位由构建器分配)")
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

    stats = {
        'file_size': parser.get_file_size(),
        'total_entries': parser.get_entry_count(),
    }

    lengths = [len(e.text) for e in parser.entries]
    stats.update({
        'avg_length': sum(lengths) / len(lengths) if lengths else 0,
        'max_length': max(lengths) if lengths else 0,
        'single_char': sum(1 for l in lengths if l == 1),
        'double_char': sum(1 for l in lengths if l == 2),
        'triple_char': sum(1 for l in lengths if l == 3),
        'quad_char': sum(1 for l in lengths if l == 4),
        'longer': sum(1 for l in lengths if l > 4),
    })

    print(f"文件: {args.file}")
    print(f"文件大小: {stats['file_size']} 字节")
    print(f"词条数量: {stats['total_entries']}")
    print(f"平均长度: {stats['avg_length']:.2f}")
    print(f"最大长度: {stats['max_length']}")
    print(f"单字词: {stats['single_char']}")
    print(f"双字词: {stats['double_char']}")
    print(f"三字词: {stats['triple_char']}")
    print(f"四字词: {stats['quad_char']}")
    print(f"四字以上: {stats['longer']}")


def cmd_build(args):
    """从文本构建 mschxudp 格式词库

    输入格式: 每行一个词条，使用制表符分隔
        词条\t拼音\t词频（可选）

    示例:
        中国\tzhongguo\t31450
        北京\tbeijing
    """
    profile = get_profile(args.profile) if args.profile else None
    limit = args.limit if args.limit is not None else (profile.limit if profile else None)
    min_freq = args.min_freq if args.min_freq is not None else (profile.min_freq if profile else 0)
    max_word_chars = (args.max_word_chars if args.max_word_chars is not None
                      else (profile.max_word_units if profile else None))
    if args.exclude_single is not None:
        exclude_single = args.exclude_single
    else:
        exclude_single = profile.exclude_single if profile else False

    builder = Win10MSPinyinBuilder(timestamp=args.timestamp or 0)
    selected = builder.add_from_text_file(
        args.input,
        min_freq=min_freq,
        exclude_single=exclude_single,
        max_word_units=max_word_chars,
        limit=limit,
    )

    output = args.output or (os.path.splitext(args.input)[0] + '.dat')
    data = builder.build()
    with open(output, 'wb') as f:
        f.write(data)

    stats = builder.stats
    size_mb = os.path.getsize(output) / 1024 / 1024

    print("构建完成:")
    print(f"  输入文件: {args.input}")
    print(f"  输出文件: {output} ({size_mb:.2f} MB)")
    if profile:
        print(f"  策略: {profile.describe()}")
    print(f"  读取词条: {selected:,}")
    print(f"  写入词条: {stats.accepted:,}")
    print(f"  清洗统计: {stats.summary()}")
    if stats.accepted > MAX_IMPORT_ENTRIES:
        print(f"  ⚠️  词条数超过微软拼音约 {MAX_IMPORT_ENTRIES:,} 条上限："
              f"Windows 无法完整导入，请改用 lite 档（--profile lite）或转其他输入法")
    return 0


def cmd_validate(args):
    """校验 DAT 文件，分类报告格式错误/文件损坏/内容违规/容量警告"""
    report = DatValidator().validate(args.file)
    if args.json:
        payload = {
            'path': report.path,
            'file_size': report.file_size,
            'phrase_count': report.phrase_count,
            'parsed_entries': report.parsed_entries,
            'exit_code': report.exit_code,
            'verdict': report.verdict,
            'stats': report.stats,
            'issues': [
                {
                    'category': issue.category,
                    'severity': issue.severity,
                    'code': issue.code,
                    'message': issue.message,
                    'count': issue.count,
                    'samples': issue.samples,
                }
                for issue in report.issues
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(report.format_text(max_samples=args.samples))
    return report.exit_code


def main():
    parser = argparse.ArgumentParser(
        description='微软拼音词库管理工具 (mschxudp 格式)'
    )
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # parse 命令
    p_parse = subparsers.add_parser('parse', help='解析词库')
    p_parse.add_argument('file', help='词库文件路径')
    p_parse.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    p_parse.add_argument('-l', '--list', action='store_true', help='列出词条')

    # export 命令
    p_export = subparsers.add_parser('export', help='导出词库')
    p_export.add_argument('file', help='词库文件路径')
    p_export.add_argument('-o', '--output', default='dict.txt', help='输出文件')
    p_export.add_argument('-f', '--format', choices=['txt', 'csv', 'json'],
                          default='txt', help='输出格式')

    # import 命令
    p_import = subparsers.add_parser('import', help='批量导入')
    p_import.add_argument('file', help='词库文件路径')
    p_import.add_argument('input', help='要导入的文件')

    # convert 命令
    p_convert = subparsers.add_parser('convert', help='格式转换')
    p_convert.add_argument('input', help='输入文件')
    p_convert.add_argument('output', help='输出文件')
    p_convert.add_argument('-f', '--format', choices=['rime', 'msp'],
                           default='rime', help='目标格式')

    # add 命令
    p_add = subparsers.add_parser('add', help='添加词条')
    p_add.add_argument('file', help='词库文件路径')
    p_add.add_argument('text', help='词条文本')
    p_add.add_argument('-p', '--pinyin', default='', help='拼音字符串')
    p_add.add_argument('-r', '--rank', type=int, default=1, help='词频排名')

    # remove 命令
    p_remove = subparsers.add_parser('remove', help='删除词条')
    p_remove.add_argument('file', help='词库文件路径')
    p_remove.add_argument('text', help='词条文本')

    # stats 命令
    p_stats = subparsers.add_parser('stats', help='显示统计')
    p_stats.add_argument('file', help='词库文件路径')

    # build 命令
    p_build = subparsers.add_parser('build', help='从文本构建 mschxudp 词库')
    p_build.add_argument('input', help='输入文本文件')
    p_build.add_argument('-o', '--output', help='输出 .dat 文件')
    p_build.add_argument('--profile', choices=sorted(PROFILES),
                         help='三档发布策略（lite 精简推荐 / standard / full 存档）')
    p_build.add_argument('--limit', type=int, help='最多写入多少条（按输入顺序取前 N 条）')
    p_build.add_argument('--min-freq', type=int, help='最低词频')
    p_build.add_argument('--max-word-chars', type=int, help='词条最大字数（UTF-16 单元）')
    p_build.add_argument('--exclude-single', action=argparse.BooleanOptionalAction,
                         help='剔除单字词（微软拼音自带单字）')
    p_build.add_argument('--timestamp', type=int,
                         help='写入文件头的 Unix 时间戳（用于可复现构建）')

    # validate 命令
    p_validate = subparsers.add_parser('validate', help='校验 .dat 是否可被 Windows 导入')
    p_validate.add_argument('file', help='词库文件路径')
    p_validate.add_argument('--json', action='store_true', help='输出 JSON 报告')
    p_validate.add_argument('-n', '--samples', type=int, default=5,
                            help='每类问题展示的样本条数')

    args = parser.parse_args()

    commands = {
        'parse': cmd_parse,
        'export': cmd_export,
        'import': cmd_import,
        'convert': cmd_convert,
        'add': cmd_add,
        'remove': cmd_remove,
        'stats': cmd_stats,
        'build': cmd_build,
        'validate': cmd_validate,
    }

    cmd = commands.get(args.command)
    if cmd:
        rc = cmd(args)
        if isinstance(rc, int):
            sys.exit(rc)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
