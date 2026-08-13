# 测试规程

### PROC-001：分数限值设置后，验证对未产生评价结果的项目立即生效，对已汇总项目无影响
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-019`
**阶段依据**：fallback_default.E-LIMIT

**Given**
- E-LIMIT 状态 = 规则适用前提满足 (E-LIMIT, E-PROJ相关数据已准备)

**When**
- E-LIMIT 按规则"分数限值设置后对未产生评价结果的项目立即生效；对已经汇总的项目无影响"执行操作事件 [按规则"分数限值设置后对未产生评价结果的项目立即生效；对已经汇总的项目无影响"执行操作]

**Then**
- E-LIMIT [BR-19]正面: 分数限值设置后对未产生评价结果的项目立即生效；对已经汇总的项目无影响 (behavior) [BR: BR-19]
- E-LIMIT [BR-19]负面: 不满足条件时规则不触发 (behavior) [BR: BR-19]

**后置状态**：E-LIMIT→(规则验证完成)
**弱依赖**：PROC-016.1

### PROC-002 (×2)：机构下无项目、无用户、无子机构时才可删除，根机构不可删除
**业务定位**：P0 ｜ invalid ｜ 溯源: `RO-BR-032`
**阶段依据**：dep_state_phase_map.E-ORG.min_phase

**Given**
- E-ORG 状态 = 规则适用前提满足 ([实例 1] 不可删除相关数据已准备)

**When**
- E-ORG 尝试违反规则操作事件 [尝试违反规则操作]

**Then**
- E-ORG 机构下无项目、无用户、无子机构时才可删除；根机构不可删除 (prompt) [BR: BR-32]
- E-ORG [BR-32]正面: 机构下无项目、无用户、无子机构时才可删除；根机构不可删除 (behavior) [BR: BR-32]
- E-ORG [BR-32]负面: 不满足条件时规则不触发 (behavior) [BR: BR-32]

**后置状态**：E-ORG→(操作被阻止)
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-003：实现基于角色的访问控制
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-034`
**阶段依据**：fallback_default.E-ROLE

**Given**
- E-ROLE 状态 = 规则适用前提满足 (E-ROLE, E-USER相关数据已准备)

**When**
- E-ROLE 按规则"实现基于角色的访问控制"执行操作事件 [按规则"实现基于角色的访问控制"执行操作]

**Then**
- E-ROLE [BR-34] 实现基于角色的访问控制 (behavior) [BR: BR-34]

**后置状态**：E-ROLE→(规则验证完成)
**弱依赖**：PROC-045.1

### PROC-004：下发时限配置变更后，验证下发时限显示为修改后的值
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-012`
**阶段依据**：fallback_default.E-TIMEOUT

**Given**
- E-TIMEOUT 状态 = 下发时限为当前值 (当前下发时限配置值)

**When**
- E-TIMEOUT 下发时限配置变更事件 [修改下发时限]

**Then**
- E-TIMEOUT.下发时限 下发时限显示为修改后的值 (state)

**操作提示**
1. 导航至E-TIMEOUT配置入口

**后置状态**：E-TIMEOUT.下发时限→(已修改)

### PROC-005：启动时限配置变更后，验证启动时限显示为修改后的值
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-013`
**阶段依据**：fallback_default.E-TIMEOUT

**Given**
- E-TIMEOUT 状态 = 启动时限为当前值 (当前启动时限配置值)

**When**
- E-TIMEOUT 启动时限配置变更事件 [修改启动时限]

**Then**
- E-TIMEOUT.启动时限 启动时限显示为修改后的值 (state)

**操作提示**
1. 导航至E-TIMEOUT配置入口

**后置状态**：E-TIMEOUT.启动时限→(已修改)

### PROC-006：归档时限配置变更后，验证归档时限显示为修改后的值
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-015`
**阶段依据**：fallback_default.E-TIMEOUT

**Given**
- E-TIMEOUT 状态 = 归档时限为当前值 (当前归档时限配置值)

**When**
- E-TIMEOUT 归档时限配置变更事件 [修改归档时限]

**Then**
- E-TIMEOUT.归档时限 归档时限显示为修改后的值 (state)

**操作提示**
1. 导航至E-TIMEOUT配置入口

**后置状态**：E-TIMEOUT.归档时限→(已修改)

### PROC-007：评审时限配置变更后，验证评审时限显示为修改后的值
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-014`
**阶段依据**：fallback_default.E-TIMEOUT

**Given**
- E-TIMEOUT 状态 = 评审时限为当前值 (当前评审时限配置值)

**When**
- E-TIMEOUT 评审时限配置变更事件 [修改评审时限]

**Then**
- E-TIMEOUT.评审时限 评审时限显示为修改后的值 (state)

**操作提示**
1. 导航至E-TIMEOUT配置入口

**后置状态**：E-TIMEOUT.评审时限→(已修改)

### PROC-008：超时设置完成后，验证对所有计划立即生效
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-033`
**阶段依据**：fallback_default.E-TIMEOUT

**Given**
- E-TIMEOUT 状态 = 规则适用前提满足 (E-TIMEOUT, E-PLAN相关数据已准备)

**When**
- E-TIMEOUT 按规则"超时设置完成后，对所有计划立即生效"执行操作事件 [按规则"超时设置完成后，对所有计划立即生效"执行操作]

**Then**
- E-TIMEOUT [BR-33] 超时设置完成后，对所有计划立即生效 (behavior) [BR: BR-33]

**后置状态**：E-TIMEOUT→(规则验证完成)
**弱依赖**：PROC-014.1

### PROC-009 (×2)：专家人数配置为5后，验证评审计划相关规则生效
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-005`
**阶段依据**：fallback

**Given**
- E-PLAN 状态 = 专家人数为当前值 ([实例 1] 当前专家人数配置值)

**When**
- E-PLAN 专家人数配置变更为5事件 [修改专家人数为5]

**Then**
- E-PLAN.专家人数 配置专家人数=5的效果已生效 (behavior) [BR: BR-07]
- E-PLAN.专家人数 [BR-07] 评审计划的评审组由5、7或9个专家组成，有且只能有一个组长专家 (behavior) [BR: BR-07] [cross: E-EXPERT]
- E-PLAN.专家人数 [BR-20] 项目评价：去掉普通专家的一个最高分和一个最低分，计算剩余普通专家打分的平均分，然后按系统内置打分权重表计算，结果四舍五入保留两位小数 (behavior) [BR: BR-20] [cross: E-SCORE,E-PROJ]
- E-PLAN.专家人数 [BR-69] 评审组专家人数决定组长专家与普通专家合计权重：5人 40%/60%；7人 25%/75%；9人 18%/82% (behavior) [BR: BR-69] [cross: E-EXPERT]

**操作提示**
1. 导航至E-PLAN配置入口

**后置状态**：E-PLAN.专家人数→5
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-010 (×2)：专家人数配置为7后，验证评审计划相关规则生效
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-005`
**阶段依据**：fallback

**Given**
- E-PLAN 状态 = 专家人数为当前值 ([实例 1] 当前专家人数配置值)

**When**
- E-PLAN 专家人数配置变更为7事件 [修改专家人数为7]

**Then**
- E-PLAN.专家人数 配置专家人数=7的效果已生效 (behavior) [BR: BR-07]
- E-PLAN.专家人数 [BR-07] 评审计划的评审组由5、7或9个专家组成，有且只能有一个组长专家 (behavior) [BR: BR-07] [cross: E-EXPERT]
- E-PLAN.专家人数 [BR-20] 项目评价：去掉普通专家的一个最高分和一个最低分，计算剩余普通专家打分的平均分，然后按系统内置打分权重表计算，结果四舍五入保留两位小数 (behavior) [BR: BR-20] [cross: E-SCORE,E-PROJ]
- E-PLAN.专家人数 [BR-69] 评审组专家人数决定组长专家与普通专家合计权重：5人 40%/60%；7人 25%/75%；9人 18%/82% (behavior) [BR: BR-69] [cross: E-EXPERT]

**操作提示**
1. 导航至E-PLAN配置入口

**后置状态**：E-PLAN.专家人数→7
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-011 (×2)：专家人数配置为9后，验证评审计划相关规则生效
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-005`
**阶段依据**：fallback

**Given**
- E-PLAN 状态 = 专家人数为当前值 ([实例 1] 当前专家人数配置值)

**When**
- E-PLAN 专家人数配置变更为9事件 [修改专家人数为9]

**Then**
- E-PLAN.专家人数 配置专家人数=9的效果已生效 (behavior) [BR: BR-07]
- E-PLAN.专家人数 [BR-07] 评审计划的评审组由5、7或9个专家组成，有且只能有一个组长专家 (behavior) [BR: BR-07] [cross: E-EXPERT]
- E-PLAN.专家人数 [BR-20] 项目评价：去掉普通专家的一个最高分和一个最低分，计算剩余普通专家打分的平均分，然后按系统内置打分权重表计算，结果四舍五入保留两位小数 (behavior) [BR: BR-20] [cross: E-SCORE,E-PROJ]
- E-PLAN.专家人数 [BR-69] 评审组专家人数决定组长专家与普通专家合计权重：5人 40%/60%；7人 25%/75%；9人 18%/82% (behavior) [BR: BR-69] [cross: E-EXPERT]

**操作提示**
1. 导航至E-PLAN配置入口

**后置状态**：E-PLAN.专家人数→9
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-012 (×2)：计划类型配置为开题后，验证评审计划相关规则生效
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-003`
**阶段依据**：fallback

**Given**
- E-PLAN 状态 = 计划类型为当前值 ([实例 1] 当前计划类型配置值)

**When**
- E-PLAN 计划类型配置变更为开题事件 [修改计划类型为开题]

**Then**
- E-PLAN.计划类型 配置计划类型=开题的效果已生效 (behavior) [BR: BR-68]
- E-PLAN.计划类型 [BR-68] 评审计划类型决定选入项目的阶段范围与打分项集合：开题计划选开题阶段项目并使用开题打分项；验收计划选验收阶段项目并使用验收打分项 (behavior) [BR: BR-68] [cross: E-PROJ]

**操作提示**
1. 导航至E-PLAN配置入口

**后置状态**：E-PLAN.计划类型→开题
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-013 (×2)：计划类型配置为验收后，验证评审计划相关规则生效
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-003`
**阶段依据**：fallback

**Given**
- E-PLAN 状态 = 计划类型为当前值 ([实例 1] 当前计划类型配置值)

**When**
- E-PLAN 计划类型配置变更为验收事件 [修改计划类型为验收]

**Then**
- E-PLAN.计划类型 配置计划类型=验收的效果已生效 (behavior) [BR: BR-68]
- E-PLAN.计划类型 [BR-68] 评审计划类型决定选入项目的阶段范围与打分项集合：开题计划选开题阶段项目并使用开题打分项；验收计划选验收阶段项目并使用验收打分项 (behavior) [BR: BR-68] [cross: E-PROJ]

**操作提示**
1. 导航至E-PLAN配置入口

**后置状态**：E-PLAN.计划类型→验收
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-014 (×2)：建立评审计划后，验证状态转换为已建立
**业务定位**：P0 ｜ happy ｜ 溯源: `T-PL01`
**阶段依据**：phase_table.评审计划状态.已建立

**Given**
- E-PLAN.评审计划状态 状态 = (初始) ([实例 1] 选取1-5个已选入项目)

**When**
- E-PLAN.评审计划状态 建立评审计划（目标状态：已建立） by R-ADMIN [建立评审计划]

**Then**
- E-PLAN.评审计划状态 状态转换为已建立 (state)

**后置状态**：E-PLAN.评审计划状态→已建立
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-015 (×2)：评审计划已建立时，管理员取消评审计划，验证状态变更为取消结束
**业务定位**：P0 ｜ rollback ｜ 溯源: `T-PL03`
**阶段依据**：phase_table.评审计划状态.取消结束

**Given**
- E-PLAN.评审计划状态 状态 = 已建立 ([实例 1] 评审计划处于已建立状态)

**When**
- E-PLAN.评审计划状态 取消评审计划（目标状态：取消结束） by R-ADMIN [取消评审计划]

**Then**
- E-PLAN.评审计划状态 状态转换为取消结束 (state)

