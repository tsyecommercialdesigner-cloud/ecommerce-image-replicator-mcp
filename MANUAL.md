# 使用手册

## 1. 环境准备

Python 3.12+；开发与 CI 固定 Python 3.12、uv 0.12.23。官方 MCP Python SDK 锁定 2.3.0，
服务类为 MCPServer；协议测试使用 2026-07-28 discover 流程、本地 stdio。
Host 产品和旧协议兼容性尚未验证。需要 GitHub/PyPI 访问，业务 API 为 `ai.t8star.org`。

安装根 `.env` 提供 `ZHENZHEN_GEMINILLM_API_KEY` 和 `ZHENZHEN_GPTIMAGEGEN_API_KEY`。
逐字段 `.env` → 进程 → Windows 当前用户环境，仅缺失可回退；空值、重复、语法错误、
读取失败均报错。不展开变量，不执行代码；限制为服务账号及必要管理员可读取，修改后重启。
安装根与 Agent 工作区通过 `--project-root` 和 `--workspace` 分别指定，不依赖 Host cwd。

## 2. 项目初始化

尚无已通过 CI 发布的标签；以下为开发安装，不能当作已验收的稳定发行版。

```powershell
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path 'D:\MCP' -Force | Out-Null
$ProjectDir = 'D:\MCP\ecommerce-image-replicator-mcp'
if (Test-Path $ProjectDir) { throw '目录已存在，请使用更新流程。' }
git clone --branch dev --single-branch https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp $ProjectDir
if ($LASTEXITCODE -ne 0) { throw 'clone 失败' }
Set-Location $ProjectDir
uv sync --locked --no-dev
if ($LASTEXITCODE -ne 0) { throw '安装失败' }
if (!(Test-Path '.env')) { Copy-Item '.env.example' '.env' -ErrorAction Stop }
notepad '.env'
```

手动填写私有密钥，不修改空值模板。Windows 使用文件安全属性限制 `.env` 读取账号；
Unix 使用 `chmod 600 .env`。Agent 工作区按工作流契约放入输入，不覆盖已有业务文件。

## 3. 可用性测试

开发安装 `uv sync --locked` 后执行 `uv run --no-sync python scripts/check.py`。
检查格式、lint、类型、测试和秘密模式；失败返回非零。测试包含实际 SDK stdio 子进程，
资源/提示/工具发现、输入准备、错误返回与 SQLite 恢复，使用临时目录和假值，不触发收费。
构建用 `uv build --no-sources`；依赖检查用 `uv run --no-sync pip-audit`。
CI job 超时设为 15 分钟。上述检查不代表真实图像质量或 Host 联调通过。

## 4. 客户端配置

本地 MCP JSON 见根目录 `.mcp.json.example`；使用前填写实际 Agent 工作区绝对路径。
后端密钥由 MCP 自行读取安装根 `.env`，不在 Host 配置中传递。
本地 JSON/Claude Code 项目配置候选（未联调）如下，与模板内容一致：

```json
{
  "mcpServers": {
    "ecommerce-image-replicator": {
      "command": "uv",
      "args": [
        "--directory",
        "D:\\MCP\\ecommerce-image-replicator-mcp",
        "run",
        "--no-sync",
        "python",
        "-m",
        "image_replicator",
        "--project-root",
        "D:\\MCP\\ecommerce-image-replicator-mcp",
        "--workspace",
        "D:\\AgentWorkspace"
      ]
    }
  }
}
```

Codex TOML 候选片段（未联调），只合并目标服务，保留无关配置：

```toml
[mcp_servers.ecommerce-image-replicator]
command = "uv"
args = [
  "--directory", "D:\\MCP\\ecommerce-image-replicator-mcp",
  "run", "--no-sync", "python", "-m", "image_replicator",
  "--project-root", "D:\\MCP\\ecommerce-image-replicator-mcp",
  "--workspace", "D:\\AgentWorkspace"
]
```

保存后按实际 Host 操作重启、检查能力发现，再绑定任务 Agent。不要求 cwd。
Claude-3p、Cherry Studio、DSH web/desktop/multica 及各 Host CLI 的 PowerShell/Bash/Zsh
注册流程未验证，本版不声明支持或提供猜测的补丁。仅本地 stdio 接入。

## 5. 启动排障与更新

```powershell
uv --directory 'D:\MCP\ecommerce-image-replicator-mcp' run --no-sync python -m image_replicator --project-root 'D:\MCP\ecommerce-image-replicator-mcp' --workspace 'D:\AgentWorkspace'
if ($LASTEXITCODE -ne 0) { throw '服务退出失败，检查 stderr。' }
```

