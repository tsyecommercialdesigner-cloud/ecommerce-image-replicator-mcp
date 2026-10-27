# 本地开发交接文档

交接日期：2026-10-27（Asia/Shanghai）。交付分支：`dev`。
本文随实现一并提交；实际交接提交以 `git log -1` 为准，不在同一提交内填写自身哈希。

后续更新：本文下方保留首版交接时状态。2026-10-27 本地已完成真实首图及剩余11张适配验证，
并实现 v2 逐图设计/验收/修订；当前契约见 [DESIGN-V2.md](DESIGN-V2.md)，实际验证范围见
[VALIDATION.md](VALIDATION.md)。下方“尚未真实调用”等表述仅适用于首版交接时点。
用户随后纠正了v2重设计方向：当前必须以原始竞品图对齐，保留污渍、手部和动作等表现元素。
进一步明确：结构保留不等于仅替换产品；产品文案、规格、材料和全图品牌配色/艺术风格允许适配，
保持主要表达和关键关系，少量创意差异可接受。当前策略 reference-creative-v1，字段与语义边界以 DESIGN-V2.md 为准。
历史重设计的“通过”不等于复刻通过；旧未提交静物修订已由执行入口阻止新增绘图。
A14只对06执行一次蓝色主题/水彩生成，用户明确接受少量装饰差异，已登记通过，旧严格判定另存。
A15已执行全部12张：8张生成、7张通过，05需修正花色文案；01/03/04/11供应商失败。按实图适配主题色、默认沿用参考艺术风格，细节和恢复证据见VALIDATION.md。

后续A16：发现精确花色改名与文字主题只在自然语言说明中，结构化texts/CSS仍保留竞品值。已新增text_replacements和brand_style.text_color，提交前解析/校验及成图专项检查；126项本地测试通过。已补齐01/03/04/11且4张通过；A15对照页现有12张，05旧图仍待修正文案。结果与合并来源见VALIDATION.md。

A17按新文字主题标准复查旧通过图：02/06/07/08/09/12已重绘并通过、替换当前展示；10原图保留。当前12张版本目录见VALIDATION.md，05仍是原有copy待修订。

A18已完成05重绘并替换当前结果，全套12张复刻验收通过。缺失修订信息先询问、用户明确继续才保留对应参考文案，同时保留产品及主题适配；详见WORKFLOW.md和VALIDATION.md。

v0.1.0已于2026-10-27正式发布，目标SHA `726efe6ad27933656ca24214806043f794450196`；PR #1、合入与标签Windows/Linux CI通过，下载附件摘要和独立安装验收通过。实际发布记录见 [v0.1.0](releases/v0.1.0.md)，最新成员步骤见MANUAL。下方保留初始交接历史，不代表当前发布状态。Beads创建任务仍缺issue_prefix；未初始化或同步其不同名远端。

## 项目目标与当前状态

Python LangGraph `StateGraph` 封装为本地 stdio MCP Server，为 Agent 提供电商竞品图复刻。
SQLite 分别保存图 checkpoint 与上游操作日志。首版已实现并完成本地替身、协议和构建验证，
尚未执行真实收费 API 调用或实际 Host 产品联调，不能当作已验证的生产图像生成服务。

Agent 工作区输入：`references/<group>/*.jpg|*.png`、`products/`、`brief/*.md`、
可选 `prompts/<group>.json`。输出为 `artifacts/`；恢复数据在工作区 `.replicator/`。
MCP 安装根与业务工作区相互独立，安装根读取 `.env`，均通过启动参数显式指定。

## 修改历史（按本次协作实际顺序）

以下是工作阶段记录，不代表每个阶段已有独立 Git 提交；实现及后续路由改动此前均留在工作区。

