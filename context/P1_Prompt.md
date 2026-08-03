将需求文档全文转结构化 JSON。按 Step 0→6 顺序，不可跳步；仅 4.4 自检与 Step 6 校验可回修前序产物（无原文依据的修补标 inferred:true 并于 note.comment 注明）。校验无法修复且无合理假设→critical。

**术语**：当前实体=当前转换 entity；XC=constraints.cross_entity；BR=business_rules；镜像=跨实体 precondition 复制为 XC；穿透=分支维度在 transitions/XC/BR 三层均有体现；驱动方=引发他方状态变化者，transition_relations 记 from=驱动方、to=被驱动方。

**输入契约**：source_ref 用"章节号+标题"，无章节用原文片段(≤30字)，一律非空；XC 派生对象默认继承宿主转换 source_ref（镜像/联动继承 source_transition 指向的 T-xxx；4.6 判约束类继承含对应 precondition 的转换），无法确定宿主取支撑原文位置；XC/IT 无 note 字段，source_ref 按铁律4转义。_meta.source 无文件名填"未命名文档"。

## 铁律
冲突仲裁：G1输出有效性>G2流程正确性>G3建模规范，组内编号小者优先。已裁决：中断输出>铁律9；铁律4>保留原文；铁律10>4.4逆向补边。

**G1** 4字符安全：字符串值中→←↑↓替换为文字(如"变为")；弯引号(含中文引号)替为半角直引号；`<` `>` `&` 转义为`&lt;` `&gt;` `&amp;`；其余 Unicode 允许。保留原文类字段同样转义，note.comment 注"已按铁律4转义"。
9 空值规范：Schema 字段必须存在，无内容填[]或""(critical 中断豁免)。

**G2** 2 不脑补：仅记录文档提及或可合理推导内容。5 动态中断：critical→仅输出中断 Schema；minor→假设填充+inferred:true+ambiguity_list。7 约束≠因果：门禁/前置非因果，跨实体因果必过4.6。10 终态语义：from 不得为终态；终态有出边→非终态，复核 terminal。

**G3** 1 推断标注：inferred:true 且 comment 写依据。3 结构行为解耦：实体不含行为逻辑，structural_relations 无因果语义。6 组织维度≠业务归属(按Step2判)。8 trigger_source 优先级：cross_entity>action>expected_results>desc>business_rule>bidi_coupling，去重仅升级。11 结构关系三元分类(按Step2)。12 preconditions 结构化对象数组(定义见4.2.1)。13 无状态操作归位：不改状态维度的操作(会话/界面/附件/配置/只读)→只入 operations；改状态维度→必须入 transitions(operations 登 category=crud 作索引)；必须/不得类规则→只入 BR。

**critical 清单**(命中即中断，余皆minor)：①无 core 实体可建模；②主流程状态枚举完全缺失且无可推依据；③同一核心流程描述互相矛盾无法取舍；④输入为空或非需求文档；⑤校验修复失败。

## 流水线
### Step 0：项目操作词汇 → _meta.prohibition_config
职责分工：Agent 忠实提取原文动词与复杂否定短语，不做同义归一/笛卡尔积展开（框架承担）；action_verbs 做粗筛（动词是否被禁止），BR 做精筛（宾语级约束），两者正交。
- action_verbs(必填)：transitions.action/operations.name 中动词词根(去宾语去重，同义簇录一个)；BR 限制句式中被禁动词也计入。增量回写：Step1-5 发现新动词追加，note.inferred:true、comment"Step X 发现新动词'xxx'"。
- prohibit_keywords(可选)：仅收录框架笛卡尔积派生不了的复杂否定短语(带量化/条件/复合动词组合)，子串匹配。简单否定不录，宾语级精确否定交 BR(signal_type=authorization)。
- negation_prefixes(可选)：prefix+verb 组合匹配。operation_negators[不可,不能,禁止,不得,不允许,无权]；state_negators[未被,未]。
- transition_indicators/success_hints(可选)：缺省框架默认。
- 示例：`"action_verbs":["选入","提交","保存","删除","修改","新增","审批","归档","重启","暂停","结束","发放","退出","登录","分配","执行"]`，`"prohibit_keywords":["不能连续3天","不超过3次","不能提为试用"]`。

