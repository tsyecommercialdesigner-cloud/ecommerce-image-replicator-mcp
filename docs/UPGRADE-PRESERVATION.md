# v0.1.1 → v0.1.2 → v0.1.1 保留验证

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
