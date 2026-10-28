# 电商竞品图复刻 MCP：消费端 Agent 使用手册

本文写给调用 MCP 的 Agent，不是 MCP 开发约定。先完整阅读，再准备输入或执行；工具 schema 和当前连接返回的契约优先于示例。不要声称完成未执行的检查。

本手册适用于已发布v0.1.6新增的 `preflight_run`、`prepare_analysis_recovery`；发布目标 `1459ebd0e4b63de6bc5a75e41458846f7e6dce83`，安装和升级以在线MANUAL为准。已发布 v0.1.5 及更早版本没有这两个工具；不能只复制手册就改变服务能力。发现工具缺失时报告版本差异，请操作者更新实际服务并重启当前连接，不自行安装开发版、改 Host 配置或杜撰调用。

## 1. 接手时先做什么

1. 发现 Host 实际暴露的工具名称及参数。名称可能有 Host 前缀，不猜前缀。
2. 读取 Resource `replicator://input-contract` 和 Prompt `prepare_inputs`。后者不是 Tool。Host 不桥接资源/提示时，通过本手册及实际工具 schema 核对能力，不为读不到资源而调用收费工具试连接。
3. 记录当前版本、`workspace_mode`、`allowed_roots`、`state_directory` 和限制策略。新恢复能力标识为 `analysis_recovery_policy=explicit-pre-image-child-v1`。有标识仍须核对两个工具的发现结果。
4. 确认这次是新任务还是接手旧任务；有 run_id 先 `get_run`，不要重新 prepare。确认用户已授权的图数、范围和费用；本手册不授予费用或文件权限。

不要去翻服务源码、SQLite、注册表、进程列表或递归遍历 Host 配置来猜用法。接口诊断不足时保存脱敏证据，交给操作者；没有额外授权不修改私有 Host 配置、代理、密钥或终止进程。

## 2. 工作区、身份和凭据

安装目录与业务工作区不同。任务模式启动不必带 `--workspace`；新任务由 `inspect_inputs`、`prepare_run` 显式传入业务项目绝对路径。它不会自动跟随 Agent 当前目录。

后续工具用返回的 run_id；不要混用 run_id/thread_id，也不要把同一 run_id 指向另一个目录。固定模式兼容原 thread_id；旧任务切到任务模式时，只有尚未绑定的 thread_id 才需 `import_run(workspace, thread_id)`。已有 run_id 直接查询。

同一工作区、相同冻结输入重复 prepare，得到同一稳定身份是正常行为，不代表旧任务残留。不要为了换 ID 随意改 brief、改选图或删数据库。

密钥由 MCP 从实际安装根 `.env` → 进程环境 → Windows当前用户环境逐字段读取，仅缺失可回退，空值/非法值不回退。业务目录不另建密钥文件，不把密钥放入 brief/提示词/日志。用户环境变量已存在时，不用空 `.env` 字段遮蔽它。

升级/重启保留安装根或自定义state-dir的索引、各业务目录完整 `.replicator/`、receipt/checkpoint、输入和 `artifacts/`。run_id不能代替备份。目录不移动，数据不清空。

## 3. 新任务的输入与边界

```text
业务工作区/
  references/<group>/*.png 或 *.jpg
  products/*.png 或 *.jpg
  brief/*.md
  brief/design.json          可选，结构化产品事实和默认增量
  prompts/<group>.json       可选，每张参考图对应一个增量对象
```

先 `inspect_inputs(workspace)` 取得自然排序和稳定image_id。`prompts/<group>.json` 必须对应整组图片，每图一个元素，不能因为只选3张就把12个元素缩成3个。选图在 `options.selected_image_ids` 中使用 inspect 返回的真实ID。人类说的“第02张”不是image_id；工具返回的index从0开始，不能与order混用。

原始竞品参考图是构图、关键对象及关系的对齐目标，保留污渍、水迹、手部、擦拭/拉取动作和对照角色。可按事实修改用户产品文案、规格、材料、外观及品牌配色；无明确艺术风格要求时保留参考图风格。换色不自动授权水彩化。少量不改变表达主旨的创意差异可接受。

