# ecommerce-image-replicator-mcp

基于 Python LangGraph 的电商竞品图复刻 MCP，通过本地 stdio 提供输入准备、生成、恢复、验收和单图修订。
原始竞品图决定构图、关键对象与互动关系；用户产品图与有来源的增量适配产品文案和品牌主题。
默认沿用参考图艺术风格，允许不改变主旨的小幅创意差异。未知提交不自动重复绘图。

## 发布状态

当前维护源码新增画布尺寸补偿及 `recover_postprocess`（尚未发布，共12工具）。小幅比例偏差先归一化到请求画布，再去补边并恢复原图精确宽高；已下载的v2失败图可沿原run_id纯本地恢复，无供应商请求。详见[尺寸恢复说明](docs/POSTPROCESS-RECOVERY.md)。下述v0.1.6发布记录及附件保持原样，该发布版没有此新入口。

[正式发布v0.1.6](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/releases/tag/v0.1.6)，2026-10-28 14:40（Asia/Shanghai），目标 `1459ebd0e4b63de6bc5a75e41458846f7e6dce83`。
新增逐图预检与显式分析恢复，共11工具。220通过/1项平台跳过，Windows/Linux PR、合入及标签CI通过；附件、源码/wheel安装、旧任务升级回滚及安装后保留7图的恢复准备检查通过，无真实收费请求。
详细证据见[发布记录](docs/releases/v0.1.6.md)。

## 任务级工作区

维护源码另增代理兼容（未发布）：默认 `--proxy-mode environment`，保留HTTP/HTTPS/ALL代理与NO_PROXY绕过规则，在本客户端兼容合法的方括号IPv6条目，不修改进程或用户环境。仅需直连时由操作者显式加 `--proxy-mode direct`，忽略代理但继续使用CA环境并校验证书；不自动降级直连。规则见[网络兼容说明](docs/NETWORK-COMPATIBILITY.md)。

消费端 Agent 从[使用手册](docs/guidebook-of-ecommerce-image-replicator-mcp.md)开始，按“阶段→诊断→修改位置→恢复入口”处理问题。可复制入口在[output-docs](output-docs/AGENTS.md)：AGENTS.md / CLAUDE.md / CONVENTIONS.md 均相对链接到随包交付的 docs 手册，复制时保留该目录。

v0.1.6新增 `preflight_run` 和 `prepare_analysis_recovery`（v0.1.5没有）：逐图预检文本替换、查看成功缓存及安全错误位置，并仅为未提交的失败图准备关联恢复任务。成功图和原任务保留，准备不执行；分析和绘图仍需单独授权execute。不要把分析失败交给需要已有成图的prepare_revision，也不要通过编辑磁盘文件假定旧冻结任务已更新。

启动不再必须传 `--workspace`。Agent 在 `inspect_inputs` / `prepare_run` 中提供当前项目的绝对目录，
后续以返回的 `run_id` 生成、查询、验收、修订与恢复。不同项目独立日志、checkpoint、输出和执行锁。
目录不会随Agent当前项目自动改变；Agent须明确提供目录。任务绑定用于同账号路由，不是多用户权限沙箱。

旧 `--workspace` 配置与 `thread_id` 继续兼容；任务模式通过 `import_run` 绑定已有任务。
升级保留安装根私有 `.env`、状态目录的 `.replicator`，以及各业务目录的 `.replicator` 和 `artifacts`；不自动迁移旧任务。
详见[任务级工作区](docs/TASK-WORKSPACES.md)及[使用手册](MANUAL.md)。

## 安装与使用

