读取 P1 领域模型 JSON，输出覆盖义务模型 JSON。目标：生成逻辑自洽、无冗余、可直接用于测试用例生成的覆盖义务模型。

**接口契约**：输入必须为 P1 结构化输出；preconditions 非对象数组 → 立即终止（Step 0.3），不做降级处理。下列防御性分支正常输入不触发，触发时记 judgment：P1 ref=null 的 ref 补全（2.3）、2.1 终态行、字符串 operation 兼容（1.2）。

**术语**：

| 术语 | 定义 |
|------|------|
| R | P1 domain_model.transition_relations 条目 |
| XC | P1 constraints.cross_entity 条目 |
| BD | P1 _meta.branch_dimensions 条目 |
| 当前 TO | 正在处理的 transition_obligation |
| to_index | 以 tid 为键的 TO 索引，Step 2 遍历时构建，拆分后同步更新 |
| P1 原转换 | 拆分前 P1 state_and_flow.transitions 中的转换；派生 dimension/to/source_ref 时以此为准，避免拆分后取到任意分支 |
| 保留方 | CO 合并时保留的一方：confidence 高者优先，并列取 ID 小者 |
| 车道 | CO 的三条生成路径：constraint / auto / lifecycle |

---

## 核心规则

1. **ID**：EO-ATC-NNN、EO-CRU-NNN、CO-NNN、RO-IT-NNN、RO-BR-NNN 重新编号；TO 沿用 P1 tid，拆分加后缀 [a]~[p]。
2. **异常处理**：未定义边界优先保留数据，转 BR 优于跳过；记录 judgment/warning，禁止静默丢弃。
3. **输出**：严格遵循「输出 Schema 字段清单」，禁止省略必填字段，空值用 [] 或 null。
4. **转义**：输出 JSON 文本中 `<` `>` `&` 转义为 `<` `>` `&`。
5. **suggested_action** 只描述"对哪个对象执行什么操作"，不写预期结果。
6. **source_ref 溯源**：所有义务对象统一输出 source_ref 字段，无来源置 null。
   - 透传：TO 透传 P1 transition.source_ref；EO-CRU 透传 P1 operations[].source_ref；CO 的 constraint 车道与 auto 车道 XC 联动类透传 XC.source_ref；RO-IT 透传 IT.source_ref；RO-BR 透传 BR.source_ref（由 XC 转换生成的 RO-BR 改透传 XC.source_ref）。透传不二次转义（P1 已按铁律 4 处理）。
   - 派生：auto 车道 R 来源的 CO，取 R.evidence_transitions 首条指向的 P1 原转换的 source_ref。
   - 置 null + judgment：EO-ATC（P1 属性无此字段）、EO-CRU 兼容分支（字符串 operation 无此字段）、lifecycle 车道 CO（SR 无此字段）、R 来源且 evidence_transitions 为空。
   - CO 合并时 source_ref 取保留方，被合并方值不同则以分号连接去重并入。
   - 防御：P1 输入缺失 source_ref 不视为致命错误，按置 null + judgment 处理，不终止。


## 核心原则

- **R1 最小必要拆分**：分支维度（取值影响 from/to/action/preconditions/expected_results，如项目阶段、评级）→ 触发拆分；配置属性（仅影响内部计算，如评审组人数、技术领域、超时设置）→ 不拆分，note 标注。拆分仅在组合间上述字段存在实质差异时进行（判定前置，见 2.4）。
- **R2 (E,D,S) 三元组验证**：enabler_state 必须是 state_info 中的合法状态值；"按4.5(5)归档""累计10次优"等非状态值 → 强制转 BR，不生成 CO。
- **R3 XC 前置分类**：处理 CO 前，将所有 XC 按 desc 模板分流（仅候选，终判归 R4）：
  - "镜像 T-" 或 "由 Step 4.6 约束-因果鉴别确认" 开头，或含"前置条件/门禁" → 状态门禁类（constraint 车道）
  - "联动: T-" 开头，或含"触发/联动" → 因果联动类（auto 车道）
  - "分支[" 开头 → 业务规则类（已由 TO 拆分覆盖，转 BR）
  - 含"累计/计算/公式/评级/归档"或无法判定 → 转 BR（Step 4.2.1）
