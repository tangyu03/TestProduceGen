将需求文档全文转化为结构化 JSON。按 Step 1→6 顺序执行，不可跳步；仅 4.4 自检与 Step 6 校验阶段允许回修前序产物（无原文依据的修补标 inferred:true 并在 note.comment 注明理由）；校验无法修复且无合理假设 → 按 critical 歧义处理。

**术语**：当前实体=当前转换的 entity 值；XC=constraints.cross_entity；BR=business_rules；镜像=将跨实体 precondition 复制生成 XC；穿透=分支维度在 transitions/XC/BR 三层均有体现；驱动方=引发他方状态变化的一方，transition_relations 记 from=驱动方、to=被驱动方。

**输入契约**：source_ref 用"章节号+标题"，无章节用原文片段（≤30 字），一律非空（不适用铁律 9 的空串填充）；XC 为派生对象，默认继承宿主转换的 source_ref（镜像/联动类继承 source_transition 指向的 T-xxx，4.6 判约束类继承含对应 precondition 的转换），无法确定宿主时按通用格式取支撑原文位置；XC/IT 无 note 字段，source_ref 按铁律 4 转义但免写注明。_meta.source 无文件名填"未命名文档"。


---

## 铁律

冲突仲裁：G1 输出有效性 > G2 流程正确性 > G3 建模规范，组内编号小者优先。
已裁决结论（直接执行）：中断输出 > 铁律 9；铁律 4 > "保留原文"；铁律 10 > 4.4 逆向补边。

**G1**
- 4 字符安全：字符串值中箭头符号（→←↑↓）替换为文字（如"变为"）；弯引号（含中文引号）替换为半角直引号；`<` `>` `&` 转义为 `<` `>` `&`；其余 Unicode 允许。保留原文类字段同样转义，并在 note.comment 注明"已按铁律4转义"。
- 9 空值规范：Schema 字段必须存在，无内容填 [] 或 ""（critical 中断输出豁免）。

**G2**
- 2 不脑补：仅记录文档提及或可合理推导（有间接描述或状态枚举可推）的转换与关系。
- 5 动态中断：critical 歧义→立即暂停，仅输出中断 Schema；minor→最合理假设填充 + inferred:true + 写 ambiguity_list。
- 7 约束≠因果：门禁/前置条件不是因果；每条跨实体因果写入前必须过 4.6 鉴别。
- 10 终态语义：任何转换 from 不得为终态；文档称终态有出边 → 该状态非终态，复核 terminal。

**G3**
- 1 推断标注：inferred:true 且 note.comment 写明依据。
- 3 结构行为解耦：实体不含行为逻辑；structural_relations 无因果语义。
- 6 组织维度≠业务归属（按 2.3 判定）。
- 8 trigger_source 优先级：cross_entity > action > expected_results > desc > business_rule > bidi_coupling（左端为高）；去重合并仅升级不降级。
- 11 结构关系三元分类（按 2.3）。
- 12 preconditions 必须为结构化对象数组（含 text/type/ref），不得为纯字符串数组（定义按 4.2.1）。
- 13 无状态操作归位：不改变实体状态维度的操作（会话/界面/附件/配置/只读）→ 只入 operations；改变实体状态维度的操作 → 必须入 transitions（operations 登记 category=crud 作索引，不视为重复）；必须/不得类规则 → 只入 BR。

**critical 清单**（命中其一即中断，其余一律 minor）：①无 core 实体可建模；②主流程状态枚举完全缺失且无可推依据；③同一核心流程描述互相矛盾无法取舍；④输入为空或不是需求文档；⑤校验修复失败。

---

## 流水线

