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
import os
import urllib.request
from pathlib import Path

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
    ('rime-frost_composite.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/composite.dict.yaml'),
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


def main() -> int:
    parser = argparse.ArgumentParser(description='下载 rime-ice / rime-frost 词库源到 cache/')
    parser.add_argument('--cache', default=str(ROOT / 'cache'), help='缓存目录')
    parser.add_argument('--force', action='store_true', help='已存在也重新下载')
    args = parser.parse_args()

    cache_dir = Path(args.cache)
    cache_dir.mkdir(parents=True, exist_ok=True)

    failed = []
    for fname, url in FILES:
        out_path = cache_dir / fname
        if out_path.exists() and not args.force:
            print(f'SKIP {fname} ({out_path.stat().st_size // 1024}KB)')
            continue
        print(f'DOWN {fname}...', flush=True)
        try:
            urllib.request.urlretrieve(url, out_path)
            print(f'  OK ({out_path.stat().st_size // 1024}KB)')
        except Exception as e:  # 网络抖动单个文件失败不中断整体下载
            print(f'  FAIL: {e}')
            failed.append(fname)

    print(f'\n完成：{len(FILES) - len(failed)}/{len(FILES)} 个文件')
    if failed:
        print('失败文件: ' + ', '.join(failed))
        print('可重跑本脚本补齐（已存在的文件会跳过）')
        return 1
    print('下一步: python scripts/merge.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