不编造尺寸、片数、材质、克重或认证等事实。文案待修订且不知道正确内容时询问用户；用户明确坚持不修改时才保留未解决部分的参考文案。产品身份和品牌/文字颜色的必要替换仍保留，不把旧成图改标成通过。

`texts` 是明确的最终文字块，`text_replacements` 是对已提取文字做带来源的字面替换，两者不能同时非空使用。`scene`/`instruction` 仅能补充产品/品牌，不能授权删物、改构图或反转互动关系。

### 谁负责文字和场景分析

默认由MCP的LangGraph内LLM节点执行，MCP请求供应商，文字/场景结果分别缓存。消费Agent负责产品事实、合法增量和最终验收，不要求每次自己抄图。

当有效增量的texts/scene为null或缺省时，对应分析节点使用成功缓存或请求模型；显式提供某一字段则仅跳过该字段的分析，两项都提供则两项都跳过。preflight中provided表示人工/增量覆盖，succeeded才表示有效LLM缓存，不能混称“模型分析成功”。

不要认为“补了一半，另一半必定重新收费”：另一半若有有效缓存，会复用。先查preflight，不因旧error标记认为缓存失败。持续供应商失败时，具备读图能力的Agent可以在核实后提供人工覆盖，但这不是默认恢复方案，更不能填写占位内容来让节点“无事可做”。

- texts须为核实后的最终文案，保留应有文字层级、位置和产品/品牌适配。texts=[]是明确的空文案，不是“自动提取”，不能把它当成跳过OCR的开关。
- 实测像素坐标不能原样冒充归一化框。以EXIF方向校正后原图宽W、高H换算：x=1000*x_px/W，width=1000*width_px/W；y=1000*y_px/H，height=1000*height_px/H，且框不越出0..1000。
- scene覆盖仍仅作产品/品牌说明，不能取代原始竞品参考图，更不能编造对象、改变污渍/手部/擦拭关系。生成仍必须携带完整原图。
- 对已冻结失败任务，覆盖值通过prepare_analysis_recovery的完整delta提交；改磁盘文件不会让原run读取新值。准备不收费，execute仍可能产生其它分析/绘图费用。

## 4. 最短安全调用顺序

| 操作 | 目的 | 供应商请求/费用 |
|---|---|---|
| inspect_inputs | 顺序、ID和输入位置 | 无；可能初始化本地日志 |
| prepare_run | 冻结输入，获得身份 | 无；写快照和本地状态 |
| preflight_run | 逐图检查已知分析/文本替换 | 无；可能重建本地预处理图片 |
| execute_run | 生成或恢复已授权任务 | **可能收费：LLM分析及绘图** |
| get_run / get_design | 进度、产物、契约 | 无；不主动查询供应商 |
| record_review | 写入图像哈希绑定的验收 | 无供应商请求 |
| prepare_analysis_recovery | 准备出图前失败的恢复任务 | 无，不执行 |
| prepare_revision | 准备已有成图的视觉修订 | 无，不执行 |
| reconcile_submission | 核查已有供应商task_id并绑定 | 有供应商查询；不提交新绘图 |

首次执行前先做逐图preflight。文字尚未提取时，返回 `analysis_required`/`pending_text_analysis` 是正常的未完成检查，**不是文案已验证通过**。可以在用户已授权分析/生成的范围内execute，运行时会先分析文字并检查替换，之后才分析场景和绘图。

`get_design` 的 analysis_required 仅表示契约尚未构造，不能据此断定服务故障、代理有误或预算缺失。更细诊断用preflight，不读SQLite猜测。

execute返回scheduled只说明调度受理，不能报告出图完成。按有限间隔查询get_run；例如5秒、10秒、20秒后仍无变化就报告状态和脱敏诊断，不忙循环execute。用户授权小样本就只执行该选图任务，不能自行扩到全套。

## 5. 如何读状态与错误

