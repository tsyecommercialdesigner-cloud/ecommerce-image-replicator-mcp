# 逐图复刻：保留表达主旨，允许适度创意差异

当前口径由用户进一步明确：绘图是创意工作，不以逐像素一致或所有对象细节完全相同为验收目标。
少量装饰、位置、比例和渲染差异，只要不改变表达主旨、关键对象身份和互动关系，应验收通过。
主题配色可由Agent根据产品图提交；艺术风格除非用户明确指定，否则继承每张参考图。
A14第06张蓝色水彩图的少量页眉装饰按此口径通过，原严格判定保留为历史，不能继续当作缺陷。

用户于2026-10-27明确纠正：目标是尽可能像原始竞品参考图。此前把参考图降为布局线索、
清除污渍/手部、改成静物的设计方向不符合目标。历史“通过”仅代表满足当时错误的重设计方案，
不能当作复刻通过；原图、成图、旧契约和验收记录保留供追溯。

## 生成依据

原始竞品图定义画面结构，用户产品图和事实定义主推产品，增量仅在产品与品牌属性范围内生效。
整体配色和色调可以按产品/品牌调整；更换艺术风格必须有用户明确要求，配色增量不暗含水彩或插画请求。

| 范围 | 允许增量修改 | 不允许借此改变 |
|---|---|---|
| 产品 | 名称、文案、尺寸规格、材料、颜色、花纹、质感等有依据的自身属性 | 不能改变关键主体角色和互动的表达含义 |
| 品牌 | 全图主题色、色调；用户明确要求时更换艺术风格 | 不能以换色为由自动水彩化或插画化，不能改掉主要版式和关系 |
| 画面 | 少量无损主旨的装饰、几何和渲染差异 | 不能把擦拭改成静物、去掉关键污渍/水流，或反转对照主体身份 |

真实尺寸可以改变产品自身比例或轮廓，但仍在原视觉位置和角色中，并保留与其它对象的接触。
旧抹布等对照对象可以随全图换笔触/色调，但不能变成新品或丢失脏旧状态。
原图有脏盘和擦拭，水彩风的结果仍须有可辨认的脏盘和擦拭；不是必须保持原棕色色值。
若差异明显改变画面主旨或关键关系，应判失败；少量装饰对象不应仅因原图未出现就判失败。

绘图 image[0] 始终是完整参考图的等比缩放/填充版本，之后才是用户产品图。
不再提供 layout/rebuild 模式，不绘制空白框图替代原图，不因 scene 增量舍弃参考图。
提示中的分析结果是辅助描述，不能替代原图作为依据，也不能授权删除未提及的元素。

新 manifest 仍为 version=2，策略更新为 `alignment_policy=reference-creative-v1`；解析契约 version=5，
包含原图 source/sha256、不可由增量覆盖的 edit_boundary、字段角色、产品/品牌变化和检查项。
策略标记进入冻结清单及任务身份，旧策略的契约/验收/操作身份不会被原地改写或冒用。

## 增量与事实

| 输入 | 当前语义 |
|---|---|
| texts 缺省/null | 分析原图文案；按合法产品/品牌增量调整对应内容（如材料/规格），其它继承原图；转录仅为辅助 |
| texts 数组或 [] | 替换产品/品牌文案集合或清空文字；不能借 box/css 重排原文字区域、对象或视觉层级 |
| scene 缺省/null | 原图的非文字辅助描述；不是新的场景设计 |
| scene 字符串 | 仅为产品/品牌外观说明，不能授权构图、对象、互动变化 |
| instruction | 仅补充产品/品牌要求；非空逐图值替换默认值，不累加历史轮次，也不能覆盖 edit_boundary |
| design.product_attributes | property/value/source 数组；property 为 name/dimensions/material/color/pattern/texture/specification，字段不重复，source 必填；作用于主推产品 |
| design.brand_style | palette/tone可按产品图适配；art_style只在用户明确指定时填写，缺省继承原图艺术风格；typography为字体表现 |
| design.objects/layout_regions/forbidden_elements | 非空数组在本地校验拒绝；为兼容保留 null/[]，不再提供结构性修改入口 |
| design.reference_mode | 仅允许 full 或缺省；layout/rebuild 在准备阶段拒绝 |
| design.checks | 仅补充检查；不应把无损主旨的细小差异升级成自动失败 |