### Step 1：实体与内部结构 → domain_model.entities
（roles 在 4.3 汇总，本步不建）
- 排除前言/变更记录，优先采纳术语定义，扫描名词性概念。
- 独立实体判定（任一）：独立生命周期 / 被多实体引用 / 独立状态流转或操作权限。
- 分类：core=定义状态枚举/多步骤多角色流程/状态自主；managed=管理员 CRUD/配置字典/状态简单。交集 → core。
- 属性=静态特征（取值导致流转分支的标 is_config:true）；状态维度=生命周期演进（≥2 状态）。
- 属性 desc 完整转录全部约束（范围/长度/格式/必填/唯一/默认值/不可编辑/排除性，多条款分号分隔）。
- 状态维度二次判定（优先于初步结论）：多角色审批链 / 独立业务载体 / 可独立循环 → 剥离为独立实体。
- tags：approvable（多级审批）/multi-state（≥2 维度）/expirable（时间触发）/collaborative（多方汇总）/configurable（CRUD 为主）。
- operations 提取（铁律 13）：扫描文档全部用户可执行的功能操作（含通用功能/易用性章节），逐操作输出 {name, category, expected_results[], source_ref, note}；仅记录文档提及的操作（铁律 2），推断标 inferred:true 并注明依据。
  - category 六枚举：session=会话操作（登录/注销/修改密码）；ui=纯前端交互（排序/分页/重置/菜单收起展开）；file=附件操作（上传/下载附件）；query=只读查询（查看/查询/搜索）；crud=实体增删改（transitions 已覆盖的）；config=配置参数管理（超时/限值设置）。不属六类取最接近者并在 note.comment 注明理由。
  - expected_results ≥1 条，逐字取自原文的可观察结果关键词（成功/失败/提示语均收，如"登录成功""附件格式不符提示"），禁止概括改写（供下游覆盖矩阵命中）；原文未述及结果时以操作名原文短语补入并标 inferred:true。
  - 去重：同实体同名操作合并；跨实体通用操作仅在最相关实体登记一次并在 note.comment 注明"通用操作，适用多实体"，其余实体不重复登记。

### Step 2：结构关系 → domain_model.structural_relations
- 方向：from=父/拥有方，to=子/被拥有方；cardinality 为父→子视角（1:N/1:1/M:N），永不 N:1。M:N 无方向动词 → 按叙述顺序先出现者为 from 并注明。
- relation_type 信号：拥有/包含/组成→composition；关联/引用/属于→reference；上下级包含→hierarchy；递归→self_reference。子侧描述翻转为父侧视角。
- 三元分类（铁律 11）：
  - 判定 1（业务归属）：B 核心产出属第三方 C → 改 C→B；A 仅提供参数/模板 → (a) 类；属于 A → 判定 2。
  - 判定 2（创建同步性）：

  | 类别 | 信号 | relation_type | ownership_dimension |
  |------|------|---------------|---------------------|
  | (a) 配置来源 | A 为 B 提供配置/规则模板/分类数据，B 生命周期独立 | reference | configuration_source |
  | (b) 生命周期同步归属 | B 无独立创建流程且 A 创建时 B 自动进入 initial；B 无独立审批/触发；每条 A 必有 B | composition | business_ownership |
  | (c) 事件触发归属 | B 有独立多步创建流程/前置业务条件/可能永不创建/文档描述独立创建时点 | reference | configuration_source（枚举受限的折中取值，勿按语义改值） |

  - 判定 3（1:1 验证）：判为 (b) 但 1:1 → 复核"每条 A 必有 B"；存在无 B 可能 → 归 (c)。
- 联动约束：composition↔business_ownership，reference↔configuration_source。management_dimension 必须复核，确认纯属管理归属可保留并在 note.comment 写复核结论，否则改业务归属值。

### Step 3：分支维度 → _meta.branch_dimensions
- 配置型：is_config:true 属性，创建时确定、互斥、影响后续行为。运行时选择型：信号"根据…选择/分为…情况"，evidence 注明"运行时选择型"。
- 输出 `{dimension, entity, values[], impact_scope, evidence, branches[{value, target_transition, desc}], coverage:{transitions[], cross_entity[], business_rules[]}}`；coverage 本步留空，Step 6 回填。

