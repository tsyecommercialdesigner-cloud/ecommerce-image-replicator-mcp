# ecommerce-image-replicator-mcp 技术规格与 Skill 适配交接

文档版本：1.0。核对日期：2026-10-29（Asia/Shanghai）。与 [PRD.md](PRD.md) 配套。

本文记录2026-10-29核对的 MCP 实现及 Skill 接入要求，不代表当前 Skill 实现或 Host 验收状态。历史源码核对基线为 `b066d89680f5f4745702a48380a761631be808d1`；发行基线 v0.1.7 的源码目标为 `88ef28e76bdcd2cf7f3738e25e157ff7841a6cb3`。前者包含发布后的文档说明，并非当前分支提交；不能据此移动既有标签。后续分阶段检查、候选产物复用及受控发布的实际状态见现行 [CI/CD 说明](docs/CI-CD.md)。

接口以消费端**当前连接**发现的 schema/资源为准。本文的调用示例均用于说明结构，示例身份和产品文案必须替换为实际工具返回及核实内容；阅读本文不授权执行收费请求。

## 1. 项目标识、技术栈与运行入口

| 项目 | 实际值/依据 |
|---|---|
| GitHub 仓库 | [tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp) |
| Python distribution | `ecommerce-image-replicator-mcp`，版本0.1.7 |
| Python module / console script | `image_replicator` / `ecommerce-image-replicator` |
| MCP Server 名称 | `ecommerce-image-replicator`；Host 配置别名可不同 |
| 运行时 | 声明 Python >=3.12；项目 CI 使用 Python3.12、uv0.12.23 |
| SDK | 官方 Python `mcp` 2.3.0，`mcp.server.mcpserver.MCPServer` |
| 传输/协议验证 | 本地 stdio；现有测试使用2026-07-28 discover 流程；不能由 SDK 版本推导所有旧 Host 均兼容 |
| 编排与持久化 | langgraph1.2.18；langgraph-checkpoint-sqlite3.1.2；标准库 sqlite3；portalocker3.2.0 |
| 网络/模型 | httpx0.28.1；pydantic2.14.1；python-dotenv1.2.4 |
| 图片/构建 | Pillow13.0.0；hatchling；实际精确依赖见 [uv.lock](uv.lock) |
| 检查 | pytest/pytest-asyncio、ruff、mypy、pip-audit、有限秘密扫描；[scripts/check.py](scripts/check.py) |

常规启动由 Host 完成，运行时不安装依赖、不拉代码：

```powershell
uv --directory 'D:\MCP\ecommerce-image-replicator-mcp' run --no-sync python -m image_replicator --project-root 'D:\MCP\ecommerce-image-replicator-mcp'
```

省略 `--workspace` 即任务模式；固定模式额外传该参数。stdout 只承载 MCP 协议，日志写 stderr。启动/配置/升级操作归操作者管理，具体步骤见 [MANUAL.md](MANUAL.md)。

## 2. 分层与模块分工

```text
消费端 Agent + 新 Skill
  └─ Host 实际工具映射 / Resources / Prompts
       └─ server.py：MCP 边界、后台任务与诊断
            ├─ routing.py：run_id → workspace/thread_id 持久绑定
            ├─ inputs.py / models.py / design.py：冻结输入、严格契约、合法适配
            ├─ recovery.py：本地预检、分析/文案恢复子任务
            ├─ postprocessing.py：已下载原图的原任务本地恢复
            └─ workflow_v2.py：每图独立 StateGraph + 工作区执行锁
                 ├─ analysis.py / workflow.py：分析缓存、有限重试、receipt
                 ├─ provider.py / network.py：HTTP、代理与下载边界
                 └─ images.py / storage.py / runtime.py：尺寸、原子写入、数据库
```

| 模块 | 职责与 Skill 应了解的边界 |
|---|---|
| [server.py](src/image_replicator/server.py) | 注册12工具/1资源/1提示；把任务交后台；准备和执行分开；工具错误脱敏 |
| [routing.py](src/image_replicator/routing.py) | 绝对工作区与允许根校验、固定/任务模式、持久索引、不可重定向绑定 |
| [inputs.py](src/image_replicator/inputs.py) | 自然排序、稳定 image_id、快照、选图、manifest/thread_id；路径和哈希验证 |
| [models.py](src/image_replicator/models.py) | strict Pydantic 输入，extra=forbid；字段、枚举、归一化坐标 |
| [design.py](src/image_replicator/design.py) | 合并默认/逐图增量、文字替换、CSS文字色、原图边界、生成与验收契约 |
| [workflow_v2.py](src/image_replicator/workflow_v2.py) | 每图图流程、失败阶段、验收和整批聚合；成功图独立保留 |
| [workflow.py](src/image_replicator/workflow.py) | LLM尝试/缓存、绘图POST/查询/下载receipt，兼容v1；v2复用其执行原语 |
| [analysis.py](src/image_replicator/analysis.py) | 分析缓存身份、text/visual状态、旧错误清除、schema错误位置 |
| [recovery.py](src/image_replicator/recovery.py) | 无网络逐图预检；无绘图receipt的失败图显式恢复；request_id幂等 |
| [postprocessing.py](src/image_replicator/postprocessing.py) | 原run、downloaded receipt、本地raw恢复，不构造Provider或执行图 |
| [images.py](src/image_replicator/images.py) | PNG/JPEG校验、预处理画布、模型档位、比例补偿/裁补边/原图宽高 |
| [provider.py](src/image_replicator/provider.py) | LLM分析、异步绘图提交/查询、公网HTTPS下载；不在HTTP边界盲重试POST |
| [network.py](src/image_replicator/network.py) | 本客户端环境代理和合法方括号IPv6兼容；显式direct；不改进程/用户环境 |
| [diagnostics.py](src/image_replicator/diagnostics.py) | LLM HTTP错误脱敏、元数据/响应摘要/diagnostic_id |
| [storage.py](src/image_replicator/storage.py) / [runtime.py](src/image_replicator/runtime.py) | SQLite WAL/FULL、JSON严格解析、原子文件写入、运行目录与启动错误 |