可选 `brief/design.json` 包含 facts（value/source）、forbidden_claims、defaults（Delta）。
事实用于产品属性与文案适配；不能编造尺寸/材料，也不因“缺少性能事实”删除污渍或动作。
forbidden_claims 只对显式替换的 texts 作字面校验，不静默改写参考图转录或清除表现元素。
Markdown brief 继续冻结作为背景记录；历史重设计指令不自动拼入新的生成提示。
brand_style 逐字段合并默认值与逐图值：null/缺省继承，非空值覆盖，palette=[] 清除继承的指定色板、回到参考色板。
product_attributes 数组整体替换；[] 清除默认属性增量。所有输入（包括自定义 checks）均无权改动 edit_boundary。

```json
{
  "facts": [{"value": "橙子花纹、浅米底色", "source": "products/my-product.png"}],
  "defaults": {
    "instruction": "产品按用户照片适配，保留原图构图、对象及互动关系。",
    "design": {
      "reference_mode": "full",
      "brand_style": {"palette": ["海军蓝", "浅蓝"], "art_style": "水彩插画"}
    }
  }
}
```

完整 texts/scene 仍可省去对应分析调用，但不能省去生成与验收中的原始参考图。
分析结果不完整时，生成仍以图像为准。新分析单图并发处理，沿用既有3+3次尝试和终止HTTP错误策略。

## 对照验收

视觉评审依次接收：原始参考图、恢复原尺寸后的成图、用户产品图。评审要比较两幅图，
不能只判断“是否符合提示词”或“是否更好看”。必检项为：

| 检查 ID | 依据 |
|---|---|
| composition | 原图主要版式、层级和表达重心可辨认；允许小幅几何差异 |
| elements | 关键主体、示意污渍/水迹和对照身份保留；允许少量无损表达的装饰增减 |
| actions | 原图手势、擦拭/拉布等动作及接触关系 |
| style | 品牌配色/色调生效；未明确指定艺术风格时必须沿用原图媒介，不因换色自动改变摄影/插画类型 |
| copy | 保留原文字区域/层级；texts 显式数组为最终文案，否则按合法产品/品牌要求适配对应内容 |
| identity | 主推产品按事实/照片适配名称、规格、材料和外观；对照对象身份及状态不变 |
| change_scope | 产品/品牌适配和少量创意差异可接受；主要表达、主体身份或关键互动发生实质改变才判失败 |

额外 checks 分配 custom_1 等 ID。ReviewReport 必须包含 image_id、reference_sha256、
artifact_sha256、design_sha256，以及全部检查项的 pass/fail/uncertain 和逐项对照证据。
原图或成图文件被改动、哈希不匹配、缺项或重复项均拒绝。出现 fail 为 needs_revision；
无 fail 但有 uncertain 为 review_required；全部通过为 accepted。

review_mode 默认 manual，等待 Agent/操作者 record_review。vision 每份图/契约最多发出一次评审，
错误或中断转人工，不偷偷重评或重绘。局部结构校验不能证明真实视觉相似度，仍需实图验收。
参考哈希字段和对照评审请求已在A14的06号真实小样本中运行成功。原先因新增页眉装饰而判失败过严，
用户明确按创意工作口径接受该差异，已登记通过。接口成功仍不等于所有实图都自动满足用户目的。
本地 schema 能拒绝结构化越界字段，不能完整识别自然语言是否夹带越界要求或 source 是否可信。
生成提示要求忽略越界部分；人工/视觉验收再对照原图检查，语义不明标 uncertain，结构违规标 fail。
本地测试只能证明传参与状态机制，不能证明模型始终遵守提示或真实视觉相似度。

## 逐图执行与修订

保留稳定 image_id、selected_image_ids、逐图 checkpoint、独立落盘和部分失败可见性。
生成与验收分别报告；partial/blocked 仍返回已完成产物。get_design 返回原图绑定契约，
get_run 增加 alignment_policy、reference_alignment_verified；历史 accepted 不意味着参考图保真已验收。

