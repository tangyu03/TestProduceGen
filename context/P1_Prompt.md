## 0. 术语
当前实体=当前转换 entity；XC=cross_entity；BR=business_rules；镜像=跨实体 precondition 复制为 XC；穿透=分支维度在 transitions/XC/BR 三层均有体现；驱动方=引发他方状态变化者，transition_relations 记 from=驱动方、to=被驱动方；侧挂=暂停/挂起状态。

## 1. 职责边界
AI 仅执行：理解文档→按步骤产出结构化数据→自检校验。凡"框架/校验器/自动推导/笛卡尔积"字样=下游框架职责，AI 不执行、不假设其行为，仅产出其所需数据。

## 2. 优先级仲裁（命中冲突按下表取高者）
|级|规则|要点|
|---|---|---|
|P0|critical 中断|命中清单→停，仅输出中断 Schema，豁免 P2|
|P1|字符安全|箭头→文字、弯引号→直引号、`<>&`转义；保留原文类字段同样转义，note.comment 注"已按铁律4转义"；覆盖"保留原文"|
|P2|空值规范|字段必存在填`[]`/`""`；source_ref 例外必非空|
|P3|不脑补|仅记录文档提及或可合理推导|
|P4|动态中断|critical→中断；minor→假设填充+inferred+ambiguity_list|
|P5|约束≠因果|门禁/前置非因果，跨实体因果必过 4.6|
|P6|终态语义|from≠终态；终态有出边→非终态；覆盖 4.4 逆向补边|
|P7|推断标注|inferred:true 时 comment 写依据|
|P8|结构行为解耦|实体不含行为逻辑，structural 无因果语义|
|P9|组织维度≠业务归属|按 Step2 判|
|P10|trigger_source 优先级|cross_entity>action>expected_results>desc>business_rule>bidi_coupling，去重仅升级|
|P11|结构四元分类|按 Step2|
|P12|preconditions 结构化|对象数组，见 4.2.1|
|P13|无状态操作归位|不改状态维度→只入 operations；改状态→入 transitions(crud 作索引)；必须/不得→只入 BR|

**critical 清单**（命中即中断，余皆 minor）：①无 core 实体；②主流程状态枚举完全缺失且无可推依据；③同一核心流程描述矛盾无法取舍；④输入为空或非需求文档；⑤校验修复失败。

## 3. 输入契约
source_ref 用"章节号+标题"，无章节用原文片段(≤30字)，一律非空。XC 派生对象继承宿主转换 source_ref（镜像/联动继承指向 T-xxx；4.6 判约束类继承含对应 precondition 的转换），无法确定取支撑原文位置。XC/IT 无 note 字段，source_ref 按 P1 转义。`_meta.source` 无文件名填"未命名文档"。

**增量回写**：回写=仅向 Step0(action_verbs)/Step0.5(permissions) 数组追加新项，标 inferred:true+comment"Step X 发现…，回写"；不重跑步骤、不改既有项。

