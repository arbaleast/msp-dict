# 🎯 微软拼音增强词库

> 让你的输入法更懂你——101万+ 条有效词条，三档可选，半月自动更新

[![Biweekly Build](https://github.com/arbaleast/msp-dict/actions/workflows/biweekly-build.yml/badge.svg)](https://github.com/arbaleast/msp-dict/actions)
[![Release](https://img.shields.io/github/v/release/arbaleast/msp-dict?color=blue)](https://github.com/arbaleast/msp-dict/releases/latest)
[![词条数](https://img.shields.io/badge/词条-101万+-blue)](https://github.com/arbaleast/msp-dict/releases)

---

## 📖 项目简介

本项目把 [Rime-Frost（白霜拼音）](https://github.com/gaboolic/rime-frost) 与
[Rime-Ice（雾凇拼音）](https://github.com/iDvel/rime-ice) 的词库合并、清洗、重排后，
生成 Windows 10/11 微软拼音「用户定义的短语」可直接导入的 `mschxudp` 二进制词库。

除了词库本身，仓库还提供两样工程能力：

- **二进制强校验器**：`python -m src.cli validate <file.dat>`，把「格式错误 / 文件损坏 /
  候选位与内容违规 / 容量超限」分开报告，不再笼统地归为「文件已损坏」；
- **Canary 探针诊断**：生成带首尾探针的独立诊断词库，用记事本盲打即可确认
  Windows 是否真的加载了词条、有没有静默截断。

> 本项目只生成「用户定义的短语」（`mschxudp`）。微软拼音的「自学习词汇」
> （`ChsPinyinUDL`，文件头 `55AA8881`）是另一套格式，本项目不生成、也不接受。

---

## 📦 下载与版本选择

到 [最新 Release](https://github.com/arbaleast/msp-dict/releases/latest) 的 Assets 里下载。
**默认只需要 `msp_lite.dat` 一个文件。**

<!-- STATS:START -->
| 文件 | 词条数 | 大小 | 适用场景 |
|:---|---:|---:|:---|
| **msp_lite.dat** | 19,992 | 869 KB | Windows 10/11 直接导入（推荐） |
| msp_standard.dat | 49,202 | ~2 MB | 进阶用户；管理页会明显卡顿 |
| msp_full.dat | 1,015,471 | ~52 MB | 存档 / 转 Rime 等，Windows 无法完整导入 |
| msp_win10.dat | 19,992 | 869 KB | 兼容旧链接（= msp_lite.dat） |
<!-- STATS:END -->

| 档位 | 规模 | 说明 |
|---|---:|---|
| `msp_lite.dat` | 约 1.5~2 万条 | **强烈推荐**。剔除单字与低价值长句，按真实词频保留常用词与核心专业词 |
| `msp_standard.dat` | 约 4.5~5 万条 | 进阶可选。覆盖更广，但管理界面会明显卡顿 |
| `msp_full.dat` | 全量 100 万+ | **切勿直接导入微软拼音**。仅供存档，或用深蓝词库转换器转入 Rime / 小狼毫 |
| `msp_win10.dat` | 等同 Lite | 兼容旧下载链接的副本，内容与 `msp_lite.dat` 完全一致 |

> [!IMPORTANT]
> 微软拼音打开「用户定义的短语」时会**一次性加载全部词条**构建列表：
>
> - ≤ 2 万条：正常；
> - 2 万 ~ 5 万：明显卡顿；
> - 5 万以上：转圈假死，甚至点不动「清除」。
>
> 所以请默认使用 `msp_lite.dat`。已经卡死无法操作？见下文「管理界面转圈卡死：强制恢复」。

---

## 🚀 导入步骤（Windows 10 / 11）

### Windows 11

1. **设置** → **时间和语言** → **语言和区域**
2. 中文(简体，中国) 右侧 **…** → **语言选项**
3. 微软拼音 右侧 **…** → **键盘选项** → **词库和自学习**
4. 在「用户定义的短语」一栏，打开开关并点击 **添加或编辑自定义短语**（会弹出独立窗口）
5. 在独立窗口点 **导入** → 选择 `msp_lite.dat`

### Windows 10

1. **设置** → **时间和语言** → **语言**
2. 中文(简体，中国) → **选项**
3. 微软拼音 → **选项** → **词库和自学习**
4. 「用户定义的短语」→ 打开开关 → **添加或编辑自定义短语**（独立窗口）→ **导入**
5. 选择 `msp_lite.dat`

> [!WARNING]
> 同一个「词库和自学习」页面上还有一个 **「导入自学习词汇」** 按钮——那是另一套格式
> （`ChsPinyinUDL`，文件头 `55AA8881`），**不接受本项目的 mschxudp `.dat`**，
> 点了必然提示「导入失败：文件格式错误或文件已损坏」。
> 只有「添加或编辑自定义短语」窗口里的「导入」才是正确入口。

### 提示「文件格式错误或文件已损坏」怎么办

先确认两件事，再怀疑文件：

1. **是不是下成了网页？** 用浏览器直接打开下载链接时可能得到 HTML。检查文件头：
   ```bash
   head -c 8 msp_lite.dat      # 应输出 mschxudp
   ```
2. **是不是点错了导入入口？** 见上面的警告：`导入自学习词汇` 不接受本项目文件。

确认无误后，用校验器做正式预检：

```bash
python -m src.cli validate msp_lite.dat
```

校验器会区分四类问题，而不是笼统的「格式错误」：

- **文件格式错误**（退出码 2）：签名/协议头/版本不对，根本不是 `mschxudp`；
  若文件其实是自学习词汇库（`55AA8881`）或 Windows 内部存储（`55AA8880`），会直接提示该走哪个入口；
- **文件已损坏**（退出码 3）：截断、偏移表越界或非递增、UTF-16LE 未对齐、分隔符缺失；
- **候选位置/内容违规**（退出码 4）：候选序号不在 1~9、拼音非法、词条超长、重复词条；
- **容量警告**：词条数超过 2 万 / 5 万，导入会失败或让管理页假死。

退出码：`0` 通过（可含警告）、`2` 格式错误、`3` 文件损坏、`4` 内容违规。

---

## 🧪 Canary 探针：验证词库是否真正加载

**结构合法 ≠ Windows 真的加载了。** 导入可能被拒绝，也可能成功但被静默截断，
这两种情况在 Python 侧看起来都「没问题」。Canary 构建把两条探针写进词库首尾，
导入后在记事本里盲打就能分辨。

默认探针（均为合法汉语拼音音节，避免被全拼切分器忽略造成假阴性）：

| 探针 | 拼音 | 预期候选词 | 位置 |
|---|---|---|---|
| 全拼探针 | `cikutanzhen` | 词库探针已生效 | 拼音字典序靠前，验证头部 |
| 尾部探针 | `zuiweitan` | 词库尾部已生效 | 拼音字典序靠后，验证尾部未被截断 |

### 生成与检查

```bash
# 生成独立诊断产物（不会覆盖正式 msp_lite.dat），并回读二进制写 manifest
python scripts/build_releases.py --input msp_full.txt --profiles lite --with-canary

# 四维检查：STRUCT / CANARY / MANIFEST / WINDOWS
python -m src.cli check-canary msp_lite_canary.dat --manifest msp_lite_canary.json
```

也可以单文件构建：

```bash
python -m src.cli build msp_full.txt -o msp_lite_canary.dat \
  --profile lite --with-canary --manifest msp_lite_canary.json
```

探针支持成对自定义（`--canary-pinyin` / `--canary-word`，可重复）：

```bash
python -m src.cli build msp_full.txt -o probe.dat --profile lite --with-canary \
  --canary-pinyin cikutanzhen --canary-word 词库探针已生效 \
  --canary-pinyin zuiweitan  --canary-word 词库尾部已生效
```

### 四维输出

| 维度 | 含义 |
|---|---|
| `[STRUCT]` | DAT 二进制结构与 Offset Table 校验 |
| `[CANARY]` | 探针在最终文件中的物理位置、拼音/词条/候选位/字节偏移 |
| `[MANIFEST]` | SHA-256 与词条计数一致性 |
| `[WINDOWS]` | 微软拼音实际加载状态——**永远是「待实机验证」** |

`[WINDOWS]` 不会因为 Python 校验通过而变绿，这是刻意设计：代码无法替代真机结论。

### 实测闭环

1. 导入 `msp_lite_canary.dat`（入口同上）。
2. 记事本盲打 `cikutanzhen` → 应出现「词库探针已生效」；
   盲打 `zuiweitan` → 应出现「词库尾部已生效」。
3. 在设置页点 **导出**，对导出的文件再跑一次 `check-canary`：
   探针仍在、词条数不减少 = Windows 没有静默截断。

完整说明与结果解读见 [docs/CANARY_TESTING.md](docs/CANARY_TESTING.md)。

---

## 🆘 管理界面转圈卡死：强制恢复

如果已经导入了超大词库，设置页一直转圈，连「清除」都点不了，按下面顺序恢复。
**这只重置微软拼音的用户词条，不影响系统其他设置。**

1. **先备份**（可选）：打开 `%LocalAppData%\Microsoft\InputMethod\Chs`，
   把 `ChsPinyin*.dat` / `ChsPinyin*.lex` 复制到桌面。
2. **结束进程**（任务管理器 → 详细信息）：
   - `SystemSettings.exe`（设置页）
   - `Windows 输入体验`（`TextInputHost.exe`）
   - `ctfmon.exe`（输入法服务，系统会自动重启它）

   命令行等价：
   ```bat
   taskkill /f /im SystemSettings.exe
   taskkill /f /im TextInputHost.exe
   taskkill /f /im ctfmon.exe
   ```
3. **清理词库数据**：删除或改名下面目录里的词库文件
   - `%LocalAppData%\Microsoft\InputMethod\Chs`
     - `ChsPinyinUDP.lex`（用户自定义短语）
     - `ChsPinyinEUDL.dat` / `ChsPinyinUDL.dat`（自学习词汇）
     - `ChsPinyinIH.dat`（用户词条）、`ChsPinyinDeletedCands.dat`（删除候选）
   - `%AppData%\Microsoft\InputMethod\Chs`（若存在同名文件）
4. **注销并重新登录**（或重启），让输入法服务重新加载空词库。
5. 重新打开设置页，列表应为空、可以正常操作；确认后再导入 `msp_lite.dat`。

> [!WARNING]
> 若提示文件被占用，先注销再删。只处理 `Chs` 目录下的词库文件，
> 不要删除整个 `InputMethod` 目录；自学习词汇会一起清空。

---

## 📚 数据来源与自动更新

### 数据来源

| 上游 | 内容 |
|---|---|
| [Rime-Frost（白霜拼音）](https://github.com/gaboolic/rime-frost) | base / ext / 8105 / others + 21 个领域细胞词库（美食、成语、医药、计算机、地名、姓名等） |
| [Rime-Ice（雾凇拼音）](https://github.com/iDvel/rime-ice) | base / ext / 8105 / others（tencent 为纯词频表，无拼音，合并阶段剔除） |
| `crawler/` | 可选的词条采集器（搜狗、维基、B 站等），不参与默认发布流程 |

### 自动更新流程

GitHub Actions 每月 **1 日、15 日 03:30 UTC**（北京时间 11:30）运行：

```
下载源词库（30+ 文件，约 80MB）
  → merge.py 合并去重（同词保留最高词频，剔除无拼音项）
  → build_releases.py 构建 lite / standard / full + msp_win10.dat
  → validate 逐文件校验（失败即阻断发布）
  → build_releases.py --with-canary 生成诊断产物 → check-canary 校验
  → update_readme.py 刷新本页统计 → 提交 → 发布 Release
```

正式产物与 Canary 产物完全隔离：Canary 只生成 `msp_lite_canary.dat`，不会污染三档词库。

---

## 🛠️ 本地开发

```bash
git clone https://github.com/arbaleast/msp-dict.git
cd msp-dict
pip install pytest                 # 构建本身只用标准库

# 0) 下载源词库到 cache/（cache/ 不入库，新克隆必须先跑一次，约 80MB）
python scripts/download_frost.py

# 1) 合并 -> msp_full.txt（缺失源文件会直接报错，不再静默产出残缺词库）
python scripts/merge.py

# 2) 三档构建（含 msp_win10.dat 兼容副本与 build_summary.json）
python scripts/build_releases.py --input msp_full.txt

# 3) 校验
python -m src.cli validate msp_lite.dat

# 可选：梯度测试包（1w / 3w / 5w / 10w，用于对比管理页卡顿）
python scripts/make_scale_samples.py --input msp_full.txt

# 可选：单文件构建（自定义筛选）
python -m src.cli build msp_full.txt -o output.dat --profile standard --limit 40000

# 测试（CI 使用同一命令，ubuntu + windows 矩阵）
python -m pytest tests -q
```

`python scripts/update_readme.py` 会用 `build_summary.json` 刷新本页的词条数与大小，
CI 在每次构建后自动执行；本地也可以手动跑，脚本是幂等的。

### 项目结构

```
msp-dict/
├── .github/workflows/
│   ├── biweekly-build.yml     # 半月构建、校验、发布（含 Canary 检查）
│   └── test.yml               # ubuntu + windows 测试矩阵
├── src/                       # 核心库（只有库代码，无测试）
│   ├── format_spec.py         # mschxudp 规范常量与字段校验（唯一事实来源）
│   ├── parser.py              # 解析器（strict 模式区分格式错误与损坏）
│   ├── builder_win10.py       # 构建器（清洗、候选位、时间戳）
│   ├── validator.py           # 四类问题分类 + Canary 四维检查
│   ├── canary.py              # 探针定义、二进制回读、manifest
│   ├── profiles.py            # lite / standard / full 三档策略
│   ├── converter.py           # Rime ↔ mschxudp 转换
│   ├── editor.py              # 编辑器（哈希索引，批量导入 O(N)）
│   ├── exporter.py            # 导出 txt / csv / json
│   ├── importer.py            # 导入 txt / csv / Rime
│   └── cli.py                 # 命令行入口（parse/export/import/convert/add/remove/stats/build/validate/check-canary）
├── scripts/                   # 正式流水线脚本（5 个）
│   ├── download_frost.py      # 下载 rime-ice / rime-frost 源到 cache/
│   ├── merge.py               # 合并 Rime 源 -> msp_full.txt
│   ├── build_releases.py      # 三档 DAT + 兼容副本 + Canary + 构建摘要
│   ├── make_scale_samples.py  # 1w/3w/5w/10w 梯度测试包
│   └── update_readme.py       # 自动刷新本页统计
├── tests/                     # pytest（fixtures/ 下是真实 Windows 样本）
├── crawler/                   # 可选词条采集器
├── docs/
│   ├── ISSUE3_DIAGNOSIS.md    # 导入失败/卡死的实证诊断
│   └── CANARY_TESTING.md      # 探针测试完整指南
├── AGENTS.md                  # Agent 入口（规则正文在 .trellis/spec/）
├── pyproject.toml             # pytest / coverage 配置
└── README.md
```

### 词库格式（mschxudp）

```
Header: 64 字节（mschxudp + 版本 + 偏移表位置 + 词条数 + 时间戳）
词条偏移表: 4 字节 × 词条数
词条记录: magic | hanzi_offset | 候选序号(1~9) | 0x06 | 0 | 2000纪元秒
          | 拼音 UTF-16LE | 0x0000 | 词条 UTF-16LE | 0x0000
```

- 拼音只允许小写 `a-z` 与音节分隔符 `'`，最多 32 个 UTF-16 单元；
- 词条最多 64 个 UTF-16 单元；
- 候选序号是「同一拼音下的第几个候选」，从 1 起、最多 9，**不是词频**。

---

## 🐞 问题反馈

提 Issue 时请附上这些信息，能省掉大部分来回：

1. **Windows 版本**：`winver` 的完整版本号（如 Windows 11 24H2 26100.x）；
2. **文件名与 SHA-256**：
   - Windows：`certutil -hashfile msp_lite.dat SHA256`
   - Linux/macOS：`sha256sum msp_lite.dat`
3. **校验器输出**：`python -m src.cli validate msp_lite.dat` 的完整结果；
4. **Canary 实测结果**：`cikutanzhen` / `zuiweitan` 是否出候选，以及 `check-canary` 的四维输出；
5. **导入入口截图**：确认点的是「添加或编辑自定义短语 → 导入」，而不是「导入自学习词汇」。

历史问题分析见 [docs/ISSUE3_DIAGNOSIS.md](docs/ISSUE3_DIAGNOSIS.md)。

---

## 🙏 致谢

- [Rime](https://github.com/rime) — 中州韵输入法引擎
- [Rime-Ice](https://github.com/iDvel/rime-ice) — 雾凇拼音
- [Rime-Frost](https://github.com/gaboolic/rime-frost) — 白霜拼音
- [imewlconverter](https://github.com/studyzy/imewlconverter) — mschxudp 格式参考与真实样本

词库内容遵循上游 Rime 词库协议。

---

<!-- BUILD_DATE: 2026-11-17 -->

⭐ **喜欢这个项目？给个 Star 吧！**
