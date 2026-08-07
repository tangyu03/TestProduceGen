# P2→P3 管线修复决策记录

记录 P2 义务模型 / P3 程序生成的修复决策(①②③④⑤ 系列)与已验证事实。
新增条目追加到顶部,每条含日期、决策、证据链。

---

## 2026-08-07 ⑰ S0 Strategy 0 匹配机制去脆弱——结构化 ref 优先取 max，文本扫描降级兜底

**背景**:⑮ 修 phase_anchor 前置误触发后，用户要求"修复 S0 Strategy 0 的匹配机制脆弱的问题"。⑮ 只跳过了 `pattern=phase_anchor` 的前置，但 Strategy 0 本体仍是**裸子串扫描**（`state_name in prec_text`，first-match dict 迭代序），隐患依旧。

**根因（第一性原理：数据层信号弃而不用，反而猜表层文本）**:P2 已把每条前置产出为结构化 `{"text","type","ref"}`，`ref={entity,dimension,state}` 明确命名了被引用的状态。但 Strategy 0 不读 `ref`，转而对 `text` 做子串匹配：
- **first-match 顺序脆弱**：E-SCORE T-034 前置"评审计划状态由待启动变为待评审"，`ref.state=待评审`（P2）。文本扫描在 `primary_states.items()` dict 序中先命中 from 态 **待启动**（P1）→ 返回 `1+1=2`；而 entry 条件实为 to 态 **待评审**（P2）→ 应返回 `2+1=3`。from 态/起始态恰好排在前，是典型误中。
- **无维度限定**：只要文本含主维度状态名即触发，不校验引用对象是不是主实体/主维度（⑮ 的 {6,7,8} 就是例证）。
- **first-match-wins**：多个主状态名出现时，赢家取决于 dict 插入序，非语义（入口须等所有引用状态达成 = 取 max）。

**解法**:Strategy 0 优先用结构化 `ref`——`ref.entity==primary_entity`、`ref.dimension==primary_dim`、`ref.state in primary_states` 三者齐备才采信，多 ref 取 **max phase**（每个引用的状态都是入口门禁）；文本扫描保留为**兜底**（无可用 ref 的 P1-inherited 裸串）。`phase_anchor` 前置继续跳过（单转换锚定 ≠ 整机入口锚定，⑮ 语义不变）。

**验证结果**（全管线重跑，Engine State 结构化对比）:
- `dep_state_phase_map` 唯一差异 = **E-SCORE.打分状态 {2,3,4}→{3,4,5}**（T-034 ref 待评审=P2，+1=3），语义正确（打分任务在计划进入待评审后分配）；
- E-ORG.机构状态 {0,1,2}、E-PROJ.项目状态/项目阶段、E-USER.锁定状态 **全部不变**——phase_anchor 跳过与共享状态名不调用两条路径均未回归；
- contextual_phase_rules / state_type_map / dependent_entities / entity_parent / topology_levels / transition_upstream_map **canonical diff 全部 SAME**（dependency_depth/topology_levels 仅 dict 键序差异，数值一致）；
- 0 errors，警告 49→48（减少 1 条，非新增）。
- 注意：P3 为 LLM 生成，两次 run 的 TC 编号/标题不可跨 run 比对；相位验证一律以 S0/S1 的**确定性 Engine State** 为准。

---

## 2026-08-07 ⑯ 约束谓词解析器表层语法表去硬编码——领域名词全部数据派生

**背景**:A3 修 phase_anchor `raw_text` 后，用户复查 `context/generate_obligation_model.py` 指出"仍然存在很多硬编码"。全文件中文串字面量清点后，违规集中在 **Step 3 约束谓词解析器 `_PREDICATE_SURFACES` 表层语法表**（记忆条目"P2 解析器禁止名字硬编码"的第三次触发）。

**根因**:表层语法表把领域名词/动词/态名直接写进了正则与常量表：
- `_NEGATION_MARKERS = ("不可选入", "不能提交")` —— 否定标记把领域动词（选入/提交）与通用否定词捆死；
- `_COMPLETION_STATE_SURFACES = {"提交了": "已提交"}` —— 领域表层→态名的映射表；
- selection_range / config / occurrence_limit / completion 四个正则分别硬编码实体名 **项目**（两处）、**评审计划+专家**、**项目**、**专家+打分**。

