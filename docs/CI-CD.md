# 分阶段 CI、候选验收与单一发布入口

维护实现日期：2026-11-14。本文对应仓库的工作流与脚本变更；在提交、合入并完成远端运行之前，本地验证不代表新工作流已经在线生效。既有 v0.1.7 及更早发布的目标、标签和附件保持不变。

## 1. 触发与分工

| 阶段 | 实际入口 | 执行与结果 |
|---|---|---|
| feature/* → dev | ci.yml，pull_request | 根据改动分为 docs/light/full；固定最终检查名 `CI gate` |
| 合入 dev / 推送 feature | 无 push 工作流 | 不重复 PR CI，不执行 CD |
| dev → main 发布 PR | ci.yml，pull_request | 完整 Windows/Linux 验收；Linux 保存刚完成安装验证的候选产物 |
| 合入 main | ci.yml，push | 查关联已合并 dev PR，校验候选来源/摘要与完整 Git tree；相同则复用，缺失/不符则完整验收并生成新候选 |
| 发布后文档回填 | dev → main PR，预先加 `delivery-docs` 标签 | 只有分类确实为纯文档才轻检查；合入 main 同样轻检查，不生成新发行物或发布 |
| 正式发布 | release.yml，workflow_dispatch | 只能选 main；输入 tag 与 main_run_id，使用 release 环境及单一发布并发组，发布已确认的原字节 |

不使用标签 push、Release 事件、workflow_run 或 pull_request_target 自动发布。Reusable `validate.yml` 只有 workflow_call，不构成第二个发布入口。PR 的 token 只读，不接触供应商密钥；只有正式发布 job 获得 contents:write。

单人维护的评审由维护者本人、Agent 与 CI 协作完成，不要求其他人批准。Agent须记录实际评审的内容与问题；自动检查成功不替代评审或当前授权。

## 2. 按改动检查

`scripts/ci_policy.py` 负责分类及阶段判断，`scripts/ci_checks.py` 执行轻检查：

- docs：Markdown链接、代码围栏、JSON示例、适用JSON/TOML配置解析、diff格式及秘密扫描。检查已删除文件的引用时，仍以当前存在内容为准；完整发布验收会解析所有版本化文档。

本地链接还必须出现在Git交付清单中，避免开发机上存在但干净checkout缺失的私有brief掩盖断链。测试清理仅限工作区.cache内的临时目录，Windows Git只读对象可清除只读位后重试；真实ACL/占用失败仍报错，不将清理失败吞掉。
- light：代码/测试改动运行变更Python文件的ruff格式与lint、src类型检查、基础契约/stdio测试及相关模块测试。network、diagnostics、images有明确映射；共享控制流、测试fixtures或无法确定依赖影响时保守运行完整测试集，但不因此重复构建/审计/发布。
- full：脚本、工作流、锁、依赖/构建配置、未知文件类型及安装/Host行为改动，走完整验收。文档中修改安装命令、指定Shell/Python代码或MCP配置也升级为full。`delivery-docs` 标签不能把代码或安装命令改动降级。

完整验收包括共享质量门禁、全部测试、文档、工作流actionlint、依赖审计、wheel/sdist构建及两种包的隔离无开发依赖stdio检查。Windows另跑原有升级/回滚保留验证。所有业务API使用替身或不调用；不读取真实业务工作区和凭据。

API文档引用的2026-10-20外部历史验证归档不随仓库交付。文档检查对现有文档/目标的精确白名单输出“未在本地检查”，不伪称归档存在；新链接及同名链接出现在其它文档时仍按普通断链处理。不放宽为忽略整个validation目录。

## 3. 候选与 main 合并确认

逻辑候选名为 `release-candidate-<run_attempt>`，保留30天。载荷包含wheel、sdist、candidate.json。清单记录仓库、PR编号/head SHA、实际测试checkout SHA/tree、run ID/attempt、版本、Python/uv、锁摘要和两包SHA256。

构建发行包时禁用uv自动生成输出目录的.gitignore，防止构建辅助文件混入候选清单；候选仍严格只接受两个发行包与candidate.json，不能通过扩大白名单掩盖额外文件。此问题由首次dev→main候选记录步骤实际检出，失败运行未产生可发布候选。

main查找本次合并的同仓库dev PR及其成功CI，只下载对应head和attempt的候选；核对工作流路径、运行结论、归档SHA256、扁平文件白名单、包摘要、PR身份及完整tree。拒绝过期/重复条目、额外文件、符号链接、路径穿越和篡改。

GitHub API权限或服务故障若连关联PR/运行来源也无法读取，则直接令确认失败，交操作者处理；不把权限拒绝伪装成验证通过或修改凭据绕过。已定位候选的缺失、格式/摘要问题可回退完整验收，不能复用损坏的下载内容。

当前项目使用静态版本的hatchling构建，不依赖merge commit SHA。测试checkout与main SHA可以不同，完整tree一致时可复用包；发现动态版本、VCS版本或构建hook时不走该快速复用路径。该策略有意保守：任何tree差异、候选缺失/过期或无法核实的构建输入都回退完整验收。不能仅凭源码目录相同或缓存命中复用。

main确认后生成 `verified-release-<run_attempt>`，包含：

1. 原wheel、sdist、candidate.json（字节不变）。
2. confirmation.json，绑定实际main目标、tree、main运行ID/attempt及candidate.json摘要。
3. SOURCE_COMMIT，指实际main发布目标；candidate.json另保留最初构建checkout。
4. SHA256SUMS，覆盖其余五个文件。

确认不会重建包，也不会执行下载包中的脚本。新式未来Release共六个附件；不补写或替换既有Release的四个历史附件。

## 4. 维护者发布步骤

1. 在feature分支完成变更和评审，经PR进入dev，可继续积累其它功能。
2. 发布前在dev准备版本和锁、`docs/releases/vX.Y.Z.md`候选说明，经dev → main PR完成完整验收。
3. 合并后等main的CI gate成功。找到含verified-release的main CI run ID；纯文档回填的run不能用来发版。候选过期时重新运行main完整确认流程，不使用缓存或本地重打包替代。
4. 明确授权实际发布后，在GitHub Actions的Release中选择main，填写tag与main_run_id，执行workflow_dispatch。GitHub CLI等价命令如下（示例版本和run ID必须替换为本次真实值，不可重用已发布版本）：

```powershell
$ErrorActionPreference = 'Stop'
$Tag = Read-Host '输入本次已验收的正式版本标签'
$MainRunId = Read-Host '输入成功 main CI 的运行 ID'
gh workflow run release.yml --repo tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp --ref main -f "tag=$Tag" -f "main_run_id=$MainRunId"
if ($LASTEXITCODE -ne 0) { throw '发布调度失败；先查询运行记录，不盲目重复提交。' }
```

5. 发布任务核对成功main运行、attempt、目标tree、版本和来源，确认目标为当前main历史中的提交。已有标签必须指向该目标；不存在时由gh在已验证目标上创建。先准备草稿，仅上传缺失附件；远端已有附件摘要不一致立即停止，禁止clobber。
6. 六个远端附件摘要全部匹配后，同一受控任务才将草稿正式发布。已公开版本再次请求会拒绝，不能覆盖；失败后先查Actions和草稿状态，相同输入的重跑只补齐已核验草稿的缺项。已有草稿目标不符或附件多出也拒绝。
7. 按实际发布结果回填README、MANUAL和发布记录，仍经feature → dev，再以带delivery-docs标签的dev → main PR轻检查合入。不要再跑一次CD；保留标签与发布包。

release环境保持现有受控配置，不要求额外他人审批；环境若已有与单人维护冲突的保护，由维护者授权调整。远端规则不是YAML文件能自行改变的。

## 5. 本地验证与证据范围

在现有开发环境中运行，无需设置真实API Key：

```powershell
uv run --no-sync python -m pytest tests/test_ci_policy.py -q --basetemp=.cache/ci-policy-tests
uv run --no-sync python scripts/ci_checks.py docs --all --base HEAD
uv run --no-sync python scripts/check.py
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.7 -shellcheck= -pyflakes=
uv build --no-sources --out-dir .cache/ci-local-dist
uv run --no-sync python scripts/verify_candidate_install.py .cache/ci-local-dist
```

测试覆盖分类、PR方向、文档回填、相同tree复用、候选缺失回退、来源/摘要/确认篡改、危险归档、已发布版本保护和草稿部分上传后的续传。GitHub API与发布操作在离线测试中使用替身，不实际创建标签/草稿/Release。

新稳定检查名为CI gate。迁移远端保护时，应先完成新工作流的实际PR运行，再由获授权的维护者配置CI gate，保留PR要求而不强制独立人工批准。

2026-11-14远端验收：[PR #21](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/pull/21)的最终提交`7facebadda1fc6cd5ec21320beb5aa92c5adfb61`通过[Windows/Linux CI及CI gate](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/actions/runs/43549891351)，已记录对应提交的Agent评审并合入dev（`fff518420d2389152b1b66f66fcaf7b62499bfba`）。合并tree与受验提交一致，dev未重复触发push CI。前两次失败实际使gate失败；修复了版本化文档链接检查、Windows只读Git测试文件清理及opentelemetry-api安全补丁，没有跳过门禁。

本机gh已确认当前账号有仓库admin权限；先前403属于GitHub集成通道，不代表gh无权限。main/dev分支保护均已配置并读回：要求PR，要求GitHub Actions（app_id 15368）的CI gate，批准人数0，不要求CODEOWNER或最后推送者以外的人批准，管理员也受保护，禁止强推与删除。strict=false，不因基线推进机械强制更新分支；合并内容仍按本流程核对。此次仅合入dev，main仍为`b066d89680f5f4745702a48380a761631be808d1`；候选跨工作流复用、main确认和受控CD尚未在线执行，需后续dev→main时验证。未触发发布，既有v0.1.7标签及附件保持不变。

本地质量与安装验证不等于远端GitHub事件/权限验证；合入时仍需实际核对PR、main和手动发布的权限、artifact下载及保护环境。参考GitHub官方的[可复用工作流](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)、[Artifact接口](https://docs.github.com/en/rest/actions/artifacts)与[触发事件](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)。

[PR #22](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/pull/22)的纯文档路径暴露了空依赖缓存导致setup-uv结束步骤失败的问题，CI gate正确阻止合并。修复后，docs模式不运行setup-uv或安装依赖，仅使用系统Python标准库；light模式仍安装锁定依赖。最终提交`e350bc2750133cef7536c4bb4a52de751c2a45a6`通过[完整Windows/Linux CI](https://github.com/tsyecommercialdesigner-cloud/ecommerce-image-replicator-mcp/actions/runs/43550543660)及Agent评审，并在已启用的PR/CI保护下正常合入dev，没有使用管理员绕过。纯文档还须核对scoped成功、full跳过与CI gate成功。

2026-11-14本地记录：完整质量门禁309通过、1项平台跳过，ruff/mypy/秘密扫描通过；随后补充的真实Git内容树回归随CI专项54项一起通过。actionlint1.7.7检查通过（未启用额外shellcheck/pyflakes工具），全库文档解析通过，wheel/sdist隔离锁定依赖安装及stdio通过。v0.1.6→当前HEAD→v0.1.6旧任务保留验证通过，假提交总数保持2，真实供应商请求0；其HEAD是当前已提交基线，不将尚未提交的流水线改动声称为已完成远端候选验收。证据在本地.cache/ci-quality-final.log、ci-install.log、ci-upgrade-check.log与.cache/validation/；临时安装环境已删除。