## 4. 输出 Schema
```json
{
  "_meta":{"version":"19.2","generated_at":"","source":"","document_scope":"","has_critical_ambiguity":false,"consistency_check":"passed|warnings","ambiguity_list":[],"pipeline_trace":{},"branch_dimensions":[]},
  "_context":{
    "prohibition_config":{"action_verbs":[],"prohibit_keywords":[],"negation_prefixes":{"operation_negators":["不可","不能","禁止","不得","不允许","无权"],"state_negators":["未被","未"]},"transition_indicators":["状态转换为","状态变更为","变为","进入"],"success_hints":["操作成功","提交成功","保存成功","已完成","已生成","已发送"],"note":{"inferred":false,"comment":""}},
    "permissions":[{"role":"R-001","operations":[]}]
  },
  "domain_model":{
    "entities":[{"id":"E-XXX","name":"","desc":"","type":"core|managed","tags":[],"attributes":[{"name":"","desc":"","is_config":false}],"state_dimensions":[{"dimension_name":"","states":[],"initial":"","terminal":[],"note":{"inferred":false,"comment":""}}],"operations":[{"name":"","category":"session|ui|file|query|crud|config","expected_results":[],"source_ref":"","note":{"inferred":false,"comment":""}}]}],
    "roles":[{"id":"R-XXX","name":"","readonly":false}],
    "structural_relations":[{"from":"E-XXX","to":"E-YYY","relation_type":"composition|reference|hierarchy|self_reference","cardinality":"1:N|1:1|M:N","ownership_dimension":"business_ownership|management_dimension|configuration_source","desc":"","confidence":"high|medium|low","note":{"inferred":false,"comment":"","conflict":""}}],
    "transition_relations":[{"from":"E-XXX","to":"E-YYY","desc":"","trigger":"","trigger_source":"cross_entity|action|expected_results|desc|business_rule|bidi_coupling","evidence_transitions":["T-XXX"],"rollback_propagation":false,"confidence":"high|medium|low","note":{"inferred":false,"comment":""}}]
  },
  "state_and_flow":{
    "transitions":[{"id":"T-XXX","entity":"E-XXX","dimension":"","from":"源状态|null","to":"","action":"","role":"R-XXX|system","preconditions":[{"text":"","type":"state_ref|event_ref|constraint","ref":{"entity":"E-XXX","dimension":"","state":""}}],"expected_results":[],"traits":[],"direction":"forward|backward|lateral|resume","priority":"P0|P1|P2","source_ref":"","note":{"inferred":false,"comment":"","conflict":"","branch_dimension":""}]}]
  },
  "constraints":{
    "invalid_transitions":[{"id":"IT-XXX","entity":"E-XXX","from":"","to":"","reason":"","source_ref":""}],
    "cross_entity":[{"id":"XC-XXX","source_entity":"E-XXX","source_transition":"T-XXX","source_state":"","target_entity":"E-YYY","target_dimension":"","target_from":"被驱动转换起点状态或null","target_to":"被驱动转换终点状态或null","target_condition":"人读备注(自由文本,可省略)","desc":"","source_ref":""}],
    "business_rules":[{"id":"BR-XXX","category":"validation|computation|authorization|timing|notification|usability|display","desc":"","entities_involved":["E-XXX"],"enforcement":"mandatory|conditional","source_ref":"","signal_type":"restrictive|usability|display|field_constraint","note":{"inferred":false,"comment":"","branch_dimension":""}}]
  }
}
```

**字段硬约束**：action_verbs 必填非空；permissions 仅声明无状态操作（转换型由 transitions.role 承载），role 用 R-XXX；note.inferred 必填，true 时 comment 必填；矛盾 conflict 必填；受分支影响 branch_dimension 必填（仅 transitions/BR）；preconditions[*].text 必填(P1转义)，state_ref 时 ref 必填且 state∈该实体该维度 states，event_ref/constraint 时 ref=null；operations[*].name/category/source_ref 必填非空，expected_results≥1 原文措辞，未述及以操作名原文短语补入标 inferred，crud 类与 transitions 并存不视为重复、note.comment 回填 T-xxx；evidence_transitions：desc/business_rule 来源允许`[]`但注明，其余必填且引用存在；confidence：显式 high/推导 medium/修补不得 high；entities_involved 为数组。

**pipeline_trace 键**：
```
step0_prohibition_config{action_verbs_count,prohibit_keywords_count,inferred_additions_count}
step0_5_permissions{roles_count,operations_count,inferred_additions_count}
step1_entities[]
step2_structural_relations
step3_branch_dimensions
step4_transitions
step4_transition_relations
step4_roles
step4_precondition_stats{total,state_ref,event_ref,constraint,state_ref_resolved,state_ref_unresolved}
step5_invalid_transitions
step5_cross_entity
step5_business_rules
```

## 5. 流水线（Step0→6 不可跳步；仅 4.4 自检与 Step6 校验可回修，无原文依据标 inferred 注明）

