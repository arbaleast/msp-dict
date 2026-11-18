# 开发与构建指南

面向需要自己构建词库、改代码或跑爬虫的人。只想用词库的话，看
[README](../README.md) 就够了。

## 安装

```bash
git clone https://github.com/arbaleast/msp-dict.git
cd msp-dict

# 核心链路（src/）只用标准库；requests 是唯一的基础依赖
pip install -e ".[test]"          # 日常开发 + 跑测试
pip install -e ".[crawler]"       # 需要跑爬虫时（额外装 python-dotenv / pypinyin）
```

装好之后可以用 `msp-dict <子命令>`，等价于 `python -m src.cli <子命令>`。

| 依赖组 | 内容 | 用途 |
|---|---|---|
| （基础） | `requests>=2.28` | 下载器 |
| `test` | `pytest>=7.0` | 跑测试 |
| `crawler` | `python-dotenv>=1.0`、`pypinyin>=0.49` | 爬虫补拼音、读 `.env` |

## 完整构建流程

```bash
# 0) 下载源词库到 cache/（cache/ 不入库，新克隆必须先跑一次，约 140MB）
python scripts/download_frost.py

# 1) 合并 -> msp_full.txt（缺失源文件会直接报错，不再静默产出残缺词库）
python scripts/merge.py

# 2) 三档构建（含 msp_win10.dat 兼容副本与 build_summary.json）
python scripts/build_releases.py --input msp_full.txt

# 3) 校验
python -m src.cli validate msp_lite.dat

# 可选：梯度测试包（1w / 3w / 5w / 10w，用于对比管理页卡顿）
python scripts/make_scale_samples.py --input msp_full.txt

# 测试（CI 使用同一命令，ubuntu + windows 矩阵）
python -m pytest tests -q
```

`python scripts/update_readme.py` 会用 `build_summary.json` 刷新 README 的词条数与大小，
CI 在每次构建后自动执行；本地也可以手动跑，脚本是幂等的。

## 脚本参数速查

<details>
<summary><b>scripts/download_frost.py</b></summary>

| 参数 | 默认 | 说明 |
|---|---|---|
| `--cache` | `./cache` | 缓存目录 |
| `--force` | 关 | 已存在也重新下载 |
| `--retries` | `3` | 单个文件的下载重试次数（每轮轮换镜像） |
| `--no-extended` | 关 | 不下载扩展源（萌娘/维基） |
| `--extended-only` | 关 | 只下载扩展源 |
| `--strict-ext` | 关 | 扩展源失败也视为失败（默认只告警） |

基础源缺失一律失败；扩展源缺失默认只告警（第三方站点波动不该瘫痪整个构建），
需要严格时加 `--strict-ext`。每个源支持 jsDelivr / Fastly / GitHub Raw 三镜像回退。

</details>

<details>
<summary><b>scripts/merge.py</b></summary>

| 参数 | 默认 | 说明 |
|---|---|---|
| `--cache` | `./cache` | 缓存目录（不存在直接报错） |
| `--output` | 仓库根 | 输出目录，生成 `msp_full.txt` / `CHANGELOG.md` / `msp_full.meta.json` |
| `--emit-freq-tiers` | 关 | 额外输出旧的 `msp_freq*.txt`（仅调试用） |
| `--no-extended` | 关 | 不合并扩展源 |
| `--strict-ext` | 关 | 扩展源缺失时直接失败 |

</details>

<details>
<summary><b>scripts/build_releases.py</b></summary>

| 参数 | 默认 | 说明 |
|---|---|---|
| `--input` | `msp_full.txt` | 合并后的文本词库 |
| `--output-dir` | 仓库根 | 产物目录 |
| `--profiles` | `lite,standard,full` | 要构建的档位 |
| `--timestamp` | `0`（用当前时间） | 固定时间戳以获得可复现产物 |
| `--summary` | `build_summary.json` | 构建摘要输出路径 |
| `--with-canary` | 关 | 额外生成 `<profile>_canary.dat` + `.json` |
| `--canary-only` | 关 | 只生成 Canary（必须配合 `--with-canary`） |
| `--canary-pinyin` / `--canary-word` | 默认探针 | 成对使用、可重复 |