- **R4 causal_type 终判**（R3 只做候选分流，R4 做生成前终判，冲突以 R4 为准，判不过转 BR）：
  - `constraint`（状态门禁）：enabler 状态在 dependent 转换的 preconditions 中有明确引用（存在 type=state_ref 且 ref 指向 enabler 的项）。能回答："因为 enabler 到了状态 S，所以 dependent 被允许执行 T"。
  - `auto`（因果联动）：文档或逻辑明确"联动/触发"，dependent 发生自动的、系统驱动的状态变更。能回答："因为 enabler 到了状态 S，所以 dependent 自动执行了 T"。
  - 兜底：其余一律禁止 constraint/auto，强制转 BR（如依赖累计次数/计算公式/动态评级/人工归档等无法解析为状态引用的逻辑）。
- **R5 语义过滤**：拆分组合前过滤无效组合，证据仅限 P1 产物（invalid_transitions、restrictive 类 BR、preconditions 矛盾）；无明确证据的组合一律保留并记 judgment，禁止凭业务直觉删除。
- **R6 precondition 透传与补全**：①透传 P1 的 {text,type,ref}，不得修改 P1 已判定的 type（P1 有文档上下文，判定更权威）；②仅当 type=state_ref 且 ref=null 时尝试补全（防御性，操作见 2.3）；③同步生成 precondition_state_refs。
  pattern 枚举（单一事实源）：`p1_inherited | explicit_state_match | implicit_same | cross_entity_ref | fuzzy_match | branch_injected`。

---

## Step 0：输入校验

1. **必备节点**：domain_model.entities / structural_relations / transition_relations、state_and_flow.transitions、constraints.cross_entity / invalid_transitions / business_rules、_meta.branch_dimensions。缺失 → 终止，输出：
   `{"_context": {"fatal_error": "缺少必备节点", "missing_nodes": [...]}}`
2. **构建 state_info 索引**（供 R6 补全与 Step 3 字段派生）：
   - `state_lookup: {entity_id: {dimension: set(states)}}`
   - `state_to_entities: {state_value: set((entity_id, dimension))}`（反向索引，用于消歧与维度反查）
3. **结构检查**：所有 transition.preconditions 必须为对象数组且每项含 text/type/ref；发现纯字符串 → 终止，输出：
   `{"_context": {"fatal_error": "P1 preconditions 未结构化，需 P1 v18.4+ 输出"}}`

---

## Step 1：entity_obligations

**1.1 EO-ATC（配置属性）**

遍历 `entities[].attributes[is_config==true]`，生成 EO-ATC：
`id=EO-ATC-NNN；type="attribute_config"；entity/entity_name/attribute_name/attribute_desc 透传 P1；description="覆盖[entity_name]的配置属性[attr_name]不同取值对流转的影响"；suggested_action="修改[entity_name]的[attr_name]，影响[attribute_desc中的业务分支描述]"；coverage_priority="medium"；dimension/from/to=null;source_ref=null（P1 属性无此字段）。`

**1.2 EO-CRU（功能操作，覆盖无状态操作）**

遍历 `entities[].operations[]`，全 category（session/ui/file/query/crud/config）逐操作生成 EO-CRU，不在本步筛选（下游按 operation_category 分流）：
`id=EO-CRU-NNN；type="crud_operation"；entity/entity_name 透传 P1；operation_name=op.name；operation_category=op.category（缺失默认"crud" + judgment）；description="覆盖[entity_name]的[operation_name]操作"；expected_results 原样透传 op.expected_results（不改写、不二次转义；为空则以 operation_name 补入一条 + judgment）；suggested_action="对[entity_name]执行[operation_name]"；coverage_priority="medium"；source_ref 透传 op.source_ref。`
兼容（防御）：op 为字符串（P1 v19.1- 产物）→ 以该字符串为 operation_name、operation_category="crud"、expected_results=[operation_name]、source_ref=null 生成，记 judgment。

