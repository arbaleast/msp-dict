<a id="readme-top"></a>

[![Monthly Build](https://github.com/arbaleast/msp-dict/actions/workflows/biweekly-build.yml/badge.svg)](https://github.com/arbaleast/msp-dict/actions/workflows/biweekly-build.yml)
[![Latest Release](https://img.shields.io/github/v/release/arbaleast/msp-dict?color=blue&label=Release)](https://github.com/arbaleast/msp-dict/releases/latest)
[![词条数](https://img.shields.io/badge/词条-223万+-blue)](https://github.com/arbaleast/msp-dict/releases)
[![Issues](https://img.shields.io/github/issues/arbaleast/msp-dict?color=blue)](https://github.com/arbaleast/msp-dict/issues)

<div align="center">

# msp-dict

**微软拼音增强词库**

融合白霜拼音（Rime-Frost）、雾凇拼音（Rime-Ice）、中文维基百科与萌娘百科的
Windows 10/11 微软拼音 `mschxudp` 词库，下载即用。

<!-- TAGLINE:START -->
<p><strong>223万+</strong> 条有效词条 · 三档可选 · 每月自动更新</p>
<!-- TAGLINE:END -->

### 📥 [下载最新词库](https://github.com/arbaleast/msp-dict/releases/latest)

[快速开始](#快速开始) · [报告 Bug](https://github.com/arbaleast/msp-dict/issues/new?template=bug_report.yml) · [数据源问题](https://github.com/arbaleast/msp-dict/issues/new?template=data_source.yml) · [提出建议](https://github.com/arbaleast/msp-dict/issues/new?template=feature_request.yml)

</div>

---

<details>
<summary>目录</summary>
<ol>

<li><a href="#关于项目">关于项目</a></li>
<li><a href="#版本选择">版本选择</a></li>
<li><a href="#数据来源">数据来源</a></li>
<li><a href="#快速开始">快速开始</a></li>
<li><a href="#导入步骤">导入步骤</a></li>
<li><a href="#命令行清理与重置">命令行清理与重置</a></li>
<li><a href="#本地构建与用法">本地构建与用法</a></li>
<li><a href="#参与贡献">参与贡献</a></li>
<li><a href="#致谢">致谢</a></li>

</ol>
</details>

---

## 关于项目

Windows 自带的微软拼音打不出新词、流行语、专业名词和 ACG 角色名。
本项目把多个公开词库合并、清洗后，写成微软拼音「用户定义的短语」能直接导入的
`mschxudp` 二进制文件，导入后即可正常打出这些词。

仓库同时提供两个命令行工具：

| 工具 | 作用 |
|---|---|
| `python -m src.cli validate <file.dat>` | 校验词库二进制结构与词条内容是否符合微软拼音要求 |
| `python -m src.cli check-canary <file.dat> --manifest <file.json>` | 核对探针词库与 manifest 是否一致，分结构、探针、清单、实机四维输出 |

<p align="right">(<a href="#readme-top">返回顶部</a>)</p>

---

## 版本选择

按**需求与词汇覆盖面**划分四档，按需下载：

<!-- STATS:START -->
| 文件 | 词条数 | 大小 | 适用场景 |
|:---|---:|---:|:---|
| **msp_lite.dat** | 199,580 | ~9 MB | 日常高频主力档，日常使用首选 |
| msp_standard.dat | 793,861 | ~41 MB | 专业与百科扩充档，覆盖面更广 |
| msp_full.dat | 2,238,515 | ~118 MB | 全量归档档，用于存档 / 转其他输入法 |
| msp_win10.dat | 199,580 | ~9 MB | 兼容副本（= msp_lite.dat） |
<!-- STATS:END -->

<p align="right">(<a href="#readme-top">返回顶部</a>)</p>

---

## 数据来源

| 来源 | 提供什么 |
|---|---|
| [Rime-Frost（白霜拼音）](https://github.com/gaboolic/rime-frost) | 基础词库 + 20 多个领域词库（美食、成语、医药、计算机、地名、姓名等） |
| [Rime-Ice（雾凇拼音）](https://github.com/iDvel/rime-ice) | 基础词库 |
| [mw2fcitx](https://github.com/outloudvi/mw2fcitx) | 萌娘百科词条（ACG / 二次元） |
| [fcitx5-pinyin-zhwiki](https://github.com/felixonmars/fcitx5-pinyin-zhwiki) | 中文维基百科实体与专有名词 |
| 搜狗输入法细胞词库 | 网络流行新词、计算机、医药、财经等垂直领域词库（`.scel`，需自行下载） |

技术栈：Python 3.9+ 标准库为核心，`requests` 为唯一基础依赖。

<p align="right">(<a href="#readme-top">返回顶部</a>)</p>

---

## 快速开始

**不用写代码，也不用装 Python，下载即用。**

1. 打开 [Releases 页面](https://github.com/arbaleast/msp-dict/releases/latest)，下载 `msp_lite.dat`
2. 按下面的[导入步骤](#导入步骤)导入微软拼音
3. 打开记事本盲打 `cikutanzhen`，出现「词库探针已生效」即导入成功

<p align="right">(<a href="#readme-top">返回顶部</a>)</p>

### 导入步骤

> [!WARNING]
> 别点 **「导入自学习词汇」**。那个按钮要的是另一种格式（`ChsPinyinUDL`，文件头 `55AA8881`），
> 选本项目的 `.dat` 必然报「文件格式错误或文件已损坏」。
> 必须用 **「添加或编辑自定义短语」** 弹窗里的 **导入**。

**Windows 11**

设置 → 时间和语言 → 语言和区域 → 中文(简体，中国) `…` → 语言选项 → 微软拼音 `…`
→ 键盘选项 → 词库和自学习 → **添加或编辑自定义短语** → **导入**

**Windows 10**

设置 → 时间和语言 → 语言 → 中文(简体) 选项 → 微软拼音 选项 → 词库和自学习
→ **添加或编辑自定义短语** → **导入**

下载后先核对文件没被改坏：

```bash
sha256sum msp_lite.dat                    # Linux / macOS
certutil -hashfile msp_lite.dat SHA256    # Windows
head -c 8 msp_lite.dat                    # 应输出 mschxudp
```

导入失败的其他排查见 [导入失败诊断](docs/ISSUE3_DIAGNOSIS.md)。

<p align="right">(<a href="#readme-top">返回顶部</a>)</p>

### 命令行清理与重置

「用户定义的短语」页面打不开、一直转圈时，可以绕过界面直接用命令行清理。
这不是词库文件坏了：设置页会把全部短语一次性做成 UI 列表，「清除」按钮又在这个页面里，
所以进得去才发现点不动。打字本身不受影响，删掉短语库文件即可恢复。
下面的命令会**删除你导入的词库文件**，其中包含你自己添加的自定义短语与输入法自学习数据，
**先备份再执行**。

```bat
REM 1) 先备份（管理员 CMD / PowerShell）
mkdir "%USERPROFILE%\Desktop\msp-backup"
xcopy "%APPDATA%\Microsoft\InputMethod\Chs" "%USERPROFILE%\Desktop\msp-backup\Chs-roaming" /E /I /H
xcopy "%LOCALAPPDATA%\Microsoft\InputMethod\Chs" "%USERPROFILE%\Desktop\msp-backup\Chs" /E /I /H

REM 2) 关掉占用文件的进程
taskkill /F /IM SystemSettings.exe
taskkill /F /IM TextInputHost.exe
taskkill /F /IM ctfmon.exe

REM 3) 删除自定义短语库（在 Roaming 下，不是 Local）
del "%APPDATA%\Microsoft\InputMethod\Chs\ChsPinyinEUDPv1.lex"

REM 4) 注销重登后再导入 msp_lite.dat
```

> [!IMPORTANT]
> 只删 `Chs` 目录里的词库文件，**不要删除整个 `InputMethod` 目录**。
> 完整的逐文件处理表、回滚方法与自学习数据的影响说明见 [卡死恢复流程](docs/RECOVERY.md)。

<p align="right">(<a href="#readme-top">返回顶部</a>)</p>

---

## 本地构建与用法

### 环境安装

```bash
git clone https://github.com/arbaleast/msp-dict.git
cd msp-dict

pip install -e ".[test]"        # 测试与核心命令行
pip install -e ".[crawler]"      # 额外装 pypinyin / python-dotenv，用于爬虫采集
```

### 完整构建流水线

```bash
python scripts/download_frost.py --retries 5     # 下载源词库到 .cache/（约 140MB，不入库）
python scripts/merge.py                          # 合并清洗 -> .tmp/msp_full.txt
python scripts/build_releases.py                 # 生成三档 .dat 到 .tmp/dist/ 与 build_summary.json
python -m src.cli validate .tmp/dist/msp_lite.dat   # 校验产物
```

脚本的完整参数说明见 [开发与构建指南](docs/DEVELOPMENT.md)。

### 导入、导出与采集

文本词库为 TSV，**拼音是必填项**，缺失或非法的拼音会被拦截并计入 `errors`：

```bash
python -m src.cli import msp_lite.dat words.txt   # words.txt: 词条<TAB>拼音<TAB>词频
python -m src.cli export msp_lite.dat -f csv -o words.csv
python -m crawler.cli update --all --mspinyin .tmp/my_words.dat
```

`crawler.cli update` 会抓取网络热词并用 `pypinyin` 自动补拼音；补不出来的词写入
`unresolved.txt`，**空拼音不会进入词库**。

### Canary 探针

`--with-canary` 会在词库首尾注入两个诊断词条并生成 manifest，用来确认 Windows
到底有没有加载成功、尾部有没有被截断：

```bash
python scripts/build_releases.py --input .tmp/msp_full.txt --profiles lite --with-canary
python -m src.cli check-canary .tmp/dist/msp_lite_canary.dat --manifest .tmp/dist/msp_lite_canary.json
```

探针原理、四维输出与实机闭环步骤见 [Canary 探针测试](docs/CANARY_TESTING.md)。

<p align="right">(<a href="#readme-top">返回顶部</a>)</p>

---

## 参与贡献

1. Fork 本仓库并创建分支（`git checkout -b feature/xxx`）
2. 安装开发环境：`pip install -e ".[test]"`
3. 提交前跑一遍测试：`pytest -q`
4. 提交 Pull Request，说明改动动机与验证方式

改动 `.dat` 二进制格式或候选序号语义时，请在 PR 里写清「旧行为 → 新行为」及原因。

<p align="right">(<a href="#readme-top">返回顶部</a>)</p>

---

## 致谢

- [Rime](https://github.com/rime) —— 输入法引擎与词库协议
- [Rime-Frost](https://github.com/gaboolic/rime-frost) / [Rime-Ice](https://github.com/iDvel/rime-ice) —— 基础词库
- [mw2fcitx](https://github.com/outloudvi/mw2fcitx) / [fcitx5-pinyin-zhwiki](https://github.com/felixonmars/fcitx5-pinyin-zhwiki) —— 百科词库
- [imewlconverter](https://github.com/studyzy/imewlconverter) —— `mschxudp` 格式参考与真实样本

词库内容遵循上游 Rime 词库协议。

<p align="right">(<a href="#readme-top">返回顶部</a>)</p>

---

<!-- BUILD_DATE: 2026-11-18 -->

⭐ **喜欢这个项目？给个 Star 吧！**
