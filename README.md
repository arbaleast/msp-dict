# 🎯 微软拼音增强词库

> 让你的输入法更懂你——101万+ 条有效词条，三档可选，半月自动更新

[![Biweekly Build](https://github.com/arbaleast/msp-dict/actions/workflows/biweekly-build.yml/badge.svg)](https://github.com/arbaleast/msp-dict/actions)
[![Release](https://img.shields.io/github/v/release/arbaleast/msp-dict?color=blue)](https://github.com/arbaleast/msp-dict/releases/latest)
[![词条数](https://img.shields.io/badge/词条-101万+-blue)](https://github.com/arbaleast/msp-dict/releases)

---

## ⚠️ 先读这一段：微软拼音不适合「越大越好」

Windows 10/11 的微软拼音在打开 **设置 → 用户自定义短语** 时会一次性加载全部词条来构建列表：

| 词条规模 | 实际表现 |
|---:|---|
| ≤ 2 万 | 正常，管理页响应流畅 |
| 2 万 ~ 5 万 | 管理页明显卡顿；参考实现（深蓝词库转换）超过 2 万条会直接截断 |
| 5 万 ~ 10 万+ | 列表转圈/假死，甚至无法点击「清除」 |

因此本项目不再推荐单一的「超大完整版」，而是发布三档：

<!-- STATS:START -->
| 文件 | 词条数 | 大小 | 适用场景 |
|:---|---:|---:|:---|
| **msp_lite.dat** | 19,992 | 869 KB | Windows 10/11 直接导入（推荐） |
| msp_standard.dat | 49,199 | ~2 MB | 进阶用户；管理页会明显卡顿 |
| msp_full.dat | 1,013,978 | ~52 MB | 存档 / 转 Rime 等，Windows 无法完整导入 |
| msp_win10.dat | 19,992 | 869 KB | 兼容旧链接（= msp_lite.dat） |
<!-- STATS:END -->

> [!IMPORTANT]
> 直接导入请选 **`msp_lite.dat`**（或旧的 `msp_win10.dat`，内容相同）。
> `msp_standard.dat` / `msp_full.dat` 超过 Windows 管理界面的舒适区，导入后可能卡死且无法清除，
> 只建议存档或配合深蓝词库转换器转到 Rime / 小狼毫等输入法。

---

## 📥 快速下载

[**前往最新 Release 下载**](https://github.com/arbaleast/msp-dict/releases/latest) — Assets 中展开即可看到全部文件。

---

## 🚀 快速上手（Windows 10/11）

1. 下载 `msp_lite.dat`
2. 打开 **设置** → **时间和语言** → **语言和区域** → 中文(简体) 的 **语言选项**
3. 找到 **微软拼音** → **词典** / **用户自定义短语** → **导入**
4. 选择 `msp_lite.dat`

> [!TIP]
> 导入后无需重启。若提示「文件格式错误或文件已损坏」，请先用下面的 `validate`
> 命令确认文件本身是否合法（Release 产物在发布前都会跑一遍校验）。

### 出问题先自检

```bash
python -m src.cli validate msp_lite.dat
```

校验器会把问题分成四类，而不是笼统的「格式错误」：

- **文件格式错误**：签名/协议头/版本不对（根本不是 mschxudp）
- **文件已损坏**：截断、偏移表越界/非递增、UTF-16LE 未对齐、分隔符缺失
- **候选位置/内容违规**：候选序号不在 1~9、拼音非法、词条超长、重复词条
- **Windows 容量警告**：词条数超过 2 万 / 5 万，导入会失败或让管理页假死

退出码：`0` 通过（可能含警告）、`2` 格式错误、`3` 文件损坏、`4` 内容违规。

---

## 📊 词库格式

### Win10 DAT（mschxudp）

```
Header: 64 字节（mschxudp + 版本 + 偏移表位置 + 词条数 + 时间戳）
词条偏移表: 4 字节 × 词条数
词条记录: magic | hanzi_offset | 候选序号(1~9) | 0x06 | 0 | 2000纪元秒
          | 拼音 UTF-16LE | 0x0000 | 词条 UTF-16LE | 0x0000
```

- 拼音只允许小写 `a-z`（与音节分隔符 `'`），最多 32 个 UTF-16 单元
- 词条最多 64 个 UTF-16 单元
- 候选序号是「同一拼音下的第几个候选」，从 1 起、最多 9

### TXT（源数据）

```
词语    拼音    词频
人工智能    zhong ren gong neng    31450
机器学习    ji qi xue xi    20106
```

---

## 📚 数据来源

### Rime-Ice（雾凇拼音）

| 文件 | 说明 |
|:---|:---|
| base.dict.yaml | 基础词库 |
| ext.dict.yaml | 扩展词库 |
| tencent.dict.yaml | 腾讯词频表（仅词频，无拼音，无法写入 DAT，会剔除） |
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
| chess / chess2 / composite / industry_product | 棋类 / 复合 / 工业 |
| inputmethod / literature / name / name2 | 输入法 / 文学 / 姓名 |
| place / shulihua / luna_pinyin | 地名 / 数量词 / 朙月拼音 |

---

## ⚙️ 自动化流程

每月 **1 日和 15 日 03:30 UTC**（北京时间 **11:30**）自动运行：

```
✅ 下载 rime-ice + rime-frost 最新词库（30+ 个文件）
✅ 合并去重，保留最高词频；剔除无拼音的纯词频表
✅ 构建 lite / standard / full 三档 DAT，并生成 msp_win10.dat 兼容副本
✅ 对每个产物运行 validate，校验失败则阻断发布
✅ 更新 README 统计信息，创建新 release（格式：v2026.11.17）
```

---

## 📁 项目结构

```
msp-dict/
├── .github/workflows/
│   └── biweekly-build.yml     # 半月自动构建
├── src/
│   ├── format_spec.py         # mschxudp 规范常量与字段校验（唯一事实来源）
│   ├── parser.py              # mschxudp 解析器（支持 strict 模式）
│   ├── builder_win10.py       # Win10 DAT 构建器（清洗 + 候选序号 + 时间戳）
│   ├── validator.py           # 四类问题分类校验器
│   ├── profiles.py            # lite / standard / full 三档策略
│   ├── converter.py           # 格式转换器
│   ├── editor.py              # 词库编辑器
│   ├── exporter.py            # 导出器
│   ├── importer.py            # 导入器
│   └── cli.py                 # 命令行入口
├── crawler/                   # 词条采集（可选）
├── scripts/
│   ├── merge.py               # 合并 Rime 源 -> msp_full.txt
│   ├── build_releases.py      # 三档 DAT + 兼容副本 + 构建摘要
│   ├── make_scale_samples.py  # 1w/3w/5w/10w 梯度测试包
│   └── update_readme.py       # CI 自动更新 README 统计
├── tests/                     # 单元测试（pytest）
└── README.md
```

---

## 🛠️ 本地构建

```bash
git clone https://github.com/arbaleast/msp-dict.git
cd msp-dict
pip install pytest          # 构建本身只用标准库

# 1) 合并已有缓存词库 -> msp_full.txt
python scripts/merge.py

# 2) 三档构建（含 msp_win10.dat 兼容副本与 build_summary.json）
python scripts/build_releases.py --input msp_full.txt

# 3) 校验
python -m src.cli validate msp_lite.dat

# 单文件构建（自定义筛选）
python -m src.cli build cache/rime-ice_base.txt -o output.dat --profile lite
python -m src.cli build msp_full.txt -o output.dat --profile standard --limit 40000

# 测试
python -m pytest tests -q
```

---

## 🩺 Issue #3 修复说明

此前版本导入失败/卡死的三个独立原因（详见 [docs/ISSUE3_DIAGNOSIS.md](docs/ISSUE3_DIAGNOSIS.md)）：

1. **候选序号写成了词频 `rank & 0xFF`**：95% 的记录候选位是 0 或 >9，Windows 拒绝导入；
   现在按「同一拼音内 1~9」重新编号。
2. **无拼音词条（腾讯纯词频表）被写成 0 长度编码记录**：完整版里占 47%，Windows 解析即失败；
   现在合并阶段剔除。
3. **词库规模远超 Windows 上限**：旧推荐档约 27 万条，设置页必然假死；
   现在默认发布 ≤2 万条的 `msp_lite.dat`。

---

<!-- BUILD_DATE: 2026-11-17 -->

⭐ **喜欢这个项目？给个 Star 吧！**

## 🙏 致谢

- [Rime](https://github.com/rime) - 中州韵输入法引擎
- [Rime-Ice](https://github.com/iDvel/rime-ice) - 雾凇拼音
- [Rime-Frost](https://github.com/gaboolic/rime-frost) - 白霜拼音
- [imewlconverter](https://github.com/studyzy/imewlconverter) - mschxudp 格式参考

---

## 📄 License

遵循上游 Rime 词库协议。
