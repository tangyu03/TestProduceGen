# P2→P3 管线修复决策记录

记录 P2 义务模型 / P3 程序生成的修复决策(①②③④⑤ 系列)与已验证事实。
新增条目追加到顶部,每条含日期、决策、证据链。

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
