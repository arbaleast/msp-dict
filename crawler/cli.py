#!/usr/bin/env python3
"""
MSPinyin 词库爬虫 CLI

Usage:
    python -m crawler.cli fetch       # 抓取新词（不导入）
    python -m crawler.cli update      # 抓取 + 导入到词库
    python -m crawler.cli stats      # 显示数据源统计
"""

import argparse
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crawler.fetchers import GitHubFetcher, WikipediaFetcher, BilibiliFetcher
from crawler.pipeline import Pipeline, save_words, load_existing_words


def cmd_fetch(args):
    """抓取新词（不导入）"""
    print("[CLI] Fetching words from data sources...")
    print("=" * 50)
    
    sources = {}
    
    # GitHub Trending
    if args.github or args.all:
        print("\n[1/3] Fetching GitHub Trending...")
        fetcher = GitHubFetcher(proxy=args.proxy)
        projects = fetcher.fetch_all_languages()
        sources['github'] = projects
        print(f"      Got {len(projects)} project names")
        
    # Wikipedia
    if args.wikipedia or args.all:
        print("\n[2/3] Fetching Wikipedia Most Visited...")
        fetcher = WikipediaFetcher(proxy=args.proxy)
        titles = fetcher.fetch(limit=args.limit)
        sources['wikipedia'] = titles
        print(f"      Got {len(titles)} article titles")
        
    # Bilibili
    if args.bilibili or args.all:
        print("\n[3/3] Fetching Bilibili Hot Keywords...")
        fetcher = BilibiliFetcher(proxy=args.proxy)
        keywords = fetcher.fetch(limit=args.limit)
        keywords2 = fetcher.fetch_trending()
        sources['bilibili'] = list(set(keywords + keywords2))
        print(f"      Got {len(sources['bilibili'])} keywords")
    
    if not sources:
        print("[CLI] No data source selected. Use --all or specify sources.")
        return 1
        
    # 处理词条
    print("\n[Pipeline] Processing words...")
    pipeline = Pipeline()
    
    # 加载已有词库（如果有）
    existing_words = set()
    if args.existing:
        existing_words = load_existing_words(args.existing)
        print(f"      Loaded {len(existing_words)} existing words from {args.existing}")
    
    result = pipeline.process(sources, existing_words)
    pipeline.print_stats()
    
    # 保存结果
    output_file = args.output or 'new_words.txt'
    save_words(result, output_file)
    print(f"\n[CLI] Saved {len(result)} words to {output_file}")
    
    return 0


def cmd_update(args):
    """抓取并导入到词库"""
    # 先抓取
    print("[CLI] Step 1: Fetching new words...")
    print("=" * 50)
    
    # 临时保存抓取结果
    temp_output = '/tmp/mspinyin_fetch_temp.txt'
    
    # 修改参数，设置临时输出
    class FetchArgs:
        github = args.github or args.all
        wikipedia = args.wikipedia or args.all
        bilibili = args.bilibili or args.all
        all = args.all
        proxy = args.proxy
        limit = args.limit
        existing = args.existing
        output = temp_output
        
    fetch_args = FetchArgs()
    result = cmd_fetch(fetch_args)
    
    if result != 0:
        print("[CLI] Fetch failed, aborting update.")
        return result
        
    # 导入到词库
    print("\n[CLI] Step 2: Importing to词库...")
    print("=" * 50)
    
    if not args.mspinyin:
        print("[CLI] Error: --mspinyin required for update command")
        return 1
        
    from crawler.importer import BatchImporter
    from crawler.editor import MSPinyinEditor
    
    # 加载词库编辑器
    editor = MSPinyinEditor()
    editor.load(args.mspinyin)
    
    print(f"Current word count: {editor.get_entry_count()}")
    
    # 导入新词
    importer = BatchImporter(editor)
    imported, skipped, errors = importer.import_txt(temp_output)
    
    stats = importer.get_stats()
    print(f"\nImport results:")
    print(f"  Imported: {stats['imported']}")
    print(f"  Skipped:  {stats['skipped']}")
    print(f"  Errors:   {stats['errors']}")
    
    if stats['imported'] > 0:
        # 保存
        editor.save(args.mspinyin)
        print(f"\n[CLI] Updated词库: {args.mspinyin}")
        print(f"New word count: {editor.get_entry_count()}")
        
    # 清理临时文件
    if os.path.exists(temp_output):
        os.remove(temp_output)
        
    return 0