Skill 负责产品事实、逐图增量、授权范围、工具选择和视觉证据。文字与非文字分析默认由 LangGraph 内 LLM 节点完成。Skill 不写 SQLite，不复制 Provider，不修改 checkpoint。

## 3. 能力发现与资源契约

Tools：`inspect_inputs`、`prepare_run`、`import_run`、`preflight_run`、`prepare_analysis_recovery`、`recover_postprocess`、`execute_run`、`get_run`、`get_design`、`record_review`、`prepare_revision`、`reconcile_submission`。

Resource：`replicator://input-contract`，`application/json`。Prompt：`prepare_inputs()`，无参数，返回输入准备与原图边界指令；**它不是 Tool**。

资源内关键字段：

| 字段 | v0.1.7语义 |
|---|---|
| workspace_mode / default_workspace | task/fixed；task默认工作区为null，调用时显式指定 |
| allowed_roots / state_directory | 允许业务根集合/持久任务索引根；空允许根集合不限制集合范围，仍校验路径权限 |
| task_identity | run_id绑定不可变workspace/thread_id |
| delta_item_schema / product_context_schema / review_schema / analysis_recovery_update_schema | 当前严格业务schema，优先于复制的示例 |
| alignment_policy / edit_boundary | reference-creative-v1；允许产品/品牌适配，保护场景主旨与关键关系 |
| generation_image_roles | original_reference、user_product_photos |
| review_image_roles | original_reference、generated_output、user_product_photos |
| analysis_recovery_policy | explicit-pre-image-child-v1 |
| postprocess_recovery_policy | downloaded-local-v1 |
| canvas_compensation_policy / canvas_aspect_tolerance | canvas-normalize-v1 / 0.01 |
| execution_limit_policy / operational_limit_policy / unlimited_value | opt-in-v1 / opt-in-v1 / null |
| proxy_mode / no_proxy_compatibility | environment（默认）或direct / httpx-bracketed-ipv6-v1 |
| ordering / structured_output | 组内文件名自然排序 / true |

版本来自服务发现元数据，不假定资源含 version 字段。Host 工具前缀以实际发现为准，不写死 `mcp__…`。资源/提示不桥接时，使用随 Skill 附带指南和当前工具schema，报告无法读取的部分，不能调用execute试连接。

## 4. 工作区、文件与身份

### 4.1 输入和输出

```text
业务工作区/
  references/<group>/*.png|*.jpg
  products/*.png|*.jpg
  brief/*.md
  brief/design.json                 可选 ProductContext
  prompts/<group>.json              可选 Delta[]，整组自然排序、一图一项
  artifacts/<group>_<order>_<task_id>.png|.jpg
  artifacts/<同名>.geometry.json
  .replicator/                     完整保留，内部文件不是消费API
```

实现按扩展名 `.png`/`.jpg` 发现文件，再验证实际PNG/JPEG、单帧与EXIF方向；`.jpeg`不在发现扩展名集合内。references 至少一组且每组有图，products 至少一图，brief 至少一份Markdown。组名满足 `[\w-]{1,80}`。按组内自然序1、2、10；歧义数字/大小写同序名称会拒绝。

`inspect_inputs`返回 `workspace`、`groups`（组→相对路径数组）、`images`（source/order/image_id）。`order`从1开始且按组计数；get_run/preflight的`index`从0开始，指当前冻结run.jobs，选图或子任务会改变index。reconcile使用该run返回的index，不根据文件名推断。

冻结输入位于 `.replicator/inputs/`；日志 `.replicator/journal.sqlite`；v2图checkpoint为`.replicator/checkpoints-v2.sqlite`，旧v1为`.replicator/checkpoints.sqlite`。保留整个`.replicator`及WAL相关文件，其内还包括prepared-v2、llm、errors、designs、raw、reviews等缓存和证据。不要把单独某个DB当完整备份。

任务索引在 `state_directory/.replicator/task-registry.sqlite`，state_directory默认安装根，可由`--state-dir`设置。安装根`.env`、业务工作区、任务索引是三个不同概念。

### 4.2 身份规则

- v2 image_id：`参考相对路径:原图SHA256前16位`，以实际返回为准。
- thread_id：冻结manifest的canonical JSON SHA256，64位小写十六进制；同输入/选项获得同身份。
- run_id：`run_`+workspace/thread_id绑定的SHA256。相同输入在不同工作区不会共享run_id。
- 同一个身份参数位置必须且只能传run_id或thread_id之一。task模式后续用run_id；固定模式可兼容thread_id。
- 新模式接手未绑定的旧thread_id，用`import_run(workspace, thread_id)`；已知run_id直接查询。
- 改磁盘brief/prompts不改变旧run的冻结输入；不要改输入只为换ID，更不能删除数据库重来。
- 后续工具不接受workspace重定向。索引/工作区移动或丢失时交操作者恢复，不为查不到任务而prepare覆盖。

不同工作区可并发；同工作区跨进程执行互斥。各图按冻结concurrency并发，null时按本run图数放行。该隔离不是账号权限沙箱，不面向多机共享文件系统部署。

## 5. 输入类型明细

所有以下模型为strict Pydantic，未知字段拒绝；类型不依赖字符串自动转换。

### 5.1 RunOptions

| 字段 | 类型/默认/范围 |
|---|---|
| image_model | `gpt-image-2.5-flare`（默认）或`gpt-image-2.5-sunburst`，只选家族 |
| concurrency | int>=1或null（默认）；不是启动参数 |
| selected_image_ids | 非空、唯一、来自inspect的string[]或null（全部）；整组prompts仍完整 |
| review_mode | manual（默认）或vision；vision可额外收费 |
| max_visual_revisions | int>=0或null（默认）；0禁止修订，null不限；谱系额度持久化 |