**后置状态**：E-PLAN.评审计划状态→取消结束
**依赖**：PROC-014.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-016 (×5)：初始状态下，组织管理员新增项目，验证状态变更为待选入
**业务定位**：P0 ｜ happy ｜ 溯源: `T-P01`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.待选入

**Given**
- E-PROJ.项目状态 状态 = (初始) ([实例 1])

**When**
- E-PROJ.项目状态 新增项目（目标状态：待选入） by R-ORG [新增项目]

**Then**
- E-PROJ.项目状态 状态转换为待选入 (state)

**后置状态**：E-PROJ.项目状态→待选入
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-017 (×5)：初始状态下，组织管理员新增项目初始化阶段，验证状态变更为开题
**业务定位**：P0 ｜ happy ｜ 溯源: `T-PS00`
**阶段依据**：dep_state_phase_map.E-PROJ.项目阶段.开题

**Given**
- E-PROJ.项目阶段 状态 = (初始) ([实例 1])

**When**
- E-PROJ.项目阶段 新增项目初始化项目阶段（目标状态：开题） by R-ORG [新增项目初始化项目阶段]

**Then**
- E-PROJ.项目阶段 状态转换为开题 (state)

**后置状态**：E-PROJ.项目阶段→开题
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-018 (×5)：项目待归档且评级不合格或差，评审计划已归档，归档操作后验证状态变更为待选入
**业务定位**：P0 ｜ branch ｜ 溯源: `T-P07b`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.待选入

**Given**
- E-PROJ.项目状态 状态 = 待归档 ([实例 1] 项目处于待归档状态; 项目阶段为开题; 项目的评级为不合格或差)
- E-PROJ.项目状态 状态 = 待归档 (评审计划已归档（状态为结束或超时结束）)

**When**
- E-PROJ.项目状态 归档-开题-不合格或差（目标状态：待选入） by [待确认角色] [归档-开题-不合格或差]

**Then**
- E-PROJ.项目状态 状态转换为待选入 (state)

**后置状态**：E-PROJ.项目状态→待选入
**依赖**：PROC-016.1, PROC-017.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-019 (×5)：项目开题且评级合格及以上，开题评审合格及以上归档操作后验证状态变更为验收
**业务定位**：P0 ｜ branch ｜ 溯源: `T-PS01`
**阶段依据**：dep_state_phase_map.E-PROJ.项目阶段.验收

**Given**
- E-PROJ.项目阶段 状态 = 开题 ([实例 1] 项目阶段为开题; 项目处于待归档状态; 项目的评级在合格及以上)

**When**
- E-PROJ.项目阶段 开题评审合格及以上归档（目标状态：验收） by [待确认角色] [开题评审合格及以上归档]

**Then**
- E-PROJ.项目阶段 状态转换为验收 (state)

**后置状态**：E-PROJ.项目阶段→验收
**依赖**：PROC-017.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-020 (×5)：项目处于待归档状态且评级不合格或差，且评审计划已归档时，待确认角色归档-验收-不合格或差，验证项目状态变更为待选入
**业务定位**：P0 ｜ branch ｜ 溯源: `T-P07d`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.待选入

**Given**
- E-PROJ.项目状态 状态 = 待归档 ([实例 1] 项目处于待归档状态; 项目阶段为验收; 项目的评级为不合格或差)
- E-PROJ.项目状态 状态 = 待归档 (评审计划已归档（状态为结束或超时结束）)

**When**
- E-PROJ.项目状态 归档-验收-不合格或差（目标状态：待选入） by [待确认角色] [归档-验收-不合格或差]

**Then**
- E-PROJ.项目状态 状态转换为待选入 (state)

**后置状态**：E-PROJ.项目状态→待选入
**依赖**：PROC-016.1, PROC-019.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-021 (×5)：待选入状态的项目尝试转换为已选入，验证操作被拒绝且状态仍为待选入，并满足相关规则
**业务定位**：P0 ｜ invalid ｜ 溯源: `RO-IT-001`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.待选入

**Given**
- E-PROJ 状态 = 待选入 ([实例 1] E-PROJ处于"待选入"状态)

**When**
- E-PROJ 尝试待选入→已选入转换事件 [尝试执行从"待选入"到"已选入"的操作]

**Then**
- E-PROJ 操作被拒绝，本阶段评价结果为差的项目不可选入（4.7.1(3)） (prompt)
- E-PROJ 状态仍为待选入 (state)
- E-PROJ [BR-26]正面: 专家有待评审或者评审中的项目时不可以删除 (behavior) [BR: BR-26] [cross: E-EXPERT]
- E-PROJ [BR-26]负面: 不满足条件时规则不触发 (behavior) [BR: BR-26] [cross: E-EXPERT]

**后置状态**：E-PROJ→(操作被阻止)
**依赖**：PROC-016.1, PROC-018.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-022 (×4)：尝试对内置管理员进行违规操作，验证操作被拒绝并满足相关规则
**业务定位**：P0 ｜ invalid ｜ 溯源: `RO-BR-029`
**阶段依据**：dep_state_phase_map.E-USER.min_phase

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] 不可对内置的审计管理员、系统管理员、评审管理员、评审助理进行编辑、锁定、重置密码等操作相关数据已准备)

**When**
- E-USER 尝试违反规则操作事件 [尝试违反规则操作]

**Then**
- E-USER 不可对内置的审计管理员、系统管理员、评审管理员、评审助理进行编辑、锁定、重置密码等操作 (prompt) [BR: BR-29]
- E-USER [BR-29] 不可对内置的审计管理员、系统管理员、评审管理员、评审助理进行编辑、锁定、重置密码等操作 (behavior) [BR: BR-29] [cross: E-ROLE]
- E-USER [BR-30]正面: 删除用户时如有未完成的任务，不能删除 (behavior) [BR: BR-30]
- E-USER [BR-30]负面: 不满足条件时规则不触发 (behavior) [BR: BR-30]

**后置状态**：E-USER→(操作被阻止)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-023 (×2)：评审身份配置变更为组长专家，验证配置效果生效并满足相关规则
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-009`
**阶段依据**：fallback_default

**Given**
- E-EXPERT 状态 = 评审身份为当前值 ([实例 1] 当前评审身份配置值)

**When**
- E-EXPERT 评审身份配置变更为组长专家事件 [修改评审身份为组长专家]

**Then**
- E-EXPERT.评审身份 配置评审身份=组长专家的效果已生效 (behavior) [BR: BR-62]
- E-EXPERT.评审身份 [BR-62] 专家.技术领域：必填项；取值范围 A-J 领域；可选择1-3个 (behavior) [BR: BR-62]
- E-EXPERT.评审身份 [BR-70] 评审身份决定打分在项目评价中的权重角色：组长专家按组长权重计入；普通专家去掉一个最高分和一个最低分后按普通专家合计权重计入 (behavior) [BR: BR-70]

**操作提示**
1. 导航至E-EXPERT配置入口

**后置状态**：E-EXPERT.评审身份→组长专家
**多实例**：2 × entity=E-EXPERT dim_count=0 instances=2

### PROC-024 (×2)：评审身份配置变更为普通专家，验证配置效果生效并满足相关规则
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-009`
**阶段依据**：fallback_default

**Given**
- E-EXPERT 状态 = 评审身份为当前值 ([实例 1] 当前评审身份配置值)

**When**
- E-EXPERT 评审身份配置变更为普通专家事件 [修改评审身份为普通专家]

**Then**
- E-EXPERT.评审身份 配置评审身份=普通专家的效果已生效 (behavior) [BR: BR-62]
- E-EXPERT.评审身份 [BR-62] 专家.技术领域：必填项；取值范围 A-J 领域；可选择1-3个 (behavior) [BR: BR-62]
- E-EXPERT.评审身份 [BR-70] 评审身份决定打分在项目评价中的权重角色：组长专家按组长权重计入；普通专家去掉一个最高分和一个最低分后按普通专家合计权重计入 (behavior) [BR: BR-70]

**操作提示**
1. 导航至E-EXPERT配置入口

**后置状态**：E-EXPERT.评审身份→普通专家
**多实例**：2 × entity=E-EXPERT dim_count=0 instances=2

### PROC-025 (×4)：评审计划启动后，分配打分任务，验证打分状态转换为未保存
**业务定位**：P0 ｜ happy ｜ 溯源: `T-S01`
**阶段依据**：dep_state_phase_map.E-SCORE.打分状态.未保存

**Given**
- E-SCORE.打分状态 状态 = (初始) ([实例 1])
- E-SCORE.打分状态 状态 = (初始) (评审计划已启动（状态为待评审或之后）)

**When**
- E-SCORE.打分状态 分配打分任务（目标状态：未保存） by [待确认角色] [分配打分任务]

**Then**
- E-SCORE.打分状态 状态转换为未保存 (state)

**后置状态**：E-SCORE.打分状态→未保存
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-026 (×4)：打分状态为未保存时，保存打分，验证状态转换为已保存
**业务定位**：P0 ｜ happy ｜ 溯源: `T-S02`
**阶段依据**：dep_state_phase_map.E-SCORE.打分状态.已保存

**Given**
- E-SCORE.打分状态 状态 = 未保存 ([实例 1] 打分状态为未保存)

**When**
- E-SCORE.打分状态 保存打分（目标状态：已保存） by R-EXPERT [保存打分]

**Then**
- E-SCORE.打分状态 状态转换为已保存 (state)

**后置状态**：E-SCORE.打分状态→已保存
**依赖**：PROC-025.1
**弱依赖**：PROC-078.1, PROC-079.1, PROC-082.1, PROC-084.1, PROC-088.1
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-027 (×4)：打分状态为已保存且项目打分不全为零时，提交打分，验证状态转换为已提交
**业务定位**：P0 ｜ audit ｜ 溯源: `T-S03`
**阶段依据**：dep_state_phase_map.E-SCORE.打分状态.已提交

**Given**
- E-SCORE.打分状态 状态 = 已保存 ([实例 1] 打分状态为已保存; 项目各项打分不全为零)

**When**
- E-SCORE.打分状态 提交打分（目标状态：已提交） by R-EXPERT [提交打分]

**Then**
- E-SCORE.打分状态 状态转换为已提交 (state)

**后置状态**：E-SCORE.打分状态→已提交
**依赖**：PROC-025.1, PROC-026.1
**弱依赖**：PROC-089.1, PROC-095.1
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-028 (×4)：已提交状态的项目尝试修改分数，验证操作被拒绝且状态不变
**业务定位**：P0 ｜ invalid ｜ 溯源: `RO-IT-002`
**阶段依据**：dep_state_phase_map.E-SCORE.打分状态.已提交

**Given**
- E-SCORE 状态 = 已提交 ([实例 1] E-SCORE处于"已提交"状态)

**When**
- E-SCORE 尝试已提交→已保存转换事件 [尝试执行从"已提交"到"已保存"的操作]

**Then**
- E-SCORE 操作被拒绝，已提交的项目不能进行分数修改（4.9.2(3)） (prompt)
- E-SCORE 状态仍为已提交 (state)

**后置状态**：E-SCORE→(操作被阻止)
**依赖**：PROC-027.1
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-029 (×4)：按规则执行项目打分全部为零不能提交，验证规则触发及不触发情况
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-018`
**阶段依据**：dep_map_max_phase.E-SCORE.0

**Given**
- E-SCORE 状态 = 规则适用前提满足 ([实例 1] E-SCORE相关数据已准备)

**When**
- E-SCORE 按规则"项目各项打分全部为零的不能提交"执行操作事件 [按规则"项目各项打分全部为零的不能提交"执行操作]

**Then**
- E-SCORE [BR-18]正面: 项目各项打分全部为零的不能提交 (behavior) [BR: BR-18]
- E-SCORE [BR-18]负面: 不满足条件时规则不触发 (behavior) [BR: BR-18]

**后置状态**：E-SCORE→(规则验证完成)
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-030：E-LOG规则执行时，验证系统日志记录只能由系统审计员查看
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-047`
**阶段依据**：fallback_default.E-LOG

**Given**
- E-LOG 状态 = 规则适用前提满足 (E-LOG相关数据已准备)