| 返回内容 | 意义与下一步 |
|---|---|
| prepared / not_submitted | 本地尚未观察到该图绘图receipt；不等于没有发生LLM分析费用 |
| running | 当前后台执行中；等待查询，不并发重复提交 |
| partial | 有成功产物也有空缺；先保留成功部分，再逐图诊断 |
| blocked + phase=provider_initialization | 客户端初始化失败；按异常类型交给操作者修正环境，重启后沿原身份恢复 |
| phase=analysis | 用analysis_kind/cache_key/attempts/schema_errors定位文字还是场景、请求还是校验，不猜是构图类型不受支持 |
| analysis中retry_available | 上次失败但剩余重试尚未耗尽；修正已确认条件后沿原run恢复，不另开额度。更改文案仍需提交完整delta |
| phase=copy_preflight + copy_replacement_unmatched | replacement_indexes指出不匹配的规则；对照本图transcription改该图增量 |
| analysis_*_failed | 区分provider_request、response_storage、json_validation、schema_validation、identity_validation；没有原始响应正文不是允许捏造堆栈 |
| unknown / submitting / pending / success且未保存完成 | 沿原任务恢复/核查原task_id，不能走分析恢复或新建任务绕过 |
| generated_preserved | 已有成图，预检不改动、不重生成；需要视觉修改走revision |
| recovery_prepared / recovery_run_id | 已准备独立恢复任务；后续查询该ID，不能把原任务反复execute当作新恢复 |

分析成功的`result`不能因旧error标记被当成失败。新执行会清除活动error，并保留失败历史；preflight遇到旧缓存时以经过schema/ID校验的成功结果为准，可能提示stale_error_marker。不要因为错误字段曾存在就重花分析费用。

blocked不是跨阶段通用的“永远终态”。普通中断可沿原ID恢复，但已耗尽的分析缓存不会因为重复execute自动重置。绘图未知结果、分析耗尽和文本规则错误必须分开处理。

### 错误在哪一阶段，就改对应层

| 阶段/可见证据 | 应检查或修改什么 | 恢复方式 | 不要做什么 |
|---|---|---|---|
| inspect/prepare拒绝；JSON、数组长度、图片格式或路径错误 | 新任务输入文件与实际契约；prompts整组顺序和长度；操作账号权限 | 改正后inspect/prepare。已冻结旧任务先保留并确认是否需要新输入任务 | 删库、换锁、编造规格或强制覆盖文件 |
| scheduled后prepared；或provider_initialization | 当前连接版本及脱敏异常类型；操作者确认代理/TLS等环境问题 | 操作者修正已确认配置/升级并重启当前连接，再沿原ID查询恢复 | 改brief、重复prepare、因进程多就杀进程 |
| phase=preprocess；冻结图片哈希/预处理失败 | 原冻结输入是否被改动，文件访问是否正常 | 保留现场，由操作者恢复原快照/访问条件；确需换图则重新确认新任务范围 | 把它当scene格式错，改LLM提示词或重置分析次数 |
| phase=analysis，kind=text/visual，schema_errors有images/scene等路径 | 模型响应结构、身份与schema；输入类型本身不一定有错 | preflight确认失败kind，仅为该kind准备显式恢复 | 因纯图标/卡片图报错就断定MCP不支持该构图；填假scene绕过 |
| phase=analysis，请求失败/六次耗尽 | 供应商/传输状态及diagnostic_id，成功缓存是否可复用 | 排除持续故障后只重开失败kind的有限额度；准备不收费，execute可能收费 | 原样循环execute或把有历史error的成功result当失败 |
| phase=copy_preflight；unmatched/overlap/chain/conflict及规则索引 | 该图transcription、replacement_rule_source、effective_delta；修正该图的完整delta | prepare_analysis_recovery，保留其它产品/品牌增量；通常不重置已成功分析 | 用prepare_revision；全局删掉所有替换；改磁盘文件后假定旧run已更新 |
| phase=resolve_design/design_preflight | 最终文案、禁用claim、产品属性/品牌色与契约是否一致 | 出图前、无receipt时可准备带完整修正delta的分析/文案恢复 | 为过校验放宽原图构图、对象、互动边界 |
| phase=generate；已有image receipt或unknown/pending | 原供应商任务状态，task_id及是否已受理 | 原run恢复/必要时reconcile；只有已有成图的视觉修改才用revision | 开分析恢复、换run或直接API重提 |
| phase=postprocess；供应商成功但本地保存/哈希失败 | 保存权限、下载限制、原receipt与产物路径 | 修正本地条件后恢复原操作、下载原任务结果 | 改文案、重置分析或重新付费绘图 |
| review_required/needs_revision/phase=review | 原图+产品图+成图的实际验收证据，review检查覆盖/哈希 | 记录验收；已有成图需改时prepare_revision，再执行及复验 | 直接把旧失败图标成通过，或删除成功图重来 |