def cmd_stats(args):
    """显示数据源统计"""
    print("[CLI] Data Source Statistics")
    print("=" * 50)
    
    stats_info = []
    
    # GitHub
    if args.github or args.all:
        print("\n[GitHub Trending]")
        print("  URL: https://github.com/trending")
        print("  Languages: python, go, javascript, typescript, java, rust")
        fetcher = GitHubFetcher(proxy=args.proxy)
        projects = fetcher.fetch_all_languages()
        print(f"  Current count: {len(projects)}")
        stats_info.append(('GitHub', len(projects)))
        
    # Wikipedia
    if args.wikipedia or args.all:
        print("\n[Wikipedia Most Visited]")
        print("  API: zh.wikipedia.org/w/api.php")
        fetcher = WikipediaFetcher(proxy=args.proxy)
        titles = fetcher.fetch(limit=100)
        print(f"  Current count: {len(titles)}")
        stats_info.append(('Wikipedia', len(titles)))
        
    # Bilibili
    if args.bilibili or args.all:
        print("\n[Bilibili Hot Keywords]")
        print("  APIs: search/hot, ranking/v2")
        fetcher = BilibiliFetcher(proxy=args.proxy)
        keywords = fetcher.fetch(limit=50)
        keywords2 = fetcher.fetch_trending()
        total = len(set(keywords + keywords2))
        print(f"  Current count: {total}")
        stats_info.append(('Bilibili', total))
    
    if not stats_info:
        print("\nNo data source selected.")
        return 1
        
    print("\n" + "=" * 50)
    print("Summary:")
    total = sum(s[1] for s in stats_info)
    for name, count in stats_info:
        print(f"  {name}: {count}")
    print(f"  Total: {total}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='MSPinyin 词库爬虫 - 从多数据源抓取新词',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 抓取所有数据源
  python -m crawler.cli fetch --all

  # 只抓取 GitHub 和维基百科
  python -m crawler.cli fetch --github --wikipedia

  # 抓取并导入到词库
  python -m crawler.cli update --all --mspinyin user_dict.dat

  # 显示数据源统计
  python -m crawler.cli stats --all
"""
    )
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # fetch 命令
    fetch_parser = subparsers.add_parser('fetch', help='抓取新词（不导入）')
    fetch_parser.add_argument('--all', '-a', action='store_true', help='抓取所有数据源')
    fetch_parser.add_argument('--github', action='store_true', help='抓取 GitHub Trending')
    fetch_parser.add_argument('--wikipedia', action='store_true', help='抓取维基百科')
    fetch_parser.add_argument('--bilibili', action='store_true', help='抓取B站热词')
    fetch_parser.add_argument('--proxy', default='http://localhost:7893', help='代理地址')
    fetch_parser.add_argument('--limit', type=int, default=100, help='每个数据源抓取数量')
    fetch_parser.add_argument('--existing', help='已有词库文件（用于去重）')
    fetch_parser.add_argument('--output', '-o', help='输出文件路径')
    
    # update 命令
    update_parser = subparsers.add_parser('update', help='抓取并导入词库')
    update_parser.add_argument('--all', '-a', action='store_true', help='抓取所有数据源')
    update_parser.add_argument('--github', action='store_true', help='抓取 GitHub Trending')
    update_parser.add_argument('--wikipedia', action='store_true', help='抓取维基百科')
    update_parser.add_argument('--bilibili', action='store_true', help='抓取B站热词')
    update_parser.add_argument('--proxy', default='http://localhost:7893', help='代理地址')
    update_parser.add_argument('--limit', type=int, default=100, help='每个数据源抓取数量')
    update_parser.add_argument('--mspinyin', required=True, help='微软拼音词库文件路径')
    update_parser.add_argument('--existing', help='已有词库文件（用于去重）')
    
    # stats 命令
    stats_parser = subparsers.add_parser('stats', help='显示数据源统计')
    stats_parser.add_argument('--all', '-a', action='store_true', help='所有数据源')
    stats_parser.add_argument('--github', action='store_true', help='GitHub Trending')
    stats_parser.add_argument('--wikipedia', action='store_true', help='维基百科')
    stats_parser.add_argument('--bilibili', action='store_true', help='B站热词')
    stats_parser.add_argument('--proxy', default='http://localhost:7893', help='代理地址')
    
    args = parser.parse_args()
    
    if args.command == 'fetch':
        return cmd_fetch(args)
    elif args.command == 'update':
        return cmd_update(args)
    elif args.command == 'stats':
        return cmd_stats(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
