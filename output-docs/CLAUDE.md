# CLAUDE.md — 电商竞品图复刻 MCP 使用约定

本文件写给调用 `ecommerce-image-replicator` MCP 的消费方 Agent，适用任务级工作区及下述执行限制策略。它不要求你开发 MCP 源码，也不要求消费项目采用 MCP 仓库的开发、测试或发布流程。

## 接入与契约优先

- 会话开始先发现当前 Host 实际提供的工具与参数 schema，再读取 `replicator://input-contract` 资源和 `prepare_inputs` 提示。工具在 Host 中可能带前缀；下文使用原始工具名，不猜测完整名称。
- `prepare_inputs` 是 MCP Prompt，不是 Tool。Host 不提供 Prompts 时读取资源和本文件；DSH 的部分版本不桥接 Prompts。资源也不可访问时，核对实际工具 schema 和输入契约文档，不自行创造替代工具。
- 资源会说明 `workspace_mode`、`default_workspace`、`allowed_roots`、`state_directory`、输入 schema 和执行预算。实际发现结果与本文不一致时先定位安装版本/配置差异，不用反复试错调用收费入口。
- 首次使用无需调用生成来测试连接。使用工具发现和 `inspect_inputs`。本文件不会授予额外文件权限、下载权限或绘图费用授权。

## 执行限制：默认不限制，按需启用

读取当前连接 `replicator://input-contract`。新实现以 `execution_limit_policy: "opt-in-v1"` 标识：

| 资源字段 | 可选启动参数 | 未配置时 |
|---|---|---|
| batch_images | --max-batch-images | null，不限制分析批次图数 |
| request_bytes | --max-request-bytes | null，不限制应用层请求体字节数 |
| output_tokens | --max-output-tokens | null，省略上游max_tokens，采用供应商默认 |

无需业务人员配置三个数值。可只设置其中任意一项为正整数，其余保持不限制；显式0、负数和非法值会报错。
不限制仅指这三项应用层限制，供应商/模型上限、文件大小、并发、修订额度和下载域名规则仍生效；绘图仍需用户授权与有效凭据。
收到null不是配置缺失，不要因此阻止执行、索取预算或搜索源码/遍历宿主配置。
限制属于启动参数，不放进prepare_run.options、brief或delta。batch_images不是选图数或总费用额度。

只有操作者需要启用/修改限制时，才编辑当前Host/profile中目标服务的args，每个参数和数值各占一个元素；保留其它参数及私有配置，重启该Host管理的MCP子进程。
重新读取当前连接资源，核对指定项已生效，其余为null，并核对state_directory和工作区约束。无需同时修改web、desktop、multica三个profile。
已有任务先get_run，再沿原run_id执行恢复；不重新prepare、不重写增量、不重复生成成功图片，unknown仍按原规则核查。

**旧版兼容**：已发布v0.1.2仍采用默认0且禁止执行的旧策略。本次改造尚未发布；不带opt-in-v1标识的服务不能套用null新语义。
旧实例报告预算为0时，向操作者说明需升级到包含新策略的版本，或按旧版手册配置三个正值并重启；不能仅更新本文件就声称服务行为已改变。

## 其它运行限额（operational_limit_policy=opt-in-v1）

新策略下，输入/下载字节、下载域名名单、轮询截止、HTTP超时均默认null，不需业务人员补配置。
按需可设置--max-input-pixels（正整数像素）、--max-input-bytes、--max-download-bytes（正整数字节）、--poll-timeout、--http-timeout（正整数秒）；--download-host可重复，只有显式设置后才启用域名名单。
不设置域名名单仍只下载无URL凭据的公网HTTPS/443图片，拒绝私网和自动重定向；不能以“不限制”为由绕过安全检查。
新prepare_run.options的concurrency和max_visual_revisions默认null，分别表示不限制任务并发数和修订谱系次数。前者显式设置须为正整数，后者为非负整数，0明确禁止修订。
legacy_revision_budget也可省略为null；既有冻结任务和谱系保存的额度继续有效，不能自动重置旧额度。缺省无限修订不是授权Agent无限自动重绘，每次仍按用户范围执行。
任意业务文本长度硬上限已移除，JSON类型/必填、原图结构、坐标和产品事实校验仍适用。供应商画布与图片解码限制、同工作区执行锁、未知提交防重复、有限自动重试仍保留。

## 工作区与输入文件

任务模式下，先确定用户当前消费项目的**真实、已存在的绝对目录**。在 `inspect_inputs` 和 `prepare_run` 中传 `workspace`，不根据聊天名、Host cwd或 MCP 安装目录猜路径。目录拒绝相对路径、`..`、符号链接及 Windows junction，并须满足允许根与账号权限。

