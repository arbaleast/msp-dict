#!/usr/bin/env python3
"""
下载 rime-ice / rime-frost 词库源到 cache/（scripts/merge.py 的输入）。

cache/ 不入库（见 .gitignore），新克隆的仓库必须先跑一次本脚本，
再执行 scripts/merge.py 构建词库。下载清单与
.github/workflows/biweekly-build.yml 保持一致。

用法:
    python scripts/download_frost.py                 # 下载缺失文件
    python scripts/download_frost.py --force         # 重新下载全部
    python scripts/download_frost.py --cache cache   # 指定缓存目录
"""

import argparse
import hashlib
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import List

ROOT = Path(__file__).parent.parent

# (缓存文件名, 下载地址) —— 与 CI 的 curl 清单一一对应
FILES = [
    # ---- rime-ice ----
    ('rime-ice_base.txt', 'https://cdn.jsdelivr.net/gh/iDvel/rime-ice@main/cn_dicts/base.dict.yaml'),
    ('rime-ice_ext.txt', 'https://cdn.jsdelivr.net/gh/iDvel/rime-ice@main/cn_dicts/ext.dict.yaml'),
    ('rime-ice_tencent.txt', 'https://cdn.jsdelivr.net/gh/iDvel/rime-ice@main/cn_dicts/tencent.dict.yaml'),
    ('rime-ice_8105.txt', 'https://cdn.jsdelivr.net/gh/iDvel/rime-ice@main/cn_dicts/8105.dict.yaml'),
    ('rime-ice_others.txt', 'https://cdn.jsdelivr.net/gh/iDvel/rime-ice@main/cn_dicts/others.dict.yaml'),
    # ---- rime-frost ----
    # rime-frost tencent.dict.yaml 约 29MB，超过 GitHub 25MB 限制且未配置 LFS，跳过
    # （rime-ice tencent 已包含约 98 万腾讯词条）
    # rime-frost composite.dict.yaml 超过 jsDelivr 单文件 20MB 限制（HTTP 403），
    # 任何镜像都取不到，已从清单移除（scripts/merge.py 里有同名可选源标记）
    ('rime-frost_base.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts/base.dict.yaml'),
    ('rime-frost_ext.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts/ext.dict.yaml'),
    ('rime-frost_8105.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts/8105.dict.yaml'),
    ('rime-frost_others.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts/others.dict.yaml'),
    ('rime-frost_food.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/food.dict.yaml'),
    ('rime-frost_idiom.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/idiom.dict.yaml'),
    ('rime-frost_history.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/history.dict.yaml'),
    ('rime-frost_medication.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/medication.dict.yaml'),
    ('rime-frost_computer.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/computer.dict.yaml'),
    ('rime-frost_sport.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/sport.dict.yaml'),
    ('rime-frost_geography.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/geography.dict.yaml'),
    ('rime-frost_exthot.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/exthot.dict.yaml'),
    ('rime-frost_game.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/game.dict.yaml'),
    ('rime-frost_music.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/music.dict.yaml'),
    ('rime-frost_media.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/media.dict.yaml'),
    ('rime-frost_animal.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/animal.dict.yaml'),
    ('rime-frost_chess.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/chess.dict.yaml'),
    ('rime-frost_chess2.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/chess2.dict.yaml'),
    ('rime-frost_industry_product.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/industry_product.dict.yaml'),
    ('rime-frost_inputmethod.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/inputmethod.dict.yaml'),
    ('rime-frost_literature.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/literature.dict.yaml'),
    ('rime-frost_name.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/name.dict.yaml'),
    ('rime-frost_name2.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/name2.dict.yaml'),
    ('rime-frost_place.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/place.dict.yaml'),
    ('rime-frost_shulihua.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/shulihua.dict.yaml'),
    # ---- 朙月拼音（raw.githubusercontent，jsDelivr 对该文件返回 403） ----
    ('rime-frost_luna_pinyin.txt', 'https://raw.githubusercontent.com/gaboolic/rime-frost/master/luna_pinyin.dict.yaml'),
]


