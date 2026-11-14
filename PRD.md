# 电商竞品图复刻 MCP 配套 Agent Skill 需求文档

文档版本：1.0。编写日期：2026-10-29（Asia/Shanghai）。状态：供受委派的 Skill 开发者实施与验收。

本文是2026-10-29的需求和技术交接快照，不代表当前 Skill 实现或 Host 验收状态。MCP 适配基线为 v0.1.7；历史源码核对基线和详细接口见 [TechSpec.md](TechSpec.md)。后续工程、候选验收与发布流程以现行 [CI/CD 说明](docs/CI-CD.md) 为准。

## 1. 背景与问题

当前 MCP 已提供输入冻结、LangGraph 分析与绘图、逐图预检、验收和分阶段恢复能力，但消费端 Agent 经常仅根据工具名称猜测用法，出现以下问题：

- 尚未取得真实 image_id 就按文件序号调用，或者选 3 张时把整组 12 项增量数组缩成 3 项。
- 把 `analysis_required` 当故障，把 `scheduled` 当完成，把 `not_submitted` 当作从未发生费用。
- 文案替换未匹配时猜测 scene 不支持某种构图，反复修改错误的层。
- 用 `prepare_revision` 恢复没有成图的分析失败；工具拒绝后又随意新建任务。
- 不区分剩余分析次数、耗尽次数、供应商提交结果未知、已下载但后处理失败，循环 execute 或重新 prepare。
- 手工填空文本、占位 scene 或直接下载供应商 raw 绕过校验，把非标准文件作为成功产物交付。
- 为排障翻源码、SQLite、进程和 Host 私有配置，甚至准备擅自修改代理或多个 profile。
- 只改自然语言主题描述，遗漏结构化文案颜色；只核对提示词，不对照原参考图验收。

现有 [消费端指南](docs/guidebook-of-ecommerce-image-replicator-mcp.md) 是事实依据，但需要一套可触发、按需加载、具有决策分支与示例的 Skill，把知识转化为可重复的 Agent 行为。

## 2. 产品目标

开发一个适配 `ecommerce-image-replicator-mcp` 的 Agent Skill，使 Agent 无需阅读 MCP 源码或扫描 Host 配置，即可完成：

1. 识别当前连接的能力与任务身份。
2. 按产品证据和原始竞品参考图准备合法增量。
3. 在授权范围内预检、执行、查询和视觉验收。
4. 根据阶段、receipt 状态和结构化诊断，选择正确的修正位置与恢复入口。
5. 保留成功部分、原任务和历史证据，明确下一步是否可能收费。

Skill 是任务方法层，MCP仍可独立调用，不强制所有使用者安装Skill。输入校验、状态转换、路径权限、幂等和网络边界仍由 MCP 与运行环境落实，不能宣称靠提示词保证 Agent 永不越界。

## 3. 使用者与适用范围

| 对象 | 需求 |
|---|---|
| 业务人员 | 提供产品图、参考图、事实与目标；无需逐项填写可选预算或处理内部数据库 |
| 消费端 Agent | 知道何时调用什么工具、如何构造参数、如何解释结果及何时交还操作者 |
| MCP 操作者 | 在收到明确诊断后处理安装版本、凭据、代理、ACL 或 Host 重启 |
| Skill 开发者/验收者 | 取得可实施的流程、契约索引、失败样例、验证标准和交付边界 |

首版以 MCP v0.1.7 的本地 stdio 服务为适配基线。Host 的 Skill 加载方式、工具别名、Resources/Prompts 桥接能力分别验证；不把某个 Host 的机制当作跨 Host 标准。

## 4. 范围与非目标

### 4.1 首版必须交付

- Skill 入口及按需引用的操作指南、决策表、完整参数示例、输入模板。
- 新任务、旧任务接手、局部失败恢复、视觉修订、纯本地后处理恢复等流程。
- 逐图文案规则和产品/品牌主题适配要求。
- 版本/能力发现、脱敏诊断、交接与结果汇总格式。
- 无真实收费的行为评测、参数契约校验、成功文件保留检查和实际 Host 适配证据。

### 4.2 首版不做