</details>

<details>
<summary><b>scripts/make_scale_samples.py</b></summary>

| 参数 | 默认 | 说明 |
|---|---|---|
| `--input` | `msp_full.txt` | 合并后的文本词库 |
| `--output-dir` | `./scale_samples` | 梯度样本输出目录 |
| `--sizes` | `10000,30000,50000,100000` | 各档条数 |
| `--timestamp` | `0` | 固定时间戳 |

</details>

## 文本词库格式

`msp_full.txt` 与导入用的 TXT 都是 **TSV**，**拼音是必填项**：

```text
中国	zhongguo
北京	beijing
测试	ceshi
```

- 第一列：词条（纯中文）；
- 第二列：拼音，**只允许小写 `a-z` 与音节分隔符 `'`**（`zhong'guo` 也合法）；
- 第三列（可选）：词频，仅影响排序，不写入 DAT 的候选序号。

> ⚠️ 缺拼音的行会被**拦截并计入 `errors`**（不是静默跳过），也不会产生空拼音记录。
> 用 `python -m src.cli import <词库.dat> <文件.txt>` 导入后，
> 输出会列出每类错误的原因与样例。

## 爬虫

爬虫是**独立于发布流水线**的辅助工具：发布用的正式词库来自 Rime 官方词典，
爬虫用于按需补充网络热词、百科新词。

### 依赖

```bash
pip install -e ".[crawler]"
```

| 包 | 用途 | 缺失后果 |
|---|---|---|
| `pypinyin` | 给采集到的纯词条补全拼音 | 采集结果无法写入 DAT，全部进 `unresolved.txt` |
| `python-dotenv` | 读取 `.env` 里的 `SOGOU_COOKIE` | 只有搜狗细胞词库下载器不可用，其余源照常 |

> `python-dotenv` 是**可选依赖**：`crawler/fetchers/__init__.py` 用惰性加载，
> 没装它时基础命令（`--help`、非搜狗数据源）依然能正常启动。

### 用法

```bash
# 抓取所有源并写入词库（拼音自动补全）
python -m crawler.cli update --all --mspinyin output/my_words.dat

# 只抓某几个源
python -m crawler.cli update --wikipedia --moegirl --mspinyin output/my_words.dat

# 常用参数
#   --limit N        每个数据源抓取数量（默认 100）
#   --proxy URL      代理地址
#   --existing FILE  已有词库文件，用于去重
```

### 工作原理与产出

```
Fetcher 抓取纯词条
  → pypinyin 补全拼音（逐词校验合法性）
      ├─ 成功 → 写成「词条<TAB>拼音」交给 BatchImporter
      │            └─ 缺拼音 / 非法拼音 → 计入 errors，不会写入词库
      └─ 失败 → 写入 <词库同目录>/unresolved.txt（不是静默丢弃）
  → MSPinyinEditor 载入目标 DAT → 导入 → 保存
```

- `unresolved.txt` 与目标词库同目录，每行一个词；补上拼音后可以手动加回；
- 导入结束会打印 `Imported / Skipped / Errors` 与错误原因分布；
- 采集输出同时生成 `<输出名>.meta.json`，记录各源贡献条数与 SHA-256。

> ⚠️ `update` 会**改写** `--mspinyin` 指定的 DAT 文件。建议先复制一份备份再操作。

## 格式规范

词库文件是微软拼音的 `mschxudp` 容器：

```
Header: 64 字节（mschxudp + 版本 + 偏移表位置 + 词条数 + 时间戳）
词条偏移表: 4 字节 × 词条数
词条记录: magic | hanzi_offset | 候选序号(1~9) | 0x06 | 0 | 2000纪元秒
          | 拼音 UTF-16LE | 0x0000 | 词条 UTF-16LE | 0x0000
```

- 拼音只允许小写 `a-z` 与音节分隔符 `'`，最多 32 个 UTF-16 单元；
- 词条最多 64 个 UTF-16 单元；
- 候选序号是「同一拼音下的第几个候选」，从 1 起、最多 9，**不是词频**；
- 头部 `0x28–0x3F` 与记录 `+0x08–+0x0B` 是保留字节，必须为 0（校验器会拦）。