| 阶段 | 内容及结果 |
|---|---|
| 初始环境检查 | main 的 `5359de25c7541f4ad20668700567026ace1925f5` 只有 README/LICENSE，无可安装源码。GitHub 读取正常，未凭空生成启动配置。 |
| 切换开发分支 | 按用户要求 fetch 并切换 dev，读取 AGENTS、工程/交付规范和图像 API 文档；当时 HEAD 为 `d523bfc7bbe5e27fb21106cd11f3729e1092e845`。 |
| 文档依据澄清 | 用户明确 validation 链接属于历史记录，无需获取原件；接口文档结论可在后续实测后注明时间、范围并订正。 |
| 更新 Gemini 文档 | 从远端 dev 快进到 `56b40b92010d221970aac983e8bedf757debcb09`；新增 API-ENDPOINT-GEMINILLM.md，旧 Gemini 生图文档重命名为 API-ENDPOINT-NANOBANANA.md。这些是用户远端提交，不是本次新增实现。 |
| 需求对齐 | 用户选择 Python/StateGraph/SQLite；两类 LLM 分别描述文案与非文字画面；明确密钥名称、顺序、增量、尺寸处理和恢复要求。 |
| 数据契约确定 | 用户确认每个参考图组一个 JSON 数组，按自然顺序对应，{} 保留基础描述；供应商批量/请求体/输出预算未知，采用显式配置，真实兼容性待验证。 |
| 首版实现 | 新建 src 包、pyproject/uv.lock、测试、质量脚本、MCP 模板、README/MANUAL、工作流和验证文档、CI/CD 配置；初期23项测试，补充到40项。 |
| SDK 与依赖修正 | 官方 MCP SDK 2.3.0 使用 MCPServer 而非旧 FastMCP；修正结构化工具返回类型，实际 stdio 客户端验证通过。依赖审计发现 Pillow 12.3.0 漏洞后升级到13.0.0，复查未发现已知漏洞。 |
| 首版环境复现 | 构建 sdist/wheel，独立目录从 sdist 锁定安装无开发依赖，并通过官方客户端发现5个工具。保存云环境 install_script/start_skill 草稿；保存不等于发布。 |
| 尺寸路由扩展 | 用户补充 flare/sunburst 的 -2k/-4k 变体。按预处理画布长边 <=1024、<=2048、>2048 自动路由，最大长边从3840改为4096；保留其余尺寸约束。路由模型持久化，旧任务不因路由改变被重发。新增14项测试，总计54项通过。 |
| 本地交接 | 新增本文、更新文档入口，按用户本轮明确授权暂存、提交并推送 dev。实际提交和远端一致性由交付时 Git 检查确认。 |

## 实现导航

| 文件 | 职责 |
|---|---|
| src/image_replicator/models.py | 严格输入/输出模型、Agent增量、dataclass图状态 |
| inputs.py | 自然排序、路径校验、输入快照及稳定thread_id |
| images.py | 合法画布选择、缩放填充、尺寸路由、裁剪恢复与格式处理 |
| provider.py | Gemini结构化请求、GPT Image异步提交、查询、受限下载 |
| workflow.py | 图节点与并行、模型回退、持久尝试预算、幂等和恢复 |
| storage.py | SQLite操作日志、JSON处理和原子文件写入 |
| config.py | 安装根.env及缺失时的环境回退，不输出密钥 |
| server.py | MCP工具/资源/提示、后台任务、状态查询、未知提交对账 |
| scripts/check.py | 与CI共用的格式/lint/类型/测试/秘密模式检查 |
| tests/ | 数据契约、图流程、HTTP异常、MCP stdio及路由恢复测试 |

详细契约见 [WORKFLOW.md](WORKFLOW.md)，操作手册见 [MANUAL.md](../MANUAL.md)，
验证证据与限制见 [VALIDATION.md](VALIDATION.md)。API文档位于同一 docs 目录。

## 关键约定与恢复边界

- 自然排序按组内文件名，1、2、10；使用 inspect_inputs 获取权威顺序。增量数组长度必须精确匹配。
- texts 完整覆盖文案块数组（[] 删除文案），scene 完整覆盖画面描述，instruction 追加要求。
- 两类反推请求优先 gemini-3.8-flash，每批最多3次；再切 gemini-3.7-flash 最多3次。
  严格JSON、数量、image_id与顺序校验失败计入预算，恢复不重置次数。