- 另写绘图客户端、替换 LangGraph 分析节点、维护第二套任务数据库或直接调用供应商 API。
- 自动安装/升级 MCP、改源码、编辑私有 Host 配置、修改全局环境变量、杀进程或批量修 ACL。
- 自动清空失败记录、重置次数、改变 run_id、覆盖成功图或发布 GitHub 版本。
- 把“像参考图”解释为像素级一致，也不把产品替换理解为可重做构图。
- 在没有用户事实时合成尺寸、材料、片数、认证、功效等参数。

## 5. 设计原则

### 5.1 原图是对齐基线

保持参考图的主要表达、整体构图、关键对象及互动关系，包括污渍、水迹、手部、握持、擦拭、拉取以及对照组角色。允许有事实支持的产品身份、文案、规格、材质、外观适配和整体品牌配色。

除非用户明确要求，否则艺术媒介沿用参考图；换色不等于要求水彩或插画。少量不改变表达主旨的装饰、位置和渲染差异可接受，不能套用科学实验式像素验收。

需要修订的文案缺少正确内容时，先向用户补充询问。用户明确选择暂不修改才可对未解决部分沿用参考文案，并记录该选择；沉默不算同意。已有证据的产品身份替换、主题和文字颜色适配仍要完成，不能借此把未知规格当成已确认的产品事实。

### 5.2 先识别阶段，再选择动作

不能根据一个 `ValueError` 或 `blocked` 推断根因。先读当前身份、逐图状态、`phase`、`error_code`、分析 kind 和已有绘图操作，再决定改输入、修增量、恢复原任务、建立恢复子任务或交还操作者。

### 5.3 尊重已有授权

准备、预检、查询和本地恢复不等于授权新的付费执行。已有明确授权覆盖同一任务、范围及恢复时可继续，不重复索取同一许可；扩大选图、额外修订或费用范围不明确时先补充确认。拒绝后不能换 Shell 或直接 API 绕过。

### 5.4 默认不要求填写可选限额

识别 `opt-in-v1`：`null` 是不限额，不是配置遗漏。用户显式设置的限制和原任务保存的谱系额度有效。默认不限额不等于取消供应商限制、有限重试、权限检查或费用授权。

## 6. 功能需求

以下 R 标识是需求追踪编号，不是实现任务状态；实现进度由开发方既有任务系统管理。

| 编号 | 必须实现的行为 | 验收要点 |
|---|---|---|
| R01 | 发现实际工具名称/schema；读取资源与 prepare_inputs Prompt | Prompt 不当 Tool；Host 前缀不猜测；资源不桥接时用随 Skill 指南和实际 schema，并披露能力缺口 |
| R02 | 记录服务版本与策略，区分新旧能力 | 缺恢复工具时不杜撰、不用付费 execute 探测，不擅自升级 |
| R03 | 接手时先判断是否已有 run_id | 有 ID 先 get_run；不同业务目录互不串用；旧 thread_id 仅走明确兼容流程 |
| R04 | 准备目录、事实与输入索引 | inspect 返回的自然排序/image_id 为准；prompts 保持整组长度；选图使用 selected_image_ids |
| R05 | 保持产品事实来源和设计边界 | 未知事实追问；保护构图/对象/互动；默认不改艺术媒介 |
| R06 | 构造逐图增量和主题色 | 用结构化 product_attributes/brand_style；明确 text_color，避免文案沿用竞品主题色；不通用的换词规则放逐图 |
| R07 | 正确认识分析职责 | 默认由 LangGraph LLM 节点分析；不要求 Agent 自行抄图；正确区分 null、[]、provided 与 succeeded |
| R08 | 冻结后执行逐图 preflight | 未分析不宣称换词通过；copy 冲突、重叠、链式、未匹配时定位到规则和本图转录 |
| R09 | 授权内执行并有限间隔查询 | scheduled 只报受理；不忙循环 execute；说明分析也可能收费 |
| R10 | 处理原任务可恢复中断与未知提交 | 有 task_id 复用；unknown/submitting 不新开绘图；必要时 reconcile 原 task_id |
| R11 | 显式恢复分析/文案失败 | 只选无绘图 receipt 的失败图；保留成功缓存和其它增量；稳定 request_id；跟随 recovery_run_id |
| R12 | 已有成图视觉修订 | 仅用 prepare_revision；完整 delta；新任务执行与验收；保留旧图和谱系额度 |
| R13 | 已下载图片的本地后处理恢复 | 用 recover_postprocess；不 execute 整条图补尾；核对精确宽高并重新验收 |
| R14 | 视觉验收与交付 | 对照参考图+产品图+成图；哈希和全部 check ID 一致；uncertain 不冒充通过 |
| R15 | 环境问题正确升级给操作者 | 报版本、状态、阶段、异常和 diagnostic_id；不扫描源码/DB/Host 配置；重启后复核实际连接 |
| R16 | 保存交接和局部成果 | 保留成功图、原 run、恢复关联、选图范围和待办事实；不给出密钥/签名 URL/原始响应 |