**解法（第一性原理：表层语法只描述句式，名词一律来自数据）**：
- 实体名（项目/评审计划/打分/专家/机构/…）由 p1 `domain_model.entities` 派生 `_ENTITY_NOUN_ALT`（`key=(-len, name)` 确定序，保证输出可复现），四个正则的实体名词位全部换用该 alternation；
- 否定标记拆为 **通用中文否定前缀**（`_GENERIC_NEGATION_PREFIXES`，语言级，与 `_prohibition_config.negation_prefixes` 默认值共用单一真相源）+ 可选**动词尾捕获**（领域动作词从表层捕获但节点不消费）；
- 完成态不查映射表，改由 `_resolve_completion_state` 在 state_lookup 中按 **"已"+动词** 解析（语言级"已X=已完成X"惯例），多候选优先 terminal 态；
- `classify_xc` 的 to_br 内容信号去掉领域词 评级/归档（保留通用计算语义词 累计/计算/公式）——该分支对当前 28 条 XC 全被模板前缀分支先行捕获，属死分支，去领域词零风险。

**验证结果**:重跑 P2，`coverage_obligations.json` 与 A3 基线（fa3a351）**递归 JSON diff = 0**（仅 generated_at 时间戳差异）——constraint_predicate / judgments / self_check / snapshot 逐项一致，无任何行为回归。谓词样例复核：T-006 completion target 仍 = {E-SCORE,打分状态,已提交}；T-002 仍 negation(field_equals 评级,差)；T-015 仍展开 field_in(评审组人数,[5,7,9]) ∧ field_equals(组长专家数,1)。

**残留（未改，属数据层格式约定而非领域名词）**:`classify_xc` 的 desc 模板前缀（"镜像 T-" / "联动: T-" / "分支[" / "由 Step 4.6 约束-因果鉴别确认"）匹配的是 P1 生成的机器可读 desc 格式（管线契约）；`derive_direction` 的 `"(初始)"` 哨兵对当前 P1 数据为死代码（数据用 None）；RO-BR category 关键词（显示/展示/不得/禁止…）为通用中文词。若需把这些也数据化，需改 P1 输出格式，另行排期。

---

## 2026-08-07 ⑮ A3 相位锚定的 S0 副作用——phase_anchor 前置误触发整机入口锚定

**决策**:`context/generate_obligation_model.py` Step 2.5c 给 E-ORG.机构状态 非创建转换（T-042/043/044/045）写入 `precondition_state_refs`（S3 Guard 6 依赖边）+ `preconditions` state_ref dict（S1 `_max_state_ref_phase` 抬相位到 计划状态.结束=P5），配置在数据层 `_context.phase_anchors`（与 prohibition_config 同构，单一真相源）。

**根因（改结果不改代码会踩的坑）**：首版只写了两个消费通道（S1/S3），结果全维抬到 {6,7,8}——S0 `_compute_entry_phase` Strategy 0 扫描**该维度所有转换**的 preconditions 文本，命中"计划状态为**结束**"→ 返回 `5+1=6`，把**整个循环状态机**（合格0/不合格1/试用2）入口锚到 6，连创建转换 T-041（scope=non_creation 明确排除）也被拖到 P6。这是 S0 把"单转换相位信号"误读为"整机入口锚定信号"。

**解法（数据驱动，无名字硬编码）**：`phase_anchor` 前置带 `pattern="phase_anchor"` 标记（单转换锚定，非入口锚定）；S0 `_compute_entry_phase` Strategy 0 对 `pattern=="phase_anchor"` 的 precondition 跳过。`raw_text` 取数据层配置 `note`（领域语义不进代码），S3 Guard 6 只读 entity/dimension/state 不受影响。

**验证结果**：重跑后 dep_state_phase_map 保持 {合格0,不合格1,试用2}，添加机构（T-041）回 P0；T-042/043/044/045 全部 P5（`phase_basis` 显式 "→ bumped to P5 (state_ref 评审计划.计划状态.结束)"），T-042 依赖边 →T-032 归档评审计划；phase 直方图回到 0-5，无 6/7/8。errors=[]、36/36、V01 pass。

---

## 2026-08-07 ⑭ C轮评审 7 问题 → Tier1 三动作（项目簇合并 / RO-IT 吸收 / 机构评价相位锚定）

**决策**:C 轮用户评审 7 个问题归因为三类根因，按 A1→A2→A3 逐个实施、每步独立重跑验证：
- **A1（新增项目簇合并+去重）**：P2 Step 2.5a 跨维度初始化联动并入（T-013 并入 T-001，标记 `merged_into`）；Step 2.5b CRUD 初始化覆盖去重（EO-CRU-001/026 被初始化转换覆盖，标记 `covered_by`）。解决 PROC-057/059 拆分重复（同源连锁反应拆成多条）与 PROC-057/060 重复。
- **A2（选入簇 RO-IT 吸收+抑制）**：P2 将 RO-IT 吸收进 T-002 否定分支（标记 `absorbed_by_transition`）；S1 Type6 跳过 absorbed RO，Type1 否定分支注入具体拒绝理由。解决 PROC-080 前置不足（Given 未声明评价结果为差 → now "操作被拒绝，本阶段评价结果为差的项目不可选入"）。
- **A3（机构评价相位锚定）**：见下。

