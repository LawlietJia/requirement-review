# 来源注册表（sources.md）

> dimensions.md 各检查项引用 Source ID；引用规则：`[S-xx]`。法规类条目与 regulations.md 一致（以 regulations.md 为法规唯一权威源，本表只登记不重复内容要点）。

## A. 法规/标准（authority_grade=法规）

| ID | 名称 | 版本/文号 | 关键章节 | 适用范围 | 链接 | 核验日期 |
|---|---|---|---|---|---|---|
| S-01 | 银行保险机构消费者权益保护管理办法 | 银保监会令 2022 年第 9 号 | 第 40 条 | 银行保险机构营销信息 | 见 regulations.md | 2026-08-29 |
| S-02 | 金融产品网络营销管理办法 | 八部门公告〔2026〕第 9 号 | 第 10/12/13/20 条 | 金融机构网络营销（生效日 2026-09-30 动态判定） | 见 regulations.md | 2026-08-29（二次） |
| S-03 | 银行业金融机构数据治理指引 | 银保监发〔2018〕22 号 | 全文 | 银行业金融机构数据治理 | 见 regulations.md | 2026-08-29 |
| S-04 | 个人金融信息保护技术规范 | JR/T 0171—2020 | 分级条款 | 个人金融信息处理 | 见 regulations.md | 2026-08-29 |
| S-05 | 个人信息保护法 | 主席令第九十一号 | 第 6 条 | 个人信息处理活动 | 见 regulations.md | 2026-08-29 |
| S-06 | 银行业金融机构国别风险管理办法 | 金规〔2023〕12 号 | 第 5/20/21/31 条 | 银行业金融机构国别风险管理 | 见 regulations.md | 2026-08-29（二次） |
| S-07 | 反洗钱法（2024 修订） | 主席令第 38 号 | 第 34/53 条 | 客户身份资料与交易信息保存（34 条适用范围限定） | 见 regulations.md | 2026-08-29（二次） |
| S-08 | ISO/IEC/IEEE 29148:2018 | 2018 版 | Clause 5.2（单条 9 特性+集合 5 特性） | 需求工程质量判据 | iso.org（标准购买页/文本） | 2026-08-29（调研） |
| S-10 | 银行保险机构数据安全管理办法 | 金规〔2024〕24 号 | 分类分级/共享/委托/跨境 | 银行数据安全（D7 数据类首选） | 见 regulations.md | 2026-08-29（三次核验） |
| S-09 | GB/T 9385-2008 计算机软件需求规格说明规范 | 国标 | 八特性/一致性三类矛盾 | SRS 质量与结构 | 官方记录：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=2790825C43AD0B69E3C38C140BFFCFE6 | 2026-08-29（二次） |

## B. 权威方法论（authority_grade=方法论）

| ID | 来源 | 具体内容 | 适用 |
|---|---|---|---|
| S-40 | Wiegers《软件需求》（第 3 版，Karl Wiegers & Joy Beatty） | 单条 7 特性；连锁律（歧义→不完整→不可验证）；聚焦用户任务查缺 | D2/D5 |
| S-41 | EARS（Mavin & Noonan 2016, "Simple Design..."） | When[触发] The System Shall[响应] 改写检测 | D2-3 |
| S-42 | Firesmith（CMU SEI） | 弱词清单；NFR 量化阈值缺失检查 | D2-2/D6 |
| S-43 | MoSCoW/DSDM 官方手册 | 优先级判定问句；删除测试（镀金识别） | D8 |
| S-44 | INVEST（XP 实践） | 用户故事独立可验证 | D2-6 |
| S-45 | Fagan 正式审查（IEEE 论文 1976/1986） | 计划/准备/会议/返工/跟进；高低层文档比对 | 流程 |
| S-46 | RTM 双向追溯实践（Jama/ReqView 文档） | coverage gap vs gold plating 双向 | D4 |

## C. 社区/行业实践（authority_grade=社区）

| ID | 来源 | 内容 |
|---|---|---|
| S-20 | GitHub testany-io/testany-agent-skills@prd-reviewer（https://github.com/testany-io/testany-agent-skills） | 结构完整性、覆盖矩阵、1:N 审查 |
| S-21 | GitHub bm629/agent-skills@reviewing-prd（https://github.com/bm629/agent-skills） | 12 条可规划性检查（无伪造证据/风险诚实披露/依赖已命名/NFR 带数字/无孤儿需求） |
| S-22 | GitHub nesnilnehc/ai-cortex@review-requirements（https://github.com/nesnilnehc/ai-cortex） | 需求 ID/开放问题/约束清单/范围界限 |
| S-23 | GitHub github/spec-kit（https://github.com/github/spec-kit） | clarify 歧义/覆盖扫描 11 大类 |
| S-24 | ThoughtWorks 需求实践 | 系统性五连问、界面惯例、非功能清单 |
| S-25 | 中电金信/InvestGlass 银行 CRM 实践 | 审计追踪、适当性、CRM 功能链路 |
| S-26 | 国内银行科技实践（多源） | 权限复用 4A、批量日切、数据迁移、外购二开 Gap |

## D. agent 推断（authority_grade=推断，validation_status 标注）

| ID | 规则 | validation_status |
|---|---|---|
| S-30 | D3-9 取值域 vs 映射域核对 | 项目验证（基线 S4/V1.1 盲测） |
| S-31 | D3-10 码值逐值比对 | 项目验证（B3/B4） |
| S-32 | D3-11 字段链三方比对 | 项目验证（S1→V1.1 F-004 双 run） |
| S-33 | D3-4 术语形近异名机械比对 | 样例验证（裁决实证仅 2/8 run 发现该型缺陷——执行稳定性为已知弱点，重要文档双跑时重点人工复核此维） |
| S-34 | P1→阻断三判据 | 项目验证（V1.1 消摆动）+人工确认 |
| S-35 | D1-8 附件外包自足性 | 项目验证（B10/F-006） |
| S-36 | D5-11/12/13 权限复用/频控/报表扩展组 | 未验证（来自调研推断，待真实使用） |
| S-37 | G 外购 Gap 三态 | 未验证 |
| S-38 | D2-10 同源错误归并计数 | 样例验证（基线各 run 已自然执行） |

**维护规则**：新检查项入 dimensions.md 时必须登记 Source ID；推断类规则经真实评审验证后更新 validation_status；法规类只认 regulations.md 核验表。