**When**
- E-LOG 按规则"系统日志记录只能由系统审计员查看"执行操作事件 [按规则"系统日志记录只能由系统审计员查看"执行操作]

**Then**
- E-LOG [BR-47] 系统日志记录只能由系统审计员查看 (behavior) [BR: BR-47]

**后置状态**：E-LOG→(规则验证完成)

### PROC-031：E-LOG规则执行时，验证系统日志记录事件的相关信息
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-048`
**阶段依据**：fallback_default.E-LOG

**Given**
- E-LOG 状态 = 规则适用前提满足 (E-LOG相关数据已准备)

**When**
- E-LOG 按规则"系统日志记录事件的时间、角色、操作类型、日志内容和日志类型等"执行操作事件 [按规则"系统日志记录事件的时间、角色、操作类型、日志内容和日志类型等"执行操作]

**Then**
- E-LOG [BR-48] 系统日志记录事件的时间、角色、操作类型、日志内容和日志类型等 (behavior) [BR: BR-48]

**后置状态**：E-LOG→(规则验证完成)

### PROC-032 (×2)：初始状态下，添加研制机构后验证机构状态转换为合格
**业务定位**：P1 ｜ happy ｜ 溯源: `T-O05`
**阶段依据**：dep_state_phase_map.E-ORG.机构状态.合格

**Given**
- E-ORG.机构状态 状态 = (初始) ([实例 1])

**When**
- E-ORG.机构状态 添加研制机构（目标状态：合格） by R-SYS [添加研制机构]

**Then**
- E-ORG.机构状态 状态转换为合格 (state)

**后置状态**：E-ORG.机构状态→合格
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-033 (×2)：机构状态不合格且累计评级不合格次数小于3时，系统管理员提为试用后验证状态转换为试用
**业务定位**：P0 ｜ happy ｜ 溯源: `T-O02`
**阶段依据**：dep_state_phase_map.E-ORG.机构状态.试用

**Given**
- E-ORG.机构状态 状态 = 不合格 ([实例 1] 机构状态为不合格; 研制机构累计评级为不合格次数小于3)

**When**
- E-ORG.机构状态 系统管理员提为试用（目标状态：试用） by R-SYS [系统管理员提为试用]

**Then**
- E-ORG.机构状态 状态转换为试用 (state)

**后置状态**：E-ORG.机构状态→试用
**依赖**：PROC-032.1
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-034 (×2)：试用机构且累计10次项目阶段评价结果为优时，验证机构状态升级为合格
**业务定位**：P1 ｜ happy ｜ 溯源: `T-O03`
**阶段依据**：dep_state_phase_map.E-ORG.机构状态.合格

**Given**
- E-ORG.机构状态 状态 = 试用 ([实例 1] 机构状态为试用; 机构累计10次项目阶段评价结果为优)

**When**
- E-ORG.机构状态 试用机构升级（目标状态：合格） by [待确认角色] [试用机构升级]

**Then**
- E-ORG.机构状态 状态转换为合格 (state)

**后置状态**：E-ORG.机构状态→合格
**依赖**：PROC-032.1, PROC-033.1
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-035 (×2)：评审计划已建立时，下发评审计划后验证状态转换为待启动
**业务定位**：P1 ｜ happy ｜ 溯源: `T-PL02`
**阶段依据**：phase_table.评审计划状态.待启动

**Given**
- E-PLAN.评审计划状态 状态 = 已建立 ([实例 1] 评审计划处于已建立状态)

**When**
- E-PLAN.评审计划状态 下发评审计划（目标状态：待启动） by R-ADMIN [下发评审计划]

**Then**
- E-PLAN.评审计划状态 状态转换为待启动 (state)

**后置状态**：E-PLAN.评审计划状态→待启动
**依赖**：PROC-014.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-036 (×2)：评审计划已建立且下发时限已过时，系统下发超时后验证状态转换为待启动
**业务定位**：P1 ｜ happy ｜ 溯源: `T-PL02T`
**阶段依据**：phase_table.评审计划状态.待启动

**Given**
- E-PLAN.评审计划状态 状态 = 已建立 ([实例 1] 评审计划处于已建立状态; 下发时限已过)

**When**
- E-PLAN.评审计划状态 下发超时（目标状态：待启动） by 系统 [下发超时]

**Then**
- E-PLAN.评审计划状态 状态转换为待启动 (state)

**后置状态**：E-PLAN.评审计划状态→待启动
**依赖**：PROC-014.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-037 (×2)：评审计划已建立且接近截止时间时，系统下发超时(时间边界)后验证状态转换为待启动(时间边界生效)
**业务定位**：P1 ｜ time_sensitive ｜ 溯源: `T-PL02T`
**阶段依据**：phase_table.评审计划状态.待启动 (time_boundary)

**Given**
- E-PLAN.评审计划状态 状态 = 已建立 ([实例 1] 时间边界条件: 接近截止时间)

**When**
- E-PLAN.评审计划状态 下发超时(时间边界)（目标状态：待启动） by 系统 [下发超时(边界)]

**Then**
- E-PLAN.评审计划状态 状态转换为待启动(时间边界生效) (state)

**后置状态**：E-PLAN.评审计划状态→待启动(时间边界)
**依赖**：PROC-014.1, PROC-036.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-038 (×2)：评审计划已建立且时间过期时，尝试下发超时事件后验证操作不可执行或状态不变
**业务定位**：P1 ｜ time_sensitive ｜ 溯源: `T-PL02T`
**阶段依据**：phase_table.评审计划状态.待启动 (time_expired)

**Given**
- E-PLAN.评审计划状态 状态 = 已建立 ([实例 1] 时间过期条件: 超过截止时间)

**When**
- E-PLAN.评审计划状态 尝试下发超时事件(已过期) by 系统 [尝试下发超时(已过期)]

**Then**
- E-PLAN.评审计划状态 操作不可执行或状态不变 (behavior)

**后置状态**：E-PLAN.评审计划状态→(过期未执行)
**依赖**：PROC-014.1, PROC-036.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-039 (×5)：项目处于待归档状态且评级合格及以上且评审计划已归档时，验证项目状态转换为已选入
**业务定位**：P1 ｜ branch ｜ 溯源: `T-P07a`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.已选入

**Given**
- E-PROJ.项目状态 状态 = 待归档 ([实例 1] 项目处于待归档状态; 项目阶段为开题; 项目的评级在合格及以上)
- E-PROJ.项目状态 状态 = 待归档 (评审计划已归档（状态为结束或超时结束）)

**When**
- E-PROJ.项目状态 归档-开题-合格及以上（目标状态：已选入） by [待确认角色] [归档-开题-合格及以上]

**Then**
- E-PROJ.项目状态 状态转换为已选入 (state)

**后置状态**：E-PROJ.项目状态→已选入
**依赖**：PROC-016.1, PROC-017.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-040 (×5)：项目已选入时，管理员选出项目，验证项目状态变更为待选入
**业务定位**：P1 ｜ rollback ｜ 溯源: `T-P03`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.已选入

**Given**
- E-PROJ.项目状态 状态 = 已选入 ([实例 1] 项目处于已选入状态)

**When**
- E-PROJ.项目状态 选出项目（目标状态：待选入） by R-ADMIN [选出项目]

**Then**
- E-PROJ.项目状态 状态转换为待选入 (state)

**后置状态**：E-PROJ.项目状态→待选入
**依赖**：PROC-016.1, PROC-039.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-041 (×5)：项目待选入时，管理员选入项目，验证项目状态变更为已选入
**业务定位**：P1 ｜ happy ｜ 溯源: `T-P02`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.已选入

**Given**
- E-PROJ.项目状态 状态 = 待选入 ([实例 1] 项目处于待选入状态)

**When**
- E-PROJ.项目状态 选入项目（目标状态：已选入） by R-ADMIN [选入项目]

**Then**
- E-PROJ.项目状态 状态转换为已选入 (state)

**后置状态**：E-PROJ.项目状态→已选入
**依赖**：PROC-016.1, PROC-018.1, PROC-020.1, PROC-040.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-042 (×4)：技术领域配置变更时，验证技术领域显示为修改后的值
**业务定位**：P1 ｜ happy ｜ 溯源: `EO-ATC-010`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 技术领域为当前值 ([实例 1] 当前技术领域配置值)

**When**
- E-USER 技术领域配置变更事件 [修改技术领域]

**Then**
- E-USER.技术领域 技术领域显示为修改后的值 (state)

**操作提示**
1. 导航至E-USER配置入口

**后置状态**：E-USER.技术领域→(已修改)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-043 (×4)：角色配置变更时，验证角色显示为修改后的值
**业务定位**：P1 ｜ happy ｜ 溯源: `EO-ATC-011`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 角色为当前值 ([实例 1] 当前角色配置值)

**When**
- E-USER 角色配置变更事件 [修改角色]

**Then**
- E-USER.角色 角色显示为修改后的值 (state)

**操作提示**
1. 导航至E-USER配置入口

**后置状态**：E-USER.角色→(已修改)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-044 (×4)：初始状态下，系统新增用户后，验证用户锁定状态变更为未锁定
**业务定位**：P1 ｜ happy ｜ 溯源: `T-U01`
**阶段依据**：dep_state_phase_map.E-USER.锁定状态.未锁定

**Given**
- E-USER.锁定状态 状态 = (初始) ([实例 1])

**When**
- E-USER.锁定状态 新增用户（目标状态：未锁定） by R-SYS [新增用户]

**Then**
- E-USER.锁定状态 状态转换为未锁定 (state)

**后置状态**：E-USER.锁定状态→未锁定
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-045 (×4)：用户未锁定状态下，系统锁定用户后，验证用户锁定状态变更为锁定
**业务定位**：P0 ｜ happy ｜ 溯源: `T-U02`
**阶段依据**：dep_state_phase_map.E-USER.锁定状态.锁定

**Given**
- E-USER.锁定状态 状态 = 未锁定 ([实例 1] 用户状态为未锁定)

**When**
- E-USER.锁定状态 锁定用户（目标状态：锁定） by R-SYS [锁定用户]

**Then**
- E-USER.锁定状态 状态转换为锁定 (state)

**后置状态**：E-USER.锁定状态→锁定
**依赖**：PROC-044.1
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-046 (×4)：用户连续密码错误3次后，系统自动锁定用户，验证用户锁定状态变更为锁定
**业务定位**：P0 ｜ happy ｜ 溯源: `T-U04`
**阶段依据**：dep_state_phase_map.E-USER.锁定状态.锁定

**Given**
- E-USER.锁定状态 状态 = 未锁定 ([实例 1] 用户状态为未锁定; 普通用户连续密码错误3次)

**When**
- E-USER.锁定状态 密码错误3次自动锁定（目标状态：锁定） by 系统 [密码错误3次自动锁定]

**Then**
- E-USER.锁定状态 状态转换为锁定 (state)

**后置状态**：E-USER.锁定状态→锁定
**依赖**：PROC-044.1
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-047 (×4)：用户锁定状态下，系统解锁用户后，验证用户锁定状态变更为未锁定
**业务定位**：P1 ｜ happy ｜ 溯源: `T-U03`
**阶段依据**：dep_state_phase_map.E-USER.锁定状态.未锁定

**Given**
- E-USER.锁定状态 状态 = 锁定 ([实例 1] 用户状态为锁定)

**When**
- E-USER.锁定状态 解锁用户（目标状态：未锁定） by R-SYS [解锁用户]

**Then**
- E-USER.锁定状态 状态转换为未锁定 (state)

**后置状态**：E-USER.锁定状态→未锁定
**依赖**：PROC-044.1, PROC-045.1
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-048 (×4)：规则适用前提满足时，执行登录时密码不以明文显示规则，验证规则执行正确
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-035`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"登录时密码不以明文显示"执行操作事件 [按规则"登录时密码不以明文显示"执行操作]

**Then**
- E-USER [BR-35] 登录时密码不以明文显示 (behavior) [BR: BR-35]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-049 (×4)：用户数据准备就绪时，执行身份证信息加密规则，验证身份证年月日不显示明文
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-036`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"身份证的年月日不以明文显示"执行操作事件 [按规则"身份证的年月日不以明文显示"执行操作]

**Then**
- E-USER [BR-36] 身份证的年月日不以明文显示 (behavior) [BR: BR-36]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-050 (×4)：用户数据准备就绪时，执行初次登录更改密码规则，验证用户需更改密码
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-037`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"用户初次登录时需更改密码"执行操作事件 [按规则"用户初次登录时需更改密码"执行操作]