### 5.2 Delta 与 ProductContext

| Delta字段 | 类型与语义 |
|---|---|
| texts | TextBlock[]或null；null继承默认/待分析；[]是最终空文案，绝非自动提取 |
| text_replacements | CopyReplacement[]或null；[]可覆盖默认规则为空；有规则时不能同时使用显式texts |
| scene | 非空string或null；显式覆盖仅补充产品/品牌，不授权改构图/对象/动作 |
| instruction | string，默认空；逐图非空值替换默认instruction，不是追加patch |
| design | DesignOverrides或null；结构见下 |

TextBlock：`content`非空string；`css`为string；`box`含x/y（0..1000）、width/height（>0且<=1000），并要求x+width<=1000、y+height<=1000。坐标基于EXIF校正后的原图归一化；像素换算为`1000*x_px/W`、`1000*y_px/H`等。

CopyReplacement：`old`/`new`/`source`均非空string。匹配是忽略大小写的字面子串、一次替换，**不支持正则**；每条旧词须在本图转录中出现。旧词重复/相互包含，或任意new仍含任何old而造成链式/残留，均拒绝。

DesignOverrides：

- `reference_mode`：只能full或null。
- `product_attributes`：属性数组，property只能name/dimensions/material/color/pattern/texture/specification；value/source非空；同property不得重复。
- `brand_style`：palette为非空字符串元素数组或null；text_color为`#RRGGBB`或null；tone/art_style/typography为非空string或null。art_style仅在用户明确要求时设置。
- `checks`：自定义验收string[]或null；不得放宽服务端edit_boundary。
- 旧兼容字段`objects`/`layout_regions`/`forbidden_elements`只允许空数组或null，不能填写结构覆盖。

ProductContext由`brief/design.json`提供：`facts`默认[]，每项value/source非空；`forbidden_claims`默认[]；`defaults`默认空Delta。Markdown brief被冻结为来源资料，**不会自动转换成结构化facts/brand_style/精确换词**，Skill须写入需要确定执行的结构化增量。

默认合并：texts/scene/text_replacements只有逐图非null才覆盖；instruction取逐图非空，否则保留默认；design浅合并，brand_style再按非null字段合并。product_attributes数组为整体替换，不按property合并。恢复/修订传入的delta也是完整逐图替换；省掉原字段可能让默认重新生效。

### 5.3 主题色与验收输入

palette/tone描述全图主题；`brand_style.text_color`将每个结构化文字块的CSS前景color统一为指定值，保留位置和其它排版信息，生成前再次校验。只写“改成橙色”不能代替这个字段。只有需要统一文字主题时设置，颜色应兼顾产品图和可读性，不能把颜色观察当成材质/参数证据。

ReviewReport实际使用ReferenceReviewReport：`image_id`、`artifact_sha256`、`design_sha256`、`reference_sha256`、`checks`。三个hash均为64位小写十六进制。每项check含id、verdict=pass/fail/uncertain、非空evidence；所有get_design.plan.checks的ID恰好覆盖一次，不硬编码只有七项（可能增加换词、text_theme及custom检查）。

## 6. 十二个 Tool 的接口与副作用

所有Tool声明structured_output，outputSchema为开放dict，并非完整稳定的业务字段枚举。应同时判断MCP `isError`及业务status/jobs；不能只看工具是否返回JSON。下面`Identity`表示`thread_id?: string|null`、`run_id?: string|null`，默认都null但业务必须二选一。

| Tool | 完整输入参数（?为可省略） | 主要输出/前提 | 网络与副作用 |
|---|---|---|---|
| inspect_inputs | workspace?: string|null | workspace/groups/images；task模式必需workspace | 无供应商请求；可能创建本地日志 |
| prepare_run | options?: RunOptions|null, workspace?: string|null | 冻结manifest；返回身份、workspace、初始状态/jobs | 本地写快照、日志、索引；不执行 |
| import_run | workspace: string, thread_id: string | 绑定存在的旧任务，返回run_id和状态 | 本地索引写入，不生成 |
| preflight_run | image_ids?: string[]|null, Identity | 逐图analysis/copy/delta；provider_requests=0 | 本地检查，可能重建预处理图；执行期间拒绝 |
| prepare_analysis_recovery | updates: AnalysisRecoveryUpdate[], request_id: string, Identity | recovery_prepared及新run_id，或preflight_failed | 写恢复子manifest/关联；无供应商调用，不执行 |
| recover_postprocess | image_ids: string[], Identity | status=ok或partial_or_rejected；jobs逐图结果；provider_calls=0 | 原run本地raw→成品；无Provider/网络；执行期间拒绝 |
| execute_run | Identity | scheduled，或已有活动任务状态 | **可能收费**分析/绘图/vision验收；后台推进，返回不代表完成 |
| get_run | Identity | 身份、options、聚合状态、jobs、产物/诊断 | 本地查询；不主动查供应商 |
| get_design | image_id: string, Identity | plan/design_sha256，或analysis_required/missing | 本地查询；不自动发起分析 |
| record_review | report: ReferenceReviewReport, Identity | 更新验收后任务状态 | 本地写验收；要求已有generated产物，核对hash |
| prepare_revision | updates: RevisionUpdate[], parent_thread_id?: string|null, legacy_revision_budget?: int|null, product_context?: ProductContext|null, parent_run_id?: string|null | 新run_id、parent_run_id；完整delta；已有downloaded+generated产物 | 本地准备/占谱系额度；不执行，不删除父图 |
| reconcile_submission | index: int, task_id: string, Identity | 核查并绑定后status；仅unknown/submitting可用 | 调供应商查询，不POST绘图；成功改receipt为pending |

