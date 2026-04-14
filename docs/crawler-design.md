# MSPinyin 词库爬虫设计方案

## 概述

为 mspinyin-dict 项目新增热词爬虫子系统，从 GitHub Trending、维基百科、B站热词三个数据源自动抓取新词，定期更新微软拼音用户词库。

## 数据源

| 数据源 | 抓取内容 | 优先级 |
|--------|----------|--------|
| GitHub Trending | Python/Go/JS 项目名、库名 | P0 |
| 维基百科 | 中文词条标题（按访问量排序） | P0 |
| B站弹幕热词 | 弹幕高频词、梗 | P1 |

## 架构

```
mspinyin-dict/
├── src/                    # 现有词库管理代码
├── crawler/                # 爬虫子系统 [新增]
│   ├── __init__.py
│   ├── cli.py              # 爬虫CLI入口
│   ├── fetchers/           # 数据源抓取器
│   │   ├── __init__.py
│   │   ├── github.py       # GitHub Trending
│   │   ├── wikipedia.py    # 维基百科
│   │   └── bilibili.py     # B站热词
│   ├── pipeline.py         # 去重/过滤/合并
│   └── schedule.py         # 定时任务
└── docs/
    └── crawler-design.md
```

## 数据源详情

### GitHub Trending

- **URL**: `https://github.com/trending?since=monthly`
- **方法**: curl 抓取 HTML
- **提取**: 项目名（英文转中文或保留英文）
- **过滤**: 跳过非项目名内容
- **示例**: `llama.cpp` → `llama.cpp` / `Qwen` → `Qwen`

### 维基百科

- **URL**: `https://zh.wikipedia.org/w/api.php?action=query&list=mostvisited&mpnsoffset=0&format=json`
- **方法**: curl + JSON API
- **提取**: 词条标题（中文）
- **过滤**: 纯英文词条跳过

### B站热词

- **方案A**: B站开放API（若有）
- **方案B**: 抓取排行榜页面
- **提取**: 弹幕高频词、弹幕梗
- **限制**: B站反爬严格，优先使用公开页面

## 处理流程

```
1. fetchers 并行抓取三个数据源
       ↓
2. 各数据源返回 List[str]（原始词条）
       ↓
3. pipeline 去重/合并
       ↓
4. 过滤规则:
   - 长度: 1-20字符
   - 字符: 主要包含中文字符
   - 去重: 与现有词库对比，已存在跳过
       ↓
5. 输出 clean_words.txt
       ↓
6. 调用现有 importer.py 导入
```

## CLI 接口

```bash
# 手动运行一次
python -m crawler.cli fetch        # 抓取新词
python -m crawler.cli update       # 抓取 + 导入
python -m crawler.cli stats        # 显示数据源统计

# 定时任务配置
python -m crawler.schedule setup  # 配置每周cron
```

## 定时任务

- **频率**: 每周一次（用户指定）
- **执行时间**: 每周一 03:00
- **交付方式**: 自动导入到用户词库文件
- **Cron job prompt**: 包含数据源路径和导入逻辑

## 依赖

- Python 3.8+
- 仅使用标准库 + curl（无第三方爬虫库）
- 网络请求走已有代理配置（localhost:7893）

## 已知限制

1. **B站**: 反爬严格，可能需要 User-Agent 轮换或限速
2. **GitHub**: 抓取英文项目名，中文翻译需用户补充
3. **维基百科**: 纯学术词条可能较多，需过滤

## Out of Scope

- 微博/知乎热榜（用户选择跳过）
- 实时热词监控
- 用户交互式选词
- 多线程加速（数据量小，单线程足够）

## 风险

1. B站反爬导致抓取失败 → 记录日志，跳过该数据源
2. GitHub 页面结构变化 → 定期检查正则表达式
3. 维基百科 API 限流 → 加延时 + 重试

## 验证步骤

1. `curl` 各数据源，确认能获取数据
2. 单独运行各 fetcher，确认输出正确
3. pipeline 去重/过滤逻辑单元测试
4. 端到端: 抓取 → 过滤 → 生成 clean_words.txt
5. 调用 importer.py 导入到测试词库文件
