# 🎯 微软拼音增强词库

> 让你的输入法更懂你——223万+ 条有效词条，三档可选，每月自动更新

[![Biweekly Build](https://github.com/arbaleast/msp-dict/actions/workflows/biweekly-build.yml/badge.svg)](https://github.com/arbaleast/msp-dict/actions)
[![Release](https://img.shields.io/github/v/release/arbaleast/msp-dict?color=blue)](https://github.com/arbaleast/msp-dict/releases/latest)
[![词条数](https://img.shields.io/badge/词条-223万+-blue)](https://github.com/arbaleast/msp-dict/releases)

---

## ⚡ 只想用词库？直接下载

**不需要运行任何代码，也不需要装 Python。**

1. 打开 [Releases 页面](https://github.com/arbaleast/msp-dict/releases/latest)；
2. 下载 **`msp_lite.dat`**（约 855 KB）；
3. 导入微软拼音（Win10 / Win11 路径见 [🚀 导入步骤](#-导入步骤windows-10--11)）。

```bash
# 顺手校验一下文件没被改坏（可选）
sha256sum msp_lite.dat          # Linux / macOS
certutil -hashfile msp_lite.dat SHA256   # Windows
```

Release 里还提供 `msp_standard.dat`（进阶）、`msp_full.dat`（存档/转换）、`msp_win10.dat`（旧链接兼容副本）
和 `SHA256SUMS`（校验和清单）。选哪个看 [📦 下载与版本选择](#-下载与版本选择)。

---

## 📑 目录

| 章节 | 适合谁 | 内容 |
|---|---|---|
| [⚡ 只想用词库？直接下载](#-只想用词库直接下载) | 普通用户 | 三步导入，不用装环境 |
| [📖 项目简介](#-项目简介) | 所有人 | 项目做了什么、附带了什么工具 |
| [📦 下载与版本选择](#-下载与版本选择) | 普通用户 | 四档词库对比、容量与卡顿阈值 |
| [🚀 导入步骤（Windows 10 / 11）](#-导入步骤windows-10--11) | 普通用户 | 正确入口、导入失败排查 |
| [🧪 Canary 探针](#-canary-探针验证词库是否真正加载) | 进阶用户 | 验证 Windows 是否真加载、有没有静默截断 |
| [🆘 管理界面卡死：强制恢复](#-管理界面转圈卡死强制恢复) | 出问题的用户 | 备份 + 清库 + 回滚的完整流程 |
| [📚 数据来源与可追溯性](#-数据来源与可追溯性) | 所有人 | 词源清单、配额策略、SHA-256 溯源 |
| [🛠️ 开发者指南](#-开发者指南构建词库) | 开发者 | 本地构建三档、脚本参数全表 |
| [🕷️ 爬虫（可选）](#-爬虫可选采集新词) | 采集者 | `crawler update` 完整链路与依赖 |
| [📐 词库格式（mschxudp）](#-词库格式mschxudp) | 开发者 | 二进制布局与字段约束 |
| [🐞 问题反馈](#-问题反馈) | 所有人 | 提 Issue 需要附什么 |
| [🙏 致谢](#-致谢) | — | 上游项目 |

---

## 📖 项目简介

本项目将 [Rime-Frost（白霜拼音）](https://github.com/gaboolic/rime-frost) 与
[Rime-Ice（雾凇拼音）](https://github.com/iDvel/rime-ice) 作为基础源，融合
[萌娘百科](https://github.com/outloudvi/mw2fcitx)、
[中文维基百科](https://github.com/felixonmars/fcitx5-pinyin-zhwiki) 与搜狗细胞词库等扩展源，
合并、清洗、按档位配额重排后，生成 Windows 10/11 微软拼音「用户定义的短语」可直接导入的
`mschxudp` 二进制词库。

同时内置两项核心诊断工具：

- **二进制强校验器 (`validate`)**：精确区分格式错误、文件损坏、内容违规与容量超限，
  不再笼统归为「文件已损坏」。
- **Canary 探针诊断 (`check-canary`)**：注入首尾探针，通过记事本盲打与导出回环，
  确认 Windows 是否真实加载、是否发生静默截断。

> 本项目只生成「用户定义的短语」（`mschxudp`）。微软拼音的「自学习词汇」
> （`ChsPinyinUDL`，文件头 `55AA8881`）是另一套格式，本项目不生成、也不接受。

---

## 📦 下载与版本选择

<!-- STATS:START -->
| 文件 | 词条数 | 大小 | 适用场景 |
|:---|---:|---:|:---|
| **msp_lite.dat** | 19,988 | 855 KB | Windows 10/11 直接导入（推荐） |
| msp_standard.dat | 48,986 | ~2 MB | 进阶用户；管理页会明显卡顿 |
| msp_full.dat | 2,238,515 | ~118 MB | 存档 / 转 Rime 等，Windows 无法完整导入 |
| msp_win10.dat | 19,988 | 855 KB | 兼容旧链接（= msp_lite.dat） |
<!-- STATS:END -->

| 档位 | 规模 | 说明 |
|---|---:|---|
| `msp_lite.dat` | 约 2 万条 | **强烈推荐**。剔除单字与低价值长句，按真实词频保留常用词与核心专有名词 |
| `msp_standard.dat` | 约 5 万条 | 进阶可选。覆盖更广，但管理界面会明显卡顿 |
| `msp_full.dat` | 全量 220 万+ | **切勿直接导入微软拼音**。仅供存档，或用深蓝词库转换器转入 Rime / 小狼毫 |
| `msp_win10.dat` | 等同 Lite | 兼容旧下载链接的副本，内容与 `msp_lite.dat` 完全一致 |

> [!IMPORTANT]
> **为什么默认推荐 `msp_lite.dat`？**
> 微软拼音打开「用户定义的短语」设置页时会**一次性加载全部词条**构建列表：
> ≤ 2 万条流畅；2~5 万条明显卡顿；超过 5 万条会导致设置页转圈假死甚至无法点击「清除」。
> `msp_lite.dat` 已剔除冗余单字与低价值长句，精选高频词与核心专有名词。

Release 统一按日期命名（`vYYYY.MM.DD — 微软拼音增强词库`），只保留最近 3 个版本；
每个版本附带 `SHA256SUMS` 用于校验。

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
- **文件已损坏**（退出码 3）：截断、偏移表越界或非递增、UTF-16LE 未对齐、分隔符缺失、
  头部/记录保留字节被写脏；
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
| `[MANIFEST]` | SHA-256、文件大小与词条计数一致性 |
| `[WINDOWS]` | 微软拼音实际加载状态——**永远是「待实机验证」** |

`[WINDOWS]` 不会因为 Python 校验通过而变绿，这是刻意设计：代码无法替代真机结论。

### 实测闭环

1. 导入 `msp_lite_canary.dat`（入口同上）。该文件**不随 Release 发布**（正式产物零探针），
   请从最近一次 Actions 构建的 `msp-dict-dat-*` artifact 获取，或按上面的命令本地生成。
2. 记事本盲打 `cikutanzhen` → 应出现「词库探针已生效」；
   盲打 `zuiweitan` → 应出现「词库尾部已生效」。
3. 在设置页点 **导出**，对导出的文件再跑一次 `check-canary`：
   探针仍在、词条数不减少 = Windows 没有静默截断。

完整说明与结果解读见 [docs/CANARY_TESTING.md](docs/CANARY_TESTING.md)。

---

## 🆘 管理界面转圈卡死：强制恢复

> **⚠️ 严重警告 / WARNING**
>
> 本节涉及**删除微软拼音的用户词库文件**。这些文件里存放着你的**自定义词条**和
> **输入法自学习数据**（你平时手动输入、修正过的词条都会被微软拼音记进去）。
> 直接删除 = **这些数据永久丢失，无法从任何地方找回**。
>
> **请先做完第 0 步的备份，再往下操作。**
>
> 同时请注意：
> - 只操作 `%LocalAppData%\Microsoft\InputMethod\Chs` 与 `%AppData%\Microsoft\InputMethod\Chs`
>   **这两个目录内的词库文件**；
> - **绝对不要删除整个 `InputMethod` 目录**，那会破坏输入法注册信息，可能导致系统
>   找不到微软拼音（表现为输入法无法唤起、需要重新安装语言包）；
> - 清理 `ChsPinyinUDL.dat` / `ChsPinyinEUDL.dat` 会**一并清空自学习词汇**，
>   这部分数据只能靠重新使用输入法慢慢积累；
> - 恢复完成后请重新导入 `msp_lite.dat`，**不要导入 `msp_full.dat`**——那会让问题复发。

### 第 0 步：必须先备份（不可跳过）

在 **管理员** PowerShell / CMD 里执行，把两个目录整个复制到桌面：

```bat
mkdir "%USERPROFILE%\Desktop\msp-backup"

REM 本机用户数据（自定义短语、自学习、删除候选记录等）
xcopy "%LOCALAPPDATA%\Microsoft\InputMethod\Chs" "%USERPROFILE%\Desktop\msp-backup\Chs" /E /I /H

REM 漫游配置（若存在）
xcopy "%APPDATA%\Microsoft\InputMethod\Chs" "%USERPROFILE%\Desktop\msp-backup\Chs-roaming" /E /I /H
```

备份完成后，确认桌面上出现 `msp-backup\Chs\` 目录且里面能看到 `ChsPinyin*.dat` / `ChsPinyin*.lex` 文件，再继续。

> **回滚方法**：如果清理后想找回原来的自定义词条，把备份里的 `ChsPinyinUDP.lex`
> （自定义短语）与 `ChsPinyinEUDL.dat` / `ChsPinyinUDL.dat`（自学习）**原样拷回**
> `%LocalAppData%\Microsoft\InputMethod\Chs\`，然后注销重登即可。

### 第 1 步：结束占用进程

任务管理器 → **详细信息** 选项卡 → 结束：

- `SystemSettings.exe`（设置页，就是一直转圈的那个）
- `Windows 输入体验`（`TextInputHost.exe`）
- `ctfmon.exe`（输入法框架，系统会按需自动重启它）

命令行等价：

```bat
taskkill /f /im SystemSettings.exe
taskkill /f /im TextInputHost.exe
taskkill /f /im ctfmon.exe
```

### 第 2 步：清理异常词库文件

在 `%LocalAppData%\Microsoft\InputMethod\Chs\` 中删除（或改名成 `.bak`）这些文件：

| 文件 | 内容 | 删掉的后果 |
|---|---|---|
| `ChsPinyinUDP.lex` | **用户自定义短语**（你导入的词库） | 导入的词库消失，需重新导入 |
| `ChsPinyinEUDL.dat` | 用户扩展自学习数据 | 自学习记录清空 |
| `ChsPinyinUDL.dat` | 自学习词汇库 | 自学习记录清空 |
| `ChsPinyinIH.dat` | 内部用户词条存储 | 清空 |
| `ChsPinyinDeletedCands.dat` | 删除候选记录 | 清空 |

如果提示文件被占用，说明进程还没退干净——**先注销登录再删**，不要强行结束系统关键进程。

### 第 3 步：注销并重新登录

让输入法服务重新加载空词库。重新打开设置页，列表应为空、可以正常操作。
确认没问题后再导入 `msp_lite.dat`。

---

## 📚 数据来源与可追溯性

### 词源清单

| 上游 | 角色 | 内容 |
|---|---|---|
| [Rime-Frost（白霜拼音）](https://github.com/gaboolic/rime-frost) | 基础源 | base / ext / 8105 / others + 20 余个领域细胞词库（美食、成语、医药、计算机、地名、姓名等） |
| [Rime-Ice（雾凇拼音）](https://github.com/iDvel/rime-ice) | 基础源 | base / ext / 8105 / others（tencent 为纯词频表，无拼音，合并阶段剔除） |
| [萌娘百科](https://github.com/outloudvi/mw2fcitx) | 扩展源 | ACG / 二次元词条 |
| [中文维基百科](https://github.com/felixonmars/fcitx5-pinyin-zhwiki) | 扩展源 | 百科实体与专有名词 |
| 搜狗细胞词库（`.scel`） | 扩展源 | 可选：网络流行新词、计算机、医药、财经、热门游戏等（需自行放入 `cache/scel/`） |

### 分档配额

扩展源的原始词频尺度与基础源完全不同（维基/萌娘多为固定值 1），直接混排会挤掉日常高频词，
所以按档位做**配额保护**（实测值）：

| 档位 | 基础源占比 | 扩展源占比 | 说明 |
|---|---:|---:|---|
| `msp_lite.dat` | **88%** | 12% | 扩展源上限约 2,400 条 |
| `msp_standard.dat` | **78%** | 22% | 扩展源上限约 11,000 条 |
| `msp_full.dat` | 全量 | 全量 | 无配额限制 |

同一拼音下，扩展源词条**不会挤占基础高频常用词的第 1 候选位**。

### 可追溯性：每一份数据都带 SHA-256

本项目对上游动态数据做完整溯源，方便复现与排查：

| 元数据文件 | 由谁生成 | 内容 |
|---|---|---|
| `cache/sources_metadata.json` | `scripts/download_frost.py` | 每个下载源的 URL / 状态 / 时间 / 大小 / **SHA-256** |
| `msp_full.meta.json` | `scripts/merge.py` | 基础源与扩展源各自的 SHA-256、合并条数、可写入条数、产物 SHA-256 |
| `<输出名>.meta.json` | `crawler/pipeline.py` | 采集输出的条目数与 SHA-256、各数据源贡献条数 |
| `SHA256SUMS` | `biweekly-build.yml` | 四个 Release 产物的 SHA-256 清单 |

想复现某次构建：拿 `sources_metadata.json` 里的 SHA-256 校验源文件，再按
`msp_full.meta.json` 里的条数比对产物即可。

### 自动更新流程

GitHub Actions **每月 1 日**运行，安排两个低峰时段：

- 主：`04:17 UTC`（北京时间 12:17）
- 备：`12:17 UTC`（北京时间 20:17）——主任务被平台延迟时的兜底

两次跑的是同一个按日期命名的 tag（`vYYYY.MM.DD`），同日重跑只更新不新建。
GitHub 的定时任务不保证准点启动，实际可能延后数小时；也可用
[Actions 页面手动触发](https://github.com/arbaleast/msp-dict/actions/workflows/biweekly-build.yml)。

```
下载源词库（30+ 文件，约 140MB，含扩展源；每源支持 jsDelivr / Fastly / GitHub Raw 三镜像回退）
  → merge.py 合并去重（同词同读音保留，多音字各读音都保留，剔除无拼音项）
  → build_releases.py 构建 lite / standard / full + msp_win10.dat
  → validate 逐文件校验（失败即阻断发布）
  → build_releases.py --with-canary 生成诊断产物 → check-canary 校验
  → update_readme.py 刷新本页统计 → 提交 → 发布 Release（标题 vYYYY.MM.DD — 微软拼音增强词库）
  → 生成 SHA256SUMS → 淘汰第 4 个及更早的历史版本
```

正式产物与 Canary 产物完全隔离：Canary 只生成 `msp_lite_canary.dat`，不会污染三档词库。

---

## 🛠️ 开发者指南：构建词库

### 安装

```bash
git clone https://github.com/arbaleast/msp-dict.git
cd msp-dict

# 核心链路（src/）只用标准库；requests 是唯一的基础依赖
pip install -e ".[test]"          # 日常开发 + 跑测试
pip install -e ".[crawler]"       # 需要跑爬虫时（额外装 python-dotenv / pypinyin）
```

装好之后可以用 `msp-dict <子命令>`，等价于 `python -m src.cli <子命令>`。

### 完整构建流程

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

`python scripts/update_readme.py` 会用 `build_summary.json` 刷新本页的词条数与大小，
CI 在每次构建后自动执行；本地也可以手动跑，脚本是幂等的。

### 脚本参数速查

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
需要严格时加 `--strict-ext`。

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

### 文本词库格式

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

### 项目结构

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
│   └── update_readme.py       # 自动刷新本页统计
├── tests/                     # pytest（fixtures/ 下是真实 Windows 样本与 SCEL 样本）
├── crawler/                   # 可选词条采集器（见下节）
├── docs/
│   ├── ISSUE3_DIAGNOSIS.md    # 导入失败/卡死的实证诊断
│   └── CANARY_TESTING.md      # 探针测试完整指南
├── AGENTS.md                  # Agent 入口（规则正文在 .trellis/spec/）
├── pyproject.toml             # 项目元数据 + pytest / coverage 配置
└── README.md
```

---

## 🕷️ 爬虫（可选）：采集新词

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

---

## 📐 词库格式（mschxudp）

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

<!-- BUILD_DATE: 2026-11-18 -->

⭐ **喜欢这个项目？给个 Star 吧！**
