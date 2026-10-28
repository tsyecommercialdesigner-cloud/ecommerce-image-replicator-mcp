# v0.1.6 实际交付

v0.1.6 已于 2026-10-28 14:40（Asia/Shanghai）正式发布，目标 `1459ebd0e4b63de6bc5a75e41458846f7e6dce83`。
提供11工具/1资源/1提示，新增preflight_run与prepare_analysis_recovery。逐图报告分析缓存、规则来源、文案预检及安全阶段诊断；仅为未提交的失败图准备关联恢复任务，不自动执行，成功结果及原任务保留。
本地220通过/1项平台跳过，格式/lint/mypy/秘密检查以及Windows/Linux PR、合入、标签CI通过。7成功4失败隔离回归保留原7文件和receipt，只恢复4图，无真实收费请求。
v0.1.5→v0.1.6目标→v0.1.5隔离验证保留测试.env字节/ACL、工作区、旧任务和产物，pending receipt恢复不重复提交。该回滚验证针对升级前旧任务；新恢复指向/scope不承诺旧版执行，不混用新旧服务处理同一工作区。
隔离安装对子进程采用GitHub/PyPI直连，未改用户环境或Host配置。四个下载附件与GitHub摘要、SHA256SUMS、SOURCE_COMMIT一致；源码包锁定无开发依赖安装、wheel锁定依赖安装、stdio及两种安装的非收费恢复准备/幂等/重启绑定/保留7图验证通过。三份消费入口相对手册链接及副本一致。
无真实供应商或实际消费Host联调，未修改用户密钥、工作区、原任务或7张业务成功图。此前发布标签及附件不变；标签内文档为候选快照，实际交付说明以main在线手册为准。

[实际发布记录](releases/v0.1.6.md)。以下保留历史候选与交接记录。

# v0.1.5后分析恢复与消费手册改造（未提交、未发布）

当前维护源码提供preflight_run、prepare_analysis_recovery和explicit-pre-image-child-v1能力标识，工具增至11，资源/提示仍各1；正式v0.1.5发布仍为9工具。新增非收费的逐图文本/缓存/规则来源预检，以及只针对未提交失败图的关联恢复准备。成功清除活动error但保留历史，流程按阶段报告安全诊断。原任务有恢复指向后跳过该图，防止重复处理；恢复请求在文件锁与SQLite事务下幂等。
使用说明维护源docs/guidebook-of-ecommerce-image-replicator-mcp.md，同步副本output-docs/docs/同名文件；三份消费约定均相对链接该文件，复制时同时交付docs子目录。手册明确默认规则与逐图覆盖、冻结文件不随磁盘修改、分析恢复与视觉修订的区别。
本地220通过、1项平台跳过，格式/lint/mypy/秘密检查通过。回归模拟11张中7成功4失败，只恢复4张、原7文件及receipt/原manifest/job_result不变；包括默认规则逐图空数组覆盖、旧成功scene残留error、HTTP重试确认、并发幂等、错误无正文泄漏、stdio发现和isError结构化诊断。源码/wheel本地构建验证交付手册链接及新增模块，无发布操作。
未访问实际消费任务、密钥或7张成功图，未运行收费请求；本改造没有提交/推送或远端CI。Beads创建记录仍因issue_prefix缺失失败，原.beads/config.yaml改动保留，未初始化或修改。

# v0.1.5 实际交付

v0.1.5 已于 2026-10-28 13:35（Asia/Shanghai）正式发布，目标 `b1c1bd1bcdba05ec50ec5e33a83797c90ec5751f`。
修复后台Provider初始化失败未落盘、scheduled后始终prepared及任务注册残留；清理失败不覆盖已保存结果，启动前取消与日志写入失败有脱敏观测。
6项定向回归、完整本地201通过/1项平台跳过，Windows/Linux PR、合入和标签CI通过。
v0.1.4→v0.1.5目标→v0.1.4隔离升级回滚验证保留测试.env字节/ACL、工作区、任务索引和成功产物；pending receipt沿原身份恢复，无重复提交。
四个下载附件与GitHub摘要、SHA256SUMS及SOURCE_COMMIT一致；源码包锁定无开发依赖安装、wheel锁定依赖安装、任务/固定模式stdio，以及两种安装的初始化失败可观测和原run_id恢复检查通过。
无真实收费请求、实际消费Host联调或成员环境修改。消费端具体触发条件仍待脱敏堆栈，无效代理仅为离线复现条件。
此前发布标签与附件不变。标签内文档为候选快照，实际交付结果以main在线手册为准。

[发布核验](releases/v0.1.5.md)。以下保留历史候选和交接记录。

# v0.1.4后后台执行维护修复（未提交、未发布）

消费端报告scheduled后始终prepared。已确认Provider构造在worker异常保护与首条running写入之前，初始化抛错会缺失状态并遗留tasks注册；真实httpx无效代理协议可离线复现，但消费端具体原因仍待脱敏stderr确认。另修复close异常导致任务注册不清理，以及首次启动前取消/日志写入失败的观测边界。
6项定向回归与完整本地201通过/1跳过，格式/lint/mypy/秘密检查通过；文档配置解析及三份消费指南正文一致性通过。
尚无本补丁的远端CI、真实Host或收费调用，未修改消费端安装/配置/任务。根因与恢复边界见[后台执行记录](BACKGROUND-EXECUTION.md)。
Beads创建记录报issue_prefix缺失，未初始化或修改用户已有.beads/config.yaml。

