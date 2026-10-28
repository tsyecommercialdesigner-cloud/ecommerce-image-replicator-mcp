# Windows并发路径误拒绝修复（v0.1.4候选）

## 根因与稳定复现

v0.1.3 CI的脱敏栈指向 `inputs.safe_path` 的 `is_relative_to` 判断，错误是ValueError，而非供应商失败。
核对本机CPython 3.12的 `Lib/ntpath.py:realpath`：非严格解析先调用GetFinalPathName，再查找已存在的父目录，最后尝试去除Windows扩展命名空间前缀。
输出目录并发创建时，两次探测可能分别得到WinError2（文件不存在）和3（目录不存在）。
stdlib只在前后错误码相同时去除前缀；不同时可能保留 `\\?\`。
于是同一物理工作区出现 `E:\project` 与 `\\?\E:\project\output` 两种Path表示，直接比较包含关系会误判越界。
v0.1.3的原子替换拒绝重试处理的是另一条写入路径，不能消除此表示差异。

`tests/test_windows_paths.py` 控制最终路径探测顺序，实际执行stdlib realpath算法，覆盖2→3和3→2。
修复前两项确定失败（Path escapes authorized workspace），报告 `.cache/validation/v014-red.xml`；修复后两项通过。
这不是靠概率重跑得到的结论，也没有触发供应商调用。

## 修复边界

- 解析后把普通DOS/UNC路径和对应的扩展前缀路径统一为比较表示；不额外探测文件系统。
- 先做包含检查，再按已解析root的原表示构造返回值，使后续relative_to及既有run_id工作区绑定保持一致。
- 允许根比较使用相同表示；注册记录、thread_id、run_id、供应商task_id与checkpoint格式不改变。
- 拒绝设备命名空间、转换后含尾点/尾空格等不等价路径；相对路径检查继续拒绝绝对、驱动器相对、父级跳转及Windows ADS。
- 原有符号链接/junction、真实解析后越界、不同盘符/UNC主机/共享名检查继续生效。

## 回归范围

覆盖扩展/普通DOS和UNC、真实越界、设备及歧义路径、junction、驱动器相对与ADS、
5轮×40文件×8线程的真实并发目录创建/原子写入，以及扩展根的既有任务绑定重启恢复。
Windows定向23项通过；完整质量与远端CI结果以实际交付记录为准。
POSIX不会应用Windows命名空间转换。权限拒绝、真实越界及无法解析的路径仍报错，不能把这些错误当成本缺陷绕过。

v0.1.3及更早标签/附件保持原样，成员需升级实际服务到包含修复的版本，再沿原run_id查询和恢复。