**Then**
- E-USER [BR-37] 用户初次登录时需更改密码 (behavior) [BR: BR-37]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-051 (×4)：用户数据准备就绪时，执行密码设置规则，验证密码长度和复杂度要求
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-038`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"密码设置时长度在8到18位，要包含字母、数字和特殊字符"执行操作事件 [按规则"密码设置时长度在8到18位，要包含字母、数字和特殊字符"执行操作]

**Then**
- E-USER [BR-38] 密码设置时长度在8到18位，要包含字母、数字和特殊字符 (behavior) [BR: BR-38]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-052 (×4)：用户数据准备就绪时，执行用户唯一标识和登录限制规则，验证用户唯一标识和登录限制
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-039`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"用户都应有唯一标识；同一用户同时段不能重复登录"执行操作事件 [按规则"用户都应有唯一标识；同一用户同时段不能重复登录"执行操作]

**Then**
- E-USER [BR-39] 用户都应有唯一标识；同一用户同时段不能重复登录 (behavior) [BR: BR-39]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-053 (×4)：用户数据准备就绪时，执行用户登录超时规则，验证用户无操作30分钟后需重新登录
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-040`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"用户登录系统后若30分钟内无任何操作，则需要重新登录"执行操作事件 [按规则"用户登录系统后若30分钟内无任何操作，则需要重新登录"执行操作]

**Then**
- E-USER [BR-40] 用户登录系统后若30分钟内无任何操作，则需要重新登录 (behavior) [BR: BR-40]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-054 (×4)：用户连续密码错误3次时，验证账户被锁定并可由管理员解锁
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-041`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"普通用户（除系统管理员和审计管理员外）连续密码错误3次时锁定该账户；锁定后可由系统管理员解锁"执行操作事件 [按规则"普通用户（除系统管理员和审计管理员外）连续密码错误3次时锁定该账户；锁定后可由系统管理员解锁"执行操作]

**Then**
- E-USER [BR-41] 普通用户（除系统管理员和审计管理员外）连续密码错误3次时锁定该账户；锁定后可由系统管理员解锁 (behavior) [BR: BR-41]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-055 (×4)：用户密码有效期为7天，验证过期后强制更改且不能与上一密码相同
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-042`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"普通用户密码有效期为7天；过期后强制对密码进行更改；不能与上一密码相同"执行操作事件 [按规则"普通用户密码有效期为7天；过期后强制对密码进行更改；不能与上一密码相同"执行操作]

**Then**
- E-USER [BR-42] 普通用户密码有效期为7天；过期后强制对密码进行更改；不能与上一密码相同 (behavior) [BR: BR-42]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-056 (×4)：用户修改密码时，验证需要输入原密码且输入不正确给出提示
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-043`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"用户修改自己密码时需要输入原密码；输入不正确则给出提示"执行操作事件 [按规则"用户修改自己密码时需要输入原密码；输入不正确则给出提示"执行操作]

**Then**
- E-USER [BR-43] 用户修改自己密码时需要输入原密码；输入不正确则给出提示 (behavior) [BR: BR-43]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-057 (×4)：用户设置新密码时，验证新密码与原密码不同且需两次输入相同
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-044`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"新密码与原密码应不同；新密码需要确认输入两次且相同"执行操作事件 [按规则"新密码与原密码应不同；新密码需要确认输入两次且相同"执行操作]

**Then**
- E-USER [BR-44] 新密码与原密码应不同；新密码需要确认输入两次且相同 (behavior) [BR: BR-44]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-058 (×4)：对服务端返回客户端的数据进行加密，验证加密操作执行
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-045`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"对服务端返回客户端的数据进行加密"执行操作事件 [按规则"对服务端返回客户端的数据进行加密"执行操作]

**Then**
- E-USER [BR-45] 对服务端返回客户端的数据进行加密 (behavior) [BR: BR-45]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-059 (×4)：用户信息传输加密规则执行后，验证用户信息加密
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-046`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"对客户端提交到服务端的用户相关信息在传输中进行加密"执行操作事件 [按规则"对客户端提交到服务端的用户相关信息在传输中进行加密"执行操作]

**Then**
- E-USER [BR-46] 对客户端提交到服务端的用户相关信息在传输中进行加密 (behavior) [BR: BR-46]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-060 (×4)：页面提示信息规则执行后，验证提示信息不含系统后台和技术框架信息
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-049`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"页面提示信息不能含有系统后台、技术框架等信息"执行操作事件 [按规则"页面提示信息不能含有系统后台、技术框架等信息"执行操作]

**Then**
- E-USER [BR-49] 页面提示信息不能含有系统后台、技术框架等信息 (behavior) [BR: BR-49]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-061 (×4)：用户账号或密码错误提示规则执行后，验证有错误提示
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-050`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"当输入的用户账号或者密码错时有提示"执行操作事件 [按规则"当输入的用户账号或者密码错时有提示"执行操作]

**Then**
- E-USER [BR-50] 当输入的用户账号或者密码错时有提示 (behavior) [BR: BR-50]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-062 (×4)：日期类数据输入规则执行后，验证提供日历选择功能
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-051`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER, E-PROJ, E-PLAN相关数据已准备)

**When**
- E-USER 按规则"日期类数据输入应提供日历选择功能"执行操作事件 [按规则"日期类数据输入应提供日历选择功能"执行操作]

**Then**
- E-USER [BR-51] 日期类数据输入应提供日历选择功能 (behavior) [BR: BR-51]

**后置状态**：E-USER→(规则验证完成)
**弱依赖**：PROC-014.1, PROC-016.1
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-063 (×4)：查询功能组合查询规则执行后，验证支持两个以上字段组合查询
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-052`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER, E-PROJ, E-PLAN, E-EXPERT, E-LOG相关数据已准备)

**When**
- E-USER 按规则"查询功能中的组合查询支持两个（含）以上字段与的查询"执行操作事件 [按规则"查询功能中的组合查询支持两个（含）以上字段与的查询"执行操作]

**Then**
- E-USER [BR-52] 查询功能中的组合查询支持两个（含）以上字段与的查询 (behavior) [BR: BR-52]

**后置状态**：E-USER→(规则验证完成)
**弱依赖**：PROC-014.1, PROC-016.1, PROC-023.1
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-064 (×4)：用户操作时，验证必填项标识和提示信息
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-053`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER, E-PROJ, E-PLAN, E-EXPERT, E-ORG相关数据已准备)

**When**
- E-USER 按规则"添加、编辑页面中的必填项应给出*标识；对未输入的必填项给出提示"执行操作事件 [按规则"添加、编辑页面中的必填项应给出*标识；对未输入的必填项给出提示"执行操作]

**Then**
- E-USER [BR-53] 添加、编辑页面中的必填项应给出*标识；对未输入的必填项给出提示 (behavior) [BR: BR-53]

**后置状态**：E-USER→(规则验证完成)
**弱依赖**：PROC-014.1, PROC-016.1, PROC-023.1, PROC-033.1
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-065 (×4)：用户操作时，验证关联数据一致性和同步性
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-054`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER, E-PROJ, E-PLAN, E-EXPERT, E-ORG相关数据已准备)

**When**
- E-USER 按规则"同页面关联数据刷新后保持一致性；不同页面重新打开关联数据应保持同步"执行操作事件 [按规则"同页面关联数据刷新后保持一致性；不同页面重新打开关联数据应保持同步"执行操作]

**Then**
- E-USER [BR-54] 同页面关联数据刷新后保持一致性；不同页面重新打开关联数据应保持同步 (behavior) [BR: BR-54]

**后置状态**：E-USER→(规则验证完成)
**弱依赖**：PROC-014.1, PROC-016.1, PROC-023.1, PROC-033.1
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-066 (×4)：用户登录时，验证待办任务和超时任务说明
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-055`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER, E-PLAN相关数据已准备)

**When**
- E-USER 按规则"评审管理员、评审助理和评审专家登录账号时应有待办任务和距超时5小时内的任务的说明"执行操作事件 [按规则"评审管理员、评审助理和评审专家登录账号时应有待办任务和距超时5小时内的任务的说明"执行操作]

**Then**
- E-USER [BR-55] 评审管理员、评审助理和评审专家登录账号时应有待办任务和距超时5小时内的任务的说明 (behavior) [BR: BR-55]

**后置状态**：E-USER→(规则验证完成)
**弱依赖**：PROC-014.1
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-067 (×4)：用户注册时，验证用户账号规则
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-063`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"用户.用户账号：必填项；可由汉字、字母、数字、下划线组成；不可重复"执行操作事件 [按规则"用户.用户账号：必填项；可由汉字、字母、数字、下划线组成；不可重复"执行操作]

**Then**
- E-USER [BR-63] 用户.用户账号：必填项；可由汉字、字母、数字、下划线组成；不可重复 (behavior) [BR: BR-63]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-068 (×4)：用户注册时，验证登录密码规则
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-064`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"用户.登录密码：必填项；只能由数字、字母和特殊符号组成；长度8-18"执行操作事件 [按规则"用户.登录密码：必填项；只能由数字、字母和特殊符号组成；长度8-18"执行操作]

