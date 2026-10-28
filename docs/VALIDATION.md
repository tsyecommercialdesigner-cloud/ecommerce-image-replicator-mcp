# 验证记录

## v0.1.5 后台执行异常修复

v0.1.5 已于 2026-10-28 13:35（Asia/Shanghai）正式发布，目标 `b1c1bd1bcdba05ec50ec5e33a83797c90ec5751f`。
修复后台Provider初始化失败未落盘、scheduled后始终prepared及任务注册残留；清理失败不覆盖已保存结果，启动前取消与日志写入失败有脱敏观测。
6项定向回归、完整本地201通过/1项平台跳过，Windows/Linux PR、合入和标签CI通过。
v0.1.4→v0.1.5目标→v0.1.4隔离升级回滚验证保留测试.env字节/ACL、工作区、任务索引和成功产物；pending receipt沿原身份恢复，无重复提交。
四个下载附件与GitHub摘要、SHA256SUMS及SOURCE_COMMIT一致；源码包锁定无开发依赖安装、wheel锁定依赖安装、任务/固定模式stdio，以及两种安装的初始化失败可观测和原run_id恢复检查通过。
无真实收费请求、实际消费Host联调或成员环境修改。消费端具体触发条件仍待脱敏堆栈，无效代理仅为离线复现条件。
此前发布标签与附件不变。标签内文档为候选快照，实际交付结果以main在线手册为准。

维护Agent复核，无独立人工审批；具体CI及附件证据见[发布记录](releases/v0.1.5.md)。

## v0.1.4 Windows并发路径修复

两种Win32错误探测顺序在旧代码稳定触发误拒绝，修复后通过。Windows定向23项回归，完整本地195通过、1项平台跳过，格式/lint/mypy/秘密检查通过。
Windows/Linux PR、实际合入及标签CI通过；v0.1.3升级/回滚、发布附件摘要、源码/wheel锁定安装和stdio检查通过，临时安装已清理。
根因与边界见[修复记录](WINDOWS-PATH-FIX.md)，精确SHA、CI与附件摘要见[发布记录](releases/v0.1.4.md)。
无真实收费请求或实际Host产品联调；维护Agent复核，不是独立人工审批。仓库main未启用分支保护，本次逐项核对CI及评审后执行合并。

## 运行限制全面检查（历史阶段）

v0.1.3已于2026-10-28 12:01（Asia/Shanghai）发布，目标f437164d10a8a7dd7fd21bd85ee1deccf7b4533e。
PR #10/#11及修复后合入/标签Windows/Linux CI通过，下载摘要、锁定安装及默认null契约验证通过。
候选升级/回滚验证保留测试.env及ACL、任务/索引和产物；无收费调用。实际证据见[发布记录](releases/v0.1.3.md)。
以下未发布及失败记录为历史阶段，原v0.1.2标签和附件不变。

完整清单见[OPERATIONAL-LIMITS.md](OPERATIONAL-LIMITS.md)。本地质量门禁167通过、1项POSIX跳过，格式/lint/mypy/秘密检查通过。
新增运行限制用例7项，覆盖输入字节/像素与长brief、默认与显式下载大小和域名名单、公网HTTPS校验、
默认无修订限额及旧显式0保留、无HTTP超时；stdio资源返回完整默认null策略。
初次全量出现原有多项目恢复测试的Windows原子替换WinError5，失败XML保留在.cache/validation/operational-first-run.xml；
未修改该写入实现，随后两次全量分别167通过/1跳过。首次文件访问失败根因未确定。
三份消费指南正文/示例及本地链接检查通过；临时测试环境已清理，无真实供应商调用，无实际Host/发布变更。

# 可选执行限制验证（2026-10-28，未发布）

当前源码采用opt-in-v1，三项限制默认None/资源null；显式正整数独立生效。
本地质量门禁160通过、1项POSIX跳过，格式/lint/mypy/秘密检查通过。
新增15项用例覆盖默认Service执行、批次/字节/token独立限额、非法参数、
分析及视觉评审省略max_tokens、已完成原任务复执行不重复提交。
stdio资源确认策略及null语义；测试使用受控替身/MockTransport，无真实供应商请求。
已发布v0.1.2标签/附件与真实Host安装均未修改。以下记录保留其历史验证范围。

# 本地验证记录

