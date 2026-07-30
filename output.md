# 测试规程

### PROC-001：技术领域配置变更后，验证技术领域显示为修改后的值
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-007`
**阶段依据**：fallback_default.E-EXP

**Given**
- E-EXP 状态 = 技术领域为当前值 (当前技术领域配置值)

**When**
- E-EXP 技术领域配置变更事件 [修改技术领域]

**Then**
- E-EXP.技术领域 技术领域显示为修改后的值 (state)

**操作提示**
1. 导航至E-EXP配置入口

**后置状态**：E-EXP.技术领域→(已修改)

### PROC-002：评审身份配置变更为组长专家后，验证评审身份效果生效及打分规则
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-008`
**阶段依据**：P6: topology_level L0 → P0

**Given**
- E-EXP 状态 = 评审身份为当前值 (当前评审身份配置值)

**When**
- E-EXP 评审身份配置变更为组长专家事件 [修改评审身份为组长专家]

**Then**
- E-EXP.评审身份 配置评审身份=组长专家的效果已生效 (behavior) [BR: BR-028]
- E-EXP.评审身份 [BR-028] 本次评审项目得分基于各专家对项目的打分进行计算，具体计算方式为：去掉普通专家的一个最高分和一个最低分，计算剩余普通专家打分的平均分，然后按系统内置打分权重表进行计算，计算结果四舍五入，保留两位小数 (behavior) [BR: BR-028] [cross: E-SCORE,E-PROJ]
- E-EXP.评审身份 [BR-030] 打分权重：评审组人数5时组长专家权重40%、普通专家合计权重60%；人数7时25%/75%；人数9时18%/82% (behavior) [BR: BR-030] [cross: E-SCORE]

**操作提示**
1. 导航至E-EXP配置入口

**后置状态**：E-EXP.评审身份→组长专家

### PROC-003：评审身份配置变更为普通专家后，验证评审身份效果生效及打分规则
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-008`
**阶段依据**：P6: topology_level L0 → P0

**Given**
- E-EXP 状态 = 评审身份为当前值 (当前评审身份配置值)

**When**
- E-EXP 评审身份配置变更为普通专家事件 [修改评审身份为普通专家]

**Then**
- E-EXP.评审身份 配置评审身份=普通专家的效果已生效 (behavior) [BR: BR-028]
- E-EXP.评审身份 [BR-028] 本次评审项目得分基于各专家对项目的打分进行计算，具体计算方式为：去掉普通专家的一个最高分和一个最低分，计算剩余普通专家打分的平均分，然后按系统内置打分权重表进行计算，计算结果四舍五入，保留两位小数 (behavior) [BR: BR-028] [cross: E-SCORE,E-PROJ]
- E-EXP.评审身份 [BR-030] 打分权重：评审组人数5时组长专家权重40%、普通专家合计权重60%；人数7时25%/75%；人数9时18%/82% (behavior) [BR: BR-030] [cross: E-SCORE]

**操作提示**
1. 导航至E-EXP配置入口

**后置状态**：E-EXP.评审身份→普通专家

### PROC-004：新增专家时，验证操作覆盖、账号和密码设置及删除规则
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-027`
**阶段依据**：fallback_default.E-EXP

**Given**
- E-EXP 状态 = 存在 (操作入口可用)

**When**
- E-EXP 新增专家 [执行新增专家]

**Then**
- E-EXP 覆盖专家的新增专家操作 (behavior)
- E-EXP 手机号作为账号 (behavior)
- E-EXP 密码默认为手机号后六位 (behavior)
- E-EXP [BR-036] 专家删除：专家有待评审或者评审中的项目时不可以删除；如删除后同一技术领域的专家不足5人时需进行确认；如删除后同一技术领域中组长专家不足2人时需进行确认 (behavior) [BR: BR-036]

**操作提示**
1. 导航至专家页面

**后置状态**：E-EXP→(新增专家完成)

### PROC-005：编辑专家时，验证操作覆盖及不可编辑字段
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-028`
**阶段依据**：fallback_default.E-EXP

**Given**
- E-EXP 状态 = 存在 (操作入口可用)

**When**
- E-EXP 编辑专家 [执行编辑专家]

**Then**
- E-EXP 覆盖专家的编辑专家操作 (behavior)
- E-EXP 不能编辑技术领域、机构、评审身份和手机号 (behavior)

**操作提示**
1. 导航至专家页面

**后置状态**：E-EXP→(编辑专家完成)

### PROC-006：删除专家时，验证操作覆盖、删除规则及提示信息
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-029`
**阶段依据**：fallback_default.E-EXP

**Given**
- E-EXP 状态 = 存在 (操作入口可用)

**When**
- E-EXP 删除专家 [执行删除专家]

**Then**
- E-EXP 覆盖专家的删除专家操作 (behavior)
- E-EXP 专家有待评审或者评审中的项目时不可以删除，并提示 (behavior)
- E-EXP 如删除后同一技术领域的专家不足5人时需进行确认 (behavior)
- E-EXP 如删除后同一技术领域中组长专家不足2人时需进行确认 (behavior)

**操作提示**
1. 导航至专家页面

**后置状态**：E-EXP→(删除专家完成)

### PROC-007：查询专家时，验证操作覆盖及查询条件
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-030`
**阶段依据**：fallback_default.E-EXP

**Given**
- E-EXP 状态 = 存在 (操作入口可用)

**When**
- E-EXP 查询专家 [执行查询专家]

**Then**
- E-EXP 覆盖专家的查询专家操作 (behavior)
- E-EXP 根据姓名、手机号和技术领域进行查询 (behavior)

**操作提示**
1. 导航至专家页面

**后置状态**：E-EXP→(查询专家完成)

### PROC-008：打分项目查看时，验证操作覆盖及查看信息
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-031`
**阶段依据**：fallback_default.E-EXP

**Given**
- E-EXP 状态 = 存在 (操作入口可用)

**When**
- E-EXP 打分项目查看 [执行打分项目查看]

**Then**
- E-EXP 覆盖专家的打分项目查看操作 (behavior)
- E-EXP 查看该专家参评的项目的打分信息与意见 (behavior)

**操作提示**
1. 导航至专家页面

**后置状态**：E-EXP→(打分项目查看完成)

### PROC-009：回避项目设置时，验证操作覆盖及设置规则
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-032`
**阶段依据**：fallback_default.E-EXP

**Given**
- E-EXP 状态 = 存在 (操作入口可用)

**When**
- E-EXP 回避项目设置 [执行回避项目设置]

**Then**
- E-EXP 覆盖专家的回避项目设置操作 (behavior)
- E-EXP 在已选入的项目中进行专家回避项目设置 (behavior)
- E-EXP 只对回避项目设置后建立的评审计划有效 (behavior)

**操作提示**
1. 导航至专家页面

**后置状态**：E-EXP→(回避项目设置完成)

### PROC-010：执行专家回避项目设置规则，验证规则有效性
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-037`
**阶段依据**：fallback_default.E-EXP

**Given**
- E-EXP 状态 = 规则适用前提满足 (E-EXP, E-PROJ, E-PLAN相关数据已准备)

**When**
- E-EXP 按规则"专家回避项目设置只在已选入的项目中进行，且只对回避项目设置后建立的评审计划有效"执行操作事件 [按规则"专家回避项目设置只在已选入的项目中进行，且只对回避项目设置后建立的评审计划有效"执行操作]

**Then**
- E-EXP [BR-037] 专家回避项目设置只在已选入的项目中进行，且只对回避项目设置后建立的评审计划有效 (behavior) [BR: BR-037]

**后置状态**：E-EXP→(规则验证完成)
**弱依赖**：PROC-064.1, PROC-076.1

### PROC-011 (×2)：添加研制机构后，验证机构状态转换为合格及默认状态
**业务定位**：P0 ｜ happy ｜ 溯源: `T-301`
**阶段依据**：dep_state_phase_map.E-ORG.机构状态.合格

**Given**
- E-ORG.机构状态 状态 = (初始) ([实例 1])

**When**
- E-ORG.机构状态 添加研制机构（目标状态：合格） by R-004 [添加研制机构]

**Then**
- E-ORG.机构状态 状态转换为合格 (state)
- E-ORG.机构状态 机构建立后默认为合格状态 (behavior)

**后置状态**：E-ORG.机构状态→合格
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-012 (×2)：试用机构升为合格时，验证操作被拒绝及状态流转
**业务定位**：P0 ｜ happy ｜ 溯源: `T-304`
**阶段依据**：dep_state_phase_map.E-ORG.机构状态.合格

**Given**
- E-ORG.机构状态 状态 = 试用 ([实例 1] 机构处于试用状态; 机构累计10次项目阶段评价结果为优; 当处于试用状态的机构同时可满足升为合格或降为不合格时，降为不合格)

**When**
- E-ORG.机构状态 试用机构升为合格（目标状态：合格） by [待确认角色] [试用机构升为合格]

**Then**
- E-ORG.机构状态 操作被拒绝，试用状态保持不变并给出禁止提示（BR-033） (prompt) [BR: BR-033]
- E-ORG.机构状态 状态流转：试用→合格 (state)
- E-ORG.机构状态 可以升为合格机构 (behavior)

**后置状态**：E-ORG.机构状态→合格
**依赖**：PROC-011.1
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-013 (×2)：添加研制机构时，验证操作覆盖、默认状态及规则
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-044`
**阶段依据**：dep_state_phase_map.E-ORG.min_phase

**Given**
- E-ORG 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-ORG 添加研制机构 [执行添加研制机构]

**Then**
- E-ORG 覆盖机构的添加研制机构操作 (behavior)
- E-ORG 机构建立后默认为合格状态 (behavior)
- E-ORG [BR-033] 对试用机构：机构累计10次项目阶段评价结果为优，可以升为合格机构；机构累计2次项目阶段评价结果为差，将机构降为不合格；机构累计1次差且2次及以上不合格，将机构降为不合格；机构累计4次不合格，将机构降为不合格机构；当处于试用状态的机构同时可满足升为合格或降为不合格时，降为不合格 (behavior) [BR: BR-033]
- E-ORG [BR-038] 机构删除：机构下无项目、无用户、无子机构时，才可删除，根机构不可删除 (behavior) [BR: BR-038]

**操作提示**
1. 导航至机构页面

**后置状态**：E-ORG→(添加研制机构完成)
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-014 (×2)：编辑研制机构时，验证操作覆盖及不可编辑字段
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-045`
**阶段依据**：dep_state_phase_map.E-ORG.min_phase

**Given**
- E-ORG 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-ORG 编辑研制机构 [执行编辑研制机构]

**Then**
- E-ORG 覆盖机构的编辑研制机构操作 (behavior)
- E-ORG 不可编辑上级机构、机构编码、不合格次数和机构状态 (behavior)

**操作提示**
1. 导航至机构页面

**后置状态**：E-ORG→(编辑研制机构完成)
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-015 (×2)：删除研制机构时，验证操作覆盖及删除规则
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-046`
**阶段依据**：dep_state_phase_map.E-ORG.min_phase

**Given**
- E-ORG 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-ORG 删除研制机构 [执行删除研制机构]

**Then**
- E-ORG 覆盖机构的删除研制机构操作 (behavior)
- E-ORG 机构下无项目、无用户、无子机构时，才可删除 (behavior)
- E-ORG 根机构不可删除 (behavior)

**操作提示**
1. 导航至机构页面

**后置状态**：E-ORG→(删除研制机构完成)
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-016：角色存在时，查看角色操作覆盖查看角色及用户信息
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-047`
**阶段依据**：fallback_default.E-ROLE

**Given**
- E-ROLE 状态 = 存在 (操作入口可用)

**When**
- E-ROLE 查看角色 [执行查看角色]

**Then**
- E-ROLE 覆盖角色的查看角色操作 (behavior)
- E-ROLE 查看各角色及其对应的用户信息 (behavior)

**操作提示**
1. 导航至角色页面

**后置状态**：E-ROLE→(查看角色完成)

### PROC-017：角色存在时，关联用户查看操作覆盖查看关联用户
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-048`
**阶段依据**：fallback_default.E-ROLE

**Given**
- E-ROLE 状态 = 存在 (操作入口可用)

**When**
- E-ROLE 关联用户查看 [执行关联用户查看]

**Then**
- E-ROLE 覆盖角色的关联用户查看操作 (behavior)
- E-ROLE 查看相应角色下的关联用户 (behavior)

**操作提示**
1. 导航至角色页面

**后置状态**：E-ROLE→(关联用户查看完成)

### PROC-018：角色存在时，查询角色操作覆盖按名称查询角色
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-049`
**阶段依据**：fallback_default.E-ROLE

**Given**
- E-ROLE 状态 = 存在 (操作入口可用)

**When**
- E-ROLE 查询角色 [执行查询角色]

**Then**
- E-ROLE 覆盖角色的查询角色操作 (behavior)
- E-ROLE 根据角色名称查询 (behavior)

**操作提示**
1. 导航至角色页面

**后置状态**：E-ROLE→(查询角色完成)

### PROC-019：分数限值为当前值时，分数限值配置变更事件修改分数限值显示
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-012`
**阶段依据**：fallback_default.E-THR

**Given**
- E-THR 状态 = 分数限值为当前值 (当前分数限值配置值)

**When**
- E-THR 分数限值配置变更事件 [修改分数限值]

**Then**
- E-THR.分数限值 分数限值显示为修改后的值 (state)

**操作提示**
1. 导航至E-THR配置入口

**后置状态**：E-THR.分数限值→(已修改)

### PROC-020：分数限值存在时，设置分数限值操作使未评价项目立即生效，已汇总项目无影响
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-057`
**阶段依据**：fallback_default.E-THR

**Given**
- E-THR 状态 = 存在 (操作入口可用)

**When**
- E-THR 设置分数限值 [执行设置分数限值]

**Then**
- E-THR 覆盖分数限值的设置分数限值操作 (behavior)
- E-THR 对未产生评价结果的项目立即生效 (behavior)
- E-THR 对已经汇总的项目无影响 (behavior)

**操作提示**
1. 导航至分数限值页面

**后置状态**：E-THR→(设置分数限值完成)

### PROC-021：分数限值存在时，编辑分数限值操作允许评审管理员编辑
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-058`
**阶段依据**：fallback_default.E-THR

**Given**
- E-THR 状态 = 存在 (操作入口可用)

**When**
- E-THR 编辑分数限值 [执行编辑分数限值]

**Then**
- E-THR 覆盖分数限值的编辑分数限值操作 (behavior)
- E-THR 评审管理员可对分数限值进行编辑 (behavior)

**操作提示**
1. 导航至分数限值页面

**后置状态**：E-THR→(编辑分数限值完成)

### PROC-022：分数限值存在时，查看结果汇总操作覆盖查看评价分数大于等于分数限值的项目信息
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-059`
**阶段依据**：fallback_default.E-THR

**Given**
- E-THR 状态 = 存在 (操作入口可用)

**When**
- E-THR 查看结果汇总 [执行查看结果汇总]

**Then**
- E-THR 覆盖分数限值的查看结果汇总操作 (behavior)
- E-THR 查看评价分数大于等于分数限值的项目信息 (behavior)

**操作提示**
1. 导航至分数限值页面

**后置状态**：E-THR→(查看结果汇总完成)

### PROC-023：分数限值规则适用时，执行操作事件确保分数限值符合规则
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-025`
**阶段依据**：fallback_default.E-THR

**Given**
- E-THR 状态 = 规则适用前提满足 (E-THR相关数据已准备)

**When**
- E-THR 按规则"分数限值：0.0&amp;lt;分数限值&amp;lt;=100.0，四舍五入后结果保留一位小数"执行操作事件 [按规则"分数限值：0.0&amp;lt;分数限值&amp;lt;=100.0，四舍五入后结果保留一位小数"执行操作]

**Then**
- E-THR [BR-025] 分数限值：0.0&amp;lt;分数限值&amp;lt;=100.0，四舍五入后结果保留一位小数 (behavior) [BR: BR-025]

**后置状态**：E-THR→(规则验证完成)

### PROC-024：分数限值规则适用时，执行操作事件确保分数限值设置规则生效
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-026`
**阶段依据**：fallback_default.E-THR