旧版本可能只给笼统ValueError，不能根据异常类猜是scene还是文案。新preflight能定位时用它；能力缺失则报告缺口，不连续尝试互不适用的工具。

## 6. 逐图文字替换预检

先对整个run调用：

```json
{
  "run_id": "替换为prepare_run返回的真实run_id"
}
```

以上是 `preflight_run` 参数；可追加 `image_ids` 数组只检查指定图片。它返回每图status、analysis.text/visual、copy_status、transcription及原冻结delta。

1. 只给确实出现旧文案的图片配置该条替换。例如某页没有“青苹果”，不要给它套用“青苹果→新主题标签”的规则。
2. 缺文字分析时标为pending，不猜匹配成功，也不要编造scene/texts去绕过分析。
3. 不匹配、重复/重叠规则、替换链或冲突输入会阻止该图继续；保留其它已通过图片。
4. 修正时保留该图其它产品属性、主题色和来源。不得为了通过校验把必要的产品身份替换全删掉。

### “全局青苹果规则”这个例子该怎么处理

如果preflight显示 `replacement_rule_source=product_context.defaults.text_replacements`，说明规则来自冻结的 `brief/design.json` 默认值；查看effective_delta才是该图最终生效的增量，delta是原逐图覆盖。

- 02/03没有“青苹果/green apple”：只在这两张的完整逐图delta中覆盖text_replacements。若整组默认规则都不适用于这两张，设为 `[]`；有其它必要规则时保留它们，不能一律清空。
- 07/08确实有该文案：保留原规则。如果失败的是visual分析，只指定 `retry_kinds: ["visual"]`，不要因为其它页不匹配而删除它们的标签替换。
- 已成功的7张不进入updates，也不去改它们的artifact、receipt或验收记录。

**冻结后编辑磁盘上的brief/design.json或prompts文件不会改变旧run。** 对旧run出图前失败应使用恢复工具提交修正。若为今后的新任务整理默认规则，可以把不通用的规则下沉到逐图prompts，但这不能替代对旧任务的恢复，也不能当成重做整套图的授权。

## 7. 只恢复分析/文案失败的图片

适用：原图job_result为blocked，并且**该图没有任何绘图receipt**。原任务已成功的7张不选；未知/已提交/已有成图不适用。prepare_revision必须已有下载并后处理的成图，不是分析失败的替代入口。

### 先看诊断，再准备

1. 原run_id调用get_run和preflight_run，明确每图是copy问题，还是哪个分析kind失败。
2. copy问题：在完整冻结delta上只改有问题的规则；retry_kinds可省略，成功文字缓存会复用。
3. 分析重试耗尽：只对确已阻塞/耗尽的 `text` 或 `visual` 指定retry_kinds。scene字段对应visual，不叫scene retry。retry_available表示还有剩余次数，沿原run恢复而不重置额度。
4. 终态HTTP错误不能原样循环重试。操作者已修正相关配置后，才可显式设置allow_terminal_http_retry=true；这不是让Agent擅自改代理/凭据的授权。

`prepare_analysis_recovery` 的纯分析重试参数结构：

```json
{
  "run_id": "替换为原run_id",
  "request_id": "analysis-recovery-round-1",
  "updates": [
    {
      "image_id": "替换为失败图的真实image_id",
      "retry_kinds": [
        "visual"
      ]
    }
  ]
}
```

文案修正中的delta是**完整逐图替换对象**，不是零散patch。下面仅说明参数构造，不是Shell命令或收费执行：

```python
fixed_delta = dict(preflight_row["delta"])
fixed_delta["text_replacements"] = corrected_rules_for_this_image
update = {"image_id": preflight_row["image_id"], "delta": fixed_delta}
```

corrected_rules须来自该图transcription和已有产品事实；复制原delta保留instruction/design/品牌配色等。空数组只能移除已确认不适用于该图的规则，不能删掉必要的替换。

### 准备结果不是执行结果