**Then**
- E-USER [BR-64] 用户.登录密码：必填项；只能由数字、字母和特殊符号组成；长度8-18 (behavior) [BR: BR-64]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-069 (×4)：用户信息准备就绪时，执行手机号码验证规则，验证手机号码格式正确
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-065`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"用户.手机号码：必填项；数字组成；手机号验证规则（首位1，次位3-9，共11位）；唯一"执行操作事件 [按规则"用户.手机号码：必填项；数字组成；手机号验证规则（首位1，次位3-9，共11位）；唯一"执行操作]

**Then**
- E-USER [BR-65] 用户.手机号码：必填项；数字组成；手机号验证规则（首位1，次位3-9，共11位）；唯一 (behavior) [BR: BR-65]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-070 (×4)：用户信息准备就绪时，执行技术领域选择规则，验证技术领域选择正确
**业务定位**：P1 ｜ rule ｜ 溯源: `RO-BR-066`
**阶段依据**：dep_map_max_phase.E-USER.1

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"用户.技术领域：必填项；取值范围 A-J 领域；可选择1-3个；只有评审专家有该信息"执行操作事件 [按规则"用户.技术领域：必填项；取值范围 A-J 领域；可选择1-3个；只有评审专家有该信息"执行操作]

**Then**
- E-USER [BR-66] 用户.技术领域：必填项；取值范围 A-J 领域；可选择1-3个；只有评审专家有该信息 (behavior) [BR: BR-66]

**后置状态**：E-USER→(规则验证完成)
**多实例**：4 × entity=E-USER dim_count=1 instances=4

### PROC-071 (×2)：合格机构满足降级条件时，执行降级操作，验证机构状态变更为不合格
**业务定位**：P2 ｜ happy ｜ 溯源: `T-O01`
**阶段依据**：dep_state_phase_map.E-ORG.机构状态.不合格

**Given**
- E-ORG.机构状态 状态 = 合格 ([实例 1] 机构状态为合格; 差累计3次及以上，或差1次及以上且不合格3次及以上，或不合格5次及以上)

**When**
- E-ORG.机构状态 合格机构降级判定（目标状态：不合格） by [待确认角色] [合格机构降级判定]

**Then**
- E-ORG.机构状态 状态转换为不合格 (state)

**后置状态**：E-ORG.机构状态→不合格
**依赖**：PROC-032.1, PROC-034.1
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-072 (×2)：试用机构满足降级条件时，执行降级操作，验证机构状态变更为不合格
**业务定位**：P2 ｜ happy ｜ 溯源: `T-O04`
**阶段依据**：dep_state_phase_map.E-ORG.机构状态.不合格

**Given**
- E-ORG.机构状态 状态 = 试用 ([实例 1] 机构状态为试用; 差2次及以上，或差1次且不合格2次及以上，或不合格4次及以上，或同时满足升降条件)

**When**
- E-ORG.机构状态 试用机构降级（目标状态：不合格） by [待确认角色] [试用机构降级]

**Then**
- E-ORG.机构状态 状态转换为不合格 (state)

**后置状态**：E-ORG.机构状态→不合格
**依赖**：PROC-032.1, PROC-033.1
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-073 (×2)：机构类型配置变更时，验证机构类型显示为修改后的值
**业务定位**：P2 ｜ happy ｜ 溯源: `EO-ATC-007`
**阶段依据**：dep_map_max_phase.E-ORG.2

**Given**
- E-ORG 状态 = 机构类型为当前值 ([实例 1] 当前机构类型配置值)

**When**
- E-ORG 机构类型配置变更事件 [修改机构类型]

**Then**
- E-ORG.机构类型 机构类型显示为修改后的值 (state)

**操作提示**
1. 导航至E-ORG配置入口

**后置状态**：E-ORG.机构类型→(已修改)
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-074 (×2)：规则适用前提满足时，执行评审规则，验证不合格机构所属项目无法进行评审
**业务定位**：P2 ｜ rule ｜ 溯源: `RO-BR-022`
**阶段依据**：dep_map_max_phase.E-ORG.2

**Given**
- E-ORG 状态 = 规则适用前提满足 ([实例 1] E-ORG, E-PROJ相关数据已准备)

**When**
- E-ORG 按规则"不能对不合格研制机构所属项目进行评审"执行操作事件 [按规则"不能对不合格研制机构所属项目进行评审"执行操作]

**Then**
- E-ORG [BR-22]正面: 不能对不合格研制机构所属项目进行评审 (behavior) [BR: BR-22]
- E-ORG [BR-22]负面: 不满足条件时规则不触发 (behavior) [BR: BR-22]

**后置状态**：E-ORG→(规则验证完成)
**弱依赖**：PROC-016.1
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-075 (×2)：规则适用前提满足时，执行机构提级规则，验证系统管理员可对不合格机构提为试用机构
**业务定位**：P2 ｜ rule ｜ 溯源: `RO-BR-024`
**阶段依据**：dep_map_max_phase.E-ORG.2

**Given**
- E-ORG 状态 = 规则适用前提满足 ([实例 1] E-ORG相关数据已准备)

**When**
- E-ORG 按规则"系统管理员可以对不合格机构提为试用机构；研制机构累计3次评级为不合格，则不能提为试用机构"执行操作事件 [按规则"系统管理员可以对不合格机构提为试用机构；研制机构累计3次评级为不合格，则不能提为试用机构"执行操作]

**Then**
- E-ORG [BR-24]正面: 系统管理员可以对不合格机构提为试用机构；研制机构累计3次评级为不合格，则不能提为试用机构 (behavior) [BR: BR-24]
- E-ORG [BR-24]负面: 不满足条件时规则不触发 (behavior) [BR: BR-24]

**后置状态**：E-ORG→(规则验证完成)
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-076 (×2)：规则适用前提满足时，执行试用机构升降级规则，验证试用机构升降级条件正确
**业务定位**：P2 ｜ rule ｜ 溯源: `RO-BR-025`
**阶段依据**：dep_map_max_phase.E-ORG.2

**Given**
- E-ORG 状态 = 规则适用前提满足 ([实例 1] E-ORG相关数据已准备)

**When**
- E-ORG 按规则"试用机构：累计10次优可升合格；累计2次差降不合格；累计1次差且2次及以上不合格降不合格；累计4次不合格降不合格；同时满足升降条件时降为不合格"执行操作事件 [按规则"试用机构：累计10次优可升合格；累计2次差降不合格；累计1次差且2次及以上不合格降不合格；累计4次不合格降不合格；同时满足升降条件时降为不合格"执行操作]

**Then**
- E-ORG [BR-25]正面: 试用机构：累计10次优可升合格；累计2次差降不合格；累计1次差且2次及以上不合格降不合格；累计4次不合格降不合格；同时满足升降条件时降为不合格 (behavior) [BR: BR-25]
- E-ORG [BR-25]负面: 不满足条件时规则不触发 (behavior) [BR: BR-25]

**后置状态**：E-ORG→(规则验证完成)
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-077 (×2)：机构编辑时，验证不可编辑上级机构、机构编码、不合格次数和机构状态
**业务定位**：P2 ｜ rule ｜ 溯源: `RO-BR-031`
**阶段依据**：dep_map_max_phase.E-ORG.2

**Given**
- E-ORG 状态 = 规则适用前提满足 ([实例 1] E-ORG相关数据已准备)

**When**
- E-ORG 按规则"机构编辑不可编辑上级机构、机构编码、不合格次数和机构状态"执行操作事件 [按规则"机构编辑不可编辑上级机构、机构编码、不合格次数和机构状态"执行操作]

**Then**
- E-ORG [BR-31] 机构编辑不可编辑上级机构、机构编码、不合格次数和机构状态 (behavior) [BR: BR-31]

**后置状态**：E-ORG→(规则验证完成)
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-078 (×2)：评审计划待启动状态下，启动评审计划后，验证状态转换为待评审
**业务定位**：P2 ｜ happy ｜ 溯源: `T-PL04`
**阶段依据**：phase_table.评审计划状态.待评审

**Given**
- E-PLAN.评审计划状态 状态 = 待启动 ([实例 1] 评审计划处于待启动状态)

**When**
- E-PLAN.评审计划状态 启动评审计划（目标状态：待评审） by R-ASSIST [启动评审计划]

**Then**
- E-PLAN.评审计划状态 状态转换为待评审 (state)

**后置状态**：E-PLAN.评审计划状态→待评审
**依赖**：PROC-014.1, PROC-035.1
**弱依赖**：PROC-086.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-079 (×2)：评审计划待启动且启动时限已过时，系统启动超时后，验证状态转换为待评审
**业务定位**：P2 ｜ happy ｜ 溯源: `T-PL04T`
**阶段依据**：phase_table.评审计划状态.待评审

**Given**
- E-PLAN.评审计划状态 状态 = 待启动 ([实例 1] 评审计划处于待启动状态; 启动时限已过)

**When**
- E-PLAN.评审计划状态 启动超时（目标状态：待评审） by 系统 [启动超时]

**Then**
- E-PLAN.评审计划状态 状态转换为待评审 (state)

**后置状态**：E-PLAN.评审计划状态→待评审
**依赖**：PROC-014.1, PROC-035.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-080 (×2)：评审计划接近截止时间时，系统启动超时后，验证状态转换为待评审并生效时间边界
**业务定位**：P2 ｜ time_sensitive ｜ 溯源: `T-PL04T`
**阶段依据**：phase_table.评审计划状态.待评审 (time_boundary)

**Given**
- E-PLAN.评审计划状态 状态 = 待启动 ([实例 1] 时间边界条件: 接近截止时间)

**When**
- E-PLAN.评审计划状态 启动超时(时间边界)（目标状态：待评审） by 系统 [启动超时(边界)]

**Then**
- E-PLAN.评审计划状态 状态转换为待评审(时间边界生效) (state)

**后置状态**：E-PLAN.评审计划状态→待评审(时间边界)
**依赖**：PROC-014.1, PROC-035.1, PROC-079.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-081 (×2)：评审计划时间过期时，尝试启动超时事件后，验证操作不可执行或状态不变
**业务定位**：P2 ｜ time_sensitive ｜ 溯源: `T-PL04T`
**阶段依据**：phase_table.评审计划状态.待评审 (time_expired)

**Given**
- E-PLAN.评审计划状态 状态 = 待启动 ([实例 1] 时间过期条件: 超过截止时间)

**When**
- E-PLAN.评审计划状态 尝试启动超时事件(已过期) by 系统 [尝试启动超时(已过期)]

**Then**
- E-PLAN.评审计划状态 操作不可执行或状态不变 (behavior)

**后置状态**：E-PLAN.评审计划状态→(过期未执行)
**依赖**：PROC-014.1, PROC-035.1, PROC-079.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-082 (×2)：评审计划暂停状态下，重启评审计划后，验证状态转换为待评审
**业务定位**：P2 ｜ rollback ｜ 溯源: `T-PL09a`
**阶段依据**：phase_table.评审计划状态.暂停

**Given**
- E-PLAN.评审计划状态 状态 = 暂停 ([实例 1] 评审计划处于暂停状态; 暂停前状态为待评审)

**When**
- E-PLAN.评审计划状态 重启评审计划（目标状态：待评审） by R-ASSIST [重启评审计划]

**Then**
- E-PLAN.评审计划状态 状态转换为待评审 (state)

**后置状态**：E-PLAN.评审计划状态→待评审
**依赖**：PROC-014.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-083 (×2)：评审计划待评审状态下，暂停评审计划后，验证状态转换为暂停
**业务定位**：P2 ｜ happy ｜ 溯源: `T-PL08c, T-PL08a, T-PL08b`
**阶段依据**：phase_table.评审计划状态.暂停

**Given**
- E-PLAN.评审计划状态 状态 = 待评审 ([实例 1] 评审计划处于待评审状态)

**When**
- E-PLAN.评审计划状态 暂停评审计划（目标状态：暂停） by R-ASSIST [暂停评审计划]

**Then**
- E-PLAN.评审计划状态 状态转换为暂停 (state)

**后置状态**：E-PLAN.评审计划状态→暂停
**依赖**：PROC-014.1, PROC-078.1, PROC-082.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-084 (×2)：评审计划暂停且暂停前状态为评审中时，重启评审计划后，验证状态转换为评审中
**业务定位**：P2 ｜ rollback ｜ 溯源: `T-PL09b`
**阶段依据**：phase_table.评审计划状态.暂停

**Given**
- E-PLAN.评审计划状态 状态 = 暂停 ([实例 1] 评审计划处于暂停状态; 暂停前状态为评审中)

**When**
- E-PLAN.评审计划状态 重启评审计划（目标状态：评审中） by R-ASSIST [重启评审计划]

**Then**
- E-PLAN.评审计划状态 状态转换为评审中 (state)

**后置状态**：E-PLAN.评审计划状态→评审中
**依赖**：PROC-014.1, PROC-083.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-085 (×2)：评审计划暂停且暂停前状态为已完成时，重启评审计划后，验证状态转换为已完成
**业务定位**：P2 ｜ rollback ｜ 溯源: `T-PL09c`
**阶段依据**：phase_table.评审计划状态.暂停

**Given**
- E-PLAN.评审计划状态 状态 = 暂停 ([实例 1] 评审计划处于暂停状态; 暂停前状态为已完成)

**When**
- E-PLAN.评审计划状态 重启评审计划（目标状态：已完成） by R-ASSIST [重启评审计划]

**Then**
- E-PLAN.评审计划状态 状态转换为已完成 (state)

**后置状态**：E-PLAN.评审计划状态→已完成
**依赖**：PROC-014.1, PROC-083.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-086 (×5)：项目已选入状态下，纳入评审计划后，验证项目状态转换为待评审
**业务定位**：P2 ｜ happy ｜ 溯源: `T-P04`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.待评审

**Given**
- E-PROJ.项目状态 状态 = 已选入 ([实例 1] 项目处于已选入状态)

**When**
- E-PROJ.项目状态 纳入评审计划（目标状态：待评审） by R-ADMIN [纳入评审计划]

**Then**
- E-PROJ.项目状态 状态转换为待评审 (state)

**后置状态**：E-PROJ.项目状态→待评审
**依赖**：PROC-016.1, PROC-039.1, PROC-041.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-087 (×5)：项目待评审状态下，取消评审计划导致项目回退，验证项目状态变更为已选入
**业务定位**：P2 ｜ rollback ｜ 溯源: `T-P08`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.待评审

**Given**
- E-PROJ.项目状态 状态 = 待评审 ([实例 1] 项目处于待评审状态; 评审计划状态为取消结束)

**When**
- E-PROJ.项目状态 取消评审计划导致项目回退（目标状态：已选入） by [待确认角色] [取消评审计划导致项目回退]

**Then**
- E-PROJ.项目状态 状态转换为已选入 (state)

**后置状态**：E-PROJ.项目状态→已选入
**依赖**：PROC-015.1, PROC-016.1, PROC-086.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-088 (×2)：评审计划待评审状态下，评审专家首次打分保存，验证评审计划状态变更为评审中
**业务定位**：P3 ｜ happy ｜ 溯源: `T-PL05`
**阶段依据**：phase_table.评审计划状态.评审中

**Given**
- E-PLAN.评审计划状态 状态 = 待评审 ([实例 1] 评审计划处于待评审状态)
- E-PLAN.评审计划状态 状态 = 待评审 (评审专家对该计划的项目进行打分保存)

**When**
- E-PLAN.评审计划状态 评审专家首次打分保存（目标状态：评审中） by R-EXPERT [评审专家首次打分保存]

**Then**
- E-PLAN.评审计划状态 状态转换为评审中 (state)

**后置状态**：E-PLAN.评审计划状态→评审中
**依赖**：PROC-014.1, PROC-078.1, PROC-082.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-089 (×5)：项目待评审状态下，启动评审计划，验证项目状态变更为评审中
**业务定位**：P3 ｜ happy ｜ 溯源: `T-P05`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.评审中

**Given**
- E-PROJ.项目状态 状态 = 待评审 ([实例 1] 项目处于待评审状态; 评审计划状态为待评审)

**When**
- E-PROJ.项目状态 评审计划启动（目标状态：评审中） by [待确认角色] [评审计划启动]

**Then**
- E-PROJ.项目状态 状态转换为评审中 (state)

**后置状态**：E-PROJ.项目状态→评审中
**依赖**：PROC-016.1, PROC-078.1, PROC-079.1, PROC-082.1, PROC-086.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-090 (×5)：项目评审中状态下，已完成计划归档时项目回退，验证项目状态变更为已选入
**业务定位**：P3 ｜ branch ｜ 溯源: `T-P09`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.评审中

**Given**
- E-PROJ.项目状态 状态 = 评审中 ([实例 1] 项目处于评审中状态; 所属评审计划状态为已完成)
- E-PROJ.项目状态 状态 = 评审中 (计划归档时（4.5(5)e）)

**When**
- E-PROJ.项目状态 已完成计划归档时项目回退（目标状态：已选入） by [待确认角色] [已完成计划归档时项目回退]

**Then**
- E-PROJ.项目状态 状态转换为已选入 (state)

**后置状态**：E-PROJ.项目状态→已选入
**依赖**：PROC-016.1, PROC-085.1, PROC-089.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-091 (×2)：评审计划处于评审中状态时，系统自动将所有项目变为待归档，状态转换为已完成
**业务定位**：P4 ｜ happy ｜ 溯源: `T-PL06`
**阶段依据**：phase_table.评审计划状态.已完成

**Given**
- E-PLAN.评审计划状态 状态 = 评审中 ([实例 1] 评审计划处于评审中状态)
- E-PLAN.评审计划状态 状态 = 评审中 (评审计划中所有项目在评审时限内变为待归档状态)

**When**
- E-PLAN.评审计划状态 所有项目变为待归档（目标状态：已完成） by 系统 [所有项目变为待归档]

**Then**
- E-PLAN.评审计划状态 状态转换为已完成 (state)

**后置状态**：E-PLAN.评审计划状态→已完成
**依赖**：PROC-014.1, PROC-084.1, PROC-088.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-092 (×2)：评审计划待评审且评审时限已过时，系统自动将评审超时，状态转换为已完成
**业务定位**：P4 ｜ happy ｜ 溯源: `T-PL06T3, T-PL06T1, T-PL06T2`
**阶段依据**：phase_table.评审计划状态.已完成

**Given**
- E-PLAN.评审计划状态 状态 = 待评审 ([实例 1] 评审计划处于待评审状态; 评审时限已过)

**When**
- E-PLAN.评审计划状态 评审超时（目标状态：已完成） by 系统 [评审超时]

**Then**
- E-PLAN.评审计划状态 状态转换为已完成 (state)

**后置状态**：E-PLAN.评审计划状态→已完成
**依赖**：PROC-014.1, PROC-078.1, PROC-082.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-093 (×2)：评审计划接近截止时间时，系统自动将评审超时，状态转换为已完成（时间边界生效）
**业务定位**：P4 ｜ time_sensitive ｜ 溯源: `T-PL06T3, T-PL06T1, T-PL06T2`
**阶段依据**：phase_table.评审计划状态.已完成 (time_boundary)

**Given**
- E-PLAN.评审计划状态 状态 = 待评审 ([实例 1] 时间边界条件: 接近截止时间)

**When**
- E-PLAN.评审计划状态 评审超时(时间边界)（目标状态：已完成） by 系统 [评审超时(边界)]

**Then**
- E-PLAN.评审计划状态 状态转换为已完成(时间边界生效) (state)

**后置状态**：E-PLAN.评审计划状态→已完成(时间边界)
**依赖**：PROC-014.1, PROC-078.1, PROC-082.1, PROC-092.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-094 (×2)：评审计划时间过期时，尝试评审超时事件，操作不可执行或状态不变
**业务定位**：P4 ｜ time_sensitive ｜ 溯源: `T-PL06T3, T-PL06T1, T-PL06T2`
**阶段依据**：phase_table.评审计划状态.已完成 (time_expired)

**Given**
- E-PLAN.评审计划状态 状态 = 待评审 ([实例 1] 时间过期条件: 超过截止时间)

**When**
- E-PLAN.评审计划状态 尝试评审超时事件(已过期) by 系统 [尝试评审超时(已过期)]

**Then**
- E-PLAN.评审计划状态 操作不可执行或状态不变 (behavior)

**后置状态**：E-PLAN.评审计划状态→(过期未执行)
**依赖**：PROC-014.1, PROC-078.1, PROC-082.1, PROC-092.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-095 (×5)：项目处于评审中状态且评审组全部专家已提交打分时，提交打分后，项目状态转换为待归档
**业务定位**：P4 ｜ happy ｜ 溯源: `T-P06`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.待归档

**Given**
- E-PROJ.项目状态 状态 = 评审中 ([实例 1] 项目处于评审中状态)
- E-PROJ.项目状态 状态 = 评审中 (评审组全部专家已提交项目打分)

**When**
- E-PROJ.项目状态 评审组全部专家提交打分（目标状态：待归档） by [待确认角色] [评审组全部专家提交打分]

**Then**
- E-PROJ.项目状态 状态转换为待归档 (state)

**后置状态**：E-PROJ.项目状态→待归档
**依赖**：PROC-016.1, PROC-089.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-096 (×2)：当前评审时段配置变更时，评审时段显示为修改后的值
**业务定位**：P5 ｜ happy ｜ 溯源: `EO-ATC-006`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 评审时段为当前值 ([实例 1] 当前评审时段配置值)

**When**
- E-PLAN 评审时段配置变更事件 [修改评审时段]

**Then**
- E-PLAN.评审时段 评审时段显示为修改后的值 (state)

**操作提示**
1. 导航至E-PLAN配置入口

**后置状态**：E-PLAN.评审时段→(已修改)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-097 (×2)：评审计划已完成状态时，管理员归档评审计划，状态转换为结束
**业务定位**：P5 ｜ audit ｜ 溯源: `T-PL07`
**阶段依据**：phase_table.评审计划状态.结束

**Given**
- E-PLAN.评审计划状态 状态 = 已完成 ([实例 1] 评审计划处于已完成状态)

**When**
- E-PLAN.评审计划状态 归档评审计划（目标状态：结束） by R-ADMIN [归档评审计划]

**Then**
- E-PLAN.评审计划状态 状态转换为结束 (state)

**后置状态**：E-PLAN.评审计划状态→结束
**依赖**：PROC-014.1, PROC-085.1, PROC-091.1, PROC-092.1
**弱依赖**：PROC-086.1, PROC-089.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-098 (×2)：评审计划已完成且归档时限已过时，系统自动将归档超时，状态转换为超时结束
**业务定位**：P5 ｜ audit ｜ 溯源: `T-PL07T`
**阶段依据**：phase_table.评审计划状态.超时结束

**Given**
- E-PLAN.评审计划状态 状态 = 已完成 ([实例 1] 评审计划处于已完成状态; 归档时限已过)

**When**
- E-PLAN.评审计划状态 归档超时（目标状态：超时结束） by 系统 [归档超时]

**Then**
- E-PLAN.评审计划状态 状态转换为超时结束 (state)

**后置状态**：E-PLAN.评审计划状态→超时结束
**依赖**：PROC-014.1, PROC-085.1, PROC-091.1, PROC-092.1
**弱依赖**：PROC-086.1, PROC-089.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-099 (×2)：评审计划接近截止时间时，系统自动将归档超时，状态转换为超时结束（时间边界生效）
**业务定位**：P5 ｜ time_sensitive ｜ 溯源: `T-PL07T`
**阶段依据**：phase_table.评审计划状态.超时结束 (time_boundary)

**Given**
- E-PLAN.评审计划状态 状态 = 已完成 ([实例 1] 时间边界条件: 接近截止时间)

**When**
- E-PLAN.评审计划状态 归档超时(时间边界)（目标状态：超时结束） by 系统 [归档超时(边界)]

**Then**
- E-PLAN.评审计划状态 状态转换为超时结束(时间边界生效) (state)

**后置状态**：E-PLAN.评审计划状态→超时结束(时间边界)
**依赖**：PROC-014.1, PROC-085.1, PROC-091.1, PROC-092.1, PROC-098.1
**弱依赖**：PROC-086.1, PROC-089.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-100 (×2)：评审计划超过截止时间时，系统尝试归档超时，验证操作不可执行或状态不变
**业务定位**：P5 ｜ time_sensitive ｜ 溯源: `T-PL07T`
**阶段依据**：phase_table.评审计划状态.超时结束 (time_expired)

**Given**
- E-PLAN.评审计划状态 状态 = 已完成 ([实例 1] 时间过期条件: 超过截止时间)

**When**
- E-PLAN.评审计划状态 尝试归档超时事件(已过期) by 系统 [尝试归档超时(已过期)]

**Then**
- E-PLAN.评审计划状态 操作不可执行或状态不变 (behavior)

**后置状态**：E-PLAN.评审计划状态→(过期未执行)
**依赖**：PROC-014.1, PROC-085.1, PROC-091.1, PROC-092.1, PROC-098.1
**弱依赖**：PROC-086.1, PROC-089.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-101 (×2)：规则适用前提满足时，执行规则，验证评审管理员选取项目纳入评审计划
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-006`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 规则适用前提满足 ([实例 1] E-PLAN, E-PROJ相关数据已准备)