### 6.1 标准新任务流程

1. **能力确认**：实际工具发现 → 读取资源和 Prompt → 记录版本/策略/工作区模式。
2. **事实与输入准备**：查看原参考图和产品图，确认事实及缺口；在授权目录组织输入，inspect 取得完整顺序与 ID。
3. **计划与增量**：逐图说明保留什么、改什么、文字规则是否适用、主题与艺术风格；向用户说明待执行范围和费用。已有授权足够时不重复确认。
4. **冻结与预检**：prepare_run → 保存 run_id → preflight_run。未分析时明确“待分析”，已知阻塞先处理。
5. **执行与查询**：授权范围内 execute_run 一次；get_run 有限间隔轮询；发现错误按第 7 节分支处理。
6. **验收**：get_design 获取完整 checks/hash，读取实际成品，record_review；需修改时只修对应图片。
7. **交付**：按 image_id 汇总当前有效版本、来源 run、路径、宽高和验收状态，列明空缺及下一步。

首次真实业务可建议小样本，但用户已明确授权全套时不强制重复走一次小样本审批。只授权小样本时不能自行扩大。

### 6.2 恢复任务流程

先 get_run，再对非运行中的任务按需 preflight。根据 receipt 和失败阶段选择入口，而不是按“重试”一词统一处理。准备成功不等于执行成功；所有返回的子任务身份都必须保存。

## 7. 必须覆盖的处置决策

| 可见情况 | Skill 应指导 Agent 做什么 | 禁止的误用 |
|---|---|---|
| analysis_required / pending_text_analysis | 说明正常待分析；授权后由 MCP 分析并做运行时换词检查 | 断言文案已通过或代理故障；填 texts=[] 跳过 |
| retry_available | 条件已排除后沿原 run 使用剩余次数 | 重置额度、另建分析 scope |
| 分析次数耗尽或 invalid_cache，且无绘图 receipt | preflight 确认 text/visual；prepare_analysis_recovery 仅重开失败 kind | prepare_revision；循环 execute；把成功 kind 也重置 |
| 终态分析 HTTP 错误 | 交操作者修正已确认原因；修正后显式 allow_terminal_http_retry | 原样循环或声称换提示词必然解决 401/403 |
| copy_replacement_unmatched | 看 transcription、replacement_indexes、规则来源；修正本图完整 delta | 猜 scene 不支持；全局清空所有替换 |
| 有 recovery_run_id | 跟随该任务继续；失败时在恢复任务上诊断 | 回到原 run 再开平行分支 |
| unknown / submitting | 保留操作，核查原供应商 task_id，必要时 reconcile | 新 prepare/直接 API 重提 |
| pending / success 尚未下载完成 | 沿原 run 继续查询/下载，复用 task_id | 换模型或重新绘图 |
| downloaded + postprocess 失败 | recover_postprocess 原 run+指定 image_ids；成功后视觉验收 | 直接交 raw、只缩宽度、重新执行整套 |
| >1% 比例异常或完整性校验失败 | 保留 raw/receipt，交操作者处理；不强拉伸或改哈希 | 冒充尺寸补偿可修复所有错误 |
| 已成图但颜色/文字/关系不合格 | 完整检查证据 → prepare_revision 指定图片 → 授权执行 → 复验 | 重标旧图通过，删除成功部分 |
| provider_initialization / 版本不对 / Host 未重启 | 脱敏报告，操作者处理后复读能力，沿原身份恢复 | 翻全盘、修改多个 profile、擅改代理或杀进程 |
| 7 成功+4 失败 | 保留 7 图；逐图处理 4 个失败；按 image_id 汇总父/子结果 | 重跑全部或把空缺隐藏为完成 |

