#!/usr/bin/env python3
"""
MSPinyin 词库爬虫定时任务配置

Usage:
    python -m crawler.schedule setup     # 配置每周定时任务
    python -m crawler.schedule remove    # 移除定时任务
    python -m crawler.schedule list      # 查看定时任务
"""

import sys
import subprocess
from pathlib import Path

# 项目配置
PROJECT_ROOT = Path(__file__).parent.parent
CRAWLER_MODULE = f"{PROJECT_ROOT}/crawler"
MSPINYIN_DICT = Path.home() / "AppData" / "Roaming" / "Microsoft" / "InputMethod" / "OC" / "英" / "1049" / "custom_phrase.dat"

# 默认定时任务配置
CRON_NAME = "mspinyin-crawler"
CRON_SCHEDULE = "0 3 * * 1"  # 每周一 03:00


def setup_cron(mspinyin_path: str = None, proxy: str = "http://localhost:7893"):
    """
    配置每周定时任务
    
    Args:
        mspinyin_path: 微软拼音词库文件路径
        proxy: 代理地址
    """
    mspinyin = mspinyin_path or str(MSPINYIN_DICT)
    
    # Cron job prompt
    prompt = f"""运行微软拼音词库爬虫，抓取新词并更新词库。

工作目录: {PROJECT_ROOT}
词库文件: {mspinyin}
代理: {proxy}

执行步骤:
1. 使用 crawler.cli fetch --all 抓取 GitHub/Wikipedia/B站 热词
2. 使用 crawler.cli update --all --mspinyin {mspinyin} 导入新词

输出简洁的结果报告（抓取数量、导入数量）。
如果词库文件不存在或无法访问，输出警告但不要失败。
"""
    
    try:
        # 创建 cron job
        result = subprocess.run(
            ['crontab', '-l'],
            capture_output=True,
            text=True
        )
        current_crons = result.stdout if result.returncode == 0 else ""
        
        # 移除旧的任务（如果存在）
        new_crons = []
        for line in current_crons.split('\n'):
            if CRON_NAME not in line and line.strip():
                new_crons.append(line)
        
        # 添加新的任务
        new_crons.append(f"# {CRON_NAME} - 每周一 03:00 更新微软拼音词库")
        new_crons.append(f"{CRON_SCHEDULE} cd {PROJECT_ROOT} && python3 -m crawler.cli update --all --mspinyin {mspinyin} --proxy {proxy} #{CRON_NAME}")
        
        # 安装新的 crontab
        new_crontab = '\n'.join(new_crons) + '\n'
        proc = subprocess.Popen(
            ['crontab', '-'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = proc.communicate(new_crontab.encode())
        
        if proc.returncode == 0:
            print(f"[Schedule] Cron job installed: {CRON_NAME}")
            print(f"  Schedule: {CRON_SCHEDULE} (每周一 03:00)")
            print(f"  Command: python3 -m crawler.cli update --all --mspinyin {mspinyin}")
            return 0
        else:
            print(f"[Schedule] Error installing cron job: {stderr.decode()}")
            return 1
            
    except Exception as e:
        print(f"[Schedule] Error: {e}")
        return 1


def remove_cron():
    """移除定时任务"""
    try:
        result = subprocess.run(
            ['crontab', '-l'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("[Schedule] No crontab installed")
            return 0
            
        current_crons = result.stdout
        new_crons = []
        removed = False
        
        for line in current_crons.split('\n'):
            if CRON_NAME in line:
                removed = True
            elif line.strip():
                new_crons.append(line)
        
        if not removed:
            print(f"[Schedule] Cron job '{CRON_NAME}' not found")
            return 0
            
        new_crontab = '\n'.join(new_crons) + '\n'
        proc = subprocess.Popen(
            ['crontab', '-'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = proc.communicate(new_crontab.encode())
        
        if proc.returncode == 0:
            print(f"[Schedule] Cron job '{CRON_NAME}' removed")
            return 0
        else:
            print(f"[Schedule] Error removing cron job: {stderr.decode()}")
            return 1
            
    except Exception as e:
        print(f"[Schedule] Error: {e}")
        return 1


def list_cron():
    """查看定时任务"""
    try:
        result = subprocess.run(
            ['crontab', '-l'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("[Schedule] No crontab installed")
            return 0
            
        lines = result.stdout.split('\n')
        found = False
        
        print("[Schedule] Current crontab:")
        for line in lines:
            if CRON_NAME in line:
                print(f"  {line}")
                found = True
                
        if not found:
            print(f"  (no '{CRON_NAME}' job found)")
            
        return 0
        
    except Exception as e:
        print(f"[Schedule] Error: {e}")
        return 1


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='MSPinyin 词库爬虫定时任务管理')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # setup 命令
    setup_parser = subparsers.add_parser('setup', help='配置定时任务')
    setup_parser.add_argument('--mspinyin', help='微软拼音词库文件路径')
    setup_parser.add_argument('--proxy', default='http://localhost:7893', help='代理地址')
    
    # remove 命令
    subparsers.add_parser('remove', help='移除定时任务')
    
    # list 命令
    subparsers.add_parser('list', help='查看定时任务')
    
    args = parser.parse_args()
    
    if args.command == 'setup':
        return setup_cron(args.mspinyin, args.proxy)
    elif args.command == 'remove':
        return remove_cron()
    elif args.command == 'list':
        return list_cron()
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