### Step 0 禁词配置 → prohibition_config
提取原文动词词根(去宾语去重，同义簇录一个)入 action_verbs；BR 限制句中被禁动词也计入。action_verbs 做粗筛（动词是否被禁止），BR 做精筛（宾语级约束），两者正交。prohibit_keywords 仅录框架笛卡尔积派生不了的复杂否定短语(带量化/条件/复合动词)，子串匹配；简单否定不录，宾语级精确否定交 BR(signal_type=authorization)。Step1-5 发现新动词追加并标 inferred。

### Step 0.5 角色权限 → permissions
仅声明无状态操作权限(session/ui/file/query/config 及无对应转换的 crud)；转换型由 transitions.role 承载不写。role 用 R-XXX(与 transitions.role 同引用键)。permission 做粗筛（角色→可执行操作集合），授权类 BR(signal_type=authorization) 做精筛（操作范围/条件/宾语级限制），两者不重复。数据/机构范围限制交授权类 BR。Step1-5 发现新角色/操作追加标 inferred。

### Step 1 实体 → entities
排除前言/变更记录，优先术语定义。独立实体(任一)：独立生命周期/被多实体引用/独立状态流转或操作权限。core(定义状态枚举/多步多角色/状态自主) vs managed(CRUD/配置字典/状态简单)，交集→core。二次判定：多角色审批链/独立业务载体/可独立循环→剥离独立实体。tags: approvable/multi-state/expirable/collaborative/configurable。属性=静态特征(取值致流转分支标 is_config:true)，desc 完整转录约束(范围/长度/格式/必填/唯一/默认/不可编辑/排除性，分号分隔)。状态维度=生命周期演进(≥2状态)，明确 initial/terminal/states。operations(P13)：扫描全部用户可执行操作(含通用/易用性章节)，逐操作输出；category 六枚举他类取最近注明；expected_results≥1 原文关键词禁概括，未述及以操作名原文短语补入标 inferred；同实体同名合并，跨实体通用仅最相关实体登一次注"通用操作"。

### Step 2 结构关系 → structural_relations
from=父/拥有方,to=子；cardinality 父→子视角永不 N:1，M:N 无方向先出现者 from 并注明。relation_type：拥有/包含/组成→composition；关联/引用/属于→reference；上下级→hierarchy；递归→self_reference。desc 翻转为父侧视角。

**四元分类判定**：
```
判定1(业务归属)：B核心产出属第三方C→改C→B；A仅提供参数/模板→(a)；属于A→判定2
判定2(创建同步性)：
  (a)配置来源[A提供配置/规则模板/分类数据,B生命周期独立]→reference/configuration_source
  (b)生命周期同步[B无独立创建,A创建时B自动进initial,无独立审批/触发,每条A必有B]
     判定3(1:1验证):若1:1且可能存在无B→归(d)
     否则→composition/business_ownership
  (c)事件触发+B为core流程实体[B有独立多步创建/前置条件/可能永不创建；B是core且自身有
     dependent，A为其业务归属容器]→composition/business_ownership(dependent拓扑需沿
     composition链传递,不可降为(d))
  (d)事件触发且非(c)[B有独立多步创建/前置条件/可能永不创建/独立创建时点；其余情况]
     →reference/configuration_source(折中取值勿按语义改)
联动约束：composition↔business_ownership，reference↔configuration_source
management_dimension 必复核，纯管理归属可保留注复核结论否则改业务归属
```

### Step 3 分支维度 → branch_dimensions
配置型(is_config:true 属性，创建时确定互斥影响后续行为)；运行时选择型(信号"根据…选择/分为"，evidence 注"运行时选择型")。输出{dimension,entity,values[],impact_scope,evidence,branches[{value,target_transition,desc}],coverage{transitions[],cross_entity[],business_rules[]}}。coverage 本步留空，Step6 回填。

### Step 4 转换与因果