**新标记字段（本轮新增）**：`merged_into`（A1 跨维度合并）、`covered_by`（A1 CRUD 去重）、`absorbed_by_transition`（A2 RO 吸收）、`pattern=phase_anchor`（A3 锚定）。一致性保障：**单一写入点**在 P2 Step 2.5（a/b/c），S1 是多个消费端（跳过 merged/absorbed、读 state_ref 抬相位），写入与消费分离，校验器只查必填字段不拒未知字段。

**验证结果**：`errors=[]`、`clause_coverage 36/36`、V01 依赖相位单调全图 0 违例；V10 的 3 条 coverage_misses（T-013 / EO-CRU-001,026 / RO-IT-001）为 A1/A2 刻意合并/吸收的**预期产物**，与 A2 基线逐字节相同（signature 一致），非回归。各动作提交：A1=e24a76a、A2=058260b、A3=（本轮）。

**Tier 2 排期（本轮不做，记档待后续）**：PROC-009（没有项目就执行不了评审计划动作）、PROC-085（还没创建评审计划就查看计划）、PROC-087（还没打分就查看打分记录）、PROC-066（仅 CRUD 触发的评价靠前）同属**领域前置不足**类——CRUD/查看类义务缺少"前置对象必须已存在"的领域先决（如 E-PLAN 计划须已建立、E-SCORE 须已打分），非过渡类义务。根因方向：为 EO-CRU/查看类义务建立**领域前置机制**（数据驱动，声明该义务依赖的实体实例先决状态，接入 S1 preconditions/相位 与 S3 Guard 6 依赖），暂不实现。

---

## 2026-08-07 ⑬ S1 结构化跨维度 state_ref 相位抬升——补上 P2 dict 前置的死代码缺口

**决策**:`nodes/s1_generation.py` 新增 `_max_state_ref_phase()`，并把 `_resolve_phase_for_transition` 从早退 return 改为**逐级取 max 再统一返回**（三机制 AND 语义取最晚）：① 文本版 `_max_precondition_phase`（仅 string 前置）② `predicate_phase_lower_bound`（结构化字段谓词）③ 新增的结构化跨维度 state_ref。规则：`preconditions` 中 `type=="state_ref"` 且引用 `(entity, dimension)` ≠ 转移自身时，抬升到该状态相位；**同一状态机引用（`re_ent==entity and re_dim==dimension`）排除**（套套逻辑，自身 from/to 已表达）。

**背景（证据链）**:
- 用户质疑 PROC-111："开题了马上就变验收？评审计划和评分都没开始呢"。T-014（归档后阶段变更，开题→验收）卡在 P1、仅依赖 PROC-059(新增项目)，链条读起来像"新增项目→立即验收"。
- 根因三层失效：① `_max_precondition_phase` 对 P2 dict 前置是死代码（`isinstance(prec,str)` 过滤），且 `exclude_entity` 排掉整个自身实体；② `build_constraint_predicate` 只认 `type=="constraint"`，state_ref 全为 null；③ Guard 6 的结构化锚点边被相位单调性拦截——T-014 的"待归档"ref（P4）依赖候选相位 > 自身 P1，V01 丢弃。
- 事实核对：T-014 触发条件本身是"待归档 ∧ 评级合格"（Given 描述即含），**不是**开题后立即触发；问题在呈现（phase/依赖），非事实矛盾。与 PROC-059 同源不同支。

**解法（数据驱动，无名字硬编码）**：跨维度 state_ref 抬升用 `get_state_phase`（路由主实体 phase_table + 依赖实体 dep_state_phase_map 两表）。受影响 13 个 TO：T-007[a/b/c]/T-008[a/b]/T-010[a-e] 4→5（经 `计划状态.结束`）、T-011 3→5（计划归档回退）、T-012 2→5（计划取消回退）、T-014 1→4（经 `项目状态.待归档`）。T-011/T-012 的 +2/+3 是**回退边**（`is_rollback` base=from_state），触发于计划结束/取消之后，P5 为真实执行点，非过度抬升。新增 `scripts/v32_check.py`/`v32_edgediff.py` 作为回归探针。

