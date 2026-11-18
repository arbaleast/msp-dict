"""crawler CLI 与采集→导入链路的回归测试。

覆盖 Phase 0 审计确认的阻断问题：
- B1 ``crawler.editor`` 导入路径不存在导致 ``crawler update`` 必崩
- B2 可选依赖 ``python-dotenv`` 缺失导致 CLI 无法启动
- 采集结果没有拼音，无法进入 DAT（空拼音被静默丢弃）
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crawler import cli as crawler_cli  # noqa: E402
from crawler.pinyin_resolver import pypinyin_available, resolve_pinyin  # noqa: E402
from src.builder_win10 import Win10MSPinyinBuilder  # noqa: E402


class TestCliStartup:
    """CLI 必须能在没有可选依赖的环境下启动。"""

    def test_module_help_runs(self):
        result = subprocess.run(
            [sys.executable, '-m', 'crawler.cli', '--help'],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        assert 'fetch' in result.stdout
        assert 'update' in result.stdout

    def test_import_package_does_not_require_dotenv(self):
        """crawler.fetchers 不得在模块顶层无条件导入需要 python-dotenv 的搜狗模块。"""
        import ast
        tree = ast.parse((ROOT / 'crawler' / 'fetchers' / '__init__.py').read_text('utf-8'))

        guarded = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test = node.test
                is_typing_guard = (
                    isinstance(test, ast.Name) and test.id == 'TYPE_CHECKING')
                if is_typing_guard:
                    for inner in ast.walk(node):
                        guarded.add(inner)

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names]
                module = getattr(node, 'module', '') or ''
                if 'sogou' in module or 'Sogou' in names:
                    assert node in guarded, (
                        '搜狗模块只能在 TYPE_CHECKING 分支中导入，'
                        '否则缺少 python-dotenv 时整个 CLI 无法启动')

    def test_fetchers_import_succeeds_without_dotenv(self):
        """模拟缺少 python-dotenv：import crawler.fetchers 仍须成功。"""
        script = (
            'import sys\n'
            'class Blocker:\n'
            '    def find_module(self, name, path=None):\n'
            '        return self if name == "dotenv" else None\n'
            '    def load_module(self, name):\n'
            '        raise ImportError("blocked: " + name)\n'
            'sys.meta_path.insert(0, Blocker())\n'
            'for mod in list(sys.modules):\n'
            '    if mod.startswith(("dotenv", "crawler")):\n'
            '        del sys.modules[mod]\n'
            'import crawler.fetchers as f\n'
            'print("OK", f.GitHubFetcher.__name__)\n'
        )
        result = subprocess.run(
            [sys.executable, '-c', script],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        assert 'OK GitHubFetcher' in result.stdout

    def test_sogou_fetcher_is_lazy(self):
        """SogouFetcher 只能通过模块级 __getattr__ 惰性加载。"""
        source = (ROOT / 'crawler' / 'fetchers' / '__init__.py').read_text('utf-8')
        assert '__getattr__' in source
        assert 'TYPE_CHECKING' in source

    def test_update_imports_editor_from_src(self):
        """crawler update 必须从 src.editor 导入编辑器（crawler.editor 不存在）。"""
        assert not (ROOT / 'crawler' / 'editor.py').exists()
        source = (ROOT / 'crawler' / 'cli.py').read_text('utf-8')
        assert 'from crawler.editor import MSPinyinEditor' not in source
        assert 'from src.editor import MSPinyinEditor' in source

    def test_editor_is_importable_from_crawler_importer(self):
        from crawler.importer import MSPinyinEditor
        from src.editor import MSPinyinEditor as SrcEditor
        assert MSPinyinEditor is SrcEditor


class TestPinyinResolver:
    """采集词条的拼音补全。"""

    def test_resolves_chinese_words(self):
        resolved, unresolved = resolve_pinyin(['中国', '北京'])
        if not pypinyin_available():
            assert resolved == {}
            assert unresolved == ['中国', '北京']
            return
        assert resolved['中国'] == 'zhongguo'
        assert resolved['北京'] == 'beijing'
        assert unresolved == []

    def test_never_produces_placeholder_pinyin(self):
        resolved, _ = resolve_pinyin(['中国'])
        for pinyin in resolved.values():
            assert pinyin != 'xx'
            assert pinyin and pinyin.strip()

    def test_non_chinese_is_unresolved(self):
        resolved, unresolved = resolve_pinyin(['hello-world', '123'])
        assert resolved == {}
        assert set(unresolved) == {'hello-world', '123'}


class TestUpdateFlow:
    """crawler update 的完整链路：抓取 → 补拼音 → 导入 → 保存 DAT。"""

    @staticmethod
    def _make_dat(path: Path) -> None:
        builder = Win10MSPinyinBuilder()
        builder.add_word('测试', 'ceshi', 1)
        builder.save(str(path))

    def _run_update(self, tmp_path, words, monkeypatch):
        dat = tmp_path / 'user_dict.dat'
        self._make_dat(dat)

        def fake_fetch(args):
            with open(args.output, 'w', encoding='utf-8') as f:
                for word in words:
                    f.write(f'{word}\n')
            return 0

        monkeypatch.setattr(crawler_cli, 'cmd_fetch', fake_fetch)

        args = type('Args', (), {})()
        args.all = True
        args.github = args.wikipedia = args.bilibili = False
        args.moegirl = args.wikidata = args.zhihu = False
        args.proxy = ''
        args.limit = 100
        args.existing = None
        args.mspinyin = str(dat)
        return dat, crawler_cli.cmd_update(args)

    def test_update_imports_words_with_pinyin(self, tmp_path, monkeypatch):
        if not pypinyin_available():
            pytest.skip('未安装 pypinyin（可选依赖）')
        dat, rc = self._run_update(tmp_path, ['中国', '北京'], monkeypatch)
        assert rc == 0

        from src.parser import MSPinyinParser
        parser = MSPinyinParser()
        parser.load(str(dat))
        words = {e.text: e.pinyin for e in parser.entries}
        assert '中国' in words and '北京' in words
        assert words['中国'] == 'zhongguo'
        assert words['北京'] == 'beijing'

    def test_update_writes_unresolved_words_to_file(self, tmp_path, monkeypatch):
        """无法补全拼音的词条必须落盘，而不是塞空拼音进词库。"""
        dat, rc = self._run_update(tmp_path, ['hello-world'], monkeypatch)
        assert rc == 0

        # 无论 pypinyin 是否可用，解析不了的词条都必须落盘（不能静默丢弃）
        unresolved = tmp_path / 'unresolved.txt'
        assert unresolved.exists()
        assert 'hello-world' in unresolved.read_text('utf-8')

        from src.parser import MSPinyinParser
        parser = MSPinyinParser()
        parser.load(str(dat))
        assert 'hello-world' not in {e.text for e in parser.entries}

    def test_update_cleans_temp_file(self, tmp_path, monkeypatch):
        dat, rc = self._run_update(tmp_path, ['中国'], monkeypatch)
        assert rc == 0
        leftovers = list(Path('/tmp').glob('mspinyin_fetch_*.txt'))
        assert not leftovers, f'临时文件未清理: {leftovers}'