- isError=true且status=preflight_failed：未建立恢复任务，检查内嵌安全诊断并修正，不execute返回的原ID绕过；错误响应不回传文案/增量正文，需要原始转录时单独调用preflight_run。
- status=recovery_prepared：只创建关联恢复run_id，不调用模型。对选中失败kind开新的有限重试scope，保留旧缓存和失败记录；成功kind不重置。
- 网络/工具响应不明时，用**同一request_id和同一updates**重试准备，返回同一恢复任务。不要换request_id碰运气；已建立恢复任务后，同ID换参数会拒绝。已有关联恢复时跟随recovery_run_id。
- 已有费用授权明确覆盖本次恢复时，按该授权对恢复run_id调用execute_run；未覆盖或范围扩大时先补充确认。分析和后续绘图都可能收费，准备工具本身不提交。
- 原run_id保留原7张成图和失败历史；恢复run_id只含所选失败图，parent_run_id指向原任务。汇总交付时按image_id合并两个任务的结果，不改写旧数据库、覆盖成功文件或把旧失败图标成通过。
- 原任务已转向恢复的图片不会再由原任务重新处理。若恢复再次失败，先查恢复run_id，再在该恢复任务上准备下一次显式恢复；不回到原任务重复开分支。

新入口不改变原始参考图、产品照片、冻结brief或工作区绑定。需要变更产品事实/全局主题时不是分析重试，应另与用户核对任务范围。

兼容边界：新版可读取旧v2任务并准备恢复，但旧v0.1.5不识别新恢复指向和retry scope。建立恢复后不要在同一工作区混用新旧服务执行；不能承诺把新恢复任务降级到旧版仍能安全执行。升级/回滚交给操作者，保留索引和数据，不删新记录迁就旧版。

## 8. 视觉验收和已有成图修订

逐图检查参考图、用户产品图和产物，核对核心构图/对象/动作、产品身份、文字内容与颜色、艺术风格。通过record_review提交绑定原图/成图/契约哈希的完整检查；generation_complete不等于验收通过。

已有成图需调整时用prepare_revision，只选需要修改的图片并提供完整delta。准备后仍需对新run执行和验收；原图和原成图不删除。成功文件被外部改动后，不伪造哈希重新验收。

## 9. 环境与限制：不要再走的弯路

- 新策略opt-in-v1的null表示不限制，不是未配置。三项预算参数只在用户显式设置时生效；显式0不是无限。旧v0.1.2及更早仍有旧行为，报告版本差异，不扫描Host配置。
- 默认不限额不取消供应商限制、有限自动重试、路径/哈希/权限检查和用户费用授权。分析失败六次已可能产生LLM费用，不能承诺“没有出图就免费”。
- 对本项目锁定HTTPX 0.28.1，NO_PROXY使用 `localhost,127.0.0.1,::1`，不要加 `[::1]`。IPv6在完整URL里才使用例如 `http://[::1]:10888` 的方括号形式。不要自行修改操作者环境；修改后重启当前Host/MCP，让新进程继承值。
- v0.1.5已修复Provider构造异常不落盘及清理注册残留。它让错误可见，不自动修正NO_PROXY。没有历史stderr不能伪造堆栈；日志未记录某异常也不能证明该异常没有发生。
- 缺少可用诊断就报告准确的run_id、image_id、阶段、状态和异常类型，不根据进程数量判根因，不全盘找日志，不杀掉所有服务实例。
- get_run/local preflight无供应商请求；reconcile有查询，execute可能收费。权限拒绝不能通过Shell或直接API绕过。

## 10. 接手与交付清单

给下一位Agent留下：当前业务目录、版本/策略标识、原run_id及关联恢复run_id、逐图image_id/状态/异常code、成功产物路径及验收状态、仍缺的用户事实或授权。不要留下密钥、代理认证URL或原始供应商响应。

本文件在仓库 `docs/` 维护；`output-docs/docs/` 提供相同的可复制副本。把三种约定之一放到消费项目根目录时，必须同时合并相邻 `docs/guidebook-of-ecommerce-image-replicator-mcp.md`，保留原文件，不覆盖项目已有开发约定。三种约定只是入口，不代替当前连接的schema。
