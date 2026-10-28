# 使用手册

v0.1.1 已于2026-10-27 18:20（Asia/Shanghai）正式发布。本页按实际发布结果回填；标签内手册保留发布前快照，最新交付证据见本页和Release。

| 发布核对项 | 实际结果 |
|---|---|
| Release | [v0.1.1](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/releases/tag/v0.1.1) |
| 标签完整SHA | `c85f396c559411a68bdd5a2cba4bbbe858ab3245` |
| PR及审查 | [修复#3](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/pull/3)、[目录#4](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/pull/4)；维护代理审查，无独立人员审批 |
| PR Windows/Linux CI | [修复通过](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/actions/runs/40486497182)、[目录通过](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/actions/runs/40486824660) |
| 合入Windows/Linux CI | [通过](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/actions/runs/40487042057) |
| 标签CI/CD | [通过](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/actions/runs/40487272872)，先草稿、核验后公开 |
| 安装验证 | Windows Python 3.12.14，远端干净checkout及下载源码包锁定无开发依赖安装、wheel安装通过；8工具/1资源/1提示；无收费调用 |

本地131项测试通过、1项POSIX专项跳过，CI覆盖Windows/Linux。仓库未配置分支保护，门禁按流程核对。实际Host跨提升权限切换未实机联调。4个附件GitHub摘要及下载文件一致，两个包与SHA256SUMS一致，SOURCE_COMMIT与标签一致。

| 正式附件 | SHA256 |
|---|---|
| [ecommerce_image_replicator_mcp-0.1.1-py3-none-any.whl](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/releases/download/v0.1.1/ecommerce_image_replicator_mcp-0.1.1-py3-none-any.whl) | `1656dd7973d7f6d7a92c19116c7034f7160a46b61e039de838765608a6f1931a` |
| [ecommerce_image_replicator_mcp-0.1.1.tar.gz](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/releases/download/v0.1.1/ecommerce_image_replicator_mcp-0.1.1.tar.gz) | `06eaabdf08c1a92bd2e6e84d8e4fa84c286e9971d902f7346e718712e2faf0a9` |
| [SHA256SUMS](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/releases/download/v0.1.1/SHA256SUMS) | `5e9028bb84a68d1804a383aefb94bb8b5c0d62ce7e5ff26cfebc94ba88c7c3ba` |
| [SOURCE_COMMIT](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/releases/download/v0.1.1/SOURCE_COMMIT) | `88fbd95e3822b1a799818c341c662e49130aeb0cdd391821b65256287355cbbd` |

## 1. 环境准备

使用与Host相同账号的普通PowerShell安装、检查和启动。安装父目录如需管理员授权，可单独准备该目录；不要长期以管理员身份运行Host。Windows运行目录继承业务工作区ACL，工作区应仅向需要访问任务数据的账号开放。

Python 3.12+；开发与 CI 固定 Python 3.12、uv 0.12.23。官方 MCP Python SDK 锁定 2.3.0，
服务类为 MCPServer；协议测试使用 2026-07-28 discover 流程、本地 stdio。
Host 产品和旧协议兼容性尚未验证。需要 GitHub/PyPI 访问，业务 API 为 `ai.t8star.org`。

安装根 `.env` 提供 `ZHENZHEN_GEMINILLM_API_KEY` 和 `ZHENZHEN_GPTIMAGEGEN_API_KEY`。
逐字段 `.env` → 进程 → Windows 当前用户环境，仅缺失可回退；空值、重复、语法错误、
读取失败均报错。不展开变量，不执行代码；限制为服务账号及必要管理员可读取，修改后重启。
安装根固定通过 `--project-root` 指定。已发布 v0.1.1 用 `--workspace` 固定业务目录；当前源码支持任务级目录，见第4节及下方说明，均不依赖 Host cwd。

## 2. 项目初始化

以下为已发布v0.1.1的固定版本安装流程。
先从仓库Release核对发布状态、Windows CI及附件SOURCE_COMMIT全文；完整SHA必须对应该标签。
仓库访问需成员自己的GitHub权限，不能把令牌拼入URL。D盘及运行账号须有相应空间与读写权限。

```powershell
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path 'D:\MCP' -Force | Out-Null
$ProjectDir = 'D:\MCP\ecommerce-image-replicator-mcp'
if (Test-Path $ProjectDir) { throw '目录已存在，请使用更新流程。' }
$ExpectedCommit = 'c85f396c559411a68bdd5a2cba4bbbe858ab3245'
if ($ExpectedCommit -notmatch '^[a-fA-F0-9]{40}$') { throw 'SHA格式不正确，停止安装' }
git clone --branch v0.1.1 --single-branch https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp $ProjectDir
if ($LASTEXITCODE -ne 0) { throw 'clone 失败' }
$ActualCommit = git -C $ProjectDir rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $ActualCommit -ne $ExpectedCommit) { throw '提交不匹配，停止安装' }
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
CI job 超时设为15分钟。成员无需安装开发依赖即可执行下面的只读协议发现检查（45秒超时，不请求供应商）：

```powershell
New-Item -ItemType Directory -Path 'D:\EcommerceImageReplicator' -Force | Out-Null
uv --directory 'D:\MCP\ecommerce-image-replicator-mcp' run --no-sync python scripts/smoke.py --project-root 'D:\MCP\ecommerce-image-replicator-mcp' --workspace 'D:\EcommerceImageReplicator'
if ($LASTEXITCODE -ne 0) { throw '协议发现失败，停止接入Host' }
```

工作区需已存在。成功输出包含8个工具、1个资源、1个提示；失败非零退出。该检查不执行绘图，也不代表具体Host联调通过。

现有用户可以继续显式指定原业务工作区；默认目录改名不代表自动迁移。不要只切换路径后丢弃原`.replicator`，其中包含任务与供应商恢复记录。

## 4. 客户端配置（v0.1.2 候选，待发布核验）

本节配置用于已完成任务级工作区改造的当前源码，不能直接用于上述 v0.1.1 安装。
已发布 v0.1.1 仍须在 args 末尾增加 `"--workspace", "D:\\EcommerceImageReplicator"`；现有固定工作区配置继续有效。
当前源码的本地 MCP JSON 见根目录 `.mcp.json.example`；启动不绑定业务目录。
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
        "D:\\MCP\\ecommerce-image-replicator-mcp"
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
  "--project-root", "D:\\MCP\\ecommerce-image-replicator-mcp"
]
```

保存后按实际 Host 操作重启、检查能力发现，再绑定任务 Agent。不要求 cwd。
Claude-3p、Cherry Studio、DSH web/desktop/multica 及各 Host CLI 的 PowerShell/Bash/Zsh
注册流程未验证，本版不声明支持或提供猜测的补丁。仅本地 stdio 接入。

## 5. 启动排障与更新

```powershell
uv --directory 'D:\MCP\ecommerce-image-replicator-mcp' run --no-sync python -m image_replicator --project-root 'D:\MCP\ecommerce-image-replicator-mcp' --workspace 'D:\EcommerceImageReplicator'
if ($LASTEXITCODE -ne 0) { throw '服务退出失败，检查 stderr。' }
```

启动不安装、构建或升级；等待协议输入时没有普通输出是正常行为。收费执行前追加
`--max-batch-images N --max-request-bytes B --max-output-tokens T`，N/B/T 由操作者填写正整数，
不代表经供应商确认的上限。下载额外域名通过重复 `--download-host` 显式允许。

更新前停止 MCP、记录 `git rev-parse HEAD` 并检查 `git status --porcelain`；有修改先保留。
成员只更新到已公开且核验通过的标签，避免跟随开发分支。

```powershell
$ErrorActionPreference = 'Stop'
$ProjectDir = 'D:\MCP\ecommerce-image-replicator-mcp'
$Changes = git -C $ProjectDir status --porcelain
if ($LASTEXITCODE -ne 0 -or $Changes) { throw '工作区存在改动或检查失败，停止升级' }
$PreviousCommit = git -C $ProjectDir rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw '无法记录原提交' }
Write-Host "保留原提交：$PreviousCommit"
$ExpectedCommit = Read-Host '粘贴目标Release的SOURCE_COMMIT完整40位SHA'
if ($ExpectedCommit -notmatch '^[a-fA-F0-9]{40}$') { throw 'SHA无效' }
git -C $ProjectDir fetch origin tag v0.1.1
if ($LASTEXITCODE -ne 0) { throw '获取目标失败' }
$TagCommit = git -C $ProjectDir rev-parse 'v0.1.1^{commit}'
if ($LASTEXITCODE -ne 0 -or $TagCommit -ne $ExpectedCommit) { throw '标签与发布提交不一致' }
git -C $ProjectDir switch --detach --no-overwrite-ignore v0.1.1
if ($LASTEXITCODE -ne 0) { throw '切换失败' }
uv --directory $ProjectDir sync --locked --no-dev
if ($LASTEXITCODE -ne 0) { throw '安装失败，不启动服务' }
uv --directory $ProjectDir run --no-sync python scripts/smoke.py --project-root $ProjectDir --workspace 'D:\EcommerceImageReplicator'
if ($LASTEXITCODE -ne 0) { throw '协议复验失败' }
```

回滚同样先确认工作区干净，用记录的完整SHA执行`git switch --detach --no-overwrite-ignore`，再锁定安装和协议检查。回滚切回已记录 SHA 后重新安装；保留 `.env`、工作区和 `.replicator`，
不 reset/clean 清空。不承诺未来数据库 schema 的降级兼容。

## 6. 文件清单

Git 跟踪 src、tests、pyproject、uv.lock、脚本、CI、规范和空密钥模板。
`.venv`、缓存、构建、测试报告为生成物。业务工作区 `.replicator` 保存恢复状态和中间图像，
`artifacts` 保存最终结果。入口 `python -m image_replicator`。Release计划附源码包、wheel和摘要/来源文件，不提供额外成员ZIP安装包。源码包采用显式白名单，不包含产品图、竞品图、业务brief、任务数据库或本地证据。

## 7. 资源清单

下表对应当前源码的新契约，尚未发布；v0.1.1 保留固定工作区及8工具契约。

| 能力 | 参数和结果 | 副作用 |
|---|---|---|
| Resource `replicator://input-contract` | 增量 schema、顺序、预算 | 无收费 |
| Prompt `prepare_inputs` | 无参数，返回 Agent 输入说明 | 无收费 |
| Tool `inspect_inputs` | workspace（任务模式必填），返回分组顺序和稳定 image_id | 读取工作区，可能初始化本地日志 |
| Tool `prepare_run` | workspace、options：image_model、concurrency、selected_image_ids、review_mode、max_visual_revisions | 冻结 v2 输入，返回 run_id/workspace/thread_id/jobs |
| Tool `execute_run` | run_id（固定模式兼容 thread_id） | 授权收费，后台执行或恢复 |
| Tool `get_run` | run_id（固定模式兼容 thread_id）；返回状态、jobs、完成时 artifacts | 本地查询；旧任务首次查询可登记绑定，无 API 调用 |
| Tool `reconcile_submission` | run_id（固定模式兼容 thread_id）、从0开始的index、供应商task_id | 查询并绑定已知任务，不提交绘图 |
| Tool `get_design` | run_id（固定模式兼容 thread_id）、image_id；返回原图绑定的复刻契约及哈希或缺失的分析字段 | 只读本地 |
| Tool `record_review` | run_id（固定模式兼容 thread_id）、report；必须匹配原图/成图/契约哈希及全部检查项 | 保存对照验收证据，无 API 调用 |
| Tool `prepare_revision` | parent_run_id（固定模式兼容 parent_thread_id）、updates；可选 product_context、legacy_revision_budget | 预留谱系预算并冻结指定图片修订，无 API 调用 |
| Tool `import_run` | workspace、thread_id | 绑定原工作区已有任务，返回 run_id；无 API 调用 |

工具名称如表，Host 对模型暴露的前缀由 Host 决定。工具失败使用 isError；后台失败为
run.status=blocked。scheduled 只表示已安排执行，不代表生成成功，使用 get_run 查询。

## 8. 功能说明

Agent 根据 brief/产品图/竞品图，按 inspect_inputs 顺序写 prompts 数组，调用 prepare_run，
检查 jobs 后调用 execute_run，再轮询 get_run。options.image_model 选择 flare 或 sunburst 系列；
按预处理后画布长边自动选版本：<=1024 无后缀，1024 < 长边 <=2048 使用 -2k，
2048 < 长边 <=4096 使用 -4k。实际模型持久化并由 jobs[].model 返回，重试复用。
当前以原始参考图的构图、对象和互动关系为基线；允许产品属性与品牌主题变化。v2 只反推缺失字段，再逐图生成、落盘和对照验收。产品事实和默认要求写入
brief/design.json；Markdown 仅冻结留档，不再整段加入提示。完整 texts/scene 可以省去两类反推。
相同冻结输入得到同一 thread_id；修改原文件需重新 prepare。
同一 thread 恢复复用 checkpoint 和供应商任务，已完成时返回已有产物。

默认 review_mode=manual、max_visual_revisions=0，生成后为 review_required；vision 增加每图最多
一次 Gemini 视觉评审。accepted 才表示全部验收项通过，模型判断不等于真实商品性能认证。
生成始终携带完整参考图；验收同时携带原图、成图和产品图，保留污渍、手部、动作等原有表现元素。
design.product_attributes 用 property/value/source 指定产品名称、尺寸、材料、规格、外观等有依据的属性；
design.brand_style 的 palette/tone 可按产品图适配；art_style 只在用户明确指定艺术风格时填写，
否则沿用各原图的摄影/图标/插画等原有风格，不因配色变化自动水彩化。
scene/instruction 不能改变主要表达、关键主体身份和互动；允许少量无损主旨的装饰、位置和渲染差异。
精确花色等改名用`text_replacements`指定old/new/source；构造阶段落实为最终texts，未匹配或冲突会阻止提交。
`design.brand_style.text_color`指定六位HEX主题字色，构造阶段覆盖结构化文字CSS并校验，成图另查text_theme。
文案缺少修订信息时先询问；用户明确坚持继续才沿用未确定部分的参考文案，产品及颜色适配不能撤销。
已有明确改名要求直接修订，不重复索取；新图需重新验收，不能把旧失败图直接标为通过。
新输入拒绝 layout/rebuild，以及非空的 objects/layout_regions/forbidden_elements 结构覆盖。
验收检查表达主旨/关键关系保留与增量生效，不要求像素或所有细节完全一样；小差异可通过。
自然语言越界仍需人工或模型对照验收，本地 schema 不保证完整语义识别。
历史 accepted 不代表复刻通过，应核对 alignment_policy 和 reference_alignment_verified。
新策略为 reference-creative-v1，旧v2未提交任务不能继续执行，已提交任务仅恢复查询/下载，不再追加绘图POST。
历史用户明确接受的结果仍保留，策略标记变更不撤销用户接受决定。
partial 会返回已完成图片，needs_revision 可用 prepare_revision 只修订指定图；之后仍需显式 execute。
使用 selected_image_ids 选择小样本，不必另建参考目录。完整字段、预算、状态和 v1 迁移见
[v2 设计与修订](docs/DESIGN-V2.md)。已有 v1 thread 按原流程恢复，不自动重绘或升级验收状态。

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
- Gemini schema：项目将本地引用展开并适配供应商 schema 子集，完整约束仍由客户端校验。
  LLM HTTP 400/401/403/404/413/415/422 会阻塞相同请求；查看错误中的 diagnostic_id 对应
  `.replicator/errors/<diagnostic_id>.json`。记录仅含脱敏、限长字段及响应摘要，不含原始 HTTP 正文。
- 顺序错误：核对自然排序及增量数组；错序 LLM 输出会拒绝。
- NOT_START/IN_PROGRESS：继续查询，不重复提交。
- 提交未知：向供应商找回原 task_id，再 reconcile；无法找回保持阻塞。
- 下载失败：补充授权域名后恢复已有任务。
- 返回尺寸不符：原图已保留，先确认供应商 size 行为，避免错误裁剪。
- 安装失败：核对锁、uv/Python 与 TLS/包源，不删锁或关闭校验。
- GitHub标签或权限错误：确认Release已公开、账号有仓库权限，并核对SOURCE_COMMIT；不可改装未核验开发HEAD。
- Host无法发现：先执行smoke.py；模板只验证语法，Host产品、旧协议或CLI注册组合未联调。
- 本地126项测试及12张真实复刻验收通过，不等于GitHub目标提交、Windows CI或发布安装已验收。

### Windows运行目录拒绝访问

v0.1.0在管理员环境首次启动时可能创建仅SYSTEM、Administrators及OWNER RIGHTS可访问的`.replicator`。v0.1.1对新目录改为继承工作区ACL；升级不会自动修复已有ACL，避免改变成员的访问策略。

若出现`Workspace runtime access denied`，先停止使用该工作区的MCP，在普通Host账号终端运行`whoami /user`记录实际SID；由管理员检查目标目录的`icacls`和`Get-Acl`。确认账号和目录后，仅授予该账号对`.replicator`及子项的修改权限，保留原ACL。不要授予Everyone完全控制，不要删除数据库或任务记录。修复后在普通权限终端重新执行协议检查，再启用Host。

`Cannot initialize workspace journal`也可能是磁盘空间或数据库锁问题，不应一律当作权限错误。保留原文件并检查相应条件。`Workspace directory not found`表示需要先创建业务工作区。

已知展示问题：已发布v0.1.1的MCP serverInfo仍显示0.1.0，发行包及SOURCE_COMMIT为正确的0.1.1版本，Windows权限修复已包含。版本展示修正及一致性检查已纳入发布后的源码PR，尚未进入新的发布标签；不覆盖v0.1.1附件。


## 任务级工作区使用（v0.1.2 候选，待发布核验）

当前源码提供9个工具，第7节工具表按新契约更新。已发布 v0.1.1 为8个工具，无 import_run，仍需固定工作区。
省略启动 --workspace 后，Agent 必须在 inspect_inputs / prepare_run 传已有项目绝对目录，保存返回 run_id；
后续用 run_id 查询、生成、验收与恢复，prepare_revision 用 parent_run_id。旧固定模式继续兼容 thread_id。
详细调用示例、可选目录限制、索引备份和旧任务导入见[任务级工作区说明](docs/TASK-WORKSPACES.md)。
无需强制安装配套 Skill 或填写 AGENTS.md / CLAUDE.md；Agent 应先读 MCP 自带资源和提示。
