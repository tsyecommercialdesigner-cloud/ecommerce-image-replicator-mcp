# scheduled后停在prepared：后台初始化异常缺口

本记录对应v0.1.4后的维护源码修复，尚未发布，不改变v0.1.4标签或附件。

## 已确认的代码原因

v0.1.4的Service.execute先返回scheduled，由asyncio任务执行后续工作。
worker在try之外构造Provider，构造成功后才写running。构造失败时没有blocked记录，
finally也不会清理tasks；get_run退回默认prepared，所有job保持not_submitted。
同一服务再次execute还会被遗留的tasks项当成正在执行，不能恢复。
此外，旧finally中provider.close失败会跳过tasks.pop，让已完成或失败任务继续占据注册表。

## 稳定复现与验证边界

tests/test_background_execution.py覆盖构造异常注入、真实httpx读取无效HTTPS_PROXY协议、
执行成功/失败时的清理异常、首次运行前取消、journal无法写入。
前三个原始用例在旧代码均失败；构造失败实际得到prepared，清理失败残留finished task。
修复后6项通过，使用测试凭据且没有任何网络或真实供应商请求。
完整本地质量门禁201通过、1项平台跳过，格式/lint/mypy/秘密检查通过；尚未进行本补丁的远端CI或实际消费Host联调。
失败阶段、异常类型可见，fixture中的认证/异常正文不进入日志和get_run；替换测试Provider后沿同一thread恢复，无需重冻输入。

无效代理仅是可复现触发条件，不是对消费端配置的诊断结论。
当前反馈没有初始化异常堆栈，不能据此认定其代理有误、后台一定已退出或日志改存位置。
多个服务进程也不足以判定故障，应先核对当前连接返回的工作区绑定及脱敏stderr。

## 修复边界与恢复

Provider初始化移入异常保护，先写running和phase=provider_initialization；成功后进入execution。
初始化失败写blocked、phase及异常类型，正文使用固定脱敏信息；stderr仅记录任务标识、阶段和异常类型。
清理异常不覆盖已保存的执行结果，任务注册始终清理；done callback接收未捕获异常，
日志数据库自身无法写入时至少记录脱敏stderr，不声称数据库已成功保存blocked。
首次运行前取消会清理注册并尽力记录interrupted，不自动重试或提交供应商请求。

scheduled仅说明调度受理。消费Agent有限间隔查询后若仍是prepared/not_submitted，
保存原run_id及当前连接的状态，向操作者报告并获取脱敏stderr；不要忙循环execute，
不要创建新run绕过、遍历Host配置、擅自清空任务数据库或终止所有服务进程。
由操作者修正已确认的环境问题或更新实际服务并重启当前连接后，先get_run核对逐图状态，
再按已有授权恢复同一run_id；unknown仍先核查原供应商task_id。
本补丁不更改目录、任务标识、冻结manifest或receipt/checkpoint格式，不迁移任务，也不自动提交或发布。
