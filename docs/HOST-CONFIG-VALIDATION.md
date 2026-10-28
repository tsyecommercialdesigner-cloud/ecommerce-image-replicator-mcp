# 四类 Host 配置交付核对

2026-10-28。适用服务版本v0.1.2；这是发布后的文档补充，不修改原标签、发布目标或四个附件。
MANUAL第4节包含四类Host完整配置、DSH三profile的合并/生效方式，以及三类CLI×三种Shell的九组命令。
正式模板在[hosts](hosts)，旧标签用户直接复制在线手册即可，不必切换开发代码。

## 来源与适用范围

| Host | 本次核对依据 | 交付内容 |
|---|---|---|
| Cherry Studio | [官方操作文档](https://docs.cherryai.com.cn/advanced-basic/extensions/mcp.md)；源码提交`c40a14ba138255987f6f5019c77e5f51d80bc8d9`的[导入处理](https://github.com/CherryHQ/cherry-studio/blob/c40a14ba138255987f6f5019c77e5f51d80bc8d9/src/renderer/pages/settings/McpSettings/AddMcpServerModal.tsx)与[schema](https://github.com/CherryHQ/cherry-studio/blob/c40a14ba138255987f6f5019c77e5f51d80bc8d9/src/renderer/types/mcp.ts) | mcpServers JSON、表单映射、启用与Agent绑定；不虚构GUI产品注册CLI |
| Codex | [官方MCP文档](https://learn.chatgpt.com/docs/extend/mcp)；本机codex-cli 0.163.0的mcp add/get帮助 | TOML、用户/可信项目作用域、三Shell用户级注册及查询 |
| Claude Code | [官方MCP文档](https://code.claude.com/docs/en/mcp)；本机2.1.303的mcp add帮助 | 项目JSON、user/local/project区别、三Shell显式user作用域注册；保留`--`分隔符 |
| Claude-3p | [官方3p扩展](https://claude.com/docs/third-party/claude-desktop/extensions.md)、[3p本地MCP策略](https://claude.com/docs/third-party/claude-desktop/configuration#islocaldevmcpenabled)、[官方Desktop教程](https://modelcontextprotocol.io/docs/develop/connect-local-servers) | 设备级用户mcpServers JSON、Developer入口、重启/启用；与Claude Code及managedMcpServers区分 |
| DSH | 本机CLI和官方mcp-client均0.2.1-rc.2，实际安装包README/lib源码；上游提交`22ddee3792402c3e70ec5f86a63c3e3e895a2f60`的[插件说明](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/mcp/mcp-client/README.md)和[CLI说明](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/apps/cli/README.md) | insert补丁、serverName长度校验、三Shell overlay流程、三profile持久合并 |

Multica适用性另核对本机已安装`@multica-ai/dsh-runtime` 0.1.0-private.2的package.json、README和bundle补丁，
它组合dsh-base，声明DSH `>=0.2.1-rc.2 <0.3.0`，提供probe/stdio给宿主使用。
没有读取或复制成员的业务密钥、推理配置或会话内容。
desktop是Electron保留profile：npm CLI拒绝启动和配置dump，因此不交付虚假的desktop CLI命令。

## 验证层次

- 配置：JSON/TOML解析，五个交付文件与MANUAL代码块逐字一致；启动参数与根模板一致，没有cwd、env、收费预算或固定workspace。
- DSH：实际0.2.1-rc.2的loadOverlayPatches、composeEntries和MCP Config校验通过；附带无关条目保持不变，未挂载插件。
- CLI：临时CODEX_HOME / CLAUDE_CONFIG_DIR中的真实CLI注册通过，读取写出的配置确认参数完整、原sentinel服务保留；未修改用户真实Host配置。
- DSH CLI：临时DSH_HOME的自建空bundle profile中，真实`--patch ... --dump-config`通过；只验证合成，不启动web、desktop或Multica，不安装profile依赖。
- Shell：PowerShell代码块AST解析、Bash代码块由Git Bash语法检查；直接提取手册中的Codex/Claude Code两组PowerShell及两组Bash命令，在隔离配置中执行注册和get查询，四组均通过，全部参数及无关服务保留。Zsh命令使用显式Windows进程和WSL路径转换，已核对语法/参数设计；本机Ubuntu没有Zsh，未执行该解释器，不能宣称九组均实机执行。
- 服务协议和业务回归：沿用项目质量门禁及Windows升级保留CI。Host GUI联调与真实收费API不是本次配置交付的验证结果。

本次临时注册目录在仓库.cache内创建，finally删除；报告在`.cache/validation/host-cli.json`，
文档检查报告在`.cache/validation/host-docs.json`，四组Shell执行报告在`.cache/validation/host-shells.json`。
本地完整质量门禁145通过、1项POSIX平台跳过，格式/lint/mypy/秘密检查通过。
来源摘录仅在本地.cache/host-sources中用于核对，不纳入发布物。
安装的Host版本和文档来源已经明确；模板交付不以尚未执行GUI操作为理由省略任何Host配置。