## 2026-10-28 手册补齐与升级/回滚保留验证

Windows/Python3.12真实Git切换与锁定无开发依赖安装：v0.1.1→v0.1.2→v0.1.1通过。
对比.env、业务文件、SQLite/checkpoint及原产物的SHA256与Owner/Group/DACL，切换安装前后保持；
升级生成的任务索引在回滚时保留。两个替身任务分别覆盖已完成与待完成，恢复未增加提交。
实际SDK子进程完成固定模式/任务模式的发现、旧任务导入与查询；无真实供应商调用。
报告及复现范围见[保留验证](UPGRADE-PRESERVATION.md)。文档十节、JSON/TOML与模板一致性、
PowerShell示例AST解析及本地链接通过；未执行用户真实升级、Host配置或跨权限账号联调。

## 2026-10-28 任务级工作区（当前源码，尚未发布）

`uv run --no-sync python scripts/check.py`：格式、lint、mypy、秘密检查通过；145测试通过，
1项POSIX权限测试在Windows跳过。JUnit报告位于本地 `.cache/validation/pytest.xml`。
新增覆盖：同历史ID的跨项目隔离、持久绑定防篡改、允许根重检、缺失日志拒绝恢复、
并发索引写入、同目录服务复用、junction拒绝、两项目并行生成、单目录锁互不影响、
未知提交重启不重提、后台任务取消后按原供应商编号续查、修订/评审沿用父工作区。
官方SDK stdio子进程测试覆盖无固定目录启动、两项目准备、进程重启查询及旧任务导入；
原固定模式协议测试继续通过。`scripts/smoke.py --project-root .`通过：9工具、1资源、1提示，
provider_requests=0。替身结果不代表真实图片或供应商验证；未执行收费调用和实际Host联调，
本次未提交、推送、运行远端CI或发布。此前发布与真实图像证据保持原历史口径。

## 2026-10-27 A18 文案修订询问规则及05重绘（最新）

用户补充流程：缺少文案修订信息时先询问；只有用户明确选择继续不修改时，未确定部分沿用竞品参考文案。
产品身份/花色、品牌与文字主题的修改仍必须执行。规则写入Agent工作流及MCP使用说明；现有接口承担冻结、提交及验收，未虚构新的交互状态节点。
05已有明确的青苹果→橙子和橙色文字指令，无需再次询问，也未启用未确定文案回退。

126项本地测试、格式、lint、mypy与秘密模式检查通过。单独05真实提交一次，用户级环境密钥；模型和Agent实图复核均通过。
右上已为橙子/orange、主副标题与花色文字均为橙色，三份报告及放大表格结构保留。报告细小内容仅作为参考画面，未认证为用户商品事实。
验收后替换A15当前对照页05位置；最新12张目录为`.cache/validation/image05-copy-revision-20261027/current-suite/`，整套12张复刻验收通过。
旧35张图片哈希保持一致，原始任务与旧验收未覆盖；替换记录在replacement-manifest.json。

证据目录`.cache/validation/image05-copy-revision-20261027/`，含before-*、agent-reviews.json、final-status.json、summary.json及当前12张index.json。
临时测试目录已清理。Beads仍缺issue_prefix，创建失败无可关闭ID；未初始化数据库或执行Git操作。


## 2026-10-27 A17 旧验收图文字主题复查与替换

用户授权对A15已通过的旧图按新的文字主题标准复查，仅重提不符合者并替换当前结果。
实图检查02/06/07/08/09/10/12：10的标题、说明、花色标记已为橙色，保留；其余6张有明显绿色主题文案，需修订。
新标准针对本套已明确的深橙文字主题，不以HEX逐像素误差验收；产品绿叶、绿色图标与为可读性使用的白字徽标可保留。

本轮实际绘图POST 6次，范围02/06/07/08/09/12，每张一次。06本地超时后沿原task_id恢复下载，未重复提交。
6张均通过模型及Agent实图复核，原构图、关键对象、动作和默认艺术风格保留，文字已适配橙色主题。
仅在验收通过后更新A15的merged-status、merged-visual-notes及gallery；原MCP任务、冻结计划、原始结果与历史验收不覆盖。
提供`.cache/validation/text-theme-reaudit-20261027/current-suite/`，含当前12张及index.json。
05仍为此前copy待修订图，本次仅审视旧通过图，没有扩大范围重绘05。

