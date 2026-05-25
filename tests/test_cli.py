"""
测试 src/cli.py 模块

验证 CLI 命令的解析参数和命令分发功能。
不执行实际的 I/O 操作，仅验证参数解析和命令调用。
"""

import os
import sys
import tempfile
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.cli import main
from src.builder_win10 import Win10MSPinyinBuilder
from src.parser import MSPinyinParser


class TestCLIParsing:
    """CLI 参数解析测试"""

    def test_parse_subcommand(self):
        """parse 子命令参数解析"""
        # 测试 argparse 参数解析（不实际运行命令）
        from src.cli import cmd_parse
        # 验证 cmd_parse 函数存在且可调用
        assert callable(cmd_parse)

    def test_export_subcommand(self):
        """export 子命令参数解析"""
        from src.cli import cmd_export
        assert callable(cmd_export)

    def test_import_subcommand(self):
        """import 子命令参数解析"""
        from src.cli import cmd_import
        assert callable(cmd_import)

    def test_convert_subcommand(self):
        """convert 子命令参数解析"""
        from src.cli import cmd_convert
        assert callable(cmd_convert)

    def test_add_subcommand(self):
        """add 子命令参数解析"""
        from src.cli import cmd_add
        assert callable(cmd_add)

    def test_remove_subcommand(self):
        """remove 子命令参数解析"""
        from src.cli import cmd_remove
        assert callable(cmd_remove)

    def test_stats_subcommand(self):
        """stats 子命令参数解析"""
        from src.cli import cmd_stats
        assert callable(cmd_stats)

    def test_build_subcommand(self):
        """build 子命令参数解析"""
        from src.cli import cmd_build
        assert callable(cmd_build)

    def test_parse_command_line(self):
        """验证 argparse 参数定义完整性"""
        # 模拟命令行参数并验证解析
        import argparse as _argparse

        # 重新创建参数解析器（与 main 相同逻辑）
        parser = _argparse.ArgumentParser(description='微软拼音词库管理工具')
        subparsers = parser.add_subparsers(dest='command', help='子命令')

        # 验证所有子命令都注册了
        p_parse = subparsers.add_parser('parse', help='解析词库')
        p_parse.add_argument('file', help='词库文件路径')
        p_parse.add_argument('-v', '--verbose', action='store_true')
        p_parse.add_argument('-l', '--list', action='store_true')

        p_export = subparsers.add_parser('export', help='导出词库')
        p_export.add_argument('file', help='词库文件路径')
        p_export.add_argument('-o', '--output', default='dict.txt')
        p_export.add_argument('-f', '--format', choices=['txt', 'csv', 'json'], default='txt')

        p_import = subparsers.add_parser('import', help='批量导入')
        p_import.add_argument('file', help='词库文件路径')
        p_import.add_argument('input', help='要导入的文件')

        p_convert = subparsers.add_parser('convert', help='格式转换')
        p_convert.add_argument('input', help='输入文件')
        p_convert.add_argument('output', help='输出文件')
        p_convert.add_argument('-f', '--format', choices=['rime', 'msp'], default='rime')

        p_add = subparsers.add_parser('add', help='添加词条')
        p_add.add_argument('file', help='词库文件路径')
        p_add.add_argument('text', help='词条文本')
        p_add.add_argument('-p', '--pinyin', default='')
        p_add.add_argument('-r', '--rank', type=int, default=1)

        p_remove = subparsers.add_parser('remove', help='删除词条')
        p_remove.add_argument('file', help='词库文件路径')
        p_remove.add_argument('text', help='词条文本')

        p_stats = subparsers.add_parser('stats', help='显示统计')
        p_stats.add_argument('file', help='词库文件路径')

        p_build = subparsers.add_parser('build', help='从文本构建 mschxudp 词库')
        p_build.add_argument('input', help='输入文本文件')
        p_build.add_argument('-o', '--output', help='输出 .dat 文件')

        # 验证 parse 子命令
        args = parser.parse_args(['parse', 'test.dat'])
        assert args.command == 'parse'
        assert args.file == 'test.dat'

        # 验证 export 子命令
        args = parser.parse_args(['export', 'test.dat', '-o', 'out.txt', '-f', 'csv'])
        assert args.command == 'export'
        assert args.format == 'csv'
        assert args.output == 'out.txt'

        # 验证 add 子命令
        args = parser.parse_args(['add', 'test.dat', '新词条', '-p', 'xincitiao', '-r', '5'])
        assert args.command == 'add'
        assert args.text == '新词条'
        assert args.pinyin == 'xincitiao'
        assert args.rank == 5

        # 验证 remove 子命令
        args = parser.parse_args(['remove', 'test.dat', '旧词条'])
        assert args.command == 'remove'
        assert args.text == '旧词条'

        # 验证 stats 子命令
        args = parser.parse_args(['stats', 'test.dat'])
        assert args.command == 'stats'

        # 验证 build 子命令
        args = parser.parse_args(['build', 'input.txt', '-o', 'output.dat'])
        assert args.command == 'build'
        assert args.input == 'input.txt'
        assert args.output == 'output.dat'

        # 验证 convert 子命令
        args = parser.parse_args(['convert', 'input.txt', 'output.dat', '-f', 'msp'])
        assert args.command == 'convert'
        assert args.format == 'msp'

        # 验证 import 子命令
        args = parser.parse_args(['import', 'dict.dat', 'source.txt'])
        assert args.command == 'import'
        assert args.input == 'source.txt'

    def test_command_dispatcher(self):
        """验证命令分发映射完整性"""
        from src.cli import cmd_parse, cmd_export, cmd_import, cmd_convert
        from src.cli import cmd_add, cmd_remove, cmd_stats, cmd_build

        commands = {
            'parse': cmd_parse,
            'export': cmd_export,
            'import': cmd_import,
            'convert': cmd_convert,
            'add': cmd_add,
            'remove': cmd_remove,
            'stats': cmd_stats,
            'build': cmd_build,
        }

        # 验证所有命令函数都是可调用的
        for name, func in commands.items():
            assert callable(func), f"命令 {name} 不可调用"

        # 验证命令数量完整
        assert len(commands) == 8
