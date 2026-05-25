# MSPinyin Dict 项目

微软拼音用户自定义词库管理工具。

> ⚠️ **2026-05-23 重大更新**：废弃旧版 60 字节固定格式，全面迁移到 `mschxudp` 格式（Win10 微软拼音原生格式）。

---

## 目标

- 读取/解析微软拼音 `.dat` 词库格式（`mschxudp` 协议）
- 支持批量导入新词汇
- 支持导出为可编辑文本格式
- 支持添加/删除词条
- 支持从文本文件构建 `mschxudp` 格式词库

---

## 微软拼音 DAT 格式

### 说明

当前项目采用 `mschxudp` 格式，这是微软拼音 **Win10** 及更高版本的用户自定义词库格式。

旧版 `custom_phrase.dat` 的 60 字节固定格式已被验证为错误的，**不再使用**。

格式参考来源：

- [imewlconverter](https://github.com/studyzy/imewlconverter) [`Win10MsPinyin.cs`](https://github.com/studyzy/imewlconverter/blob/master/IMECollection/IME/Win10/Win10MsPinyin.cs)

### 文件结构

```
+0x000 - +0x03F: 文件头 (64 字节)
+0x040 - +0x040 + phrase_count * 4: 偏移表
+0x040 + phrase_count * 4 - ...: 词条数据区
```

### 文件头 (0x00-0x3F, 64 字节)

```
偏移    大小    说明
0x00    8      'mschxudp' 协议标识
0x08    4      固定值 0x00600002
0x0C    4      版本号 (通常为 1)
0x10    4      phrase_offset_start = 0x40 (偏移表起始)
0x14    4      phrase_start (词条数据起始偏移)
0x18    4      phrase_end (词条数据结束偏移)
0x1C    4      phrase_count (词条数量)
0x20    8      timestamp (Unix 时间戳)
0x28    24     保留字段 (全零)
```

### 词条结构

```
偏移    大小    说明
+0x00   4      magic 0x00100010
+0x04   2      hanzi_offset (汉字偏移 = 18 + pinyin_char_len * 2)
+0x06   1      rank (词频排名)
+0x07   1      固定值 0x06
+0x08   4      未知字段 0x00000000
+0x0C   4      固定魔数 0xE679CD20
+0x10   var    UTF-16LE 编码的拼音字符串
+var    2      null 分隔符 (0x0000)
+var+2  var    UTF-16LE 编码的汉字文本
+end    2      null 终止符 (0x0000)
```

### 词条解析算法

1. 验证文件头前 8 字节是否为 `mschxudp`
2. 从偏移 0x10 读取 `phrase_offset_start`
3. 从偏移 0x14 读取 `phrase_start`
4. 从偏移 0x1C 读取 `phrase_count`
5. 读取偏移表：从 `phrase_offset_start` 开始，每个词条 4 字节偏移量
6. 解析每个词条：
   - 按偏移表定位词条数据
   - 读取 `magic` 验证是否为 `0x00100010`
   - 读取 `hanzi_offset` 计算拼音长度
   - 提取拼音字符串和汉字文本

---

## 项目结构

```
mspinyin-dict/
├── README.md
├── plan.md
├── SPEC.md
├── docs/
│   ├── code-quality-analysis.md      # 源码质量评估报告
│   ├── fix-proposal.md               # 修复建议方案
│   └── crawler-design.md             # 爬虫设计文档
├── src/
│   ├── __init__.py                   # 包入口
│   ├── parser.py                     # mschxudp 格式解析 ✅
│   ├── editor.py                     # 词条添加/删除 (重建模式) ✅
│   ├── exporter.py                   # 导出工具 (TXT/CSV/JSON)
│   ├── importer.py                   # 批量导入 (TXT/CSV/Rime)
│   ├── converter.py                  # Rime ↔ 微软拼音互转
│   ├── builder_win10.py              # Win10 格式构建/解析 (参考实现)
│   ├── builder.py                    # (废弃) 旧版 60 字节格式
│   └── cli.py                        # CLI 工具入口
├── crawler/
│   ├── cli.py                        # 爬虫 CLI
│   ├── pipeline.py                   # 爬虫管道
│   ├── importer.py                   # 爬虫数据导入
│   └── fetchers/                     # 数据源抓取器
└── .github/
    └── workflows/
        └── weekly-build.yml          # 每日自动构建
```

---

## 功能列表

| 功能 | 状态 | 说明 |
|------|------|------|
| 解析 mschxudp 格式 | ✅ 已完成 | 支持完整解析 |
| 提取所有词条 | ✅ 已完成 | 含拼音和词频 |
| 导出 TXT/CSV/JSON | ✅ 已完成 | 多种格式支持 |
| 添加新词条 | ✅ 已完成 | 重建模式 |
| 删除词条 | ✅ 已完成 | 重建模式 |
| 批量导入 (TXT/CSV/Rime) | ✅ 已完成 | 自动格式检测 |
| Rime 格式互转 | ✅ 已完成 | 自动拼音补全 |
| 从文本构建词库 | ✅ 已完成 | 制表符分隔格式 |
| 词频更新 | ❌ 未实现 | 需要编辑后重新构建 |

---

## CLI 使用示例

```bash
# 解析词库
python -m src.cli parse custom_phrase.dat -v -l

# 导出词库
python -m src.cli export custom_phrase.dat -o dict.txt -f txt

# 添加词条
python -m src.cli add custom_phrase.dat "机器学习" -p jiqixuexi -r 1

# 删除词条
python -m src.cli remove custom_phrase.dat "旧词条"

# 从文本构建词库
python -m src.cli build words.txt -o custom_phrase.dat

# 批量导入
python -m src.cli import custom_phrase.dat rime_dict.txt

# 显示统计
python -m src.cli stats custom_phrase.dat

# 格式转换
python -m src.cli convert rime_dict.txt msp_dict.txt -f msp
```

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | — | 初始版本，60 字节固定格式 |
| v2.0 | 2026-05-23 | **全面迁移**：废弃 60 字节格式，统一使用 `mschxudp` 格式 |