启动不安装、构建或升级；等待协议输入时没有普通输出是正常行为。收费执行前追加
`--max-batch-images N --max-request-bytes B --max-output-tokens T`，N/B/T 由操作者填写正整数，
不代表经供应商确认的上限。下载额外域名通过重复 `--download-host` 显式允许。

更新前停止 MCP、记录 `git rev-parse HEAD` 并检查 `git status --porcelain`；有修改先保留。
开发更新在干净 dev 执行 `git pull --ff-only origin dev`，再 `uv sync --locked --no-dev`。
稳定发布后获取并核对标签/SHA，使用 `git switch --detach --no-overwrite-ignore <标签或SHA>`，
重新锁定安装并验证。回滚切回已记录 SHA 后重新安装；保留 `.env`、工作区和 `.replicator`，
不 reset/clean 清空。不承诺未来数据库 schema 的降级兼容。

## 6. 文件清单

Git 跟踪 src、tests、pyproject、uv.lock、脚本、CI、规范和空密钥模板。
`.venv`、缓存、构建、测试报告为生成物。业务工作区 `.replicator` 保存恢复状态和中间图像，
`artifacts` 保存最终结果。入口 `python -m image_replicator`，不提供 ZIP。

## 7. 资源清单

| 能力 | 参数和结果 | 副作用 |
|---|---|---|
| Resource `replicator://input-contract` | 增量 schema、顺序、预算 | 无收费 |
| Prompt `prepare_inputs` | 无参数，返回 Agent 输入说明 | 无收费 |
| Tool `inspect_inputs` | 无参数，返回分组顺序 | 读取工作区 |
| Tool `prepare_run` | 可选 options：image_model、concurrency（1..8，默认2） | 冻结输入，返回 thread_id/jobs |
| Tool `execute_run` | thread_id | 授权收费，后台执行或恢复 |
| Tool `get_run` | thread_id；返回状态、jobs、完成时 artifacts | 只读本地 |
| Tool `reconcile_submission` | thread_id、从0开始的index、供应商task_id | 查询并绑定已知任务，不提交绘图 |

工具名称如表，Host 对模型暴露的前缀由 Host 决定。工具失败使用 isError；后台失败为
run.status=blocked。scheduled 只表示已安排执行，不代表生成成功，使用 get_run 查询。

## 8. 功能说明

Agent 根据 brief/产品图/竞品图，按 inspect_inputs 顺序写 prompts 数组，调用 prepare_run，
检查 jobs 后调用 execute_run，再轮询 get_run。options.image_model 选择 flare 或 sunburst 系列；
按预处理后画布长边自动选版本：<=1024 无后缀，1024 < 长边 <=2048 使用 -2k，
2048 < 长边 <=4096 使用 -4k。实际模型持久化并由 jobs[].model 返回，重试复用。
文案、画面分别反推，校验后整合增量并发绘图，
持久化原图，再裁剪恢复尺寸。相同冻结输入得到同一 thread_id；修改原文件需重新 prepare。
同一 thread 恢复复用 checkpoint 和供应商任务，已完成时返回已有产物。

## 9. 注意事项

详见 [工作流契约](docs/WORKFLOW.md)。绘图最多三次尝试，明确失败后的新提交可能再次收费；
未知提交不会重发。供应商无幂等键时，框架无法消除“受理成功但未收到ID”的不确定窗口。
停止 MCP 不撤销供应商任务，下次 execute 相同 thread_id 恢复。
`.replicator` 包含业务信息和原始响应，需本机权限保护并按业务留存要求管理。
默认下载允许 ai.t8star.org、files.closeai.fans，不跟随重定向；结合部署出口限制使用。
原尺寸恢复涉及缩放，不保证像素无损；文案位置和生成质量仍需视觉验收。

## 10. 常见问题

- 未配置预算/密钥：配置启动参数和安装根 `.env` 后重启。
- 严格 JSON 不支持或截断：核对供应商能力和输出预算；不自动降级自由文本。
- 顺序错误：核对自然排序及增量数组；错序 LLM 输出会拒绝。
- NOT_START/IN_PROGRESS：继续查询，不重复提交。
- 提交未知：向供应商找回原 task_id，再 reconcile；无法找回保持阻塞。
- 下载失败：补充授权域名后恢复已有任务。
- 返回尺寸不符：原图已保留，先确认供应商 size 行为，避免错误裁剪。
- 安装失败：核对锁、uv/Python 与 TLS/包源，不删锁或关闭校验。
- Beads：当前云环境缺少 bd，尚未创建任务记录；未覆盖现有 Dolt 配置。
