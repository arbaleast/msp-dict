# MSPinyin Dict 项目

微软拼音用户自定义词库管理工具。

> 📖 **格式规格以 [`SPEC.md`](SPEC.md) 为准**。`plan.md` 为项目计划文档，不再包含格式描述。

---

## 目标

- 读取/解析微软拼音 `.dat` 词库格式（**`mschxudp` 格式** ✅）
- 支持批量导入新词汇
- 支持导出为可编辑文本格式
- 支持添加/删除词条

---

## 2026-05-23 重构

### 背景

旧版代码使用 60 字节固定格式的 `custom_phrase.dat` 格式，
该格式已被验证为错误的（详见 [`src/builder.py`](src/builder.py:4-6) 顶部的警告注释）。

### 变更

- 废弃 60 字节固定格式
- 全面迁移到 `mschxudp` 格式（Win10 微软拼音原生格式）
- 集成格式参考：imewlconverter Win10MsPinyin.cs

### 影响模块

| 模块 | 变更 |
|------|------|
| [`parser.py`](src/parser.py) | **重写**：从 60 字节格式→`mschxudp` 格式 |
| [`editor.py`](src/editor.py) | **重写**：基于新的 parser + 构建逻辑 |
| [`exporter.py`](src/exporter.py) | **适配**：使用新的 DictEntry（pinyin 字符串） |
| [`importer.py`](src/importer.py) | **适配**：使用新的 editor.add_entry(text, pinyin, rank) |
| [`converter.py`](src/converter.py) | **适配**：使用新的 DictEntry + 拼音映射表扩展 |
| [`cli.py`](src/cli.py) | **重写**：移除 sys.path hack，使用相对导入，新增 build 命令 |
| [`__init__.py`](src/__init__.py) | **更新**：导出符号对齐新接口 |
| [`builder.py`](src/builder.py) | **保留仅供研究**，不参与构建流程 |
| [`builder_win10.py`](src/builder_win10.py) | **保留为参考实现**，构建命令调用 Win10MSPinyinBuilder |

---

## 项目结构

```
mspinyin-dict/
├── README.md
├── plan.md                      # 项目计划
├── SPEC.md                      # 格式规格（权威文档）
├── docs/
│   ├── code-quality-analysis.md  # 源码质量评估
│   ├── fix-proposal.md           # 修复建议
│   └── crawler-design.md         # 爬虫设计
├── src/
│   ├── __init__.py
│   ├── parser.py                 # mschxudp 格式解析 ✅
│   ├── editor.py                 # 添加/删除词条
│   ├── exporter.py               # 导出 TXT/CSV/JSON
│   ├── importer.py               # 批量导入
│   ├── converter.py              # Rime ↔ 微软拼音互转
│   ├── builder.py                # (废弃) 旧格式
│   ├── builder_win10.py          # Win10 构建器参考
│   └── cli.py                    # CLI 入口
├── crawler/
│   ├── __init__.py
│   ├── cli.py
│   ├── pipeline.py
│   ├── importer.py
│   └── fetchers/
└── .github/
    └── workflows/
        └── weekly-build.yml
```

---

## 功能状态

| 功能 | 状态 | 备注 |
|------|------|------|
| 解析 mschxudp 格式 | ✅ 已完成 | 完整解析含拼音和词频 |
| 导出 (TXT/CSV/JSON) | ✅ 已完成 | 含拼音导出 |
| 添加词条 | ✅ 已完成 | 重建模式 |
| 删除词条 | ✅ 已完成 | 重建模式 |
| 批量导入 (TXT/CSV/Rime) | ✅ 已完成 | 自动格式检测 |
| Rime ↔ 微软拼音互转 | ✅ 已完成 | 自动拼音补全 |
| 从文本构建词库 | ✅ 已完成 | build 命令 |
| 词频更新 | ❌ 待实现 | 需要编辑后重新构建 |
| 拼音编码映射 | ⚠️ 部分 | 覆盖高频词汇，生僻字用 xx 占位 |

---

## TODO

- [ ] 实现词频更新功能
- [ ] 集成 pypinyin 库完善拼音映射
- [ ] 补充单元测试
- [ ] Web UI 界面