**When**
- E-PLAN 按规则"评审管理员从处于已选入状态的项目中选取1-5个项目纳入评审计划"执行操作事件 [按规则"评审管理员从处于已选入状态的项目中选取1-5个项目纳入评审计划"执行操作]

**Then**
- E-PLAN [BR-06] 评审管理员从处于已选入状态的项目中选取1-5个项目纳入评审计划 (behavior) [BR: BR-06]

**后置状态**：E-PLAN→(规则验证完成)
**弱依赖**：PROC-016.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-102 (×2)：规则适用前提满足时，执行规则，验证评审专家技术领域覆盖项目领域
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-008`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 规则适用前提满足 ([实例 1] E-PLAN, E-EXPERT, E-PROJ相关数据已准备)

**When**
- E-PLAN 按规则"每个评审专家的技术领域应覆盖评审计划中项目的领域"执行操作事件 [按规则"每个评审专家的技术领域应覆盖评审计划中项目的领域"执行操作]

**Then**
- E-PLAN [BR-08] 每个评审专家的技术领域应覆盖评审计划中项目的领域 (behavior) [BR: BR-08]

**后置状态**：E-PLAN→(规则验证完成)
**弱依赖**：PROC-016.1, PROC-023.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-103 (×2)：规则适用前提满足时，执行规则，验证下发后的评审计划不能编辑或取消
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-014`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 规则适用前提满足 ([实例 1] E-PLAN相关数据已准备)

**When**
- E-PLAN 按规则"下发后的评审计划不能编辑或取消"执行操作事件 [按规则"下发后的评审计划不能编辑或取消"执行操作]

**Then**
- E-PLAN [BR-14] 下发后的评审计划不能编辑或取消 (behavior) [BR: BR-14]