### Step 4：转换与因果 → state_and_flow.transitions, domain_model.transition_relations, domain_model.roles
**4.1-4.2 转换提取**
- 状态维度明确 initial/terminal/states。转换必填：id(T-XXX)、entity、dimension、from（仅创建为 null）、to、action、role、preconditions、expected_results、traits、direction、priority、source_ref、note。
- traits ∈ [audit, rollback, branch, time_sensitive, data_constraint]；priority：P0 主路径/P1 异常分支/P2 辅助。
- **direction** ∈ [forward, backward, lateral, resume]（必填，不可省略）：
  - `forward`：主链推进，相位递增。
  - `backward`：合法回退，回到业务流程中更早的状态。
  - `lateral`：侧挂状态入口，进入主链之外的暂停/挂起状态（如 待评审→暂停、评审中→暂停）。侧挂状态不推进相位，与源状态同相位。
  - `resume`：从侧挂状态返回主链（如 暂停→待评审 重启返回暂停前状态）。
  - **判定优先级**：①文档明确描述方向（"回退/返回/暂停/重启"等）→ 按文档；②文档未明确但 from/to 状态在 states 列表中有明确先后顺序 → to 在 from 之后=forward，to 在 from 之前=backward；③无法从文档或状态顺序判断 → 标 inferred:true 并在 note.comment 写明判定依据。
  - **与 traits 的关系**：direction 和 traits 是两个正交维度——traits 描述"这个迁移有什么业务特征"（如 audit 需审计），direction 描述"这个迁移在状态机拓扑上往哪个方向走"。rollback trait 不等于 backward direction（一个 rollback trait 的转换可能是 backward 也可能是 resume，取决于它是回到更早状态还是从侧挂返回）。
- 分支穿透：受分支影响的转换标 branch trait；expected_results 用条件句"若 {维度}={值}，则 {结果}"（多分支多条）；note.branch_dimension 标维度名。
- 跨维度联动：仅在源维度建转换，expected_results 含目标维度变化，Step 5 登记联动 XC。联动转换的 direction 按源维度判定。
- sub_steps：仅文档明确转换内部多步骤且有角色/操作依赖时使用。

**4.2.1 preconditions 结构化（铁律 12）**：每项 `{text, type, ref}`，text 保留原文（按铁律 4 转义）。
- type 判定优先级 state_ref > event_ref > constraint：
  - state_ref：某实体某维度处于具体状态，且该值是已建模 states 合法值；
  - event_ref：独立业务事件已完成，无法映射到具体状态；
  - constraint：含"不可/不得/禁止/累计/按 X 计算"等规则描述。
- ref 仅 state_ref 填 `{entity, dimension, state}`，其余为 null。提取顺序：显式"实体.维度=状态"→ 仅状态值时先匹配当前实体同维度、再匹配他实体同维度 → 跨实体"实体名+状态值"→ 状态值不存在或无法消歧则降级 constraint、ref=null、note.comment 注明降级理由。

**4.3 角色**：收录文档提及的全部角色，未作执行者的标 readonly:true。`system` 为保留角色不入 roles，转换 role 可引用 system，引用校验豁免。

**4.4 自检修复**：①每个非终态有出边；②孤立终态补入边：from 必须非终态（铁律 10），优先业务合理源状态，补入转换标 inferred:true 并注明"终态可达性补入"；无非终态可用 → 放弃并标 note.conflict="孤立终态[xxx]无非终态入边"；③初始可达；④分支覆盖；⑤crud 操作回填：category=crud 的 operations 在 note.comment 标注对应转换 T-xxx（多个分号分隔），确无对应转换的注明"无对应转换"及理由。

**4.5 因果构建 → transition_relations**（from=驱动方，to=被驱动方）
- 来源 1 显式因果：扫描"B 完成后 A 状态变为/B 触发 A/A 依赖 B 完成/审批结果驱动"等句式 → trigger_source=desc，trigger 填原文描述。
- 来源 2 数据推导：

  | 信号 | from→to | trigger_source | trigger 取值 |
  |------|---------|----------------|--------------|
  | T1.expected_results 含对实体 E2 状态的影响 | T1.entity→E2 | expected_results | T1 中的影响描述 |
  | T2.preconditions 含 type=state_ref 且 ref.entity=E1 | E1→T2.entity | action | 使 E1 进入 ref.state 的转换的 action |

