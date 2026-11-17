# src/：mschxudp 读写核心

## 模块职责（与文件一一对应）

| 文件 | 职责 | 不许做的事 |
|---|---|---|
| `format_spec.py` | 协议常量、UTF-16 单元数、拼音规范化、长度上限 | 不依赖其它 `src` 模块 |
| `builder_win10.py` | 清洗 → 去重 → 排序 → 分配候选位 → 序列化 | 不写文件、不打印，只回 `bytes` 与 `BuildStats` |
| `parser.py` | 读取/校验结构，`strict` 区分 `format`/`corruption` | 不在解析中修改数据 |
| `validator.py` | 四类问题分类报告与退出码；识别 55AA8881/55AA8880/DEL 容器并给出导入入口提示 | 不复用 builder 的写路径 |
| `editor.py` | 增删词条（哈希索引 O(1)）、保存重建 | 不在保存时改变同音候选顺序 |
| `importer.py` | TXT/CSV/Rime 批量导入、拼音规范化与拦截 | 不接收无拼音/非法拼音词条 |
| `profiles.py` | lite/standard/full 档位参数 | 不含具体词条数据 |
| `canary.py` | 诊断探针定义、探针物理定位（独立回读路径）、manifest 生成 | 不参与正式产物构建 |
| `cli.py` | 子命令编排与用户输出 | 不内联二进制逻辑 |
| `converter.py` / `exporter.py` | Rime 互转 / txt·csv·json 导出 | 不改写 DAT 协议 |

## mschxudp 红线（改任何一项都要同步 parser/validator/测试）

- 头部 64 字节：`mschxudp` | `0x00600002` | version 1 | 0x40 | `0x40+4N` | 文件大小 | N | Unix 秒；`0x24–0x3F` 必须为 0。
- 记录：magic `0x00100010` | `hanzi_offset = 18 + 拼音字节数` | **候选位 1~9** | `0x06` | 0 | 2000 纪元秒 | 拼音 UTF-16LE | `0x0000` | 词条 UTF-16LE | `0x0000`。
- 上限：拼音 ≤32 UTF-16 单元、词条 ≤64、同拼音候选 ≤9；参考实现导入上限 20,000 条。
- 长度一律用 `utf16_units()` / `encode('utf-16-le')` 的字节数，禁止用 `len(str)` 推算偏移。

## Canary 诊断构建（零污染）

- 正式产物（`msp_lite.dat` / `msp_standard.dat` / `msp_full.dat` / `msp_win10.dat`）**永远不含探针**；
  探针只出现在独立的 `msp_<profile>_canary.dat` + `msp_<profile>_canary.json`。
- 注入时机：普通词条筛选、去重、截断（`limit - canary_count`）**之后**，探针走与普通词条
  完全相同的序列化路径。
- 探针用超大源词频（`CANARY_SOURCE_RANK`）确保同拼音下拿到候选位 1；manifest 里记录的
  `rank` 是**最终候选位**。
- DAT 记录按拼音字典序物理排列，因此**必须回读二进制文件**确认探针的真实
  `physical_index` / `byte_offset`，不能拿内存插入顺序当证据（`canary.iter_physical_records`）。
- `check-canary` 输出四维：`STRUCT` / `CANARY` / `MANIFEST` / `WINDOWS`；
  `[WINDOWS]` 恒为「待实机验证」，Python 侧全绿**不等于** Windows 已加载。

## 词频与候选位（两种语义，不可混用）

- `rank_mode='frequency'`：输入是真实词频，构建器在同一拼音内按词频降序分配 1~9，超出计 `candidate_overflow` 丢弃。
- `rank_mode='position'`：输入已是 1~9 顺位，原样保留；非法值/重复位拦截。
- 编辑器的 `save()` 使用 position 模式，保证「打开旧词库再保存」不反转同音候选顺序。

## Pre-dev 检查清单（改 src/ 必读）

1. 先读 `format_spec.py`：要改的常量/上限是否已存在？优先复用。
2. 影响二进制布局的改动：同步 `parser` 的结构校验、`validator` 的错误分类、`tests/test_builder_format.py` 与 `tests/test_parser.py`。
3. 影响 CLI 的改动：保持既有子命令与参数可用（`parse/export/import/convert/add/remove/stats/build`），新增参数用可选默认值。
4. 新增清洗规则：必须在 `BuildStats.reasons` 计数，CLI 与 CI 能看到拦截数量。
5. 改 `editor`：索引与 `entries` 必须同步；`add/remove/save` 后 `find_by_text` 结果必须与列表一致。

## 质量门

- `python -m pytest tests -q` 全绿（含 20 万条导入性能用例）。
- 用真实词库构建三档后，`python -m src.cli validate` 全部 exit 0。
- 新建 DAT 的候选位分布只允许 1~9；`validate --json` 中不得出现 `error` 级 issue。
- 不提交任何 `.dat` 或 `msp_*.txt`。
