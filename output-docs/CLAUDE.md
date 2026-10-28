# CLAUDE.md — 电商竞品图复刻 MCP 使用约定

本文件写给调用 `ecommerce-image-replicator` MCP 的消费端 Agent，不是服务端开发约定。
**开始工作前完整阅读[消费端使用手册](./docs/guidebook-of-ecommerce-image-replicator-mcp.md)**，尤其是“错误在哪一阶段，就改对应层”和“只恢复分析/文案失败的图片”。

本文和手册适用于已发布v0.1.6的显式分析恢复契约，发布目标 `1459ebd0e4b63de6bc5a75e41458846f7e6dce83`。已发布v0.1.5没有新增的两个工具；以当前连接的工具schema和资源策略为准。能力缺失请报告版本差异，不自行改安装/Host配置或反复调用不存在的工具。

## 开始前与费用

- 先发现工具，读取 `replicator://input-contract` 和 `prepare_inputs` Prompt；Prompt不是Tool，不猜Host前缀。
- 有旧run_id先get_run；任务模式新输入显式传业务目录绝对路径。相同冻结输入得到同一稳定ID是正常行为，不删库换ID。
- 准备、预检、查询和恢复准备不提交供应商请求；execute_run可能同时产生LLM分析和绘图费用。not_submitted不等于零费用。只执行用户已授权范围。
- 新策略opt-in-v1的null表示不限额，不因null索取预算。字段/策略不明时报告当前实际值，不翻源码、注册表或遍历Host配置。

## 必须守住的输入与复刻边界

- 原竞品图对齐构图、关键对象和互动，保留污渍、水迹、手部、动作及对照角色。只按有来源事实调整产品属性和品牌主题；无明确风格要求沿用参考风格，允许不改主旨的小幅创意差异。
- 不合成未知规格，不将竞品事实冒充用户产品事实。缺文案修订信息先询问；用户明确坚持不改时才保留未解决的参考文案，产品身份与必要品牌/文字色替换仍保留。
- prompts数组对应整组自然顺序；小样本用selected_image_ids，不缩短原组数组。image_id取实际inspect结果，不用“02”猜ID。

## 遇错先定位阶段

- 使用preflight_run看每图analysis、copy_status、transcription、replacement_rule_source和effective_delta；未知文字标pending，不当成校验已通过。
- copy_replacement_unmatched只修正该图完整delta里的规则。全局默认来自冻结product_context；逐图text_replacements=[]可覆盖不适用默认，其它必要规则及产品/配色必须保留。编辑磁盘文件不会更新旧run。
- 分析失败与重试耗尽用prepare_analysis_recovery，仅选blocked且无绘图receipt的图，指定失败的text/visual。它只准备关联恢复run_id，不执行；同request_id+同参数重试准备，后续跟随recovery_run_id。
- 已成功的7张等已有产物不进入恢复updates；原任务/产物/receipt保留。已提交、unknown、pending等状态沿原操作查询/核查task_id，不能用新任务或分析恢复绕过。
- prepare_revision只用于已有下载并后处理成图的视觉修改；不是分析失败的恢复入口。不能把所有blocked都叫终态，也不能靠反复execute重置分析额度。
- scheduled不是完成。有限间隔查询仍不推进时报告状态和脱敏诊断，不忙循环，不因服务进程多就判断根因或杀进程。

## 隐私、恢复与交付

- 密钥由MCP读取安装根.env并按字段回退环境变量；业务目录不另存密钥，不把密钥、代理认证URL或原始响应放进brief/共享日志。不伪造缺失stderr，不把“没有记录”当成反证。
- 不编辑journal/registry/checkpoint，不递归查找私有Host配置，不擅自改代理/凭据或直接调用API绕过工具拒绝。
- 本项目HTTPX的NO_PROXY使用localhost,127.0.0.1,::1，不加[::1]；环境修改交给操作者，重启实际Host/MCP后复核连接。
- 保留安装索引、业务工作区完整.replicator、原输入、receipt/checkpoint和成功产物。按image_id汇总原任务与恢复任务，区分生成成功、视觉验收与缺口，不覆盖原成功文件或改标旧失败图。

## 复制到消费项目

将本文件与相邻 `docs/guidebook-of-ecommerce-image-replicator-mcp.md` 一起合并到消费项目根目录；三种约定任选一种，核心正文一致。保留项目已有约定与文件，不能覆盖为MCP服务端的开发流程。仓库docs/为手册维护源，output-docs/docs/为同步交付副本。
