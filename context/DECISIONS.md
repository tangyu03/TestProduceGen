# P2→P3 管线修复决策记录

记录 P2 义务模型 / P3 程序生成的修复决策(①②③④⑤ 系列)与已验证事实。
新增条目追加到顶部,每条含日期、决策、证据链。

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

**残留**:V06 4 项(T-039 派生的 PROC-025/026 缺 mechanism),另一问题,排期。

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