**后置状态**：E-PLAN→(规则验证完成)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-104 (×2)：规则适用前提满足时，执行规则，验证暂停时专家不能评审且管理员不能归档
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-015`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 规则适用前提满足 ([实例 1] E-PLAN, E-SCORE相关数据已准备)

**When**
- E-PLAN 按规则"暂停时专家不能对计划中的项目进行评审；评审助理和评审管理员不能对该计划归档"执行操作事件 [按规则"暂停时专家不能对计划中的项目进行评审；评审助理和评审管理员不能对该计划归档"执行操作]

**Then**
- E-PLAN [BR-15]正面: 暂停时专家不能对计划中的项目进行评审；评审助理和评审管理员不能对该计划归档 (behavior) [BR: BR-15]
- E-PLAN [BR-15]负面: 不满足条件时规则不触发 (behavior) [BR: BR-15]

**后置状态**：E-PLAN→(规则验证完成)
**弱依赖**：PROC-025.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-105 (×2)：规则适用前提满足时，执行规则，验证暂停期间计时不停
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-016`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 规则适用前提满足 ([实例 1] E-PLAN相关数据已准备)

**When**
- E-PLAN 按规则"暂停期间计时不停"执行操作事件 [按规则"暂停期间计时不停"执行操作]

**Then**
- E-PLAN [BR-16]正面: 暂停期间计时不停 (behavior) [BR: BR-16]
- E-PLAN [BR-16]负面: 不满足条件时规则不触发 (behavior) [BR: BR-16]

**后置状态**：E-PLAN→(规则验证完成)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-106 (×2)：规则适用前提满足时，执行规则，验证管理员和助理可删除特定状态的计划
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-017`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 规则适用前提满足 ([实例 1] E-PLAN相关数据已准备)

**When**
- E-PLAN 按规则"评审管理员和评审助理可删除处于已建立状态和取消结束状态的计划"执行操作事件 [按规则"评审管理员和评审助理可删除处于已建立状态和取消结束状态的计划"执行操作]

**Then**
- E-PLAN [BR-17]正面: 评审管理员和评审助理可删除处于已建立状态和取消结束状态的计划 (behavior) [BR: BR-17]
- E-PLAN [BR-17]负面: 不满足条件时规则不触发 (behavior) [BR: BR-17]

**后置状态**：E-PLAN→(规则验证完成)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-107 (×2)：规则适用前提满足时，执行规则，验证不合格机构影响和计划取消
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-023`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 规则适用前提满足 ([实例 1] E-PLAN, E-PROJ, E-ORG相关数据已准备)

**When**
- E-PLAN 按规则"已下发的评审计划中的项目不受不合格机构影响；对未下发计划的项目从计划中去掉；若某未下发评审计划中的项目均属于不合格的研制机构，则取消该计划"执行操作事件 [按规则"已下发的评审计划中的项目不受不合格机构影响；对未下发计划的项目从计划中去掉；若某未下发评审计划中的项目均属于不合格的研制机构，则取消该计划"执行操作]

**Then**
- E-PLAN [BR-23]正面: 已下发的评审计划中的项目不受不合格机构影响；对未下发计划的项目从计划中去掉；若某未下发评审计划中的项目均属于不合格的研制机构，则取消该计划 (behavior) [BR: BR-23]
- E-PLAN [BR-23]负面: 不满足条件时规则不触发 (behavior) [BR: BR-23]

**后置状态**：E-PLAN→(规则验证完成)
**弱依赖**：PROC-016.1, PROC-033.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-108 (×2)：规则适用前提满足时，执行规则，验证组建评审组时显示匹配的评审专家
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-056`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 规则适用前提满足 ([实例 1] E-PLAN, E-EXPERT相关数据已准备)

**When**
- E-PLAN 按规则"在组建评审组时可以根据项目领域和回避规则显示匹配的评审专家"执行操作事件 [按规则"在组建评审组时可以根据项目领域和回避规则显示匹配的评审专家"执行操作]

**Then**
- E-PLAN [BR-56] 在组建评审组时可以根据项目领域和回避规则显示匹配的评审专家 (behavior) [BR: BR-56]

**后置状态**：E-PLAN→(规则验证完成)
**弱依赖**：PROC-023.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-109 (×2)：规则适用前提满足时，执行规则，验证评审计划编号自动生成且唯一不可编辑
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-060`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 规则适用前提满足 ([实例 1] E-PLAN相关数据已准备)

**When**
- E-PLAN 按规则"评审计划.计划编号：自动生成且唯一；不可编辑"执行操作事件 [按规则"评审计划.计划编号：自动生成且唯一；不可编辑"执行操作]

**Then**
- E-PLAN [BR-60] 评审计划.计划编号：自动生成且唯一；不可编辑 (behavior) [BR: BR-60]

**后置状态**：E-PLAN→(规则验证完成)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-110 (×5)：技术领域配置变更后，验证技术领域显示为修改后的值
**业务定位**：P5 ｜ happy ｜ 溯源: `EO-ATC-004, EO-ATC-001`
**阶段依据**：dep_map_max_phase.E-PROJ.5

**Given**
- E-PROJ 状态 = 技术领域为当前值 ([实例 1] 当前技术领域配置值)

**When**
- E-PROJ 技术领域配置变更事件 [修改技术领域]

**Then**
- E-PROJ.技术领域 技术领域显示为修改后的值 (state)

**操作提示**
1. 导航至E-PROJ配置入口

**后置状态**：E-PROJ.技术领域→(已修改)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-111 (×5)：项目状态为待归档且评审计划已归档时，验证项目状态转换为已归档
**业务定位**：P5 ｜ branch ｜ 溯源: `T-P07c`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.已归档

**Given**
- E-PROJ.项目状态 状态 = 待归档 ([实例 1] 项目处于待归档状态; 项目阶段为验收; 项目的评级在合格及以上)
- E-PROJ.项目状态 状态 = 待归档 (评审计划已归档（状态为结束或超时结束）)

**When**
- E-PROJ.项目状态 归档-验收-合格及以上（目标状态：已归档） by [待确认角色] [归档-验收-合格及以上]

**Then**
- E-PROJ.项目状态 状态转换为已归档 (state)

**后置状态**：E-PROJ.项目状态→已归档
**依赖**：PROC-016.1, PROC-019.1, PROC-095.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-112 (×5)：项目类型配置变更后，验证项目类型显示为修改后的值
**业务定位**：P5 ｜ happy ｜ 溯源: `EO-ATC-002`
**阶段依据**：dep_map_max_phase.E-PROJ.5

**Given**
- E-PROJ 状态 = 项目类型为当前值 ([实例 1] 当前项目类型配置值)

**When**
- E-PROJ 项目类型配置变更事件 [修改项目类型]

**Then**
- E-PROJ.项目类型 项目类型显示为修改后的值 (state)

**操作提示**
1. 导航至E-PROJ配置入口

**后置状态**：E-PROJ.项目类型→(已修改)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-113 (×5)：按规则执行操作时，验证对于本阶段不合格评价结果的项目只有1次选入机会
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-001`
**阶段依据**：dep_map_max_phase.E-PROJ.5

**Given**
- E-PROJ 状态 = 规则适用前提满足 ([实例 1] E-PROJ相关数据已准备)

**When**
- E-PROJ 按规则"对于本阶段不合格评价结果的项目，只有1次选入机会"执行操作事件 [按规则"对于本阶段不合格评价结果的项目，只有1次选入机会"执行操作]

**Then**
- E-PROJ [BR-01]正面: 对于本阶段不合格评价结果的项目，只有1次选入机会 (behavior) [BR: BR-01]
- E-PROJ [BR-01]负面: 不满足条件时规则不触发 (behavior) [BR: BR-01]

**后置状态**：E-PROJ→(规则验证完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-114 (×5)：项目数据准备就绪时，执行规则验证评价结果差项目不可选入
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-002`
**阶段依据**：dep_map_max_phase.E-PROJ.5

**Given**
- E-PROJ 状态 = 规则适用前提满足 ([实例 1] E-PROJ相关数据已准备)

**When**
- E-PROJ 按规则"对于本阶段评价结果为差的项目，不可选入"执行操作事件 [按规则"对于本阶段评价结果为差的项目，不可选入"执行操作]

**Then**
- E-PROJ [BR-02]正面: 对于本阶段评价结果为差的项目，不可选入 (behavior) [BR: BR-02]
- E-PROJ [BR-02]负面: 不满足条件时规则不触发 (behavior) [BR: BR-02]

