# 通用约定：提交、命名与错误处理

> 只写本仓库已成立、且跨模块复用的结论。格式细节在 `src/index.md`，测试细节在 `../tests/index.md`。

## 提交信息

| 范围 | 约定 |
|---|---|
| 类型 | Conventional Commits：`feat` / `fix` / `docs` / `refactor` / `test` / `chore` / `ci` |
| 语言 | subject 以中文为主，可带 scope（`fix(win10):`、`ci:`、`chore(trellis):`） |
| 粒度 | 一次提交只含一个主题；CI 自动提交为 `Daily build: YYYY-MM-DD` |
| 兼容性说明 | 改二进制语义/CLI 行为时，提交说明必须写清「旧行为 → 新行为」及原因 |

## 命名

- 模块按职责命名，单数、snake_case：`format_spec`、`builder_win10`、`validator`。
- 测试文件 `tests/test_<主题>.py`，测试类 `Test<主题>`，用例名描述行为而非实现。
- 脚本 `scripts/<动词>_<对象>.py`；新增脚本必须能 `python scripts/<name>.py --help`。
- 产物固定命名：`msp_lite.dat` / `msp_standard.dat` / `msp_full.dat` / `msp_win10.dat`。

## 错误与日志

- 库代码抛异常或返回统计，不 `print`；CLI 层负责面向用户的输出。
- 构建/导入的「被拦截词条」必须计数（`BuildStats.reasons`），禁止静默丢弃。
- 解析错误分两类：`format`（协议头不对）与 `corruption`（截断/越界/未对齐），不得混用。
- 校验器退出码：`0` 通过、`2` 格式错误、`3` 文件损坏、`4` 内容违规。

## 文件落点

- 构建/调试产物进 `.tmp/`（已 gitignore）；发布产物进 `dist/`（已 gitignore）。
- 不提交 `.dat`、`msp_*.txt`、`build_summary.json`、`scale_samples/`。
- 长文放 `docs/`，README 只保留用户需要的最短路径与统计块。
