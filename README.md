# ecommerce-image-replicator-mcp

本地接手请先阅读 [工作交接文档](docs/HANDOFF.md)，包含修改历史、恢复边界及验证状态。

Python LangGraph StateGraph 电商竞品图复刻服务，通过本地 stdio MCP 为 Agent 提供输入契约、
任务准备、后台执行、查询与恢复能力，SQLite 保存 checkpoint 和上游操作记录。

开发安装（Python 3.12、uv 0.12.23）：

```bash
uv sync --locked
uv run --no-sync python scripts/check.py
```

业务工作区目录：`references/<group>/`、`products/`、`brief/`、`prompts/`、`artifacts/`。
私有 `.env` 固定放在 MCP 安装根，密钥字段见 `.env.example`；保留已有文件，不覆盖。

```bash
uv run --no-sync python -m image_replicator --project-root "$PWD" --workspace /absolute/agent-workspace
```

未设置预算时可以发现能力、准备和查询任务，收费执行会明确报错。业务使用前需配置两个密钥
及 `--max-batch-images`、`--max-request-bytes`、`--max-output-tokens`。这些是操作者配置，
供应商实际上限及严格 JSON 兼容性尚未验证。

见 [使用手册](MANUAL.md) 与 [工作流契约](docs/WORKFLOW.md)。当前为开发版本，尚无经
GitHub CI 发布的标签。测试使用受控替身、实际 LangGraph/SQLite 及官方 MCP SDK stdio
客户端；真实收费调用与 Host 产品联调未执行。
