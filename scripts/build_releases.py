#!/usr/bin/env python3
"""
构建三档发布词库（Issue #3）

从合并后的全量文本（默认 msp_full.txt，按词频降序）生成：

    msp_lite.dat      精简版，≤ 20,000 条，剔除单字/长句 —— Windows 10/11 默认推荐
    msp_standard.dat  标准版，≤ 50,000 条
    msp_full.dat      完整版，全量合法词条（仅存档/转其他输入法）

并复制一份 msp_win10.dat 指向精简版，兼容旧下载链接。

用法:
    python scripts/build_releases.py --input msp_full.txt
    python scripts/build_releases.py --input msp_full.txt --output-dir dist
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.builder_win10 import Win10MSPinyinBuilder  # noqa: E402
from src.profiles import PROFILES, get_profile  # noqa: E402
from src.validator import DatValidator  # noqa: E402


def build_one(profile_name: str, source: Path, output_dir: Path,
              timestamp: int, validate: bool = True) -> dict:
    profile = get_profile(profile_name)
    builder = Win10MSPinyinBuilder(timestamp=timestamp)
    selected = builder.add_from_text_file(
        str(source),
        min_freq=profile.min_freq,
        exclude_single=profile.exclude_single,
        max_word_units=profile.max_word_units,
        limit=profile.limit,
    )

    output = output_dir / f"msp_{profile.name}.dat"
    output.write_bytes(builder.build())

    record = {
        'profile': profile.name,
        'label': profile.label,
        'source': str(source),
        'file': output.name,
        'selected': selected,
        'entries': builder.stats.accepted,
        'size_bytes': output.stat().st_size,
        'size_mb': round(output.stat().st_size / 1024 / 1024, 2),
        'build': builder.stats.to_dict(),
        'windows_importable': profile.windows_importable,
    }

    print(f"[{profile.name}] {profile.describe()}")
    print(f"  读取 {selected:,} 条 -> 写入 {builder.stats.accepted:,} 条，"
          f"{record['size_mb']:.2f} MB ({record['file']})")
    print(f"  清洗: {builder.stats.summary()}")

    if validate:
        report = DatValidator(now=timestamp).validate(str(output))
        record['validation'] = {
            'exit_code': report.exit_code,
            'verdict': report.verdict,
            'issues': [
                {
                    'category': issue.category,
                    'severity': issue.severity,
                    'code': issue.code,
                    'message': issue.message,
                    'count': issue.count,
                }
                for issue in report.issues
            ],
        }
        status = 'OK' if report.exit_code == 0 else f'FAILED(exit={report.exit_code})'
        print(f"  校验: {status} — {report.verdict}")
        if report.exit_code != 0:
            for issue in report.issues:
                if issue.severity == 'error':
                    print(f"    ❌ {issue.message} ({issue.count:,})")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description='构建 lite/standard/full 三档词库')
    parser.add_argument('--input', default=str(ROOT / 'msp_full.txt'),
                        help='合并后的全量文本（词条\\t拼音\\t词频，按词频降序）')
    parser.add_argument('--output-dir', default=str(ROOT),
                        help='输出目录')
    parser.add_argument('--profiles', default='lite,standard,full',
                        help='要构建的档位，逗号分隔')
    parser.add_argument('--timestamp', type=int, default=0,
                        help='写入文件头的 Unix 时间戳（0 = 当前时间）')
    parser.add_argument('--summary', default='build_summary.json',
                        help='构建摘要 JSON 文件名')
    args = parser.parse_args()

    source = Path(args.input)
    if not source.exists():
        print(f"错误: 输入文件不存在: {source}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    import time
    timestamp = args.timestamp or int(time.time())

    profiles = [p.strip() for p in args.profiles.split(',') if p.strip()]
    for name in profiles:
        if name not in PROFILES:
            print(f"错误: 未知档位 {name!r}", file=sys.stderr)
            return 1

    records = [build_one(name, source, output_dir, timestamp) for name in profiles]

    # 兼容旧链接：msp_win10.dat 始终等于当前推荐的 lite
    if 'lite' in profiles:
        shutil.copyfile(output_dir / 'msp_lite.dat', output_dir / 'msp_win10.dat')
        print('[compat] msp_win10.dat <- msp_lite.dat')

    summary = {
        'timestamp': timestamp,
        'source': str(source),
        'profiles': records,
    }
    summary_path = output_dir / args.summary
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n',
                            encoding='utf-8')
    print(f'[summary] {summary_path}')

    failed = [r for r in records if r.get('validation', {}).get('exit_code', 0) != 0]
    if failed:
        print(f"错误: {len(failed)} 个档位未通过校验", file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