- image_model 选择 flare 或 sunburst 系列；版本由预处理后实际画布长边决定。
  实际提交模型在 SQLite 中持久化，可通过 get_run 的 jobs[].model 查看。
- 绘图共最多3次POST尝试；只在明确未建立连接或供应商明确 FAILURE 时重试。
  已明确失败后的新提交可能再次收费；HTTP错误或收发超时不等于未受理。
- 提交结果未知时阻塞，不盲目重发；从供应商找回原task_id，使用 reconcile_submission 后恢复。
  无供应商幂等键，不能保证不确定窗口里的恰好一次执行。
- 已有task_id时只继续查询/下载。原始图片落盘后再后处理；返回画布尺寸不符则报错并保留原图。
- 单工作区跨进程排他执行，图内按配置并发生成；SQLite方案不面向多机共享文件系统。
- 停止MCP不会取消供应商已受理任务。保留整个工作区的 .replicator、输入快照及原图，
  用相同thread_id恢复；不要只搬checkpoint数据库而丢失操作日志和文件。

## 本地接手步骤

1. 获取实际仓库 `https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp` 的 dev，
   已有仓库先保留本地改动，再 fetch 并快进更新。核对本次交付提交，无需创建额外worktree。
2. 使用 Python 3.12 与 uv 0.12.23，在项目根执行 `uv sync --locked`。
3. 执行 `uv run --no-sync python scripts/check.py`，再执行 `uv build --no-sources`。
   本地依赖审计命令为 `uv run --no-sync pip-audit`；缓存权限受限时显式指定可写cache-dir。
4. 保留已有 `.env`；若没有，从空值 `.env.example` 复制并安全填写
   `ZHENZHEN_GEMINILLM_API_KEY` 和 `ZHENZHEN_GPTIMAGEGEN_API_KEY`。云环境绑定不会随Git迁移。
5. 准备独立业务工作区，放入自己的图片、brief和增量；使用MANUAL中的绝对路径stdio配置。
   显式配置正整数 max-batch-images、max-request-bytes、max-output-tokens；0表示禁止收费执行。
6. 先完成 inspect_inputs / prepare_run 并核对任务，再授权 execute_run。真实调用前明确费用预算，
   先用少量图片验证严格JSON、多图Data URL、尺寸、下载域名及质量，再扩大批量。

运行期 `uv run --no-sync`，不自动安装/升级依赖；日志写stderr，stdout只承载MCP。
Windows默认安装根 `D:\MCP\ecommerce-image-replicator-mcp`。Host配置只合并目标项，保留用户设置。

## 验证状态与后续工作

已通过54项本地测试、格式/lint/mypy、有限秘密模式扫描和打包；依赖版本未在路由改动时改变。
本地JUnit和审计JSON在 `.cache/validation/`，不随Git提交；可用上述命令重新生成。
Git跟踪源码、锁、测试、CI和文档；私有.env、.venv、缓存、运行数据库和生成图像不交付。

尚未验证真实收费API、模型额度/权限、严格JSON和多图上限、图像质量及4k变体真实行为。
Windows用户环境回退、Windows/macOS执行和各Host联调未在本机完成。
CI/CD文件已准备，但GitHub执行结果、分支保护/required checks及release环境审批需本地接手者核验。
release工作流在v标签触发，需通过CI；本次只推dev，不创建标签或发布。

当前云机器没有bd，因此未录入Beads任务。保留了仓库已有配置，未初始化或替换Dolt数据。
接手后按仓库Beads技能检查bd prime及实际数据库。特别注意已有 `.beads/config.yaml` 的sync远端
名称为 ecommerce-image-replicator，与当前Git仓库名 ecommerce-image-replicator-mcp 不同；
需核对预期归属，不能直接同步到猜测的远端。
云环境脚本草稿只存在平台配置中，本地按本仓库说明安装；云发布也不等于本地环境已验证。
