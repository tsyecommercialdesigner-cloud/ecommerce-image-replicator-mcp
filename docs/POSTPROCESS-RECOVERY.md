# 请求画布补偿与纯本地后处理恢复

维护源码新增，未发布；v0.1.6标签与附件保持不变。当前12工具，资源/提示各1。

尺寸归一化属于图片后处理，不改变模型选择、提示词、冻结输入或收费请求身份。对PNG/JPEG单帧输出，按两方向比例max/min-1计算宽高比偏差，不超过1%时以Lanczos归一化到请求画布，再按原预处理crop去补边、恢复原图完整宽高。尺寸一致不额外缩放。超过1%返回postprocess/provider_canvas_aspect_mismatch及实际/请求尺寸，保留raw；没有静默大幅拉伸、裁主体或填补缺失内容。

原例790×857的请求画布为800×864，供应商返回1206×1304，偏差约0.12%，最终必须为790×857。产物旁geometry.json与任务postprocess报告可审计尺寸、crop及补偿方法；尺寸正确不等于视觉验收通过，低分辨率放大不恢复真实细节。

`recover_postprocess(image_ids, run_id=...)`（固定模式兼容thread_id）只支持v2原任务；显式非空唯一image_ids，受工作区绑定和同一execution.lock保护。必须有downloaded image receipt和保留raw；新receipt保存实际请求transform，旧receipt使用冻结参考图重建几何。没有网络、Provider构造、分析、下载、绘图或自动vision验收。成功结果review_required，保留旧失败快照postprocess_history；原manifest、receipt、raw和其他成功结果不变。已成功图仅校验哈希并返回generated_preserved。

按图返回recovered/generated_preserved/rejected，任一拒绝则MCP isError=true；已经恢复的部分保留，重复调用幂等。缺文件、未下载、哈希变化、几何冲突和比例超差有独立诊断。无原始文件不能用此入口自动下载；不接受Agent提供任意图片路径。也不使用prepare_analysis_recovery/prepare_revision替代。调用之后直接get_run、视觉检查和record_review，不用execute_run完成收尾。

该入口不改LangGraph检查点；本地恢复标记让后续execute跳过该图原检查点，保留后续显式验收，不重跑该图的分析、绘图或vision验收。同run其他图仍可能收费，手动验收后不要为恢复再执行。生成成功和验收通过分别记录。

开发回归覆盖尺寸归一化、补边裁切、PNG/JPEG、两模型默认档、大小缩放/比例错误、原尺寸精确还原、不覆盖、旧receipt、保留7图、并发锁/重启和实际SDK错误语义。均为本地fixture或假供应商，不操作成员任务或付费请求。

2026-10-28本地串行执行 `uv run --no-sync python scripts/check.py`：243通过、1项平台跳过；格式、lint、mypy和秘密检查通过。实际SDK stdio发现12工具/1资源/1提示，新恢复工具成功与isError结构化失败均覆盖。日志 `.cache/validation/postprocess-quality.log`；早期两轮重叠检查共用临时目录的干扰结果已弃用。尚无本改造的远端CI、实际消费Host或真实供应商验证，未提交、推送或发布。
