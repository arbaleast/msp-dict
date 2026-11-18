#!/usr/bin/env python3
"""
生成梯度规模测试包（1w / 3w / 5w / 10w），用于压测构建/解析链路。

不含任何清洗之外的选词策略：直接取全量词库中词频最高的前 N 条，
保留单字与长词的真实占比，用来观察不同规模下构建、解析、校验的耗时与内存。

输出（默认 .tmp/scale_samples/）:
    msp_scale_10000.dat ...
    scale_report.json          每个包的词条数/大小/词频分位数/单字占比/长词占比

用法:
    python scripts/make_scale_samples.py
    python scripts/make_scale_samples.py --input .tmp/msp_full.txt --output-dir .tmp/scale_samples
    python scripts/make_scale_samples.py --sizes 10000,30000,50000,100000
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.builder_win10 import Win10MSPinyinBuilder  # noqa: E402
from src.format_spec import utf16_units  # noqa: E402
from src.validator import DatValidator  # noqa: E402


def quantiles(values, points=(0.5, 0.9, 0.99)):
    if not values:
        return {}
    ordered = sorted(values)
    result = {}
    for p in points:
        idx = min(len(ordered) - 1, int(round(p * (len(ordered) - 1))))
        result[f'p{int(p * 100)}'] = ordered[idx]
    result['max'] = ordered[-1]
    return result


def build_sample(source: Path, size: int, output_dir: Path, timestamp: int) -> dict:
    builder = Win10MSPinyinBuilder(timestamp=timestamp)
    selected = builder.add_from_text_file(str(source), limit=size)

    # 输入侧分布（用于解释词条构成）
    freqs = []
    lengths = []
    with open(source, encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= selected:
                break
            parts = line.rstrip('\n').split('\t')
            if len(parts) >= 3:
                try:
                    freqs.append(int(parts[2]))
                except ValueError:
                    pass
            lengths.append(utf16_units(parts[0]))

    total = len(lengths) or 1
    output = output_dir / f'msp_scale_{size}.dat'
    output.write_bytes(builder.build())
    report = DatValidator(now=timestamp).validate(str(output))

    record = {
        'requested': size,
        'entries': builder.stats.accepted,
        'file': output.name,
        'size_bytes': output.stat().st_size,
        'size_mb': round(output.stat().st_size / 1024 / 1024, 2),
        'dropped': builder.stats.skipped,
        'freq_quantiles': quantiles(freqs),
        'single_char_ratio': round(sum(1 for n in lengths if n == 1) / total, 4),
        'short_ratio': round(sum(1 for n in lengths if 2 <= n <= 4) / total, 4),
        'long_ratio': round(sum(1 for n in lengths if n > 4) / total, 4),
        'validation_exit_code': report.exit_code,
        'validation_issues': [i.code for i in report.issues],
    }
    print(f"{size:>7,} 条 -> 写入 {record['entries']:,} 条  "
          f"{record['size_mb']:.2f} MB  "
          f"词频 p50={record['freq_quantiles'].get('p50')} "
          f"单字={record['single_char_ratio']:.1%} 长词={record['long_ratio']:.1%}  "
          f"校验={'OK' if report.exit_code == 0 else report.exit_code}")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description='生成梯度规模测试包')
    parser.add_argument('--input', default=str(ROOT / '.tmp' / 'msp_full.txt'))
    parser.add_argument('--output-dir', default=str(ROOT / '.tmp' / 'scale_samples'))
    parser.add_argument('--sizes', default='10000,30000,50000,100000')
    parser.add_argument('--timestamp', type=int, default=0)
    args = parser.parse_args()

    source = Path(args.input)
    if not source.exists():
        print(f'错误: 输入文件不存在: {source}', file=sys.stderr)
        return 1

    import time
    timestamp = args.timestamp or int(time.time())
    sizes = [int(s) for s in args.sizes.split(',') if s.strip()]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print('规模        写入       大小        分布')
    records = [build_sample(source, size, output_dir, timestamp) for size in sizes]
    (output_dir / 'scale_report.json').write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"\n报告: {output_dir / 'scale_report.json'}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