- 来源 3 双向耦合：structural A→B 但 B 驱动 A（信号：T_B.expected_results 影响 A / T_A.preconditions 含 state_ref 依赖 B / 文档描述子变致父变）→ 输出 B→A，trigger_source=bidi_coupling。
- evidence_transitions：trigger_source=desc/business_rule 时允许 [] 但 note.comment 注明证据位置；其余来源必填且引用存在。
- rollback_propagation：驱动方含 rollback、desc 含"退/撤销/驳回/回退/拒绝"、被驱动方随之回退 → true。
- confidence：显式=high，推导=medium，修补产物不得 high。同 (from,to) 去重，按铁律 8 取高优先级。

**4.6 约束/因果鉴别（铁律 7，每条写入前必过）**，X=驱动方候选，Y=被驱动方候选：
- Q1：X 变是否直接导致 Y 变？Y 需额外操作才变 → 约束，不写入；自动变 → 可写入。
- Q2：已在 Y 侧转换的 precondition（state_ref 指向 X）或 XC 中表达 → 门禁关系，不写入。
- Q3：跨层级时，上级状态作下级门禁 → 约束；下级全部完成后上级自动推进 → 因果（双向耦合）。
- 判为约束的关系必须入 XC。

### Step 5：约束与因果补充 → constraints.*, domain_model.transition_relations（补充）
- **invalid_transitions**：仅文档明确禁止时生成。
- **XC 三来源**：①镜像：跨实体 precondition（state_ref 且 ref.entity≠当前实体）→ desc 以"镜像 T-xxx precondition '…'"开头；4.6 判约束的关系同此，desc 以"由 Step 4.6 约束-因果鉴别确认"开头。②联动：desc="联动: T-xxx 执行后 {实体}.{维度} 由 {旧值} 变为 {新值}"。③分支差异：desc="分支[{维度}={值}]: {约束差异}"。
- **BR 三信号**：①限制性词（必须/不得/仅当/禁止/不能/不可/不超过）→ validation|computation|authorization|timing|notification，signal_type=restrictive；②陈述句（应提供/应支持/可）→ usability，（显示/展示）→ display，易用性章节逐条独立成 BR；③字段约束属性 → validation，desc 复用属性完整约束，signal_type=field_constraint。每个分支维度目标 ≥1 条 BR 含 note.branch_dimension；无信号不生成，coverage 标缺口（铁律 2）。
- **5.4 因果补充**：XC 中 source≠target 且 source_transition+target_condition 构成因果链 → cross_entity；timing 类 BR 的时间触发+受影响实体 → business_rule。均须过 4.6，同 (from,to) 按铁律 8 仅升级。

### Step 6：校验与输出 → _meta.consistency_check / ambiguity_list / pipeline_trace，回填 branch_dimensions.coverage，最终组装
失败则自修，修复失败 → critical。校验清单：
1. 引用完整性：实体/角色/状态引用存在（role=system 豁免）。
2. 状态结构：初始可达；非终态有出边；终态语义（铁律 10）：from∈terminal 且 to∈terminal → 移除并标 conflict；rollback 且 from∈terminal → warning。
3. preconditions 结构（铁律 12）：对象数组、text 非空、type 合法；state_ref 时 ref 为对象且能对应已建模实体与维度；event_ref/constraint 时 ref=null。纯字符串 → 判定 type 后封装；ref 缺失 → 补全或降级。
4. 镜像完整性：每个跨实体 precondition 至少在 transition_relations 或 XC 之一有表达；4.6 判约束的关系必须入 XC。缺失则补。
5. 分支穿透：T/XC/BR 三层均有体现；回填各维度 coverage。
6. structural 一致性：父→子方向；无 N:1；无因果语义；联动约束成立；management_dimension 均有复核结论。
7. transition_relations 一致性：方向与 transitions 数据一致；trigger/trigger_source 必填；evidence 符合 4.5；bidi_coupling 时 structural 有反向 A→B；structural A→B 且 B 驱动 A 时必有 B→A。
8. composition 同步性：composition+business_ownership 的 A→B，若 B 创建转换的 preconditions 引用 A 之外实体的后期状态 → 降级为 reference。
9. 跨模块对账：同对象描述矛盾 → note.conflict 标差异，consistency_check=warnings。
10. 字符安全（铁律 4）：等效 json.loads 验证，扫描残留箭头/弯引号/未转义 <>&。
11. 空值规范（铁律 9；source_ref 例外，按输入契约必须非空）。
12. operations 完整性（铁律 13）：category 六枚举合法；source_ref 非空；expected_results ≥1 且为原文措辞；session/ui/file/query/config 类未误入 transitions/BR；crud 类已回填 T-xxx 关联；无同实体同名重复。
13. **direction 完整性**：每个 transition 必填 direction 字段（forward/backward/lateral/resume）；from=null 的创建转换必须为 forward；direction=resume 时 from 必须为侧挂状态（如暂停）；direction=lateral 时 to 必须为侧挂状态；direction=backward 时 to 的 states 列表索引应小于 from（除非环状机升级/降级边，需在 note.comment 注明"环状机"）。

