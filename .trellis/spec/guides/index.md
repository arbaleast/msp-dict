# msp-dict 工程规范索引

> 作用域：`msp-dict` 仓库。本目录是**门禁索引**，不是规则仓库——正文在 `guides/` 与各包目录，
> 这里只回答「动手前读什么、做完凭什么算完成」。

## 读取顺序（每次改动前）

| 顺序 | 读什么 | 为什么 |
|---|---|---|
| 1 | `README.md` | 项目定位、三档产物、Windows 导入限制 |
| 2 | 本文件 | 阅读路由与质量门 |
| 3 | `src/index.md` | 改 `src/` 前必读：mschxudp 红线与模块职责 |
| 4 | `scripts/index.md` | 改构建/发布链路前必读 |
| 5 | `tests/index.md` | 新增/修改测试前必读 |

## 按任务的最低阅读集

| 任务 | 必读 | 说明 |
|---|---|---|
| 改二进制格式 / 构建器 / 解析器 | `src/index.md` + `README.md` 的词库格式节 | 任何字段变更必须同步 parser/validator/测试 |
| 改三档构建 / CI 发布 | `scripts/index.md` + `.github/workflows/biweekly-build.yml` | 产物名与 README 统计块必须一致 |
| 改编辑器 / 批量导入 | `src/index.md` + `tests/index.md` | 索引与底层列表必须 100% 一致 |
| 写测试 | `tests/index.md` | 硬编码期望、强断言、先红后绿 |
| 改文档 | `README.md` + `docs/ISSUE3_DIAGNOSIS.md` | 数字以 `build_summary.json` / CI 实测为准 |

## 架构地图（与真实目录一一对应）

```
src/        核心库（mschxudp 读写与校验）
scripts/    词库合并、三档构建、规模样本、README 统计
tests/      pytest 套件（130+ 用例）
crawler/    可选词条采集（不参与发布主链路）
docs/       诊断报告等长文
.github/workflows/  test.yml（双平台测试）/ biweekly-build.yml（构建发布）
```

## 质量门（完成前逐条核对）

| # | 门 | 判定 |
|---|---|---|
| 1 | 二进制向后兼容 | `mschxudp` 头部与记录布局不变；新字段必须先加校验再落盘 |
| 2 | 测试跑过 | `python -m pytest tests -q` 全绿；失败先怀疑实现 |
| 3 | 产物可导入 | `python -m src.cli validate` 对 lite/standard/full/win10 均 exit 0 |
| 4 | 文档同步 | README 统计块与 `build_summary.json` 一致；格式变更写入 README/诊断文档 |
| 5 | 仓库干净 | `git status --short` 只含本次改动；`.dat`/`.txt` 产物不提交 |
