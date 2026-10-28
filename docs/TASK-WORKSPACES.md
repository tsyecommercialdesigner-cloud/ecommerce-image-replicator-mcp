# 任务级工作区（v0.1.2）

此能力已包含在 v0.1.2 发布附件中，v0.1.1 尚不支持。安装根继续由 `--project-root` 指定，密钥仍按安装根
`.env` → 进程 → Windows 当前用户环境逐字段读取；业务目录不参与凭据查找。

## 启动与配置

当前源码的 `.mcp.json.example` 以及 MANUAL 第4节提供不带 `--workspace` 的本地 stdio 配置。
启动和能力发现无需业务目录；Agent 在准备任务时提供已存在的绝对路径。
不从 Host cwd、聊天名称或项目名称推断目录，也不默认写入 `D:\EcommerceImageReplicator`。

可选参数：

| 参数 | 作用 |
|---|---|
| `--workspace D:\EcommerceImageReplicator` | 旧固定模式；工具不能切换到其他目录 |
| `--allow-workspace-root D:\Projects` | 限制可选工作区到该目录及其子目录；可重复指定，每次恢复也重新检查 |
| `--state-dir D:\ReplicatorState` | 已存在的持久状态目录；默认是安装根，需运行账号可写 |

未设置允许根时，可以显式选择运行账号有权限访问的已有目录。工作区路径拒绝相对路径、
`..`、符号链接和 Windows junction。目录限制与任务绑定防止误路由，**不是多用户权限隔离**；
持有另一个项目 run_id 的同账号调用者仍可以访问它。不同信任主体应使用不同账号、实例和目录权限。

当前源码可不收费检查默认模式：

```powershell
uv --directory 'D:\MCP\ecommerce-image-replicator-mcp' run --no-sync python scripts/smoke.py --project-root 'D:\MCP\ecommerce-image-replicator-mcp'
if ($LASTEXITCODE -ne 0) { throw '协议检查失败' }
```

通过应发现9工具、1资源、1提示。`--workspace` 仍可用于检查固定模式。
这不代表实际 Claude/Codex 等 Host 联调或供应商真实调用已通过。

## Agent 调用顺序

先读 `replicator://input-contract` 或调用 `prepare_inputs` 提示，核对 workspace_mode、允许根和输入契约。
不强制用户编写 AGENTS.md / CLAUDE.md；可在项目指令中注明本项目的绝对路径与输入文件约定。
MCP 无法自行知道用户刚在 Host 中选中了哪个项目；Agent 必须提供正确目录。

1. 按契约在项目目录准备 `references/<group>/`、`products/`、`brief/` 和可选 `prompts/`。
2. `inspect_inputs({"workspace":"D:\\Projects\\ProductA"})` 获取权威图片顺序。可能初始化本地日志目录，无供应商调用。
3. `prepare_run({"workspace":"D:\\Projects\\ProductA","options":{}})` 冻结输入，保存返回的 `run_id`。
4. 获得绘图授权且启动预算已配置后，`execute_run({"run_id":"run_…"})` 执行或恢复。
5. `get_run({"run_id":"run_…"})` 查询；用返回的 `workspace` 拼接相对 `artifacts`，不要拼接 Agent 当前目录。

`get_design`、`record_review`、`reconcile_submission` 同样传 `run_id`，其余参数不变。
`prepare_revision` 传 `parent_run_id` 和 `updates`，子任务继承父任务工作区并返回新的 `run_id`、`parent_run_id`。
这些后续接口不接受 workspace 重定向。每次只传一种标识，不能同时给 run_id 和 thread_id。

不同项目使用各自的日志、checkpoint、输出和执行锁，可并行执行；同一工作区仍保留原来的单执行锁。
相同冻结输入在同一工作区得到稳定标识；不同工作区即使历史 thread_id 相同，也得到不同 run_id。
并发预算按各工作区执行配置计算，不是全实例共享总额度。

## 旧任务和重启恢复

旧固定配置不必修改：仍可用 `thread_id`、`parent_thread_id`；返回额外 run_id 和 workspace。
改成不带 `--workspace` 启动后，先调用：

```json
{"workspace":"D:\\EcommerceImageReplicator","thread_id":"已有任务的原始标识"}
```

将以上参数交给 `import_run`，保存返回 run_id。导入只绑定已有日志任务，不重建输入、不重新绘图。
不自动扫描磁盘或迁移旧目录。旧供应商任务编号、操作记录和 checkpoint 保留不变。

任务索引在 `<state-dir>/.replicator/task-registry.sqlite`；每个业务工作区的 `.replicator/` 保存
原始任务日志与 checkpoint，`artifacts/` 保存结果。更新或重启需保留索引和业务工作区，
保持 state-dir 一致；备份前停止服务，保留整个 `.replicator`（包括可能存在的 SQLite WAL 文件）。
不能只备份 run_id 或索引就恢复图片任务。索引丢失时，可用原目录和原 thread_id 重新 import_run。
目录移动后旧 run_id 不会自动跟随；本次不提供目录迁移功能。

重启不会自动启动收费流程；显式 execute_run 才恢复。已提交任务继续查询原 task_id；
结果未知仍阻止自动重提，按原流程核查后 reconcile_submission。恢复时目录、日志缺失或允许根
不再匹配会报错，不在另一个目录创建空任务冒充恢复成功。