Windows建议PowerShell 7、Git、Python 3.12和uv 0.12.23，安装于 `D:\MCP\ecommerce-image-replicator-mcp`。
从本仓库取得v0.1.6标签，按[手册](MANUAL.md#2-项目初始化)核对完整SHA并执行 `uv sync --locked --no-dev`。
凭据固定读取安装根 `.env`，逐字段回退至进程及Windows用户环境；业务工作区不参与凭据查找。
密钥为 `ZHENZHEN_GEMINILLM_API_KEY` 和 `ZHENZHEN_GPTIMAGEGEN_API_KEY`。
已有用户级密钥时，不要创建含空密钥字段的 `.env`；空值会阻止环境变量回退。
日常启动使用 `uv run --no-sync`，不临时安装依赖；执行仍需用户授权及有效密钥，三项限制按下述策略处理。

**v0.1.3已将三项执行限制改为按需启用**：默认不限制，无需业务人员配置数值。
input-contract的execution_limit_policy为opt-in-v1时，batch_images、request_bytes、output_tokens的null分别表示未启用批次图数、请求字节、输出token限制；未设置token限制时省略上游max_tokens。
可独立通过--max-batch-images、--max-request-bytes、--max-output-tokens设置正整数；显式0或负数无效。调整后只重启当前Host/profile的MCP并读取资源复核，沿原run_id恢复。
已发布v0.1.2仍采用默认0且阻塞执行的旧策略，需要升级实际服务才能改变；标签和附件未修改。详见[限制策略与恢复](MANUAL.md#执行预算预检配置与原任务恢复)。
供应商上限、凭据、费用授权及其它运行边界仍生效。

业务目录包含 `references/<group>/`、`products/`、`brief/` 和可选 `prompts/`；产物在 `artifacts/`。
MCP配置见 [.mcp.json.example](.mcp.json.example)，四类Host完整JSON/TOML/YAML配置及三类CLI×三种Shell流程见[MANUAL](MANUAL.md#4-客户端配置v016)。
Agent先读服务资源和提示，无需强制配置配套Skill、AGENTS.md或CLAUDE.md。

- [发布记录](docs/releases/v0.1.6.md)：目标、CI、附件摘要及安装验证。
- [升级与回滚](MANUAL.md#5-启动排障与更新)：v0.1.5升级v0.1.6及旧任务回滚，保留密钥、原工作区模式、显式限制和状态目录。
- [保留验证](docs/UPGRADE-PRESERVATION.md)：Windows隔离验证v0.1.1→v0.1.2→v0.1.1，原文件内容/ACL及任务记录保留，未重复提交。
- [工作流契约](docs/WORKFLOW.md)与[复刻契约](docs/DESIGN-V2.md)：输入及验收边界。
- [验证记录](docs/VALIDATION.md)与[开发交接](docs/HANDOFF.md)：验证范围及历史决策。

## 开发验证

```powershell
uv sync --locked
if ($LASTEXITCODE -ne 0) { throw '锁定安装失败' }
uv run --no-sync python scripts/check.py
if ($LASTEXITCODE -ne 0) { throw '本地质量检查失败' }
```

SDK锁定MCP Python 2.3.0，协议测试为2026-07-28 discover流程。实际Host产品与旧协议兼容尚未验证。
v0.1.2已修复旧v0.1.1的serverInfo展示版本问题，旧发布附件保持不变；旧运行目录ACL仍不自动修复。

Host模板见 [docs/hosts](docs/hosts)，包含Cherry Studio、Codex、Claude Code、Claude-3p及DSH。
DSH区分web/desktop/multica的加载方式；desktop由App启动，不能用npm CLI代替。
v0.1.3发布包含三份消费端指南；旧v0.1.2服务需按升级流程更新，不能仅复制新指南改变服务行为。
核对来源与验证范围见[Host交付记录](docs/HOST-CONFIG-VALIDATION.md)。

v0.1.3另将输入/下载大小、下载域名名单、轮询/HTTP超时和新任务并发/修订额度改为默认不限制、显式设置才生效。
业务文本长度上限已移除；完整检查清单与保留的校验见[运行限制审计](docs/OPERATIONAL-LIMITS.md)。旧任务已冻结额度继续有效。

v0.1.4已修复Windows并发准备图片的路径包含检查误拒绝。升级并重启当前MCP后，沿原run_id查询与恢复，不重建任务；unknown先核查原供应商task_id。真实越界、junction或权限错误仍拒绝，见[根因与恢复边界](docs/WINDOWS-PATH-FIX.md)。

v0.1.5已修复v0.1.4后台Provider初始化异常未落盘、任务注册未清理的缺口。初始化失败可见blocked/phase，修正已确认问题或更新并重启实际服务后沿原run_id恢复，保留receipt和成功产物。消费端具体触发原因仍须脱敏stderr确认，排查边界见[后台执行诊断](docs/BACKGROUND-EXECUTION.md)。
