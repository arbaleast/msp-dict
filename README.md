# 微软拼音增强词库

基于 rime-ice + rime-frost + 热词爬虫合并转换的微软拼音自定义词典。

## 来源

- [iDvel/rime-ice](https://github.com/iDvel/rime-ice) - 雾凇拼音
- [gaboolic/rime-frost](https://github.com/gaboolic/rime-frost) - 白霜拼音
- GitHub Trending / 维基百科 / B站热词 - 热词爬虫

## 版本

| 文件 | 条目数 | 说明 |
|------|--------|------|
| `msp_full.txt` | ~1.7M | 完整版（词频≥1）|
| `msp_freq10.txt` | ~1.5M | 精简版（词频≥10）|
| `msp_freq50.txt` | ~1.5M | 标准版（词频≥50）|
| `msp_freq100.txt` | ~1.4M | 优质版（词频≥100）|
| `msp_freq500.txt` | ~200K | 高频版（词频≥500）|

## 格式

`词语\t词频`，可直接导入微软拼音。

导入路径：**设置 → 时间和语言 → 拼音设置 → 词典 → 添加词典**

## 热词爬虫

每周自动从以下数据源抓取新词：

- **GitHub Trending** - 高星项目名
- **维基百科** - 热门词条
- **B站排行榜** - 弹幕热词

```bash
# 抓取热词
python -m crawler.cli fetch --all -o new_words.txt

# 导入到词库
python -m src.cli import user_dict.dat new_words.txt

# 配置每周定时更新
python -m crawler.schedule setup --mspinyin user_dict.dat
```

## 词库管理工具

位于 `src/` 目录：

```bash
python -m src.cli parse <file.dat>      # 解析词库
python -m src.cli stats <file.dat>      # 显示统计
python -m src.cli export <file.dat> -o out.txt   # 导出
python -m src.cli add <file.dat> "词条"  # 添加词条
python -m src.cli remove <file.dat> "词条" # 删除词条
python -m src.cli import <file.dat> words.txt  # 批量导入
```

## 许可证

遵循上游词库协议。
