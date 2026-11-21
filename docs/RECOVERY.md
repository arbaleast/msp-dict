# 管理界面转圈卡死：强制恢复

> **⚠️ 严重警告 / WARNING**
>
> 本文涉及**删除微软拼音的用户词库文件**。这些文件里存放着你的**自定义词条**和
> **输入法自学习数据**（你平时手动输入、修正过的词条都会被微软拼音记进去）。
> 直接删除 = **这些数据永久丢失，无法从任何地方找回**。
>
> **请先做完第 0 步的备份，再往下操作。**
>
> 同时请注意：
> - 只操作 `%APPDATA%\Microsoft\InputMethod\Chs`（Roaming，**自定义短语
>   `ChsPinyinEUDPv1.lex` 就在这里**）与 `%LOCALAPPDATA%\Microsoft\InputMethod\Chs`
>   （Local，自学习等文件）**这两个目录内的词库文件**；
> - **绝对不要删除整个 `InputMethod` 目录**，那会破坏输入法注册信息，可能导致系统
>   找不到微软拼音（表现为输入法无法唤起、需要重新安装语言包）；
> - 清理 `ChsPinyinUDL.dat` / `ChsPinyinEUDL.dat` 会**一并清空自学习词汇**，
>   这部分数据只能靠重新使用输入法慢慢积累；
> - 恢复完成后请重新导入 `msp_lite.dat`（20 万条），**不建议直接导入 `msp_full.dat`**
>   （223 万条）——不是文件有问题，而是设置页要把每条都做成列表项，
>   按 1.5 KB/条算会吃掉几 GB 内存，等于把刚恢复的页面重新拖死。

## 为什么进这个页面会卡死

不是词库文件坏了，也不是「超过某个条数上限」——微软从未公布自定义短语的数量上限。

真实原因是设置页的实现：

- 一进入「用户定义的短语」，页面就把 `ChsPinyinEUDPv1.lex` 里的**全部短语**
  一次性做成 UI 列表（无分页、无虚拟化、无上限），条数越多，加载越慢、内存越大；
  实测 600 万条约占 9 GB，十几分钟仍加载不出；
- 「清除」按钮就在这个页面里，必须先进来才能点，而一进来就开始全量加载 →
  于是**永远点不到清除**（逻辑死锁）。这就是「点了清除也卡死」的原因；
- **输入引擎不受影响**：导入后打字能正常出候选，只有设置页打不开。

所以恢复手段只有一条：**绕过界面，直接删 lex 文件**。

## 什么时候需要这套流程

- 导入词库后，设置 → 词库和自学习 → 用户定义的短语页面**一直转圈**；
- 列表加载不出来，或能看见但**点不动「清除」「编辑」**；
- 想把导入的词库整个删掉，但界面根本进不去。

## 第 0 步：必须先备份（不可跳过）

在 **管理员** PowerShell / CMD 里执行，把两个目录整个复制到桌面：

```bat
mkdir "%USERPROFILE%\Desktop\msp-backup"

REM 本机用户数据（自定义短语、自学习、删除候选记录等）
xcopy "%LOCALAPPDATA%\Microsoft\InputMethod\Chs" "%USERPROFILE%\Desktop\msp-backup\Chs" /E /I /H

REM 漫游配置（若存在）
xcopy "%APPDATA%\Microsoft\InputMethod\Chs" "%USERPROFILE%\Desktop\msp-backup\Chs-roaming" /E /I /H
```

备份完成后，确认桌面上出现 `msp-backup\Chs\` 目录且里面能看到 `ChsPinyin*.dat` / `ChsPinyin*.lex` 文件，再继续。

> **回滚方法**：如果清理后想找回原来的自定义词条，把备份里的 `ChsPinyinEUDPv1.lex`
> （自定义短语）与 `ChsPinyinEUDL.dat` / `ChsPinyinUDL.dat`（自学习）**原样拷回**
> `%APPDATA%\Microsoft\InputMethod\Chs\`（自定义短语）与
> `%LOCALAPPDATA%\Microsoft\InputMethod\Chs\`（自学习），然后注销重登即可。

## 第 1 步：结束占用进程

任务管理器 → **详细信息** 选项卡 → 结束：

- `SystemSettings.exe`（设置页，就是一直转圈的那个）
- `Windows 输入体验`（`TextInputHost.exe`）
- `ctfmon.exe`（输入法框架，系统会按需自动重启它）

命令行等价：

```bat
taskkill /f /im SystemSettings.exe
taskkill /f /im TextInputHost.exe
taskkill /f /im ctfmon.exe
```

## 第 2 步：清理异常词库文件

在 `%APPDATA%\Microsoft\InputMethod\Chs\` 与 `%LOCALAPPDATA%\Microsoft\InputMethod\Chs\`
中删除（或改名成 `.bak`）这些文件（**两处都要看**，以实际存在的为准）：

| 文件 | 内容 | 删掉的后果 |
|---|---|---|
| `ChsPinyinEUDPv1.lex` | **用户自定义短语**（你导入的词库，位于 `%APPDATA%`） | 导入的词库消失，需重新导入 |
| `ChsPinyinEUDL.dat` | 用户扩展自学习数据 | 自学习记录清空 |
| `ChsPinyinUDL.dat` | 自学习词汇库 | 自学习记录清空 |
| `ChsPinyinIH.dat` | 内部用户词条存储 | 清空 |
| `ChsPinyinDeletedCands.dat` | 删除候选记录 | 清空 |

如果提示文件被占用，说明进程还没退干净——**先注销登录再删**，不要强行结束系统关键进程。

## 第 3 步：注销并重新登录

让输入法服务重新加载空词库。重新打开设置页，列表应为空、可以正常操作。
确认没问题后再导入 `msp_lite.dat`。

## 附：只清理「某个词库」而不清空全部

如果你只想移除本项目导入的词库、保留自己手动添加的短语，可以只删除
`ChsPinyinEUDPv1.lex`——但注意这个文件里既有导入的词库也有你手动加的短语，
**无法按来源区分**。想保留手动词条时务必先做第 0 步备份。

## 相关文档

- [词库格式与导入入口排查](ISSUE3_DIAGNOSIS.md)
- [用探针确认词库是否真的生效](CANARY_TESTING.md)