prepare_revision的parent_run_id/parent_thread_id同样二选一；不是run_id字段。v2保留原谱系额度，legacy_revision_budget仅用于旧v1导入修订，不能用它重置v2限制。product_context可在准备视觉修订时显式更新，但必须有事实/授权依据。

AnalysisRecoveryUpdate：image_id必需；delta默认null；retry_kinds默认[]，元素仅text/visual且唯一；allow_terminal_http_retry默认false。delta和retry_kinds至少提供一项有效操作。scene对应visual，不存在`retry_kinds=[scene]`。

RevisionUpdate：image_id和完整delta必需。所有选图数组都应使用工具返回的真实身份；恢复/修订不能包含成功且不需改动的图片。

### 6.1 新任务调用示例

以下run_id/image_id为示例，不能直接执行。先inspect取得实际image_id，再构造prepare参数。参考组有12张时，prompts仍须12项，下面仅选择一图说明参数。

<!-- contract-example: inspect_inputs -->
```json
{
  "workspace": "E:\\BusinessProjects\\ExampleProduct"
}
```

<!-- contract-example: prepare_run -->
```json
{
  "workspace": "E:\\BusinessProjects\\ExampleProduct",
  "options": {
    "image_model": "gpt-image-2.5-flare",
    "selected_image_ids": [
      "references/detailpages/02.png:0123456789abcdef"
    ],
    "review_mode": "manual"
  }
}
```

<!-- contract-example: preflight_run -->
```json
{
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
```

只有取得有效run_id并满足费用授权后，才能将同一身份传给execute_run。下面两个参数结构相同，但一个启动执行，一个只读本地状态；不要把示例ID用于测试真实服务。

<!-- contract-example: execute_run -->
```json
{
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
```

<!-- contract-example: get_run -->
```json
{
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
```

<!-- contract-example: get_design -->
```json
{
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "image_id": "references/detailpages/02.png:0123456789abcdef"
}
```

旧thread_id尚未绑定时，import参数如下；已有run_id不要重复导入：

<!-- contract-example: import_run -->
```json
{
  "workspace": "E:\\BusinessProjects\\ExampleProduct",
  "thread_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
```

### 6.2 分析重试示例

适用：visual耗尽、text成功、该图blocked且无任何绘图receipt；若还有retry_available则沿原run执行，不用本例重置。

<!-- contract-example: prepare_analysis_recovery -->
```json
{
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "request_id": "visual-recovery-round-1",
  "updates": [
    {
      "image_id": "references/detailpages/08.png:0123456789abcdef",
      "retry_kinds": [
        "visual"
      ]
    }
  ]
}
```

成功返回的新run_id才是恢复执行对象；parent_run_id指向父任务。同request_id+同updates重复准备幂等；已建立后同request_id换参数拒绝；已有恢复关联则跟随recovery_run_id。恢复任务再失败，在该恢复任务上继续诊断。

### 6.3 文案修正示例的构造规则

以preflight.jobs中的**delta**为完整逐图底稿，结合effective_delta和replacement_rule_source判断继承。只改不适用于该图的规则，保留其它产品和主题字段。示意逻辑如下，变量来自真实preflight和核实事实，不是可独立执行的脚本：

```python
fixed_delta = copy.deepcopy(preflight_row["delta"])
fixed_delta["text_replacements"] = corrected_rules_for_this_image
update = {"image_id": preflight_row["image_id"], "delta": fixed_delta}
```

全局“青苹果→香橙”仅在用户已确认新文案、且本图确实出现旧词时适用。无角标的02/03只移除不适用规则；有角标的07/08保留。若默认全部不适用可设[]，但不能清空其它必要身份替换。纯copy修正一般不传retry_kinds，复用成功分析。

### 6.4 本地恢复和未知提交示例

<!-- contract-example: recover_postprocess -->
```json
{
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "image_ids": [
    "references/detailpages/02.png:0123456789abcdef"
  ]
}
```

<!-- contract-example: reconcile_submission -->
```json
{
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "index": 0,
  "task_id": "example-provider-task-01"
}
```

reconcile的task_id必须由操作者/供应商核实为原请求，不能仅因查询成功就推断供应商证明它属于某张图。当前实现校验ID格式并查询可用性，没有供应商级的原请求归属证明；Skill须保留人工核实来源。

### 6.5 视觉修订与验收示例

以下prepare_revision示例假设：父图已downloaded+generated、用户要求改主题、该图原delta仅有此brand_style。实际修订须复制**本图完整旧delta**再修改；不可照抄示例丢掉已有事实、换词和instruction。

<!-- contract-example: prepare_revision -->
```json
{
  "parent_run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "updates": [
    {
      "image_id": "references/detailpages/02.png:0123456789abcdef",
      "delta": {
        "design": {
          "brand_style": {
            "palette": [
              "暖橙",
              "米白"
            ],
            "text_color": "#8C3E13"
          }
        }
      }
    }
  ]
}
```

record_review示例仅演示**只有七项基础checks**的设计且各项确实看图通过时的结构；有text_theme、换词或custom检查时必须按实际plan添加。示例hash与证据为教学占位，不能原样提交，更不能在没有看图时声明pass。