**Given**
- E-THR 状态 = 规则适用前提满足 (E-THR, E-PROJ相关数据已准备)

**When**
- E-THR 按规则"分数限值设置后，对未产生评价结果的项目立即生效，对已经汇总的项目无影响"执行操作事件 [按规则"分数限值设置后，对未产生评价结果的项目立即生效，对已经汇总的项目无影响"执行操作]

**Then**
- E-THR [BR-026] 分数限值设置后，对未产生评价结果的项目立即生效，对已经汇总的项目无影响 (behavior) [BR: BR-026]

**后置状态**：E-THR→(规则验证完成)
**弱依赖**：PROC-076.1

### PROC-025：下发时限为当前值时，下发时限配置变更事件修改下发时限显示
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-013`
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

### PROC-026：启动时限为当前值时，启动时限配置变更事件修改启动时限显示
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-014`
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

### PROC-027：归档时限为当前值时，归档时限配置变更事件修改归档时限显示
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-016`
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

### PROC-028：评审时限为当前值时，评审时限配置变更事件修改评审时限显示
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-015`
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

### PROC-029：超时设置存在时，设置超时操作覆盖对评审计划进行超时设置
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-060`
**阶段依据**：fallback_default.E-TIMEOUT

**Given**
- E-TIMEOUT 状态 = 存在 (操作入口可用)

**When**
- E-TIMEOUT 设置超时 [执行设置超时]

**Then**
- E-TIMEOUT 覆盖超时设置的设置超时操作 (behavior)
- E-TIMEOUT 对评审计划的活动进行超时设置 (behavior)

**操作提示**
1. 导航至超时设置页面

**后置状态**：E-TIMEOUT→(设置超时完成)

### PROC-030：超时设置存在时，编辑超时操作覆盖对评审计划进行超时时间编辑并立即生效
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-061`
**阶段依据**：fallback_default.E-TIMEOUT

**Given**
- E-TIMEOUT 状态 = 存在 (操作入口可用)

**When**
- E-TIMEOUT 编辑超时 [执行编辑超时]

**Then**
- E-TIMEOUT 覆盖超时设置的编辑超时操作 (behavior)
- E-TIMEOUT 可对评审计划进行超时时间进行编辑 (behavior)
- E-TIMEOUT 超时设置完成后，对所有计划立即生效 (behavior)

**操作提示**
1. 导航至超时设置页面

**后置状态**：E-TIMEOUT→(编辑超时完成)

### PROC-031：超时设置规则适用时，执行操作事件确保超时设置规则生效
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-022`
**阶段依据**：fallback_default.E-TIMEOUT

**Given**
- E-TIMEOUT 状态 = 规则适用前提满足 (E-TIMEOUT相关数据已准备)

**When**
- E-TIMEOUT 按规则"超时设置完成后，对所有计划立即生效"执行操作事件 [按规则"超时设置完成后，对所有计划立即生效"执行操作]

**Then**
- E-TIMEOUT [BR-022] 超时设置完成后，对所有计划立即生效 (behavior) [BR: BR-022]

**操作提示**
1. scheduler_manual_trigger: 系统调度器在时限到达时自动触发
2. clock_injection: 测试时注入时钟到边界值
3. db_time_update: 直接更新数据库时间到过期后

**后置状态**：E-TIMEOUT→(规则验证完成)

### PROC-032 (×2)：技术领域为当前值时，技术领域配置变更事件修改技术领域显示
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-009`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 技术领域为当前值 ([实例 1] 当前技术领域配置值)

**When**
- E-USER 技术领域配置变更事件 [修改技术领域]

**Then**
- E-USER.技术领域 技术领域显示为修改后的值 (state)

**操作提示**
1. 导航至E-USER配置入口

**后置状态**：E-USER.技术领域→(已修改)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-033 (×2)：用户状态为初始状态时，新增用户操作将用户状态转换为未锁定并成功
**业务定位**：P0 ｜ happy ｜ 溯源: `T-401`
**阶段依据**：dep_state_phase_map.E-USER.用户状态.未锁定

**Given**
- E-USER.用户状态 状态 = (初始) ([实例 1])

**When**
- E-USER.用户状态 新增用户（目标状态：未锁定） by R-004 [新增用户]

**Then**
- E-USER.用户状态 状态转换为未锁定 (state)
- E-USER.用户状态 用户新增成功 (behavior)

**后置状态**：E-USER.用户状态→未锁定
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-034 (×2)：用户处于锁定状态时，管理员解锁用户，验证用户状态变更为未锁定且可以登录系统
**业务定位**：P0 ｜ happy ｜ 溯源: `T-403`
**阶段依据**：dep_state_phase_map.E-USER.用户状态.未锁定

**Given**
- E-USER.用户状态 状态 = 锁定 ([实例 1] 用户处于锁定状态)

**When**
- E-USER.用户状态 解锁用户（目标状态：未锁定） by R-004 [解锁用户]

**Then**
- E-USER.用户状态 状态转换为未锁定 (state)
- E-USER.用户状态 状态流转：锁定→未锁定 (state)
- E-USER.用户状态 解锁后可以登录此系统 (behavior)

**后置状态**：E-USER.用户状态→未锁定
**依赖**：PROC-033.1
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-035 (×2)：用户未锁定时，尝试锁定用户，验证操作被拒绝且状态保持未锁定
**业务定位**：P0 ｜ happy ｜ 溯源: `T-402`
**阶段依据**：dep_state_phase_map.E-USER.用户状态.锁定

**Given**
- E-USER.用户状态 状态 = 未锁定 ([实例 1] 用户处于未锁定状态; 普通用户连续密码错误3次时，锁定该账户)

**When**
- E-USER.用户状态 锁定用户（目标状态：锁定） by R-004 [锁定用户]

**Then**
- E-USER.用户状态 操作被拒绝，未锁定状态保持不变并给出禁止提示（BR-046） (prompt) [BR: BR-046]
- E-USER.用户状态 状态流转：未锁定→锁定 (state)
- E-USER.用户状态 锁定后不得登录此系统 (behavior)

**后置状态**：E-USER.用户状态→锁定
**依赖**：PROC-033.1, PROC-034.1
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-036 (×2)：角色配置变更事件触发后，验证角色显示为修改后的值
**业务定位**：P0 ｜ happy ｜ 溯源: `EO-ATC-010`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 角色为当前值 ([实例 1] 当前角色配置值)

**When**
- E-USER 角色配置变更事件 [修改角色]

**Then**
- E-USER.角色 角色显示为修改后的值 (state)

**操作提示**
1. 导航至E-USER配置入口

**后置状态**：E-USER.角色→(已修改)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-037 (×2)：用户登录时，验证覆盖登录操作，正确登录及错误提示，以及内置角色操作限制
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-033`
**阶段依据**：dep_state_phase_map.E-USER.min_phase

**Given**
- E-USER 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-USER 登录 [执行登录]

**Then**
- E-USER 覆盖用户的登录操作 (behavior)
- E-USER 输入正确的用户账号与相应的密码后可进入本系统 (behavior)
- E-USER 如输入的用户账号或密码错误，则系统给出提示 (behavior)
- E-USER [BR-034] 不可对内置的审计管理员、系统管理员、评审管理员、评审助理进行编辑、锁定、重置密码等操作 (behavior) [BR: BR-034]
- E-USER [BR-044] 用户都应有唯一标识，同一用户同时段不能重复登录 (behavior) [BR: BR-044]
- E-USER [BR-047] 普通用户密码有效期为7天，过期后强制对密码进行更改，不能与上一密码相同 (behavior) [BR: BR-047]
- E-USER [BR-052] 页面提示信息不能含有系统后台、技术框架等信息 (behavior) [BR: BR-052]
- E-USER [BR-060] 本样品内置六个角色，不可对其进行编辑；系统管理员角色、审计管理员角色、评审管理员角色和评审助理角色均绑定到唯一用户 (behavior) [BR: BR-060] [cross: E-ROLE]

**操作提示**
1. 导航至用户页面

**后置状态**：E-USER→(登录完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-038 (×2)：用户注销时，验证覆盖注销操作，确认退出后返回登录界面
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-034`
**阶段依据**：dep_state_phase_map.E-USER.min_phase

**Given**
- E-USER 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-USER 注销 [执行注销]

**Then**
- E-USER 覆盖用户的注销操作 (behavior)
- E-USER 确认退出后，系统将返回登录界面 (behavior)

**操作提示**
1. 导航至用户页面

