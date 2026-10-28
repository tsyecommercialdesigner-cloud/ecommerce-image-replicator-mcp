# 环境代理与IPv6绕过兼容

维护源码新增，未发布；v0.1.6发布标签/附件不变。默认无需改现有Host参数。

## 模式与边界

`--proxy-mode environment`（默认）使用标准库getproxies与锁定HTTPX 0.28.1相同的大小写优先级及适用平台系统代理回退。保持HTTP_PROXY/HTTPS_PROXY/ALL_PROXY、NO_PROXY的域名/子域、端口、localhost、IPv4、裸IPv6和 `*` 语义；额外识别合法独立方括号IPv6，例如 `[::1]`、`[2001:db8::1]:8443`，构造成正确的绕过路由。不只是删除 `[::1]`，没有裸地址副本时也保留绕过语义。显式URL条目仍按HTTPX规则处理。不新增CIDR等上游原本不支持的匹配语义。

`--proxy-mode direct` 显式让本MCP的分析、绘图、查询及HTTPS下载忽略环境/系统代理；不是关闭TLS，也不关闭系统VPN/TUN等网络路由。两种模式均继续使用SSL_CERT_FILE/SSL_CERT_DIR及正常证书校验。业务API Key仍按安装根.env→进程→Windows用户读取，文件字段仅Key，不自动导入NO_PROXY等环境变量。

实现使用HTTPX公开的transport/mounts接口，显式基础transport阻止HTTPX再次解析未规范化的NO_PROXY；不使用运行时私有API、不修改os.environ、不替换进程环境、不改注册表、Host或用户代理。外部传入测试client仍直接使用。解析错误脱敏失败，不静默退回直连，不记录含认证的代理URL、环境原值或CA路径。

## 配置与复核

默认不加参数，当前连接资源应显示proxy_mode=environment及no_proxy_compatibility=httpx-bracketed-ipv6-v1。仅需直连时，经授权由操作者将以下两个元素追加到当前服务args，保留其他配置：

```json
[
  "--proxy-mode",
  "direct"
]
```

这是args追加片段，不是完整Host配置。重启实际Host管理的MCP子进程后读资源复核proxy_mode=direct，不能用另起命令行实例代替；缺字段/参数时报告实际版本不支持，交操作者升级，不自行改源码。恢复代理模式可删去这两个元素或将direct改成environment后重启。模式不改变工作区绑定、原run_id、供应商receipt或成功图；执行恢复仍按原授权，配置变更不授权收费。

## 对消费Agent报告的核验

2026-10-28只读核对当前安装的DSH app.asar，确有LOOPBACK_NO_PROXY同时列出localhost、127.0.0.1、::1、[::1]及withLoopback合并逻辑、`*`短路。因此跨语言解析不兼容的核心判断有依据。安装包SHA256为 `47874618bf5b3011fcaac10cd4c85f69da333e70d4f99b921207c78d0999512a`；只证明该安装包的静态代码，不推断所有版本、每种profile/子进程覆盖顺序或消费任务的实际调用链。

“MCP必然起不来”不准确：本项目延迟创建Provider，可能连接、准备均正常，直到执行时客户端初始化失败。`/v1/models`的401只证明那一时刻那个路径可达，不证明带密钥分析、绘图、查询或文件域名可用；未在此执行真实网络探测。451也不能单独证明具体地域限制。

不能采用遍历os.environ并删除所有以 `[` 开头条目的补丁：它会误删其他IPv6/端口规则并影响同进程其他客户端。本次改造保留规则语义及独立客户端范围。

官方依据：[HTTPX环境变量](https://www.python-httpx.org/environment_variables/)、[公开传输与路由接口](https://www.python-httpx.org/advanced/transports/)。本地回归使用真实HTTPX构造和假transport请求验证，不访问供应商或真实代理；具体消费Host联调另计。

2026-10-28最终串行质量门禁 `uv run --no-sync python scripts/check.py`：256通过、1项平台跳过，格式/lint/mypy/秘密检查通过；包含前一轮尺寸恢复回归与新增13项代理/直连测试。真实SDK stdio确认默认environment和显式direct资源字段。独立离线探针复现原HTTPX的 `Invalid port: ':1]'`，兼容客户端构造/关闭成功，无HTTP请求。证据：`.cache/validation/proxy-compat-quality.log`、`proxy-compat-probe.json`。未修改成员数据、Host/用户环境、密钥或代理配置，未提交、推送或发布。

## 真实DSH宿主初始化核验

2026-10-28用户授权直接在本机DSH进程测试。已通过当前运行的DSH Desktop 0.2.1-rc.2宿主本机调试接口，让实际宿主派生诊断Python子进程；核对宿主spawn PID与Python运行时父PID，使用现场安装版相同Python 3.12/httpx 0.28.1依赖。没有修改安装源码、Host配置或代理环境，也没有向消费Agent发送消息。

三组均继承宿主实际环境：HTTP/HTTPS代理存在，NO_PROXY含裸::1及[::1]。加载D盘现有v0.1.6安装源码时Provider初始化复现InvalidURL；加载本仓库修复源码时，environment和direct两模式均成功创建并关闭Provider。重复执行结果一致，代理/CA环境前后未变。用户级NO_PROXY不含[::1]，宿主及其此次实际子进程含该条目，支持本现场的宿主注入判断，不推广到所有Host版本/profile。

测试使用假凭据且不调用read_keys，不发送HTTP请求；审计钩子禁止诊断阶段DNS/连接，三组均无网络尝试。只覆盖真实宿主下的客户端初始化，不代表实际MCP工具链、供应商网络或绘图验收。既有DSH/MCP进程、工作区、run_id和成功产物保留；没有安装或切换修复版，现有正式v0.1.6不会自动获得补丁。证据 `.cache/validation/dsh-live-proxy/results.json` 及同目录初始化探针；诊断子进程与调试连接均已退出。