<!-- contract-example: record_review -->
```json
{
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "report": {
    "image_id": "references/detailpages/02.png:0123456789abcdef",
    "artifact_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "design_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "reference_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    "checks": [
      {
        "id": "composition",
        "verdict": "pass",
        "evidence": "占位：应替换为原图与成图版式对照的实际观察。"
      },
      {
        "id": "elements",
        "verdict": "pass",
        "evidence": "占位：应替换为关键对象及污渍、水迹是否保留的实际观察。"
      },
      {
        "id": "actions",
        "verdict": "pass",
        "evidence": "占位：应替换为手部、动作和接触关系的实际观察。"
      },
      {
        "id": "style",
        "verdict": "pass",
        "evidence": "占位：应替换为配色与艺术媒介是否符合要求的实际观察。"
      },
      {
        "id": "copy",
        "verdict": "pass",
        "evidence": "占位：应替换为文案内容、层级和可读性的实际观察。"
      },
      {
        "id": "identity",
        "verdict": "pass",
        "evidence": "占位：应替换为产品照片及已核实事实的对照观察。"
      },
      {
        "id": "change_scope",
        "verdict": "pass",
        "evidence": "占位：应替换为变化是否保留参考表达主旨的实际观察。"
      }
    ]
  }
}
```

### 6.6 输出的消费方法

- prepare_run/import_run/大部分状态操作返回thread_id、run_id、workspace及任务状态；prepare_revision另有parent_run_id。不要只保存人类文件序号。
- execute_run的scheduled没有“已生成”的含义；由get_run读取逐图进展。
- preflight_run含jobs、provider_requests=0、ready_for_generation、analysis_calls_may_be_billable；jobs可含transcription、原delta、effective_delta、replacement_rule_source和诊断。`ready_for_generation=false`可能只是待分析，也可能真有阻塞，须读逐图字段。
- get_design要么返回plan/design_sha256，要么返回status=analysis_required及missing字段；没有plan时不制造验收hash。
- prepare_analysis_recovery成功返回新的run_id；provider_requests=0，首次准备含auto_execute=false。幂等重放可省略preflight等字段，不能按“字段缺失”断言任务丢失。
- recover_postprocess含provider_calls=0与jobs；isError=true时仍可能有recovered成功图，逐图汇总。

Tool执行错误可能只有安全文本，不承诺统一的error对象。即使MCP层成功，也要核对业务status与jobs；相反，批量部分失败不等于已保存成功图应被丢弃。

## 7. LangGraph执行、状态与重试

### 7.1 v2每图顺序

`START → preprocess → analyze_missing → resolve_design → generate → postprocess → review → END`

- preprocess核对冻结参考哈希，生成预处理画布。
- analyze_missing先text分析/复用/显式覆盖，然后resolve_copy检查换词；通过后才visual分析。错误换词会在场景和绘图收费前拦下，但text分析本身可能已收费。
- resolve_design合并事实/增量、生成完整原图对齐契约，校验最终文案/CSS，写入可查询design，再进入绘图边界。
- generate复用receipt或有限提交、轮询、下载；图1始终为完整原参考图（预处理版），后续图为用户产品图。
- postprocess从raw生成精确原图宽高的成品与几何报告。
- review：manual默认保留review_required；vision每artifact/plan最多一次模型验收请求，结果不完整/失败留待显式验收。

### 7.2 分析缓存语义

text和visual分别有缓存身份，包含请求内容/契约和可选恢复scope。每kind先gemini-3.8-flash最多3次，再gemini-3.7-flash最多3次；重启不重置。严格JSON、schema、数量/顺序/image_id校验失败计入次数。

显式texts只跳过text，显式scene只跳过visual；两者均提供才都跳过，且仍需真实核实及产品/品牌边界。另一半若缓存成功则复用，不是必然重新分析。人工覆盖是`provided`，LLM有效缓存是`succeeded`；`texts=[]`是最终无文案，不能伪装分析完成。

旧error与有效result共存时，preflight按schema/ID校验有效result，标stale_error_marker；执行清除活动错误并保留failure_history。仅凭历史error不能判定再次收费必要。

人工覆盖不应成为默认修复手段。持续分析失败且具备读图能力时，可以核实后提供完整texts/scene；人工texts是最终文案且坐标必须归一化，scene仍不授权结构改动。缺修订事实先问用户，明确坚持暂不修改才保留未解决参考文案；该选择不能冒充产品事实来源或取消必要主题适配。

### 7.3 三层状态分别读取

| 层 | 主要状态 | 解释 |
|---|---|---|
| run/调度 | prepared、scheduled、running、interrupted、interrupted_or_other_process | scheduled是调用返回；running不在本进程tasks时显示可能中断/其它进程，不据此杀进程 |
| run/聚合 | partial、blocked、review_required、needs_revision、accepted | 未全部生成时有成功则partial，否则blocked；全部生成但有fail则needs_revision；全accepted才accepted |
| jobs[].status（receipt） | not_submitted、new、submitting、unknown、pending、success、downloaded、failed、exhausted | not_submitted不证明无分析费用；success是供应商成功，downloaded也不证明后处理/验收成功 |
| generation_status / review_status | generated或blocked / not_ready、review_required、needs_revision、accepted | 与receipt分层，必须逐图判断 |
| preflight状态 | ready、analysis_required、blocked、generated_preserved、image_operation_exists、recovery_prepared | ready只是本地已知检查通过，不是生成完成 |
| analysis.text/visual.status | provided、succeeded、analysis_required、retry_available、blocked、invalid_cache | provided是人工覆盖；retry_available仍有原预算 |

聚合`generation_complete=true`不等于accepted。get_run.jobs可能带phase/error_code/analysis_kind/cache_key/attempts/schema_errors/http_status/diagnostic_id/recovery_action、artifact/hash、model、revision、postprocess和recovery_run_id；并非每阶段都有所有字段。

### 7.4 绘图与查询幂等边界

绘图操作身份包含image_id、原图hash、最终prompt、产品图hash、模型家族及revision；实际路由模型保存到receipt，恢复不因新路由规则重发。

最多3次POST尝试。只在明确未建连接（ConnectError/ConnectTimeout/PoolTimeout）或供应商明确FAILURE时有限重试；后者新提交仍可能收费。POST HTTP非200、收发超时、无有效task_id等均按可能已受理处理，不能直接重放。供应商无可靠幂等键，不能承诺恰好一次。

