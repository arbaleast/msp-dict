# 🎯 微软拼音增强词库

> 让你的输入法更懂你——200万+ 词条，半月自动更新，开箱即用

[![Daily Build](https://github.com/arbaleast/msp-dict/actions/workflows/biweekly-build.yml/badge.svg)](https://github.com/arbaleast/msp-dict/actions)
[![Release](https://img.shields.io/github/v/release/arbaleast/msp-dict?color=blue)](https://github.com/arbaleast/msp-dict/releases/latest)
[![词条数](https://img.shields.io/badge/词条-200万+-blue)](https://github.com/arbaleast/msp-dict/releases)

---

## ✨ 特性一览

| 🚀 超大海量词库 | 🔄 半月自动更新 | 📦 多版本可选 | 🎯 即插即用 |
|:---:|:---:|:---:|:---:|
| 200万+ 词条 | 每月 1/15 日构建 | 完整/标准/高频 | 下载即用 |

---

## 📥 快速下载

### ⭐ 推荐版本（Windows 10/11 直接导入）

| 📄 文件 | 📊 词条数 | 📝 说明 | 📏 大小 |
|:---|:---:|:---|---:|
| [**msp_win10.dat**](https://github.com/arbaleast/msp-dict/releases/latest) ⭐ | ~27万 | **Win10 DAT 推荐下载** | - |

> [!TIP]
> 直接导入 Windows 微软拼音，无需任何配置！

### 📚 其他版本

| 📄 文件 | 📝 说明 | 📏 大小 |
|:---|:---|---:|
| [msp_full.dat](https://github.com/arbaleast/msp-dict/releases/latest) | 完整版（最全） | ~67 MB |
| [msp_freq10.dat](https://github.com/arbaleast/msp-dict/releases/latest) | 词频 ≥ 10 | - |
| [msp_freq50.dat](https://github.com/arbaleast/msp-dict/releases/latest) | 词频 ≥ 50 | - |
| [msp_freq100.dat](https://github.com/arbaleast/msp-dict/releases/latest) | 词频 ≥ 100 | - |
| [msp_freq500.dat](https://github.com/arbaleast/msp-dict/releases/latest) | 词频 ≥ 500 | - |

> [!NOTE]
> 点击 Release 页面 **Assets** 展开下载所有版本

---

## 🚀 快速上手

### Windows 10/11 导入 DAT 文件

1. 下载 `msp_win10.dat`
2. 打开 **设置** → **时间和语言** → **语言和区域**
3. 找到 **微软拼音** → **词典** → **导入词典**
4. 选择下载的 `msp_win10.dat` 文件

> [!TIP]
> 💡 导入后无需重启，立即生效！

---

## 📊 词库格式

### Win10 DAT (推荐) ✅

```
mschxudp 二进制格式
├── Header: 64 字节
├── 词条偏移表
└── 词条数据 (UTF-16LE)
```

### TXT 格式

```
词语    拼音    词频
人工智能    zhong ren gong neng    31450
机器学习    ji qi xue xi    20106
神经网络    shen jing wang luo    15620
深度学习    shen du xue xi    7020
```

---

## 📚 数据来源

### Rime-Ice（雾凇拼音）

| 文件 | 说明 |
|:---|:---|
| base.dict.yaml | 基础词库 |
| ext.dict.yaml | 扩展词库 |
| tencent.dict.yaml | 腾讯词库 |
| 8105.dict.yaml | 8105 常用字 |
| others.dict.yaml | 其他词库 |

### Rime-Frost（白霜拼音）

| 文件 | 说明 |
|:---|:---|
| base / ext / 8105 / others | 基础词库 |
| food / idiom / history | 美食 / 成语 / 历史 |
| medication / computer / sport | 医药 / 计算机 / 体育 |
| geography / exthot / game | 地理 / 热搜 / 游戏 |
| music / media / animal | 音乐 / 媒体 / 动物 |
| chess / composite / industry_product | 棋类 / 复合 / 工业 |
| inputmethod / literature / name | 输入法 / 文学 / 姓名 |
| name2 / place / shulihua | 姓名2 / 地名 / 数量词 |
| luna_pinyin | 朙月拼音 |

---

## ⚙️ 自动化流程

每月 **1 日和 15 日 03:30 UTC** (北京时间 **11:30**) 自动运行：

```
✅ 下载 rime-ice + rime-frost 最新词库（30+ 个文件）
✅ 合并去重，保留最高词频
✅ 生成 5 个版本的 DAT 文件
✅ 更新 README 统计信息
✅ 创建新 release（格式：v1.2-YYYY.MM.DD）
```

---

## 📁 项目结构

```
msp-dict/
├── .github/workflows/
│   ├── biweekly-build.yml     # 半月自动构建
│   └── weekly-build.yml       # 周构建（可选）
├── src/
│   ├── parser.py              # mschxudp 格式解析器
│   ├── builder_win10.py       # Win10 DAT 格式构建器
│   ├── converter.py          # 格式转换器
│   ├── editor.py              # 词库编辑器
│   ├── exporter.py            # 导出器
│   ├── importer.py            # 导入器
│   └── cli.py                 # 命令行入口
├── crawler/
│   ├── pipeline.py           # 词条处理管道
│   ├── schedule.py           # 定时任务
│   ├── scel_downloader.py    # 搜狗词库下载器
│   ├── scel_parser.py         # scel 格式解析器
│   └── fetchers/              # 词库采集器
├── scripts/
│   └── update_readme.py      # CI 自动更新 README 统计
├── tests/                     # 单元测试
└── README.md
```

---

## 🛠️ 本地构建

```bash
# 克隆项目
git clone https://github.com/arbaleast/msp-dict.git
cd msp-dict

# 安装依赖
pip install requests

# 构建词库
python -m src.cli build -i cache/rime-ice_base.txt -o output.dat

# 解析现有词库
python -m src.parser your_dict.dat
```

---

<!-- BUILD_DATE: 2026-05-26 -->

⭐ **喜欢这个项目？给个 Star 吧！**

## 🙏 致谢

基于以下优秀项目构建：

- [Rime](https://github.com/rime) - 中州韵输入法引擎
- [Rime-Ice](https://github.com/iDvel/rime-ice) - 雾凇拼音
- [Rime-Frost](https://github.com/gaboolic/rime-frost) - 白霜拼音
- [imewlconverter](https://github.com/studyzy/imewlconverter) - mschxudp 格式参考

---

## 📄 License

遵循上游 Rime 词库协议。