**4.1-4.2 转换提取**：必填 id/entity/dimension/from(仅创建null)/to/action/role/preconditions/expected_results/traits/direction/priority/source_ref/note。traits∈[audit,rollback,branch,time_sensitive,data_constraint]；priority P0/P1/P2。

**direction 判定**（必填，与 traits 正交，rollback trait≠backward direction）：
|优先级|条件|direction|
|---|---|---|
|①|文档明确(回退/返回/暂停/重启)|按文档|
|②|from/to 为侧挂状态|lateral(进入侧挂)/resume(返回)|
|③|states 有先后|to 在后=forward；to 在前=backward|
|④|无法判断|inferred+依据|

forward=主链推进；backward=合法回退；lateral=侧挂入口(同相位)；resume=从侧挂返回。分支穿透：受分支影响转换标 branch trait，expected_results 用"若{维度}={值}，则{结果}"，note.branch_dimension 标维度。跨维度联动：仅源维度建转换，expected_results 含目标维度变化，Step5 登记联动 XC。文档明确转换内多步骤且有角色/操作依赖时，拆分为多条转换，用 preconditions 表达步骤先后。

**4.2.1 preconditions**(P12)：每项{text,type,ref}，text 保留原文(P1转义)。type 优先级 state_ref>event_ref>constraint。
```
显式"实体.维度=状态"且state∈states         → state_ref, ref={entity,dimension,state}
仅状态值:先匹配当前实体同维度→再他实体→无法消歧→constraint,ref=null,注明理由
独立业务事件已完成(无法映射状态,如"通知单已上传")→event_ref,ref=null
含"不可/不得/禁止/累计/按X计算"等规则        →constraint,ref=null
```

**4.3 角色**：收录全部角色，未作执行者标 readonly:true。system 保留角色不入 roles，转换 role 可引用。

**4.4 自检修复**：①每非终态有出边；②孤立终态补入边(from 必非终态(P6)，优先业务合理源标 inferred 注"终态可达性补入"，无非终态→放弃标 conflict="孤立终态[xxx]无非终态入边")；③初始可达；④分支覆盖；⑤crud 操作回填(note.comment 标对应 T-xxx 分号分隔，确无注明"无对应转换"及理由)。回写特权扩展至 action_verbs。

**4.5 因果构建 → transition_relations**(from=驱动方,to=被驱动方)：
|来源|触发信号|trigger_source|evidence|confidence|
|---|---|---|---|---|
|显式因果|"B完成后A变为/B触发A/审批结果驱动"|desc|允许`[]`注明位置|high|
|数据推导①|T1.expected_results 影响E2状态→T1.entity→E2|expected_results|必填引用存在|medium|
|数据推导②|T2.preconditions 含 state_ref 指向E1→E1→T2.entity|action|必填|medium|
|双向耦合|structural A→B 但B驱动A(T_B.expected_results影响A/T_A.preconditions依赖B/子变致父变)|bidi_coupling|必填且structural反向A→B存在|medium|

rollback_propagation：驱动方含 rollback 且 desc 含"退/撤销/驳回/回退/拒绝"被驱动方随退→true。同(from,to)按 P10 去重仅升级。

**4.6 约束/因果鉴别**(P5，每条写入前必过)：X=驱动方候选,Y=被驱动方候选。
```
Q1 因果性：X变是否直接导致Y变(无需额外操作)？需额外→约束(必入XC,不写relations)
Q2 已表达性：Y侧precondition.state_ref指向X或已有XC？→门禁不重复写
Q3 层级性：上级状态作下级门禁→约束(入XC)；下级全完成上级自动推进→因果(双向耦合,入relations)
```