# 扩展源：优先取上游 latest release 的 Rime 词典，避免自己爬站
# (缓存文件名, GitHub 仓库, 资源名匹配规则, 兜底地址)
EXTENDED = [
    ('ext-moegirl.dict.yaml', 'outloudvi/mw2fcitx',
     lambda name: name == 'moegirl.dict.yaml',
     'https://github.com/outloudvi/mw2fcitx/releases/download/20261024/moegirl.dict.yaml'),
    ('ext-zhwiki.dict.yaml', 'felixonmars/fcitx5-pinyin-zhwiki',
     lambda name: name.startswith('zhwiki-') and name.endswith('.dict.yaml'),
     'https://github.com/felixonmars/fcitx5-pinyin-zhwiki/releases/download/0.3.1/zhwiki-20261018.dict.yaml'),
]


def resolve_extended_url(repo: str, matcher) -> str:
    """通过 GitHub API 找 latest release 里的目标资源；失败时由调用方回退。"""
    api = f'https://api.github.com/repos/{repo}/releases/latest'
    req = urllib.request.Request(api, headers={'User-Agent': 'msp-dict-build',
                                               'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    for asset in data.get('assets', []):
        if matcher(asset.get('name', '')):
            return asset['browser_download_url']
    raise OSError(f'{repo} 的 latest release 中没有匹配的资源')


def download_one(url: str, out_path: Path, retries: int) -> bool:
    """单文件下载，失败重试；成功返回 True。

    下载先写 ``<目标>.part``，校验非空后再原子替换目标文件：
    中断或失败不会在缓存目录留下半截文件，旧的完整文件也不会被破坏。
    """
    part_path = out_path.with_name(out_path.name + '.part')
    for attempt in range(1, retries + 1):
        try:
            if part_path.exists():
                part_path.unlink()
            urllib.request.urlretrieve(url, part_path)
            if part_path.stat().st_size == 0:
                raise OSError('下载结果为空文件')
            # 校验通过才替换正式文件
            os.replace(part_path, out_path)
            print(f'  OK ({out_path.stat().st_size // 1024}KB)', flush=True)
            return True
        except Exception as e:  # 网络抖动/CDN 限流：重试后再判定失败
            print(f'  重试 {attempt}/{retries}: {e}')
            if part_path.exists():
                try:
                    part_path.unlink()
                except OSError:
                    pass
            if attempt < retries:
                time.sleep(3 * attempt)
    return False


def is_usable_cache(path: Path) -> bool:
    """判断已有缓存文件是否可用。

    规则：必须是普通文件、非空，且不是下载过程中的临时文件（*.part）。
    """
    try:
        if path.name.endswith('.part'):
            return False
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def sha256_of_file(path: Path) -> str:
    """计算文件 SHA-256（大文件按块读取）。"""
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now_iso() -> str:
    """当前 UTC 时间（秒级 ISO-8601）。"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def file_mtime_iso(path: Path) -> str:
    """文件最后修改时间（UTC ISO-8601），用于标注「沿用旧缓存」的溯源时间。"""
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime(
        '%Y-%m-%dT%H:%M:%SZ')


def describe_source(path: Path, url: str, status: str) -> dict:
    """生成单个词源的溯源记录。"""
    stat = path.stat()
    return {
        'file': path.name,
        'url': url,
        'status': status,
        'fetched_at': file_mtime_iso(path),
        'size_bytes': stat.st_size,
        'sha256': sha256_of_file(path),
    }


def write_source_metadata(cache_dir: Path, entries: List[dict]) -> Path:
    """把词源溯源信息写入 cache/sources_metadata.json。

    每次下载都会刷新该文件，字段包含来源 URL、拉取时间、原始文件大小与
    SHA-256，保证上游动态数据可追溯。
    """
    path = cache_dir / 'sources_metadata.json'
    payload = {
        'format': 'msp-dict-source-metadata/1',
        'generated_at': utc_now_iso(),
        'description': '上游词源溯源信息（URL / 拉取时间 / 大小 / SHA-256）',
        'sources': entries,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding='utf-8')
    return path


def download_extended(cache_dir: Path, force: bool, retries: int,
                      meta: List[dict] = None) -> list:
    """下载扩展源；返回失败的文件名列表（默认只告警）。"""
    failed = []
    if meta is None:
        meta = []
    for fname, repo, matcher, fallback in EXTENDED:
        out_path = cache_dir / fname
        if not force and is_usable_cache(out_path):
            print(f'SKIP {fname} ({out_path.stat().st_size // 1024}KB)')
            meta.append(describe_source(out_path, fallback, 'cached'))
            continue
        print(f'DOWN {fname}...', flush=True)
        url = fallback
        try:
            url = resolve_extended_url(repo, matcher)
            print(f'  latest: {url}')
        except Exception as e:
            print(f'  查询 latest release 失败（{e}），回退固定版本')
        if not download_one(url, out_path, retries):
            failed.append(fname)
        elif meta is not None:
            meta.append(describe_source(out_path, url, 'downloaded'))
    return failed


def main() -> int:
    parser = argparse.ArgumentParser(description='下载 rime-ice / rime-frost 词库源到 cache/')
    parser.add_argument('--cache', default=str(ROOT / 'cache'), help='缓存目录')
    parser.add_argument('--force', action='store_true', help='已存在也重新下载')
    parser.add_argument('--retries', type=int, default=3, help='单个文件的下载重试次数')
    parser.add_argument('--no-extended', action='store_true',
                        help='只下载基础源（rime-ice / rime-frost）')
    parser.add_argument('--extended-only', action='store_true',
                        help='只下载扩展源（萌娘百科 / 中文维基）')
    parser.add_argument('--strict-ext', action='store_true',
                        help='扩展源下载失败时返回非 0（默认只告警，避免第三方波动阻断发布）')
    args = parser.parse_args()

    cache_dir = Path(args.cache)
    cache_dir.mkdir(parents=True, exist_ok=True)

    failed = []
    meta: List[dict] = []
    for fname, url in ([] if args.extended_only else FILES):
        out_path = cache_dir / fname
        if not args.force and is_usable_cache(out_path):
            print(f'SKIP {fname} ({out_path.stat().st_size // 1024}KB)')
            meta.append(describe_source(out_path, url, 'cached'))
            continue
        if out_path.exists() and not is_usable_cache(out_path):
            # 0 字节的残片不算有效缓存，先删掉再重下
            print(f'  清理无效缓存: {fname}')
            try:
                out_path.unlink()
            except OSError:
                pass
        print(f'DOWN {fname}...', flush=True)
        if not download_one(url, out_path, args.retries):
            failed.append(fname)
        else:
            meta.append(describe_source(out_path, url, 'downloaded'))

    base_total = 0 if args.extended_only else len(FILES)
    print(f'\n基础源完成：{base_total - len(failed)}/{base_total} 个文件')

    ext_failed = []
    if not args.no_extended:
        print('\n=== 扩展源（萌娘百科 / 中文维基） ===')
        ext_failed = download_extended(cache_dir, args.force, args.retries, meta)

    meta_path = write_source_metadata(cache_dir, meta)
    print(f'词源溯源信息已写入: {meta_path}')

    if failed:
        print('失败文件: ' + ', '.join(failed))
        print('可重跑本脚本补齐（已存在的文件会跳过）')
        return 1
    if ext_failed:
        print('扩展源缺失: ' + ', '.join(ext_failed))
        if args.strict_ext:
            print('--strict-ext 已开启，视为失败')
            return 1
        print('将降级为仅基础源构建（merge.py 会告警）')
    print('下一步: python scripts/merge.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