---

## Step 2：transition_obligations

TO = P1 transition 全字段透传 + 本节新增/覆盖字段。遍历 transitions，同步构建 to_index。

**2.1 coverage_priority（按序首个命中）**

| 条件 | priority |
|------|----------|
| from==null 或 to∈terminal | critical |
| P1 priority∈{P0,P1} 或 inferred==true | high |
| （防御）from∈terminal 且 to∈terminal | low |
| 默认 | medium |

注：inferred→high 为有意设计——推断产物按不确定风险提高覆盖优先级（与 P1 confidence 规则相反，勿自行"修正"）。

**2.2 字段**
- `risk_traits`：透传 P1 traits（TO 中字段更名为 risk_traits）。
- `is_repeatable`：from==to → true + repeat_condition（从 P1 desc/note/expected_results 提取重复条件，无描述填"可随时重复"）；否则 false, null。
- `side_effects`：双渠道合并，去重键 (target_entity, target_dimension)：
  - 渠道1：R.from==当前实体且 evidence_transitions 含当前 tid → target_entity=R.to，target_dimension=entity==R.to 的 P1 原转换的 dimension，effect_desc=R.desc；
  - 渠道2：当前转换 expected_results 中的他实体状态变更描述，优先精确匹配实体名。
- `source_ref`：透传 P1 transition.source_ref（不更名、不修改、不二次转义）；2.4 拆分产生的分支 TO 原样继承同一 source_ref。


**2.3 precondition 处理（执行 R6）**
1. 透传 {text,type,ref}。
2. 补全（仅 type=state_ref 且 ref=null，防御性）：在 state_lookup 中查找——显式匹配（文本含"实体.维度=状态"）优先；隐式同实体次之（仅含状态值且存在于当前实体同维度）；跨实体需文本显式出现实体名。成功 → 回填 ref 并加入 precondition_state_refs（pattern=explicit_state_match / implicit_same / cross_entity_ref / fuzzy_match）；失败 → 保持 null，warnings 记 precondition_state_refs_unresolved。
3. 同步 precondition_state_refs：每项 type=state_ref 且 ref 非 null → 提取 ref + raw_text（原 text）+ pattern（P1 直接带来的标 p1_inherited）。

示例（P1 输入）：

```json
"preconditions": [
  {"text": "项目处于待选入状态", "type": "state_ref",
   "ref": {"entity": "E-PROJ", "dimension": "项目状态", "state": "待选入"}},
  {"text": "本阶段评价结果为差的项目不可选入", "type": "constraint", "ref": null}
]
```

输出（透传 + 同步 refs）：

```json
{
  "preconditions": [
    {"text": "项目处于待选入状态", "type": "state_ref",
     "ref": {"entity": "E-PROJ", "dimension": "项目状态", "state": "待选入"}},
    {"text": "本阶段评价结果为差的项目不可选入", "type": "constraint", "ref": null}
  ],
  "precondition_state_refs": [
    {"entity": "E-PROJ", "dimension": "项目状态", "state": "待选入",
     "raw_text": "项目处于待选入状态", "pattern": "p1_inherited"}
  ]
}
```