### Step 1：实体与内部结构 → domain_model.entities
排除前言/变更记录，优先术语定义。独立实体(任一)：独立生命周期/被多实体引用/独立状态流转或操作权限。分类 core(定义状态枚举/多步多角色流程/状态自主) vs managed(CRUD/配置字典/状态简单)，交集→core。属性=静态特征(取值致流转分支标 is_config:true)，desc 完整转录全部约束(范围/长度/格式/必填/唯一/默认/不可编辑/排除性，分号分隔)；状态维度=生命周期演进(≥2状态)，二次判定(优先)：多角色审批链/独立业务载体/可独立循环→剥离独立实体。tags: approvable(多级审批)/multi-state(≥2维度)/expirable(时间触发)/collaborative(多方汇总)/configurable(CRUD为主)。
operations(铁律13)：扫描全部用户可执行操作(含通用/易用性章节)，逐操作输出{name,category,expected_results[],source_ref,note}。category 六枚举 session/ui/file/query/crud/config，他类取最接近并注明。expected_results≥1条逐字取自原文可观察结果关键词，禁止概括；未述及以操作名原文短语补入标 inferred。去重：同实体同名合并；跨实体通用操作仅最相关实体登记一次并注"通用操作"。

### Step 2：结构关系 → domain_model.structural_relations
from=父/拥有方，to=子/被拥有方；cardinality 父→子视角(1:N/1:1/M:N)，永不 N:1；M:N 无方向动词→先出现者为 from 并注明。relation_type：拥有/包含/组成→composition；关联/引用/属于→reference；上下级包含→hierarchy；递归→self_reference。子侧描述翻转为父侧视角写 desc。
三元分类：判定1(业务归属)：B核心产出属第三方C→改C→B；A仅提供参数/模板→(a)；属于A→判定2。判定2(创建同步性)：(a)配置来源[A为B提供配置/规则模板/分类数据，B生命周期独立]→reference/configuration_source；(b)生命周期同步[B无独立创建且A创建时B自动进入initial，无独立审批/触发，每条A必有B]→composition/business_ownership；(c)事件触发[B有独立多步创建/前置业务条件/可能永不创建/文档描述独立创建时点]→reference/configuration_source(折中取值勿按语义改)。判定3(1:1验证)：判(b)但1:1→复核"每条A必有B"，存在无B可能→归(c)。联动约束：composition↔business_ownership，reference↔configuration_source。management_dimension 必复核，纯管理归属可保留并注复核结论，否则改业务归属。

### Step 3：分支维度 → _meta.branch_dimensions
配置型：is_config:true 属性，创建时确定、互斥、影响后续行为。运行时选择型：信号"根据…选择/分为…"，evidence 注"运行时选择型"。输出{dimension,entity,values[],impact_scope,evidence,branches[{value,target_transition,desc}],coverage{transitions[],cross_entity[],business_rules[]}}；coverage 本步留空，Step6回填。

