# 本地验证记录

日期：2026-10-27（Asia/Shanghai）。基线为 dev 的
`56b40b92010d221970aac983e8bedf757debcb09`。以下记录为交接提交前的本地验证；
交接历史见 [HANDOFF.md](HANDOFF.md)，最终提交以 Git 记录为准。

环境：Linux，Python 3.12.14，uv 0.12.23；实际依赖见 uv.lock。
SDK：官方 MCP Python 2.3.0，协议 2026-07-28，stdio discover。
LangGraph 1.2.18，SQLite checkpointer 3.1.2，Pillow 13.0.0。

| 检查 | 结果与范围 |
|---|---|
| `uv run --no-sync python scripts/check.py` | 路由更新后退出0；格式、lint、mypy、54项测试和秘密模式检查通过 |
| `uv build --no-sources` | 退出0；源码发行包和 wheel 构建成功 |
| `pip-audit --cache-dir .cache/pip-audit` | 退出0；当前已安装依赖未发现已知漏洞 |
| 首版干净运行环境 | 解包首版 sdist，`uv sync --locked --no-dev` 退出0；独立 Python 启动 MCP，官方客户端 discover 并发现5项工具 |
| 发行包内容 | sdist 含 uv.lock；不含私有 .env、.venv 或运行数据库 |
| Git diff | `git diff --check` 无空白错误；验证阶段未创建标签或发布 |

测试涵盖自然排序与增量对应、路径越界、严格 JSON、文案框边界、密钥优先级、尺寸约束及恢复，
真实 StateGraph/SQLite 的端到端执行和重启恢复，LLM三次主模型失败后切换备用模型，
拒绝错序输出、批量限制、仅增量变更复用基础分析和未变任务，跨进程排他锁，
提交意图/未知结果保护、已知失败三次预算、下载失败不重复收费提交，HTTP传输不确定性，
未授权下载目标拒绝以及官方 SDK 客户端通过 stdio 调用和 isError 行为。

新增路由验证：两个系列在1024/1025/2048/2049/4096长边的版本选择、横竖图一致性、
预处理可保留4096长边、超限拒绝；实际图执行按预处理画布而非原图路由，所选模型持久化，
下载失败恢复不重复提交，以及旧版未知提交不会因新增路由而绕过保护。
新增变体未执行真实收费 API 验证。

本地 JUnit 与依赖审计结果保存在 `.cache/validation/`；正式 CI artifacts 保留14天。
独立安装测试环境和测试临时工作区在验证后清理；开发 `.venv` 与必要缓存保留。
秘密模式检查是针对私钥、常见令牌及非空密钥赋值的有限扫描，不是历史全量秘密审计。

没有真实收费 API 调用。Gemini 两个型号的严格 JSON、多图/容量限制、定位质量、
GPT Image Data URL 多图行为、实际尺寸和图像质量均未验证。
两个指定密钥当前均存在，仅检查名称/存在状态，没有核验供应商授权或打印值。
Windows/macOS、Windows 用户环境回退和 Host 产品联调未在本机执行。
CI/CD 文件已准备，但 GitHub 上的执行、分支保护、required checks、release 环境审批和发布
尚未配置/验证。远程服务部署不适用于本地 stdio 交付。
Beads CLI 当前缺失，因此未创建持久任务记录，也未更改已有 Dolt 远端或数据库配置。