pending复用task_id，供应商NOT_START/IN_PROGRESS继续轮询，SUCCESS保存result，FAILURE按剩余尝试处理。单轮连续查询错误最多3次后保留任务；下载最多3次，失败保留result；沿原run恢复可继续查询/下载，不重建绘图任务。get_run本身只读本地状态。

停止MCP会取消本地worker，不取消供应商已受理任务。原receipt=failed/exhausted为终态，不会被普通execute无限重开；不能用分析恢复绕过。若确需新的付费尝试而现有入口不支持，应交操作者/维护者核对明确方案。

## 8. 三条恢复路径的准确前提

| 项目 | prepare_analysis_recovery | prepare_revision | recover_postprocess |
|---|---|---|---|
| 适用 | v2原图对齐任务，出图前分析/文案/设计失败 | 已有完成下载并后处理的成图，要改视觉结果 | v2已有downloaded receipt与本地raw，后处理未完成 |
| 不适用 | 未执行/成功图；任何已有绘图receipt；预处理/绘图/后处理失败 | 无父成图、未处理完的供应商操作 | v1；无raw；unknown/pending等未下载状态；任意外部raw |
| 身份 | 建关联子run；不改父7图 | 建修订子run，记录父artifact/hash和谱系 | 原run，无子run |
| 输入变化 | 完整delta或失败kind的显式retry scope | 完整delta；按事实可显式product_context | 不改brief、prompt、参考图或产品图 |
| 网络/费用 | 准备为0；后续execute可收费 | 准备为0；后续execute可收费 | 0，不构造Provider、不执行图/验收模型 |
| 完成条件 | 跟随子run执行/验收，按image_id合并 | 新图执行/验收，保留旧图 | recovered后仍review_required，显式视觉验收 |

分析恢复还要求job_result.generation_status=blocked，phase属于analysis/copy_preflight/resolve_design/design_preflight（兼容旧缺phase）；不能因无receipt就把所有本地错误归入此入口。retry_kinds只能重开blocked/invalid_cache的kind；retry_available及已成功kind拒绝。终态HTTP需确认配置修正并显式allow_terminal_http_retry=true。

恢复准备会先本地preflight，仍blocked则返回`isError=true,status=preflight_failed`，不建立子任务。错误中的preflight正文被裁成安全诊断；要看transcription/完整delta另调preflight_run。成功才写原图→恢复任务关联；父任务不再处理已转向恢复的图片。

本地后处理逐图返回recovered/generated_preserved/rejected，任一拒绝时整体`isError=true,status=partial_or_rejected`，成功部分已保存。已有成功图须hash一致；不覆盖不同内容。新恢复标记阻止以后重放该图旧checkpoint并保留显式验收；但execute同run的其它图仍可能收费，不能为了“收尾”调用它。

## 9. 错误分类与处置矩阵

接口参数/协议错误与工具执行失败分开；SDK ToolError形成工具错误，不能根据“有返回”宣称成功。当前部分边界只给脱敏异常类型，不暴露内部原文；证据不足应报告缺口。

| 阶段/异常或error_code | 现有含义 | Agent该改哪里/用什么入口 |
|---|---|---|
| inspect/prepare：ToolError包裹ValueError/ValidationError | 路径、格式、整组数组长度、字段等拒绝；边界可能不提供具体正文 | 对照输入契约核对已知输入；不扫描源码/DB；诊断不足交操作者 |
| StartupError/PermissionError/sqlite3.OperationalError | 账号权限、目录、磁盘、锁问题 | 操作者检查明确目录及账号；保留DB/ACL，不全量放权或删库 |
| phase=provider_initialization，ValueError/InvalidURL等 | 网络客户端构造问题；也可能是CA/其它非法代理配置 | 交操作者核实，升级/配置后重启实际连接，get_run后按原授权恢复 |
| preprocess_failed/input_preflight/local_preflight_failed | 冻结输入读取、hash、路径/图片预处理等 | 修复原快照/访问条件，不能伪造hash或换scene |
| analysis_http_failure / LLMHTTPFailure | HTTP分析错误；400/401/403/404/413/415/422为终态 | 记录http_status/diagnostic_id；修正确定原因后显式恢复，不凭HTTP码猜唯一根因 |
| analysis_provider_request_failed | 请求/封装响应失败 | preflight查kind/剩余次数，原run或显式恢复 |
| analysis_response_storage_failed | 响应本地持久化失败 | 操作者修磁盘/权限；不误判prompt或图形类型问题 |
| analysis_json_validation_failed | 非严格JSON、重复字段/非有限数等 | 定位分析kind和有限次数；耗尽后只恢复失败kind |
| analysis_schema_validation_failed | 字段/类型/框等不符 | 看schema_errors.path/type；不根据构图种类推断不支持 |
| analysis_identity_validation_failed | 数量、顺序或image_id不符 | 同上，不能改真实image_id迎合错误输出 |
| analysis_retry_exhausted / analysis_previous_attempt_failed / invalid_analysis_cache | 兜底诊断或缓存失效；更具体failure_code可能优先 | preflight区分retry_available与blocked，复用成功缓存 |
| copy_input_conflict | 显式texts与有效replacements同时存在 | 在本图完整delta中选择一种，注意默认继承 |
| copy_replacements_overlap / copy_replacements_chain | 旧词重叠/重复，或new造成链/旧词残留 | 修本图规则，不改LLM scene |
| copy_replacement_unmatched | 本图转录无对应old；replacement_indexes为0基 | 查transcription/规则来源，prepare_analysis_recovery修完整delta |
| design_validation_failed / resolve_design_failed | 最终文案、禁用claim、主题色或契约不符 | 对照产品事实与effective_delta，出图前合法恢复；不放宽构图边界 |
| generate_failed / SubmissionUnknown | 生成阶段；可能已受理，或早前相同来源操作未解决 | 看receipt/task_id；unknown/submitting先reconcile，不重提 |
| ProviderFailure，查询/下载错误 | 供应商任务/网络/下载边界 | 保留原task_id/result；原run继续；不把超时说成未受理 |
| failed/exhausted receipt | 绘图尝试已终止 | 不用分析恢复或删除receipt重置；交操作者明确后续 |
| provider_canvas_aspect_mismatch / CanvasMismatch | 实际与请求画布比例偏差>1% | 保留raw/尺寸，人工确认；不强拉伸或新绘图碰运气 |
| downloaded_receipt_required / image_operation_missing | 缺本地恢复前提 | 核对原提交/下载，不用外部raw绕过 |
| local_file_missing / local_permission_denied | raw/快照等缺失或访问拒绝 | 保留现场、操作者恢复文件/权限；本地恢复不自动下载 |
| artifact_hash_mismatch / frozen_reference_hash_mismatch / stored_geometry_conflict | 产物/原图/几何完整性冲突 | 不改hash/覆盖，交操作者 |
| review_required / review_error | 已生成但待验收或vision验收失败 | 手工看图并record_review；无需重新绘图 |
| needs_revision | 实图检查有fail | 补齐修订事实，prepare_revision指定图片；不重标旧图通过 |
| RecoveryRejected / LockException / active execution | 选择、状态、request_id或并发前提不符 | 读固定安全消息与原状态；等待/改合法参数，不删锁或开第二实例 |