**验证结果（真实 S0→S3 重跑，非改旧图数字）**:
- V01（依赖相位单调性）全图 0 违例；errors=0，warnings 全为既有信息消息。
- 依赖边 diff：+11 新增、0 移除；11 条全为 Guard 6 结构化锚点且语义正确（T-007/008/010/011→T-032 归档评审计划、T-012→T-016 取消评审计划、**T-014→T-006 待归档**）。
- PROC-111 相位 1→4，依赖变为 [T-013 开题, T-006 待归档]——用户关注的"评审计划/评分/待归档"链条解锁（Guard 6 锚点本来就存在，此前被相位单调性挡住）。
- 相位移动严格限于 13 个 TO（60 procedure）；FIELD-VAL 在 diff 中"变化"系 source_ids 中文名/实体码命名差异的假阳性，相位相同。
- 修复范围：仅 S3 内的 S1 节点，P1/P2 输出不动，只重跑 P3。

---

## 2026-08-07 ⑫ P2 分支拆分初始化守卫——剔除"自身维度 from=None"的伪分支

**决策**:`context/generate_obligation_model.py` `get_matched_dims()` 增加初始化守卫——当转移为**自身维度初始化**（`t.from is None` 且匹配的分支维度 == 转移自身 dimension）时，从 matched 集剔除该维度。初始化转移没有"既有状态"可分支，coverage 命中只因该维度被**初始化**而非条件分支；按其维度值拆分只会伪造矛盾变体。

**背景（证据链）**:
- 用户报告 PROC-059 矛盾："项目阶段为验收，后面有说转为开题"。根因：T-013（新增项目 → 项目阶段初始化为开题，from=None, to=开题）被 P2 按 项目阶段 维度拆分为 T-013[a]（开题）/ T-013[b]（验收），后者产生 Given=验收 → Then=转换为开题的矛盾场景。
- SRS 原文 4.6 项目管理（1）a："新增：实现项目新增的功能，项目状态初始化为待选入，处于开题阶段"——新增项目无条件处于开题阶段，无 验收 分支。
- 拆分机制：P1 `_backfill_branch_coverage` 把 `note.branch_dimension="项目阶段"` 的转移（T-013/T-014）都计入 coverage.transitions；P2 `get_matched_dims` 命中后，因该维度无 target_transition=T-013 的分支，回退取**全部值** ["开题","验收"] → 2 combos → 拆出 [b]。
- T-014（from=开题, to=验收, 有真实既有状态）不受守卫影响，分支保持正确。

**解法（数据驱动，无名字硬编码）**：`from is None` + `bd.dimension == t.dimension` 时剔除——跨维度分支（如 T-015 按 评审组人数）不受影响。P2 重生成后 T-013 恢复单一转移（无 branch_path、无注入的"项目阶段=验收" precondition），`transition_splits` 移除 T-013。同步更新 `nodes/s1_generation.py` 中为之辩护的过时注释（588-593 行）与 `scripts/s3_probe.py` 默认 focus（T-013[b]→T-013）。

**验证结果**:
- P2 自检全绿（no_branch_scenarios: True 等 8 项），T-013[b] 从 coverage_obligations.json 消失。
- P3 重生成（main.py 默认路径覆盖 p3_agent_output.*）：PROC-059 变为 `溯源: T-013`，Given=(初始)，When=新增项目，Then=初始化为开题——矛盾消除；总 procedure 782→777，恰减 5（T-013[b] ×5 实例）。
- 全量 grep 确认"新增项目 [项目阶段=验收]"0 命中；剩余"项目阶段为验收"均为 T-009/T-010 归档分支（合法）。
- validate_p2 CO 引用解析：T-013 现为已输出 TO id，无 dangling。

---

## 2026-08-06 ⑪ P1 校验下沉 srs_pipeline——删除 P1_Prompt 派生的三个 validate_p1*.py

**决策**:`context/verify/` 下三个 P1 校验脚本(`validate_p1.py` / `validate_p1_direction.py` / `validate_p1_structured_fields.py`)全部删除。P1 已由 `srs_pipeline/` 取代，校验内联于 `model.assemble()`（Step6 校验清单 C01~C17 + schema.validate_llm），独立的旧校验器是 `P1_Prompt.md` 时代的产物，随 P1 迁移作废。readme.md 同步清理：移除 `scripts/validate_p1_structured_fields.py` 行（文件本就不在该路径），P1 相关路径 `P1output.json`/`P1_Prompt.md`/`generate_json.py` 改为 `review_structured.json`/`srs_pipeline/`。