**后置状态**：E-USER→(注销完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-039 (×2)：用户修改密码时，验证原密码输入，新密码不同且确认，以及密码有效期规则
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-035`
**阶段依据**：dep_state_phase_map.E-USER.min_phase

**Given**
- E-USER 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-USER 修改密码 [执行修改密码]

**Then**
- E-USER 覆盖用户的修改密码操作 (behavior)
- E-USER 需要输入原密码，如果输入的原密码不对，则给出提示 (behavior)
- E-USER 新密码与原密码应不同，否则系统给出提示 (behavior)
- E-USER 新密码需要确认，输入两次，且相同，否则系统给出提示 (behavior)

**操作提示**
1. 导航至用户页面

**后置状态**：E-USER→(修改密码完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-040 (×2)：用户操作菜单收起和展开时，验证支持菜单收起和展开功能
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-036`
**阶段依据**：dep_state_phase_map.E-USER.min_phase

**Given**
- E-USER 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-USER 菜单收起和展开 [执行菜单收起和展开]

**Then**
- E-USER 覆盖用户的菜单收起和展开操作 (behavior)
- E-USER 支持菜单收起和展开功能 (behavior)

**操作提示**
1. 导航至用户页面

**后置状态**：E-USER→(菜单收起和展开完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-041 (×2)：用户新增用户时，验证覆盖新增用户操作，实现用户新增功能
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-037`
**阶段依据**：dep_state_phase_map.E-USER.min_phase

**Given**
- E-USER 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-USER 新增用户 [执行新增用户]

**Then**
- E-USER 覆盖用户的新增用户操作 (behavior)
- E-USER 实现用户新增的功能 (behavior)

**操作提示**
1. 导航至用户页面

**后置状态**：E-USER→(新增用户完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-042 (×2)：用户编辑用户时，验证覆盖编辑用户操作，不可编辑用户关键信息
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-038`
**阶段依据**：dep_state_phase_map.E-USER.min_phase

**Given**
- E-USER 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-USER 编辑用户 [执行编辑用户]

**Then**
- E-USER 覆盖用户的编辑用户操作 (behavior)
- E-USER 不可编辑用户账号、手机号、技术领域、所属机构和角色 (behavior)

**操作提示**
1. 导航至用户页面

**后置状态**：E-USER→(编辑用户完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-043 (×2)：用户锁定用户时，验证覆盖锁定用户操作，锁定后不得登录系统
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-039`
**阶段依据**：dep_state_phase_map.E-USER.min_phase

**Given**
- E-USER 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-USER 锁定用户 [执行锁定用户]

**Then**
- E-USER 覆盖用户的锁定用户操作 (behavior)
- E-USER 锁定后不得登录此系统 (behavior)

**操作提示**
1. 导航至用户页面

**后置状态**：E-USER→(锁定用户完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-044 (×2)：用户存在且操作入口可用时，解锁用户，验证解锁操作覆盖并允许登录
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-040`
**阶段依据**：dep_state_phase_map.E-USER.min_phase

**Given**
- E-USER 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-USER 解锁用户 [执行解锁用户]

**Then**
- E-USER 覆盖用户的解锁用户操作 (behavior)
- E-USER 解锁后可以登录此系统 (behavior)

**操作提示**
1. 导航至用户页面

**后置状态**：E-USER→(解锁用户完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-045 (×2)：用户存在且操作入口可用时，重置密码，验证重置操作覆盖并实现密码重置
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-041`
**阶段依据**：dep_state_phase_map.E-USER.min_phase

**Given**
- E-USER 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-USER 重置密码 [执行重置密码]

**Then**
- E-USER 覆盖用户的重置密码操作 (behavior)
- E-USER 实现用户密码的重置 (behavior)

**操作提示**
1. 导航至用户页面

**后置状态**：E-USER→(重置密码完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-046 (×2)：用户存在且操作入口可用时，删除用户，验证删除操作覆盖且未完成任务的用户不能删除
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-042`
**阶段依据**：dep_state_phase_map.E-USER.min_phase

**Given**
- E-USER 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-USER 删除用户 [执行删除用户]

**Then**
- E-USER 覆盖用户的删除用户操作 (behavior)
- E-USER 如有未完成的任务，不能删除 (behavior)

**操作提示**
1. 导航至用户页面

**后置状态**：E-USER→(删除用户完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-047 (×2)：用户存在且操作入口可用时，查询用户，验证查询操作覆盖并支持组合和模糊查询
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-043`
**阶段依据**：dep_state_phase_map.E-USER.min_phase

**Given**
- E-USER 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-USER 查询用户 [执行查询用户]

**Then**
- E-USER 覆盖用户的查询用户操作 (behavior)
- E-USER 根据用户账号、技术领域、角色、机构和状态进行组合和模糊查询 (behavior)

**操作提示**
1. 导航至用户页面

**后置状态**：E-USER→(查询用户完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-048 (×2)：用户管理操作结果同步到专家管理，验证规则执行后结果同步正确
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-035`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER, E-EXP相关数据已准备)

**When**
- E-USER 按规则"用户管理操作结果同步到专家管理；专家管理操作结果同步到用户管理"执行操作事件 [按规则"用户管理操作结果同步到专家管理；专家管理操作结果同步到用户管理"执行操作]

**Then**
- E-USER [BR-035] 用户管理操作结果同步到专家管理；专家管理操作结果同步到用户管理 (behavior) [BR: BR-035]

**后置状态**：E-USER→(规则验证完成)
**弱依赖**：PROC-001
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-049 (×2)：用户管理操作结果同步到专家管理，验证基于角色的访问控制规则执行正确
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-039`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER, E-ROLE相关数据已准备)

**When**
- E-USER 按规则"实现基于角色的访问控制"执行操作事件 [按规则"实现基于角色的访问控制"执行操作]

**Then**
- E-USER [BR-039] 实现基于角色的访问控制 (behavior) [BR: BR-039]

**后置状态**：E-USER→(规则验证完成)
**弱依赖**：PROC-016
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-050 (×2)：登录时，验证密码不以明文显示的规则执行正确
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-040`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"登录时，密码不以明文显示"执行操作事件 [按规则"登录时，密码不以明文显示"执行操作]

**Then**
- E-USER [BR-040] 登录时，密码不以明文显示 (behavior) [BR: BR-040]

**后置状态**：E-USER→(规则验证完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-051 (×2)：验证身份证的年月日不以明文显示的规则执行正确
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-041`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"身份证的年月日不以明文显示"执行操作事件 [按规则"身份证的年月日不以明文显示"执行操作]

**Then**
- E-USER [BR-041] 身份证的年月日不以明文显示 (behavior) [BR: BR-041]

**后置状态**：E-USER→(规则验证完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-052 (×2)：验证用户初次登录时需更改密码的规则执行正确
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-042`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"用户初次登录时需更改密码"执行操作事件 [按规则"用户初次登录时需更改密码"执行操作]

**Then**
- E-USER [BR-042] 用户初次登录时需更改密码 (behavior) [BR: BR-042]

**后置状态**：E-USER→(规则验证完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-053 (×2)：验证密码设置时长度和复杂度的规则执行正确
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-043`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"密码设置时，长度在8到18位，要包含字母、数字和特殊字符"执行操作事件 [按规则"密码设置时，长度在8到18位，要包含字母、数字和特殊字符"执行操作]

**Then**
- E-USER [BR-043] 密码设置时，长度在8到18位，要包含字母、数字和特殊字符 (behavior) [BR: BR-043]

**后置状态**：E-USER→(规则验证完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-054 (×2)：用户登录系统后，若30分钟内无任何操作，则需重新登录
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-045`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"用户登录系统后，若30分钟内无任何操作，则需要重新登录"执行操作事件 [按规则"用户登录系统后，若30分钟内无任何操作，则需要重新登录"执行操作]

**Then**
- E-USER [BR-045] 用户登录系统后，若30分钟内无任何操作，则需要重新登录 (behavior) [BR: BR-045]

**后置状态**：E-USER→(规则验证完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-055 (×2)：普通用户连续密码错误3次时，锁定账户，可由管理员解锁
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-046`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"普通用户连续密码错误3次时，锁定该账户，锁定后可由系统管理员解锁"执行操作事件 [按规则"普通用户连续密码错误3次时，锁定该账户，锁定后可由系统管理员解锁"执行操作]

**Then**
- E-USER [BR-046] 普通用户连续密码错误3次时，锁定该账户，锁定后可由系统管理员解锁 (behavior) [BR: BR-046]

**后置状态**：E-USER→(规则验证完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-056 (×2)：用户修改密码时，需输入原密码，新密码需不同且确认一致
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-048`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"用户修改自己密码时，需要输入原密码，如果输入的原密码不对，则给出提示；新密码与原密码应不同，否则系统给出提示；新密码需要确认，输入两次，且相同，否则系统给出提示"执行操作事件 [按规则"用户修改自己密码时，需要输入原密码，如果输入的原密码不对，则给出提示；新密码与原密码应不同，否则系统给出提示；新密码需要确认，输入两次，且相同，否则系统给出提示"执行操作]

**Then**
- E-USER [BR-048] 用户修改自己密码时，需要输入原密码，如果输入的原密码不对，则给出提示；新密码与原密码应不同，否则系统给出提示；新密码需要确认，输入两次，且相同，否则系统给出提示 (behavior) [BR: BR-048]

**后置状态**：E-USER→(规则验证完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-057 (×2)：对服务端返回客户端数据及用户信息进行加密传输
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-049`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"对服务端返回客户端的数据进行加密；对客户端提交到服务端的用户相关信息在传输中进行加密"执行操作事件 [按规则"对服务端返回客户端的数据进行加密；对客户端提交到服务端的用户相关信息在传输中进行加密"执行操作]

**Then**
- E-USER [BR-049] 对服务端返回客户端的数据进行加密；对客户端提交到服务端的用户相关信息在传输中进行加密 (behavior) [BR: BR-049]

**后置状态**：E-USER→(规则验证完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-058 (×2)：输入错误用户账号或密码时，系统给出提示
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-053`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"当输入的用户账号或者密码错时，有提示"执行操作事件 [按规则"当输入的用户账号或者密码错时，有提示"执行操作]

**Then**
- E-USER [BR-053] 当输入的用户账号或者密码错时，有提示 (behavior) [BR: BR-053]

**后置状态**：E-USER→(规则验证完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-059 (×2)：日期类数据输入，应提供日历选择功能
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-054`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"日期类数据输入，应提供日历选择功能"执行操作事件 [按规则"日期类数据输入，应提供日历选择功能"执行操作]

**Then**
- E-USER [BR-054] 日期类数据输入，应提供日历选择功能 (behavior) [BR: BR-054]

**后置状态**：E-USER→(规则验证完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-060 (×2)：查询功能支持两个以上字段'与'的组合查询
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-055`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"查询功能中的组合查询支持两个(含)以上字段'与'的查询"执行操作事件 [按规则"查询功能中的组合查询支持两个(含)以上字段'与'的查询"执行操作]

**Then**
- E-USER [BR-055] 查询功能中的组合查询支持两个(含)以上字段'与'的查询 (behavior) [BR: BR-055]

**后置状态**：E-USER→(规则验证完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-061 (×2)：添加、编辑页面必填项需标识并提示未输入项
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-056`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"添加、编辑页面中的必填项应给出*标识，对未输入的必填项给出提示"执行操作事件 [按规则"添加、编辑页面中的必填项应给出*标识，对未输入的必填项给出提示"执行操作]

**Then**
- E-USER [BR-056] 添加、编辑页面中的必填项应给出*标识，对未输入的必填项给出提示 (behavior) [BR: BR-056]

**后置状态**：E-USER→(规则验证完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-062 (×2)：同页面关联数据刷新后保持一致性，不同页面重新打开应同步
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-057`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER相关数据已准备)

**When**
- E-USER 按规则"同页面关联数据刷新后保持一致性，不同页面重新打开关联数据应保持同步"执行操作事件 [按规则"同页面关联数据刷新后保持一致性，不同页面重新打开关联数据应保持同步"执行操作]

**Then**
- E-USER [BR-057] 同页面关联数据刷新后保持一致性，不同页面重新打开关联数据应保持同步 (behavior) [BR: BR-057]

**后置状态**：E-USER→(规则验证完成)
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-063 (×2)：评审管理员、助理和专家登录账号时，应有待办和超时任务说明
**业务定位**：P0 ｜ rule ｜ 溯源: `RO-BR-058`
**阶段依据**：dep_map_max_phase.E-USER.0

**Given**
- E-USER 状态 = 规则适用前提满足 ([实例 1] E-USER, E-PLAN相关数据已准备)

**When**
- E-USER 按规则"评审管理员、评审助理和评审专家登录账号时，应有待办任务和距超时5小时内的任务的说明"执行操作事件 [按规则"评审管理员、评审助理和评审专家登录账号时，应有待办任务和距超时5小时内的任务的说明"执行操作]

**Then**
- E-USER [BR-058] 评审管理员、评审助理和评审专家登录账号时，应有待办任务和距超时5小时内的任务的说明 (behavior) [BR: BR-058]

**操作提示**
1. scheduler_manual_trigger: 系统调度器在时限到达时自动触发
2. clock_injection: 测试时注入时钟到边界值
3. db_time_update: 直接更新数据库时间到过期后

**后置状态**：E-USER→(规则验证完成)
**弱依赖**：PROC-064.1
**多实例**：2 × entity=E-USER dim_count=1 instances=2

### PROC-064 (×2)：评审管理员建立评审计划后，验证计划状态变更为已建立且项目状态变为待评审
**业务定位**：P0 ｜ happy ｜ 溯源: `T-101`
**阶段依据**：phase_table.计划状态.已建立

**Given**
- E-PLAN.计划状态 状态 = (初始) ([实例 1] 评审管理员从处于已选入状态的项目中选取1-5个项目纳入评审计划; 评审计划的评审组由5、7或9个专家组成，有且只能有一个组长专家; 每个评审专家的技术领域应覆盖评审计划中项目的领域)

**When**
- E-PLAN.计划状态 建立评审计划（目标状态：已建立） by R-001 [建立评审计划]

**Then**
- E-PLAN.计划状态 状态转换为已建立 (state)
- E-PLAN.计划状态 保存后评审计划状态为已建立 (behavior)
- E-PLAN.计划状态 处于已建立状态的计划，可以进行编辑 (behavior)
- E-PLAN.计划状态 纳入项目状态由已选入变为待评审 (behavior)
- E-PROJ.项目状态 评审计划建立后项目状态由已选入变为待评审 (behavior)
- E-PROJ.项目阶段 纳入项目状态由已选入变为待评审 (behavior)

**后置状态**：E-PLAN.计划状态→已建立
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-065 (×2)：评审管理员建立评审计划后，验证计划状态变更为已建立并覆盖相关规则
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-016`
**阶段依据**：phase_table.计划状态

**Given**
- E-PLAN 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PLAN 建立评审计划 [执行建立评审计划]

**Then**
- E-PLAN 覆盖评审计划的建立评审计划操作 (behavior)
- E-PLAN 保存后评审计划状态为已建立 (behavior)
- E-PLAN [BR-010] 当人为设置了专家回避项目，评审计划中有该项目时，该专家不可选入评审组 (behavior) [BR: BR-010] [cross: E-EXP]
- E-PLAN [BR-012] 专家不能被连续3天晚上分配任务 (behavior) [BR: BR-012] [cross: E-EXP]
- E-PLAN [BR-015] 下发后的评审计划不能编辑或取消 (behavior) [BR: BR-015]
- E-PLAN [BR-016] 评审管理员和评审助理可删除处于已建立状态和取消结束状态的计划 (behavior) [BR: BR-016]
- E-PLAN [BR-017] 评审助理可在待评审、评审中和已完成状态暂停评审计划和重启评审计划 (behavior) [BR: BR-017]
- E-PLAN [BR-018] 下发时限：从已建立到下发的时间(单位:天)，1-2，默认为1，超过时限计划自动转为待启动状态 (behavior) [BR: BR-018] [cross: E-TIMEOUT]
- E-PLAN [BR-019] 启动时限：从下发到启动的时间(单位:天)，1-5，默认为2，超过时限计划自动转为待评审状态 (behavior) [BR: BR-019] [cross: E-TIMEOUT]
- E-PLAN [BR-020] 评审时限：从待评审到已完成的时间(单位:天)，1-5，默认为2，超过时限计划自动转为已完成状态 (behavior) [BR: BR-020] [cross: E-TIMEOUT]
- E-PLAN [BR-021] 归档时限：从已完成到结束的时限(单位:天)，1-3，默认为2，超过时限计划自动转为超时结束状态 (behavior) [BR: BR-021] [cross: E-TIMEOUT]

**操作提示**
1. 导航至评审计划页面

**后置状态**：E-PLAN→(建立评审计划完成)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-066 (×2)：评审管理员取消评审计划后，验证计划状态变更为取消结束且项目状态恢复
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-017`
**阶段依据**：phase_table.计划状态

**Given**
- E-PLAN 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PLAN 取消评审计划 [执行取消评审计划]

**Then**
- E-PLAN 覆盖评审计划的取消评审计划操作 (behavior)
- E-PLAN 评审计划状态由已建立变为取消结束 (behavior)
- E-PLAN 项目和专家状态返回到该计划建立前的状态 (behavior)

**操作提示**
1. 导航至评审计划页面

**后置状态**：E-PLAN→(取消评审计划完成)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-067 (×2)：评审管理员下发评审计划后，验证计划状态变更为待启动
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-018`
**阶段依据**：phase_table.计划状态

**Given**
- E-PLAN 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PLAN 下发评审计划 [执行下发评审计划]

**Then**
- E-PLAN 覆盖评审计划的下发评审计划操作 (behavior)
- E-PLAN 评审计划状态由已建立变为待启动 (behavior)

**操作提示**
1. 导航至评审计划页面

**后置状态**：E-PLAN→(下发评审计划完成)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-068 (×2)：评审管理员启动评审计划后，验证计划状态变更为待评审
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-019`
**阶段依据**：phase_table.计划状态

**Given**
- E-PLAN 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PLAN 启动评审计划 [执行启动评审计划]

**Then**
- E-PLAN 覆盖评审计划的启动评审计划操作 (behavior)
- E-PLAN 评审计划状态由待启动变为待评审 (behavior)

**操作提示**
1. 导航至评审计划页面

**后置状态**：E-PLAN→(启动评审计划完成)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-069 (×2)：评审管理员暂停评审计划后，验证计划状态变为暂停且专家无法评审
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-020`
**阶段依据**：phase_table.计划状态

**Given**
- E-PLAN 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PLAN 暂停评审计划 [执行暂停评审计划]

**Then**
- E-PLAN 覆盖评审计划的暂停评审计划操作 (behavior)
- E-PLAN 计划状态变为暂停 (behavior)
- E-PLAN 专家不能对计划中的项目进行评审 (behavior)
- E-PLAN 评审助理和评审管理员不能对该计划归档 (behavior)
- E-PLAN 暂停期间计时不停 (behavior)

**操作提示**
1. 导航至评审计划页面

**后置状态**：E-PLAN→(暂停评审计划完成)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-070 (×2)：评审管理员重启评审计划后，验证计划状态返回到暂停前的状态
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-021`
**阶段依据**：phase_table.计划状态

**Given**
- E-PLAN 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PLAN 重启评审计划 [执行重启评审计划]

**Then**
- E-PLAN 覆盖评审计划的重启评审计划操作 (behavior)
- E-PLAN 启动后，状态返回到暂停前的状态 (behavior)

**操作提示**
1. 导航至评审计划页面

**后置状态**：E-PLAN→(重启评审计划完成)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-071 (×2)：评审管理员归档评审计划后，验证计划状态变更为结束并执行归档操作
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-022`
**阶段依据**：phase_table.计划状态

**Given**
- E-PLAN 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PLAN 归档评审计划 [执行归档评审计划]

**Then**
- E-PLAN 覆盖评审计划的归档评审计划操作 (behavior)
- E-PLAN 评审计划状态由已完成为结束 (behavior)
- E-PLAN 对该计划中项目按照4.5(5)归档 (behavior)
- E-PLAN 根据项目阶段评价结果对机构进行评价 (behavior)

**操作提示**
1. 导航至评审计划页面

**后置状态**：E-PLAN→(归档评审计划完成)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-072 (×2)：评审管理员删除评审计划后，验证可删除处于已建立和取消结束状态的计划
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-023`
**阶段依据**：phase_table.计划状态

**Given**
- E-PLAN 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PLAN 删除评审计划 [执行删除评审计划]

**Then**
- E-PLAN 覆盖评审计划的删除评审计划操作 (behavior)
- E-PLAN 可删除处于已建立状态和取消结束状态的计划 (behavior)

**操作提示**
1. 导航至评审计划页面

**后置状态**：E-PLAN→(删除评审计划完成)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-073 (×2)：评审管理员查看评审计划后，验证可查看计划状态、评审组和执行信息
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-024`
**阶段依据**：phase_table.计划状态

**Given**
- E-PLAN 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PLAN 查看评审计划 [执行查看评审计划]

**Then**
- E-PLAN 覆盖评审计划的查看评审计划操作 (behavior)
- E-PLAN 对评审计划的状态、评审组的组成和计划的执行信息等进行查看 (behavior)

**操作提示**
1. 导航至评审计划页面

**后置状态**：E-PLAN→(查看评审计划完成)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-074 (×2)：评审计划查询时，验证覆盖查询操作及条件查询功能
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-025`
**阶段依据**：phase_table.计划状态

**Given**
- E-PLAN 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PLAN 查询评审计划 [执行查询评审计划]

**Then**
- E-PLAN 覆盖评审计划的查询评审计划操作 (behavior)
- E-PLAN 根据专家姓名、项目名称、技术领域和评审时段查询符合条件的计划 (behavior)

**操作提示**
1. 导航至评审计划页面

**后置状态**：E-PLAN→(查询评审计划完成)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-075 (×2)：评审计划组建评审组时，验证覆盖组建操作及匹配专家功能
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-026`
**阶段依据**：phase_table.计划状态

**Given**
- E-PLAN 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PLAN 组建评审组 [执行组建评审组]

**Then**
- E-PLAN 覆盖评审计划的组建评审组操作 (behavior)
- E-PLAN 根据项目领域和回避规则显示匹配的评审专家 (behavior)

**操作提示**
1. 导航至评审计划页面

**后置状态**：E-PLAN→(组建评审组完成)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-076 (×5)：新增项目时，验证项目状态转换为待选入及初始化项目阶段
**业务定位**：P0 ｜ happy ｜ 溯源: `T-001`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.待选入

**Given**
- E-PROJ.项目状态 状态 = (初始) ([实例 1])

**When**
- E-PROJ.项目状态 新增项目（目标状态：待选入） by R-005 [新增项目]

**Then**
- E-PROJ.项目状态 状态转换为待选入 (state)
- E-PROJ.项目状态 项目状态初始化为待选入 (behavior)
- E-PROJ.项目状态 项目阶段初始化为开题 (behavior)

**后置状态**：E-PROJ.项目状态→待选入
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-077 (×5)：新增项目时，验证项目操作覆盖、状态初始化及业务规则
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-001`
**阶段依据**：dep_state_phase_map.E-PROJ.min_phase

**Given**
- E-PROJ 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PROJ 新增项目 [执行新增项目]

**Then**
- E-PROJ 覆盖项目的新增项目操作 (behavior)
- E-PROJ 项目状态初始化为待选入，处于开题阶段 (behavior)
- E-PROJ [BR-003] 对于本阶段不合格评价结果的项目，只有1次选入机会 (behavior) [BR: BR-003]
- E-PROJ [BR-004] 对于本阶段评价结果为差的项目，不可选入 (behavior) [BR: BR-004]
- E-PROJ [BR-005] 评审管理员只能对已选入状态的项目进行选出 (behavior) [BR: BR-005]
- E-PROJ [BR-013] 评审管理员从处于已选入状态的项目中选取1-5个项目纳入评审计划 (behavior) [BR: BR-013] [cross: E-PLAN]
- E-PROJ [BR-032] 对不合格机构：不能对不合格研制机构所属项目进行评审；已下发的评审计划中的项目不受影响；对未下发计划的项目从计划中去掉，如果某个未下发评审计划中的项目均属于不合格的研制机构，则取消该计划；系统管理员可以对不合格机构提为试用机构，研制机构累计3次评级为不合格，则不能提为试用机构 (behavior) [BR: BR-032] [cross: E-ORG,E-PLAN]

**操作提示**
1. 导航至项目页面

**后置状态**：E-PROJ→(新增项目完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-078 (×5)：删除项目时，验证只能删除待选入且未评价过的项目
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-002`
**阶段依据**：dep_state_phase_map.E-PROJ.min_phase

**Given**
- E-PROJ 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PROJ 删除项目 [执行删除项目]

**Then**
- E-PROJ 覆盖项目的删除项目操作 (behavior)
- E-PROJ 只能删除待选入且未评价过的项目 (behavior)

**操作提示**
1. 导航至项目页面

**后置状态**：E-PROJ→(删除项目完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-079 (×5)：编辑项目时，验证操作覆盖及编辑规则
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-003`
**阶段依据**：dep_state_phase_map.E-PROJ.min_phase

**Given**
- E-PROJ 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PROJ 编辑项目 [执行编辑项目]

**Then**
- E-PROJ 覆盖项目的编辑项目操作 (behavior)
- E-PROJ 只可编辑待选入的项目信息，对评价过的项目编辑附件 (behavior)

**操作提示**
1. 导航至项目页面

**后置状态**：E-PROJ→(编辑项目完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-080 (×5)：项目存在且操作入口可用时，查看项目覆盖操作，可查看项目详细信息
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-004`
**阶段依据**：dep_state_phase_map.E-PROJ.min_phase

**Given**
- E-PROJ 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PROJ 查看项目 [执行查看项目]

**Then**
- E-PROJ 覆盖项目的查看项目操作 (behavior)
- E-PROJ 可查看项目的详细信息 (behavior)

**操作提示**
1. 导航至项目页面

**后置状态**：E-PROJ→(查看项目完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-081 (×5)：项目存在且操作入口可用时，查询项目覆盖操作，依据项目名称和技术领域条件查询
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-005`
**阶段依据**：dep_state_phase_map.E-PROJ.min_phase

**Given**
- E-PROJ 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PROJ 查询项目 [执行查询项目]

**Then**
- E-PROJ 覆盖项目的查询项目操作 (behavior)
- E-PROJ 依据项目名称和技术领域条件进行查询 (behavior)

**操作提示**
1. 导航至项目页面

**后置状态**：E-PROJ→(查询项目完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-082 (×5)：项目存在且操作入口可用时，查看项目附件覆盖操作，评审管理员和助理可查看所有附件，机构管理员只可查看本机构附件
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-006`
**阶段依据**：dep_state_phase_map.E-PROJ.min_phase

**Given**
- E-PROJ 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PROJ 查看项目附件 [执行查看项目附件]

**Then**
- E-PROJ 覆盖项目的查看项目附件操作 (behavior)
- E-PROJ 评审管理员和评审助理查看项目附件，机构管理员只可查看本机构的项目附件 (behavior)

**操作提示**
1. 导航至项目页面

**后置状态**：E-PROJ→(查看项目附件完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-083 (×5)：项目存在且操作入口可用时，项目选入覆盖操作，选入后项目状态变为已选入
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-007`
**阶段依据**：dep_state_phase_map.E-PROJ.min_phase

**Given**
- E-PROJ 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PROJ 项目选入 [执行项目选入]

**Then**
- E-PROJ 覆盖项目的项目选入操作 (behavior)
- E-PROJ 选入后项目状态变为已选入 (behavior)

**操作提示**
1. 导航至项目页面

**后置状态**：E-PROJ→(项目选入完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-084 (×5)：项目选出时，覆盖项目选出操作，状态由已选入变为待选入
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-008`
**阶段依据**：dep_state_phase_map.E-PROJ.min_phase

**Given**
- E-PROJ 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PROJ 项目选出 [执行项目选出]

**Then**
- E-PROJ 覆盖项目的项目选出操作 (behavior)
- E-PROJ 项目状态由已选入变为待选入 (behavior)

**操作提示**
1. 导航至项目页面

**后置状态**：E-PROJ→(项目选出完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-085 (×5)：项目排序时，覆盖项目排序操作，按列升序或降序显示
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-009`
**阶段依据**：dep_state_phase_map.E-PROJ.min_phase

**Given**
- E-PROJ 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PROJ 排序 [执行排序]

**Then**
- E-PROJ 覆盖项目的排序操作 (behavior)
- E-PROJ 按照相应列的升序或者降序来显示列表数据 (behavior)

**操作提示**
1. 导航至项目页面

**后置状态**：E-PROJ→(排序完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-086 (×5)：项目分页时，覆盖项目分页操作，支持设置展示条数及翻页
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-010`
**阶段依据**：dep_state_phase_map.E-PROJ.min_phase

**Given**
- E-PROJ 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PROJ 分页工具条 [执行分页工具条]

**Then**
- E-PROJ 覆盖项目的分页工具条操作 (behavior)
- E-PROJ 支持设置页面展示条数，可以进行上一页、下一页操作，显示当前页及总页数 (behavior)

**操作提示**
1. 导航至项目页面

**后置状态**：E-PROJ→(分页工具条完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-087 (×5)：项目重置时，覆盖项目重置操作，清除查询条件并刷新页面
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-011`
**阶段依据**：dep_state_phase_map.E-PROJ.min_phase

**Given**
- E-PROJ 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PROJ 重置 [执行重置]

**Then**
- E-PROJ 覆盖项目的重置操作 (behavior)
- E-PROJ 清除输入的查询条件，刷新页面 (behavior)

**操作提示**
1. 导航至项目页面

**后置状态**：E-PROJ→(重置完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-088 (×5)：项目存在且操作入口可用时，取消/关闭项目，验证取消/关闭操作覆盖项目并放弃操作
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-012`
**阶段依据**：dep_state_phase_map.E-PROJ.min_phase

**Given**
- E-PROJ 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PROJ 取消/关闭 [执行取消/关闭]

**Then**
- E-PROJ 覆盖项目的取消/关闭操作 (behavior)
- E-PROJ 放弃本次新增、编辑操作或关闭弹窗 (behavior)

**操作提示**
1. 导航至项目页面

**后置状态**：E-PROJ→(取消/关闭完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-089 (×5)：项目存在且操作入口可用时，上传附件，验证上传操作覆盖项目并将附件上传到数据库
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-013`
**阶段依据**：dep_state_phase_map.E-PROJ.min_phase

**Given**
- E-PROJ 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PROJ 上传附件 [执行上传附件]

**Then**
- E-PROJ 覆盖项目的上传附件操作 (behavior)
- E-PROJ 将选中的附件从本地上传到数据库 (behavior)

**操作提示**
1. 导航至项目页面

**后置状态**：E-PROJ→(上传附件完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-090 (×5)：项目存在且操作入口可用时，下载附件，验证下载操作覆盖项目并将附件下载到本地
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-014`
**阶段依据**：dep_state_phase_map.E-PROJ.min_phase

**Given**
- E-PROJ 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PROJ 下载附件 [执行下载附件]

**Then**
- E-PROJ 覆盖项目的下载附件操作 (behavior)
- E-PROJ 将选中的附件从数据库下载到本地 (behavior)

**操作提示**
1. 导航至项目页面

**后置状态**：E-PROJ→(下载附件完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-091 (×5)：项目存在且操作入口可用时，保存项目，验证保存操作覆盖项目并更新数据库数据
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-015`
**阶段依据**：dep_state_phase_map.E-PROJ.min_phase

**Given**
- E-PROJ 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-PROJ 保存 [执行保存]

**Then**
- E-PROJ 覆盖项目的保存操作 (behavior)
- E-PROJ 实现对数据库中的数据更新 (behavior)

**操作提示**
1. 导航至项目页面

**后置状态**：E-PROJ→(保存完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-092 (×5)：项目处于待选入状态时，尝试待选入转换事件，操作被拒绝且状态不变
**业务定位**：P0 ｜ invalid ｜ 溯源: `RO-IT-001`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.待选入

**Given**
- E-PROJ 状态 = 待选入 ([实例 1] E-PROJ处于"待选入"状态)

**When**
- E-PROJ 尝试待选入→已选入转换事件 [尝试执行从"待选入"到"已选入"的操作]

**Then**
- E-PROJ 操作被拒绝，对于本阶段评价结果为差的项目，不可选入 (prompt)
- E-PROJ 状态仍为待选入 (state)

**后置状态**：E-PROJ→(操作被阻止)
**依赖**：PROC-076.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-093 (×4)：评审计划启动后，分配打分任务，打分状态转换为未打分并初始化
**业务定位**：P0 ｜ happy ｜ 溯源: `T-201`
**阶段依据**：dep_state_phase_map.E-SCORE.打分状态.未打分

**Given**
- E-SCORE.打分状态 状态 = (初始) ([实例 1])
- E-SCORE.打分状态 状态 = (初始) (评审计划启动)

**When**
- E-SCORE.打分状态 分配打分任务（目标状态：未打分） by [待确认角色] [分配打分任务]

**Then**
- E-SCORE.打分状态 状态转换为未打分 (state)
- E-SCORE.打分状态 打分状态初始化为未打分 (behavior)

**后置状态**：E-SCORE.打分状态→未打分
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-094 (×4)：专家打分时，覆盖打分操作，显示评分细则，限制分数修改
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-052`
**阶段依据**：dep_state_phase_map.E-SCORE.min_phase

**Given**
- E-SCORE 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-SCORE 打分 [执行打分]

**Then**
- E-SCORE 覆盖专家打分的打分操作 (behavior)
- E-SCORE 专家依据打分规则对项目进行评审打分 (behavior)
- E-SCORE 显示内置的评分细则为专家打分提供参考 (behavior)
- E-SCORE [BR-024] 已提交的项目不能进行分数修改，项目各项打分全部为零的不能提交，并提示 (behavior) [BR: BR-024]

**操作提示**
1. 导航至专家打分页面

**后置状态**：E-SCORE→(打分完成)
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-095 (×4)：专家保存打分时，覆盖保存操作，打分状态变为已保存
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-053`
**阶段依据**：dep_state_phase_map.E-SCORE.min_phase

**Given**
- E-SCORE 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-SCORE 保存打分 [执行保存打分]

**Then**
- E-SCORE 覆盖专家打分的保存打分操作 (behavior)
- E-SCORE 打分状态变为已保存 (behavior)

**操作提示**
1. 导航至专家打分页面

**后置状态**：E-SCORE→(保存打分完成)
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-096 (×4)：专家打分页面提交打分时，覆盖专家打分并更新打分状态为已提交，禁止修改分数，且打分项为零时提示
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-054`
**阶段依据**：dep_state_phase_map.E-SCORE.min_phase

**Given**
- E-SCORE 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-SCORE 提交打分 [执行提交打分]

**Then**
- E-SCORE 覆盖专家打分的提交打分操作 (behavior)
- E-SCORE 打分状态变为已提交 (behavior)
- E-SCORE 已提交的项目不能进行分数修改 (behavior)
- E-SCORE 项目各项打分全部为零的不能提交，并提示 (behavior)

**操作提示**
1. 导航至专家打分页面

**后置状态**：E-SCORE→(提交打分完成)
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-097 (×4)：专家打分页面查看打分进度时，覆盖专家打分并显示已提交专家人数占比
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-055`
**阶段依据**：dep_state_phase_map.E-SCORE.min_phase

**Given**
- E-SCORE 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-SCORE 查看打分进度 [执行查看打分进度]

**Then**
- E-SCORE 覆盖专家打分的查看打分进度操作 (behavior)
- E-SCORE 打分已提交专家人数占评审专家总人数的比例 (behavior)

**操作提示**
1. 导航至专家打分页面

**后置状态**：E-SCORE→(查看打分进度完成)
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-098 (×4)：专家打分页面查看打分情况时，覆盖专家打分并展示各专家打分记录及项目得分统计
**业务定位**：P0 ｜ crud ｜ 溯源: `EO-CRU-056`
**阶段依据**：dep_state_phase_map.E-SCORE.min_phase

**Given**
- E-SCORE 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-SCORE 查看打分情况 [执行查看打分情况]

**Then**
- E-SCORE 覆盖专家打分的查看打分情况操作 (behavior)
- E-SCORE 展示评审组各专家对具体项目各打分项的打分记录及该项目的得分统计及评价结果 (behavior)

**操作提示**
1. 导航至专家打分页面

**后置状态**：E-SCORE→(查看打分情况完成)
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-099 (×2)：评审计划已建立状态下，下发评审计划后状态变为待启动，且下发后不可编辑或取消
**业务定位**：P1 ｜ happy ｜ 溯源: `T-103`
**阶段依据**：phase_table.计划状态.待启动

**Given**
- E-PLAN.计划状态 状态 = 已建立 ([实例 1] 评审计划处于已建立状态)

**When**
- E-PLAN.计划状态 下发评审计划（目标状态：待启动） by R-001 [下发评审计划]

**Then**
- E-PLAN.计划状态 状态转换为待启动 (state)
- E-PLAN.计划状态 状态流转：已建立→待启动 (state)
- E-PLAN.计划状态 评审计划状态由已建立变为待启动 (behavior)
- E-PLAN.计划状态 下发后的评审计划不能编辑或取消 (behavior)

**后置状态**：E-PLAN.计划状态→待启动
**依赖**：PROC-064.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-100 (×2)：评审计划已建立且超过下发时限时，系统下发超时后状态变为待启动
**业务定位**：P1 ｜ happy ｜ 溯源: `T-104`
**阶段依据**：phase_table.计划状态.待启动

**Given**
- E-PLAN.计划状态 状态 = 已建立 ([实例 1] 评审计划处于已建立状态; 超过下发时限)

**When**
- E-PLAN.计划状态 下发超时（目标状态：待启动） by 系统 [下发超时]

**Then**
- E-PLAN.计划状态 状态转换为待启动 (state)
- E-PLAN.计划状态 状态流转：已建立→待启动 (state)
- E-PLAN.计划状态 评审计划状态由已建立变为待启动 (behavior)

**操作提示**
1. scheduler_manual_trigger: 系统调度器在时限到达时自动触发
2. clock_injection: 测试时注入时钟到边界值
3. db_time_update: 直接更新数据库时间到过期后

**后置状态**：E-PLAN.计划状态→待启动
**依赖**：PROC-064.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-101 (×2)：评审计划接近截止时间时，系统下发超时后状态变为待启动（时间边界生效）
**业务定位**：P1 ｜ time_sensitive ｜ 溯源: `T-104`
**阶段依据**：phase_table.计划状态.待启动 (time_boundary)

**Given**
- E-PLAN.计划状态 状态 = 已建立 ([实例 1] 时间边界条件: 接近截止时间)

**When**
- E-PLAN.计划状态 下发超时(时间边界)（目标状态：待启动） by 系统 [下发超时(边界)]

**Then**
- E-PLAN.计划状态 状态转换为待启动(时间边界生效) (state)

**操作提示**
1. clock_injection: 测试时注入时钟到边界值
2. db_time_update: 直接更新数据库时间到过期后
3. scheduler_manual_trigger: 系统调度器在时限到达时自动触发

**后置状态**：E-PLAN.计划状态→待启动(时间边界)
**依赖**：PROC-064.1, PROC-100.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-102 (×2)：评审计划超过截止时间时，尝试下发超时事件操作不可执行或状态不变
**业务定位**：P1 ｜ time_sensitive ｜ 溯源: `T-104`
**阶段依据**：phase_table.计划状态.待启动 (time_expired)

**Given**
- E-PLAN.计划状态 状态 = 已建立 ([实例 1] 时间过期条件: 超过截止时间)

**When**
- E-PLAN.计划状态 尝试下发超时事件(已过期) by 系统 [尝试下发超时(已过期)]

**Then**
- E-PLAN.计划状态 操作不可执行或状态不变 (behavior)

**操作提示**
1. db_time_update: 直接更新数据库时间到过期后
2. clock_injection: 测试时注入时钟到边界值
3. scheduler_manual_trigger: 系统调度器在时限到达时自动触发

**后置状态**：E-PLAN.计划状态→(过期未执行)
**依赖**：PROC-064.1, PROC-100.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-103 (×5)：项目处于开题阶段且评级合格及以上，评审计划状态结束或超时，验证项目阶段变更为验收
**业务定位**：P1 ｜ branch ｜ 溯源: `T-008`
**阶段依据**：dep_state_phase_map.E-PROJ.项目阶段.验收

**Given**
- E-PROJ.项目阶段 状态 = 开题 ([实例 1] 项目处于开题阶段; 在开题阶段，项目的评级在合格及以上)
- E-PROJ.项目阶段 状态 = 开题 (评审计划状态由已完成变为结束或超时结束)

**When**
- E-PROJ.项目阶段 开题合格及以上项目阶段变为验收（目标状态：验收） by 系统 [开题合格及以上项目阶段变为验收]

**Then**
- E-PROJ.项目阶段 状态转换为验收 (state)
- E-PROJ.项目阶段 状态流转：开题→验收 (state)
- E-PROJ.项目阶段 项目阶段由开题变为验收 (behavior)

**后置状态**：E-PROJ.项目阶段→验收
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-104 (×4)：评审专家对未打分的项目进行打分并保存，验证打分状态变更为已保存且评审计划状态变为评审中
**业务定位**：P1 ｜ happy ｜ 溯源: `T-202`
**阶段依据**：dep_state_phase_map.E-SCORE.打分状态.已保存

**Given**
- E-SCORE.打分状态 状态 = 未打分 ([实例 1] 依据打分规则对项目进行评审打分)
- E-SCORE.打分状态 状态 = 未打分 (评审专家对分配给其的项目进行打分)

**When**
- E-SCORE.打分状态 打分保存（目标状态：已保存） by R-003 [打分保存]

**Then**
- E-SCORE.打分状态 状态转换为已保存 (state)
- E-SCORE.打分状态 状态流转：未打分→已保存 (state)
- E-SCORE.打分状态 打分状态变为已保存 (behavior)
- E-PLAN.计划状态 评审专家打分保存后评审计划状态由待评审变为评审中 (behavior)

**后置状态**：E-SCORE.打分状态→已保存
**依赖**：PROC-093.1
**弱依赖**：PROC-105.1, PROC-106.1, PROC-109.1, PROC-114.1, PROC-115.1
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-105 (×2)：评审计划处于待启动状态时，启动评审计划，验证项目状态由待评审变为评审中
**业务定位**：P2 ｜ happy ｜ 溯源: `T-105`
**阶段依据**：phase_table.计划状态.待评审

**Given**
- E-PLAN.计划状态 状态 = 待启动 ([实例 1] 评审计划处于待启动状态)

**When**
- E-PLAN.计划状态 启动评审计划（目标状态：待评审） by R-002 [启动评审计划]

**Then**
- E-PLAN.计划状态 状态转换为待评审 (state)
- E-PLAN.计划状态 状态流转：待启动→待评审 (state)
- E-PLAN.计划状态 评审计划状态由待启动变为待评审 (behavior)
- E-PLAN.计划状态 项目状态由待评审变为评审中 (behavior)
- E-PROJ.项目状态 评审计划启动后项目状态由待评审变为评审中 (behavior)
- E-PROJ.项目阶段 项目状态由待评审变为评审中 (behavior)

**后置状态**：E-PLAN.计划状态→待评审
**依赖**：PROC-064.1, PROC-099.1
**弱依赖**：PROC-154.1, PROC-156.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-106 (×2)：评审计划处于待启动状态且超过启动时限，系统启动超时，验证项目状态由待评审变为评审中
**业务定位**：P2 ｜ happy ｜ 溯源: `T-106`
**阶段依据**：phase_table.计划状态.待评审

**Given**
- E-PLAN.计划状态 状态 = 待启动 ([实例 1] 评审计划处于待启动状态; 超过启动时限)

**When**
- E-PLAN.计划状态 启动超时（目标状态：待评审） by 系统 [启动超时]

**Then**
- E-PLAN.计划状态 状态转换为待评审 (state)
- E-PLAN.计划状态 状态流转：待启动→待评审 (state)
- E-PLAN.计划状态 评审计划状态由待启动变为待评审 (behavior)
- E-PLAN.计划状态 项目状态由待评审变为评审中 (behavior)
- E-PROJ.项目状态 评审计划启动后项目状态由待评审变为评审中 (behavior)
- E-PROJ.项目阶段 项目状态由待评审变为评审中 (behavior)

**操作提示**
1. scheduler_manual_trigger: 系统调度器在时限到达时自动触发
2. clock_injection: 测试时注入时钟到边界值
3. db_time_update: 直接更新数据库时间到过期后

**后置状态**：E-PLAN.计划状态→待评审
**依赖**：PROC-064.1, PROC-099.1
**弱依赖**：PROC-154.1, PROC-156.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-107 (×2)：评审计划接近截止时间时，系统启动超时，验证状态转换为待评审
**业务定位**：P2 ｜ time_sensitive ｜ 溯源: `T-106`
**阶段依据**：phase_table.计划状态.待评审 (time_boundary)

**Given**
- E-PLAN.计划状态 状态 = 待启动 ([实例 1] 时间边界条件: 接近截止时间)

**When**
- E-PLAN.计划状态 启动超时(时间边界)（目标状态：待评审） by 系统 [启动超时(边界)]

**Then**
- E-PLAN.计划状态 状态转换为待评审(时间边界生效) (state)

**操作提示**
1. clock_injection: 测试时注入时钟到边界值
2. db_time_update: 直接更新数据库时间到过期后
3. scheduler_manual_trigger: 系统调度器在时限到达时自动触发

**后置状态**：E-PLAN.计划状态→待评审(时间边界)
**依赖**：PROC-064.1, PROC-099.1, PROC-106.1
**弱依赖**：PROC-154.1, PROC-156.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-108 (×2)：计划状态超过截止时间时，系统尝试启动超时事件，验证操作不可执行或状态不变
**业务定位**：P2 ｜ time_sensitive ｜ 溯源: `T-106`
**阶段依据**：phase_table.计划状态.待评审 (time_expired)

**Given**
- E-PLAN.计划状态 状态 = 待启动 ([实例 1] 时间过期条件: 超过截止时间)

**When**
- E-PLAN.计划状态 尝试启动超时事件(已过期) by 系统 [尝试启动超时(已过期)]

**Then**
- E-PLAN.计划状态 操作不可执行或状态不变 (behavior)

**操作提示**
1. db_time_update: 直接更新数据库时间到过期后
2. clock_injection: 测试时注入时钟到边界值
3. scheduler_manual_trigger: 系统调度器在时限到达时自动触发

**后置状态**：E-PLAN.计划状态→(过期未执行)
**依赖**：PROC-064.1, PROC-099.1, PROC-106.1
**弱依赖**：PROC-154.1, PROC-156.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-109 (×2)：评审计划处于暂停状态，重启后返回待评审，验证状态返回到暂停前的状态
**业务定位**：P2 ｜ happy ｜ 溯源: `T-111a`
**阶段依据**：phase_table.计划状态.待评审

**Given**
- E-PLAN.计划状态 状态 = 暂停 ([实例 1] 评审计划处于暂停状态; 暂停前状态为待评审)

**When**
- E-PLAN.计划状态 重启-返回待评审（目标状态：待评审） by R-002 [重启-返回待评审]

**Then**
- E-PLAN.计划状态 状态转换为待评审 (state)
- E-PLAN.计划状态 状态流转：暂停→待评审 (state)
- E-PLAN.计划状态 启动后，状态返回到暂停前的状态(待评审) (behavior)

**后置状态**：E-PLAN.计划状态→待评审
**依赖**：PROC-064.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-110 (×4)：打分已保存时，提交打分操作被拒绝，状态保持为已保存
**业务定位**：P2 ｜ negative ｜ 溯源: `T-203`
**阶段依据**：dep_state_phase_map.E-SCORE.打分状态.已提交

**Given**
- E-SCORE.打分状态 状态 = 已保存 ([实例 1] 打分状态为已保存; 项目各项打分全部为零的不能提交)

**When**
- E-SCORE.打分状态 提交打分（目标状态：已提交） by R-003 [提交打分]

**Then**
- E-SCORE.打分状态 操作被拒绝，状态保持为已保存并给出禁止提示 (state)
- E-PROJ.项目状态 评审组全部专家提交打分后项目状态由评审中变为待归档 (behavior)

**后置状态**：E-SCORE.打分状态→已保存
**依赖**：PROC-093.1, PROC-104.1
**弱依赖**：PROC-156.1, PROC-157.1, PROC-158.1
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-111 (×4)：打分已保存时，提交打分后状态转换为已提交
**业务定位**：P2 ｜ audit ｜ 溯源: `T-203`
**阶段依据**：dep_state_phase_map.E-SCORE.打分状态.已提交

**Given**
- E-SCORE.打分状态 状态 = 已保存 ([实例 1] 打分状态为已保存)

**When**
- E-SCORE.打分状态 提交打分（目标状态：已提交） by R-003 [提交打分]

**Then**
- E-SCORE.打分状态 状态转换为已提交 (state)
- E-SCORE.打分状态 状态流转：已保存→已提交 (state)

**后置状态**：E-SCORE.打分状态→已提交
**依赖**：PROC-093.1, PROC-104.1, PROC-110.1
**弱依赖**：PROC-156.1, PROC-157.1, PROC-158.1
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-112 (×4)：执行打分规则后，显示开题评审和验收评审打分项
**业务定位**：P2 ｜ rule ｜ 溯源: `RO-BR-023`
**阶段依据**：dep_map_max_phase.E-SCORE.2

**Given**
- E-SCORE 状态 = 规则适用前提满足 ([实例 1] E-SCORE相关数据已准备)

**When**
- E-SCORE 按规则"开题评审打分项:创新性、研究目标及技术指标、研究基础和保障条件、应用前景、成果及考核方式、研究方案及技术途径；验收评审打分项：创新性、技术指标达标情况、成果及其完成情况、应用前景、研制过程、关键技术"执行操作事件 [按规则"开题评审打分项:创新性、研究目标及技术指标、研究基础和保障条件、应用前景、成果及考核方式、研究方案及技术途径；验收评审打分项：创新性、技术指标达标情况、成果及其完成情况、应用前景、研制过程、关键技术"执行操作]

**Then**
- E-SCORE [BR-023] 开题评审打分项:创新性、研究目标及技术指标、研究基础和保障条件、应用前景、成果及考核方式、研究方案及技术途径；验收评审打分项：创新性、技术指标达标情况、成果及其完成情况、应用前景、研制过程、关键技术 (behavior) [BR: BR-023]

**后置状态**：E-SCORE→(规则验证完成)
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-113 (×4)：执行打分平均分规则后，单个打分项分数为所有专家相应项打分的平均分
**业务定位**：P2 ｜ rule ｜ 溯源: `RO-BR-027`
**阶段依据**：dep_map_max_phase.E-SCORE.2

**Given**
- E-SCORE 状态 = 规则适用前提满足 ([实例 1] E-SCORE, E-PROJ相关数据已准备)

**When**
- E-SCORE 按规则"所有专家打分提交后，本次评审项目的单个打分项分数为所有专家相应项打分的平均分"执行操作事件 [按规则"所有专家打分提交后，本次评审项目的单个打分项分数为所有专家相应项打分的平均分"执行操作]

**Then**
- E-SCORE [BR-027] 所有专家打分提交后，本次评审项目的单个打分项分数为所有专家相应项打分的平均分 (behavior) [BR: BR-027]

**后置状态**：E-SCORE→(规则验证完成)
**弱依赖**：PROC-076.1
**多实例**：4 × entity=E-SCORE dim_count=1 instances=4

### PROC-114 (×2)：评审计划待评审状态，评审专家打分保存后状态变为评审中
**业务定位**：P3 ｜ happy ｜ 溯源: `T-107`
**阶段依据**：phase_table.计划状态.评审中

**Given**
- E-PLAN.计划状态 状态 = 待评审 ([实例 1] 评审计划处于待评审状态)
- E-PLAN.计划状态 状态 = 待评审 (评审专家对该计划的项目进行打分保存)

**When**
- E-PLAN.计划状态 评审专家打分保存（目标状态：评审中） by R-003 [评审专家打分保存]

**Then**
- E-PLAN.计划状态 状态转换为评审中 (state)
- E-PLAN.计划状态 状态流转：待评审→评审中 (state)
- E-PLAN.计划状态 评审计划状态由待评审变为评审中 (behavior)

**后置状态**：E-PLAN.计划状态→评审中
**依赖**：PROC-064.1, PROC-105.1, PROC-109.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-115 (×2)：评审计划暂停状态，重启后状态返回到评审中
**业务定位**：P3 ｜ happy ｜ 溯源: `T-111b`
**阶段依据**：phase_table.计划状态.评审中

**Given**
- E-PLAN.计划状态 状态 = 暂停 ([实例 1] 评审计划处于暂停状态; 暂停前状态为评审中)

**When**
- E-PLAN.计划状态 重启-返回评审中（目标状态：评审中） by R-002 [重启-返回评审中]

**Then**
- E-PLAN.计划状态 状态转换为评审中 (state)
- E-PLAN.计划状态 状态流转：暂停→评审中 (state)
- E-PLAN.计划状态 启动后，状态返回到暂停前的状态(评审中) (behavior)

**后置状态**：E-PLAN.计划状态→评审中
**依赖**：PROC-064.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-116 (×2)：待评审状态下，管理员暂停计划，验证计划状态变更为暂停
**业务定位**：P4 ｜ happy ｜ 溯源: `T-108`
**阶段依据**：phase_table.计划状态.暂停

**Given**
- E-PLAN.计划状态 状态 = 待评审 ([实例 1] 评审计划处于待评审状态)

**When**
- E-PLAN.计划状态 暂停-待评审（目标状态：暂停） by R-002 [暂停-待评审]

**Then**
- E-PLAN.计划状态 状态转换为暂停 (state)
- E-PLAN.计划状态 状态流转：待评审→暂停 (state)
- E-PLAN.计划状态 计划状态变为暂停 (behavior)
- E-PLAN.计划状态 专家不能对计划中的项目进行评审 (behavior)
- E-PLAN.计划状态 评审助理和评审管理员不能对该计划归档 (behavior)
- E-PLAN.计划状态 暂停期间计时不停 (behavior)

**后置状态**：E-PLAN.计划状态→暂停
**依赖**：PROC-064.1, PROC-105.1, PROC-109.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-117 (×2)：评审中状态下，管理员暂停计划，验证计划状态变更为暂停
**业务定位**：P4 ｜ happy ｜ 溯源: `T-109`
**阶段依据**：phase_table.计划状态.暂停

**Given**
- E-PLAN.计划状态 状态 = 评审中 ([实例 1] 评审计划处于评审中状态)

**When**
- E-PLAN.计划状态 暂停-评审中（目标状态：暂停） by R-002 [暂停-评审中]

**Then**
- E-PLAN.计划状态 状态转换为暂停 (state)
- E-PLAN.计划状态 状态流转：评审中→暂停 (state)
- E-PLAN.计划状态 计划状态变为暂停 (behavior)
- E-PLAN.计划状态 专家不能对计划中的项目进行评审 (behavior)
- E-PLAN.计划状态 暂停期间计时不停 (behavior)

**后置状态**：E-PLAN.计划状态→暂停
**依赖**：PROC-064.1, PROC-114.1, PROC-115.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-118 (×2)：暂停状态下，管理员重启计划，验证状态返回到暂停前的已完成状态
**业务定位**：P4 ｜ happy ｜ 溯源: `T-111c`
**阶段依据**：phase_table.计划状态.已完成

**Given**
- E-PLAN.计划状态 状态 = 暂停 ([实例 1] 评审计划处于暂停状态; 暂停前状态为已完成)

**When**
- E-PLAN.计划状态 重启-返回已完成（目标状态：已完成） by R-002 [重启-返回已完成]

**Then**
- E-PLAN.计划状态 状态转换为已完成 (state)
- E-PLAN.计划状态 状态流转：暂停→已完成 (state)
- E-PLAN.计划状态 启动后，状态返回到暂停前的状态(已完成) (behavior)

**后置状态**：E-PLAN.计划状态→已完成
**依赖**：PROC-064.1, PROC-116.1, PROC-117.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-119 (×2)：评审中状态下，所有项目在评审时限内变为待归档，系统完成评审计划，验证状态变更为已完成
**业务定位**：P4 ｜ happy ｜ 溯源: `T-112`
**阶段依据**：phase_table.计划状态.已完成

**Given**
- E-PLAN.计划状态 状态 = 评审中 ([实例 1] 评审计划处于评审中状态)
- E-PLAN.计划状态 状态 = 评审中 (评审计划中所有项目在评审时限内变为待归档状态)

**When**
- E-PLAN.计划状态 评审计划正常完成（目标状态：已完成） by 系统 [评审计划正常完成]

**Then**
- E-PLAN.计划状态 状态转换为已完成 (state)
- E-PLAN.计划状态 状态流转：评审中→已完成 (state)
- E-PLAN.计划状态 评审计划状态由评审中转为已完成 (behavior)

**后置状态**：E-PLAN.计划状态→已完成
**依赖**：PROC-064.1, PROC-114.1, PROC-115.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-120 (×2)：待评审状态下，超过评审时限，系统自动完成评审计划，验证状态变更为已完成
**业务定位**：P4 ｜ happy ｜ 溯源: `T-113`
**阶段依据**：phase_table.计划状态.已完成

**Given**
- E-PLAN.计划状态 状态 = 待评审 ([实例 1] 评审计划处于待评审状态; 超过评审时限)

**When**
- E-PLAN.计划状态 评审超时-待评审（目标状态：已完成） by 系统 [评审超时-待评审]

**Then**
- E-PLAN.计划状态 状态转换为已完成 (state)
- E-PLAN.计划状态 状态流转：待评审→已完成 (state)
- E-PLAN.计划状态 评审计划状态由待评审变为已完成 (behavior)
- E-PLAN.计划状态 计划中项目状态不变 (behavior)

**操作提示**
1. scheduler_manual_trigger: 系统调度器在时限到达时自动触发
2. clock_injection: 测试时注入时钟到边界值
3. db_time_update: 直接更新数据库时间到过期后

**后置状态**：E-PLAN.计划状态→已完成
**依赖**：PROC-064.1, PROC-105.1, PROC-109.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-121 (×2)：已完成状态下，管理员暂停计划，验证计划状态变更为暂停
**业务定位**：P4 ｜ happy ｜ 溯源: `T-110`
**阶段依据**：phase_table.计划状态.暂停

**Given**
- E-PLAN.计划状态 状态 = 已完成 ([实例 1] 评审计划处于已完成状态)

**When**
- E-PLAN.计划状态 暂停-已完成（目标状态：暂停） by R-002 [暂停-已完成]

**Then**
- E-PLAN.计划状态 状态转换为暂停 (state)
- E-PLAN.计划状态 状态流转：已完成→暂停 (state)
- E-PLAN.计划状态 计划状态变为暂停 (behavior)
- E-PLAN.计划状态 暂停期间计时不停 (behavior)

**后置状态**：E-PLAN.计划状态→暂停
**依赖**：PROC-064.1, PROC-118.1, PROC-119.1, PROC-120.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-122 (×2)：待评审状态下，接近截止时间，系统触发时间边界，验证状态转换为已完成
**业务定位**：P4 ｜ time_sensitive ｜ 溯源: `T-113`
**阶段依据**：phase_table.计划状态.已完成 (time_boundary)

**Given**
- E-PLAN.计划状态 状态 = 待评审 ([实例 1] 时间边界条件: 接近截止时间)

**When**
- E-PLAN.计划状态 评审超时-待评审(时间边界)（目标状态：已完成） by 系统 [评审超时-待评审(边界)]

**Then**
- E-PLAN.计划状态 状态转换为已完成(时间边界生效) (state)

**操作提示**
1. clock_injection: 测试时注入时钟到边界值
2. db_time_update: 直接更新数据库时间到过期后
3. scheduler_manual_trigger: 系统调度器在时限到达时自动触发

**后置状态**：E-PLAN.计划状态→已完成(时间边界)
**依赖**：PROC-064.1, PROC-105.1, PROC-109.1, PROC-120.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-123 (×2)：待评审状态下，超过截止时间，尝试执行超时事件，验证操作不可执行或状态不变
**业务定位**：P4 ｜ time_sensitive ｜ 溯源: `T-113`
**阶段依据**：phase_table.计划状态.已完成 (time_expired)

**Given**
- E-PLAN.计划状态 状态 = 待评审 ([实例 1] 时间过期条件: 超过截止时间)

**When**
- E-PLAN.计划状态 尝试评审超时-待评审事件(已过期) by 系统 [尝试评审超时-待评审(已过期)]

**Then**
- E-PLAN.计划状态 操作不可执行或状态不变 (behavior)

**操作提示**
1. db_time_update: 直接更新数据库时间到过期后
2. clock_injection: 测试时注入时钟到边界值
3. scheduler_manual_trigger: 系统调度器在时限到达时自动触发

**后置状态**：E-PLAN.计划状态→(过期未执行)
**依赖**：PROC-064.1, PROC-105.1, PROC-109.1, PROC-120.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-124 (×2)：评审中状态下，超过评审时限，系统自动完成评审计划，验证状态变更为已完成
**业务定位**：P4 ｜ happy ｜ 溯源: `T-114`
**阶段依据**：phase_table.计划状态.已完成

**Given**
- E-PLAN.计划状态 状态 = 评审中 ([实例 1] 评审计划处于评审中状态; 超过评审时限)

**When**
- E-PLAN.计划状态 评审超时-评审中（目标状态：已完成） by 系统 [评审超时-评审中]

**Then**
- E-PLAN.计划状态 状态转换为已完成 (state)
- E-PLAN.计划状态 状态流转：评审中→已完成 (state)
- E-PLAN.计划状态 评审计划状态由评审中变为已完成 (behavior)
- E-PLAN.计划状态 计划中项目状态不变 (behavior)

**操作提示**
1. scheduler_manual_trigger: 系统调度器在时限到达时自动触发
2. clock_injection: 测试时注入时钟到边界值
3. db_time_update: 直接更新数据库时间到过期后

**后置状态**：E-PLAN.计划状态→已完成
**依赖**：PROC-064.1, PROC-114.1, PROC-115.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-125 (×2)：评审中状态下，接近截止时间，系统触发时间边界，验证状态转换为已完成
**业务定位**：P4 ｜ time_sensitive ｜ 溯源: `T-114`
**阶段依据**：phase_table.计划状态.已完成 (time_boundary)

**Given**
- E-PLAN.计划状态 状态 = 评审中 ([实例 1] 时间边界条件: 接近截止时间)

**When**
- E-PLAN.计划状态 评审超时-评审中(时间边界)（目标状态：已完成） by 系统 [评审超时-评审中(边界)]

**Then**
- E-PLAN.计划状态 状态转换为已完成(时间边界生效) (state)

**操作提示**
1. clock_injection: 测试时注入时钟到边界值
2. db_time_update: 直接更新数据库时间到过期后
3. scheduler_manual_trigger: 系统调度器在时限到达时自动触发

**后置状态**：E-PLAN.计划状态→已完成(时间边界)
**依赖**：PROC-064.1, PROC-114.1, PROC-115.1, PROC-124.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-126 (×2)：计划处于评审中且时间过期时，系统触发评审超时事件，验证操作不可执行或状态不变
**业务定位**：P4 ｜ time_sensitive ｜ 溯源: `T-114`
**阶段依据**：phase_table.计划状态.已完成 (time_expired)

**Given**
- E-PLAN.计划状态 状态 = 评审中 ([实例 1] 时间过期条件: 超过截止时间)

**When**
- E-PLAN.计划状态 尝试评审超时-评审中事件(已过期) by 系统 [尝试评审超时-评审中(已过期)]

**Then**
- E-PLAN.计划状态 操作不可执行或状态不变 (behavior)

**操作提示**
1. db_time_update: 直接更新数据库时间到过期后
2. clock_injection: 测试时注入时钟到边界值
3. scheduler_manual_trigger: 系统调度器在时限到达时自动触发

**后置状态**：E-PLAN.计划状态→(过期未执行)
**依赖**：PROC-064.1, PROC-114.1, PROC-115.1, PROC-124.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-127 (×2)：评审计划暂停且超时时，系统触发评审超时事件，验证状态转换为已完成
**业务定位**：P4 ｜ happy ｜ 溯源: `T-115`
**阶段依据**：phase_table.计划状态.已完成

**Given**
- E-PLAN.计划状态 状态 = 暂停 ([实例 1] 评审计划处于暂停状态; 超过评审时限)

**When**
- E-PLAN.计划状态 评审超时-暂停（目标状态：已完成） by 系统 [评审超时-暂停]

**Then**
- E-PLAN.计划状态 状态转换为已完成 (state)
- E-PLAN.计划状态 状态流转：暂停→已完成 (state)
- E-PLAN.计划状态 评审计划状态由暂停变为已完成 (behavior)
- E-PLAN.计划状态 计划中项目状态不变 (behavior)

**操作提示**
1. scheduler_manual_trigger: 系统调度器在时限到达时自动触发
2. clock_injection: 测试时注入时钟到边界值
3. db_time_update: 直接更新数据库时间到过期后

**后置状态**：E-PLAN.计划状态→已完成
**依赖**：PROC-064.1, PROC-116.1, PROC-117.1, PROC-121.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-128 (×2)：评审计划暂停且接近截止时间时，系统触发评审超时事件，验证状态转换为已完成
**业务定位**：P4 ｜ time_sensitive ｜ 溯源: `T-115`
**阶段依据**：phase_table.计划状态.已完成 (time_boundary)

**Given**
- E-PLAN.计划状态 状态 = 暂停 ([实例 1] 时间边界条件: 接近截止时间)

**When**
- E-PLAN.计划状态 评审超时-暂停(时间边界)（目标状态：已完成） by 系统 [评审超时-暂停(边界)]

**Then**
- E-PLAN.计划状态 状态转换为已完成(时间边界生效) (state)

**操作提示**
1. clock_injection: 测试时注入时钟到边界值
2. db_time_update: 直接更新数据库时间到过期后
3. scheduler_manual_trigger: 系统调度器在时限到达时自动触发

**后置状态**：E-PLAN.计划状态→已完成(时间边界)
**依赖**：PROC-064.1, PROC-116.1, PROC-117.1, PROC-121.1, PROC-127.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-129 (×2)：评审计划暂停且时间过期时，系统触发评审超时事件，验证操作不可执行或状态不变
**业务定位**：P4 ｜ time_sensitive ｜ 溯源: `T-115`
**阶段依据**：phase_table.计划状态.已完成 (time_expired)

**Given**
- E-PLAN.计划状态 状态 = 暂停 ([实例 1] 时间过期条件: 超过截止时间)

**When**
- E-PLAN.计划状态 尝试评审超时-暂停事件(已过期) by 系统 [尝试评审超时-暂停(已过期)]

**Then**
- E-PLAN.计划状态 操作不可执行或状态不变 (behavior)

**操作提示**
1. db_time_update: 直接更新数据库时间到过期后
2. clock_injection: 测试时注入时钟到边界值
3. scheduler_manual_trigger: 系统调度器在时限到达时自动触发

**后置状态**：E-PLAN.计划状态→(过期未执行)
**依赖**：PROC-064.1, PROC-116.1, PROC-117.1, PROC-121.1, PROC-127.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-130 (×2)：存在操作入口时，审计管理员查看日志，验证覆盖系统日志的查看日志操作
**业务定位**：P5 ｜ crud ｜ 溯源: `EO-CRU-050`
**阶段依据**：parent_primary_phase.E-PLAN.5 (via chain from E-LOG)

**Given**
- E-LOG 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-LOG 查看日志 [执行查看日志]

**Then**
- E-LOG 覆盖系统日志的查看日志操作 (behavior)
- E-LOG 审计管理员可查看、查询日志信息 (behavior)

**操作提示**
1. 导航至系统日志页面

**后置状态**：E-LOG→(查看日志完成)
**多实例**：2 × entity=E-LOG dim_count=0 instances=2

### PROC-131 (×2)：存在操作入口时，审计管理员查询日志，验证根据日志内容、创建时间进行组合查询
**业务定位**：P5 ｜ crud ｜ 溯源: `EO-CRU-051`
**阶段依据**：parent_primary_phase.E-PLAN.5 (via chain from E-LOG)

**Given**
- E-LOG 状态 = 存在 ([实例 1] 操作入口可用)

**When**
- E-LOG 查询日志 [执行查询日志]

**Then**
- E-LOG 覆盖系统日志的查询日志操作 (behavior)
- E-LOG 根据日志内容、创建时间进行组合查询 (behavior)

**操作提示**
1. 导航至系统日志页面

**后置状态**：E-LOG→(查询日志完成)
**多实例**：2 × entity=E-LOG dim_count=0 instances=2

### PROC-132 (×2)：规则适用前提满足时，执行系统日志记录规则，验证系统日志记录只能由系统审计员查看
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-050`
**阶段依据**：parent_primary_phase.E-PLAN.5 (via chain from E-LOG)

**Given**
- E-LOG 状态 = 规则适用前提满足 ([实例 1] E-LOG相关数据已准备)

**When**
- E-LOG 按规则"系统日志记录只能由系统审计员查看"执行操作事件 [按规则"系统日志记录只能由系统审计员查看"执行操作]

**Then**
- E-LOG [BR-050] 系统日志记录只能由系统审计员查看 (behavior) [BR: BR-050]

**后置状态**：E-LOG→(规则验证完成)
**多实例**：2 × entity=E-LOG dim_count=0 instances=2

### PROC-133 (×2)：规则适用前提满足时，执行系统日志记录事件规则，验证记录事件的时间、角色、操作类型等
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-051`
**阶段依据**：parent_primary_phase.E-PLAN.5 (via chain from E-LOG)

**Given**
- E-LOG 状态 = 规则适用前提满足 ([实例 1] E-LOG相关数据已准备)

**When**
- E-LOG 按规则"系统日志记录事件的时间、角色、操作类型、日志内容和日志类型等"执行操作事件 [按规则"系统日志记录事件的时间、角色、操作类型、日志内容和日志类型等"执行操作]

**Then**
- E-LOG [BR-051] 系统日志记录事件的时间、角色、操作类型、日志内容和日志类型等 (behavior) [BR: BR-051]

**后置状态**：E-LOG→(规则验证完成)
**多实例**：2 × entity=E-LOG dim_count=0 instances=2

### PROC-134 (×2)：专家人数配置变更时，验证专家人数显示为修改后的值
**业务定位**：P5 ｜ happy ｜ 溯源: `EO-ATC-005`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 专家人数为当前值 ([实例 1] 当前专家人数配置值)

**When**
- E-PLAN 专家人数配置变更事件 [修改专家人数]

**Then**
- E-PLAN.专家人数 专家人数显示为修改后的值 (state)

**操作提示**
1. 导航至E-PLAN配置入口

**后置状态**：E-PLAN.专家人数→(已修改)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-135 (×2)：技术领域配置变更时，验证技术领域显示为修改后的值
**业务定位**：P5 ｜ happy ｜ 溯源: `EO-ATC-004`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 技术领域为当前值 ([实例 1] 当前技术领域配置值)

**When**
- E-PLAN 技术领域配置变更事件 [修改技术领域]

**Then**
- E-PLAN.技术领域 技术领域显示为修改后的值 (state)

**操作提示**
1. 导航至E-PLAN配置入口

**后置状态**：E-PLAN.技术领域→(已修改)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-136 (×2)：评审计划处于已建立状态时，管理员取消评审计划，验证状态变更为取消结束
**业务定位**：P5 ｜ rollback ｜ 溯源: `T-102`
**阶段依据**：phase_table.计划状态.取消结束

**Given**
- E-PLAN.计划状态 状态 = 已建立 ([实例 1] 评审计划处于已建立状态)

**When**
- E-PLAN.计划状态 取消评审计划（目标状态：取消结束） by R-001 [取消评审计划]

**Then**
- E-PLAN.计划状态 状态转换为取消结束 (state)
- E-PLAN.计划状态 状态流转：已建立→取消结束 (state)
- E-PLAN.计划状态 评审计划状态由已建立变为取消结束 (behavior)
- E-PLAN.计划状态 项目和专家状态返回到该计划建立前的状态 (behavior)

**后置状态**：E-PLAN.计划状态→取消结束
**依赖**：PROC-064.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-137 (×2)：评审计划处于已完成状态时，管理员归档评审计划，验证状态变更为结束并归档项目
**业务定位**：P5 ｜ audit ｜ 溯源: `T-116`
**阶段依据**：phase_table.计划状态.结束

**Given**
- E-PLAN.计划状态 状态 = 已完成 ([实例 1] 评审计划处于已完成状态)

**When**
- E-PLAN.计划状态 归档评审计划（目标状态：结束） by R-001 [归档评审计划]

**Then**
- E-PLAN.计划状态 状态转换为结束 (state)
- E-PLAN.计划状态 状态流转：已完成→结束 (state)
- E-PLAN.计划状态 评审计划状态由已完成为结束 (behavior)
- E-PLAN.计划状态 对该计划中项目按照4.5(5)归档 (behavior)
- E-PLAN.计划状态 根据项目阶段评价结果对机构进行评价 (behavior)

**后置状态**：E-PLAN.计划状态→结束
**依赖**：PROC-064.1, PROC-118.1, PROC-119.1, PROC-120.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-138 (×2)：评审计划已完成且超过归档时限时，系统触发归档超时，验证状态变更为超时结束并归档项目
**业务定位**：P5 ｜ audit ｜ 溯源: `T-117`
**阶段依据**：phase_table.计划状态.超时结束

**Given**
- E-PLAN.计划状态 状态 = 已完成 ([实例 1] 评审计划处于已完成状态; 超过归档时限)

**When**
- E-PLAN.计划状态 归档超时（目标状态：超时结束） by 系统 [归档超时]

**Then**
- E-PLAN.计划状态 状态转换为超时结束 (state)
- E-PLAN.计划状态 状态流转：已完成→超时结束 (state)
- E-PLAN.计划状态 评审计划状态由已完成变为超时结束 (behavior)
- E-PLAN.计划状态 对该计划中项目按照4.5(5)归档 (behavior)
- E-PLAN.计划状态 根据项目阶段评价结果对机构进行评价 (behavior)

**操作提示**
1. scheduler_manual_trigger: 系统调度器在时限到达时自动触发
2. clock_injection: 测试时注入时钟到边界值
3. db_time_update: 直接更新数据库时间到过期后

**后置状态**：E-PLAN.计划状态→超时结束
**依赖**：PROC-064.1, PROC-118.1, PROC-119.1, PROC-120.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-139 (×2)：评审计划接近截止时间时，系统触发归档超时（时间边界），验证状态变更为超时结束
**业务定位**：P5 ｜ time_sensitive ｜ 溯源: `T-117`
**阶段依据**：phase_table.计划状态.超时结束 (time_boundary)

**Given**
- E-PLAN.计划状态 状态 = 已完成 ([实例 1] 时间边界条件: 接近截止时间)

**When**
- E-PLAN.计划状态 归档超时(时间边界)（目标状态：超时结束） by 系统 [归档超时(边界)]

**Then**
- E-PLAN.计划状态 状态转换为超时结束(时间边界生效) (state)

**操作提示**
1. clock_injection: 测试时注入时钟到边界值
2. db_time_update: 直接更新数据库时间到过期后
3. scheduler_manual_trigger: 系统调度器在时限到达时自动触发

**后置状态**：E-PLAN.计划状态→超时结束(时间边界)
**依赖**：PROC-064.1, PROC-118.1, PROC-119.1, PROC-120.1, PROC-138.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-140 (×2)：评审计划超过截止时间时，系统尝试归档超时事件，验证操作不可执行或状态不变
**业务定位**：P5 ｜ time_sensitive ｜ 溯源: `T-117`
**阶段依据**：phase_table.计划状态.超时结束 (time_expired)

**Given**
- E-PLAN.计划状态 状态 = 已完成 ([实例 1] 时间过期条件: 超过截止时间)

**When**
- E-PLAN.计划状态 尝试归档超时事件(已过期) by 系统 [尝试归档超时(已过期)]

**Then**
- E-PLAN.计划状态 操作不可执行或状态不变 (behavior)

**操作提示**
1. db_time_update: 直接更新数据库时间到过期后
2. clock_injection: 测试时注入时钟到边界值
3. scheduler_manual_trigger: 系统调度器在时限到达时自动触发

**后置状态**：E-PLAN.计划状态→(过期未执行)
**依赖**：PROC-064.1, PROC-118.1, PROC-119.1, PROC-120.1, PROC-138.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-141 (×2)：计划类型配置变更时，验证计划类型显示为修改后的值
**业务定位**：P5 ｜ happy ｜ 溯源: `EO-ATC-003`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 计划类型为当前值 ([实例 1] 当前计划类型配置值)

**When**
- E-PLAN 计划类型配置变更事件 [修改计划类型]

**Then**
- E-PLAN.计划类型 计划类型显示为修改后的值 (state)

**操作提示**
1. 导航至E-PLAN配置入口

**后置状态**：E-PLAN.计划类型→(已修改)
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-142 (×2)：评审时段配置变更时，验证评审时段显示为修改后的值
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

### PROC-143 (×2)：按规则执行操作时，验证评审组由5、7或9个专家组成，有且只能有一个组长专家
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-007`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 规则适用前提满足 ([实例 1] E-PLAN, E-EXP相关数据已准备)

**When**
- E-PLAN 按规则"评审计划的评审组由5、7或9个专家组成，有且只能有一个组长专家"执行操作事件 [按规则"评审计划的评审组由5、7或9个专家组成，有且只能有一个组长专家"执行操作]

**Then**
- E-PLAN [BR-007] 评审计划的评审组由5、7或9个专家组成，有且只能有一个组长专家 (behavior) [BR: BR-007]

**后置状态**：E-PLAN→(规则验证完成)
**弱依赖**：PROC-001
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-144 (×2)：按规则执行操作时，验证每个评审专家的技术领域应覆盖评审计划中项目的领域
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-008`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 规则适用前提满足 ([实例 1] E-PLAN, E-EXP相关数据已准备)

**When**
- E-PLAN 按规则"每个评审专家的技术领域应覆盖评审计划中项目的领域"执行操作事件 [按规则"每个评审专家的技术领域应覆盖评审计划中项目的领域"执行操作]

**Then**
- E-PLAN [BR-008] 每个评审专家的技术领域应覆盖评审计划中项目的领域 (behavior) [BR: BR-008]

**后置状态**：E-PLAN→(规则验证完成)
**弱依赖**：PROC-001
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-145 (×2)：按规则执行操作时，验证默认回避计划中的项目所属机构的专家
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-009`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 规则适用前提满足 ([实例 1] E-PLAN, E-EXP, E-ORG相关数据已准备)

**When**
- E-PLAN 按规则"默认回避计划中的项目所属机构的专家"执行操作事件 [按规则"默认回避计划中的项目所属机构的专家"执行操作]

**Then**
- E-PLAN [BR-009] 默认回避计划中的项目所属机构的专家 (behavior) [BR: BR-009]

**后置状态**：E-PLAN→(规则验证完成)
**弱依赖**：PROC-001, PROC-011.1
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-146 (×2)：规则适用前提满足时，执行评审计划规则，验证专家工作时段分配规则
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-011`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 规则适用前提满足 ([实例 1] E-PLAN, E-EXP相关数据已准备)

**When**
- E-PLAN 按规则"一个计划中，评审组专家工作时段相同，专家一个工作时段只能被分配一个评审计划"执行操作事件 [按规则"一个计划中，评审组专家工作时段相同，专家一个工作时段只能被分配一个评审计划"执行操作]

**Then**
- E-PLAN [BR-011] 一个计划中，评审组专家工作时段相同，专家一个工作时段只能被分配一个评审计划 (behavior) [BR: BR-011]

**后置状态**：E-PLAN→(规则验证完成)
**弱依赖**：PROC-001
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-147 (×2)：规则适用前提满足时，执行评审计划规则，验证计划结束后的评审时段状态
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-014`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 规则适用前提满足 ([实例 1] E-PLAN, E-EXP相关数据已准备)

**When**
- E-PLAN 按规则"只要计划结束，评审专家与计划相应的评审时段为可用"执行操作事件 [按规则"只要计划结束，评审专家与计划相应的评审时段为可用"执行操作]

**Then**
- E-PLAN [BR-014] 只要计划结束，评审专家与计划相应的评审时段为可用 (behavior) [BR: BR-014]

**后置状态**：E-PLAN→(规则验证完成)
**弱依赖**：PROC-001
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-148 (×2)：规则适用前提满足时，执行评审计划规则，验证评审专家匹配规则
**业务定位**：P5 ｜ rule ｜ 溯源: `RO-BR-059`
**阶段依据**：primary_entity_max_phase.5

**Given**
- E-PLAN 状态 = 规则适用前提满足 ([实例 1] E-PLAN, E-EXP相关数据已准备)

**When**
- E-PLAN 按规则"在组建评审组时，可以根据项目领域和回避规则显示匹配的评审专家"执行操作事件 [按规则"在组建评审组时，可以根据项目领域和回避规则显示匹配的评审专家"执行操作]

**Then**
- E-PLAN [BR-059] 在组建评审组时，可以根据项目领域和回避规则显示匹配的评审专家 (behavior) [BR: BR-059]

**后置状态**：E-PLAN→(规则验证完成)
**弱依赖**：PROC-001
**多实例**：2 × entity=E-PLAN dim_count=1 instances=2

### PROC-149 (×2)：机构不合格状态下，尝试提为试用机构，验证操作被拒绝并保持状态
**业务定位**：P47 ｜ happy ｜ 溯源: `T-303`
**阶段依据**：dep_state_phase_map.E-ORG.机构状态.试用

**Given**
- E-ORG.机构状态 状态 = 不合格 ([实例 1] 机构处于不合格状态; 研制机构累计3次评级为不合格，则不能提为试用机构)

**When**
- E-ORG.机构状态 不合格机构提为试用（目标状态：试用） by R-004 [不合格机构提为试用]

**Then**
- E-ORG.机构状态 操作被拒绝，不合格状态保持不变并给出禁止提示（BR-032） (prompt) [BR: BR-032]
- E-ORG.机构状态 状态流转：不合格→试用 (state)
- E-ORG.机构状态 系统管理员可以对不合格机构提为试用机构 (behavior)

**后置状态**：E-ORG.机构状态→试用
**依赖**：PROC-011.1
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-150 (×2)：机构合格状态下，尝试降为不合格机构，验证操作被拒绝并保持状态
**业务定位**：P48 ｜ audit ｜ 溯源: `T-302`
**阶段依据**：dep_state_phase_map.E-ORG.机构状态.不合格

**Given**
- E-ORG.机构状态 状态 = 合格 ([实例 1] 机构处于合格状态; 评价结果满足任一条件:所有项目的阶段评价为差的次数累计达到3次及以上；或差的次数累计达到1次及以上且不合格次数累计达到3个及以上；或不合格次数累计达到5次及以上)
- E-ORG.机构状态 状态 = 合格 (计划归档时对计划中项目涉及的研制机构进行累计情况更新)

**When**
- E-ORG.机构状态 合格机构降为不合格（目标状态：不合格） by [待确认角色] [合格机构降为不合格]

**Then**
- E-ORG.机构状态 操作被拒绝，合格状态保持不变并给出禁止提示（BR-031） (prompt) [BR: BR-031]
- E-ORG.机构状态 状态流转：合格→不合格 (state)
- E-ORG.机构状态 将合格的研制机构评价为不合格机构 (behavior)

**后置状态**：E-ORG.机构状态→不合格
**依赖**：PROC-011.1, PROC-012.1
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-151 (×2)：机构试用状态下，尝试降为不合格机构，验证操作被拒绝并保持状态
**业务定位**：P48 ｜ audit ｜ 溯源: `T-305`
**阶段依据**：dep_state_phase_map.E-ORG.机构状态.不合格

**Given**
- E-ORG.机构状态 状态 = 试用 ([实例 1] 机构处于试用状态; 满足任一条件:累计2次项目阶段评价结果为差；或累计1次差且2次及以上不合格；或累计4次不合格)

**When**
- E-ORG.机构状态 试用机构降为不合格（目标状态：不合格） by [待确认角色] [试用机构降为不合格]

**Then**
- E-ORG.机构状态 操作被拒绝，试用状态保持不变并给出禁止提示（BR-033） (prompt) [BR: BR-033]
- E-ORG.机构状态 状态流转：试用→不合格 (state)
- E-ORG.机构状态 将机构降为不合格 (behavior)

**后置状态**：E-ORG.机构状态→不合格
**依赖**：PROC-011.1, PROC-149.1
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-152 (×2)：机构类型配置变更时，验证机构类型显示为修改后的值
**业务定位**：P48 ｜ happy ｜ 溯源: `EO-ATC-011`
**阶段依据**：dep_map_max_phase.E-ORG.48

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

### PROC-153 (×2)：规则适用前提满足时，执行机构评价规则，验证合格机构评价为不合格
**业务定位**：P48 ｜ rule ｜ 溯源: `RO-BR-031`
**阶段依据**：dep_map_max_phase.E-ORG.48

**Given**
- E-ORG 状态 = 规则适用前提满足 ([实例 1] E-ORG相关数据已准备)

**When**
- E-ORG 按规则"对合格机构：所有项目的阶段评价为差的次数累计达到3次及以上；或差的次数累计达到1次及以上且不合格次数累计达到3个及以上；或不合格次数累计达到5次及以上，将合格的研制机构评价为不合格机构"执行操作事件 [按规则"对合格机构：所有项目的阶段评价为差的次数累计达到3次及以上；或差的次数累计达到1次及以上且不合格次数累计达到3个及以上；或不合格次数累计达到5次及以上，将合格的研制机构评价为不合格机构"执行操作]

**Then**
- E-ORG [BR-031] 对合格机构：所有项目的阶段评价为差的次数累计达到3次及以上；或差的次数累计达到1次及以上且不合格次数累计达到3个及以上；或不合格次数累计达到5次及以上，将合格的研制机构评价为不合格机构 (behavior) [BR: BR-031]

**后置状态**：E-ORG→(规则验证完成)
**多实例**：2 × entity=E-ORG dim_count=1 instances=2

### PROC-154 (×5)：项目已选入状态下，尝试纳入评审计划，验证操作被拒绝并保持状态
**业务定位**：P86 ｜ happy ｜ 溯源: `T-003`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.待评审

**Given**
- E-PROJ.项目状态 状态 = 已选入 ([实例 1] 项目处于已选入状态; 评审计划从处于已选入状态的项目中选取1-5个项目纳入评审计划)

**When**
- E-PROJ.项目状态 项目纳入评审计划（目标状态：待评审） by R-001 [项目纳入评审计划]

**Then**
- E-PROJ.项目状态 操作被拒绝，已选入状态保持不变并给出禁止提示（BR-005） (prompt) [BR: BR-005]
- E-PROJ.项目状态 状态流转：已选入→待评审 (state)
- E-PROJ.项目状态 项目状态由待评审变为待评审(纳入计划) (behavior)
- E-PROJ.项目状态 评审计划状态保存为已建立 (behavior)

**后置状态**：E-PROJ.项目状态→待评审
**依赖**：PROC-076.1
**弱依赖**：PROC-064.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-155 (×5)：待评审项目尝试转换为评审中，操作被拒绝，状态保持待评审
**业务定位**：P86 ｜ invalid ｜ 溯源: `RO-IT-002`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.待评审

**Given**
- E-PROJ 状态 = 待评审 ([实例 1] E-PROJ处于"待评审"状态)

**When**
- E-PROJ 尝试待评审→评审中转换事件 [尝试执行从"待评审"到"评审中"的操作]

**Then**
- E-PROJ 操作被拒绝，不能对不合格研制机构所属项目进行评审(已下发的评审计划中的项目不受影响) (prompt)
- E-PROJ 状态仍为待评审 (state)

**后置状态**：E-PROJ→(操作被阻止)
**依赖**：PROC-154.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-156 (×5)：待评审项目评审计划启动后进入评审中，状态流转正确
**业务定位**：P87 ｜ happy ｜ 溯源: `T-004`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.评审中

**Given**
- E-PROJ.项目状态 状态 = 待评审 ([实例 1] 项目处于待评审状态)
- E-PROJ.项目状态 状态 = 待评审 (评审计划状态由待启动变为待评审)

**When**
- E-PROJ.项目状态 评审计划启动后项目进入评审中（目标状态：评审中） by R-002 [评审计划启动后项目进入评审中]

**Then**
- E-PROJ.项目状态 状态转换为评审中 (state)
- E-PROJ.项目状态 状态流转：待评审→评审中 (state)
- E-PROJ.项目状态 项目状态由待评审变为评审中 (behavior)

**后置状态**：E-PROJ.项目状态→评审中
**依赖**：PROC-076.1, PROC-154.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-157 (×5)：评审中项目专家提交打分后状态转换为待归档，自动进行项目评价
**业务定位**：P88 ｜ audit ｜ 溯源: `T-005`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.待归档

**Given**
- E-PROJ.项目状态 状态 = 评审中 ([实例 1])
- E-PROJ.项目状态 状态 = 评审中 (评审组全部专家提交了项目打分)

**When**
- E-PROJ.项目状态 评审组全部专家提交打分（目标状态：待归档） by 系统 [评审组全部专家提交打分]

**Then**
- E-PROJ.项目状态 状态转换为待归档 (state)
- E-PROJ.项目状态 状态流转：评审中→待归档 (state)
- E-PROJ.项目状态 项目状态由评审中变为待归档 (behavior)
- E-PROJ.项目状态 自动进行项目评价 (behavior)

**后置状态**：E-PROJ.项目状态→待归档
**依赖**：PROC-076.1, PROC-156.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-158 (×5)：评审中项目专家全部提交打分后状态转换为待归档，自动进行项目评价
**业务定位**：P88 ｜ audit ｜ 溯源: `T-005[f], T-005[d], T-005[c], T-005[e], T-005[a], T-005[b]`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.待归档

**Given**
- E-PROJ.项目状态 状态 = 评审中 ([实例 1] 评审组人数=5; 评审身份=组长专家)
- E-PROJ.项目状态 状态 = 评审中 (评审组全部专家提交了项目打分)
- E-PLAN.评审组人数 状态 = 5 (分支条件: 评审组人数=5)
- E-EXP.评审身份 状态 = 组长专家 (分支条件: 评审身份=组长专家)

**When**
- E-PROJ.项目状态 评审组全部专家提交打分（目标状态：待归档） by [待确认角色] [评审组全部专家提交打分]

**Then**
- E-PROJ.项目状态 状态转换为待归档 (state)
- E-PROJ.项目状态 状态流转：评审中→待归档 (state)
- E-PROJ.项目状态 项目状态由评审中变为待归档 (behavior)
- E-PROJ.项目状态 自动进行项目评价 (behavior)

**后置状态**：E-PROJ.项目状态→待归档
**依赖**：PROC-002, PROC-003, PROC-076.1, PROC-156.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-159 (×5)：项目待归档且开题不合格或差时，系统操作，项目状态变更为待选入
**业务定位**：P88 ｜ branch ｜ 溯源: `T-006b[a], T-006b[h], T-006b[i], T-006b[e], T-006b[c], T-006b[j], T-006b, T-006b[d], T-006b[g], T-006b[f], T-006b[b]`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.待归档

**Given**
- E-PROJ.项目状态 状态 = 待归档 ([实例 1] 项目处于待归档状态; 在开题阶段，项目的评级为不合格或差)
- E-PROJ.项目状态 状态 = 待归档 (评审计划状态由已完成变为结束或超时结束)

**When**
- E-PROJ.项目状态 归档评级-开题不合格或差（目标状态：待选入） by 系统 [归档评级-开题不合格或差]

**Then**
- E-PROJ.项目状态 状态转换为待选入 (state)
- E-PROJ.项目状态 状态流转：待归档→待选入 (state)
- E-PROJ.项目状态 项目状态由待归档变为待选入 (behavior)
- E-PROJ.项目状态 阶段不变 (behavior)
- E-PROJ.项目状态 状态可回退至前驱状态 (behavior)

**后置状态**：E-PROJ.项目状态→待选入
**依赖**：PROC-076.1, PROC-103.1, PROC-157.1, PROC-158.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-160 (×5)：项目待归档且验收不合格或差时，系统操作，项目状态变更为待选入
**业务定位**：P88 ｜ branch ｜ 溯源: `T-006d[g], T-006d[i], T-006d[e], T-006d, T-006d[f], T-006d[b], T-006d[j], T-006d[a], T-006d[h], T-006d[d], T-006d[c]`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.待归档

**Given**
- E-PROJ.项目状态 状态 = 待归档 ([实例 1] 项目处于待归档状态; 在验收阶段，项目的评级为不合格或差)
- E-PROJ.项目状态 状态 = 待归档 (评审计划状态由已完成变为结束或超时结束)

**When**
- E-PROJ.项目状态 归档评级-验收不合格或差（目标状态：待选入） by 系统 [归档评级-验收不合格或差]

**Then**
- E-PROJ.项目状态 状态转换为待选入 (state)
- E-PROJ.项目状态 状态流转：待归档→待选入 (state)
- E-PROJ.项目状态 项目状态由待归档变为待选入 (behavior)
- E-PROJ.项目状态 阶段不变 (behavior)
- E-PROJ.项目状态 状态可回退至前驱状态 (behavior)

**后置状态**：E-PROJ.项目状态→待选入
**依赖**：PROC-076.1, PROC-103.1, PROC-157.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-161 (×5)：项目待归档且开题合格及以上时，系统操作，项目状态变更为已选入
**业务定位**：P89 ｜ branch ｜ 溯源: `T-006a[f], T-006a[e], T-006a[h], T-006a[d], T-006a[c], T-006a, T-006a[a], T-006a[g], T-006a[j], T-006a[b], T-006a[i]`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.已选入

**Given**
- E-PROJ.项目状态 状态 = 待归档 ([实例 1] 项目处于待归档状态; 在开题阶段，项目的评级在合格及以上)
- E-PROJ.项目状态 状态 = 待归档 (评审计划状态由已完成变为结束或超时结束)

**When**
- E-PROJ.项目状态 归档评级-开题合格及以上（目标状态：已选入） by 系统 [归档评级-开题合格及以上]

**Then**
- E-PROJ.项目状态 状态转换为已选入 (state)
- E-PROJ.项目状态 状态流转：待归档→已选入 (state)
- E-PROJ.项目状态 项目状态由待归档变为已选入 (behavior)
- E-PROJ.项目状态 项目阶段由开题变为验收 (behavior)

**后置状态**：E-PROJ.项目状态→已选入
**依赖**：PROC-076.1, PROC-103.1, PROC-157.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-162 (×5)：评审中且已完成计划中包含评审中项目时，系统操作，项目状态变更为已选入
**业务定位**：P89 ｜ happy ｜ 溯源: `T-006e`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.已选入

**Given**
- E-PROJ.项目状态 状态 = 评审中 ([实例 1] 项目处于评审中状态; 对已完成计划中包含的处于评审中状态的项目)
- E-PROJ.项目状态 状态 = 评审中 (评审计划状态由已完成变为结束或超时结束)

**When**
- E-PROJ.项目状态 已完成计划中评审中项目回到建立前（目标状态：已选入） by 系统 [已完成计划中评审中项目回到建立前]

**Then**
- E-PROJ.项目状态 状态转换为已选入 (state)
- E-PROJ.项目状态 状态流转：评审中→已选入 (state)
- E-PROJ.项目状态 项目状态回到该计划建立前(已选入) (behavior)

**后置状态**：E-PROJ.项目状态→已选入
**依赖**：PROC-076.1, PROC-156.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-163 (×5)：已选入状态的项目尝试选出，操作被拒绝并保持状态
**业务定位**：P89 ｜ rollback ｜ 溯源: `T-007`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.已选入

**Given**
- E-PROJ.项目状态 状态 = 已选入 ([实例 1] 评审管理员只能对已选入状态的项目进行选出)

**When**
- E-PROJ.项目状态 项目选出（目标状态：待选入） by R-001 [项目选出]

**Then**
- E-PROJ.项目状态 操作被拒绝，已选入状态保持不变并给出禁止提示（BR-005） (prompt) [BR: BR-005]
- E-PROJ.项目状态 状态流转：已选入→待选入 (state)
- E-PROJ.项目状态 项目状态由已选入变为待选入 (behavior)
- E-PROJ.项目状态 状态可回退至前驱状态 (behavior)

**后置状态**：E-PROJ.项目状态→待选入
**依赖**：PROC-076.1, PROC-161.1, PROC-162.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-164 (×5)：待选入状态的项目尝试选入，操作被拒绝并保持状态
**业务定位**：P89 ｜ negative ｜ 溯源: `T-002`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.已选入

**Given**
- E-PROJ.项目状态 状态 = 待选入 ([实例 1] 项目处于待选入状态; 本阶段评价结果为差的项目不可选入; 对于本阶段不合格评价结果的项目，只有1次选入机会)

**When**
- E-PROJ.项目状态 项目选入（目标状态：已选入） by R-001 [项目选入]

**Then**
- E-PROJ.项目状态 操作被拒绝，状态保持为待选入并给出禁止提示 (state)

**后置状态**：E-PROJ.项目状态→待选入
**依赖**：PROC-076.1, PROC-159.1, PROC-160.1, PROC-163.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-165 (×5)：待选入状态的项目成功选入，状态转换为已选入
**业务定位**：P89 ｜ happy ｜ 溯源: `T-002`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.已选入

**Given**
- E-PROJ.项目状态 状态 = 待选入 ([实例 1] 项目处于待选入状态; 对于本阶段不合格评价结果的项目，只有1次选入机会)

**When**
- E-PROJ.项目状态 项目选入（目标状态：已选入） by R-001 [项目选入]

**Then**
- E-PROJ.项目状态 状态转换为已选入 (state)
- E-PROJ.项目状态 状态流转：待选入→已选入 (state)

**后置状态**：E-PROJ.项目状态→已选入
**依赖**：PROC-076.1, PROC-159.1, PROC-163.1, PROC-164.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-166 (×5)：技术领域配置变更后，项目技术领域显示修改后的值
**业务定位**：P90 ｜ happy ｜ 溯源: `EO-ATC-001`
**阶段依据**：dep_map_max_phase.E-PROJ.90

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

### PROC-167 (×5)：项目待归档且评级合格及以上时，系统自动归档项目，状态变更为已归档
**业务定位**：P90 ｜ branch ｜ 溯源: `T-006c[b], T-006c[h], T-006c[g], T-006c[d], T-006c[a], T-006c, T-006c[e], T-006c[i], T-006c[f], T-006c[c], T-006c[j]`
**阶段依据**：dep_state_phase_map.E-PROJ.项目状态.已归档

**Given**
- E-PROJ.项目状态 状态 = 待归档 ([实例 1] 项目处于待归档状态; 在验收阶段，项目的评级在合格及以上)
- E-PROJ.项目状态 状态 = 待归档 (评审计划状态由已完成变为结束或超时结束)

**When**
- E-PROJ.项目状态 归档评级-验收合格及以上（目标状态：已归档） by 系统 [归档评级-验收合格及以上]

**Then**
- E-PROJ.项目状态 状态转换为已归档 (state)
- E-PROJ.项目状态 状态流转：待归档→已归档 (state)
- E-PROJ.项目状态 项目状态由待归档变为已归档 (behavior)
- E-PROJ.项目状态 阶段不变 (behavior)

**后置状态**：E-PROJ.项目状态→已归档
**依赖**：PROC-076.1, PROC-103.1, PROC-157.1
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-168 (×5)：E-PROJ.项目类型→(已修改)
**业务定位**：P90 ｜ happy ｜ 溯源: `EO-ATC-002`
**阶段依据**：dep_map_max_phase.E-PROJ.90

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

### PROC-169 (×5)：规则适用前提下，执行删除待选入且未评价过的项目操作
**业务定位**：P90 ｜ rule ｜ 溯源: `RO-BR-001`
**阶段依据**：dep_map_max_phase.E-PROJ.90

**Given**
- E-PROJ 状态 = 规则适用前提满足 ([实例 1] E-PROJ相关数据已准备)

**When**
- E-PROJ 按规则"只能删除待选入且未评价过的项目"执行操作事件 [按规则"只能删除待选入且未评价过的项目"执行操作]

**Then**
- E-PROJ [BR-001] 只能删除待选入且未评价过的项目 (behavior) [BR: BR-001]

**后置状态**：E-PROJ→(规则验证完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-170 (×5)：规则适用前提下，执行只可编辑待选入的项目信息操作
**业务定位**：P90 ｜ rule ｜ 溯源: `RO-BR-002`
**阶段依据**：dep_map_max_phase.E-PROJ.90

**Given**
- E-PROJ 状态 = 规则适用前提满足 ([实例 1] E-PROJ相关数据已准备)

**When**
- E-PROJ 按规则"只可编辑待选入的项目信息，对评价过的项目编辑附件"执行操作事件 [按规则"只可编辑待选入的项目信息，对评价过的项目编辑附件"执行操作]

**Then**
- E-PROJ [BR-002] 只可编辑待选入的项目信息，对评价过的项目编辑附件 (behavior) [BR: BR-002]

**后置状态**：E-PROJ→(规则验证完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-171 (×5)：项目数据准备齐全时，执行查询规则，验证机构管理员可按名称和领域查询项目
**业务定位**：P90 ｜ rule ｜ 溯源: `RO-BR-006`
**阶段依据**：dep_map_max_phase.E-PROJ.90

**Given**
- E-PROJ 状态 = 规则适用前提满足 ([实例 1] E-PROJ相关数据已准备)

**When**
- E-PROJ 按规则"机构管理员可依据项目名称和技术领域条件进行查询"执行操作事件 [按规则"机构管理员可依据项目名称和技术领域条件进行查询"执行操作]

**Then**
- E-PROJ [BR-006] 机构管理员可依据项目名称和技术领域条件进行查询 (behavior) [BR: BR-006]

**后置状态**：E-PROJ→(规则验证完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5

### PROC-172 (×5)：项目数据准备齐全时，执行项目进级规则，验证项目级别根据得分和约束调整
**业务定位**：P90 ｜ rule ｜ 溯源: `RO-BR-029`
**阶段依据**：dep_map_max_phase.E-PROJ.90

**Given**
- E-PROJ 状态 = 规则适用前提满足 ([实例 1] E-PROJ相关数据已准备)

**When**
- E-PROJ 按规则"依据系统内置的项目级别评判表对项目进级，优先根据得分匹配可能的最好项目级别，然后判别剩余约束是否全部满足，若全部满足则为相应最好项目级别，否则项目级别降为下一级(只降一级)"执行操作事件 [按规则"依据系统内置的项目级别评判表对项目进级，优先根据得分匹配可能的最好项目级别，然后判别剩余约束是否全部满足，若全部满足则为相应最好项目级别，否则项目级别降为下一级(只降一级)"执行操作]

**Then**
- E-PROJ [BR-029] 依据系统内置的项目级别评判表对项目进级，优先根据得分匹配可能的最好项目级别，然后判别剩余约束是否全部满足，若全部满足则为相应最好项目级别，否则项目级别降为下一级(只降一级) (behavior) [BR: BR-029]

**后置状态**：E-PROJ→(规则验证完成)
**多实例**：5 × entity=E-PROJ dim_count=2 instances=5