MCP 安装根保存依赖、私有凭据及默认任务索引；业务工作区保存图片、brief、运行日志和产物。不要把业务素材写进 MCP 安装根，也不要为每个项目重新安装 MCP。

```text
<业务工作区>/
  references/
    group_a/
      01.png
      02.png
  products/
    my-product.png
  brief/
    product.md
    design.json             # 可选：实际参与构造的产品事实及默认增量
  prompts/
    group_a.json            # 可选：该组逐图增量，严格JSON数组
  artifacts/                # 服务端生成，保留原产物
  .replicator/              # 服务端持久日志与checkpoint，恢复必需
```

- 竞品图放 `references/<group>/`，主推产品图放 `products/`。当前后缀使用 `.jpg` 或 `.png`，内容须为实际单帧 JPEG/PNG，默认不设应用层文件大小上限；若显式设置max-input-bytes则遵守该值；不要只改扩展名伪装格式。
- 分组名使用字母、数字、下划线或连字符。每组按文件名自然排序（1、2、10）；前导零/大小写产生相同自然序号时先消除冲突。
- `brief/*.md` 写需求、产品事实来源、用户决策和授权范围。**Markdown 会被保留为背景证据，不会直接拼成最终生成提示词。** 要执行的增量须同时写入 `brief/design.json` 的 `defaults` 或 `prompts/<group>.json`。
- 产品未知尺寸、材料、性能不能从竞品图推断。产品照片只能支持其中可见的外观事实；来源字段写真实文件或用户陈述，不伪造证据。
- 素材需要复制/移动时保留用户原件，按用户已授权范围操作；不要默认移动或清空用户素材目录。

## 先准备、再执行、持续查询

1. 阅读每张参考图、产品图及 brief。明确生成范围、逐图增量、费用授权和允许修订次数。已有授权继续适用，不重复询问已明确的条件；缺少关键事实时只问缺失部分。
2. 调用 `inspect_inputs`，保存返回的 `images[].image_id`、`source`、`order` 及 `workspace`。**image_id 取返回值，不能把文件名、序号或自己算的哈希当作ID。**
3. 按这个顺序写逐图增量。存在 `prompts/<group>.json` 时，其数组长度必须等于该组全部参考图数量；只选一张测试也不能把整组数组缩成一个元素。
4. 调用 `prepare_run` 冻结输入并保存返回的 `run_id`、`thread_id`、`workspace`、options 和逐图ID。准备不调用供应商，但会写入本地任务状态。
5. 对照已授权范围检查冻结任务；首图/指定图测试必须使用 `options.selected_image_ids`。按上节识别当前连接的限制策略，确认凭据由操作者配置后，再调用 `execute_run`。
6. `execute_run` 是收费执行/恢复入口，通常先返回 `scheduled`；这不等于生成完成。间隔查询 `get_run`，不要忙循环，不反复 execute 启动多个任务。
7. 产物路径按**响应中的 workspace**拼接相对 `artifacts` 或逐图 `artifact`；不要拼接当前终端目录。查询完还要看实图并验收。

以下是调用参数示意，不是Shell命令。示例目录必须替换为实际业务目录；ID占位字符串必须替换为前一步真实返回值：

```json
{"workspace":"D:\\Projects\\ProductA"}
```

交给 `inspect_inputs`。然后将下列参数交给 `prepare_run`：

```json
{
  "workspace":"D:\\Projects\\ProductA",
  "options":{
    "selected_image_ids":["替换为inspect_inputs返回的目标image_id"],
    "image_model":"gpt-image-2.5-flare",
    "concurrency":1,
    "review_mode":"manual",
    "max_visual_revisions":null
  }
}
```

将 `{"run_id":"替换为prepare_run返回的run_id"}` 分别交给 `execute_run`（已获授权时）及 `get_run`。
不筛选图片时省略 `selected_image_ids`，不能传空数组；这会准备全部参考图，必须符合用户范围。
新策略并发和修订额度均默认null。显式正整数并发生效，显式非负修订额度生效（0禁止修订）；既有谱系不能靠新分支重置额度。
模型可选 flare 或 sunburst 系列（`gpt-image-2.5-flare` / `gpt-image-2.5-sunburst`）；2k/4k由准备后的画布自动路由，不自行给 `image_model` 拼后缀。

## 复刻边界与增量构造

**视觉基线始终是原始竞品图。** 保留主要构图、文字区域和层级、关键对象身份、数量与互动，特别是手部、污渍、水迹、道具、擦拭/拉伸动作及对照对象的脏旧状态。未被文字分析提到的元素也不能擅自删除。