# v0.1.4 实际交付

v0.1.4 已于 2026-10-28 12:31（Asia/Shanghai）正式发布，目标 `a77ed089de3031cbefdbd235608b6631a95d3e40`。
修复Windows并发准备图片时等价DOS/UNC路径的扩展前缀差异导致的包含检查误拒绝；保留原root表示和任务绑定，不放宽真实越界、junction、设备路径及权限检查。
Windows定向23项回归、本地完整195通过/1项平台跳过；Windows/Linux PR、合入及标签CI通过。
v0.1.3→v0.1.4目标→v0.1.3隔离升级回滚保留验证通过，测试.env字节/ACL、工作区、旧任务与产物保留，pending receipt沿原身份恢复且不重复提交。
四个下载附件与GitHub摘要、SHA256SUMS和SOURCE_COMMIT一致；源码包锁定无开发依赖安装、wheel锁定依赖安装及任务/固定模式stdio检查通过。
无真实收费API或实际Host产品联调，未修改用户私有配置。此前发布标签和附件保持不变；标签内文档为候选快照，实际交付结果以main在线手册为准。

[发布核验](releases/v0.1.4.md)。以下保留此前候选与历史交接记录。

# 本地开发交接文档

v0.1.4候选：已稳定复现并修复Windows realpath在2/3错误码竞争中保留扩展前缀导致的路径误拒绝，
保持root表示、旧run_id及安全包含校验，详见[根因记录](WINDOWS-PATH-FIX.md)。
尚未发布，已有发布标签和附件保持原样。

v0.1.3已于2026-10-28 12:01（Asia/Shanghai）发布，目标f437164d10a8a7dd7fd21bd85ee1deccf7b4533e。
PR #10/#11及修复后合入/标签Windows/Linux CI通过，下载摘要、锁定安装及默认null契约验证通过。
候选升级/回滚验证保留测试.env及ACL、任务/索引和产物；无收费调用。实际证据见[发布记录](releases/v0.1.3.md)。
以下未发布及失败记录为历史阶段，原v0.1.2标签和附件不变。

2026-10-28 未发布：进一步放开默认运行限额，清单见[OPERATIONAL-LIMITS.md](OPERATIONAL-LIMITS.md)。
新策略只对显式配置启用限制；保留旧冻结额度、提交防重复及格式/路径/公网下载等校验。

2026-10-28 未发布改造：三项执行限制改为独立可选，默认None/资源null，策略opt-in-v1；
输出token缺省时省略max_tokens。显式0/负值非法。已发布v0.1.2保持原行为，
消费指南按资源策略区分新旧实例；本次未修改任何实际Host配置或调用真实供应商。

2026-10-28 四类Host交付补正：上一轮只列“暂不交付”的部分已补为完整配置。
MANUAL第4节、docs/hosts及README同步，依据和隔离验证范围见[HOST-CONFIG-VALIDATION.md](HOST-CONFIG-VALIDATION.md)。
含DSH insert结构、desktop保留profile限制及三CLI×三Shell流程；不修改v0.1.2标签或附件。

2026-10-28 手册规范复核补充：MANUAL恢复十节并补齐配置来源、升级/回滚、Host覆盖及工具参数。
新增Windows隔离保留验证脚本与CI步骤，实际v0.1.1→v0.1.2→v0.1.1通过；报告见
[UPGRADE-PRESERVATION.md](UPGRADE-PRESERVATION.md)。这是发布后维护，不改变v0.1.2标签或附件。

v0.1.2 已完成实际发布；PR #6、合入及标签双平台CI和附件安装核验通过。
目标 `036ef5e3246ce32f23ddd8138284fc1d18f357ed`，正式交付证据见 [v0.1.2](releases/v0.1.2.md)。以下“未发布”为历史开发阶段。

2026-10-28 当前源码已改为任务级工作区（尚未提交/发布）：CLI 可省略 --workspace，
准备时显式选目录，后续按持久 run_id 路由；旧固定配置与 thread_id 恢复保留，新增 import_run。
契约见 [TASK-WORKSPACES.md](TASK-WORKSPACES.md)。本地质量门禁145通过、1项POSIX跳过，
默认模式stdio发现9工具/1资源/1提示；使用假供应商验证隔离、并发、重启续查不重复提交。
未执行真实收费调用、实际Host联调或本次远端CI；Beads仍因issue_prefix缺失无法登记任务。
用户已有 .beads/config.yaml 改动保留。以下发布记录和交接内容均为历史状态。

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

v0.1.1已发布，目标`c85f396c559411a68bdd5a2cba4bbbe858ab3245`。Windows新建运行目录继承工作区ACL，新增非零stderr启动诊断；默认业务目录D:\EcommerceImageReplicator。PR #3/#4及合入/标签双平台CI、正式附件摘要和独立安装通过，详见[发布记录](releases/v0.1.1.md)。旧ACL不自动修复，现有任务不自动迁移。

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