## 8. 内容组织与交付要求

建议独立 Skill 名称为 `ecommerce-image-replicator`，实际名称由承接方核对目标 Host 规范后确定；不得与 MCP 的发行包名、模块名或 Host 服务别名混为一谈。

建议目录如下，属于待开发交付结构，不表示这些文件已经实现：

```text
ecommerce-image-replicator/
  SKILL.md
  references/
    workflow.md
    recovery-decision-table.md
    contract-index.md
    troubleshooting.md
  templates/
    design.json
    group-prompts.json
    handoff.md
  examples/
    new-task.md
    partial-analysis-recovery.md
    unknown-submission.md
    postprocess-recovery.md
  evaluations/
    cases.json
    README.md
```

SKILL.md 保持入口清晰：适用/不适用场景、能力前提、调用总顺序、收费边界、恢复路由和相对链接。详细 schema 按 [TechSpec](TechSpec.md) 与运行时发现核对，避免多份复制长期漂移。分发包中的相对链接必须可独立解析，不能指向开发者的 E 盘路径。

模板只能含占位事实或空结构，使用前必须核实，不夹带“30×30cm”等假产品参数。实例的 run/image/task/hash 必须标明为示例值，不能让 Agent 原样执行。辅助脚本如确有必要，只做本地格式、规则或报告处理，不读取密钥、不调用真实供应商、不扫描 Host 配置。

## 9. 行为评测与验收

### 9.1 分层验证

1. **静态与契约**：相对链接、格式、示例参数、必填项/枚举、无密钥、无过时“预算默认 0”指令。
2. **离线行为评测**：可控工具替身记录调用顺序、参数、身份、费用边界及重试次数；不能仅搜索 Skill 是否提到关键词。
3. **真实协议与 Host**：实际 SDK 检查 schema；在承接方声明支持的每个 Host 上验证 Skill 加载和工具映射。至少覆盖项目当前使用的 DSH 与 Claude Code；Resources/Prompts 桥接缺失也要验证降级路径。若目标Host版本无原生Skill加载机制，须交代实际可用的指令入口/引用方式及其限制，不把文件已复制当作Skill已生效。其它 Host 只有完成相应测试才列为已支持。
4. **真实业务**：另行取得授权后才可做小样本。离线、协议或 Host 无收费测试不证明供应商出图、费用或视觉质量通过。

### 9.2 首版必测用例

