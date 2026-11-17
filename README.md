# 🎯 微软拼音增强词库

> 让你的输入法更懂你——101万+ 条有效词条，三档可选，半月自动更新

[![Biweekly Build](https://github.com/arbaleast/msp-dict/actions/workflows/biweekly-build.yml/badge.svg)](https://github.com/arbaleast/msp-dict/actions)
[![Release](https://img.shields.io/github/v/release/arbaleast/msp-dict?color=blue)](https://github.com/arbaleast/msp-dict/releases/latest)
[![词条数](https://img.shields.io/badge/词条-101万+-blue)](https://github.com/arbaleast/msp-dict/releases)

---

## 📖 项目简介

本项目将 [Rime-Frost（白霜拼音）](https://github.com/gaboolic/rime-frost) 与 [Rime-Ice（雾凇拼音）](https://github.com/iDvel/rime-ice) 合并、清洗、重排后，生成 Windows 10/11 微软拼音「用户定义的短语」可直接导入的 `mschxudp` 二进制词库。

同时内置两项核心诊断工具：
- **二进制强校验器 (`validate`)**：精确区分格式错误、文件损坏、内容违规与容量超限。
- **Canary 探针诊断 (`check-canary`)**：注入首尾探针，通过记事本盲打与导出回环确认 Windows 是否真实加载且无静默截断。

---

## 📦 下载与版本选择

前往 [最新 Release](https://github.com/arbaleast/msp-dict/releases/latest) 下载。**日常使用只需下载 `msp_lite.dat`。**

<!-- STATS:START -->
| 文件 | 词条数 | 大小 | 适用场景 |
|:---|---:|---:|:---|
| **msp_lite.dat** | 19,992 | 869 KB | Windows 10/11 直接导入（推荐） |
| msp_standard.dat | 49,202 | ~2 MB | 进阶用户；管理页会明显卡顿 |
| msp_full.dat | 1,015,471 | ~52 MB | 存档 / 转 Rime 等，Windows 无法完整导入 |
| msp_win10.dat | 19,992 | 869 KB | 兼容旧链接（= msp_lite.dat） |
<!-- STATS:END -->

> [!IMPORTANT]
> **为什么默认推荐 `msp_lite.dat`？**
> 微软拼音打开「用户定义的短语」设置页时会**一次性加载全部词条**构建列表：≤ 2 万条流畅；2~5 万条明显卡顿；超过 5 万条会导致设置页转圈假死甚至无法点击「清除」。`msp_lite.dat` 已剔除冗余单字与低价值长句，精选高频词与核心专有名词。

---

## 🚀 导入步骤（Windows 10 / 11）

### Windows 11
1. **设置** → **时间和语言** → **语言和区域**
2. 中文(简体，中国) 右侧 **…** → **语言选项**
3. 微软拼音 右侧 **…** → **键盘选项** → **词库和自学习**
4. 在「用户定义的短语」一栏，打开开关并点击 **添加或编辑自定义短语**（弹出独立窗口）
5. 在独立窗口点击 **导入** → 选择 `msp_lite.dat`

### Windows 10
1. **设置** → **时间和语言** → **语言** → 中文(简体，中国) → **选项**
2. 微软拼音 → **选项** → **词库和自学习**
3. 在「用户定义的短语」下打开开关 → **添加或编辑自定义短语** → **导入** → 选择 `msp_lite.dat`

> [!WARNING]
> **切勿点错入口！** 同页面的 **「导入自学习词汇」** 按钮使用的是另一套私有格式（`ChsPinyinUDL`，文件头 `55AA8881`），不接受本项目的 `mschxudp` 文件，点击必报「文件格式错误或文件已损坏」。请务必进入 **「添加或编辑自定义短语」** 窗口点击导入。

### 提示「文件格式错误或文件已损坏」排查

1. **确认未下载成 HTML 网页**：`head -c 8 msp_lite.dat` 应输出 `mschxudp`。
2. **运行内置校验器预检**：
   ```bash
   python -m src.cli validate msp_lite.dat
