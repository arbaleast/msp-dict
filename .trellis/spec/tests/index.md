# tests/：pytest 套件

## 入口

```bash
python -m pytest tests -q          # 全部用例（CI 使用同一命令）
python -m pytest tests/test_builder_format.py -q
```

全部用例都在 `tests/` 下，CI 与本地跑同一条命令。

## 写法规约（与工作区 `docs/testing-rules.md` 同源）

- 期望值写成字面量，禁止调用被测实现复算（如偏移、条数、字节长度）。
- 强断言：校验具体值/结构；`is not None` 仅在语义本就只有「存在性」时允许。
- 不 mock 被测单元：只允许 mock 网络/文件系统/时钟等外部依赖；本仓库测试默认使用真实临时文件。
- 先红后绿：修复/新行为必须先在没有修复的实现上看到失败。
- 不为了让 CI 变绿而删断言、放宽断言或 skip；行为口径确实变了（如按拼音排序、无拼音词条跳过）才允许改测试，并在提交说明写原因。

## 文件地图

| 文件 | 覆盖 |
|---|---|
| `test_builder_format.py` | 候选位 1~9、时间戳、UTF-16 代理对偏移、清洗与拦截、frequency/position 双模式、构建→解析闭环 |
| `test_parser.py` | 解析往返、strict 的 `format`/`corruption` 分类、偏移单调性 |
| `test_validator.py` | 四类问题、退出码、容量警告、空拼音/非法候选位 |
| `test_editor.py` / `test_editor_roundtrip.py` / `test_editor_performance.py` | 增删语义、索引一致性、保存顺序、20 万条 O(N) 基准 |
| `test_importer.py` | TXT/CSV/Rime 导入、非法/空拼音跳过 |
| `test_releases.py` | 三档构建、`msp_win10.dat` 字节副本、summary |
| `test_canary.py` | 正式产物 0 探针、探针物理定位与上限、四维检查拦截、确定性构建 |
| `tests/fixtures/` | 真实 Windows `mschxudp` 样本（入库），用于校验真实文件兼容性 |
| `test_cli_validate.py` | `validate` 子命令退出码与输出、`build --profile` |
| `test_merge.py` | 合并口径（无拼音/零词频剔除、最高词频优先） |
| `test_exporter.py` / `test_pipeline.py` / `test_cli.py` | 导出、端到端、CLI 参数面 |

## 测试环境注意

- 子进程用例统一 `encoding='utf-8'`、`env` 显式设置，避免 Windows 默认代码页解码失败。
- 临时文件用 `tmp_path`；不要写入仓库根目录。
- 真实样本放 `tests/fixtures/`（已入库），**禁止**让单测依赖 `.tmp/` 下的未跟踪文件。
- 性能用例的断言上限是防回归护栏（20 万导入 <10 s、5 万保存 <10 s），平台变慢时先复测再调整，不得直接删掉。

## 质量门

- `pytest tests -q` 全绿且用例数不减少（新增行为必须新增用例）。
- 新用例在修复前实现上确实失败（红），修复后通过（绿）。
- 测试不依赖网络、不依赖 `.cache/` 是否存在。