---

## 中断协议
- **critical**：立即停止，仅输出 `{"_meta":{"version":"19.2","generated_at":"...","source":"...","has_critical_ambiguity":true,"ambiguity_list":[...]}}`，豁免完整 Schema。澄清后从触发步骤重跑该步及后续；被确认的假设清除 inferred 并更新 ambiguity_list。
- **minor**：不暂停，假设填充 + inferred:true + 写 ambiguity_list（severity=minor）。
- ambiguity 对象：`{amb_id, severity, concept, description, assumption, suggestion}`。
- **截断续传**：在当前完整子对象边界截断，紧随其后输出纯文本锚点：
  `断点位置: Step {N} | 已完成: {对象ID列表} | 下一个待处理: {对象ID及未完成字段}`
  收到"继续"后从锚点续输出剩余片段，全部完成后提示按序拼接。

---

## 输出协议
正常完成 → 输出单个完整 JSON，严格遵循 Schema。除 JSON 与断点锚点外不输出任何解释性内容；内部校验与修正过程不输出。

---

## 输出 JSON Schema

```json
{
  "_meta": {
    "version": "19.2",
    "generated_at": "ISO时间戳",
    "source": "源文档名称，无文件名填 未命名文档",
    "document_scope": "文档覆盖范围描述",
    "has_critical_ambiguity": false,
    "consistency_check": "passed | warnings",
    "ambiguity_list": [],
    "pipeline_trace": {},
    "branch_dimensions": []
  },
  "domain_model": {
    "entities": [{
      "id": "E-XXX", "name": "实体名", "desc": "描述",
      "type": "core | managed",
      "tags": ["approvable","multi-state","configurable","expirable","collaborative"],
      "attributes": [{ "name": "属性名", "desc": "描述", "is_config": false }],
      "state_dimensions": [{
        "dimension_name": "维度名", "states": ["状态1","状态2"],
        "initial": "状态1", "terminal": ["状态2"],
        "note": { "inferred": false, "comment": "" }
      }],
      "operations": [{ "name": "操作名", "category": "session|ui|file|query|crud|config", "expected_results": ["预期结果关键词"], "source_ref": "章节号+标题 或 原文片段", "note": { "inferred": false, "comment": "" } }]
    }],
    "roles": [{ "id": "R-XXX", "name": "角色名", "readonly": false }],
    "structural_relations": [{
      "from": "E-XXX", "to": "E-YYY",
      "relation_type": "composition | reference | hierarchy | self_reference",
      "cardinality": "1:N | 1:1 | M:N",
      "ownership_dimension": "business_ownership | management_dimension | configuration_source",
      "desc": "关系语义描述",
      "confidence": "high | medium | low",
      "note": { "inferred": false, "comment": "", "conflict": "" }
    }],
    "transition_relations": [{
      "from": "E-XXX", "to": "E-YYY",
      "desc": "驱动关系描述",
      "trigger": "触发条件",
      "trigger_source": "cross_entity | action | expected_results | desc | business_rule | bidi_coupling",
      "evidence_transitions": ["T-XXX"],
      "rollback_propagation": false,
      "confidence": "high | medium | low",
      "note": { "inferred": false, "comment": "" }
    }]
  },
  "state_and_flow": {
    "transitions": [{
      "id": "T-XXX", "entity": "E-XXX", "dimension": "维度名",
      "from": "源状态|null", "to": "目标状态", "action": "触发动作",
      "role": "R-XXX 或保留角色 system",
      "preconditions": [
        {
          "text": "前置条件原文",
          "type": "state_ref | event_ref | constraint",
          "ref": { "entity": "E-XXX", "dimension": "维度名", "state": "状态值" }
        }
      ],
      "expected_results": ["预期结果"],
      "traits": ["audit","rollback"], "direction": "forward|backward|lateral|resume", "priority": "P0|P1|P2",
      "source_ref": "章节号+标题 或 原文片段",
      "note": { "inferred": false, "comment": "", "conflict": "", "branch_dimension": "" },
      "sub_steps": [{ "step": 1, "action": "操作", "role": "R-XXX", "expected_result": "结果" }]
    }]
  },
  "constraints": {
    "invalid_transitions": [
        { "id": "IT-XXX", "entity": "E-XXX", "from": "状态A", "to": "状态B", "reason": "原因", "source_ref": "章节号+标题 或 原文片段" }
    ],
    "cross_entity": [{
      "id": "XC-XXX", "source_entity": "E-XXX", "source_transition": "T-XXX",
      "source_state": "状态X", "target_entity": "E-YYY",
      "target_dimension": "维度名", "target_condition": "状态=Y", "desc": "说明","source_ref": "章节号+标题 或 原文片段"
    }],
    "business_rules": [{
      "id": "BR-XXX", "category": "validation|computation|authorization|timing|notification|usability|display",
      "desc": "规则描述", "entities_involved": ["E-XXX"],
      "severity": "mandatory|conditional", "source_ref": "章节号+标题 或 原文片段",
      "signal_type": "restrictive|usability|display|field_constraint",
      "note": { "inferred": false, "comment": "", "branch_dimension": "" }
    }]
  }
}
```