**2.4 分支拆分（应用 R1、R5）**
1. matched_dims = BD.coverage.transitions 含当前 tid 的分支维度；coverage 无匹配但 note.branch_dimension 非空 → 以该维度为 matched_dims；两者皆空 → 不拆分。
2. **实质差异前置判定**：所有组合在 {from,to,action,preconditions,expected_results} 上完全相同 → 不拆分，note.comment 标"分支无实质差异"。
3. 生成组合，按 R5 过滤无效组合。
4. 有效组合 >16 → 降级不拆分，branch_path=[]，note.comment 标组合数。
5. 每个有效组合生成独立 TO：`id=原id+[a]~[p]`（按组合序）；`action=原action+" [dim1=val1; dim2=val2]"`；branch_path=[{dimension,value}]。
6. 删除原 TO，同步更新 to_index。
7. **继承**：分支 TO 继承原 TO 的 preconditions 与 precondition_state_refs；若分支维度名等于某 state_dimensions.dimension_name 且分支值为该维度合法状态 → 追加 precondition `{text:"{维度}={值}", type:"state_ref", ref:{entity,dimension,state:值}}` 并同步 precondition_state_refs（pattern=branch_injected）；值非法则该项 type="constraint", ref=null。

---

## Step 3：cross_entity_obligations

**3.0** 按 R3 对所有 XC 分流，初始化 xc_status[xc_id]（终态 "co" 或 "br"）。

**门禁**（constraint 车道全过 G1\~G5；auto 车道过 G1/G2/G3/G5）：

| 门禁 | 规则 |
|------|------|
| G1 配置属性 | enabler_dimension 为配置属性 → 转 BR |
| G2 不可提取 | enabler_dimension/state 与 dependent_dimension/condition 均无法派生 → 转 BR |
| G3 创建型 | dependent 转换全部 from==null → 转 BR |
| G4 字段缺失 | enabler_state 缺失 → 转 BR（auto 车道由 P1 原转换派生不会缺失，故免查） |
| G5 三元组验证（R2） | enabler_state 须在 state_lookup 合法状态列表 → 否则转 BR |

**CO 字段派生表**（公共字段 + 车道差异，单一事实源）

公共：id=CO-NNN；type="cross_entity"；enabler_role/dependent_role=对应 P1 原转换的 role（system→null）；suggested_action 按核心规则 5；merged_from=[]。

| 字段 | constraint 车道 | auto 车道 | lifecycle 车道 |
|------|----------------|-----------|----------------|
| 来源 | XC 状态门禁类 | R 或 XC 因果联动类 | structural 中 business_ownership 且 composition 且 1:1 |
| causal_type | constraint | auto | lifecycle |
| constraint_id | XC.id | XC.id 或 null | null |
| enabler_entity | XC.source_entity | R.from | SR.from（父） |
| enabler_dimension | XC.source_state 经 state_to_entities 反查（限定 source_entity） | P1 原转换 dimension | P1 原转换 dimension |
| enabler_state | XC.source_state（过 G5） | P1 原转换 to | P1 原转换 to |
| enabler_transition_id | to_index 中 to==enabler_state 的转换（无则 null） | evidence 中 entity==R.from 的 tid | 父创建转换（from==null，无则 null） |
| dependent_entity | XC.target_entity | R.to | SR.to（子） |
| dependent_transition_id | ①优先 target_from/target_to 结构化字段；②缺失则解析 target_condition（到/→/变为/变更为/状态=）；③仍有损（仅 to）→ 从同 (source_transition,target_entity,target_to) 的镜像/联动对继承 from；④按 (entity,dimension,from,to) 匹配 P1 原转换（抽象感知）。候选≠1 升级跳过，绝不取第一条 | evidence 中 entity==R.to 的 tid | 子创建转换（无则 null） |
| dependent_dimension | XC.target_dimension | 反查转换 dimension | 反查转换 dimension |
| dependent_condition | XC.target_condition | 反查转换 to | 反查转换 to |
| trigger / trigger_source | null / null | R 透传 | null / null |
| rollback_propagation | false | R 透传 | false |
| confidence | high | R 透传 | high |
| aggregation | (enabler→dependent) 为 composition 且 1:N → "all"，否则 null | 同左 | null |
| ref_to | dependent TO preconditions 含 enabler_state 项的 text（无则 null） | null | null |
| desc | "{enabler}.{dim}={state} 是 {dependent}.{dim} 推进至 {condition} 的前置条件" | R.desc 或 XC.desc | "{父} 与 {子} 生命周期同步" |
| coverage_priority | dependent 转换最高 priority | 按序：bidi_coupling 或 rollback→critical；confidence∈[low,medium]→high；默认→medium | high |
| source_ref | 透传 XC.source_ref | XC 联动类：透传 XC.source_ref；R 来源：evidence_transitions 首条指向的 P1 原转换的 source_ref，为空则 null + judgment | null + judgment |