字段常量集中在 `src/format_spec.py`，是唯一事实来源；改格式必须同步
`src/parser.py`、`src/validator.py` 与测试。

## 数据溯源

| 元数据文件 | 由谁生成 | 内容 |
|---|---|---|
| `cache/sources_metadata.json` | `scripts/download_frost.py` | 每个下载源的 URL / 状态 / 时间 / 大小 / **SHA-256** |
| `msp_full.meta.json` | `scripts/merge.py` | 基础源与扩展源各自的 SHA-256、合并条数、可写入条数、产物 SHA-256 |
| `<输出名>.meta.json` | `crawler/pipeline.py` | 采集输出的条目数与 SHA-256、各数据源贡献条数 |
| `SHA256SUMS` | CI | 四个 Release 产物的 SHA-256 清单 |

## 自动更新流程

GitHub Actions **每月 1 日**运行（主 04:17 UTC / 备 12:17 UTC 兜底）：

```
下载源词库（30+ 文件，约 140MB，含扩展源；三镜像回退）
  → merge.py 合并去重（同词同读音保留，多音字各读音都保留，剔除无拼音项）
  → build_releases.py 构建 lite / standard / full + msp_win10.dat
  → validate 逐文件校验（失败即阻断发布）
  → build_releases.py --with-canary 生成诊断产物 → check-canary 校验
  → update_readme.py 刷新 README 统计 → 提交 → 发布 Release
  → 生成 SHA256SUMS → 淘汰第 4 个及更早的历史版本
```

正式产物与 Canary 产物完全隔离：Canary 只生成 `msp_lite_canary.dat`，不会污染三档词库。

## 项目结构

```
msp-dict/
├── .github/workflows/
│   ├── biweekly-build.yml     # 每月构建、校验、发布（含 Canary 检查与滚动清理）
│   └── test.yml               # ubuntu + windows 测试矩阵
├── src/                       # 核心库（只有库代码，无测试）
│   ├── format_spec.py         # mschxudp 规范常量与字段校验（唯一事实来源）
│   ├── parser.py              # 解析器（strict 模式区分格式错误与损坏）
│   ├── builder_win10.py       # 构建器（清洗、候选位、时间戳、配额）
│   ├── validator.py           # 四类问题分类 + Canary 四维检查
│   ├── canary.py              # 探针定义、二进制回读、manifest schema
│   ├── profiles.py            # lite / standard / full 三档策略
│   ├── converter.py           # Rime ↔ mschxudp 转换
│   ├── editor.py              # 编辑器（哈希索引，批量导入 O(N)）
│   ├── exporter.py            # 导出 txt / csv / json
│   ├── importer.py            # 导入 txt / csv / Rime（拼音必填）
│   └── cli.py                 # 命令行入口
├── scripts/                   # 正式流水线脚本（5 个）
│   ├── download_frost.py      # 下载 rime-ice / rime-frost / 扩展源到 cache/（三镜像回退）
│   ├── merge.py               # 合并 Rime 源 -> msp_full.txt（保留多音字各读音）
│   ├── build_releases.py      # 三档 DAT + 兼容副本 + Canary + 构建摘要
│   ├── make_scale_samples.py  # 1w/3w/5w/10w 梯度测试包
│   └── update_readme.py       # 自动刷新 README 统计
├── tests/                     # pytest（fixtures/ 下是真实 Windows 样本与 SCEL 样本）
├── crawler/                   # 可选词条采集器
├── docs/
│   ├── DEVELOPMENT.md         # 本文件
│   ├── RECOVERY.md            # 卡死恢复流程
│   ├── CANARY_TESTING.md      # 探针测试指南
│   └── ISSUE3_DIAGNOSIS.md    # 导入失败的实证诊断
├── AGENTS.md                  # Agent 入口（规则正文在 .trellis/spec/）
├── pyproject.toml             # 项目元数据 + pytest / coverage 配置
└── README.md
```

## 相关文档

- [卡死恢复流程](RECOVERY.md)
- [Canary 探针测试](CANARY_TESTING.md)
- [Issue #3 诊断报告](ISSUE3_DIAGNOSIS.md)
