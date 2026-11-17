# msp-dict Agent 入口

> 作用域：本仓库。本文件是**路由**，不是规则仓库——规则正文在 `.trellis/spec/`，长文在 `docs/`。
> 首次接触先读 `README.md`（项目定位、三档产物、Windows 导入限制）。

## 核心原则

- **先读再改**：动 `src/`、`scripts/`、`tests/` 前先读对应分片；格式类问题先看诊断报告。
- **二进制向后兼容**：`mschxudp` 头部与记录布局不可随手改；任何字段/语义变更必须同步 parser、validator 与测试。
- **证据驱动**：修复先用真实词库扫描或测试复现，禁止凭猜测改代码。
- **Windows 默认只导入 lite**：管理界面在 2 万条以上开始卡顿，`msp_full.dat` 仅供存档/转其他输入法。

## 按需读取（路由表）

| 任务 | 先读 | 时机 |
|---|---|---|
| 改构建器 / 解析器 / 编辑器 / 校验器 | `.trellis/spec/src/index.md` | 动手前 |
| 改合并 / 三档构建 / CI 发布 | `.trellis/spec/scripts/index.md` | 动手前 |
| 新增或修改测试 | `.trellis/spec/tests/index.md` | 动手前 |
| 提交信息、命名、错误处理 | `.trellis/spec/guides/conventions.md` | 提交前 |
| 不确定读什么 | `.trellis/spec/guides/index.md` | 入口 |
| 排查导入失败 / 格式根因 | `docs/ISSUE3_DIAGNOSIS.md` | 处理 Issue #3 类问题 |
| 验证词库是否真被 Windows 加载 | `docs/CANARY_TESTING.md` | 跑探针 / 解读 check-canary |

## 常驻规则

- 测试：`python -m pytest tests -q`（CI 同一命令，ubuntu + windows 矩阵）。
- 校验：`python -m src.cli validate <file.dat>`；退出码 `0` 通过、`2` 格式错误、`3` 文件损坏、`4` 内容违规。
- Canary 诊断：`build --with-canary` 产出独立探针词库（正式产物零污染），
  `python -m src.cli check-canary <dat> --manifest <json>` 输出 `STRUCT/CANARY/MANIFEST/WINDOWS` 四维；
  `[WINDOWS]` 只能实机验证，Python 侧通过不代表 Windows 已加载。
- 不提交 `.dat`、`msp_*.txt`、`build_summary.json`、`scale_samples/`（均已在 `.gitignore`）。
- 产物落 `dist/`（发布）或 `.tmp/`（调试）；仓库根不落散文件。
- 改二进制语义或 CLI 行为时，提交说明必须写清「旧行为 → 新行为」及原因。
- 不手改 `.trellis/.runtime/`（会话状态）。

## 优先级

1. 用户当前明确指令
2. 本文件
3. `.trellis/spec/` 分片
4. `README.md` 与 `docs/`
