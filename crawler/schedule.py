#!/usr/bin/env python3
"""
MSPinyin 词库爬虫定时任务配置

Usage:
    python -m crawler.schedule setup     # 配置每周定时任务
    python -m crawler.schedule remove    # 移除定时任务
    python -m crawler.schedule list      # 查看定时任务
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# 项目配置
PROJECT_ROOT = Path(__file__).parent.parent

IS_WINDOWS = os.name == 'nt'


def default_mspinyin_dict() -> Path:
    """微软拼音「自定义短语」文件的默认位置（按平台区分）。

    Windows 上位于 %APPDATA%\Microsoft\InputMethod\OC\英\1049\custom_phrase.dat；
    其他平台没有这个目录，退回到项目内 output/ 下——Linux 上
    Path.home()/"AppData" 拼出来的路径毫无意义，不能直接拿来当默认值。
    """
    if IS_WINDOWS:
        appdata = os.environ.get('APPDATA')
        if not appdata:
            appdata = str(Path.home() / 'AppData' / 'Roaming')
        return (Path(appdata) / 'Microsoft' / 'InputMethod' / 'OC' /
                '英' / '1049' / 'custom_phrase.dat')
    return PROJECT_ROOT / 'output' / 'custom_phrase.dat'


MSPINYIN_DICT = default_mspinyin_dict()

# 默认定时任务配置
CRON_NAME = "mspinyin-crawler"
CRON_SCHEDULE = "0 3 * * 1"  # 每周一 03:00


def cron_available() -> bool:
    """当前平台是否有可用的 crontab（Windows 没有）。"""
    return shutil.which('crontab') is not None


def no_cron_hint(mspinyin: str) -> str:
    """没有 crontab 时给出对应平台的替代做法。"""
    if IS_WINDOWS:
        return (
            '[Schedule] 当前平台没有 crontab（Windows）。\n'
            '           请用「任务计划程序」新建每周一 03:00 的任务：\n'
            f'           程序: {sys.executable}\n'
            '           参数: -m crawler.cli update --all --mspinyin '
            f'"{mspinyin}"\n'
            f'           起始位置: {PROJECT_ROOT}'
        )
    return (
        '[Schedule] 当前系统找不到 crontab 命令，无法安装定时任务。\n'
        '           请先安装 cron（例如 Debian/Ubuntu: apt install cron），\n'
        '           或改用 systemd timer / 外部调度器手动调用：\n'
        f'           cd "{PROJECT_ROOT}" && "{sys.executable}" -m crawler.cli '
        f'update --all --mspinyin "{mspinyin}"'
    )


def setup_cron(mspinyin_path: str = None, proxy: str = "http://localhost:7893"):
    """
    配置每周定时任务
    
    Args:
        mspinyin_path: 微软拼音词库文件路径
        proxy: 代理地址
    """
    mspinyin = mspinyin_path or str(MSPINYIN_DICT)

    if not cron_available():
        print(no_cron_hint(mspinyin))
        return 1
    
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
        new_crons.append(
            f"{CRON_SCHEDULE} cd \"{PROJECT_ROOT}\" && \"{sys.executable}\" "
            f"-m crawler.cli update --all --mspinyin \"{mspinyin}\" "
            f"--proxy {proxy} #{CRON_NAME}"
        )
        
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
            print(f"  Command: {sys.executable} -m crawler.cli update --all --mspinyin {mspinyin}")
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