**字段约束**：
- `pipeline_trace` 键（按步骤序）：step1_entities[], step2_structural_relations, step3_branch_dimensions, step4_transitions, step4_transition_relations, step4_roles, step4_precondition_stats{total_preconditions, state_ref_count, event_ref_count, constraint_count, state_ref_resolved_count, state_ref_unresolved_count}, step5_invalid_transitions, step5_cross_entity, step5_business_rules。
- `note` 键规范：inferred 必填；inferred:true 时 comment 必填依据；发现矛盾时 conflict 必填；受分支影响时 branch_dimension 必填（仅 transitions/business_rules）。
- `preconditions[*]`：text 必填（按铁律 4 转义）；type 必填枚举；state_ref 时 ref 必填对象且 ref.state 必须在 ref.entity 的 ref.dimension 的 states 列表中；event_ref/constraint 时 ref 必填 null。
- `operations[*]`：name/category/source_ref 必填非空；expected_results ≥1 条且逐字取自原文（补入情形见 Step 1）；crud 类与 transitions 并存不视为重复，T-xxx 关联写于 note.comment（4.4 ⑤回填）。
- `entities_involved` 为数组；`traits` 全枚举见 4.1；`direction` 全枚举见 4.1（forward/backward/lateral/resume，必填）；`evidence_transitions` 空值规则见 4.5。

---

## 示例（锚定 preconditions 三种 type 的判定边界）

文档片段："项目选入的前置条件：项目处于待选入状态；结果通知单已上传；本阶段评价结果为差的项目不可选入。"

```json
"preconditions": [
  {
    "text": "项目处于待选入状态",
    "type": "state_ref",
    "ref": { "entity": "E-PROJ", "dimension": "项目状态", "state": "待选入" }
  },
  {
    "text": "结果通知单已上传",
    "type": "event_ref",
    "ref": null
  },
  {
    "text": "本阶段评价结果为差的项目不可选入",
    "type": "constraint",
    "ref": null
  }
]
```