**3.1 constraint 车道附加——反向验证**：生成 CO 的 (enabler_entity, dimension, state) 应在 dependent TO 的 precondition_state_refs 中有对应项。
- 存在 state_ref 项文本含 enabler_state 但 ref 未解析 → 补全 ref，pattern=explicit_state_match，judgments 记"CO 生成后回填"。
- 文本中未出现 → warnings 记录，CO 保留（不强制转 BR）。

生成后 xc_status[xc_id]="co"。

**3.2 auto 车道**：按派生表生成；constraint_id 非 null 时 xc_status[xc_id]="co"。

**3.3 lifecycle 车道**：按派生表生成（不涉及 XC，不更新 xc_status）。

**3.4 去重合并**
- 签名去重：签名=(enabler_entity, enabler_dimension, enabler_state, dependent_entity, dependent_dimension, dependent_condition, causal_type)，相同 → 合并。
- 语义去重：entity 对 + causal_type 相同且核心因果等价 → judgment 后去重。
- 合并规则：保留方 trigger/trigger_source/rollback_propagation 为 null/false 时可被非 null/true 覆盖；confidence 取高者；被合并方 ID 入 merged_from。

---

## Step 4：constraint_obligations

**4.1 RO-IT**：透传 P1 invalid_transitions；id=RO-IT-NNN；constraint_id=P1 的 IT-XXX；coverage_priority="high"；source_ref 透传 P1 invalid_transitions.source_ref。

**4.2 RO-BR**：透传 P1 business_rules；id=RO-BR-NNN；constraint_id=P1 的 BR-XXX；signal_type/category 原样透传，不得丢弃或降级；enforcement 直接透传 P1 enforcement 值（severity 已更名，无二次更名）；source_ref 透传 P1 business_rules.source_ref。

**4.2.1 XC→RO-BR**（所有被门禁跳过、G5 失败或无法分类的 XC）：
`id=RO-BR-NNN；type="business_rule"；constraint_id=XC.id；entities_involved=[source_entity, target_entity]；signal_type=null；description="[来源于XC-{id}] {target_condition}; {desc}"；enforcement="mandatory"；ref_to_existing_br=P1 有同主题 BR 则填其 BR-XXX；suggested_action 按核心规则 5；source_ref 透传 XC.source_ref。`
- category：按 XC 文本信号判定（显示→display，功能→usability，限制→validation）；多信号命中按 display > usability > validation 取先；无信号默认 validation。
- coverage_priority：镜像/Step4.6 确认类（原状态门禁候选）→ high；其余 → medium。
- xc_status[xc_id]="br"。

---

## Step 5：_context

透传 P1 元数据并补足：
- **branch_dimensions**：补 entity 和 affected_obligations
- **transition_splits**：`{base_tid: [variant_to_ids]}`，记录被分支拆分的转换（Option C：原 TO 删除，只输出变体 TO）。CO 的 enabler/dependent_transition_id 引用抽象转换 id，下游（S0/S1）据此解析到具体变体；未拆分转换不列入（自身即解析结果）。
- **structural_relations / transition_relations**：关键字段透传
- **state_info**：汇总各实体状态维度信息
- **prohibition_config**：**透传 P1 的 _context.prohibition_config（领域操作词汇的唯一真相源在 P1 数据层）**；P1 未声明时用框架通用默认（不可/不能/禁止/不得/不允许/无法/无权 + 通用 CRUD 动词），**禁硬编码领域动词**（选入/归档/发放等业务词只来自 P1）。
- **permissions**：**透传 P1 的 _context.permissions（角色→可执行操作，V07 校验器据此推导矩阵）**；P1 未声明时为空 list。
- **xc_to_br_mapping**：xc_status=="br" 的条目
- **judgments**：语义过滤、XC 分类、三元组验证、去重、refs 回填、operations 兼容处理等关键决策
- **warnings**：所有跳过项，含 precondition_state_refs_unresolved 列表（TO id+文本）、precondition_state_refs_coverage 统计（每条 TO 的 preconditions 总数与解析成功数）

