# 使用手册

当前维护源码增加逐图预检/显式分析恢复，尚未发布；下述v0.1.5实际发布记录和安装目标保持原样。新功能用法见[消费端使用手册](docs/guidebook-of-ecommerce-image-replicator-mcp.md)，先以实际工具发现确认可用，不能仅复制新文档就使用旧服务没有的能力。

v0.1.5 已于 2026-10-28 13:35（Asia/Shanghai）正式发布，目标 `b1c1bd1bcdba05ec50ec5e33a83797c90ec5751f`。
修复后台Provider初始化失败未落盘、scheduled后始终prepared及任务注册残留；清理失败不覆盖已保存结果，启动前取消与日志写入失败有脱敏观测。
6项定向回归、完整本地201通过/1项平台跳过，Windows/Linux PR、合入和标签CI通过。
v0.1.4→v0.1.5目标→v0.1.4隔离升级回滚验证保留测试.env字节/ACL、工作区、任务索引和成功产物；pending receipt沿原身份恢复，无重复提交。
四个下载附件与GitHub摘要、SHA256SUMS及SOURCE_COMMIT一致；源码包锁定无开发依赖安装、wheel锁定依赖安装、任务/固定模式stdio，以及两种安装的初始化失败可观测和原run_id恢复检查通过。
无真实收费请求、实际消费Host联调或成员环境修改。消费端具体触发条件仍待脱敏堆栈，无效代理仅为离线复现条件。
此前发布标签与附件不变。标签内文档为候选快照，实际交付结果以main在线手册为准。