证据目录`.cache/validation/text-theme-reaudit-20261027/`：reaudit.json、before-*快照、prior-completed-results.json、
agent-reviews.json、final-status.json、replacement-manifest.json、summary.json。旧29张图哈希保持不变，替换新图/当前目录逐张哈希一致。
本轮未改生产代码，执行前后校验与126项测试通过时的源码哈希一致，无新增临时测试环境。密钥仍使用Windows当前用户环境。
Beads建任务仍因issue_prefix缺失失败，无可关闭ID；未初始化数据库或执行Git操作。


## 2026-10-27 A16 文案、文字主题修复与缺图恢复

05并非Agent漏写替换要求，也不是出图验收失效：原instruction确有青苹果→橙子，
但最终结构化texts仍含旧花色；旧CSS还含竞品绿色，与新品牌说明并存。提交前只有结构校验，没有把修改落实为最终文案/文字颜色。
新增text_replacements并先解析到texts，拒绝未匹配、冲突、旧值残留；brand_style.text_color先覆盖文字CSS并逐块验证。
每条文案替换和文字主题分别加入成图检查，保留原构图与默认艺术风格；细微色差、白字徽标对比度等无损表达的差异可接受。
本轮Agent选择深橙#C96A23。126项本地测试、格式、lint、mypy及秘密模式检查通过。

重新查询旧任务确认01/03/04/11均FAILURE后，仅这4张各提交一次真实绘图，使用Windows当前用户环境密钥。
4张均生成，模型与Agent实图复核通过；01曾超过本地轮询期限，随后恢复原任务下载，没有重提。
新图已复制到A15原artifacts目录补齐空缺，并更新原gallery.html。现有12张，11张通过；05保留旧图及copy待修订状态，本轮没有重绘05。
原25张图片哈希不变（既有17张+A15已出8张）。原MCP任务、冻结计划及final-status.json不改写；
合并展示另存merged-status.json/merged-visual-notes.json，merge-manifest.json逐张记录来源任务及哈希。
新增字段已写入当前prompts，但旧8张不会因此自动换色；本轮真实验证仅涵盖4张缺图。

证据目录：`.cache/validation/copy-fix-recovery-20261027/`，含05-root-cause.json、05-corrected-prompt.json、
submitted-copy-audit.json、prior-failure-proof.json、agent-reviews.json、final-status.json、summary.json及merge-manifest.json。
05-corrected-prompt是本地文案/CSS回放证据（geometry为空），不是05真实绘图结果。
本次临时测试目录由质量入口finally清理。Beads仍因issue_prefix缺失无法建任务，无可关闭ID；没有初始化数据库或执行Git操作。


## 2026-10-27 A15 产品实图配色全套测试

验收采用 `reference-creative-v1`：少量创意差异只要不改变画面主旨、关键对象和互动关系即可通过。
Agent 为12张分别提交米白、橙子橙、绿叶色增量；未指定 art_style，全部继承各自参考图媒介。
未填合成产品规格。原参考图继承的参数、材质、性能和报告内容仅为复刻测试输入，并非用户商品已核实事实。

本地116项测试、ruff格式/检查、mypy通过。通过官方MCP stdio执行真实API；密钥读取Windows当前用户环境。
实际绘图POST 12次，每张1次；恢复仅查询原任务并下载，没有重复绘图。
最终8张生成：02、06、07、08、09、10、12通过；05仅copy需修订（青苹果/green apple未改为橙子/orange）。
01、03、04、11均经原任务查询确认供应商FAILURE（上游过载、超时或暂不可用），无待定任务。
供应商失败与画面验收分别统计，不将缺图称为视觉不合格，也不将全套称为全部成功。

证据：`.cache/validation/product-theme-suite-20261027/` 下 `summary.json`、`final-status.json`、
`final-provider-failures.json`、`agent-reviews.json`、`visual-notes.json`、`gallery.html`。
模型初判保留在first-pass和result记录，Agent复核通过record_review登记。
注意测试上限在HTTP前拦截4次自动重提，journal attempts=16，实际POST=12；
01/03/04/11在原journal中显示unknown属于该拦截的本地状态，真实供应商FAILURE证据及原task_id另存，未篡改历史记录。
历史17张图片、15个输入文件哈希校验通过；当前临时测试目录已清理，真实结果、原始结果、检查点保留。
Beads建任务因缺失issue_prefix失败，未初始化或修改数据库配置。未提交、推送或执行Git操作。