**后置状态**：E-PROJ→(规则验证完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-115 (×5)：项目数据准备就绪时，执行规则验证只能删除待选入且未评价过的项目
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-003`
**阶段依据**：dep_map_max_phase.E-PROJ.5

**Given**
- E-PROJ 状态 = 规则适用前提满足 ([实例 1] E-PROJ相关数据已准备)

**When**
- E-PROJ 按规则"只能删除待选入且未评价过的项目"执行操作事件 [按规则"只能删除待选入且未评价过的项目"执行操作]

**Then**
- E-PROJ [BR-03]正面: 只能删除待选入且未评价过的项目 (behavior) [BR: BR-03]
- E-PROJ [BR-03]负面: 不满足条件时规则不触发 (behavior) [BR: BR-03]

**后置状态**：E-PROJ→(规则验证完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-116 (×5)：项目数据准备就绪时，执行规则验证只可编辑待选入项目信息或评价过项目附件
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-004`
**阶段依据**：dep_map_max_phase.E-PROJ.5

**Given**
- E-PROJ 状态 = 规则适用前提满足 ([实例 1] E-PROJ相关数据已准备)

**When**
- E-PROJ 按规则"只可编辑待选入的项目信息；对评价过的项目只能编辑附件"执行操作事件 [按规则"只可编辑待选入的项目信息；对评价过的项目只能编辑附件"执行操作]

**Then**
- E-PROJ [BR-04]正面: 只可编辑待选入的项目信息；对评价过的项目只能编辑附件 (behavior) [BR: BR-04]
- E-PROJ [BR-04]负面: 不满足条件时规则不触发 (behavior) [BR: BR-04]

**后置状态**：E-PROJ→(规则验证完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-117 (×5)：项目及机构数据准备就绪时，执行规则验证机构管理员只可查看本机构项目附件
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-005`
**阶段依据**：dep_map_max_phase.E-PROJ.5

**Given**
- E-PROJ 状态 = 规则适用前提满足 ([实例 1] E-PROJ, E-ORG相关数据已准备)

**When**
- E-PROJ 按规则"机构管理员只可查看本机构的项目附件"执行操作事件 [按规则"机构管理员只可查看本机构的项目附件"执行操作]

**Then**
- E-PROJ [BR-05] 机构管理员只可查看本机构的项目附件 (behavior) [BR: BR-05]

**后置状态**：E-PROJ→(规则验证完成)
**弱依赖**：PROC-033.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-118 (×5)：规则适用前提满足时，执行项目级别评判规则，验证规则BR-21
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-021`
**阶段依据**：dep_map_max_phase.E-PROJ.5

**Given**
- E-PROJ 状态 = 规则适用前提满足 ([实例 1] E-PROJ相关数据已准备)

**When**
- E-PROJ 按规则"项目级别评判：优先根据得分匹配可能的最好项目级别，然后判别剩余约束是否全部满足；若全部满足则为相应最好级别，否则降为下一级（只降一级）"执行操作事件 [按规则"项目级别评判：优先根据得分匹配可能的最好项目级别，然后判别剩余约束是否全部满足；若全部满足则为相应最好级别，否则降为下一级（只降一级）"执行操作]

**Then**
- E-PROJ [BR-21] 项目级别评判：优先根据得分匹配可能的最好项目级别，然后判别剩余约束是否全部满足；若全部满足则为相应最好级别，否则降为下一级（只降一级） (behavior) [BR: BR-21]

**后置状态**：E-PROJ→(规则验证完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-119 (×5)：规则适用前提满足时，执行项目联系人电话规则，验证规则BR-57
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-057`
**阶段依据**：dep_map_max_phase.E-PROJ.5

**Given**
- E-PROJ 状态 = 规则适用前提满足 ([实例 1] E-PROJ相关数据已准备)

**When**
- E-PROJ 按规则"项目.联系人电话：必填项；数字组成；手机号验证规则（首位1，次位3-9，共11位）"执行操作事件 [按规则"项目.联系人电话：必填项；数字组成；手机号验证规则（首位1，次位3-9，共11位）"执行操作]

**Then**
- E-PROJ [BR-57] 项目.联系人电话：必填项；数字组成；手机号验证规则（首位1，次位3-9，共11位） (behavior) [BR: BR-57]

**后置状态**：E-PROJ→(规则验证完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-120 (×5)：规则适用前提满足时，执行项目建议书上传规则，验证规则BR-58
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-058`
**阶段依据**：dep_map_max_phase.E-PROJ.5

**Given**
- E-PROJ 状态 = 规则适用前提满足 ([实例 1] E-PROJ相关数据已准备)

**When**
- E-PROJ 按规则"项目.建议书：可上传 doc/docx/ppt/pdf/png/jpg；机构管理员可上传；大小不超过10MB；多次上传覆盖；必填项"执行操作事件 [按规则"项目.建议书：可上传 doc/docx/ppt/pdf/png/jpg；机构管理员可上传；大小不超过10MB；多次上传覆盖；必填项"执行操作]

**Then**
- E-PROJ [BR-58] 项目.建议书：可上传 doc/docx/ppt/pdf/png/jpg；机构管理员可上传；大小不超过10MB；多次上传覆盖；必填项 (behavior) [BR: BR-58]

**后置状态**：E-PROJ→(规则验证完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-121 (×5)：规则适用前提满足时，执行项目申请经费规则，验证规则BR-59
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-059`
**阶段依据**：dep_map_max_phase.E-PROJ.5

**Given**
- E-PROJ 状态 = 规则适用前提满足 ([实例 1] E-PROJ相关数据已准备)

**When**
- E-PROJ 按规则"项目.申请经费（万元）：必填项；整数；范围1-9999"执行操作事件 [按规则"项目.申请经费（万元）：必填项；整数；范围1-9999"执行操作]

**Then**
- E-PROJ [BR-59] 项目.申请经费（万元）：必填项；整数；范围1-9999 (behavior) [BR: BR-59]

**后置状态**：E-PROJ→(规则验证完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-122 (×5)：项目数据准备齐全时，执行项目归档状态转换规则，验证状态转换正确
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-067`
**阶段依据**：dep_map_max_phase.E-PROJ.5

**Given**
- E-PROJ 状态 = 规则适用前提满足 ([实例 1] E-PROJ相关数据已准备)

**When**
- E-PROJ 按规则"项目归档时根据项目阶段和评价结果决定项目状态转换：开题合格及以上变已选入且阶段变验收；开题不合格或差变待选入且阶段不变；验收合格及以上变已归档；验收不合格或差变待选入"执行操作事件 [按规则"项目归档时根据项目阶段和评价结果决定项目状态转换：开题合格及以上变已选入且阶段变验收；开题不合格或差变待选入且阶段不变；验收合格及以上变已归档；验收不合格或差变待选入"执行操作]

**Then**
- E-PROJ [BR-67] 项目归档时根据项目阶段和评价结果决定项目状态转换：开题合格及以上变已选入且阶段变验收；开题不合格或差变待选入且阶段不变；验收合格及以上变已归档；验收不合格或差变待选入 (behavior) [BR: BR-67]

**后置状态**：E-PROJ→(规则验证完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-123 (×2)：技术领域配置为当前值时，变更技术领域配置，验证显示修改后的值
**业务定位**：P5 ｜ happy ｜ 溯源: `EO-ATC-008`
**阶段依据**：parent_primary_phase.E-PLAN.5 (via chain from E-EXPERT)

**Given**
- E-EXPERT 状态 = 技术领域为当前值 ([实例 1] 当前技术领域配置值)

**When**
- E-EXPERT 技术领域配置变更事件 [修改技术领域]

**Then**
- E-EXPERT.技术领域 技术领域显示为修改后的值 (state)

**操作提示**
1. 导航至E-EXPERT配置入口

**后置状态**：E-EXPERT.技术领域→(已修改)
**多实例**：2 × entity=E-EXPERT dim_count=0 instances=2

### PROC-124 (×2)：专家数据准备齐全时，执行回避计划规则，验证回避项目专家正确
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-009`
**阶段依据**：parent_primary_phase.E-PLAN.5 (via chain from E-EXPERT)

**Given**
- E-EXPERT 状态 = 规则适用前提满足 ([实例 1] E-EXPERT, E-PROJ, E-ORG相关数据已准备)

**When**
- E-EXPERT 按规则"默认回避计划中的项目所属机构的专家"执行操作事件 [按规则"默认回避计划中的项目所属机构的专家"执行操作]

**Then**
- E-EXPERT [BR-09] 默认回避计划中的项目所属机构的专家 (behavior) [BR: BR-09]

**后置状态**：E-EXPERT→(规则验证完成)
**弱依赖**：PROC-016.1, PROC-033.1
**多实例**：2 × entity=E-EXPERT dim_count=0 instances=2

### PROC-125 (×2)：专家数据准备齐全时，执行回避项目规则，验证专家不可选入评审组
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-010`
**阶段依据**：parent_primary_phase.E-PLAN.5 (via chain from E-EXPERT)

**Given**
- E-EXPERT 状态 = 规则适用前提满足 ([实例 1] E-EXPERT, E-PLAN相关数据已准备)

**When**
- E-EXPERT 按规则"当人为设置了专家回避项目，评审计划中有该项目时，该专家不可选入评审组"执行操作事件 [按规则"当人为设置了专家回避项目，评审计划中有该项目时，该专家不可选入评审组"执行操作]

**Then**
- E-EXPERT [BR-10]正面: 当人为设置了专家回避项目，评审计划中有该项目时，该专家不可选入评审组 (behavior) [BR: BR-10]
- E-EXPERT [BR-10]负面: 不满足条件时规则不触发 (behavior) [BR: BR-10]

**后置状态**：E-EXPERT→(规则验证完成)
**弱依赖**：PROC-014.1
**多实例**：2 × entity=E-EXPERT dim_count=0 instances=2

### PROC-126 (×2)：专家数据准备齐全时，执行评审时段规则，验证专家工作时段相同且只能被分配一个评审计划
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-011`
**阶段依据**：parent_primary_phase.E-PLAN.5 (via chain from E-EXPERT)

**Given**
- E-EXPERT 状态 = 规则适用前提满足 ([实例 1] E-EXPERT, E-PLAN相关数据已准备)

**When**
- E-EXPERT 按规则"一个计划中评审组专家工作时段相同；专家一个工作时段只能被分配一个评审计划"执行操作事件 [按规则"一个计划中评审组专家工作时段相同；专家一个工作时段只能被分配一个评审计划"执行操作]

**Then**
- E-EXPERT [BR-11] 一个计划中评审组专家工作时段相同；专家一个工作时段只能被分配一个评审计划 (behavior) [BR: BR-11]

**后置状态**：E-EXPERT→(规则验证完成)
**弱依赖**：PROC-014.1
**多实例**：2 × entity=E-EXPERT dim_count=0 instances=2

### PROC-127 (×2)：专家数据准备齐全时，执行晚上分配任务规则，验证专家不能被连续3天晚上分配任务
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-012`
**阶段依据**：parent_primary_phase.E-PLAN.5 (via chain from E-EXPERT)

**Given**
- E-EXPERT 状态 = 规则适用前提满足 ([实例 1] E-EXPERT相关数据已准备)

**When**
- E-EXPERT 按规则"专家不能被连续3天晚上分配任务"执行操作事件 [按规则"专家不能被连续3天晚上分配任务"执行操作]

**Then**
- E-EXPERT [BR-12] 专家不能被连续3天晚上分配任务 (behavior) [BR: BR-12]

**后置状态**：E-EXPERT→(规则验证完成)
**多实例**：2 × entity=E-EXPERT dim_count=0 instances=2

### PROC-128 (×2)：专家数据准备齐全时，执行评审时段可用规则，验证计划结束后专家时段为可用
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-013`
**阶段依据**：parent_primary_phase.E-PLAN.5 (via chain from E-EXPERT)

**Given**
- E-EXPERT 状态 = 规则适用前提满足 ([实例 1] E-EXPERT, E-PLAN相关数据已准备)

**When**
- E-EXPERT 按规则"只要计划结束，评审专家与计划相应的评审时段为可用"执行操作事件 [按规则"只要计划结束，评审专家与计划相应的评审时段为可用"执行操作]

**Then**
- E-EXPERT [BR-13]正面: 只要计划结束，评审专家与计划相应的评审时段为可用 (behavior) [BR: BR-13]
- E-EXPERT [BR-13]负面: 不满足条件时规则不触发 (behavior) [BR: BR-13]

**后置状态**：E-EXPERT→(规则验证完成)
**弱依赖**：PROC-014.1
**多实例**：2 × entity=E-EXPERT dim_count=0 instances=2

### PROC-129 (×2)：专家数据准备齐全时，执行删除专家确认规则，验证删除后专家不足需确认
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-027`
**阶段依据**：parent_primary_phase.E-PLAN.5 (via chain from E-EXPERT)

**Given**
- E-EXPERT 状态 = 规则适用前提满足 ([实例 1] E-EXPERT相关数据已准备)

**When**
- E-EXPERT 按规则"删除专家后若同一技术领域的专家不足5人需进行确认；组长专家不足2人需进行确认"执行操作事件 [按规则"删除专家后若同一技术领域的专家不足5人需进行确认；组长专家不足2人需进行确认"执行操作]

**Then**
- E-EXPERT [BR-27]正面: 删除专家后若同一技术领域的专家不足5人需进行确认；组长专家不足2人需进行确认 (behavior) [BR: BR-27]
- E-EXPERT [BR-27]负面: 不满足条件时规则不触发 (behavior) [BR: BR-27]

**后置状态**：E-EXPERT→(规则验证完成)
**多实例**：2 × entity=E-EXPERT dim_count=0 instances=2

### PROC-130 (×2)：专家数据准备齐全时，执行专家回避项目设置规则，验证规则正面有效且不满足条件时不触发
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-028`
**阶段依据**：parent_primary_phase.E-PLAN.5 (via chain from E-EXPERT)

**Given**
- E-EXPERT 状态 = 规则适用前提满足 ([实例 1] E-EXPERT, E-PROJ, E-PLAN相关数据已准备)

**When**
- E-EXPERT 按规则"在已选入的项目中进行专家回避项目设置，只对回避项目设置后建立的评审计划有效"执行操作事件 [按规则"在已选入的项目中进行专家回避项目设置，只对回避项目设置后建立的评审计划有效"执行操作]

**Then**
- E-EXPERT [BR-28]正面: 在已选入的项目中进行专家回避项目设置，只对回避项目设置后建立的评审计划有效 (behavior) [BR: BR-28]
- E-EXPERT [BR-28]负面: 不满足条件时规则不触发 (behavior) [BR: BR-28]

**后置状态**：E-EXPERT→(规则验证完成)
**弱依赖**：PROC-014.1, PROC-016.1
**多实例**：2 × entity=E-EXPERT dim_count=0 instances=2

### PROC-131 (×2)：专家数据准备齐全时，执行专家手机号验证规则，验证规则包含必填项、数字组成、验证规则和唯一性
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-061`
**阶段依据**：parent_primary_phase.E-PLAN.5 (via chain from E-EXPERT)

**Given**
- E-EXPERT 状态 = 规则适用前提满足 ([实例 1] E-EXPERT相关数据已准备)

**When**
- E-EXPERT 按规则"专家.手机号：必填项；数字组成；手机号验证规则（首位1，次位3-9，共11位）；唯一"执行操作事件 [按规则"专家.手机号：必填项；数字组成；手机号验证规则（首位1，次位3-9，共11位）；唯一"执行操作]

**Then**
- E-EXPERT [BR-61] 专家.手机号：必填项；数字组成；手机号验证规则（首位1，次位3-9，共11位）；唯一 (behavior) [BR: BR-61]

**后置状态**：E-EXPERT→(规则验证完成)
**多实例**：2 × entity=E-EXPERT dim_count=0 instances=2