| 发布核对项 | 实际结果 |
|---|---|
| Release | [v0.1.5](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/releases/tag/v0.1.5) |
| 标签完整SHA | `b1c1bd1bcdba05ec50ec5e33a83797c90ec5751f` |
| PR | [#15](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/pull/15)，维护Agent复核，无独立人工审批 |
| PR Windows/Linux CI | [通过](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/actions/runs/40637910060) |
| 合入 Windows/Linux CI | [通过](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/actions/runs/40638188979) |
| 标签 CI/CD | [通过](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/actions/runs/40638429335)，草稿核验后发布 |

| 附件 | SHA256 |
|---|---|
| [ecommerce_image_replicator_mcp-0.1.5-py3-none-any.whl](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/releases/download/v0.1.5/ecommerce_image_replicator_mcp-0.1.5-py3-none-any.whl) | `5ed9b38be99f275d6f5280f8866dfa7b271bdbfc08a37260e1f295d79e3a1f40` |
| [ecommerce_image_replicator_mcp-0.1.5.tar.gz](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/releases/download/v0.1.5/ecommerce_image_replicator_mcp-0.1.5.tar.gz) | `862700d03c8624bd2c11143ea0e3eceba41eb1de62f47b5e518dcacf654b5b04` |
| [SHA256SUMS](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/releases/download/v0.1.5/SHA256SUMS) | `e649779295847b70020cd205b9322eefccdb989e962be9faa51a9d67192880c3` |
| [SOURCE_COMMIT](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/releases/download/v0.1.5/SOURCE_COMMIT) | `328ab643f43969b24d75c97aad5132818b656ce61a1fa64eb4bc569697591547` |

## 1. 环境准备

使用与Host相同账号的普通PowerShell安装、检查和启动。安装父目录如需管理员授权，可单独准备该目录；不要长期以管理员身份运行Host。Windows运行目录继承业务工作区ACL，工作区应仅向需要访问任务数据的账号开放。

建议普通 PowerShell 7、Git 2.23+（需支持 switch）、Python 3.12 和 uv 0.12.23。
项目声明 Python 3.12+；CI 固定 Python 3.12、uv 0.12.23。官方 MCP Python SDK 锁定 2.3.0，
服务类为 MCPServer；协议测试使用 2026-07-28 discover 流程、本地 stdio。
Host 产品和旧协议兼容性尚未验证。需要 GitHub/PyPI 访问，业务 API 为 `ai.t8star.org`。

安装根 `.env` 提供 `ZHENZHEN_GEMINILLM_API_KEY` 和 `ZHENZHEN_GPTIMAGEGEN_API_KEY`。
逐字段 `.env` → 进程 → Windows 当前用户环境，仅缺失可回退；空值、重复、语法错误、
读取失败均报错。不展开变量，不执行代码；限制为服务账号及必要管理员可读取，修改后重启。
安装根固定通过 `--project-root` 指定。已发布 v0.1.1 用 `--workspace` 固定业务目录；v0.1.2 支持任务级目录，见第4节及下方说明，均不依赖 Host cwd。

先检查本机命令；任何一项不可用时先安装对应工具并重新打开普通终端：

```powershell
$PSVersionTable.PSVersion
Get-Command git, uv -ErrorAction Stop
 git --version
if ($LASTEXITCODE -ne 0) { throw 'Git不可用' }
uv --version
if ($LASTEXITCODE -ne 0) { throw 'uv不可用' }
```

GitHub与PyPI用于下载源码和依赖，供应商域名用于业务请求，两者分别排障。
需要代理时沿用组织已核准的Git/uv代理与CA配置，不关闭TLS校验。此项目无需Git LFS或submodule。

| 凭据 | 用途及要求 |
|---|---|
| `ZHENZHEN_GEMINILLM_API_KEY` | 反推/可选视觉评审；当前执行入口统一要求此字段 |
| `ZHENZHEN_GPTIMAGEGEN_API_KEY` | 绘图提交、查询和下载；当前执行入口统一要求此字段 |

值须为非空、非纯空白字符串，不含CR/LF/NUL；不假设固定密钥前缀。以UTF-8保存 `.env`。
文件权限可用 `Get-Acl -LiteralPath 'D:\MCP\ecommerce-image-replicator-mcp\.env'` 检查；
仅实际运行账号和必要管理员应有访问权限。修改后重启Host管理的MCP子进程。
用户级环境按MCP实际运行账号读取，旧父进程继承的进程值优先于更新后的用户级值；必要时重启Host。

## 2. 项目初始化

以下为已发布v0.1.5的固定版本安装流程。
先从仓库Release核对发布状态、Windows CI及附件SOURCE_COMMIT全文；完整SHA必须对应该标签。
仓库访问需成员自己的GitHub权限，不能把令牌拼入URL。D盘及运行账号须有相应空间与读写权限。

```powershell
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path 'D:\MCP' -Force | Out-Null
$ProjectDir = 'D:\MCP\ecommerce-image-replicator-mcp'
if (Test-Path $ProjectDir) { throw '目录已存在，请使用更新流程。' }
$ExpectedCommit = 'b1c1bd1bcdba05ec50ec5e33a83797c90ec5751f'
if ($ExpectedCommit -notmatch '^[a-fA-F0-9]{40}$') { throw 'SHA格式不正确，停止安装' }
git clone --branch v0.1.5 --single-branch https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp $ProjectDir
if ($LASTEXITCODE -ne 0) { throw 'clone 失败' }
$ActualCommit = git -C $ProjectDir rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $ActualCommit -ne $ExpectedCommit) { throw '提交不匹配，停止安装' }
Set-Location $ProjectDir
uv sync --locked --no-dev
if ($LASTEXITCODE -ne 0) { throw '安装失败' }
# 安装完成；凭据配置按下方两种方式选择，不自动创建空值.env。
```

凭据配置二选一：

- **已有用户级/进程环境变量**：不创建含空凭据字段的 `.env`。若已有 `.env`，保留它；需要某字段回退环境时，手工移除该字段定义，而不是把值留空。不要打印密钥或重设用户环境变量。
- **使用安装根 `.env`**：执行以下命令，仅在文件不存在时复制；在编辑器中填写实际密钥，保留已有配置，不修改空值模板。

```powershell
$ErrorActionPreference = 'Stop'
$ProjectDir = 'D:\MCP\ecommerce-image-replicator-mcp'
$EnvPath = Join-Path $ProjectDir '.env'
if (!(Test-Path -LiteralPath $EnvPath)) {
    [IO.File]::Copy((Join-Path $ProjectDir '.env.example'), $EnvPath, $false)
}
notepad $EnvPath
if ($LASTEXITCODE -ne 0) { throw '编辑器启动失败，请手工编辑现有.env' }
```

空字段、重复字段或文件读取/解析失败会阻止执行，不会回退旧密钥。
Windows使用文件安全属性限制实际账号访问；Unix使用 `chmod 600 .env`。
Agent工作区按第8节准备输入；不覆盖已有业务文件。

## 3. 可用性测试

开发安装 `uv sync --locked` 后执行 `uv run --no-sync python scripts/check.py`。
检查格式、lint、类型、测试和秘密模式；失败返回非零。测试包含实际 SDK stdio 子进程，
资源/提示/工具发现、输入准备、错误返回与 SQLite 恢复，使用临时目录和假值，不触发收费。
构建用 `uv build --no-sources`；依赖检查用 `uv run --no-sync pip-audit`。
CI job 超时设为15分钟。成员无需安装开发依赖即可执行下面的只读协议发现检查（45秒超时，不请求供应商）：

```powershell
uv --directory 'D:\MCP\ecommerce-image-replicator-mcp' run --no-sync python scripts/smoke.py --project-root 'D:\MCP\ecommerce-image-replicator-mcp'
if ($LASTEXITCODE -ne 0) { throw '协议发现失败，停止接入Host' }
```

任务模式启动无需业务目录；选择业务目录时该目录需已存在。成功输出包含9个工具、1个资源、1个提示；失败非零退出。该检查不执行绘图，也不代表具体Host联调通过。
默认任务模式的smoke不验证真实密钥、工作区写权限或供应商认证；真实密钥在执行/供应商查询入口读取校验。

现有用户可以继续显式指定原业务工作区；默认目录改名不代表自动迁移。不要只切换路径后丢弃原`.replicator`，其中包含任务与供应商恢复记录。

升级保留专项已于2026-10-28在Windows/Python3.12隔离环境通过：干净Git副本依次安装
v0.1.1→v0.1.2→v0.1.1，验证测试.env的内容/ACL、业务目录文件/ACL、任务索引、原产物保留；
原待完成任务按同一供应商编号续查，未新增提交。仅使用假密钥和替身供应商。
可复现脚本位于最新维护分支（不在原v0.1.2标签内）：

```powershell
uv run --no-sync python scripts/verify_upgrade.py
if ($LASTEXITCODE -ne 0) { throw '升级保留验证失败' }
```

这是维护者验证命令，不在成员真实安装目录执行。脚本要求本地已有两个正式标签，检查固定SHA，
在仓库.cache中克隆并安装，finally清理临时环境，报告保留在.cache/validation。
另已对v0.1.4→v0.1.5目标→v0.1.4完成相同保留验证；维护者可用 `scripts/verify_upgrade.py --candidate v0.1.5 --baseline v0.1.4` 复现，须先获取v0.1.1/v0.1.2/v0.1.3/v0.1.4/v0.1.5标签。
详细范围见[保留验证记录](docs/UPGRADE-PRESERVATION.md)；不覆盖真实Host跨权限切换及任意未来版本降级。

## 4. 客户端配置（v0.1.5）

本节交付 Cherry Studio、Codex、Claude Code / Claude-3p、DSH 四类 Host 的本地 stdio 配置。
**已发布v0.1.2的模板省略三项预算，旧版仍须配置正值才能生成。v0.1.3已改为opt-in-v1：省略即不限制，无需填写三个数值。**
按第5节读取当前连接的策略标识区分新旧行为；仅更新文档不会升级已安装服务。
模板适用于v0.1.5；结构也适用于v0.1.2，但旧版仍需预算配置；v0.1.3已包含本节配置和消费端指南，v0.1.2标签和附件保持原样。
旧标签安装中没有 docs/hosts 时，可直接复制本节完整代码块，无需升级到开发代码。
服务名统一为 `ecommerce-image-replicator`（26字符，无小数点），安装目录保持
`D:\MCP\ecommerce-image-replicator-mcp`。所有模板均不设置 cwd、不传后端密钥、不在启动时安装依赖。
`--project-root` 固定凭据和默认任务索引位置；省略 `--workspace` 后由每个任务显式选择业务目录。
旧固定目录仍可在 args 末尾追加 `"--workspace", "D:\\EcommerceImageReplicator"`；已有用户使用自己的原路径。
保留原预算、下载域名、state-dir及允许根配置，不能用最小模板覆盖这些设置。

编辑前保留私有备份；仅合并目标服务，保留其他服务、认证和设置。同名服务已存在时更新该项，不重复注册。
本节不列私有 Host 配置的存储目录。配置保存后重新启动该 Host 管理的 MCP 子进程。
成员须先完成第2–3节安装和stdio检查，并让实际Host账号的PATH能找到uv。

### 4.1 Cherry Studio

依据[官方操作说明](https://docs.cherryai.com.cn/advanced-basic/extensions/mcp.md)和
[JSON导入源码](https://github.com/CherryHQ/cherry-studio/blob/c40a14ba138255987f6f5019c77e5f51d80bc8d9/src/renderer/pages/settings/McpSettings/AddMcpServerModal.tsx)，
打开【设置】→【MCP】→【MCP服务器】→【添加】→从JSON导入，粘贴以下完整配置。
此块与交付文件 [cherry-studio.json](docs/hosts/cherry-studio.json) 逐字一致：

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

如果使用手工表单：类型选stdio，名称填ecommerce-image-replicator，命令填uv，参数按args数组逐项输入，
每个数组元素一个参数；不要把整串参数填成一个元素，环境变量栏留空。
保存并启用服务器，打开详情检查工具列表和日志；再进入【工作】→目标Agent菜单→【编辑】→【MCP】，启用该服务器。
已有助手界面的版本在当前助手的MCP工具选择器中选择它。新发一条消息，要求Agent列出本服务工具并调用inspect_inputs。
只显示“已连接”不足以证明当前助手已绑定。此GUI分支不使用Claude或Codex的注册命令。

### 4.2 Codex

将 [codex.toml](docs/hosts/codex.toml) 的服务表合并到 `config.toml`。
用户作用域适合跨项目；受信任项目作用域仅对该项目生效。以下为完整目标表：

```toml
[mcp_servers.ecommerce-image-replicator]
command = "uv"
args = [
  "--directory", 'D:\MCP\ecommerce-image-replicator-mcp',
  "run", "--no-sync", "python", "-m", "image_replicator",
  "--project-root", 'D:\MCP\ecommerce-image-replicator-mcp'
]
```

保存并重启Codex会话/客户端，在 `/mcp` 查看连接及工具；没有启用该服务时先启用。
CLI注册写用户作用域，见4.6；项目作用域使用上面的表手工合并。
依据[官方MCP文档](https://learn.chatgpt.com/docs/extend/mcp)及本机codex-cli 0.163.0的mcp帮助。

### 4.3 Claude Code

项目共享作用域的 `.mcp.json` 使用 [claude-code.json](docs/hosts/claude-code.json)：

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

此文件是消费项目配置，不是MCP安装目录的业务工作区声明。跨项目共享优先使用4.6的 `--scope user`。
`local` 为当前项目的个人配置，`project` 为项目共享配置，`user` 为用户配置；同名时local优先于project，project优先于user。
不把完整项目JSON覆盖到个人配置：用户作用域 `.claude.json` 仅合并目标mcpServers子项。
重启会话，在 `/mcp` 中检查服务；项目服务按提示批准可信配置，再确认当前会话可见工具。
依据[Claude Code官方文档](https://code.claude.com/docs/en/mcp)及本机2.1.303的mcp add帮助。

### 4.4 Claude-3p（Claude Desktop第三方推理模式）

这是Desktop的设备级用户本地服务器配置，不是Claude Code的project/local作用域。
在第三方模式的【Settings】→【Developer】中编辑本地MCP配置 `claude_desktop_config.json`，
将以下 [claude-3p.json](docs/hosts/claude-3p.json) 的目标mcpServers项合并进去：

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

保留原第三方推理提供商、模型及认证配置，不把本块写入managedMcpServers或推理配置窗口。
保存后完全退出并重开Claude-3p，在Developer的本地服务器状态中确认启动，
在新会话的连接器/工具选择中启用该服务；若连接失败，查看该服务器stderr日志，先复跑第3节stdio检查。
组织策略 `isLocalDevMcpEnabled` 必须允许用户本地服务器；被管理员禁用时由管理员调整，不能用CLI绕过。
`claude mcp add` 管理Claude Code配置，不是该Desktop用户配置的注册命令。

依据[第三方模式扩展文档](https://claude.com/docs/third-party/claude-desktop/extensions.md)中User extensions，
[策略说明](https://claude.com/docs/third-party/claude-desktop/configuration#islocaldevmcpenabled)以及
[官方Desktop本地MCP配置教程](https://modelcontextprotocol.io/docs/develop/connect-local-servers)。
前两者确认3p设备级用户入口，后者确认mcpServers/command/args结构；不据此推断管理配置与用户配置可互换。

### 4.5 DSH：web、desktop、multica

核对版本：DSH及 `@deepseek-ai/dsh-mcp-client` 0.2.1-rc.2。
采用[官方MCP插件schema](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/mcp/mcp-client/README.md)
和[CLI补丁规则](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/apps/cli/README.md)。
官方插件的serverName允许1–32个字母、数字、下划线或连字符。本项目名称满足限制。
先完成目标Host自己的初始化和依赖安装；内置插件不能解析时核对该Host的运行时版本，不在MCP启动参数中追加npm安装。

以下是完整 [dsh.cordis.patch.yml](docs/hosts/dsh.cordis.patch.yml)，包含必需的insert补丁层：

```yaml
- insert:
    - id: mcp-ecommerce-image-replicator
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: ecommerce-image-replicator
        transport: stdio
        command: uv
        args:
          - --directory
          - 'D:\MCP\ecommerce-image-replicator-mcp'
          - run
          - --no-sync
          - python
          - -m
          - image_replicator
          - --project-root
          - 'D:\MCP\ecommerce-image-replicator-mcp'
```

| Host / profile | 合并目标与适用性 | 生效方式 |
|---|---|---|
| 原生DSH / `web` | 将补丁合并到web的独立cordis.patch.yml | 停止原web进程后重新 `dsh --profile web`；临时overlay见4.6 |
| DSH App / `desktop` | 同一补丁合并到App拥有的desktop profile | 完全退出并重启App；npm CLI保留desktop名称，拒绝启动和dump，不能用 `dsh --profile desktop` 替代App |
| Multica / `multica` | 同一补丁合并到Multica安装器已初始化的multica profile | 结束使用该运行时的活动任务，重启管理它的Multica daemon/宿主并新建DSH会话；不要另开第二个stdio进程冒充宿主连接 |

本机核对Multica桥接包 `@multica-ai/dsh-runtime` 0.1.0-private.2，声明DSH `>=0.2.1-rc.2 <0.3.0`，
其README提供 `dsh --profile multica --probe`（期望protocol version 1）和 `--stdio` 供宿主使用。
`--probe`只证明桥接发现，不证明本MCP工具可调用。不同Multica版本须满足其桥接包声明，不能将web模板覆盖multica的bundle列表。

补丁合并：目标文件只有顶层 `[]` 时，用上面的完整列表替换；已有补丁时，在同一顶层列表追加这一insert项。
已存在同id或同serverName时就地更新原条目，不再insert。保留已有插件、注释、`!!js`、缩进及无关配置；不编辑共享bundle。
缺少profile时先按其Host初始化，不能用 `--from-default-profile` 重置用户已有profile。
临时 `--patch` 只在该次CLI启动生效；持久合并后不要同时再加载相同overlay。

启动后确认没有插件加载/连接错误，Agent应看到 `mcp__ecommerce-image-replicator__inspect_inputs` 等9个工具。
权限预设若禁用工具，应按用户授权范围启用，不能直接开放所有收费工具。
该版DSH桥接Tools与Resources，但不桥接MCP Prompts；需从资源/手册获取流程，不把缺少提示模板当作MCP断连。
`--dump-config` 展示合成配置，可能包含其他插件私密字段，只在本机查看，不提交或共享完整输出。

### 4.6 适用CLI：PowerShell 7、Bash、Zsh

下面交付Codex、Claude Code、DSH三类CLI各三种Shell的完整命令。先安装相应Host并核对 `--version` / `--help`。
命令面向Windows安装的MCP：PowerShell使用Windows命令；Bash示例使用Git Bash，Zsh示例使用可调用Windows `.exe` 的WSL/MSYS环境。
后两者须在PATH中找到Windows版codex.exe、claude.exe、dsh.exe、uv.exe；不要把Windows安装目录交给Linux原生uv。
Windows客户端与Windows uv继承各自Windows配置作用域；此处 `D:/...` 是传给Windows进程的绝对路径。
原生macOS/Linux安装须先按该平台安装本项目，并把两处安装路径改为该平台真实绝对路径，不能照抄D盘路径。
引号保护空格，Shell变量始终双引号引用；无密钥参数，无Host env注入。

先在Host中检查同名项并保留私有备份。以下add命令用于没有同名项的首次注册；已有项采用4.2/4.3就地合并，不先remove。
Codex写用户作用域；Claude明确使用user以满足多项目复用，需项目共享时只将scope改成project并在目标消费项目执行。
get展示的是注册配置；`claude mcp list` 和会话 `/mcp` 才进一步检查连接，不能用注册成功代替工具可用。

#### Codex · PowerShell 7

```powershell
$ErrorActionPreference = 'Stop'
Get-Command codex,uv -ErrorAction Stop | Out-Null
codex --version
if ($LASTEXITCODE -ne 0) { throw 'Codex不可用' }
codex mcp add ecommerce-image-replicator -- uv --directory 'D:\MCP\ecommerce-image-replicator-mcp' run --no-sync python -m image_replicator --project-root 'D:\MCP\ecommerce-image-replicator-mcp'
if ($LASTEXITCODE -ne 0) { throw 'Codex注册失败' }
codex mcp get ecommerce-image-replicator --json
if ($LASTEXITCODE -ne 0) { throw 'Codex配置查询失败' }
```

#### Codex · Bash（Git Bash）

```bash
(
  set -eu
  command -v codex.exe >/dev/null
  command -v uv.exe >/dev/null
  codex.exe --version
  codex.exe mcp add ecommerce-image-replicator -- uv --directory 'D:/MCP/ecommerce-image-replicator-mcp' run --no-sync python -m image_replicator --project-root 'D:/MCP/ecommerce-image-replicator-mcp'
  codex.exe mcp get ecommerce-image-replicator --json
)
```

#### Codex · Zsh（Windows进程互操作）

```zsh
(
  set -eu
  command -v codex.exe >/dev/null
  command -v uv.exe >/dev/null
  codex.exe --version
  codex.exe mcp add ecommerce-image-replicator -- uv --directory 'D:/MCP/ecommerce-image-replicator-mcp' run --no-sync python -m image_replicator --project-root 'D:/MCP/ecommerce-image-replicator-mcp'
  codex.exe mcp get ecommerce-image-replicator --json
)
```

#### Claude Code · PowerShell 7

```powershell
$ErrorActionPreference = 'Stop'
Get-Command claude,uv -ErrorAction Stop | Out-Null
claude --version
if ($LASTEXITCODE -ne 0) { throw 'Claude Code不可用' }
claude mcp add --transport stdio --scope user ecommerce-image-replicator -- uv --directory 'D:\MCP\ecommerce-image-replicator-mcp' run --no-sync python -m image_replicator --project-root 'D:\MCP\ecommerce-image-replicator-mcp'
if ($LASTEXITCODE -ne 0) { throw 'Claude注册失败' }
claude mcp get ecommerce-image-replicator
if ($LASTEXITCODE -ne 0) { throw 'Claude配置查询失败' }
```

本机claude.exe 2.1.303保留 `--` 后的参数。若使用npm包装入口且出现 `--directory` 被Host解析的错误，
先核对 `Get-Command claude -All`，使用该安装实际存在的claude.cmd执行同一命令，不能删除分隔符或改传密钥。

#### Claude Code · Bash（Git Bash）

```bash
(
  set -eu
  command -v claude.exe >/dev/null
  command -v uv.exe >/dev/null
  claude.exe --version
  claude.exe mcp add --transport stdio --scope user ecommerce-image-replicator -- uv --directory 'D:/MCP/ecommerce-image-replicator-mcp' run --no-sync python -m image_replicator --project-root 'D:/MCP/ecommerce-image-replicator-mcp'
  claude.exe mcp get ecommerce-image-replicator
)
```

#### Claude Code · Zsh（Windows进程互操作）

```zsh
(
  set -eu
  command -v claude.exe >/dev/null
  command -v uv.exe >/dev/null
  claude.exe --version
  claude.exe mcp add --transport stdio --scope user ecommerce-image-replicator -- uv --directory 'D:/MCP/ecommerce-image-replicator-mcp' run --no-sync python -m image_replicator --project-root 'D:/MCP/ecommerce-image-replicator-mcp'
  claude.exe mcp get ecommerce-image-replicator
)
```

#### DSH · PowerShell 7

先将4.5的完整补丁保存为自己选定编辑工作目录内的 `ecommerce-image-replicator.patch.yml`（UTF-8）。
该路径是临时overlay文件，不是私有Host配置路径。命令针对已初始化的web profile，且目标服务尚未持久合并：

```powershell
$ErrorActionPreference = 'Stop'
Get-Command dsh,uv -ErrorAction Stop | Out-Null
$McpOverlay = (Resolve-Path -LiteralPath './ecommerce-image-replicator.patch.yml' -ErrorAction Stop).Path
dsh --version
if ($LASTEXITCODE -ne 0) { throw 'DSH不可用' }
dsh --profile web --patch $McpOverlay --dump-config
if ($LASTEXITCODE -ne 0) { throw 'DSH配置合成失败，停止启动' }
dsh --profile web --patch $McpOverlay
if ($LASTEXITCODE -ne 0) { throw 'DSH启动失败' }
```

#### DSH · Bash（Git Bash）

```bash
(
  set -eu
  command -v dsh.exe >/dev/null
  command -v uv.exe >/dev/null
  command -v cygpath >/dev/null
  test -f './ecommerce-image-replicator.patch.yml'
  mcp_overlay=$(cygpath -w "$PWD/ecommerce-image-replicator.patch.yml")
  dsh.exe --version
  dsh.exe --profile web --patch "$mcp_overlay" --dump-config
  dsh.exe --profile web --patch "$mcp_overlay"
)
```

#### DSH · Zsh（WSL，Windows进程互操作）

```zsh
(
  set -eu
  command -v dsh.exe >/dev/null
  command -v uv.exe >/dev/null
  command -v wslpath >/dev/null
  test -f './ecommerce-image-replicator.patch.yml'
  mcp_overlay=$(wslpath -w "$PWD/ecommerce-image-replicator.patch.yml")
  dsh.exe --version
  dsh.exe --profile web --patch "$mcp_overlay" --dump-config
  dsh.exe --profile web --patch "$mcp_overlay"
)
```

DSH的CLI操作是“合成检查→带overlay启动”，不是永久注册；停止进程后overlay失效。
永久使用按4.5合并profile并从原Host重启。desktop不使用此CLI分支；Multica的桥接由原宿主管理，
不得把上述web启动命令机械替换成multica后留下孤立进程。
Cherry Studio与Claude-3p使用本节GUI流程，没有交付虚构的专用CLI注册命令。

### 4.7 验证范围及成员接入检查

配置与CLI依据、隔离验证见 [Host交付核对记录](docs/HOST-CONFIG-VALIDATION.md)。
模板均已交付，静态解析、参数一致性和CLI注册/配置合成与GUI端到端分别记录。
本次不改成员真实Host配置、不调用收费API。完成自己的配置后，逐项检查：

1. MCP启动日志无错误；9个工具可发现，当前会话已启用该服务。
2. 用真实消费项目绝对路径调用inspect_inputs；文件缺失应返回可解释的检查结果。
3. Resources/Prompts按Host各自能力检查；DSH不支持Prompts，不能要求它显示提示模板。
4. 后续生成仍按第8节确认输入与预算；不能为测试连接自动提交绘图。

## 5. 启动排障与更新

```powershell
uv --directory 'D:\MCP\ecommerce-image-replicator-mcp' run --no-sync python -m image_replicator --project-root 'D:\MCP\ecommerce-image-replicator-mcp'
if ($LASTEXITCODE -ne 0) { throw '服务退出失败，检查 stderr。' }
```

启动不安装、构建或升级；等待协议输入时没有普通输出是正常行为。v0.1.3的三项限制可选，默认不限制。已发布v0.1.2收费执行前须追加
`--max-batch-images N --max-request-bytes B --max-output-tokens T`，N/B/T 由操作者填写正整数，
不代表经供应商确认的上限。旧版下载额外域名通过重复 `--download-host` 显式允许；当前源码只有显式名单才限制域名。

### 执行预算预检、配置与原任务恢复

v0.1.3采用默认不限制的 `execution_limit_policy=opt-in-v1`。input-contract中的batch_images、request_bytes、output_tokens为null表示未启用应用限制；正整数表示对应限制已启用。

| 资源字段 | 可选启动参数 | 用途 |
|---|---|---|
| batch_images | --max-batch-images | 分析批次图数上限 |
| request_bytes | --max-request-bytes | 请求体字节上限 |
| output_tokens | --max-output-tokens | 上游max_tokens；省略时采用供应商默认 |

三项独立可选，无需一次配置齐全；显式配置只接受正整数，0、负数或非法值报错。默认模板可在授权与凭据就绪后直接执行，不需业务人员逐项填值。
供应商/模型限制、输入文件限制、并发和修订额度、域名权限及绘图授权依然生效。这些参数不是总费用上限，也不是本次选图数量。
如有运维限额需求，在当前Host/profile目标服务的args中按需追加 `--max-batch-images N`、`--max-request-bytes B` 或 `--max-output-tokens T`，N/B/T替换为操作者确定的正整数。
每个参数和数值各占一个args元素；保留其它配置，只处理实际使用的profile，不批量改写全部Host配置。
重启该Host管理的MCP子进程后，从当前连接重新读取资源，确认指定限制生效，未配置项为null，工作区和state_directory保持预期。
已有任务先get_run，然后沿原run_id执行恢复；无需重写增量或重新prepare，不重复生成已成功产物。

已发布v0.1.2及更早版本没有该策略标识，仍是默认0、执行前要求三个正值的旧行为。
旧实例预算为0时，须升级到包含opt-in-v1的实际发布版本，或在旧配置中补齐三个正值并重启；不能把旧版0解释为不限制。
此改造未更新任何已发布标签或附件。消费Agent无需翻源码或遍历宿主配置，直接按资源策略向操作者说明版本差异即可。

### 其它限额按需启用（v0.1.3）

资源operational_limit_policy为opt-in-v1时，input_bytes、download_bytes、download_hosts、poll_timeout、http_timeout及default_concurrency/default_max_visual_revisions缺省均为null。
可选启动参数--max-input-pixels（正整数像素）、--max-input-bytes、--max-download-bytes使用正整数字节，--poll-timeout、--http-timeout使用正整数秒；省略即不限制。
--download-host可重复，省略不限制域名名单，指定后仅允许所列域名（不再自动附加默认两域名）；始终保留公网HTTPS、无URL凭据、443端口及禁止自动重定向检查。
新任务concurrency默认null，显式正整数才限制并发；max_visual_revisions默认null，显式非负整数才限制修订次数，0禁止修订。legacy_revision_budget同样缺省null。
新任务不再有并发8/修订5的任意上限；旧任务冻结值及既有谱系额度仍有效。修改启动项后只重启当前Host/profile，复读资源并沿原run_id恢复。
文案/说明/事实/证据的任意长度上限已取消，必要时通过文件/请求字节预算限制总体体量。
供应商技术边界、权限/路径/哈希/格式校验、同工作区单执行锁和有限自动重试策略仍生效；不是无限自动收费重试或无条件自动验收。
完整清单见[运行限制审计](docs/OPERATIONAL-LIMITS.md)。已发布v0.1.2仍遵从旧限制，需升级实际服务才能采用新策略。

### 从 v0.1.4 升级到 v0.1.5

先停止所有Host管理的本服务子进程，避免SQLite/WAL备份时仍有写入。记录旧配置，保留原project-root/state-dir、允许根、工作区模式和所有显式配置的限制；v0.1.5无需新增必需参数。
保持现有业务目录不移动，固定模式保留原--workspace；已使用任务模式的继续原配置。此次升级不要求切换工作区模式。

以下在普通PowerShell执行。按实际情况编辑业务目录列表；备份目录不能放进被备份目录。
已有自定义state-dir时也加入列表。目录含junction/symlink时先停止，单独核对真实目录；不要把跳过链接的备份当成完整备份。

```powershell
$ErrorActionPreference = 'Stop'
$ProjectDir = 'D:\MCP\ecommerce-image-replicator-mcp'
$DataDirs = @('D:\EcommerceImageReplicator') # 改成实际原目录，可列多个
$ExpectedCommit = 'b1c1bd1bcdba05ec50ec5e33a83797c90ec5751f'
$ExpectedRepository = 'https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp'
$Origin = git -C $ProjectDir remote get-url origin
if ($LASTEXITCODE -ne 0) { throw '无法读取origin' }
$Origin = $Origin.Trim().TrimEnd('/') -replace '\.git$', ''
if ($Origin -notin @($ExpectedRepository, 'git@github.com:tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp')) {
    throw 'origin与正式仓库不一致，停止核对'
}
$Changes = git -C $ProjectDir status --porcelain
if ($LASTEXITCODE -ne 0 -or $Changes) { throw '源码有改动/未跟踪文件或状态检查失败，先保留并处理' }
$PreviousCommit = git -C $ProjectDir rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw '无法记录旧提交' }

$State = Join-Path $ProjectDir '.replicator'
if (Test-Path -LiteralPath $State) { $DataDirs += $State }
foreach ($Dir in $DataDirs) {
    $RootItem = Get-Item -LiteralPath $Dir -Force -ErrorAction Stop
    if (!$RootItem.PSIsContainer -or ($RootItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "不是普通目录：$Dir"
    }
    $Links = Get-ChildItem -LiteralPath $Dir -Recurse -Force -ErrorAction Stop |
        Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }
    if ($Links) { throw "目录含链接，请先核对：$Dir" }
}
$Backup = Join-Path 'D:\MCP-backups' ('replicator-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $Backup -ErrorAction Stop | Out-Null
$Sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
icacls $Backup /inheritance:r /grant:r "*${Sid}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw '备份权限设置失败' }
$PreviousCommit | Set-Content (Join-Path $Backup 'previous-commit.txt') -Encoding utf8
$DataDirs | Set-Content (Join-Path $Backup 'data-directories.txt') -Encoding utf8
$EnvFile = Join-Path $ProjectDir '.env'
$EnvHash = $null
if (Test-Path -LiteralPath $EnvFile) {
    $EnvHash = (Get-FileHash -LiteralPath $EnvFile).Hash
    $EnvAcl = (Get-Acl -LiteralPath $EnvFile).Sddl
    Copy-Item -LiteralPath $EnvFile -Destination (Join-Path $Backup '.env') -ErrorAction Stop
    $EnvAcl | Set-Content (Join-Path $Backup 'env-acl.txt') -Encoding utf8
}
for ($i=0; $i -lt $DataDirs.Count; $i++) {
    robocopy $DataDirs[$i] (Join-Path $Backup "data-$i") /E /COPY:DAT /DCOPY:DAT /XJ /R:1 /W:1 | Out-Null
    if ($LASTEXITCODE -ge 8) { throw '数据备份失败' }
}
Write-Host "备份位置：$Backup；旧提交：$PreviousCommit"

git -C $ProjectDir fetch origin tag v0.1.5
if ($LASTEXITCODE -ne 0) { throw '获取标签失败' }
$Target = git -C $ProjectDir rev-parse 'v0.1.5^{commit}'
if ($LASTEXITCODE -ne 0 -or $Target -ne $ExpectedCommit) { throw '发布提交不匹配' }
git -C $ProjectDir switch --detach --no-overwrite-ignore v0.1.5
if ($LASTEXITCODE -ne 0) { throw '切换失败，保留数据并停止' }
uv --directory $ProjectDir sync --locked --no-dev
if ($LASTEXITCODE -ne 0) { throw '锁定安装失败，不启动' }
if ($EnvHash) {
    if ((Get-FileHash -LiteralPath $EnvFile).Hash -ne $EnvHash -or (Get-Acl -LiteralPath $EnvFile).Sddl -ne $EnvAcl) {
        throw '.env内容或ACL变化，请保留现场核对'
    }
}
uv --directory $ProjectDir run --no-sync python scripts/smoke.py --project-root $ProjectDir
if ($LASTEXITCODE -ne 0) { throw '协议复验失败' }
Write-Host '安装及发现检查通过；请合并Host配置并按第8节查询旧任务。'
```

备份副本使用受限备份目录权限，数据复制没有承诺克隆原ACL；原文件ACL不修改，`.env`原SDDL另存供核对。
备份不进Git。任一步失败不执行后续步骤，不使用reset/clean、删除数据库或重建工作区代替恢复。
若继续使用固定模式，保留旧 `--workspace` 即可；任务模式已有run_id直接get_run，仅未绑定的旧thread_id需要import_run，不重新prepare旧任务。

### 回滚到已发布 v0.1.4

先停止MCP并保留升级后新增数据及索引。以下仅针对已核验的v0.1.4，不能用于任意历史版本：

```powershell
$ErrorActionPreference = 'Stop'
$ProjectDir = 'D:\MCP\ecommerce-image-replicator-mcp'
$OldWorkspace = 'D:\EcommerceImageReplicator' # 实际原目录，不移动
$Changes = git -C $ProjectDir status --porcelain
if ($LASTEXITCODE -ne 0 -or $Changes) { throw '存在本地改动或状态检查失败，停止回滚' }
git -C $ProjectDir fetch origin tag v0.1.4
if ($LASTEXITCODE -ne 0) { throw '获取旧标签失败' }
$OldCommit = git -C $ProjectDir rev-parse 'v0.1.4^{commit}'
if ($LASTEXITCODE -ne 0 -or $OldCommit -ne 'a77ed089de3031cbefdbd235608b6631a95d3e40') {
    throw '旧标签提交不匹配'
}
git -C $ProjectDir switch --detach --no-overwrite-ignore v0.1.4
if ($LASTEXITCODE -ne 0) { throw '源码回滚失败' }
uv --directory $ProjectDir sync --locked --no-dev
if ($LASTEXITCODE -ne 0) { throw '旧版锁定安装失败' }
uv --directory $ProjectDir run --no-sync python scripts/smoke.py --project-root $ProjectDir --workspace $OldWorkspace
if ($LASTEXITCODE -ne 0) { throw '旧版协议检查失败' }
```

回滚沿用原v0.1.4启动配置；v0.1.5无需新增必需启动参数，默认不限额和任务工作区语义相同。
保留project-root/state-dir、允许根与业务目录，按原run_id（固定模式原thread_id）查询和恢复，不删除任务索引。
验证覆盖升级前已完成/待完成任务，不代表任意未来版本数据都能降级。v0.1.4仍有后台初始化异常未记录和任务注册残留缺陷；若因此失败，保留数据并升回v0.1.5，再重启当前MCP连接恢复。

### 启动参数与保留边界

| 参数 | 类型/默认值 | 作用 |
|---|---|---|
| --project-root | 路径，必填 | 实际安装根；固定.env位置 |
| --workspace | 路径，可省略 | 给出时固定模式；省略时准备工具必传workspace |
| --state-dir | 已存在绝对目录，默认安装根 | 保存.replicator/task-registry.sqlite，重启时保持一致 |
| --allow-workspace-root | 已存在绝对目录，可重复，默认不限根 | 工具工作区须在允许根内；仍受OS权限约束 |
| --max-batch-images | 可选正整数，新策略默认null | 显式设置才限制分析批次图数；已发布v0.1.2仍默认0并阻塞 |
| --max-request-bytes | 可选正整数，新策略默认null | 显式设置才限制请求体字节数；已发布v0.1.2仍默认0并阻塞 |
| --max-output-tokens | 可选正整数，新策略默认null | 显式设置才限制LLM输出token；已发布v0.1.2仍默认0并阻塞 |
| --download-host | 可选域名，可重复；默认null | 指定时仅接受该名单；省略不限制公网HTTPS域名 |
| --max-input-bytes / --max-download-bytes | 可选正整数字节，默认null | 输入/下载大小按显式值限制 |
| --max-input-pixels | 可选正整数像素，默认null | 输入解码前检查像素上限 |
| --poll-timeout / --http-timeout | 可选正整数秒，默认null | 显式启用轮询截止/HTTP超时 |

预算由操作者按供应商协议及费用授权填写，不把示例数字当作供应商上限；发现检查不会验证这些预算。

## 6. 文件清单

Git 跟踪 src、tests、pyproject、uv.lock、脚本、CI、规范和空密钥模板。
`.venv`、缓存、构建、测试报告为生成物。业务工作区 `.replicator` 保存恢复状态和中间图像，
`artifacts` 保存最终结果。入口 `python -m image_replicator`。Release已提供源码包、wheel和摘要/来源文件，不提供额外成员ZIP安装包。源码包采用显式白名单，不包含产品图、竞品图、业务brief、任务数据库或本地证据。

## 7. 资源清单

已发布v0.1.2至v0.1.5提供9工具；v0.1.1保留固定工作区及8工具契约。当前维护源码增加下表标注的2个未发布工具，共11工具；资源和提示各1个。

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
| Tool `preflight_run`（未发布） | run_id或固定模式thread_id；可选image_ids | 逐图分析缓存、文字匹配与设计预检，返回analysis/copy_status/规则来源/诊断；可能重建本地预处理图片，无供应商请求 |
| Tool `prepare_analysis_recovery`（未发布） | run_id或固定模式thread_id、request_id、updates | 仅为blocked且无绘图receipt的图准备关联恢复任务；完整delta修正及失败kind重试，不执行、不改成功产物 |

工具名称如表，Host 对模型暴露的前缀由 Host 决定。工具失败使用 isError；后台失败为
status=blocked。scheduled 只表示已安排执行，不代表生成成功，使用 get_run 查询。

### 参数、返回与调用约定

工具均返回结构化对象；精确类型、必填项、嵌套字段和枚举见从实际SDK发现导出的
[已发布v0.1.2契约快照](docs/MCP-CONTRACT-v0.1.2.json)；v0.1.3新增的null限额语义以当前资源与工具发现为准。prepare_inputs是无参数Prompt；input-contract是JSON Resource；
资源模板无。Tool结果的业务字段并非全部由outputSchema严格枚举，以下说明实际返回，不能把任意dict当业务成功。

| 参数/结果 | 规则 |
|---|---|
| workspace | string；inspect_inputs/prepare_run在任务模式必填，固定模式可省略；import_run始终必填 |
| run_id / thread_id | string或省略；后续工具必须二选一；thread_id仅固定模式；run_id绑定后不能改目录 |
| parent_run_id / parent_thread_id | prepare_revision父标识，二选一，同上 |
| options | 可省略/null，使用下表默认值 |
| image_id | get_design必填string；取inspect_inputs返回值，不猜图片序号 |
| index / task_id | reconcile_submission必填；index为从0开始的整数且在任务范围内，task_id为核实过的供应商编号 |
| report | record_review必填对象；使用契约review_schema，包含图片/参考/成图/设计哈希及完整检查项，不能用空报告验收 |
| updates | prepare_revision必填非空数组；每项image_id与完整替换delta；不得重复图片ID |
| product_context / legacy_revision_budget | 修订可选对象/null；新策略旧v1预算默认null，显式非负整数；v2沿用原谱系预算 |
| inspect_inputs结果 | workspace、groups、images（稳定image_id及权威排序） |
| prepare/import/get/execute/review结果 | thread_id、run_id、workspace、status、jobs；已完成时包含artifacts等状态字段 |
| prepare_revision结果 | 新run_id/thread_id、parent_run_id及子任务状态；不提交绘图 |
| get_design结果 | plan/design_sha256，或analysis_required与missing字段；不是成图 |

| RunOptions字段 | 类型、默认值与约束 |
|---|---|
| image_model | string；默认gpt-image-2.5-flare，或gpt-image-2.5-sunburst |
| concurrency | integer/null；新策略默认null，显式正整数；已发布v0.1.2默认2；不同工作区各自使用该并发，不是实例总额度 |
| selected_image_ids | string数组或null；默认null选全部；提供时至少1项，须来自输入列表 |
| review_mode | string；manual（默认）或vision；后者可能产生额外LLM费用 |
| max_visual_revisions | integer/null；新策略默认null，显式非负整数；已发布v0.1.2默认0 |

调用示例采用“字段引用”表示从上一步取真实值，不是可以直接粘贴进Shell的命令：

| 调用 | 参数示例/取值 |
|---|---|
| inspect_inputs | workspace = 当前项目绝对目录 |
| prepare_run | workspace同上，options = 第8节JSON示例 |
| get_run | run_id = prepare_run返回的run_id |
| execute_run | run_id同上；须先确认收费授权及预算 |
| get_design | run_id同上，image_id = inspect_inputs返回的目标image_id |
| record_review | run_id同上，report = 对原图/成图/产品实查后的完整review_schema对象 |
| prepare_revision | parent_run_id = 原run_id；updates = [{image_id:目标ID, delta:完整修订增量}] |
| reconcile_submission | run_id同上，index = 对应jobs中的index，task_id = 人工核实供应商原编号 |
| import_run | 第8节旧任务示例；返回run_id后再查询 |

所有哈希和供应商编号必须来自真实任务，不以示例值伪造。复杂delta/review/product_context字段由Resource与契约快照提供，
具体产品事实及验收边界见[设计契约](docs/DESIGN-V2.md)。错误使用isError；get_run的status和jobs决定任务是否成功。

## 8. 功能说明

### 准备新任务

工作区目录必须已存在，可由Agent在获授权的项目目录内准备 references/<group>、products、brief 和可选prompts。
产品事实写brief/design.json；prompts/<group>.json是按自然顺序的一图一项增量数组；路径/样例见工作流契约。
先读取replicator://input-contract和prepare_inputs，再调用inspect_inputs确认图片ID。
下面是prepare_run的完整参数示例，路径换成实际项目；不提供selected_image_ids时选择全部，试样时务必传目标ID数组：

```json
{
  "workspace": "D:\\EcommerceImageReplicator",
  "options": {
    "image_model": "gpt-image-2.5-flare",
    "concurrency": 2,
    "review_mode": "manual",
    "max_visual_revisions": 0
  }
}
```

保存返回的run_id。先get_run确认jobs与目录，再经授权execute_run，轮询get_run；scheduled不代表生成成功。
使用返回workspace拼接artifacts的相对路径；不要拼接Agent当前目录。输入修改后重新prepare，新任务与旧任务分开。

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

### 任务级工作区与旧任务导入

v0.1.2 提供9个工具，第7节工具表按新契约更新。已发布 v0.1.1 为8个工具，无 import_run，仍需固定工作区。
省略启动 --workspace 后，Agent 必须在 inspect_inputs / prepare_run 传已有项目绝对目录，保存返回 run_id；
后续用 run_id 查询、生成、验收与恢复，prepare_revision 用 parent_run_id。旧固定模式继续兼容 thread_id。
详细调用示例、可选目录限制、索引备份和旧任务导入见[任务级工作区说明](docs/TASK-WORKSPACES.md)。
无需强制安装配套 Skill 或填写 AGENTS.md / CLAUDE.md；Agent 应先读 MCP 自带资源和提示。

旧任务恢复不调用prepare_run。把原目录及原thread_id交给import_run；以下thread_id是明确待替换的任务值，
须从原对话或任务记录取完整64位ID，不能用供应商task_id代替：

```json
{
  "workspace": "D:\\EcommerceImageReplicator",
  "thread_id": "从原任务记录取得的完整thread_id"
}
```

保存返回run_id，用get_run查询；只有用户要求继续且凭据就绪、符合当前限制策略时才execute_run。
import_run无供应商调用，不复制文件、不重绘。已完成任务返回原产物；已提交任务沿原task_id查询；未知结果不自动重提。
缺少thread_id时先找原任务记录，不创建新任务冒充恢复。新模式不扫描磁盘，也不自动识别Host当前项目。

必须同时保留安装根（或自定义state-dir）的.replicator任务索引、原工作区完整.replicator日志/checkpoint、
artifacts和输入文件。备份前停止服务并包含SQLite WAL文件。索引丢失可用原目录与thread_id重新import_run；
原工作区丢失则不能只凭索引恢复。目录移动不在本版支持范围。

## 9. 注意事项

详见 [工作流契约](docs/WORKFLOW.md)。绘图最多三次尝试，明确失败后的新提交可能再次收费；
未知提交不会重发。供应商无幂等键时，框架无法消除“受理成功但未收到ID”的不确定窗口。
停止 MCP 不撤销供应商任务，下次 execute 相同 run_id 恢复（旧固定模式兼容 thread_id）。
`.replicator` 包含业务信息和原始响应，需本机权限保护并按业务留存要求管理。
默认下载允许 ai.t8star.org、files.closeai.fans，不跟随重定向；结合部署出口限制使用。
原尺寸恢复涉及缩放，不保证像素无损；文案位置和生成质量仍需视觉验收。

预算、凭据与任务选择属于执行前提；任务模式不限根时仍只能访问运行账号有权限的目录，不是多租户沙箱。
路径拒绝相对路径、父级跳转、符号链接/junction；缩小允许根后，原任务也会重新校验并可能拒绝恢复。
当前源码轮询间隔5秒；轮询截止、HTTP超时、下载大小默认不限制，可用可选CLI参数设置。已发布v0.1.2的300秒/50MiB旧默认保持历史行为；未知提交不自动重提。
停止进程只中断本地等待，不撤销供应商绘图；保留状态并查询原任务。不要重复点击执行来绕过预算或权限错误。


### Windows并发路径误拒绝：v0.1.4已修复

v0.1.4已修复v0.1.3的Windows并发目录创建期间，普通路径与扩展前缀路径被误判不相容的缺陷。根因和稳定复现见[修复记录](docs/WINDOWS-PATH-FIX.md)。
升级实际MCP并重启当前连接，复核serverInfo版本为0.1.5及原workspace_mode/allowed_roots/state_directory；沿原run_id先get_run查看逐图状态，再恢复原任务。固定模式继续原thread_id；unknown仍须先核查原供应商task_id，不重提收费请求。
不要重建prepare_run、删除任务索引或覆盖已成功产物。真实越界、链接/junction、设备路径及持续权限拒绝仍须排查，不能作为此缺陷绕过校验。旧标签及附件不变。

## 10. 常见问题

### 分析失败应该修改哪里（当前维护源码）

先get_run再preflight_run；按phase/error_code定位，不根据ValueError或blocked猜节点。完整阶段表和操作示例见[使用手册](docs/guidebook-of-ecommerce-image-replicator-mcp.md)。

copy_replacement_unmatched用replacement_indexes、transcription和replacement_rule_source定位规则。全局默认来自冻结product_context；只对不适用图片的完整delta覆盖text_replacements，空数组表示屏蔽默认规则，其它产品属性/主题色及必要规则继续保留。修改磁盘brief/design.json或prompts不会改变旧run。

分析职责：默认由LangGraph内LLM节点请求供应商分析，不是消费Agent必须手写。有效texts/scene缺省时使用缓存或模型，显式提供时只跳过对应字段；provided不等于LLM成功。另一项已有缓存不会因为只覆盖一项就必定重做。人工覆盖必须真实核实，texts框按0..1000归一化，texts=[]不是自动OCR，scene仍限产品/品牌说明；不能为了跳过分析编造内容或改变参考构图/互动。详见使用手册“谁负责文字和场景分析”。

分析耗尽只对失败的text/visual准备新有限重试scope，成功缓存复用，活动error在成功后清除但失败历史保留。`result`经校验有效时，旧error标记不代表当前失败。schema_errors只含字段路径/错误类型，不回传模型原文或凭据。

prepare_analysis_recovery要求稳定request_id和非空唯一updates。每项必填image_id；delta可选但提供时为完整逐图替换，retry_kinds可选唯一text/visual数组（至少更改delta或指定重试之一）；allow_terminal_http_retry默认false，仅确认操作者修正终态HTTP相关配置后显式启用。终态HTTP重试不授权自动改代理/密钥。

返回preflight_failed时无恢复任务，修正内嵌诊断；recovery_prepared时返回关联子run_id，原任务及7张成功图保留。相同request_id/相同参数重复准备幂等，同ID改参数拒绝；后续跟随recovery_run_id，执行前仍需费用授权。分析LLM请求也可能收费，没有绘图receipt不代表免费。get_run在原任务逐图返回recovery_thread_id/recovery_run_id，子任务有parent_run_id。prepare_revision只用于已有成图，不能用来处理这类失败。

preprocess/本地保存/已有绘图receipt/unknown等问题不通过分析恢复绕过；沿原任务修正本地条件或核查原供应商task_id。准备前持工作区执行锁，活动执行期间拒绝恢复；不删除索引、重写原manifest或清空已成功结果。

兼容性：新版读取旧v2任务，新增记录不迁移或删除原任务；但v0.1.5及更早不识别恢复指向与retry scope。建立新恢复任务后，不混用新旧服务执行同一工作区，不承诺新恢复任务可回滚旧版执行；保留全部新旧状态交由操作者处理。

- scheduled后一直prepared：v0.1.5已修复v0.1.4的Provider初始化异常未落盘及任务注册残留。初始化失败返回blocked、phase=provider_initialization与脱敏异常类型；修正已确认的环境问题后可沿原run_id恢复。旧版需升级实际服务并重启当前连接。若仍不推进，有限间隔查询后保留原run_id和脱敏stderr，不重复execute、不重建任务、不遍历Host配置或擅自终止进程；具体原因须堆栈确认。见[后台执行诊断](docs/BACKGROUND-EXECUTION.md)。
- 执行限制/密钥错误：先识别新旧限制策略；新策略null无需补预算，显式限制或凭据修改后重启复核。
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
- 历史12张真实图像验收属于旧业务阶段；当前版本的本地、CI、安装及升级保留证据见第3节，不据此宣称本版本真实API或Host联调通过。

- git/uv命令不可用：确认安装及PATH，重新打开普通PowerShell；不要改为全局pip安装。
- `.env`空字段遮蔽用户级密钥：填入实际值，或移除需回退的字段；不能以留空表示回退。
- smoke通过但执行失败：发现不验证密钥、预算、业务目录或后端认证；按失败阶段检查，日志不贴真实密钥。
- 升级有本地修改/未跟踪文件：先备份和手工处理，不强制覆盖；重装仅重新执行锁定安装，不删除.env或任务数据。
- 旧版启动提示缺workspace：回滚需恢复--workspace；旧版无法使用run_id/import_run。
- 找不到run_id：确认state-dir未变、允许根覆盖原目录；只有索引丢失时按原thread_id导入。
- 更新配置后仍旧行为：停止并重启Host管理的实际MCP子进程；检查是否存在同名旧实例。
- stdout出现普通日志或连接关闭：stdio stdout只允许协议；检查stderr、启动命令和重复实例，不能关闭校验硬连。
- 超时/401/403：区分供应商认证与下载授权，核对运行账号及凭据来源；未知提交保持原任务身份。
- 模块或scripts/smoke.py缺失：检查checkout完整SHA和锁定安装；源码clone应包含入口，无独立Node构建步骤。

### Windows运行目录拒绝访问

v0.1.0在管理员环境首次启动时可能创建仅SYSTEM、Administrators及OWNER RIGHTS可访问的`.replicator`。v0.1.1对新目录改为继承工作区ACL；升级不会自动修复已有ACL，避免改变成员的访问策略。

若出现`Workspace runtime access denied`，先停止使用该工作区的MCP，在普通Host账号终端运行`whoami /user`记录实际SID；由管理员检查目标目录的`icacls`和`Get-Acl`。确认账号和目录后，仅授予该账号对`.replicator`及子项的修改权限，保留原ACL。不要授予Everyone完全控制，不要删除数据库或任务记录。修复后在普通权限终端重新执行协议检查，再启用Host。

`Cannot initialize workspace journal`也可能是磁盘空间或数据库锁问题，不应一律当作权限错误。保留原文件并检查相应条件。`Workspace directory not found`表示需要先创建业务工作区。

已知展示问题：已发布v0.1.1的MCP serverInfo仍显示0.1.0，发行包及SOURCE_COMMIT为正确的0.1.1版本，Windows权限修复已包含。v0.1.2 已修复版本展示并验证与发行元数据一致；不覆盖v0.1.1附件。