## 第06张蓝色主题/水彩真实小样本（2026-10-27，A14）

**后续用户决定：通过。** 用户明确绘图允许不改变表达主旨的少量创意差异，A14页眉装饰可接受。
已通过record_review登记accepted，user-acceptance.json保存决定，原严格评审/最终状态/摘要/对照页
另存strict-history版本。下文的“需修订/漏检”属于当时过严口径的历史判断，不是当前结论。

- 用户授权仅06，用户级环境变量密钥；独立工作区，selected_image_ids仅含06，自动修订预算0。
  product_attributes为空，事实仅为产品实图可观察外观，未使用A13合成产品参数。
  生产源码与上一轮113项本地通过版本的哈希一致；样本入口额外限制绘图POST最多1次。
- thread_id：`9b0ab443ab30d0f90ca396b29035479a808c6dcfb917654bad68cac7d5cac3e1`。
  task_id：`bbcf68e3a079411ba3fd4d5e57c6493c`。
- Gemini文案/非文字分析共5次请求，其中3次HTTP429上游负载饱和、2份分析最终成功；
  429的脱敏响应保存在样本工作区 `.replicator/errors/`。没有HTTP400。
- Flare-2k仅1次绘图提交，画布800×1344，成图恢复790×1337；通过已有测试允许域名
  files.anyroutes.cn下载，仅作用于本次进程，未改全局白名单。随后视觉评审1次，返回全部pass。
- Agent实图复核：蓝色主题与水彩均生效；上文下图的主构图、盘面大片污渍、两只手、扶盘和压布
  擦盘关系保留，橙子花纹与实图对应，没有新增合成材料/尺寸。
- **整图仍需修订**：页眉左上/右上新增蓝色叶片，右上花色标签下新增独立橙子/切片/叶花装饰，
  原图无这些对象。自动评审漏检，甚至将新增页眉花叶描述为匹配原结构。Agent通过record_review将
  elements、change_scope改为fail，最终needs_revision、reference_alignment_verified=false。
  原自动评审结论及成图原件保留；未重绘、未执行其它11张、未准备追加收费修订。
- 16份历史成图及原工作区输入/默认配置哈希未变。证据位于
  `.cache/validation/reference06-blue-watercolor-20261027/`：preflight.json、result.json（自动评审时点）、
  vision-review.json、agent-review.json、final-status.json、comparison.html及workspace/。
  本样本证明真实生成与哈希绑定评审可运行，也暴露了自动评审对新增装饰对象的漏检，不能宣称质量门禁可靠。
- Beads仍因issue_prefix缺失无法建任务；本次无Git操作。

## 产品/品牌增量边界（2026-10-27，A13，当前策略）

用户进一步明确：复刻保留构图、对象清单和互动关系，允许产品文案/尺寸/规格/材料等自身属性，
以及全图品牌色调/艺术风格等变化，不要求除产品替换之外像素完全相同。

- 新策略 reference-bounded-v1、解析契约 version=4；固定 edit_boundary 供生成和评审共用。
  新增 product_attributes（property/value/source）和 brand_style（palette/tone/art_style/typography）。
- 非空 objects/layout_regions/forbidden_elements 结构性覆盖在准备阶段拒绝；自定义检查及自然语言
  不可放宽结构边界。自然语言语义与 source 真实性仍需人工/模型判断，不能宣称 schema 完整识别。
- style 检查允许显式品牌配色/艺术风格差异；composition/elements/actions 仍对照原图。
  “蓝色水彩但擦除污渍/手部”必须因结构违规失败，不能由风格通过抵消。
- 当前 brief 和06/09补充检查已取消颜色硬锁，仍保留污渍、动作和对照对象身份；A12保留无品牌增量
  的默认测试语义，A13新增产品/品牌允许项及结构禁止项。尺寸/材料示例均为合成数据，不是商品事实。
- 113项本地测试通过（含官方 MCP SDK stdio 的边界资源/schema检查、准备阶段拒绝路径）；
  本地替身验证传参与状态处理，不证明真实模型语义遵循或视觉质量。格式/lint/mypy通过。