`phase=analysis`中的kind只有text/visual，schema_errors含安全路径和type，不回显校验输入。不要伪造stderr、把离线复现当真实Host堆栈，或由多进程数量直接推断根因。

## 10. 尺寸、模型档位与本地恢复

请求画布边为16倍数；长边<=4096，像素总量655360..8294400，宽高比不超过3:1。原图可经等比缩放+白色补边映射到合法画布，保存original/canvas/resized/crop。基于**请求画布长边**：<=1024用家族基础模型；<=2048用-2k；其余至4096用-4k。不是由消费Agent逐张挑后缀，也不是按最终成品宽度路由。

后处理按返回真实编码与尺寸工作，不针对某个模型名硬编码补丁。定义`a=actual_w*requested_h`、`b=actual_h*requested_w`，比例偏差`max(a,b)/min(a,b)-1`。<=1%含边界时Lanczos归一化到请求画布，再按保存crop去补边，最终resize到原图**精确两维**；>1%拒绝并保留raw。

示例：原790×857、请求800×864、供应商1206×1304，产物应790×857，不是只缩宽得到790×854。`.geometry.json`及get_run.jobs.postprocess记录policy、actual_size、requested_size、final_size、crop、compensated、aspect_deviation、aspect_tolerance、method；本地恢复另外记录transform_source。

新receipt保存原请求transform；旧v2缺transform时从冻结参考重建几何。尺寸修复不保证文字清晰、对象关系或创意质量合格，仍需实图验收。

## 11. 限额、凭据和网络边界

### 11.1 启动配置

| 参数 | 默认及单位 |
|---|---|
| --project-root | 必需，现有安装根绝对路径，定位.env |
| --workspace | 省略为task；指定为fixed |
| --allow-workspace-root | 可重复，默认[]；集合不限制但路径校验保留 |
| --state-dir | 默认project-root，现有持久索引根 |
| --max-batch-images | null；正整数，分析批次图数 |
| --max-request-bytes | null；正整数字节，分析/绘图/vision请求体 |
| --max-output-tokens | null；正整数；省略则请求不带max_tokens |
| --max-input-bytes / --max-input-pixels | null；正整数字节/像素 |
| --max-download-bytes | null；正整数字节 |
| --poll-timeout / --http-timeout | null；CLI为正整数秒；内部Settings支持正数 |
| --download-host | 默认null，不按域名名单限制；重复指定后只允许所列主机 |
| --proxy-mode | environment默认；direct显式直连 |

null表示未启用相应应用层上限，不取消机器/供应商/Host限制，也不是要业务人员补数值。显式0为非法启动限额，不表示不限；RunOptions.max_visual_revisions的0则合法且禁止修订。concurrency/max_visual_revisions在prepare时冻结，原任务已保存值及谱系额度不因升级静默放开。

### 11.2 凭据

`ZHENZHEN_GEMINILLM_API_KEY`用于分析/vision；`ZHENZHEN_GPTIMAGEGEN_API_KEY`用于绘图提交/任务查询。逐字段安装根`.env`→进程环境→Windows当前用户环境；只在字段缺失时回退。空、空白、CR/LF/NUL、重复字段、文件解析/读取失败均报错，不回退旧值。

本实现`read_keys`在execute进入后台前读取两项，reconcile也读取；inspect/prepare不是凭据或网络可用性测试。业务工作区不搜索`.env`；项目.env不导入NO_PROXY或展开变量。升级保留密钥文件内容与ACL，Skill不输出或复制真实值。

### 11.3 上游接口（供维护与契约理解，不供Skill直连）

固定base_url为`https://ai.t8star.org`，不是Tool参数：

| 操作 | HTTP接口 | 请求/响应契约概要 |
|---|---|---|
| 分析/vision | POST /v1/chat/completions | model/stream=false/messages/response_format；max_tokens可省；Bearer Gemini Key；choices[0].finish_reason=stop，message.content为严格JSON |
| 绘图 | POST /v1/images/generations?async=true | model/prompt/size=`WxH`/image=DataURL[]；Bearer GPT Key；HTTP200含task_id或code=success且data为task_id |
| 查询 | GET /v1/images/tasks/{task_id} | Bearer GPT Key；code=success且data.task_id匹配；data.status为任务状态 |
| 下载 | 返回的HTTPS URL或b64_json | SUCCESS结果data.data恰好一图；保存原始字节；URL下载不携带API Authorization，不跟重定向 |