**证据链（三者在当前 P1 真源 `review_structured.json` 上实测）**:
- `validate_p1.py`:49 errors，全为 role 按 ID 查而新 schema 的转换以角色名引用（C01 同时收角色 ID+名+system 保留名）→ 结构性 schema 漂移。其 8 项检查（引用完整性/状态结构/precondition/字符安全/operations/必填字段/分支覆盖/transition_relations）分别被 C01/C02/C03/C10/C11+C12/C05/C07 + `schema.validate_llm` 覆盖。
- `validate_p1_direction.py`:0 err / 3 warn。3 warn 为 forward 索引回退（T-007 待归档→已选入、T-044 试用→合格、T-045 试用→不合格）——均为**有意**的 forward 转换，raw states 序不保证语义序；srs_pipeline 的 C13/C14/C16 刻意不含该检查（移植会使每轮生成 `consistency_check` 翻 warnings）。其余 direction 检查全部被 C13 覆盖。
- `validate_p1_structured_fields.py`:91.11%，唯一 fail = evidence_transitions 66.7%（E-EXP↔E-USER 空证据）——恰是 C07 4.5 允许的情形（`trigger_source ∈ desc/business_rule/bidi_coupling` 时证据可仅注位置）。该工具前提（"LLM 可能漏发结构化字段 → 引擎回退"）已失效：新 schema 字段经 `validate_llm` 强制必填 + C01~C17 校验，非可选发放。

**遗留（记）**:
- `scripts/cross_domain_test.py` 整脚本基于旧 P1→P2 流（其引用的 `scripts/validate_p1_structured_fields.py`、`build_obligations.py` 均不存在），早已损坏，不在本次范围。
- `srs_pipeline/validate.py` 未内置 forward 索引单调检查——T-003 类笔误由 C14（expected_results 起讫对账）+ C16（状态与原文枚举对账）兜底，与前朝第 7 项检查定位不同，不再移植。

---

## 2026-08-06 ⑩ 删除 constraint_field_overlay.py——字段注册表全量改从 DomainModel 派生

**决策**:`context/constraint_fields.py` 重写为**全量派生层**,`srs_data/constraint_field_overlay.py`(手写 8 条语义增量)删除。字段集合、kind、value_type、strip_suffix、aliases、count_aliases、value_normalization、populated_anchors、ref_state_dimension 全部从 `struct_srs.py` DomainModel 推导,机制文件不含任何领域字符串(见 constraint_fields.py 模块 docstring 的 8 条派生定式)。

**决策 A(超时类型锚点 = 6 态,真源派生)**:fail-fast 原设计(anchors=xc 人工 4 代表 + from⊆anchors 校验)已按裁定改为**锚点 = 全部 `剥后缀值+时限超时` 写点 transition 的 from 态** {已建立,待启动,待评审,评审中,暂停,已完成}。p16/T-030(评审中)、p17/T-031(暂停) 是真实写点,不再是 xc 漏选。**原 from⊆anchors fail-fast 移除**:锚点全量派生后,该检查按构造成立(from 就是扫描结果),变废话;真源派生本身就是守卫——模型加写点锚点自动长成新态。

**决策 B(死元数据删除)**:`scope`(无消费者)、`maps_to`(无消费者)、`专家人数` 死别名(输出仅 4× 以 attribute_name/实体文本出现,从无 field ref)全部删除。

**遗留债(记)**:
- 死字段记录不再保留;`desc` 本就无消费者,不再生成。
- value_normalization 派生出惰性前缀映射超集(评级:合→合格/不→不合格/不合→不合格;超时型:下→下发超时 等,经 strip_suffix 往返恒等),与旧 {优,良}/{一:1} 相比不改变任何值——**P2 全量 diff 验证字节一致**。
- P2 解析器 config 表面正则 `^\s*评审计划的(?P<f1>...由...)` 仍硬编码"评审计划的"字符串(`generate_obligation_model.py` config 行)——属解析器侧遗留,注册表已不落任何领域字符串。

**验证结果**:用 `review_structured.json`(当前 P1 真源,`context/P1_out.json`/`P1_output.json` 均为旧,已弃)重生成 P2,与提交基线 diff:**EO/TO/CO/RO 四义务集 + _context(除 generated_at)全部字节一致**。注册表 11 条(8 canonical + 3 别名),fail-fast 校验通过。

---

## 2026-08-06 ⑨ S1 phase bump 接入 constraint_predicate(共享判据,文本 bump 是死代码)

**决策**:`nodes/s1_generation.py` `_resolve_phase_for_transition` 新增 `constraint_predicate` 参数,在文本 `_max_precondition_phase` bump 之后、return 之前调用 `predicate_phase_lower_bound`(context/constraint_fields.py,同一份共享判据)。调用点 `_generate_type1` 传 `to.get("constraint_predicate")`。