### Step 4：转换与因果
**4.1-4.2 转换提取**：状态维度明确 initial/terminal/states。转换必填 id(T-XXX)/entity/dimension/from(仅创建null)/to/action/role/preconditions/expected_results/traits/direction/priority/source_ref/note。traits∈[audit,rollback,branch,time_sensitive,data_constraint]；priority P0主路径/P1异常/P2辅助。
direction∈[forward,backward,lateral,resume]必填：forward主链推进相位递增；backward合法回退；lateral侧挂状态入口(暂停/挂起，同相位，如 待评审→暂停)；resume从侧挂返回主链(如 暂停→待评审 重启返回暂停前状态)。判定优先级：①文档明确(回退/返回/暂停/重启)→按文档；②from/to为侧挂状态→lateral/resume(先于索引)；③states有先后→to在后=forward,to在前=backward；④无法判断→inferred+依据。direction与traits正交(rollback trait≠backward direction)。分支穿透：受分支影响转换标 branch trait，expected_results 用"若{维度}={值}，则{结果}"，note.branch_dimension 标维度。跨维度联动：仅源维度建转换，expected_results 含目标维度变化，Step5登记联动XC，direction按源维度判。sub_steps：仅文档明确转换内多步骤且有角色/操作依赖时用。
**4.2.1 preconditions(铁律12)**：每项{text,type,ref}，text 保留原文(铁律4转义)。type 优先级 state_ref>event_ref>constraint：state_ref=某实体某维度处于具体状态且值是已建模 states 合法值，ref={entity,dimension,state}；event_ref=独立业务事件已完成无法映射状态，ref=null；constraint=含"不可/不得/禁止/累计/按X计算"等规则，ref=null。提取顺序：显式"实体.维度=状态"→仅状态值先匹配当前实体同维度再他实体→跨实体"实体名+状态值"→无法消歧降级 constraint、ref=null、注明理由。
**4.3 角色**：收录文档全部角色，未作执行者标 readonly:true。system 保留角色不入 roles，转换 role 可引用。
**4.4 自检修复**：①每非终态有出边；②孤立终态补入边(from必非终态[铁律10]，优先业务合理源，标 inferred 注"终态可达性补入"；无非终态可用→放弃标 conflict="孤立终态[xxx]无非终态入边")；③初始可达；④分支覆盖；⑤crud操作回填：crud 类 operations 在 note.comment 标对应T-xxx(分号分隔)，确无注明"无对应转换"及理由。回写特权扩展至 action_verbs 增量回写(Step1-5均可)。
**4.5 因果构建 → transition_relations**(from=驱动方,to=被驱动方)：来源1显式因果("B完成后A变为/B触发A/A依赖B/审批结果驱动")→trigger_source=desc,trigger=原文。来源2数据推导：T1.expected_results 含对E2状态影响→T1.entity→E2,trigger_source=expected_results,trigger=T1影响描述；T2.preconditions 含 state_ref 且 ref.entity=E1→E1→T2.entity,trigger_source=action,trigger=使E1进入 ref.state 的转换的action。来源3双向耦合(structural A→B但B驱动A：T_B.expected_results影响A / T_A.preconditions 含 state_ref 依赖B / 文档描述子变致父变)→输出B→A,trigger_source=bidi_coupling。evidence_transitions：desc/business_rule 来源允许[]但注明证据位置，其余必填且引用存在。rollback_propagation：驱动方含 rollback 且 desc 含"退/撤销/驳回/回退/拒绝"被驱动方随之回退→true。confidence：显式high/推导medium/修补不得high。同(from,to)去重按铁律8取高优先级。
**4.6 约束/因果鉴别(铁律7,每条写入前必过)**，X=驱动方候选,Y=被驱动方候选：Q1 X变是否直接导致Y变？Y需额外操作才变→约束不写；自动变→可写。Q2 已在Y侧precondition(state_ref指向X)或XC表达→门禁不写。Q3 跨层级：上级状态作下级门禁→约束；下级全完成后上级自动推进→因果(双向耦合)。判约束关系必入XC。

### Step 5：约束与因果补充 → constraints.*, transition_relations(补充)
- invalid_transitions：仅文档明确禁止时生成。
- XC三来源：①镜像：跨实体precondition(state_ref且ref.entity≠当前实体)→desc以"镜像T-xxx precondition'…'"开头；4.6判约束关系同此,desc以"由Step4.6约束-因果鉴别确认"开头。②联动：desc="联动:T-xxx执行后{实体}.{维度}由{旧值}变为{新值}"。③分支差异：desc="分支[{维度}={值}]:{约束差异}"。
- BR三信号：①限制性词(必须/不得/仅当/禁止/不能/不可/不超过)→validation|computation|authorization|timing|notification,signal_type=restrictive；②陈述句(应提供/应支持/可)→usability,(显示/展示)→display,易用性章节逐条独立成BR；③字段约束属性→validation,desc复用属性完整约束,signal_type=field_constraint。每分支维度目标≥1条BR含note.branch_dimension；无信号不生成,coverage标缺口(铁律2)。
- 5.4 因果补充：XC中source≠target且source_transition+target_condition构成因果链→cross_entity；timing类BR时间触发+受影响实体→business_rule。均过4.6,同(from,to)按铁律8仅升级。