分析输出为`{"images":[{"image_id":...,"texts":[...]}]}`或对应scene数组；这里只是结构说明，不是可执行JSON。供应商Schema桥会内联$defs、适配不支持的关键词，本地仍做完整严格校验；不能通过弱化本地模型“修复”HTTP400。

### 11.4 代理与下载

environment保留HTTP_PROXY/HTTPS_PROXY/ALL_PROXY与NO_PROXY语义，通过公开HTTPX transport/mount接口规范化合法独立方括号IPv6（含端口）；不删除所有`[`项，不修改os.environ/用户注册表/Host文件。非法配置仍拒绝，绝不静默直连。

direct仅显式禁用本MCP代理选路，仍保留SSL_CERT_FILE/SSL_CERT_DIR和TLS校验；不是全局trust_env=False。操作者修改后重启实际DSH管理的MCP，再复读proxy_mode/兼容标识；旧进程不会因文档更新而改变。

公网HTTPS、禁止URL凭据、端口443、DNS必须公网、无自动重定向等安全检查始终保留；可选域名名单放开不取消这些检查。现有下载校验不等于完整网络沙箱或DNS绑定保证，执行环境还须限制网络和权限。

本机DSH Desktop0.2.1-rc.2已有宿主派生Provider初始化证据：相同含[::1]环境，旧版失败、修复environment/direct通过；该证据无HTTP请求，只证明初始化兼容，不证明完整Host业务或供应商绘图。

## 12. 诊断、验收与交付数据

LLM HTTP失败记录位于业务`.replicator/errors/<diagnostic_id>.json`，包含操作、HTTP状态、model、response_bytes、response_sha256和脱敏error摘要。只提取受限字段；不持久化原始HTTP错误正文/请求头。成功返回但格式错误的LLM文本可能保存在私有`.replicator/llm/`用于本地维护，不应原样外发。

消费Agent优先用get_run/preflight/get_design，不读取SQLite或递归找Host日志。接口不足时报告：服务版本/策略、workspace、run_id/父子关联、image_id/index、phase/error_code、analysis_kind/attempts/http_status/diagnostic_id、成功图范围、已做操作和待操作者处理项。不能保证每个异常有diagnostic_id。

验收必须实际读图并覆盖完整checks。基础检查为composition/elements/actions/style/copy/identity/change_scope，可能另有custom、copy_replacement、text_theme。any fail→needs_revision；无fail但有uncertain→review_required；全部pass→accepted。哈希不一致、缺项/重复项拒绝。不能只比较输出与提示词。

局部交付按image_id合并父run成功图、分析恢复子run和修订子run的当前有效结果；保留来源run和旧图，不改旧数据库“填空”。交接文档不构成第二套任务状态机，MCP记录仍是运行事实来源。

## 13. Skill 实施和验证建议

以 [PRD的R01–R16与A01–A32](PRD.md) 为验收映射，将短入口、详细流程、恢复决策和示例分开按需加载。辅助代码只能做必要本地处理；运行时使用发现的schema，不绑定开发者本机路径或工具前缀。

现有回归可用于理解服务边界，不能替代新Skill行为评测：

| 测试文件 | 主要覆盖 |
|---|---|
| [test_mcp.py](tests/test_mcp.py)、[test_contracts.py](tests/test_contracts.py) | 实际SDK/stdio、工具/资源、输入与输出契约 |
| [test_routing.py](tests/test_routing.py) | 多项目身份、并发、重启/导入 |
| [test_analysis_recovery.py](tests/test_analysis_recovery.py) | 保留7成功+恢复4失败、缓存error、换词、request_id与有限scope |
| [test_postprocessing.py](tests/test_postprocessing.py) | 精确宽高、1%边界、raw/receipt、局部本地恢复、保留验收 |
| [test_network.py](tests/test_network.py) | IPv6/端口代理绕过、direct、CA与非法配置 |
| [test_background_execution.py](tests/test_background_execution.py) | 初始化/清理异常、后台诊断、原身份恢复 |
| [test_adaptation.py](tests/test_adaptation.py) | 原图基线、产品/品牌边界、文字主题与视觉验收 |
| [test_windows_paths.py](tests/test_windows_paths.py)、[test_atomic_windows.py](tests/test_atomic_windows.py) | Windows路径与并发原子写入 |
| [test_optional_limits.py](tests/test_optional_limits.py)、[test_operational_limits.py](tests/test_operational_limits.py) | 默认不限、显式限额及保留的安全边界 |

已有开发环境内的只读能力检查命令（不执行付费Tool）：

```powershell
$ErrorActionPreference = 'Stop'
$ProjectDir = 'D:\MCP\ecommerce-image-replicator-mcp'
Set-Location -LiteralPath $ProjectDir
uv run --no-sync python scripts/smoke.py --project-root $ProjectDir
if ($LASTEXITCODE -ne 0) { throw '协议能力检查失败，停止后续执行。' }
```

该脚本启动独立stdio连接，只证明目标安装的协议能力，不证明当前DSH已切换到新进程、代理可达或业务验收。Skill实际Host适配要在当前连接中复核。

开发方隔离运行现有门禁时使用本项目锁定环境及`.cache`临时目录；新Skill的行为评测用替身/断网保护，记录调用轨迹与成功文件hash，禁止读取实际密钥或触发真实收费。详细既有安装/保留证据见 [UPGRADE-PRESERVATION](docs/UPGRADE-PRESERVATION.md)，运行方法见 [消费端指南](docs/guidebook-of-ecommerce-image-replicator-mcp.md)。旧版 [MCP-CONTRACT-v0.1.2.json](docs/MCP-CONTRACT-v0.1.2.json) 只是历史快照，不得当作v0.1.7 schema使用。