**背景(证据链)**:
- 文本 bump 对 P2 结构化输入是**死代码**:`_max_precondition_phase` 的 `prec_state_re` 只匹配"为XXX"状态名,aggregate_count 等约束文本(如"机构累计 10 次项目阶段评价结果为优")命中率为零;且 P2 preconditions 是 dict 形态,line 1042 `if not isinstance(prec, str): continue` 全部跳过。
- **连带 bug**:aggregate_count 的 counter field_ref 键名不一致——`context/generate_obligation_model.py` line 678 原用 `"field": rec["name"]`,而 field_equals 等(同文件 line 600)和 registry `resolve_field` 都用 `"name"` → `resolve_field` 查不到 name → `field_phase_lower_bound` 返回 None → 相位下界落空,T-044 仍 P0。
- P1 输入(`context/P1_out.json`)缺失,无法重跑解析器;按 ⑧ 先例对现有 coverage_obligations.json 做**手术式补丁**(3 个 aggregate_count counter `field`→`name`,与解析器修复产物一致)。

**解法**:
1. 解析器 line 678 改为 `"name": rec["name"]`(与其他 field ref 及 resolve_field 对齐);现有 JSON 3 个 counter 同步补丁(T-039/043/044)。
2. S1 wiring:`predicate_phase_lower_bound(constraint_predicate, dep_state_phase_map, phase_table)`,`pred_phase > base_phase` 时返回 bump,`phase_basis` 标注 `(predicate <type>)`。

**验证结果**:重生成 + 全量校验 + 确定性双跑。
- **T-044**(PROC-146):P0→**P4**(计数锚点 E-PROJ.评级=待归档=P4);**T-043**(PROC-144/145):P2→**P4**。
- T-039(连续密码错误次数,锚点未锁定=P0)保持 P0,无虚假抬升。
- 连带抬升均合理:T-007(归档后评级门控,field_range+field_equals→评级锚点)P1→P4;**T-015**(建立计划,selection_range 已选入+field_in→已建立)P0→P1;T-002(项目选入,conjunction=negation(评级≠差)→P4 + occurrence_limit→已选入 P1)P1→P4 可辩护("评级不为差"要等评级落库才可验证)。
- disjunction_ref(T-042/T-045)保守 default_phase=0 不抬升;全量 **37 处相位变化全部为抬升,0 下降**;PROC-060/068(Step 5 消歧/新机制)不受影响,仍 P0,属 ⑧ 遗留。
- 全量校验 verdict **pass, blocker 0, warning 0**(V01~V10);V01 依赖相位单调不破(所有 proc phase ≥ 依赖 phase)。metrics 与基线一致 case_total 782。
- 双跑(PYTHONHASHSEED 默认/999)业务数据(procedures/obligations/engine_state)字节一致,唯一差异 `statistics.elapsed_seconds`(耗时,预期)。

---

## 2026-08-06 ⑧ P2 约束解析 v6:value_type 声明 + disjunction_ref 状态确认 + set 迭代确定性修复

**决策**:
1. **value_type 声明落数据层**(`srs_data/constraint_field_overlay.py`):数值字段显式 `value_type:"int"`(各项打分/选入次数/连续密码错误次数/组长专家数;评审组人数经 `cast:"int"` 派生)。`context/constraint_fields.py` `_derive_field` 透传,`_normalize_constraint_value` 以 `value_type=="int"` 取代 `kind=="config"` 判断。→ **T-036 判据"全部为零"的 value 由 `"0"`(str)修为 `0`(int)**,消除任何未来 aggregate/comparison 消费方的类型债;config 值(评审组人数 5/7/9、组长专家数 1)行为不变。
2. **disjunction_ref 状态确认**:T-042(合格→不合格)、T-045(试用→不合格)的 `resolved:false` **不是"语料无目标"**,而是解析器未实现引用展开。语料有明确可解析目标:
   - T-042"评价结果满足下面任一条" ↔ `struct_srs.py` `b31`(computation):"…阶段评价为差的次数累计达到 3 次及以上;或差 1 次及以上且不合格 3 次及以上;或不合格 5 次及以上;满足任一条…不合格机构"。
   - T-045"试用机构评价结果满足降级规则任一条" ↔ `b34`(computation):"累计 2 次差降为不合格;累计 1 次差且 2 次及以上不合格降为不合格;累计 4 次不合格降为不合格;同时可满足升或降时降为不合格"。
   展开=把 computation 文本解析为 disjunction(aggregate_count/field_equals 复合谓词),属**遗留工作,需单独验收标准**。v1 保持 `resolved:false` + PREDICATE_RULES.default_phase=0 保守下界,不冒充硬约束。