### Step 5 约束与因果补充
- **invalid_transitions**：仅文档明确禁止时生成。
- **XC 三来源**：①镜像：跨实体 precondition(state_ref 且 ref.entity≠当前实体)→desc 以"镜像T-xxx precondition'…'"开头；4.6 判约束关系同此,desc 加"由Step4.6约束-因果鉴别确认"。②联动：desc="联动:T-xxx执行后{实体}.{维度}由{旧值}变为{新值}"。③分支差异：desc="分支[{维度}={值}]:{约束差异}"。
- **XC 结构化因果字段(必填,治本)**：每条 XC 必填 `target_from`/`target_to`，即被驱动转换的起止状态（target_entity 状态维度上的 from/to），由 desc 语义逐字转录——联动模板的"由{旧值}变为{新值}"即旧值=target_from、新值=target_to；镜像类同 rule 的联动对共享同一 (target_from,target_to)。单状态目标(如"回到计划建立前(已选入)")不得省略 from——回退语义下 from=回退前的状态(待评审)。聚合/计算/多转换目标(按…变更/不变…)填 null。`target_condition` 仅人读备注，下游优先读结构化字段，自由文本仅兜底。
- **BR 三信号**：①限制性词(必须/不得/仅当/禁止/不能/不可/不超过)→validation|computation|authorization|timing|notification,restrictive；②陈述句(应提供/应支持/可)→usability，(显示/展示)→display，易用性章节逐条独立成BR；③字段约束属性→validation,desc 复用属性完整约束,field_constraint。每分支维度目标≥1条BR含 branch_dimension；无信号不生成，coverage 标缺口(P3)。
- **5.4 因果补充**：XC 中 source≠target 且 source_transition+target_condition 构成因果链→cross_entity；timing 类 BR 时间触发+受影响实体→business_rule。均过 4.6，同(from,to)按 P10 仅升级。

### Step 6 校验与输出
回填 branch_dimensions.coverage，最终组装。失败自修，修复失败→critical。13 项：
①引用完整性(实体/角色/状态存在,system豁免)；②状态结构(初始可达/非终态有出边/P6:from∈terminal且to∈terminal→移除标conflict,rollback且from∈terminal→warning)；③preconditions结构(对象数组/text非空/type合法/state_ref时ref对应已建模实体维度,其余ref=null/纯字符串→判type封装/ref缺失→补全或降级)；④镜像完整性(跨实体precondition至少在relations或XC表达,4.6判约束必入XC,缺失补)；⑤分支穿透(T/XC/BR三层,回填coverage)；⑥structural一致性(父→子方向/无N:1/无因果/联动约束成立/management_dimension均复核)；⑦transition_relations一致性(方向与transitions一致/trigger·trigger_source必填/evidence符4.5/bidi_coupling时structural反向A→B/structural A→B且B驱动A时必有B→A)；⑧composition同步性(composition+business_ownership的A→B,若B创建转换preconditions引用A外实体后期状态→降级reference)；⑨跨模块对账(矛盾→note.conflict,warnings)；⑩字符安全(P1,json.loads验证,扫描残留箭头/弯引号/未转义<>&)；⑪空值规范(P2,source_ref例外非空)；⑫operations完整性(P13:六枚举合法/source_ref非空/expected_results≥1原文措辞/session·ui·file·query·config类未误入transitions/crud类回填T-xxx/无同实体同名重复)；⑬direction完整性(必填/from=null创建必forward/resume时from为侧挂/lateral时to为侧挂/backward时to索引<from除非环状注明)。

## 6. 中断与输出协议
正常→输出单个完整 JSON，严格遵循 Schema，除 JSON 与断点锚点外不输出解释。critical→立即停，仅输出 `{"_meta":{"version":"19.2","generated_at":"...","source":"...","has_critical_ambiguity":true,"ambiguity_list":[...]}}`，豁免完整 Schema；澄清后从触发步骤重跑，被确认假设清除 inferred 并更新 ambiguity_list。minor→不暂停，假设填充+inferred:true+ambiguity_list(severity=minor)，ambiguity 对象{amb_id,severity,concept,description,assumption,suggestion}。截断续传(可选)：优先单次完整；超限时在完整子对象边界截断，输出锚点"断点位置: Step{N} | 已完成:{对象ID} | 下一个待处理:{对象ID及未完成字段}"，收到"继续"续输出，完成后提示拼接。