- 旧策略保持原操作身份、历史产物和恢复行为；reference-first-v1 未提交任务不得作为新策略执行。
  证据归档于 `.cache/validation/product-brand-boundary-20261027/`，没有新增收费调用，也未执行Git操作。
- Beads创建任务因 issue_prefix 缺失失败，未擅自初始化数据库。

## 参考图优先纠正（2026-10-27，A12）

以下保留上一轮记录；其中将配色/风格一律固定的表述由上述A13边界取代。

用户明确指出此前偏离复刻目标。复核原图：06是污渍盘擦拭，08含展示卷和包装卷及拉布手势，
09是污渍布与旧灰抹布对比，11是四格擦拭演示。因此下文A11的“通过”只适用于当时错误的重设计
标准，不能证明复刻质量；该评价口径已撤回，历史记录不删除。

- 新任务标记 reference-first-v1，生成始终携带完整参考图；拒绝 layout/rebuild。
- 对照评审携带原始参考图、成图及产品图，新增原图哈希绑定；保留污渍、水迹、手部、演示动作
  和比较对象，检查构图、元素、动作、风格、文案、主推产品身份及局部修改范围。
- 移除本项目默认的暖米重配色、静物化、去污渍等要求；当前 prompts 使用原图基线，06/08/09/11
  增加针对参考图的检查。旧输入在 `.cache/validation/reference-first-20261027/before/` 备份。
- 98项本地测试通过；覆盖原图像素始终送入生成、原图/成图/产品图在评审中的顺序和哈希、
  原图被改动拒绝、移除参考图的模式拒绝、旧未提交重设计拒绝、旧任务失败不得再POST，以及历史
  accepted 不被报告为 reference_alignment_verified。格式/lint/mypy通过。
- 在隔离数据库副本上恢复三个v1和一个历史v2已完成任务，返回1/1/11/3份原结果，禁用供应商访问
  仍成功；16份历史成图及12张参考图和1张产品图哈希一致。历史11号未提交静物修订在加载密钥前被拒绝。
  证据保存在 `.cache/validation/reference-first-20261027/` 的 pytest.xml、verification.json 和 before/。
- 本轮无新收费API调用。新验收schema和真实复刻相似度尚未实测；测试通过不等于实图质量通过。
- Beads建任务仍因issue_prefix缺失失败，未重建数据库或执行Git操作。

## 历史重设计实测（2026-10-27，A11；非复刻验收）

- 仅执行08、09、11；首图及其他图片均未重复生成。用户级环境变量密钥，独立工作区，
  files.anyroutes.cn 仅在本次启动白名单。官方 MCP stdio prepare/get_design/execute/get_run 路径执行。
- thread_id：`0beaab10fc12e77974d6133f643751c319459a88cc5819c7f3147fa6dda461a9`。
  3次 Flare-2k POST、0次反推、3次视觉评审请求；3张生成尺寸全部匹配，未重试绘图。
  与原流程同样三图需6次反推相比，本样本消除了被完整增量覆盖的分析调用；评审是额外且独立的调用。
- 08：task `4a387e00c8bc4a74b2a3d986998b41ce`；layout策略，单卷、单个可见卷端及连续展开，
  Gemini评审和Agent目视均通过。
- 09：task `b3a04f7cc0f3472387d8483fa9578211`；layout策略，右卡已正确显示水平折叠平放，
  Gemini评审和Agent目视均通过。
- 11：task `8c1d9c1f354f4815af4464a524f49df8`；rebuild策略，手部和擦拭动作已消除。
  视觉评审收到429，脱敏响应为“当前分组上游负载已饱和，请稍后再试”，进入 review_required，未自动重试。
  Agent目视发现右上水槽配“锅具旁”、左下木桌配“水槽边”。原因是测试用例新scene顺序与继承texts不一致，
  通过 record_review 将 custom_2 标为fail，最终运行状态 needs_revision，没有把生成成功当作验收通过。
- 已修正11用例中的场景/对象/区域语义顺序，与 texts 绑定为左上餐盘旁、右上锅具旁、左下水槽边、右下木台面。
  prepare_revision 已仅冻结11，子 thread_id：
  `d1304dcea06cbdb7de87b19513b977da9f0da7967613912f0316206d1a94c41f`。
  状态 prepared，预留1份谱系预算，尚未 execute，新增API调用为0；08/09不在子任务内。