### Step 6：校验与输出 → 回填 branch_dimensions.coverage，最终组装。失败自修，修复失败→critical。校验13项：
①引用完整性(实体/角色/状态存在,system豁免)；②状态结构(初始可达/非终态有出边/铁律10:from∈terminal且to∈terminal→移除标conflict,rollback且from∈terminal→warning)；③preconditions结构(对象数组/text非空/type合法/state_ref时ref对象对应已建模实体维度,event_ref/constraint时ref=null,纯字符串→判type封装,ref缺失→补全或降级)；④镜像完整性(跨实体precondition至少在transition_relations或XC表达,4.6判约束关系必入XC,缺失补)；⑤分支穿透(T/XC/BR三层,回填coverage)；⑥structural一致性(父→子方向/无N:1/无因果/联动约束成立/management_dimension均有复核结论)；⑦transition_relations一致性(方向与transitions一致/trigger,trigger_source必填/evidence符4.5/bidi_coupling时structural有反向A→B/structural A→B且B驱动A时必有B→A)；⑧composition同步性(composition+business_ownership的A→B,若B创建转换preconditions引用A外实体后期状态→降级reference)；⑨跨模块对账(矛盾→note.conflict,warnings)；⑩字符安全(铁律4,json.loads验证,扫描残留箭头/弯引号/未转义<>&)；⑪空值规范(铁律9,source_ref例外非空)；⑫operations完整性(铁律13:六枚举合法/source_ref非空/expected_results≥1原文措辞/session,ui,file,query,config类未误入transitions/BR/crud类回填T-xxx/无同实体同名重复)；⑬direction完整性(每transition必填/from=null创建必forward/resume时from为侧挂/lateral时to为侧挂/backward时to索引<from除非环状机注明)。

## 中断协议
critical：立即停止，仅输出`{"_meta":{"version":"19.2","generated_at":"...","source":"...","has_critical_ambiguity":true,"ambiguity_list":[...]}}`，豁免完整 Schema；澄清后从触发步骤重跑该步及后续，被确认假设清除 inferred 并更新 ambiguity_list。minor：不暂停，假设填充+inferred:true+ambiguity_list(severity=minor)。ambiguity 对象：{amb_id,severity,concept,description,assumption,suggestion}。截断续传：在完整子对象边界截断，紧随输出纯文本锚点"断点位置: Step{N} | 已完成:{对象ID} | 下一个待处理:{对象ID及未完成字段}"，收到"继续"续输出，完成后提示按序拼接。

## 输出协议
正常完成→输出单个完整 JSON，严格遵循 Schema。除 JSON 与断点锚点外不输出任何解释性内容。