3. **set 迭代确定性修复**(`context/generate_obligation_model.py`):`for s in states`(derive_precondition_refs 首匹配 break,2 处)、`initial_targets`(BFS 种子序)、`term_set` 等值赋值(2 处)、`forward_adj` 目标集(环检/Bellman-Ford/forward_reached,3 处)全部 `sorted()`。`next(iter())`/`set.pop()`/set 直接取 `[0]` 均无;`sorted()` 元素全为 `set[str]`,可比。

**验证结果**:三跑(PYTHONHASHSEED 默认/1/999)业务数据(TO/EO/CO/RO + _context 除 generated_at)完全一致,唯一差异 `_context.generated_at`(时间戳,预期)。v6 增量写入 coverage_obligations.json:仅 T-036 谓词(`"0"`→`0`) + generated_at,其余字节不变。unparsed=0。

**遗留(接 ④ P1 结构化字段方向,独立验收)**:
- disjunction_ref 展开 b31/b34:表层"…累计 N 次(及)以上…或…;且…"复合计数条件 → disjunction 谓词。
- entry=2 TO 锚定修复(Strategy 0 消费 ref_state_dimension)、PROC-016 wiring(Step 4 aggregate_count→Guard 6)、PROC-060((state,path) 消歧,Step 5)、PROC-068(需新机制)——均为 P2 谓词已就位后的下游消费工作。

---

## 2026-08-06 ⑦ V06 修复:合并保留 time_control 声明(生成器侧补数据,非校验器豁免)

**决策**:V06 的 4 个 missing time_control 用生成器侧修复——dedup 合并并集 source_ids 后,若引用 time_sensitive 义务而 survivor 无 time_control,则按 action 语义补派生 mechanism。**不**采用"不合并"方案(V09 exact_duplicate 会拦截 BDD 相同的 T-038/T-039 变体),也不做校验器豁免。

**背景(证据链)**:
- PROC-025.1/2(negative_test)、PROC-026.1/2(audit)是 T-038(手动锁定,非时效)与 T-039(自动锁定,time_sensitive)的 dedup 合并产物:完整 source_ids=[T-038,T-039],survivor 从 T-038 路径继承 time_control=None → V06 报缺声明。
- V06 evidence 只显示 `["T-039"]`,因 evidence 只取 `srcs & needs` 交集(需要 time_control 的义务子集),非完整 source_ids——一度误导根因判断为"T-039 自身变体缺失、非合并"。以 `p3_agent_output.json` 实际 proc 为准确认是合并产物。
- T-039 的时间触发本身已被 PROC-027(clock_injection)/PROC-028(db_time_update)覆盖;缺的只是合并 survivor 的声明。

**解法(与 V06 同一份判据,共享派生)**:
- 新共享判据 `context/time_control.py` `needs_time_control_ids(model)`:time_sensitive TO + timing BR 的 id 集合。V06 与 S1 共用(同 entity_operators.py/co_derivation.py 的共享派生规则,generator 与闸门不漂移)。
- `nodes/s1_generation.py` `_dedup_procedures` 增 `time_needs` 参数 + `_ensure_time_control()`:三处合并(Branch A/B/C)并集 source_ids 后调用——并集命中 time_needs 且 survivor 无 time_control 时,补 `{"mechanism": _derive_time_mechanism(action), "status": "planned"}`,与 _generate_type1 现有格式一致。
- 非时效合并不受影响(time_control 保持 None);有针对性单测(合并并集 + 非时效不动)。

**验证结果**:重生成 + 全量校验。V06 `missing time_control=0`(原 4);verdict **pass**,blocker 0, **warning 0**(原 1);V07 仍 0/0/0;V09 仍 pass(合并保留,无 exact_duplicate);V10 覆盖不变 TO 71/71 | EO 75/75 | BR 127/127(embedded 13, xc_causal 20) | IT 7/7。

---

## 2026-08-06 ⑥ Type9 actor 修复:共享派生 entity_operators + V07 实体级检查

**决策**:Type9(field_validation)的 17 个 no_permission 用**第一性原理**修复,非豁免、非补丁。

**背景(证据链)**:
- Type9 的 action `提交含违规值的表单` 是脚手架,非领域操作 → V07 旧 action 子串匹配对 Type9 **天然失真**:17/17 全报 no_permission,含 10 个正确 actor 的误报。
- 生成器旧逻辑对无 TO 的 managed 实体(专家/分数限值/附件)兜底 `系统管理员`,7 个错误 actor。生成器与校验器各拿一半真相 → 漂移(与 co_derivation.py 记录的缺陷类别相同)。