---

## 输出协议

1. **默认单次输出**：优先在一条响应中输出完整 JSON 对象。
2. **自主分批**：当你判断完整输出难以在单条响应中容纳时（对象多、JSON 体积大），自行切换分批输出，无需请示，也不要在中途截断 JSON。分批顺序：① EO+TO ② CO+RO ③ _context；每批必须在完整子对象边界结束，保证各批按序拼接后可合并为完整 JSON。
3. **快照**：`{to_index_size, co_list_size, xc_status_summary:{total_xc,as_co,as_br}, precondition_state_refs_coverage:{total_preconditions,total_state_refs_expected,total_state_refs_resolved,unresolved_count,p1_inherited_count,p2_filled_count}}`
4. **自检**（8 项，填入 _context.self_check）：任一项 false → judgments 说明原因后放行；仅 id_globally_unique 或 p1_root_nodes_complete 为 false → 终止并输出 fatal_error。

```json
{
  "no_branch_scenarios": true,
  "all_xc_have_status": true,
  "enabler_state_valid_or_judgment": true,
  "signal_type_category_preserved": true,
  "id_globally_unique": true,
  "p1_root_nodes_complete": true,
  "all_skipped_xc_have_br": true,
  "precondition_state_refs_complete": true
}
```

- `no_branch_scenarios`：所有受分支影响的 TO（BD.coverage 命中或 note.branch_dimension 非空）均已拆分，或已记降级 judgment（组合>16 / 无实质差异），或为主TO保留（已生成 [a][b]... 分支TO，主TO仅承载跨维度联动，分支场景已覆盖）。判断降级 judgment 时按 TO id 前缀精确匹配（judgment 格式 `TOID: ...`），避免分支变体 id（如 `T-X[a]`）误命中基础 TO（`T-X`）。
- `precondition_state_refs_complete`：所有 type=state_ref 项均解析出 ref 并进入 precondition_state_refs；unresolved 非空则为 false 并在 judgments 说明降级理由。

---

## 输出 Schema（字段清单，单一事实源）

```
TO     = P1 transition 全字段（含 source_ref；traits 更名 risk_traits）
       + coverage_priority, is_repeatable, repeat_condition,
         side_effects[{target_entity, target_dimension, effect_desc}],
         branch_path[{dimension, value}],
         precondition_state_refs[{entity, dimension, state, raw_text, pattern}]
EO-ATC = {id, type:"attribute_config", entity, entity_name, attribute_name, attribute_desc,
         description, suggested_action, coverage_priority, dimension, from, to, source_ref}
EO-CRU = {id, type:"crud_operation", entity, entity_name, operation_name, operation_category,
         description, expected_results[], suggested_action, coverage_priority, source_ref}
CO     = {id, type, constraint_id, causal_type,
         enabler_entity, enabler_dimension, enabler_state, enabler_transition_id, enabler_role,
         dependent_entity, dependent_transition_id, dependent_dimension, dependent_condition, dependent_role,
         aggregation, ref_to, trigger, trigger_source, rollback_propagation,
         confidence, desc, coverage_priority, suggested_action, merged_from, source_ref}
RO-IT  = {id, type:"invalid_transition", constraint_id, entity, from, to, reason, coverage_priority, source_ref}
RO-BR  = {id, type:"business_rule", constraint_id, entities_involved, category, signal_type,
         description, enforcement, ref_to_existing_br, coverage_priority, suggested_action, source_ref}
```