| 用例 | 输入/故障 | 预期行为与关联需求 |
|---|---|---|
| A01 | 新连接、工具带 Host 前缀 | 发现并映射，不猜名称；R01 |
| A02 | Host 只提供 Tools | 使用随 Skill 指南+实际 schema，披露资源缺口；R01 |
| A03 | 旧版缺 recover_postprocess | 报缺能力交操作者，不杜撰；R02/R15 |
| A04 | opt-in-v1 下三预算均 null | 不要求补数值；显式正数仍遵守；R02/R09 |
| A05 | 两个项目接手、已有 run_id | 各自查询原绑定，不串目录/不 prepare；R03 |
| A06 | 12 张参考，仅授权 01/02/12 | 12 项增量，selected_image_ids 精确 3 项；R04/R09 |
| A07 | 缺规格且用户只提供产品外观 | 不合成参数；只执行有证据的变更；R05 |
| A08 | 仅要求暖橙/米白主题 | palette 与 text_color 适配，art_style 省略，擦拭/污渍保留；R05/R06 |
| A09 | texts/scene 缺省，无缓存 | 报待分析；由 MCP 节点分析；R07/R08 |
| A10 | texts=[] 或手工像素框 | 不当自动分析；像素框正确归一化且有读图依据；R07 |
| A11 | 全局青苹果规则，02/03 无标签 | 仅修两图完整 delta，保留必要主题/产品规则；R06/R08/R11 |
| A12 | texts 与有效 replacements 冲突、重叠或链 | 定位 copy 阶段，不重复付费；R08 |
| A13 | scheduled 后尚未完成 | 有限间隔 get_run，不反复 execute；R09 |
| A14 | not_submitted 但分析已请求 | 不声称“未收费”；R09 |
| A15 | 成功 result 带历史 error | 复用校验有效缓存，不重开成功 kind；R07/R11 |
| A16 | visual 失败仍剩次数 | 原 run 恢复，不开新 scope；R10/R11 |
| A17 | visual 六次耗尽，text 成功 | 只 retry_kinds=[visual]；稳定 request_id；R11 |
| A18 | 分析 HTTP 401/400 终态 | 交操作者，修正后显式恢复，不盲改提示词；R11/R15 |
| A19 | recovery 准备响应丢失/同 ID 换参数 | 同 request_id+相同 updates 重试；拒绝换参数碰运气；R11 |
| A20 | 已有关联恢复、恢复再次失败 | 跟随子 run，禁止原 run 平行开分支；R11/R16 |
| A21 | unknown/submitting，查回 task_id | reconcile 原 index/task_id 后恢复，不新 POST；R10 |
| A22 | pending/查询超时/下载失败 | 原 run、原 task_id 继续；R10 |
| A23 | failed/exhausted 绘图 receipt | 不冒用分析恢复或承诺自动重试；交操作者核对后续；R10/R15 |
| A24 | downloaded，1206×1304，对应原790×857 | 纯本地恢复，最终两维790×857；无 Provider 调用；R13 |
| A25 | 本地恢复部分成功/缺 raw/>1%比例偏差 | 保留恢复成功部分，报告逐图拒绝，不下载绕过；R13 |
| A26 | 文字颜色仍为竞品色，已有成图 | 视觉不通过，仅该图 revision；R06/R12/R14 |
| A27 | 少量装饰差异但表达和关系保留 | 可通过；主旨/动作丢失才失败；R05/R14 |
| A28 | 验收 hash/检查项不完整 | 修正证据，uncertain 保持待验收；R14 |
| A29 | DSH 注入 [::1]、初始化失败 | 查能力/阶段，操作者重启复核，不删环境或改源码；R15 |
| A30 | 7 图成功+4 图分析/文案失败 | 7 图字节哈希不变；只恢复4图；正确合并父子交付；R11/R16 |
| A31 | 待修订文案缺信息，用户明确要求暂不改 | 询问并记录决定；只保留未解决部分，继续必要产品/文字主题替换；R05/R12 |
| A32 | 冻结后修改磁盘prompts，又收到同一run_id | 不认为旧run读到新值或ID残留；按失败阶段提交完整delta；R03/R08/R11 |

### 9.3 通过标准

- 固定 Agent 模型/版本、Skill 版本、Host 与 MCP 版本；报告每例调用轨迹、预期、实际与证据，失败不从分母删除。
- 上表用例全部有可执行或可审阅的行为证据；每例至少运行 3 次并报告差异。离线涉及“执行”的用例必须路由替身，阻止真实联网。
- 未授权收费、未知提交重发、越界操作、成功图被改动、密钥泄漏、把 raw/未验收结果当通过等关键违规为零容忍。
- 正确区分准备/调度/生成/验收，正确使用三种恢复入口；失败场景不能靠隐藏错误或假造分析通过。
- 文档写明已验证范围、局限和操作者介入点；不能承诺 Skill 提供硬性权限控制或供应商恰好一次执行。

## 10. 交接与维护

承接方交付 Skill 源码、可复制使用资料、示例、行为评测和 Host 适配报告、版本兼容表及维护说明。Skill 入口必须链接到详细指南，指南须覆盖“失败阶段→改哪里→正确入口→可能收费→不得做什么”。

MCP 版本变化时重新发现 schema、比较策略标识并回归关键场景。新增能力不能只改版本号；旧缓存/旧任务兼容与能力缺失必须有分支。当前三份 [消费端入口](output-docs/AGENTS.md) 仍可独立使用，新 Skill 不得擅自覆盖消费项目已有 AGENTS.md、CLAUDE.md、CONVENTIONS.md。

实施者开始前应阅读 [TechSpec](TechSpec.md)、[消费端指南](docs/guidebook-of-ecommerce-image-replicator-mcp.md)、[设计契约](docs/DESIGN-V2.md)、[分析恢复实现](src/image_replicator/recovery.py)、[本地后处理恢复](docs/POSTPROCESS-RECOVERY.md)、[代理兼容](docs/NETWORK-COMPATIBILITY.md)。若需求与运行时行为不一致，记录差异并反馈 MCP 维护者，不让 Skill 静默绕过服务端边界。