允许有来源地改变主推产品的名称、规格、材料、颜色、花纹、质感及产品文案；允许全图品牌配色和色调适配。艺术风格默认继承每张竞品图，只有用户明确指定时填写 `art_style`。换主题色不意味着改成水彩或插画。

不要为了“更干净”“更高级”把演示图改成静物、去掉污渍或反转新品与旧品的对照身份。少量不影响表达主旨和关键关系的几何、装饰、渲染差异可以接受，不要求逐像素一致。

| 字段 | 正确用法 |
|---|---|
| `scene` / `instruction` | 只补充产品/品牌要求，不重构场景、对象或动作 |
| `design.product_attributes` | `property/value/source` 数组；property为name、dimensions、material、color、pattern、texture、specification，同一属性不重复 |
| `design.brand_style.palette` / `tone` | 按实际产品图或用户品牌要求适配全图配色 |
| `design.brand_style.text_color` | 六位HEX，如 `#164A68`；明确替换结构化文案的前景色，不能只改背景色 |
| `design.brand_style.art_style` | 仅用户明确指定时填写；默认省略 |
| `text_replacements` | 精确文案变更用 `old/new/source` 规则；old必须来自原图实际文案，不猜测 |
| `texts` | 完整文案块数组，每块含content、css、box；保留原文字区域和层级。缺省/null让节点分析；`[]`会清空文字，不是“保持原文” |
| `box` | x/y/width/height归一化至0–1000，宽高为正且不能越界；不是像素坐标 |

不要提交未知字段或 `layout/rebuild` 模式。`design.reference_mode` 仅 `full` 或省略；`objects`、`layout_regions`、`forbidden_elements` 不接受非空覆盖。自定义 checks、CSS及自然语言也无权绕过这些边界。

下面是 `brief/design.json` 的**条件示例**：仅在产品图确实显示蓝白配色、用户同意该适配时使用；色值为示例选择，不是对任何产品的默认事实：

```json
{
  "facts":[{"value":"产品外观为蓝白配色","source":"products/my-product.png"}],
  "defaults":{
    "instruction":"按用户产品图替换主推产品，保留原图构图、污渍、手部和互动关系。",
    "design":{
      "brand_style":{"palette":["蓝色","白色"],"text_color":"#164A68"}
    }
  }
}
```

`prompts/group_a.json` 可为 `[{},{}]`，表示该组两张图都不添加逐图覆盖，继承默认值；没有默认增量时 `{}` 只保留基础描述，不自动完成产品文案替换。
精确改名必须用实际转录的 `text_replacements` 或完整 `texts`，不能只在Markdown/instruction中写一句“替换名称”。替换未匹配、冲突、重叠或串联会阻止提交，应修正规则，不删掉校验。
默认 brand_style 按字段合并；逐图非空值覆盖，null/缺省继承。`palette:[]`清除默认指定色板并回到参考色板，不表示不使用颜色。product_attributes 数组整体替换。
严格JSON不含代码围栏、注释、重复键、NaN或额外字段。文本/非文本描述可省略，由付费分析节点补齐；不要为了省分析而编造文案、坐标或场景。

## 验收与单图修订

- 先 `get_run` 取得逐图产物与状态，再 `get_design({run_id,image_id})` 读取实际 plan、design_sha256 和检查项。`analysis_required` 表示完整契约还需分析，不是工具故障；不要为它盲填texts或清空文字。
- 对照**原始参考图、成图、用户产品图**逐项检查构图、对象、动作、风格、文案、产品身份及修改边界。文字内容已替换但仍大面积沿用竞品文字颜色，应提出修订。
- `review_mode=manual` 默认需要消费方 Agent/操作者验收；vision会增加付费视觉请求，每份产物/契约至多一次，失败转人工。看不到图片时如实报告无法确认，不伪造通过记录。
- `record_review` 参数为 `run_id` 和 `report`。report须含image_id、reference_sha256、artifact_sha256、design_sha256及全部检查项 `checks:[{id,verdict,evidence}]`；verdict为pass/fail/uncertain。使用get_design返回的精确检查ID，覆盖自定义项；哈希来自当前返回值，不手写、不用旧图哈希。若需本地算哈希，应按实现的规范化算法核对，不能随意序列化JSON。
- 有fail为needs_revision；有uncertain且无fail为review_required；全部pass才accepted。生成完成与视觉通过分别汇报。
- 修订只选失败图片：`prepare_revision({parent_run_id,updates:[{image_id,delta}]})` 返回子run_id。**delta完整替换该图原delta**，须带上仍需保留的合法修改，不能只传新增一句话却丢失旧规则。它继承冻结原图、产品图和工作区，不会自动使用磁盘上后来替换的产品照片。
- 准备修订不调用供应商，但预留谱系额度；确认范围后对返回子run_id执行与验收。原图和旧结果保留，只将新通过结果纳入交付，不擅自覆盖历史文件。
- 文案待修订但缺少改法时，先问具体缺失字段。用户明确坚持不改时，仅对未确定文案沿用竞品配置，记入brief/修订记录；仍须替换主推产品身份和品牌/文字颜色。已有明确修正直接应用，不重复询问。不能把参考参数冒充已验证产品事实，也不能把旧失败图直接改记通过。