**解法(与生成器/校验器同一份派生,单一真相源)**:
- 新模块 `context/entity_operators.py`:
  - `form_operator_roles()`(生成器选 actor):create 权限(新增/添加+实体名)优先 → 表单操作 → TO 角色 → composition+business_ownership 父继承(E-ATT→E-PROJ)。兜底系统管理员仅当实体确实无法派生(如只读 E-ROLE/E-LOG)。
  - `entity_operator_set()`(V07 成员检查):L1 表单操作角色;L1 空才并入 L2 TO 角色;L1/L2 皆空才父继承。**刻意非盲并集**——E-ORG→E-PROJ 是 composition(机构拥有项目),但机构的操作者 系统管理员 不得渗入项目;附件只继承项目自身的表单操作者。
  - 键同时支持 ID(E-PROJ)与中文名(项目):生成器传 ID(constraint_steps key),V07 读翻译后输出(main.py `_translate_procedures` 已把 E-XXX 替换为中文名)。
- `nodes/s1_generation.py` `_generate_type9_field_validation`:替换 TO 扫描+系统管理员兜底 → `form_operator_roles()`。
- `verify/checks/v07_role_permission.py`:Type9 改实体级检查(actor ∈ operators(entity)),非豁免;其他类型保持 action 子串。

**验证结果**:重生成输出 + 全量校验。V07 `empty_actor=0, unknown_actor=0, no_permission=0`(原 125 `[待确认角色]` + 17 no_permission 全清);verdict **pass**,0 blockers,1 warning(V06 缺 time_control,4 项,独立问题未处理)。非 Type9 的 765 个 proc actor 零改动。

**残留**:~~V06 4 项(T-039 派生的 PROC-025/026 缺 mechanism)~~ 已由 ⑦ 修复(missing time_control=0,verdict warning 0)。

---

## 2026-08-06 ⑤ 排期决策:weak_dependency 下游行为已确认 = 弱化消费

**决策**:⑤(S3 phase guard 对 backward/resume 边豁免相位反转)**排期做**,与下一轮迭代的 ②(结构重构)一起做。不立刻做。

**确认的 `weak_dependency` 下游行为(三选一)→ 弱化消费**:

- 边**不丢失**:S3 降级时写入独立 `weak_dependencies` 列表并记 `weak_origins[best] = "transition_upstream_phase_inversion"`(`nodes/s3_dependency.py:263-281`)。
- **无排序约束力**:Kahn 拓扑排序只吃 `dependencies`,`weak_dependencies` 不进 adjacency/in_degree(`tools/graph_algo.py:354-361`)。
- **低优先级**:环检测含 weak 边(`tools/graph_algo.py:162-165`),断环时 weak = category 0 / confidence 1,环里**第一个被砍**(`tools/graph_algo.py:281-285,308-310`)。
- **V01 豁免相位检查**:悬空引用检查**包含** weak(悬空仍 BLOCKER,`verify/checks/v01_dependency_closure.py:44`);但 phase_inversion 检查**只看 `dependencies`**(`v01_dependency_closure.py:56-61`)。
- **S1/S2 不消费**:S1 的 `_make_S3_fields` 只建空容器(`nodes/s1_generation.py:275-278`),所有 procedure 由 S1 从 transition obligation 生成,与依赖边无关 → 覆盖用例不因降级而消失。
- **可见可审计**:可读报告以「**弱依赖**:…」行输出(`main.py:624-626`);S4 多实例展开正常传播(`nodes/s4_multi_instance.py:270`)。

**为什么可以排期**:当前 pipeline 不静默丢边——边以 `transition_upstream_phase_inversion` 为 origin 保留并审计可见;②③ 校验闸门(validate_p2 重推导 + P1 结构化字段)已兜底,不会静默出错。

**⑤ 要补的残留缺口**:因果**顺序不强制**——T-012 回滚用例照常生成,但最终序列不保证排在 T-016 后,V01 也不拦。属"缺显式标签/排序",非"信息丢失"。

**⑤ 设计(已定,实施时按此)**:S3 phase guard 中 `dep_phase > my_phase` 时,查被依赖 TO 的 `direction` 字段;若 `direction ∈ ("backward", "resume")` → 保持 hard_dependency + judgment "backward 边相位反转属预期";否则 → weak_dependency(现状不变)。enabler 侧检查对当前用例(T-016 forward)不必要。

---

## 参考:①③④ 系列已落地

- ① P2 derive 修复:`context/co_derivation.py`(共享派生规则,generator 与 validate_p2 同一份)。
- ③ 校验闸门:`context/verify/validate_p2.py` 尾部 dependent-uniqueness 重推导 + 洞4(同 (enabler,dependent) 边跨 causal_type 冲突检查)。
- ④ P1 结构化字段:`target_from`/`target_to` 已回填 28 条 XC,`context/P1_Prompt.md` XC schema 已加必填说明。
