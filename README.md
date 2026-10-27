# ecommerce-image-replicator-mcp

基于 Python LangGraph 的电商竞品图复刻 MCP 服务，通过本地 stdio 向 Agent 提供输入准备、生成、恢复、验收和单图修订能力。

原始参考图决定整体构图、关键对象及互动关系；产品图和有来源的增量决定产品外观、文案与品牌主题。
默认沿用参考图艺术风格，允许不改变主旨的小幅创意差异。指定文案替换及文字主题色在提交前解析、校验，出图后再次对照验收。
SQLite 保存任务与供应商凭据，未知提交不重复绘图。

## 发布状态

**[v0.1.0 已发布](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/releases/tag/v0.1.0)**（2026-10-27），目标提交 `726efe6ad27933656ca24214806043f794450196`。
[PR #1](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/pull/1)、[合入 CI](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/actions/runs/40482261058)及[标签 CI/CD](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/actions/runs/40482454707)已完成，Windows/Linux检查通过。
126项测试、历史真实全套12张复刻验收，以及正式附件独立安装/stdio检查通过。审查由维护代理执行，无独立人员审批；实际Host产品联调尚未验证。
附件及SHA256见[发布说明](docs/releases/v0.1.0.md)和[使用手册](MANUAL.md)。

## 安装与使用

Windows建议PowerShell 7、Git、Python 3.12和uv 0.12.23，默认安装到`D:\MCP\ecommerce-image-replicator-mcp`。
从项目仓库取得v0.1.0标签，按[使用手册](MANUAL.md#2-项目初始化)核对完整SHA，执行`uv sync --locked --no-dev`，
配置安装根私有`.env`，运行不收费的协议检查，再将本地stdio服务加入Host。日常启动使用`uv run --no-sync`，不临时安装依赖。

默认业务工作区为`D:\EcommerceImageReplicator`，由`--workspace`显式传入，与MCP安装目录分离。
业务工作区包含`references/<group>/`、`products/`、`brief/`、`prompts/`；结果和恢复记录分别位于`artifacts/`、`.replicator/`。
后端密钥为`ZHENZHEN_GEMINILLM_API_KEY`与`ZHENZHEN_GPTIMAGEGEN_API_KEY`，逐字段按项目`.env`→进程→Windows用户环境读取。
未配置密钥和执行预算时只可准备、发现及查询，不会默认提交收费请求。

- [使用手册](MANUAL.md)：安装、stdio配置、预算、恢复及修订。
- [工作流契约](docs/WORKFLOW.md)与[逐图复刻契约](docs/DESIGN-V2.md)：输入与验收边界。
- [验证记录](docs/VALIDATION.md)：本地、真实API、Host与CI的验证范围。
- [v0.1.0发布说明](docs/releases/v0.1.0.md)：交付内容与发布核对状态。
- [开发交接](docs/HANDOFF.md)：历史决策和未完成交付步骤。

## 开发验证

```powershell
uv sync --locked
if ($LASTEXITCODE -ne 0) { throw '锁定安装失败' }
uv run --no-sync python scripts/check.py
if ($LASTEXITCODE -ne 0) { throw '本地质量检查失败' }
```

SDK锁定MCP Python 2.3.0，协议测试为2026-07-28 discover流程。本地stdio协议与真实供应商调用已验证；
具体Host产品联调和旧协议兼容尚未验证；发布证据见上方CI与Release链接。
