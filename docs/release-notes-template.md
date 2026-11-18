## {{TAG}}

| 文件 | 词条数 | 大小 | 用途 |
|:---|---:|---:|:---|
{{TABLE}}

### 安装（Windows 11）

设置 → 时间和语言 → 语言和区域 → 中文(简体，中国) `…` → 语言选项 → 微软拼音 `…` → 键盘选项 → 词库和自学习 → **添加或编辑自定义短语** → 导入。

Windows 10：设置 → 时间和语言 → 语言 → 中文(简体) 选项 → 微软拼音 选项 → 词库和自学习。

> ⚠️ 不要点「导入自学习词汇」，那是另一种格式（`55AA8881`），不接受本项目的 mschxudp 文件。

### 完整性校验

`SHA256SUMS` 包含四个产物的 SHA-256：`sha256sum -c SHA256SUMS`（Windows 用 `certutil -hashfile` 逐个核对）。

### 数据来源

Rime-Frost（白霜拼音）、Rime-Ice（雾凇拼音）为主，萌娘百科 / 中文维基 / 搜狗细胞词库按档位配额融合。

### 诊断

Canary 探针词库不随 Release 发布（正式产物零探针）；可从最近一次 Actions 构建的 artifact 获取，
或运行 `python scripts/build_releases.py --input msp_full.txt --profiles lite --with-canary` 本地生成。

---

历史版本存在候选位越界与超大词库问题（Issue #3），已移除；本页仅保留最近 3 个版本。
