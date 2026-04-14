# 微软拼音增强词库

<!-- Badges -->
[![Daily Build](https://github.com/arbaleast/msp-dict/actions/workflows/daily-build.yml/badge.svg)](https://github.com/arbaleast/msp-dict/actions)
[![Release](https://img.shields.io/github/v/release/arbaleast/msp-dict?color=blue)](https://github.com/arbaleast/msp-dict/releases/latest)

基于 [Rime](https://github.com/rime) 词库转换的微软拼音用户词典，每日自动更新。

## 特性

- **超大海量词库** - 200万+ 词条，涵盖互联网热词、专业术语
- **每日自动更新** - GitHub Actions 每日 03:30 UTC 构建
- **多版本可选** - 完整版 / 标准版 / 高频版，满足不同需求
- **即插即用** - 下载即可导入，无需复杂配置

## 下载

| 文件 | 词条数 | 说明 | 大小 |
|------|--------|------|------|
| [msp_win10.dat](https://github.com/arbaleast/msp-dict/releases/latest) | 279,506 | **Win10 DAT 直接导入**（推荐） | 10 MB |
| [msp_full.dat](https://github.com/arbaleast/msp-dict/releases/latest) | 1,761,099 | 完整版 | 67 MB |

> **推荐使用 `msp_win10.dat`**，可直接导入 Windows 10/11 微软拼音。

## 快速上手

### Windows 10/11 导入 DAT 文件

1. 下载 `msp_win10.dat`
2. 打开 **设置** → **时间和语言** → **语言和区域**
3. 找到 **微软拼音** → **词典** → **导入词典**
4. 选择下载的 `msp_win10.dat` 文件

### TXT 格式导入

1. 下载 `msp_freq500.txt`（推荐，高频词更精准）
2. 打开微软拼音设置 → 词典 → 添加词典 → 选择 TXT 文件

## 词库格式

### Win10 DAT (推荐)

```
mschxudp 二进制格式
├── 词条: 324,328
├── 拼音: 保留原始拼音
└── 编码: UTF-16LE
```

### TXT 格式

```
词语    词频
人工智能    31450
机器学习    20106
神经网络    15620
深度学习    7020
区块链    6670
自然语言处理    4532
```

## 数据来源

| 来源 | 词条数 | 说明 |
|------|--------|------|
| [rime-ice](https://github.com/iDvel/rime-ice) | ~190万 | 雾凇拼音，最全的 Rime 中文词库 |
| [rime-frost](https://github.com/gaboolic/rime-frost) | ~180万 | 白霜拼音，专业领域词库补充 |

## 自动化

每天 03:30 UTC (北京时间 11:30) 自动运行，构建新版本词库：

```yaml
schedule:
  - cron: '30 3 * * *'
```

每次运行自动：
1. 下载 rime-ice + rime-frost 最新词库
2. 合并去重，保留最高词频
3. 生成 5 个版本的 DAT 文件
4. 创建新 release（格式：`v1.2-YYYY-MM-DD`）

> [!TIP]
> 点击 Assets 展开下载所有版本：`msp_full.dat` / `msp_freq10.dat` / `msp_freq50.dat` / `msp_freq100.dat` / `msp_freq500.dat`

## 项目结构

```
msp-dict/
├── .github/workflows/
│   └── daily-build.yml    # 每日自动构建
├── src/
│   ├── builder.py         # 词库构建器
│   ├── builder_win10.py   # Win10 DAT 格式
│   ├── importer.py        # 批量导入
│   └── converter.py       # 格式转换
├── SPEC.md                # DAT 格式规范
└── README.md
```

## 本地构建

```bash
git clone https://github.com/arbaleast/msp-dict.git
cd msp-dict
pip install requests

# 下载词库
mkdir -p cache
curl -sL "https://raw.githubusercontent.com/iDvel/rime-ice/main/cn_dicts/base.dict.yaml" -o cache/rime-ice_base.txt
curl -sL "https://raw.githubusercontent.com/gaboolic/rime-frost/master/cn_dicts/base.dict.yaml" -o cache/rime-frost_base.txt

# 运行构建
python3 -c "
import struct

# 解析 Rime 格式
def parse_rime(content):
    entries = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#'): continue
        parts = line.split('\t')
        if len(parts) >= 3:
            entries.append((parts[0], parts[1], int(parts[-1])))
    return entries

# 合并去重...
print('请参考 src/ 目录下的构建脚本')
"
```

## License

遵循上游 Rime 词库协议。