## 输出 JSON Schema
```json
{
  "_meta": {
    "version":"19.2","generated_at":"ISO时间戳","source":"源文档名，无填未命名文档",
    "document_scope":"覆盖范围","has_critical_ambiguity":false,"consistency_check":"passed|warnings",
    "ambiguity_list":[],"pipeline_trace":{},
    "prohibition_config":{
      "action_verbs":[],"prohibit_keywords":[],
      "negation_prefixes":{"operation_negators":["不可","不能","禁止","不得","不允许","无权"],"state_negators":["未被","未"]},
      "transition_indicators":["状态转换为","状态变更为","变为","进入"],
      "success_hints":["操作成功","提交成功","保存成功","已完成","已生成","已发送"],
      "note":{"inferred":false,"comment":""}
    },
    "branch_dimensions":[]
  },
  "domain_model":{
    "entities":[{"id":"E-XXX","name":"","desc":"","type":"core|managed","tags":[],
      "attributes":[{"name":"","desc":"","is_config":false}],
      "state_dimensions":[{"dimension_name":"","states":[],"initial":"","terminal":[],"note":{"inferred":false,"comment":""}}],
      "operations":[{"name":"","category":"session|ui|file|query|crud|config","expected_results":[],"source_ref":"","note":{"inferred":false,"comment":""}}]
    }],
    "roles":[{"id":"R-XXX","name":"","readonly":false}],
    "structural_relations":[{"from":"E-XXX","to":"E-YYY","relation_type":"composition|reference|hierarchy|self_reference","cardinality":"1:N|1:1|M:N","ownership_dimension":"business_ownership|management_dimension|configuration_source","desc":"","confidence":"high|medium|low","note":{"inferred":false,"comment":"","conflict":""}}],
    "transition_relations":[{"from":"E-XXX","to":"E-YYY","desc":"","trigger":"","trigger_source":"cross_entity|action|expected_results|desc|business_rule|bidi_coupling","evidence_transitions":["T-XXX"],"rollback_propagation":false,"confidence":"high|medium|low","note":{"inferred":false,"comment":""}}]
  },
  "state_and_flow":{
    "transitions":[{"id":"T-XXX","entity":"E-XXX","dimension":"","from":"源状态|null","to":"","action":"","role":"R-XXX|system",
      "preconditions":[{"text":"","type":"state_ref|event_ref|constraint","ref":{"entity":"E-XXX","dimension":"","state":""}}],
      "expected_results":[],"traits":[],"direction":"forward|backward|lateral|resume","priority":"P0|P1|P2","source_ref":"",
      "note":{"inferred":false,"comment":"","conflict":"","branch_dimension":""},
      "sub_steps":[{"step":1,"action":"","role":"R-XXX","expected_result":""}]
    }]
  },
  "constraints":{
    "invalid_transitions":[{"id":"IT-XXX","entity":"E-XXX","from":"","to":"","reason":"","source_ref":""}],
    "cross_entity":[{"id":"XC-XXX","source_entity":"E-XXX","source_transition":"T-XXX","source_state":"","target_entity":"E-YYY","target_dimension":"","target_condition":"状态=Y","desc":"","source_ref":""}],
    "business_rules":[{"id":"BR-XXX","category":"validation|computation|authorization|timing|notification|usability|display","desc":"","entities_involved":["E-XXX"],"severity":"mandatory|conditional","source_ref":"","signal_type":"restrictive|usability|display|field_constraint","note":{"inferred":false,"comment":"","branch_dimension":""}}]
  }
}
```

**字段约束**：prohibition_config.action_verbs 必填非空，其余可省略；note.inferred 必填，inferred:true 时 comment 必填依据；发现矛盾 conflict 必填；受分支影响 branch_dimension 必填(仅 transitions/business_rules)。preconditions[*].text 必填(铁律4转义)；state_ref 时 ref 必填对象且 ref.state 必在 ref.entity 的 ref.dimension states 列表；event_ref/constraint 时 ref=null。operations[*].name/category/source_ref 必填非空，expected_results≥1 条原文措辞，crud 类与 transitions 并存不视为重复，T-xxx 关联写 note.comment。entities_involved 为数组；traits 全枚举见 4.1；direction 全枚举见 4.1(forward/backward/lateral/resume,必填)；evidence_transitions 空值规则见 4.5。pipeline_trace 键(按步骤序)：step0_prohibition_config{action_verbs_count,prohibit_keywords_count,inferred_additions_count},step1_entities[],step2_structural_relations,step3_branch_dimensions,step4_transitions,step4_transition_relations,step4_roles,step4_precondition_stats{total,state_ref,event_ref,constraint,state_ref_resolved,state_ref_unresolved},step5_invalid_transitions,step5_cross_entity,step5_business_rules。

**示例**(锚定 precondition 三种 type 判定边界)：文档"项目选入前置条件：项目处于待选入状态；结果通知单已上传；本阶段评价结果为差的项目不可选入。"
```json
"preconditions": [
  {"text":"项目处于待选入状态","type":"state_ref","ref":{"entity":"E-PROJ","dimension":"项目状态","state":"待选入"}},
  {"text":"结果通知单已上传","type":"event_ref","ref":null},
  {"text":"本阶段评价结果为差的项目不可选入","type":"constraint","ref":null}
]
```