## 失败诊断与原任务恢复

| 现象 | 下一步 |
|---|---|
| 输入/准备失败 | 核对实际workspace、允许根、图片格式/分组、自然排序冲突、逐组数组长度和schema；修复后再准备，不重复收费执行 |
| 显式限制无效/请求超限 | 报告具体限制；由操作者按需调整当前实例并重启复核。新策略null无需处理；旧版0阻塞按旧版兼容步骤处理，沿原run_id恢复 |
| 401/403、凭据读取失败 | 交给操作者修复凭据/权限；不打印密钥、不修改私有Host配置绕过限制 |
| HTTP400/422等确定请求错误 | 保留脱敏diagnostic_id；核对契约或交给维护者修复，不循环重试同一无效请求 |
| scheduled/running | 继续get_run观察；不是完成，也不需要再创建新任务 |
| partial/blocked | 查看jobs中的error/detail/status/task_id及已成功产物，按原因局部处理，不把整组全部重绘 |
| 查询超时、下载失败且已有task_id | 沿原run_id恢复；已知供应商任务只继续查询/下载，不新POST |
| unknown/提交响应丢失 | 先查供应商后台取得原task_id，使用reconcile_submission；取不到则保持阻塞，不能通过新任务/修订绕过 |
| 已启用域名名单而被拒绝 | 记录域名，由操作者按需调整当前实例显式名单并重启；默认无名单无需补域名。私网/非HTTPS拒绝不能绕过，不重新生成图片 |
| Workspace already has an active workflow | 同一工作区已有执行者；等待并查询原任务，不另起并发执行或删锁 |
| artifact/hash changed | 保留文件与日志，核对是否误改产物；不删除状态库或伪造哈希 |

`reconcile_submission` 使用 `{run_id,index,task_id}`，index为**当前get_run中jobs[].index（从0起）**，不是文件名序号；仅绑定已核验属于该操作的供应商task_id。
重启后先 `get_run`；如已中断且仍需继续，经已有授权核对后 `execute_run` 相同run_id。修改磁盘上的brief/prompts不会改变已冻结任务；要应用新要求，按修订或新准备流程明确处理，不能把它当作失败恢复。

旧固定模式继续使用配置的default_workspace和thread_id；同一次调用只给一种标识，不能同时传run_id和thread_id。改成任务模式后用 `import_run({workspace:原目录,thread_id:原始任务标识})` 绑定旧任务，保存返回run_id；导入不收费、不重建任务。
原目录缺失、允许根拒绝或索引不匹配时先修复定位，不新建空任务冒充恢复。不同项目使用各自run_id，后续工具不接受workspace重定向。

保留业务目录的完整 `.replicator/`、`artifacts/`、原输入及安装根/自定义state-dir的任务索引；备份前停止服务，包含SQLite WAL文件。不要删除数据库、缓存操作记录或旧task_id来“重置”。run_id不是备份，目录移动不会自动更新绑定。
任务路由用于同账号多项目隔离，不是多租户安全沙箱；并发预算也不是全实例总费用上限。

## 凭据、交付和查阅

凭据由MCP读取实际安装根 `.env`，按字段优先于进程环境、Windows当前用户环境；只有字段缺失才回退，空值/非法值不会回退。业务项目不创建另一份密钥文件，不把密钥写进brief、提示词、输出或共享日志。已有用户级密钥时，不用空 `.env` 字段遮蔽它。

交付时按图片列出run_id、image_id、产物绝对路径、生成状态、视觉验收、待修订原因及用户接受的差异。报告供应商失败与本地保存失败的区别；只声称实际完成的验证。保留部分成功结果，不隐瞒空缺。

需要详细安装/Host/契约资料时，查看本项目仓库的[在线手册](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/blob/main/MANUAL.md)、[任务级工作区](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/blob/main/docs/TASK-WORKSPACES.md)、[复刻边界](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/blob/main/docs/DESIGN-V2.md)。文档可能后续更新，调用以当前服务发现的版本与schema为准。

本文件可合并进消费项目已有Agent指令，保留原规则。AGENTS.md、CLAUDE.md、CONVENTIONS.md为同一正文的三个独立版本，选择Host会加载的一种；CONVENTIONS.md不会被所有Host自动加载，需要项目指令显式引用或提供内容。