- 证据：`.cache/validation/adaptation-v2-live-20261027/` 中 result.json 保存模型阶段原结果，
  agent-review.json 与 final-status.json 保存人工判断后的状态，prepared-revision-11.json 保存修订，
  comparison.html 可对照旧图/新图。历史13份成图哈希保持一致。
- 本样本验证了两份视觉评审严格schema成功、一次评审错误转人工路径和真实 artifact/plan 哈希绑定。
  未证明自动评审的整体准确率、更多尺寸/模型、供应商负载容量或完整12张新流程质量。

## LangGraph v2 改造本地回归（2026-10-27）

- 新增结构化目标方案、按需分析、full/layout/rebuild 参考策略、逐图 checkpoint/落盘/验收，
  以及 get_design、record_review、prepare_revision。官方 stdio 客户端发现8项工具并验证新接口拒绝路径。
- 88项测试通过；ruff format/check、mypy（13个源码文件）、显式49文件范围的有限秘密模式检查，
  改动文档链接与 JSON 示例检查通过。未更换依赖或锁文件。
- 覆盖完整增量零反推、仅缺字段分析、部分失败可见成图、旧图复用、稳定ID筛选/插入、视觉不确定性、
  成图与目标方案哈希绑定、文件改动拒绝、兄弟分支共享预算、修订批次原子预留和 unknown 不得绕过。
- 完整回归发现并修复同内容图片并发预处理时的 Windows 文件替换冲突；v2 预处理路径按图片身份区分。
  同图两类分析用 gather 等待各自持久化再传播失败，避免取消的同伴分支在恢复时才首次发出请求。
  两项并发回归另连续重复3次通过。
- 在真实历史数据库的隔离副本上恢复三个 v1 已完成 checkpoint，返回1、1、11份原产物，
  禁用供应商方法仍成功，0 API调用；历史13份成图哈希一致。原数据库和成图未重写。
- 本地证据：`.cache/validation/adaptation-v2-20261027/` 下 local-result.json、pytest.xml、
  migration-result.json、historical-output-hashes.json、plan-preview.json。API实测另行记录，不混为本地结果。
- Beads 建任务仍因 issue_prefix 缺失失败；保留数据库与远端配置，未执行 Git 操作。

## 剩余 11 张增量适配实测（2026-10-27，A10）

逐张查看 02～12 后编写独立 texts/scene/instruction，保存于
`brief/cases/A10-remaining11-adaptation.md` 与对应 JSON，并更新主 prompts 数组第 2～12 项。
第一项及已通过首图保持不变。隔离工作区只含 02～12；输出序号 001 对应原图 02，映射见报告。

- 状态 completed，22 次 Gemini 分析、11 次绘图提交，未触发重试；11 张输出尺寸全部匹配参考图。
  图 02 使用 Flare 基础版本，其余 10 张为 Flare-2k，按实际画布路由。
- thread_id：`faa2259a59fcbb5b5fdb8faf6221239500ee6494694aab868703304d240e76f1`。
- 用户级密钥；并发 2；单图分析批次；沿用已授权测试下载域名。首图未提交，成图 SHA-256 不变。
- 核心文案、橙子花色和暖米色调均生效。检测报告页改成设计细节卡，竞品数值和性能结论移除。
- 视觉未全部通过：08 多出卷装端结构；09 右侧画成悬挂展开而非折叠；11 仍保留擦拭姿态，
  未完全遵守静态陈列要求。另 06 布面接触盘面，而非严格摆在盘旁。均已保留原结果，未追加生成。
- 本轮未修改业务源码；与此前通过 66 项测试的源码哈希一致。完成增量 schema、输入清单、
  文件哈希、尺寸和逐图目视检查；未做像素级 OCR/定位评分。
- 本地证据与逐图报告：`.cache/validation/remaining11-20261027/result.json`；
  对照预览：同目录 gallery.html；suite/ 按原图序号汇集首图副本和本轮 11 张，均为原字节复制。
  原始输入、历史产物、数据库和 task_id 保留。测试进程已退出，没有新增临时环境。
- Beads 仍因 issue_prefix 缺失无法创建任务；未初始化或修改数据库、未执行 Git 操作。