prepare_revision 仅准备所选图片的完整替换 delta，继承冻结原图与产品图，保留旧成图并关联父任务。
每图谱系预算 max_visual_revisions 默认0、上限5，兄弟分支和后代共享，准备时原子预留。
重复准备相同修订不重复预留；收费仍需 execute_run。未知提交必须恢复原 task_id，不能借修订绕过。
旧v1迁入修订仍需明确 legacy_revision_budget；历史重设计v2迁入时必须显式提交纠正后的 product_context，
避免继承原有静物化/删元素的默认要求。既有额度不因切换策略而自动重置。

## 历史恢复边界

v1 graph、操作键和 checkpoints.sqlite 保持；逐图v2使用 checkpoints-v2.sqlite 和既有操作日志。
不匹配 reference-creative-v1 的旧v2只恢复已提交任务，不发起新绘图POST，不重写旧成图。
历史用户接受记录独立保留，旧策略不匹配当前reference_alignment_verified不撤销用户的接受决定。
未提交的旧v2准备任务（包括上轮11号静物修订）在加载密钥前拒绝执行。
旧v2已知任务若上游报FAILURE，也不能再自动POST；需要按新目标准备任务。
原有 accepted 记录保留为历史依据，reference_alignment_verified=false，不能追认为复刻通过。

测试用例见 [A12](../brief/cases/A12-reference-fidelity.md) 与
[A13](../brief/cases/A13-product-brand-boundary.md)；当前创意容差与全套输入见
[A15](../brief/cases/A15-product-theme-suite.md)，实际验证记录见 [VALIDATION.md](VALIDATION.md)。

### 指定文案与文字主题的提交前解析（plan version 6）

文字LLM节点保留参考图转录和CSS作为分析证据，不把参考CSS直接当作最终主题。
Agent将明确文案修改提交为`text_replacements: [{"old":"青苹果","new":"橙子","source":"products/my-product.png"}]`。
构造阶段进行不区分大小写的字面替换，保留原box和排版；规则未匹配、重叠、串联、与显式texts冲突时阻止绘图。
替换后的最终texts标记为explicit_replacement，提交前检查旧值不残留、新值存在，并为每条规则添加成图验收项。
自然语言instruction依然可用，但精确产品标签等必须通过结构化替换或完整texts表达，不能只依赖模型自行解释说明。

Agent指定`design.brand_style.text_color`（六位HEX）时，构造阶段覆盖结构化text块CSS的foreground color，
消除旧CSS的重复color声明，保留字号、字重、坐标和背景。未指定时保留原文字样式，不猜测品牌色。
它独立于文本内容的reference_transcription角色：文字可保持原文，但最终文字颜色应使用品牌色。
提交前逐块校验，出图新增text_theme检查；抗锯齿和自然色差允许，明显保留旧主题字色不通过。
此配置不代表更换艺术媒介，也不对未被结构化为text块的报告影像、印章或场景物体强行改色。
任意自然语言的全部语义无法由静态校验保证；成图仍需视觉验收。

### 文案待修订时的用户选择

已有明确修订信息（例如05的青苹果→橙子）直接执行修订，不重复索取。
若文案处于待修订且缺少修订信息，Agent先说明具体字段并询问用户补充。只有用户明确选择继续不修改时，
该部分文案才沿用原竞品参考配置；无回复不视为同意。将用户选择及回退字段写入此次brief/修订记录。
回退仅针对未确定的文案，不撤销产品身份/花色替换，也不撤销品牌主题及文字颜色适配；保留已有事实支持的修改。
参考图的参数和宣称仍是参考来源，不变成已核实产品事实。不虚构缺失参数，不删除污渍、手或对象互动。
通过新修订任务生成并重新验收，不能直接把旧needs_revision结果改成accepted，也不以此触发无限自动重绘。
现有text_replacements、texts、brand_style与prepare_revision能力即可表达该分支；询问和用户选择由Agent负责，
服务端继续执行结构、文案和文字主题校验。当前05修订信息已明确，不需要启用未确定文案的回退。


## 多项目任务路由（v0.1.2 候选，待发布核验）

设计与供应商操作内部继续使用原 thread_id；公开调用新增持久绑定的 run_id。
每个工作区独立日志、checkpoint、产物与执行锁；修订沿用父任务工作区。
输入准备显式选目录，后续调用不允许重定向。恢复与兼容契约见 [TASK-WORKSPACES.md](TASK-WORKSPACES.md)。
