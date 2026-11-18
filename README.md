# 🎯 微软拼音增强词库

> 让你的输入法更懂你——223万+ 条有效词条，三档可选，每月自动更新

[![Biweekly Build](https://github.com/arbaleast/msp-dict/actions/workflows/biweekly-build.yml/badge.svg)](https://github.com/arbaleast/msp-dict/actions)
[![Release](https://img.shields.io/github/v/release/arbaleast/msp-dict?color=blue)](https://github.com/arbaleast/msp-dict/releases/latest)
[![词条数](https://img.shields.io/badge/词条-223万+-blue)](https://github.com/arbaleast/msp-dict/releases)

Windows 自带的微软拼音打不出新词、流行语、专业名词和 ACG 角色名。
这个项目把白霜、雾凇、维基百科、萌娘百科等公开词库整理成微软拼音能直接导入的文件，
装进「用户定义的短语」之后就能正常打出来了。

---

## ⚡ 极速上手

**不用写代码，也不用装 Python，下载即用。**

1. 打开 [Releases 页面](https://github.com/arbaleast/msp-dict/releases/latest)，下载 **`msp_lite.dat`**（约 855 KB）
2. 打开导入窗口：
   - **Windows 11**：设置 → 时间和语言 → 语言和区域 → 中文(简体，中国) `…` → 语言选项 → 微软拼音 `…` → 键盘选项 → 词库和自学习 → **添加或编辑自定义短语**
   - **Windows 10**：设置 → 时间和语言 → 语言 → 中文(简体) 选项 → 微软拼音 选项 → 词库和自学习 → **添加或编辑自定义短语**
3. 在弹出的独立窗口点 **导入**，选择刚下载的 `msp_lite.dat`，完成

想核对下载的文件没被改坏：

```bash
sha256sum msp_lite.dat                    # Linux / macOS
certutil -hashfile msp_lite.dat SHA256    # Windows
```

---

## 📦 版本选择

> [!IMPORTANT]
> 微软拼音打开「用户定义的短语」时会**一次性加载全部词条**。
> 超过 5 万条就会转圈卡死，连「清除」都点不动。**日常使用只用 `msp_lite.dat` 就够了。**

<!-- STATS:START -->
| 文件 | 词条数 | 大小 | 适用场景 |
|:---|---:|---:|:---|
| **msp_lite.dat** | 19,988 | 855 KB | Windows 10/11 直接导入（推荐） |
| msp_standard.dat | 48,986 | ~2 MB | 进阶用户；管理页会明显卡顿 |
| msp_full.dat | 2,238,515 | ~118 MB | 存档 / 转 Rime 等，Windows 无法完整导入 |
| msp_win10.dat | 19,988 | 855 KB | 兼容旧链接（= msp_lite.dat） |
<!-- STATS:END -->

| 文件 | 什么时候用 |
|---|---|
| `msp_lite.dat` | **默认选这个。** 约 2 万条高频词与核心专有名词，导入后设置页不卡 |
| `msp_standard.dat` | 想要更全的覆盖，愿意忍受设置页卡顿 |
| `msp_full.dat` | 只用来存档，或转成 Rime / 小狼毫格式。**不要导入微软拼音** |
| `msp_win10.dat` | 旧教程里的文件名，内容和 `msp_lite.dat` 完全一样 |

---

## 🚑 常见问题

### 导入时提示「文件格式错误或文件已损坏」

> [!WARNING]
> 别点 **「导入自学习词汇」**。那个按钮要的是另一种格式（`ChsPinyinUDL`，文件头 `55AA8881`），
> 选本项目的 `.dat` 必然报这个错。
> 必须用 **「添加或编辑自定义短语」** 弹窗里的 **导入**。

如果确实是弹窗里的导入也报错，先检查文件是不是下成了网页：

```bash
head -c 8 msp_lite.dat      # 正常应输出 mschxudp
```

详细排查见 [导入失败诊断](docs/ISSUE3_DIAGNOSIS.md)。

### 设置页一直转圈、卡死、点不动

说明词条太多，界面加载不过来。完整的抢救步骤（含**备份**与回滚）见
**[docs/RECOVERY.md](docs/RECOVERY.md)** —— 动手前务必先看，那一步会删数据。

### 怎么确认词库真的生效了

记事本盲打 `cikutanzhen`，出现「词库探针已生效」就说明头部加载成功；
再打 `zuiweitan`，出现「词库尾部已生效」说明尾部也没被截断。
探针词库怎么生成、四维校验怎么看，见 [docs/CANARY_TESTING.md](docs/CANARY_TESTING.md)。

---

## 🛠️ 进阶与开发

- [本地运行与词库构建指南](docs/DEVELOPMENT.md) —— 环境安装、三档构建、脚本参数
- [爬虫采集指南](docs/DEVELOPMENT.md#爬虫) —— 抓网络热词并自动补拼音
- [mschxudp 二进制格式规范](docs/DEVELOPMENT.md#格式规范) —— 字段布局与约束
- [卡死恢复流程](docs/RECOVERY.md) —— 备份、清库、回滚
- [Canary 探针测试](docs/CANARY_TESTING.md) —— 验证 Windows 是否真的加载

---

## 📚 数据来源与致谢

词库来自这些公开项目，本项目只做合并、清洗与格式转换：

| 来源 | 提供什么 |
|---|---|
| [Rime-Frost（白霜拼音）](https://github.com/gaboolic/rime-frost) | 基础词库 + 20 多个领域词库（美食、成语、医药、计算机、地名、姓名等） |
| [Rime-Ice（雾凇拼音）](https://github.com/iDvel/rime-ice) | 基础词库 |
| [中文维基百科](https://github.com/felixonmars/fcitx5-pinyin-zhwiki) | 百科实体与专有名词 |
| [萌娘百科](https://github.com/outloudvi/mw2fcitx) | ACG / 二次元词条 |

感谢 [Rime](https://github.com/rime) 输入法引擎与
[imewlconverter](https://github.com/studyzy/imewlconverter) 提供的格式参考与真实样本。
词库内容遵循上游 Rime 词库协议。

> 扩展源（维基/萌娘）在 `msp_lite.dat` 中占约 12%，不会挤掉日常高频词；
> 同一拼音下基础词始终优先当第 1 候选。

---

<!-- BUILD_DATE: 2026-11-18 -->

⭐ **喜欢这个项目？给个 Star 吧！**