## Agent 增量适配首图（2026-10-27，A09）

用例与依据：`brief/cases/A09-product-adaptation.md`；增量对象：
`brief/cases/A09-product-adaptation.json`。通过 texts 完整覆盖文案、scene 覆盖非文字画面、
instruction 追加事实边界，实现从青苹果竞品设计到橙子产品暖米风格的适配。

- 主工作区 prompts/detailpages.json 仅第 1 项改变，其余 11 项保持空对象；实际执行仍为单参考图工作区。
- 输入校验、原图/产品图/brief 哈希核对、两类基础分析成功缓存检查通过。
  业务源码与此前 66 项测试通过时的哈希一致；本轮只改用例与增量，不重复运行未变的整套代码测试。
- 新 thread_id：`8653336d72f21fdac6833e7620bd060452de7983a7ec57b2af8dc43b6ebfba34`。
- 新 task_id：`09d60ec74c2340e99d4dedd4e9ac11a0`；Flare-2k 一次提交，completed，PNG 790×1357。
- 前后所有 LLM 记录完全一致，新增 Gemini 请求为 0；只新增一个绘图操作、一次 POST，
  原有操作记录与产物保留，未执行其余 11 张。用户级密钥与已授权测试下载域名沿用。
- 目视检查：三个指定文案块完整出现；青苹果/green apple、抗菌、周抛、干湿两用、去污等
  竞品文案移除；暖米背景和橙子花纹生效，保留主要双卷构图。本轮未进行像素级文字定位评分。
- 未提供已确认的尺寸、片数或材质参数，因此参数替换仅覆盖花色，未虚构数值规格。
- 证据：`.cache/validation/agent-delta-20261027/`。基线和增量图片共存于原小样本工作区 artifacts/。
  Beads 仍因 issue_prefix 缺失无法登记；未改业务源码、Host 配置或执行 Git 操作。

## Windows 首图修复复验（2026-10-27）

以下新增记录与下方原始 Linux 交接基线分开。Windows Python 3.12.14、uv 0.12.9，
通过 `uv sync --locked --python 3.12` 安装原锁文件依赖；未升级全局 uv。

- 修复自然排序测试的 Windows 路径分隔符断言；随后修复 Gemini schema 转发兼容性。
- 400 错误先定位到 `$defs`/`$ref`，引用展开后进一步定位到嵌套 `additionalProperties`
  和 `exclusiveMinimum`。出站适配兼容子集，同时保留完整本地验证及严格 JSON。
- 新增错误字段脱敏、非 JSON/超大响应省略、schema 适配、未知字段/零宽高拒绝、
  确定性 HTTP 失败不重试及恢复保持阻塞等回归。最终 66 项测试通过，ruff 格式/lint、mypy 通过。
- 因会话禁止 Git 操作，分项执行质量入口；秘密扫描使用原脚本模式及显式源文件范围，
  未运行其 Git 枚举步骤。未在本轮重做构建、依赖审计或远端 CI。
- 真实验证使用用户级环境变量密钥，仅第一张参考图及 my-product.png，经官方 SDK stdio 客户端执行。
  最终两类 Gemini 分析各一次成功，文本识别 6 个文案块；一次 Flare-2k 绘图提交成功。
- task_id：`cfc0c35a19314bf2aee0c4702ebc94c1`；thread_id：
  `e726b625764e3385e66b4dc25399576769db98050af369bba0fd87714539377c`。
- 图片首次下载被域名白名单阻止；用户授权 files.anyroutes.cn 后只恢复原任务下载，
  绘图提交次数仍为 1。原图 PNG 800×1360，最终 PNG 790×1357，运行状态 completed。
- 目视检查：产品橙子花纹替换成功，主要参考构图保留；首轮基础文案保留了青苹果款名和抗菌文案，
  未作为已核实商品事实或正式发布验收。其余 11 张、批量、备用模型成功路径与其他绘图模型未测试。
- 脱敏诊断与测试报告：`.cache/validation/gemini400-20261027/`；原任务状态、输入快照、
  checkpoint、分析 JSON、原图与成图：`.cache/validation/live-first-20261027/`。均为本地证据。
- Beads 创建任务仍报 `issue_prefix` 缺失，未初始化数据库、修改远端或执行 Git 操作。

## 原始 Linux 交接基线

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
