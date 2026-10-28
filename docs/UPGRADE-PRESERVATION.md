# 升级与回滚保留验证

## v0.1.4 → v0.1.5 → v0.1.4

2026-10-28，Windows本地候选及PR、合入、标签CI通过。基线 `a77ed089de3031cbefdbd235608b6631a95d3e40`，发布目标 `b1c1bd1bcdba05ec50ec5e33a83797c90ec5751f`。
测试.env字节/ACL、工作区、旧任务索引、receipt/checkpoint与成功产物保留。已完成任务可查询，pending receipt沿原身份恢复；三阶段假供应商提交总数均为2，没有重复提交或真实收费请求。
临时安装已清理。运行 `uv run --no-sync python scripts/verify_upgrade.py --candidate v0.1.5 --baseline v0.1.4` 复现，先获取v0.1.1至v0.1.5标签。
源码/wheel隔离安装后也验证初始化失败可见blocked/phase、同一run_id可以恢复，详见[发布记录](releases/v0.1.5.md)。不覆盖实际消费Host或任意未来版本降级。

## v0.1.3 → v0.1.4 → v0.1.3

2026-10-28，Windows本地候选及PR、合入、标签CI均通过。v0.1.3基线为
`f437164d10a8a7dd7fd21bd85ee1deccf7b4533e`，v0.1.4发布目标为
`a77ed089de3031cbefdbd235608b6631a95d3e40`。
隔离测试保留.env字节/ACL、工作区文件/ACL、原任务索引及产物；已完成任务可查询，pending receipt沿原任务恢复。
三阶段假供应商提交总数均为2，没有重提；真实供应商请求为0。临时安装由finally清理。
运行 `uv run --no-sync python scripts/verify_upgrade.py --candidate v0.1.4 --baseline v0.1.3`，
须先获取v0.1.1、v0.1.2、v0.1.3、v0.1.4标签；报告在.cache/validation，不能在成员真实安装目录执行。
发布附件隔离安装和CI链接见[实际发布记录](releases/v0.1.4.md)。不覆盖实际Host跨账号权限切换或任意未来版本降级。

## v0.1.1 → v0.1.2 → v0.1.1 历史验证

2026-10-28，Windows、Python 3.12，普通离线测试凭据与假供应商；网络仅用于Git/锁定依赖安装。
本地结果通过，真实供应商请求为0。实际Host产品、跨提升权限账号切换未验证。

| 阶段 | 精确源码目标 | 验证 |
|---|---|---|
| 原版 | c85f396c559411a68bdd5a2cba4bbbe858ab3245 | 无开发依赖安装，固定工作区stdio发现8工具；准备已完成及待完成两种任务 |
| 升级 | 036ef5e3246ce32f23ddd8138284fc1d18f357ed | 同目录切换并锁定安装，任务模式stdio发现9工具；import_run/get_run读取两条旧任务 |
| 回滚 | c85f396c559411a68bdd5a2cba4bbbe858ab3245 | 同目录重新锁定安装，恢复固定workspace及thread_id，stdio发现8工具并可查询原任务 |

在每次Git切换及uv安装前后，对测试.env、业务目录所有文件逐一比较SHA256和Windows安全描述符
（Owner/Group/DACL），包括SQLite/checkpoint及原产物；升级后创建的任务索引在回滚时也保留。
旧文件不覆盖，目录不迁移。这里验证原文件权限保留，不代表备份副本自动继承完全相同ACL。

假供应商在原版完成一张图，第二条任务在查询时中断，留下已提交编号。
升级后的图工作流从checkpoint续查并下载，回滚后的重放仍复用记录；总共仅两次假提交，
后两个阶段的submit入口一旦被调用就失败。原已完成产物哈希和ACL始终保持。
MCP的导入与查询通过实际SDK子进程验证；工作流续查使用进程内替身注入，未宣称真实供应商恢复成功。

复现：在开发仓库获取两个正式标签且安装开发依赖后，执行
`uv run --no-sync python scripts/verify_upgrade.py`。脚本从当前Git对象库创建无共享对象的干净副本，
先核对标签完整SHA，再依次安装；不读取维护者真实.env或修改Host。
所有生成环境放在仓库.cache下，成功或失败均清理，仅保留脱敏报告：

- `.cache/validation/upgrade-preservation.json`
- `.cache/validation/upgrade-preservation-log.json`

Windows CI增加同一检查并随原有evidence artifact归档；CI结果以相应PR/合入提交的运行记录为准。
脚本和报告说明属于发布后的维护补充，不回写或覆盖v0.1.2标签及附件。
验证范围限这两个正式版本的既有已完成/待完成任务，不保证未来schema、所有新增修订或任意降级组合。

## v0.1.3交付补充

2026-10-28已对v0.1.2→发布目标f437164d10a8a7dd7fd21bd85ee1deccf7b4533e→v0.1.2通过相同保留验证；Windows PR/合入及标签CI均执行。
`uv run --no-sync python scripts/verify_upgrade.py --candidate v0.1.3`可在维护副本复现，须先获取v0.1.2/v0.1.3标签。
测试.env内容/ACL、旧已完成及待完成任务、业务文件、原产物和索引保留，沿原task_id恢复而不重复POST。
不承诺v0.1.3新建null选项任务或新修订可由旧版执行；回滚保留新增数据，必要时升回恢复。
实际CI、附件和安装结果见[发布记录](releases/v0.1.3.md)。
