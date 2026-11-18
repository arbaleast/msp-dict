# Canary 探针测试指南

> 目标：回答一个静态校验无法回答的问题——**`.dat` 真的被微软拼音加载了吗？**
> 相关实现：`src/canary.py`、`src/cli.py check-canary`、`src/validator.py CanaryChecker`

## 为什么需要探针

Windows 的「用户自定义短语」导入有三种结局，而前两种在 Python 侧看起来完全一样：

| 结局 | Python `validate` | Windows 表现 |
|---|---|---|
| 导入成功且生效 | 通过 | 打字能出候选 |
| 导入成功但被静默截断 | 通过 | 只有前一部分词生效 |
| 导入被拒绝 | 通过（文件本身合法） | 弹「文件格式错误或已损坏」 |

Canary 构建把两条**可辨识的探针**写进词库的首尾区域，导入后在记事本里盲打探针拼音：

- 两条都能打出来 → 头尾都加载成功；
- 只能打出靠前那条 → 尾部被静默截断；
- 两条都打不出来 → 词库没生效（入口选错或导入被忽略）。

## 默认探针

探针刻意使用**合法的汉语拼音音节组合**（如 `cikutanzhen` 可切分为 `ci ku tan zhen`），
避免 `mspdicttest` 这类非拼音串被微软拼音的全拼切分器忽略，造成假阴性。

| 探针 | 拼音 | 候选词 | 词条数位置 |
|---|---|---|---|
| 全拼探针 | `cikutanzhen` | 词库探针已生效 | 拼音字典序靠前（约第 2,000 条） |
| 尾部探针 | `zuiweitan` | 词库尾部已生效 | 拼音字典序靠后（约第 19,800 条） |

两条探针的源词频设为极大值，保证在 `frequency` 模式下候选位为 1。

## 生成 Canary 产物

正式产物（`msp_lite.dat` 等）**永远不含探针**。Canary 是独立文件，不会覆盖正式产物。

```bash
# 方式一：发布脚本（同时生成 msp_lite_canary.dat + msp_lite_canary.json）
python scripts/build_releases.py --input .tmp/msp_full.txt --profiles lite --with-canary

# 只生成 Canary，不重新构建正式三档（CI 用这个，更快）
python scripts/build_releases.py --input .tmp/msp_full.txt --profiles lite \
  --with-canary --canary-only --summary build_summary_canary.json

# 方式二：单文件构建
python -m src.cli build .tmp/msp_full.txt -o .tmp/msp_lite_canary.dat \
  --profile lite --with-canary --manifest .tmp/msp_lite_canary.json
```

自定义探针（`--canary-pinyin` 与 `--canary-word` 必须成对、可重复）：

```bash
python -m src.cli build .tmp/msp_full.txt -o .tmp/probe.dat --profile lite --with-canary \
  --canary-pinyin cikutanzhen --canary-word 词库探针已生效 \
  --canary-pinyin zuiweitan  --canary-word 词库尾部已生效
```

## Manifest

构建完成后会回读最终二进制，按真实物理位置写 manifest：

```json
{
  "format": "msp-dict-canary-manifest/1",
  "profile": "lite",
  "sha256": "afb164c79faeb5ae07ff522f559da44af46a6c3169357be1330e7148c9afadfa",
  "file_size": 890328,
  "normal_entry_count": 19990,
  "canary_entry_count": 2,
  "total_entry_count": 19992,
  "probes": [
    {"pinyin": "cikutanzhen", "word": "词库探针已生效", "rank": 1,
     "physical_index": 2049, "byte_offset": 162540},
    {"pinyin": "zuiweitan", "word": "词库尾部已生效", "rank": 1,
     "physical_index": 19851, "byte_offset": 884666}
  ]
}
```

- `physical_index`：零基 Offset Table 索引，即文件中的第几条记录；
- `byte_offset`：该记录在文件中的绝对起始字节（`phrase_start + offset`）；
- `rank`：**最终候选位**（1~9），不是源词频。

## 四维检查

```bash
python -m src.cli check-canary msp_lite_canary.dat --manifest msp_lite_canary.json
```

输出固定四个维度，互不替代：

| 维度 | 检查内容 | 失败含义 |
|---|---|---|
| `[STRUCT]` | DAT 二进制结构与 Offset Table | 文件本身损坏 |
| `[CANARY]` | 探针是否物理存在，拼音/词条/候选位/偏移是否与 manifest 一致 | 探针被丢弃或位置漂移 |
| `[MANIFEST]` | SHA-256 与词条计数 | 文件被改动或计数不符 |
| `[WINDOWS]` | 微软拼音实际加载 | **永远是 PENDING**，只能实机验证 |

`[STRUCT]`/`[CANARY]`/`[MANIFEST]` 全绿而 `[WINDOWS]` 仍是 `PENDING` 时，退出码为 0——
这只代表「文件侧没问题」，**不代表 Windows 已加载**。

## Windows 实测闭环

1. 把 `msp_lite_canary.dat` 导入「用户自定义短语」：
   设置 → 时间和语言 → 语言和区域 → 中文(简体，中国) … → 语言选项 →
   微软拼音 … → 键盘选项 → 词库和自学习 → **添加或编辑自定义短语** → 导入。
2. 打开记事本，盲打 `cikutanzhen`，应出现「词库探针已生效」；
   再盲打 `zuiweitan`，应出现「词库尾部已生效」。
3. 回到同一页面点 **导出**，得到 Windows 写回的 `.dat`，再跑一次：

   ```bash
   python -m src.cli check-canary <导出的.dat> --manifest msp_lite_canary.json
   ```

   探针仍在、词条数不减少 = Windows 没有静默截断。

### 结果解读

| 现象 | 结论 | 下一步 |
|---|---|---|
| 两条探针都出候选 | 头尾都加载成功 | 正常，可放心使用 `msp_lite.dat` |
| 只有 `cikutanzhen` 出候选 | 尾部被静默截断 | 降低词条数（`--limit 10000`）后重试 |
| 两条都不出 | 词库未生效 | 确认走的是「添加或编辑自定义短语 → 导入」，不是「导入自学习词汇」 |
| 导出文件里探针缺失 | Windows 已丢弃 | 同上，按截断处理 |

## 边界与限制

- 探针依赖「同拼音按词频排序」的 `frequency` 模式；`--rank-mode position` 不做 Canary。
- `full` 档没有词条上限，不生成 Canary；Canary 只针对 `lite` / `standard`。
- 探针词条会计入 profile 上限（先给普通词条预留 `limit - 探针数` 个名额），
  因此 Canary 总量不会突破档位上限。
- Canary 构建同样走完整清洗与序列化路径，探针不会被去重逻辑误删（有单元测试守护）。

## CI 中的位置

`.github/workflows/biweekly-build.yml` 在正式三档构建后：

1. `build_releases.py --with-canary --canary-only` 生成 canary；
2. `check-canary` 检查，非 0 退出即阻断发布；
3. 四个正式 DAT + canary DAT/JSON + 构建摘要一起作为 Actions artifact 上传；
4. Release 附件同样包含 `msp_lite_canary.dat` 与 `msp_lite_canary.json`。

`[WINDOWS]` 维度在 CI 中**不会**变绿——这是设计使然，Windows 加载状态只能由人工在真机确认。
