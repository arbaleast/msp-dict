# scripts/：词库合并与三档发布

## 数据流

```
cache/rime-*.txt（CI 下载，或本地 scripts/download_frost.py）
        │  scripts/merge.py
        ▼
msp_full.txt（有拼音、词频≥1，按词频降序）
        │  scripts/build_releases.py
        ▼
msp_lite.dat / msp_standard.dat / msp_full.dat / msp_win10.dat
+ build_summary.json（词条数、大小、清洗统计、校验结果）
        │  scripts/update_readme.py
        ▼
README.md 的 <!-- STATS:START --> 区块 + BUILD_DATE
```

## 脚本契约

| 脚本 | 输入 | 输出 | 关键约束 |
|---|---|---|---|
| `download_frost.py` | rime-ice / rime-frost 上游 | `cache/rime-*.txt` | 清单与 CI 一致；`cache/` 不入库，新克隆必须先跑 |
| `merge.py` | `cache/rime-*.txt` | `msp_full.txt`、`CHANGELOG.md` | 缺源文件直接失败（不产出残缺词库）；无拼音/词频<1 的词条剔除并计数；同词保留最高词频 |
| `build_releases.py` | `msp_full.txt` | 4 个 DAT + `build_summary.json` | 逐档 validate，非 0 退出阻断；`msp_win10.dat` 必须是 lite 的字节副本 |
| `make_scale_samples.py` | `msp_full.txt` | `scale_samples/` | 仅用于复现规模卡顿，不随 Release 发布 |
| `update_readme.py` | `build_summary.json` | README 统计块 | 无数据时不得瞎改；统计块标记必须保留 |
| `build_releases.py --with-canary` | `msp_full.txt` | `msp_<profile>_canary.dat` + `.json` | 独立产物，绝不覆盖正式 DAT；需有词条上限的档位 |

## 档位参数（`src/profiles.py`，改这里即改发布策略）

| 档位 | 上限 | 单字 | 词条长度 | 用途 |
|---|---:|---|---:|---|
| lite | 20,000 | 剔除 | ≤8 单元 | Windows 默认导入 |
| standard | 50,000 | 保留 | ≤16 单元 | 进阶用户 |
| full | 不限 | 保留 | ≤64 单元 | 存档/转 Rime |

## CI（`.github/workflows/`）

- `test.yml`：push/PR 触发，ubuntu-latest + windows-latest 矩阵跑 `pytest tests`。
- `biweekly-build.yml`：每月 1/15 日 03:30 UTC，也可 `workflow_dispatch` 手动触发。
  顺序：测试 → 下载源 → merge → build → validate → **upload-artifact** → 更新 README → 提交 → 创建 Release。
- 发布资产固定为 4 个 DAT；Actions artifact 保留 30 天，Release 永久。
- 工作流只提交 `README.md` 与 `CHANGELOG.md`，禁止 `git add` 被 gitignore 的产物。

## Pre-dev 检查清单

1. 改档位参数：同时看 `README.md` 的适用场景表与 `tests/test_releases.py`。
2. 改合并口径：样本数必须写进提交说明，并同步 `docs/ISSUE3_DIAGNOSIS.md` 的统计。
3. 改 CI：先本地按同样顺序跑一遍（可指向 `.tmp/work/merged` 的文本），确认 exit code。
4. 新增产物：加入 `build_releases.py` 的 summary、upload-artifact 与 Release 资产列表，并更新 README。

## 质量门

- 本地演练：`python scripts/download_frost.py && python scripts/merge.py && python scripts/build_releases.py && python -m src.cli validate msp_lite.dat`。
- `scripts/` 只保留这 5 个正式脚本；一次性排障脚本不进仓库。
- 产物名、词条数、体积与 README 统计块一致（允许 CI 自动刷新后略有差异）。
- 工作流 YAML 可被 `yaml.safe_load` 解析；步骤失败必须让 job 失败，不得 `|| true` 吞掉。
