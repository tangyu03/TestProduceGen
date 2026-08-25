# P2→P3 管线修复决策记录

记录 P2 义务模型 / P3 程序生成的修复决策(①②③④⑤ 系列)与已验证事实。
新增条目追加到顶部,每条含日期、决策、证据链。

---

## 2026-08-25 ㊿-G 事件台账注册为模型一等注册表，F10/F15 校验落地（修复 pt_srs03 61 项校验错误）

**问题**：`srs_data/pt_srs03.py`（P1.5 新数据文件）头部事件台账（57 条 e01..e35）只写成注释块，从未注册进 DomainModel → C21(INV-4) 将 note 中 e 标签判为「未映射局部标签」→ 59 条 C21 错误；另有 2 条 C24（b18/b32 多实体 BR 缺 constrained_entity）。共 61 项 critical，CLI 中断。

**根因**：事件台账是 glm5pr §2 定义的一等概念（F4 标签引用含 e 标签 / F10 双向覆盖 / F15 主体映射实体 均为规格要求的框架校验），但实现只把台账写成注释 → 引用失联、规格校验缺位。

**决策**（用户确认范围=完整规格；签名以用户同步项为准）：
1. **`model.add_event(eid, subject, dimension, action, actor, precondition, consequence, source_ref)`**（**8 列契约**，与台账格式一致；无 note 参数，inferred 依据落数据文件注释）注册到**内部标签映射表 `self._events`（dict eid→记录）**供 F4/F10/F15 读取；`self.events`（list）仅作输出 payload → `domain_model.events`（57 条）。**不做编号移交**：e 标签即正式 id，不进 allmap/_assign_ids（`_LOCAL` 正则本就匹配，原样保留，eid 自足）。
2. **schema.py** 新增 `"event"` 对象表：eid/subject/dimension/action/actor/precondition/consequence/source_ref 全 required。**eid 参数用 add_entity/add_role 惯例**（dsl="eid"、out="id"、written_by=LLM），非 tid/xid 的 id_transfer 惯例（事件无移交）。**validate_llm 按 `[etxbi]` 正则（constants.EVENT_LABEL）对 eid 做形状 fail-fast**——注册即拒非法标签（abc/E01/e1234/5e01 拒，e01/e03b 收）。
3. **C21** valid 集追加 `set(self._events)`；**新增 C26(F15)**（事件 subject ∈ 已登记实体）与 **C27(F10)**（正向：每事件被 ≥1 转换/关系 note 消费；反向：每转换 note 引用 ≥1 事件，inferred 闭环转换豁免——note.comment 含「inferred」）。
4. **verify_schema.py / verify_schema_reverse.py** 同步注册 event 对象（MAPPED_METHODS/COLLECTIONS/COLLS）。
5. **数据层**：pt_srs03 台账注释块 → build() 顶部 57 条 `m.add_event(...)`（主体名→E-XXX 映射）；b18 补 `constrained_entity="E-JK"`（操作对象=缴费单）、b32 补 `constrained_entity="E-XM"` + note 注明「代表实体（平台性能要求，非实体门禁）」。

**坑**：`LOCAL_LABEL` 正则 `\b[a-z]{1,3}\d{2,3}[a-z]?\b` 的 `\b` 对 CJK 无效（Python `\w` 含汉字）——「e12后续」的 `后` 吞掉词界导致 e12 匹配失败；修法=数据侧加空格「源自 e12 后续」。

**验证**：CLI `--strict` 0 error / 11 warning（C02×2/C05×2/C13×5/C17×2，全为既有数据语义，与本次改动无关）/ 28 autofix；`domain_model.events` 57 条，F10 双向全覆盖 0 orphan，t11b/t26b/t26c 经 inferred 豁免；verify_schema 正向（163 对象 0 错误）与反向（trace 163 条全命中）双 PASS；回归 pt_srs.py / struct_srs.py 0 error 不受影响（未调 add_event、C26/C27 空转）。

---

## 2026-08-25 ㊿-F dimension_entry_anchors 已删除，入口相位改为数据长出（第一性原理）

**问题**（用户定调）：㊿ Fix 2a 的 `_context.dimension_entry_anchors`「像是为了这个任务硬编码的一段」——1 条手写配置（E-PJ.评价状态→E-BMJL.结果已提交）只服务评价用例，还须 P1+P2+模型三处同步。

**决策**（用户选「后置 +1」门禁语义 + 「外科手术」数据落点，废弃配置机制）：

1. **领域真相进数据通道**：把门禁写成 T-046（待评价→评价中）的跨实体 `state_ref` 前置 `报名记录.结果已提交`（P1 pt_structuredv1.json → P2 透传 → 模型 pt_coverage_obligationsv1.json，与 T-025 报告编制绑定的 state_ref 同通道；R6 自动同步 `precondition_state_refs` pattern=p1_inherited）。
2. **策略 0 推广**（s0_topology.py `_entry_from_gated_preconditions`，替换 `_entry_anchor_phase`）：按转换锚定——对维度内每条转换扫描主实体 state_ref 前置，取 `ref_phase+1` 为 target 相位，再沿相对相位映射回传 `entry = ref_phase+1 - rel_phase_map[target]`。落地：E-PJ.评价状态 = {待评价:3, 评价中:4, 已确认:5, 退回修改:4}，与㊿ 手写布局一致但由数据长出，配置机制三处全删。
3. **回归面为空**：其余从属维度无跨实体 state_ref 前置，ref 路径不被使用（E-SP/E-XM/E-BZK 相位零变化）。

**验证**（`s1_fix_replay --recompute-s0 --coverage pt_coverage_obligationsv1.json`，归档 pt_outputv1.json）：
- 601 procs；temp_id +80/-80 为**纯再编号**（80/80 内容键匹配，零内容变化，总数不变）；
- dep_state_phase_map 实测 E-PJ={待评价:3,评价中:4,已确认:5,退回修改:4}，与用户批准 preview 完全一致；
- T-046 对应 PROC-130（启动评价）guard6_precond 依赖 报名记录.结果已提交 生产者（PROC-103 提交结果 / PROC-105 重新提交结果）——跨实体边由数据长出；
- 双重跑 SHA-256 一致；V01-V10 全 pass、0 blocker、0 warning；V08 STRICT_FORWARD 仍成立（已确认=P5）。

**遗留**：同㊿——replay title 由归档 overlay（601 hit 0 miss），正式交付走 main.py 全流水线；pt_srsv2.py（E-PJX 五态评价项）迁移为独立任务。

---

## 2026-08-24 ㊿ 评价维度入口锚定 + 报告编制绑定评价完成（用户定调衔接报告编制）

**问题**（用户反馈）：`pt_outputv1.md` 中评价用例 PROC-040~050 挤在 P0/P1/P2——「评价应该在 PROC-121 结果提交后」。根因：P2 phase_mapping 是维度内**相对序**（各维度入口态都=0），E-PJ.评价状态 无任何结构化前置引用主实体状态 → `_compute_entry_phase` 策略 0/5 都返回 0 → 待评价=0。CO-003（E-XM 创建同步）是**实例存在**关系（待开始=P0），不是相位关系，不提供「结果提交后开始评价」信号。

**决策**（用户选「衔接报告编制」布局；两个数据驱动的机制，均单一真相源在 P1 数据层）：

1. **维度入口锚定（Fix 2a）**：新增 P1 `_context.dimension_entry_anchors` 配置（与 phase_anchors 同构），声明 `E-PJ.评价状态 → anchor E-BMJL.报名记录状态.结果已提交`。S0 `_derive_dep_state_phase_map` 的显式 phase_mapping 分支消费：入口相位 = 锚定状态绝对相位（**不加 +1**——入口态与锚定状态**同段**触发，如 待评价 与 结果提交 同在 P3），`_entry_anchor_phase` 优先级高于策略 0。P2 Step 5 透传配置到模型 `_context`。落地后：`{待评价:0,评价中:1,已确认:2,退回修改:1} → {3,4,5,4}`。
   - **V08 约束**：forward 严格递增（T-049 评价中→已确认）→ **已确认=P5 而非用户 preview 的 P4**；preview 的「结果确认 P4」会让 T-049 forward 不递增 → V08 blocker。合法布局整体右移 1 段（P4→P5），相对顺序不变、无倒挂。T-048（退回修改→评价中）同相位 forward 走 anomaly 豁免（与改造前一致）。
2. **报告编制绑定评价完成（Fix 2b）**：P1 把 T-025 前置「评价已完成并统计」由 event_ref（ref=null，永不解析）改为 state_ref(E-PJ.评价状态.已确认)。R6 自动同步 `precondition_state_refs`（p1_inherited）→ S1 `_max_state_ref_phase` 把 T-025 用例抬到 P5（phase_basis 实测："报告/证书审核中 → bumped to P5 (state_ref 项目评价.评价状态.已确认)"）+ S3 Guard 6 建依赖边 → 拓扑排序 评价确认(PROC-147)→编制报告(PROC-148)→发放(PROC-149)，**无倒挂**。

**验证**（`s1_fix_replay --recompute-s0 --coverage pt_coverage_obligationsv1.json`）：
- 601 procs，+0/-0 内容签名（115 条 host-state 修正 = 未发送→报名待审核，0 增 0 失）；
- 评价相位分布 {0:22,1:6,2:8} → **{3:22,4:6,5:8}**（整体 +3，P0-P2 评价用例清零）；待评价 P3、评价中 P4、已确认 P5、编制报告 P5、发放 P5；
- 双重跑 SHA-256 一致（确定性）；V01-V05/V07-V10 全 pass、V06 skipped、**0 blocker**；
- Fix 1（`_anchor_creation` 主维度优先，㊿ 前已在 domain_precondition.py 落地）回归通过：115 条无维度 CRUD givens 全部「报名记录已存在，处于报名待审核状态」（原 未发送）。

**遗留**：replay 输出 title 由归档 overlay（601 hit 0 miss）——host-state 修正体现在 givens/thens 正文，title 仍显示归档旧文本；正式交付走 main.py 全流水线（LLM 生成新 title）。已确认=5 偏离用户 preview 的 4，若坚持 P4 需改 T-049 direction 数据或放宽 V08 STRICT_FORWARD（未做）。

---

## 2026-08-22 ㊾ 主实体自身次维度相位未锚定——根因定位 + 修复方案评估（方案A已实施）

**问题**：主实体（E-BMJL 报名记录）自身的**非主维度**状态机（发票状态 / 报名记录样品状态 / 费用状态 / 通知状态）未进入任何相位映射 → S2 全部 `fallback`→P0 → 同实体跨维度排序退化为中文字典序（发票→样品→状态→费用→通知），报名记录内部未按生命周期组织（用户三连问：项目生命周期 / 报名记录生命周期 / DAG 业务时序 的根因之一）。

**证据链**：
- `phase_table.state_to_phase` 只含 primary_dimension（报名记录状态）1 个键；
- `dep_state_phase_map` 只含从属实体 6 条目（E-BZK.标准库状态 / E-PJ.评价状态 / E-SP.审批状态 / E-SYS.实验室状态 / E-XM.项目状态 / E-XM.样品状态），主实体 E-BMJL 不在其中——`_derive_dep_state_phase_map`（s0_topology.py:1740）明确 `if entity == primary: continue`；
- 实测 pt_outputv1 172 条基础用例：100 锚定 / 18 纯 fallback / 20 data_section_defer / 21 domain_precond_creat / 9 parent_primary_phase / 3 primary_entity_max_phase；**18 条纯 fallback 恰好 = 这 4 个子维度的全部用例**（发票 2 + 样品 4 + 费用 2 + 通知 10）；
- 对照：从属实体 E-XM.项目状态 = 待开始0→报名中1→进行中2→报告审核中3→已结束4 **正确锚定**（项目生命周期其实排了）→ 证明锚点法本身有效，缺口只在"主实体自身次维度"。

**入口信息仍然可得（不依赖已删的 transition_upstream_map）**：这 4 个维度入口态（待缴费 / 待开票 / 待发样 / 未发送）全部由**报名转换的级联效果**驱动（PROC-011 then："费用状态联动初始化为待缴费；发票状态联动初始化为待开票"），报名=phase 0（phase_table: 报名待审核=0）→ 入口 phase 可直接从主维度转换的级联声明锚定，再沿次维度自身转换链传播（state_type_map 区分 driving/side_effect）。`transition_relations` 仅 3 条（短信/退款），不承载该信息；cascade 声明是活数据。

**候选方案**：
- **A（推荐）**：锚点法 (a)~(f) 对主实体自身次维度也生效——anchor=主实体自己、锚映射=phase_table 主维度、入口 phase 从主维度转换级联声明（"联动初始化"）取、再沿次维度自身转换链传播。改动点：S0.3 手稿（(c) 已标注 ㊾ 待定）+ `_derive_dep_state_phase_map`（去 primary continue，补主实体次维度分支）。
- **B**：次维度作为"内部从维度"统一并入 dep_state_phase_map 同规则处理（与 A 等价，实现路径略异）。
- **C（不做）**：恢复 transition_upstream_map 入口锚定——已由 ㊼ 关闭（正向论证：同实体链冗余 + CO 边 hard 语义与 ㊻ 矛盾），复活路径不开放。

**影响面**：S0 重跑 + S2 sort_key 变化 → 报名记录内部按生命周期重排（P0 内由字符串序变业务序，如 报名→审核→缴费→发样→通知）。需回归校验：标题/givens/thens/deps 语义内容不变，仅 phase/sort_key/temp_id 顺序变化；确定性双跑 SHA-256 验证。

**状态**：**方案 A 已实施（2026-08-22）**。落地路径与评估时的 A 略有出入但效果等价且更小改动：**不**动 `_derive_dep_state_phase_map` 的 primary continue，而是把主实体次维度**并入 `phase_table.state_to_phase`**（新增 `_enrich_primary_sub_dims`，`_derive_phase_table` 加 `include_sub_dims` 参数，pipeline 主调用 3117 传 True；从属/虚拟实体复用路径 2067/2151/2774/2801 保持 False——它们的 shift 逻辑遍历全维度，多键会污染）。理由：`_resolve_phase` 对主实体只查 `phase_table.state_to_phase[dimension]`，并入后 S1/S2/S3 零改动；且 4 个次维度的 `phase_mapping` 已由 P2 显式写入 `state_info`（实测 通知状态 6 态 / 样品 4 态 / 费用 2 态 / 发票 2 态全带显式 phase_mapping），无需再从级联声明推导入口——`_get_explicit_phase_mapping` 直接取值，确定性。相邻观感问题（审核通过 P1 vs 审核退回 P0 按目标态分拆同一动作）**未处理**，保持现状。

---

**决策**（用户定调：P2 过期判据一并修正；数据迁移只迁 struct_srs，golden 数据文件冻结靠向后兼容）：`add_xc` 加 `xc_source` 参数（枚举 `XC_SOURCES`=镜像/4.5判/联动/分支差异），desc 契约改为**只写语义内容、不含来源前缀**；assemble `_assign_ids` 内 `_rebuild_xc_desc` 按 `xc_source` 用 `XC_DESC_TPL` 重建最终 desc（前缀 + 注入正式标签）。旧数据（golden 冻结）缺省 `xc_source=None` 时用 `XC_LEGACY_RE` 从旧 desc 前缀反推来源并剥掉残留 `T-tXX` 局部标签。

**根治的两个脏数据**：
- **T-T-019 双前缀**（golden `CASC-STEC-PT017.py:2746` 写 `镜像T-t13 …`）：`_LOCAL` 只匹配 `t13` 留 `T-` → 拼出 `镜像T-T-019`。现在框架剥前缀后按 `镜像 {label} {desc}` 重建 → `镜像 T-019 …`（label 注入 target_transition，与 C04 同源）。
- **P2 过期前缀判据永不命中**：`由 Step 4.6`（数据一直是 4.5）→ 改 `4.5`；镜像/联动重建后自带空格（`镜像 T-`/`联动: T-`），P2 判据直接命中 → 4.5判 XC 的 coverage_priority 由 medium 升 high。

**C23 改判**：`desc.startswith(XC_DESC_PREFIXES)` → `x.get("xc_source") not in XC_SOURCES`（desc 前缀现由框架生成，不再作为来源判定依据）。

**C25 新增**（改写后盲区闭合）：镜像类 XC 的 `target_transition` 非空——镜像记录「哪个转换持有跨实体前置条件」，空即漏登记。struct x04（评审计划超时结束→待归档）原缺 target_transition，迁移时补 t07（与 x03 同消费者锚）。

**验证结果**：verify_schema SCHEMA/REVERSE OK；struct/golden assemble 0 error、C25 零命中；golden XC-001 双前缀修复且数据文件未动；P2 self-check 全过、4.5判 cp 升 high；grep 无 `T-T-`/`镜像T-`/`联动:T-` 残留。★注意：镜像 desc 的 {label} 取自 `target_transition`（若空回退 source_transition）、联动取 `source_transition`（生产者）——维护 `XC_DESC_TPL`/`XC_LEGACY_RE` 必须三表同步（constants.py + 模板注释）。

**维护对照表（防「已删清单项」的防线静默消失）**：prompt.md 曾把下列清单项从 prompt 内移除，各自有框架兜底校验兜着；裁剪/调整校验前先查此表，缺兜底项明示为唯一防线：

| 已删 prompt 清单项 | 兜底校验 |
|---|---|
| frm 不得为终态（Step 4.1 速查） | C02（state_structure）/ C13（direction） |
| 终态有出边则非终态（Step 4.1 速查） | C02 / C13 |
| 分支穿透三覆盖（Step 4.3 自检） | C05（branch_penetration）/ C20 |
| crud 回填对应转换或无对应转换（Step 4.3 自检） | C12 |
| 同起讫转换动作一致性 | C09 |
| 跨实体通用操作仅登记一次（Step 1 写完即扫） | **无框架兜底**（唯一防线，明示） |

**判据速记**：desc 前缀=框架产物非 LLM 输入；来源判定只看 `xc_source`；新来源分类必须三表同步（`XC_SOURCES`+`XC_DESC_TPL`+`XC_LEGACY_RE`）否则旧数据反推不到。

---

## 2026-08-14 ㊼ 正式关闭 transition_upstream_map 双键索引行为变更（正向论证：新方案劣于现状）

**决策**：把 `to_by_tid`/`trans_id_to_proc_ids` 改按 `id`（双键）索引的待定项**正式关闭，不做**。S3「1. Transition upstream」块保持按 transition_id 索引的惰性 no-op，加显式守卫注释 + 重新激活路径（s3_dependency.py:241-262）。

**正向论证（回应「已经被替代」≠「替代得对」，非负推理）**：id-keyed 模拟实测——upstream_map 会物化 **112 条边 = Source1 同实体链 107 + Source2 CO 5**（80 keys）：

1. **107 条同实体链边 = 纯冗余**。它们来自 S0.6 Source 1（同维度 T2.to==T1.from），是**无语义**的文本态链匹配。Guard 1（`guard1_state_pred`）与 `chain_ordering` 已按语义（状态链匹配、创建根跳过、相位守卫）派生同类 deps——上游图路径再加一遍零信息增量，只增 break_cycles 全图 churn（实测过的 54 proc 级联）。
2. **5 条 CO 边已被 co_enabler 绑定以更优语义物化**。co_enabler 绑定产出 weak + `co_enabler_both_lateral`/`co_enabler_phase_inversion` 标签（带 ㊻ lateral 定谳）；而上游图路径会给 CO-004（T-058/T-062 双 lateral）标 `transition_upstream` conf-5 **HARD**——与 ㊻「lateral 下 hard 语义不成立」**直接矛盾**。该路径对 CO 边不是冗余，是**语义错误**。
3. **可观察空索引（激活路径保持）**：coverage TO 0/91 有 transition_id → `trans_id_to_proc_ids` 恒空 → 本块文档化 no-op。若上游某日回填 transition_id，本块自动复活——守卫注释明示复活前须先解决上述 1/2 两条（去重 + lateral hard 语义）。

**验证结果**：仅注释变更，零逻辑差异（s3_dependency.py 解析通过，无代码路径改动）；PT017_output 无需重生成。

**判据速记**：物化的边要么冗余（同实体链已被 Guard1/chain_ordering 语义化覆盖）、要么语义错误（CO 边 hard 与 ㊻ 矛盾）。上游图路径不携带任何新信息 → 双键索引劣于现状。

---

**2026-08-22 更新：消费点已清除（机制删除，复活路径关闭）**。依用户指令"清除 transition_id 相关消费点"，`transition_upstream_map` 机制连同全部死消费点已删除：S0.6 重建（`_rebuild_upstream_map`/`_build_state_pos`/`_tid_to_concrete_ids`）、Strategy 1 入口锚定、fixpoint 死循环、`_detect_contextual_phase_rules`、S1 depth_cache（`calc_all_chain_depths` 及 graph_algo 的 `build_transition_graph`/`calc_chain_depth`）、S2 死读、S3 "1. Transition upstream" no-op 块、恒空 `to_by_tid` 双索引、models/main/run_pipeline 字段透传。`_S2_fields.chain_depth` 保留写 0（break_cycles tiebreaker `.get(...,0)` 行为不变）。**保留**：活代码内散点 `transition_id` 死读（s0 primary 选择等，防御性）、CO 活字段 `enabler_transition_id`/`dependent_transition_id`。验证：`--recompute-s0` 确定性重放，procedures 语义内容（标题/givens/thens/deps/phase/sort_key/temp_id）与清除前零差异，仅 engine_state 少 `transition_upstream_map` key。**复活路径已关闭**——机制从文档（s0_prompt §11）到实现（graph_algo 死库函数）整体移除，不再有"回填 transition_id 自动复活"的路径；因果顺序完全由 guard1_state_pred + chain_ordering + co_enabler + Kahn 拓扑排序承接。

---

## 2026-08-14 ㊻ CO-004 hard-vs-weak 定谳：lateral 转换下 hard 语义不成立 → 双 lateral 规则落地 + 双表注册陷阱

**决策**（用户定调「选 1，但不是倾向 weak，而是 hard 在状态机模型里语义不成立」）：S3 co_enabler 块按**双 lateral 规则**分流：

```
en_to = to_by_id[enabler_transition_id]（或 to_by_tid）
dep_to = to_by_id[dependent_transition_id]（或 to_by_tid）
both_lateral = en_to.from==en_to.to AND dep_to.from==dep_to.to

both_lateral            → weak_dependencies + origin "co_enabler_both_lateral"
dep_phase > my_phase    → weak_dependencies + origin "co_enabler_phase_inversion"
dep_phase <= my_phase   → dependencies（HARD）+ origin "co_enabler"
```

CO-004（E-CAR T-058 已登记→已登记 提醒，enabler；E-USER T-062 正常→正常 功能限制，dependent）**双方都 lateral** → weak。CO-001/002/003（E-ARC/RCY/OUT T-018/036/042 执行中→已归档/已回收/已外送，enabler；E-CAR T-055/056/057 已登记→…，dependent）→ 相位反转 → weak。

**决定性论证（唯一判据，非多条之一）**：hard 依赖的语义前置是「前驱的**状态推进**是后继的前置条件」——前驱转换让状态机前进到某状态，后继才有资格执行。而 **lateral 转换（from==to）不推进任何状态**，状态机层面没有「前置被满足」这回事 → hard 在状态机模型里**结构性不成立**，不是「倾向 weak」而是「hard 语义失效」。辅助证据：① 时间先后（提醒 12h 前触发）是业务时序差，非因果门控——系统宕机时提醒没发出、限制照样执行（条件=已到期未处理，非「提醒已执行」）；② 限制真正的前置是状态条件（载体到期未处理），不是「提醒转换已执行」。

**双表注册陷阱（用户判「规则被否决的理由是实现 bug」）**：co_enabler_phase_inversion/co_enabler_both_lateral 只注册进 `s3_dependency.DEP_CONFIDENCE` 时，实测 `_exp_rule2` 仍 22 dep 差异（CO 弱边被剪、倒退边恢复）——因为 `tools/graph_algo.py` 内联了一份**独立** DEP_CONFIDENCE（注释「kept in sync」，circular import 规避），缺新 tag → conf 归 0 → break_cycles 按低 conf 优先剪 CO 边。**两表都必须注册新 origin**。注册后 `_exp_rule3`：dep 集合 0 差异（方向正确、CO 边保住）+ 10 处 tag-only 差异（语义可区分：CO-004→`co_enabler_both_lateral`，CO-001/002/003→`co_enabler_phase_inversion`）。

**正向推理修正（回应「已经被替代」≠「替代得对」）**：此前主张「CO 绑定替代 upstream map → 弱化不必验证」用的是**负推理**（冲突/级联），用户正确指出这混淆了替换场景与叠加场景。最终结论（全 weak + CO 方向正确）以**正论证**重新确立：lateral 下 hard 语义不成立是构造性证据，非行为后果。upstream map 双键索引行为变更仍待定（CO 绑定已实现同批弱边，见 [[transition-upstream-map-inert]]）。

**验证结果**：`_exp_rule3` 双跑 SHA-256 字节一致；与合入 PT017_output.json 的 dep 集合（dependencies/weak_dependencies）逐 proc 零差异；仅 10 处 `weak_origins` 标签变更外科合入（PROC-051.1/.2←PROC-076/077 → `co_enabler_both_lateral`；PROC-103/104/105 .1/.2←PROC-225/231/228 → `co_enabler_phase_inversion`）；681 标题保留、dep 不变、CRLF+无尾换行保持；V01-V10 全 PASS（case_total 681，全零）。

**判据速记**：hard 依赖的前置=前驱状态**推进**；lateral（from==to）无推进 → hard 结构失效，非倾向。任何新 origin tag **必须双表注册**（s3_dependency.DEP_CONFIDENCE + graph_algo.py 内联表），缺一即 conf 0 剪错边（实测）。

---

## 2026-08-12 ㊺ 删除 time_sensitive 用例的触发方式 hint 行：`scheduler_manual_trigger:/clock_injection:/db_time_update:` 不再作为 When 编号步骤注入

**决策**（用户判「添加的位置和实际需求的不一样。如无必要可以删除」→ 删除）：S1 `_build_timeout_hints()` 不再把 3 种触发机制描述（`clock_injection: 测试时注入时钟到边界值` 等，AI 措辞）注入 `operation_hints`。time_sensitive 用例的 When 块恢复为只有真实执行事件（如 PROC-197 `1. 确认导入完成 by 普通用户`）；触发机制保留在 JSON `time_control.mechanism`（V06 协议字段，机器可读）。删除函数 `_build_timeout_hints`/`_TRIGGER_HINT_TEMPLATES`/`_ALLOWED_TRIGGER_METHODS`，保留 `_derive_time_mechanism`（仍供 `time_control.mechanism` 推导，3 处调用）。

**为何可删**：
- V06 只校验 JSON `time_control.mechanism ∈ allowed_mechanisms`（`v06_time_control.py:43-44`），不读 operation_hints → hint 行非闸门负载。
- 需求原文自陈触发语义（t06「如未确认48小时后系统自动结束并删除导入文件」），Given 括号（`时间边界条件: 接近截止时间`）与 action 后缀（`(时间边界)`/`(已过期)`）已传达时序上下文 → hint 行零新增信息。
- 3 种机制全列当编号步骤、与真实事件混排，把测试基建措辞冒充业务操作——PROC-197 需求是「系统自动结束」，列 `clock_injection`/`db_time_update` 与本用例语义不符（误导读成「注入时钟」「改库时间」步骤）。

**验证结果**：重跑 727 procs，temp_id +0/-0，title overlay 727/0，双跑 SHA-256 字节一致；`time_control` 51 procs（scheduler_manual_trigger=25/clock_injection=13/db_time_update=13）保留；md 全文件 0 条 hint 行；Gate-S V01-V10 全 pass，V06 `time obligations=8, missing time_control=0`，signature null。

**判据速记**：V06 协议字段（JSON time_control）与 md 可读性解耦——机器协议留数据层，AI 措辞的「测试基建」行不冒充业务步骤。time_sensitive 语义上下文已在需求原文/Givens/action 后缀承载。

---

## 2026-08-12 ㊹ 三处语义净化下沉到数据层（S1 标记）：规则兜底/复述 desc/Then 吸收

**决策**（用户定调「三处全下沉」）：把此前在渲染层（main.py）用文本反查/逆解析实现的三个**语义型**净化全部下沉到数据层 S1，渲染层变纯格式选择器，不再反查 coverage_model 或拼接模板比对。三个纯格式净化（裸实体 target 省略、属性含「状态」时 `=` 运算符、`--hide-markers` 标签隐藏）留在渲染层——它们本就是格式选择，无语义决策。

**下沉的三个语义判定**：
1. **规则兜底 Given**（`given_type="rule"` / `"rule_noise"`）：Type7 neg_op 站 desc 由 `"规则：{原文}"` 改存纯 `{原文}`、标记 `rule`（有效规则上下文，负向模板 When/Then 只含被禁操作，规则原文只在 Given 呈现，PROC-262 删了丢规则）；两个「…相关数据已准备」空泛占位站标记 `rule_noise`（渲染直接跳过）。渲染层删除 `_is_rule_noise_given`/`_proc_br_texts`/`_br_rule_map` 三个反查 helper（原按 `desc 含被测 BR 原文？` 对照 coverage 判定，现判据在数据）。
2. **复述 desc**（`given_type="restatement"`）：Tier 2 领域前置的 `object_existence` 对象实例复述 desc（`{实体}已存在，处于{状态}状态`，全量 200 处/7 唯一形态）标记 `restatement`，渲染按 `- {desc}` 句子形态输出。渲染层删除 `desc == f"{target}已存在…"` 的模板拼接比对（该比对只在翻译后 target=中文名时命中，属隐性文本约定耦合）。
3. **Then 吸收**（`ThenClause.subsumed` 新字段）：transition_target 状态行（`状态转换为X`）被同 target 的 behavior 行（`状态…为X`，如「导出任务创建，状态初始化为草稿」）完全包含 → S1 后处理 `_mark_then_subsumption(valid_procs)` 标记 `subsumed=True`，渲染层 `_dedup_thens` 只消费标记。标记量 **152** = 旧渲染层文本比对的命中数（321 条 transition_target 中 169 条无复述者保留），逐字复刻。

**为什么下沉**：语义决策（某 Given 是否噪音、某 Then 是否冗余）属数据层职责；渲染层做文本比对/模板拼接把「数据层文本约定」耦合进渲染逻辑（㉛ 已确立「引擎层打标记、渲染层只消费标记」）。下沉后渲染层不再依赖 `规则：` 前缀、BR 原文可解析性、target 翻译状态等隐式前提。

**验证结果**（s1_fix_replay 确定性重跑 → Gate-S 全量）：
- 重跑 727 procs，temp_id +0/-0（结构 1:1），title overlay 727 hit/0 miss；双跑 SHA-256 字节一致（确定性范式未破坏）。
- 数据层：given_type 计数 state=485/constraint=393/restatement=200/rule_noise=61/rule=6/event=50/branch=165；`subsumed=True`=152。
- Gate-S V01-V10 全 pass / 0 fail，signature null，case_total 727，coverage_misses=0。
- 渲染核查：PT017_output.md PROC-067 Given=纯规则原文（无 `状态 = 规则适用前提满足` 哨兵前缀、无 `规则：` 前缀）；PROC-001 Then 只剩「导出任务创建，状态初始化为草稿」（`状态转换为草稿` 被吸收）；`相关数据已准备` 与 `状态 = 规则适用前提满足` 全文件 0 命中。

**判据速记**：语义决策（Given 噪音/Then 冗余/句子形态）在数据层标记；渲染层按标记选格式，不做文本比对/模板拼接/coverage 反查。纯格式净化（省略主语、运算符、marker 隐藏）留渲染层。判定「下沉完整」= grep 渲染层无 `规则：` 前缀剥离、无 `已存在，处于` 拼接、无 transition_target 文本比对。

---

## 2026-08-12 ㊸ 同文 BR 一实体一条的合并（9→1）：`_backfill_branch_coverage` 无实体作用域 → 配置用例 Then 重复 9 次清零

**决策**：数据层把 9 条**文本完全相同**的「任务级别」BR（b10..b18，每任务实体一条，source_ref 4.5.2/4.6.2/…/4.13.2）合并为 1 条（b10，`entities_involved` 并列 9 实体，`source_ref` 并列全条款）。P3 重生成后：PROC-013/014/015（E-IMP 任务级别 A/B/C 三个配置过程）的 **Then 从 9 条同文 BR 行 → 1 条规则**，procedures 727 不变，verdict pass / 0 blocker，V10 `BR 53/53 (embedded 7, xc_causal 14)`。

**根因**：`srs_pipeline/model.py` `_backfill_branch_coverage`（358-374）按 `re.split(r"[;；]", b["note"].get("branch_dimension"))` **只按维度名匹配、无实体作用域** → 9 条同文 BR 全挂进 E-IMP 任务级别 分支维度 coverage。P3 `_classify_business_rules` 把它们全判 attribute_effect（`s1_generation.py:2840-2850`），`_embed_brs`（3594-3598）全量嵌入 Type3 → 每条配置用例 Then 重复 9 次。用户 @PT017_output.md PROC-015 大量重复触发排查。

**为何合并而非实体作用域**：给 `_backfill_branch_coverage` 加实体过滤会让 8 条 BR 各自落向所属实体 → `br_embed` 兜底把规则铺到另外 8 个过程（E-REG/E-ARC/… 的配置用例），只是把 9×1 变成 1×9，重复总量不变还更散。这 9 条本就是**一条规则适用于 9 类实体**（4.6.2 等条款与 4.5.2 同文），正确建模 = 合并为一条多实体 BR。分支维度本只定义在 E-IMP，其它 8 实体无 任务级别 分支维度（P2 `branch_dimensions` 只 1 条），Type3 单过程、不嵌 BR。

**验证结果**（P1 0 error/5 warning → P2 TO 91/BR 53 描述全唯一、E-IMP 任务级别 coverage=['BR-011'] → P3 727 → verdict pass）：
- 输出核查：PROC-013/014/015 Then = 行为期望行 + `[BR-011]正面`（含 `[cross: 载体登记任务,…8 实体]` 合并语义）+ `[BR-011]负面` 各 1 条，无重复。
- 原始 `embedded_brs` 为 `['BR-011','BR-011']`（`_type3_then_expectation` 2206-2208 取 coverage 首条作行为期望 + `_embed_brs` 各记一次），渲染层按 BR id 去重 → md 只显示一次。此「双路径同 id」与旧文件 10 条（BR-011×2+BR-012..19）同机制，非 bug。
- BR 重新编号一致性：BR-012..BR-019 现在指向别的规则（48小时自动删除/用户账号规则等），非旧规则残留；53 条 BR 描述两两唯一。
- V05 advisory 99 不变（㊷ 已知噪音，与本次无关）；V10 embedded 由合并前更多 → 7。

**判据速记**：coverage.business_rules 回填 = 「维度名 1:N BR」匹配，若同一规则被按实体拆成 N 条同文 BR，会 1 个分支过程嵌入 N 次 → 数据层合并为 1 条多实体 BR 才是正确建模；「修复」要看渲染输出而非原始 embedded 列表（双路径可能记两次同 id，渲染去重）。

---

**决策**：修 P2 `generate_obligation_model.py` 的 R5 组合过滤 + 数据层补 9 条 审批拒绝 precond，使任务级别分支维度符合业务规则：**A级无需审批直入待执行；B级仅一级审批；C级二级审批**（证据：数据模块 4.5.2/4.6.2/…/4.13.2「任务级别为A级无需审批；B级需经过一级审批；C级需经过二级审批」）。P3 重生成后：procedures **859→727**（-132 非法组合），TO **127→91**，verdict **pass / 0 blocker**。

**根因（三层叠加）**：
1. **`branch_dimension.target_transition` 名/id 错配死代码**：分支的 `target_transition` 用的是转换**名称**（如「一级审批通过转换」），而比较目标 `t["id"]`（如 `"t02"`）——**永不相等**，`get_matched_dims` 恒落 all-values 兜底，每个分支转换对所有 3 个级别各生成 1 条 → 9 实体×(A级审批通过/拒绝 + B级直入 + C级直入)=36 条**非法**组合（A级断言审批、B/C级断言直入）。
2. **R5 组合过滤 `combo_conflicts_with_preconds` 只看 `state_dimensions` 状态**：任务级别是 `is_config` 属性（config 维度），不在状态集里 → 同级 3 值互斥无从发现，非法组合不被拦截。
3. **9 条审批拒绝转换缺「任务级别为B级或C级」precond**：数据层把「提交审批」误建模为可无条件走审批拒绝。

**落地**：
- `context/generate_obligation_model.py`：新增 `_dimension_value_universe(dim_name)`（遍历 `p1.domain_model.entities[].state_dimensions[].states` + `p1_bd` 的 values/分支 value 汇总维度值域），`combo_conflicts_with_preconds` 改为：`dim_name 出现在文本 且 val 不在文本 且 维度值域中存在其它同级值出现在文本` → 冲突。config 维度级别互斥由此可检出（同一转换内 givens 不能同时含 A级 与 B级）。
- `srs_data/CASC-STEC-PT017.py`：9 个 审批拒绝 转换（t03/t09/t15/t21/t27/t33/t39/t45/t51）各补 `precond(text="任务级别为B级或C级", ptype="constraint", ref=None)`，锚定在 `<实体>处于待审批状态` state_ref 之后。

**验证结果**（P1 0 error/5 warning → P2 TO 91 自检全 True → P3 727 procedures → verdict pass）：
- 输出核查：A级+审批通过/拒绝 = **0**；B/C级+直入 = **0**；B级审批通过/拒绝 33+33 保留（givens 含「任务级别=B级」，action 通用「审批通过/拒绝」，级别语义在 precond 不在 action 名）；C级同构 33+33；「提交XX申请（A级直入）」33 条为申请提交转换（含 2 或 5 个申请变体），非审批动作。
- V05 advisory 198→99，**全部 99 条逐一语义审计为假阳性**（复刻探针逻辑统计：B级任务仅一级审批 66 条 + A级任务无需审批 33 条 = 99；99 条中 `other_dim` 的值「二级审批/需要审批」**一处都不出现在文本** → 0 真违规）。注意 verdict `evidence` 数组只存前 50 条、`evidence_truncated=49`，真实数要读 `note` 的 `advisory hits` 字段，不能数 `len(evidence)`。
- **决策（用户确认「保持现状（设计如此）」）**：V05 note-type 探针不收紧。note-type 本就是「语义约束无法纯文本精确判定 → current 命中记 warning 提示人工复核」的设计（`v05_dimension_combo.py:12-14`），99 条是 working-as-designed 的复核候选，非 bug、非阻断；收紧会引入「文本不含 other_dim 值的语义违规漏报」风险。记录为已知噪音。
- 任务 #12/#13 关闭。

**判据速记**：分支维度 target 比较须用 `target_transition` 与转换 id 对齐的名称/标识，名/id 错配 = 死代码静默退化为全值兜底，是「看似全对实则错配」的隐蔽源；R5 组合过滤必须覆盖 config 维度（值域从 state_dimensions + branch_dimension 双向汇聚），不能只扫 state_dimensions；数据层「转换可无条件发生」的缺 precond 是业务规则漏写，校验器只能拦到「文本矛盾」，拦不到「缺前提」，须在数据层补齐。

---

## 2026-08-11 ㊶ V04 字段级保护废弃 case_spec readonly dict 数据源：唯一真相源在 P1 模型推导

**决策**：V04 字段级保护**只信 P1 数据层模型推导**（`_sysfields_from_model`：从 `_context.entity_details[].attributes.desc` 匹配自动/系统标记，产出实体限定的 `实体.字段` 精确模式）。case_spec `built_in_entities.readonly` 的 **dict 条目（字段名+clause+note 证据）整体废弃**，不再转 `*.字段` 通配参与保护。case_spec 仅保留实体级 UI 事实：readonly 字符串条目=readonly 实体名、no_form_page 两种形态=无编辑表单实体。

**根因（两处证据）**：
1. **通配跨实体误伤**：`*.文件级别` 命中 4 条 type3/9 then-target「文件扫描任务.文件级别」（PROC-037.1/.2、PROC-045.1/.2）。但 E-SCN 4.13.1 该字段 desc=「只可选:A级、B级、C级」——**用户选定字段**；case_spec 的"文件级别"clause=4.12.1（E-EXP 导出任务）且 E-EXP 根本没有独立文件级别属性（只有「文件列表」，上传时**用户确定**文件级别）。同名字段在不同实体可编辑性不同，字段名通配必然误伤。
2. **case_spec 字段证据不可靠且大多无意义**：测试架构为 AI 生成、未经人工确认（批判看待）。18 条 readonly dict 里，真正系统维护的字段（申请人/流水号/申请时间/申请部门/载体编号/载体到期提醒时间）**已全部被模型推导覆盖**（37 条）；其余（初始账号×3/内置角色×3/八种角色/密码重置默认值/载体持有时间默认值/载体快照/载体信息自动带入）都是**系统级记录、展示快照或默认值**，不是实体属性，字段名保护无意义。5 个真实 type3/9 then-target 经核验**无一**是系统维护字段（任务级别/文件级别/级别/载体类别/导出方式均为用户选定）——V04 正确结果为 0 失败。

**落地**：
- `verify/checks/v04_builtin_entity_protect.py`：readonly_ents 只收 readonly 的**字符串条目**；noform_ents 走 `entity_names_of`（两种形态）；sysfields 仅 `_sysfields_from_model`；废弃的 dict 条目在 note 中透明记录条数与清单（便于 verdict 阅读者理解）。
- `base.py` `entity_names_of`、`v09` 单例修（本会话先前）保留——`entity_names_of` 对 dict 取 `entity` 键，仍服务 no_form_page 与 V09 单例。

**验证结果**：`python -m verify.validators -s verify/PT017_case_spec.json -o PT017_output.json -m PT_017_coverage_obligations.json -j PT017_verdict.json` → **verdict=pass / blocker_failures=0 / warning_failures=0**，10/10 PASS。V04 fail=0（4→0），note 记录 18 条废弃字段证据；V10 TO 127/127 | EO 89/89 | BR 61/61 | IT 4/4 | state_misses=0；V05 198 条 note-type advisory 为既有 warning 非阻断。V09 崩溃（`set()` on dict）与单例修复同批验证通过。

**判据速记**：校验器字段级保护的数据源选择，遵循「单一真相源在 P1 数据层」——AI 生成的测试架构 case_spec 作为保护证据时须批判看待，字段名通配因同名跨实体可编辑性不同而不可靠；实体限定精确模式（`实体.字段`）是安全的保护形态。

---

## 2026-08-11 ㊵ validate_p2.py EO-ATC source_ref 契约陈旧：透传设计已确立，校验器未跟随更新

**决策**：修 `context/verify/validate_p2.py`——EO-ATC 的 source_ref 不再强制 null，改为 **null 或非空字符串（透传实体首条操作章节定位）**，并在 p1 块新增**数据驱动派生复核**闸门。生成器不改。

**根因**：两模块契约漂移。`validate_p2.py` 07-30 立 "source_ref should be null (P1 attr has no source_ref)"；`generate_obligation_model.py` 08-07 才加透传（`_entity_config_section_ref`：P1 属性无 source_ref 字段，透传实体首条带 source_ref 的操作的 source_ref 作章节定位，有注释+judgment 记录）——**透传是更新的设计且已确立**（when-then-render 渲染层依赖该章节定位），校验器是陈旧的原始契约，未跟随更新。git blame 铁证时间线 07-30 < 08-07。

**修法（validate_p2.py）**：
- 首循环：`source_ref` 结构校验改为 "null 或非空字符串"，不再一刀切拒绝。
- p1 块新增派生复核：逐条 EO-ATC 按生成器同规则重推导期望值（实体首条带 source_ref 的操作），实际 ≠ 期望即报错。数据驱动、无硬编码，防生成侧后续漂移。

**验证结果**：`python context/verify/validate_p2.py PT_017_coverage_obligations.json PT017_structured.json` → **Errors: 0 / Warnings: 0**，Self-check 8 项全 True（EO-ATC 5、EO-CRU 84、TO 127、CO 5、RO-IT 4、RO-BR 61、Judgments 132）。负面测试：篡改 EO-ATC-001 source_ref 为 '9.9.9（漂移）' → 复核闸门精确报 "与派生不符 (实体首条操作应='4.5.1（1）')"，证明新闸门非空转。5 条 EO-ATC 的透传值逐一与实体首条 op 一致（4.5.1（1）/4.6.1/4.12.1/4.13.1）。

**判据速记**：模块间契约冲突时，用 **git 时间线 + 生成侧注释/judgment/记忆中的设计意图** 判定谁是现行契约——较晚且带记录的实现是现行设计，较早的校验器是陈旧契约，修校验器而非回退新设计。

---

## 2026-08-11 ㊴ C12×44 crud 操作 4.4⑤ 回填完成：有状态效果→映射转换，无→"无对应转换"+理由

## 2026-08-11 ㊴ C12×44 crud 操作 4.4⑤ 回填完成：有状态效果→映射转换，无→"无对应转换"+理由

**决策**：给 44 条未回填的 crud 操作补 `note.comment`，满足 4.4⑤ 双型契约（①回填对应转换局部标签；②无对应转换注明"无对应转换"及理由）。C12×44 是**真完整性缺口**（crud 追溯缺失），机械补数据层。

**映射判据（逐操作核原文语义，非凑标签）**：
- **新增<X>申请**（9）→ 创建转换 t65–t73（frm=None→草稿，动作"新建X申请"）——op 即创建，有对应状态效果。
- **确认导入完成**（E-IMP，1）→ t06（待执行→已完成，动作"确认导入完成"）——op 与转换同名。
- **新增用户**（E-USER，1）→ t75（frm=None→正常，动作"新建用户"）。
- **编辑/暂存<X>申请**（18）→ **无对应转换**：编辑=草稿阶段属性修改、暂存=保持草稿，均不改任务状态（4.4 通用功能），无状态效果故无转换可指。
- **删除<X>申请**（9）→ **无对应转换**：删除=记录生命周期终止，文档无数码"已删除"具名态，不建模状态转换。
- **重置用户密码**（1）→ **无对应转换**：密码重置为属性操作不改用户状态（解锁是独立 t62 解锁用户，语义不同不混指）。
- **E-DEPT 新增/编辑/删除部门**（3）→ **无对应转换**：部门为组织分类配置实体，`state_dimensions=[]`，无状态维度。

**验证结果**：`--strict` 全量 **0 error / 65 warning / 4 autofix**（109→65，精确 −44，无回归）；C12×44→**0**；评审队列仍 0。JSON 输出中 11 条带转换引用的回填被框架改写为最终 T-id，**逐一交叉核验全部指向正确转换**（E-IMP 新建→T-063、确认完成→T-006、E-EXP 新建→T-070、E-USER 新建→T-073 等）；33 条无转换引用带理由。

**实现方式**：一次性机械补丁（带出现次数断言，44 处全命中后写盘），后删除脚本。**契约/代码层未改**——C12 判得对、回填契约已定义，缺口在数据实例层。

---

## 2026-08-11 ㊳ 评审队列 br_gap×2 全清：Gate A 排除 HTML 表格 + 短规则阈值结构性缺陷修复

## 2026-08-11 ㊳ 评审队列 br_gap×2 全清：Gate A 排除 HTML 表格 + 短规则阈值结构性缺陷修复

**决策**：清掉剩余 2 条 br_gap（限制性语句未收录）。一条是 Gate A 域门漏掉 HTML 表格形态的误报；另一条是 reconcile 覆盖判定的**结构性缺陷**——补了 BR b47 仍报，根因在判定阈值，不在数据。

**根因分析**：
1. **br_gap #1（HTML 表格误报）**：signals.py Gate A 只排除 markdown 表格行（`|` 开头），但原文 4.14.1 权限表用 **HTML `<table>`** 形态，行内容含限制词被当系统行为规则收录。→ 框架层修复：Gate A 加 `re.search(r"<\s*(table|tr|td|th)\b", ln)` 排除。
2. **br_gap #2（短规则不可命中）**：`_br_covered` 用固定阈值 `_MIN_OVERLAP=10`，`"不能删除修改根部门"` 仅 8 字，LCS 上限 8 < 10 → **结构性永远无法命中**，任何 <10 字的限制语句必误报。补 BR b47 也救不了——判据本身不可达。→ 框架层修复：`_br_covered` 阈值随候选长度缩放 `min(_MIN_OVERLAP, len(c))`，短候选退化为**全匹配**（LCS ≥ 全文长），长候选维持原 10 字；`_candidate_core` 同步剥尾随句读（。；，）避免短候选被末标点截断。

**落地**：
- `srs_pipeline/signals.py`：Gate A 域门加 HTML 表格排除（表格含 markdown 与 HTML 两种形态都排除）。
- `srs_pipeline/reconcile.py`：`_br_covered` 阈值缩放 + `_candidate_core` 剥尾随句读。
- 数据层（`srs_data/CASC-STEC-PT017.py`）：补 BR b47（不能删除修改根部门，4.14.3，validation）；E-DEPT→E-USER、E-REG→E-CAR 由 composition/business_ownership 改 reference/configuration_source（C17×2 判 (d)），note 记 (d) 理由。

**验证结果**：`--strict` 全量 **0 error / 109 warning / 4 autofix**，**评审队列 0 项**（br_gap 2→1→0）。warning 数与修复前一致，无回归。C17×2→0（改 reference 后不再触发疑似应判 composition）。

**C17×2 判 (d) 理由**（本次一并修正评审）：
- E-DEPT→E-USER：(d) 用户有独立创建流程（系统管理员新增），生命周期独立；部门仅提供组织分类，删除部门不级联用户（4.14.3 被使用部门禁止删除为阻断，非级联）。
- E-REG→E-CAR：(d) 载体由登记任务驱动产生（创建联动经 XC x10），产生后独立于登记任务流转；登记任务为**来源**非**归属容器**。E-REG 基数 1:1→1:N。

**契约层**：本批两处根因都在**代码**（Gate A 漏形态、阈值不可达），非生成契约问题——prompt.md 未改。

---

## 2026-08-11 ㊲ E-CAR 载体状态建模修正：移交/留存降为属性级操作，已外送补终态

## 2026-08-11 ㊲ E-CAR 载体状态建模修正：移交/留存降为属性级操作，已外送补终态

**决策**：E-CAR 载体状态移除假状态「已移交」「已留存」，`terminal` 补入「已外送」。C02×3 的根因是**建模错**（把属性级操作当状态转换），**非缺转换**——补转换是错修法，移除假状态 + 补终态才对。

**依据（主需求文档 = ground truth，逐节对照）**：
- 4.8.3 移交执行："移交成功后…接收人台账中自动增加此载体" → 归属人变更，载体在接收人台账继续存续，**状态不变**。
- 4.9.3 留存执行："将当前用户所持有的载体持有时间自动增加" → 纯时间延长，**状态不变**（数据 T-057 原 note 自认"持有时间延长而非状态本质变化，但语义上视为状态变更"——明知非状态变化还硬建状态）。
- 4.11.3 外送执行："载体管理员在线确认载体已外送" → 具名终态；4.11 全节（申请→审批→执行→任务查看）**无任何归还/返回回路** → **终态成立**。
- 架构方案 `载体管理系统_测试架构方案.md`（**AI 生成、未经人工确认**，仅佐证）的 inferred-4 独立给出同构结论（已归档/已回收/已外送=终态；移交/留存=已登记自环）——判定以主文档为准，不依赖该文档。

**方案D 落地（数据层 srs_data/CASC-STEC-PT017.py）**：
- states：`[已登记, 已归档, 已回收, 已外送]`；terminal：`[已归档, 已回收, 已外送]`；inferred：`[已登记]`。
- 删转换 T-056（已登记→已移交）、T-057（已登记→已留存）；删 XC x11/x12（编码了假状态变更，效果改由因果边表达）；删无效转换 i01/i02（已归档→已移交/已留存，目标态已不存在）。
- 因果3 E-TRF→E-CAR、因果4 E-RET→E-CAR 改写为**属性级效果**（归属人变更/持有时间增加，状态不变），`evidence_transitions` 只留任务侧 t24/t30。
- 4 处 note.comment 去掉"已留存"状态表述（发起移交/留存/回收/外送的前提统一为"载体处于已登记状态"）。
- C04 自动补镜像 XC-011~014 仍正常（源自任务侧 T-019/T-025/T-031/T-037 跨实体前置，与本次无关）。

**契约层防复现（prompt.md）**：根因在生成契约而非代码——Step 1 只有"改状态操作必入 transitions"一句、无判别准则，全文无终态判据。已加两处：
- Step 1 状态维度新增**操作 vs 状态**（属性级操作=归属/持有时间/关系变更，不建独立状态与转换，只入 operations 或同状态自环；改状态判据=文档给出新的具名阶段，附 4.8.3/4.9.3/4.11.3 反例正例）与**终态判据=具名+无回路**（两者缺一不立）两条。
- Step 4.1 写入前勾选新增"该转换是状态变化还是属性操作？属性操作不得建状态转换"。
- 代码校验器**不改**：C02 判得对（已外送确实无出边），但语义上无法区分"真状态缺出边"vs"操作被误建成状态"，只能事后报症状，防不住此类错误。

**验证结果**：
- `--strict` 全量：**0 error / 111 warning / 4 autofix**（原 116 warning）。C02×3→**0**；C16 62→60（假状态从 inferred 移除）；C09/C05/C13/C17 不变。
- JSON 输出：E-CAR 转换重排为 T-055 已登记→已归档 / T-056 已登记→已回收 / T-057 已登记→已外送 / T-058 已登记→已登记(到期提醒自环) / T-072 None→已登记；已外送在 terminal；假转换零残留。
- C13×3（侧挂[审批拒绝]/[已登记]/[正常]无 resume）为**框架误报**：审批拒绝是设计终态（4.8.2 任务终止，重提为新任务）；已登记/正常是主状态+自环提醒，非暂停态。C09×1 是两合法触发（手动锁 4.14.1（4）/自动锁 4.3.1（2）），非错误。C05×1（任务级别无 XC）良性。C12×44 为真完整性缺口（4.4⑤ crud 追溯），机械补。

**判据速记**：**属性级操作（归属/持有时间/关系变化）≠ 状态变化**，操作不得建为状态转换；**终态须具名 + 无回路**（4.11.3 具名且无归还回路），两者缺一不立。

---

## 2026-08-11 ㊱ ⑧ 遗留 disjunction_ref 展开：computation BR 原文 → disjunction(aggregate_count 复合谓词)

**决策**：关闭 ⑧ 遗留"disjunction_ref 展开 b31/b34"——T-042/T-045 的 `disjunction_ref(resolved:false)` 按数据层映射展开为 `disjunction(aggregate_count 复合谓词)`。展开**纯数据驱动**：BR 原文解析经表层语法表 + 字段注册表反查，不写任何字段名/BR id/章节号字面量；映射配置落 `review_structured.json._context.disjunction_refs`（与 phase_anchors 同构，P1 数据层单一事实源）。

**实现（context/generate_obligation_model.py + 数据层配置）**：
- `_context.disjunction_refs`：约束文本 → BR id（"评价结果满足下面任一条"→BR-031、"试用机构评价结果满足降级规则任一条"→BR-034）。注意 P1 的 business_rules id 是 `BR-XXX`（struct_srs 内部 b31/b34 经 P1 重编号），映射必须用 P1 id。
- `_disjunction_ref_node`：命中映射 → `_expand_computation_disjunction` 展开；失败保守回退 `resolved:false`（不冒充硬约束，⑧ v1 边界保留）。
- 展开算法：BR desc 剥"…："前缀 → `；`拆子句 → 剥前导 `或` → 尾随结果后缀 `[一-龥]为<state>$`（单字动词，状态集取 state_lookup；结果态 ≠ 转移 to → 该子句属其他转换/平局，跳过）→ `且`拆合取 → 每项经 `_parse_constraint_text`。
- 新表层行（count-value A/B/C，`_count_node` 共享构建，置于 aggregate_count 前）：`…的<计数对象>为<值>的次数累计(达到)?<N> 次`、`<值> <N> 次及以上`、`<N> 次及以上 <值>`。值→字段反查 `_resolve_field_by_value`（归一化值命中 values 的 canonical 记录，歧义 → None），`_resolve_counter_from_text` 增值兜底（累计 2 次差）。**节点构造单一事实源**：generic + count-value 两路共用 `_aggregate_count_node`（type/subject/count_scope/window 一处声明，不抄第二份）；操作词复用 `_RANGE_OPERATORS`/`_RANGE_OP_ALT`（不另写常量表）。

**行为影响（已含）**：T-042 → 3 条件子句（差×3 ∪ 差×1∧不合格×3 ∪ 不合格×5），T-045 → 3 条件子句（差×2 ∪ 差×1∧不合格×2 ∪ 不合格×4），升/平局子句正确排除。谓词下界 P4（评级锚待归档）< phase_anchor P5 → **相位/依赖不变**。

**验证结果**：
- 净效应隔离：HEAD 解析器 vs 本变更同 JSON 重跑，**仅 T-042/T-045 constraint_predicate 变化**，EO/CO/RO/_context 其余全字节相同（既存 T-002 分支漂移为提交基线陈旧，非本变更引入）。
- 引擎状态：`scripts.tier2_determinism`（PYTHONHASHSEED 0/999 双跑）SHA-256 一致；且基线(HEAD) vs 本变更输出**字节相同** → 下游 S0/S1/S3 零影响。
- Gate-S：`scripts/tier2_verify` ALL PASS（132 lifecycle + 39 mgmt，0 相位违例，0 errors）；P2 双跑确定性（唯一差异 generated_at）；py_compile 通过。
- PROC-203(T-042)/PROC-204(T-045) 相位均 P5，phase_basis 仍为 phase_anchor 抬升。

**遗留（接 ④ 下游消费）**：PROC-016 wiring（Step 4 aggregate_count→Guard 6）、PROC-060((state,path) 消歧,Step 5)、PROC-068（需新机制）——谓词已就位后的下游工作，不受本次影响。

---

## 2026-08-11 ㉟ 规则适用前提满足 Given 净化：数据层 BR 规则原文判别器（第一性原理，非"规则："前缀）

**决策**：`规则适用前提满足` Given（Type7/负向规则 PROC 的状态哨兵）渲染层净化——**仅移除空泛噪音形态 `{…}相关数据已准备`，保留携带真实规则上下文的形态**（`规则：{原文}`，规则文本可能只存在于 Given）。判别器第一性原理：给定 desc 是否包含**被测 BR 的规则原文**（数据层 `constraint_obligations[].description` 对照），不依赖 `"规则："` 内容前缀——未来规则文本形态若不带前缀，只要含 BR 原文照样保留。

**背景（两次修正）**：㉖ 边界明示该 Given"未动"。首版按"规则适用前提满足 也冗余"一刀切删全部 94 条 → user 指正 PROC-262 `规则：已提交的项目不能进行分数修改` 是有效规则（负向模板 When/Then 只有被禁操作，规则文本**仅存在于 Given**）。次版按 `desc.startswith("规则：")` 前缀匹配 → user 再指正"如果不是规则开头呢？第一性原理解决"。最终判别器 = 数据层 BR 原文包含关系。

**实现（纯渲染层，main.py，JSON 数据与哨兵不动）**：
- 三个数据驱动 helper：`_br_rule_map`（constraint_obligations → {RO-BR-XXX: 规则原文}，数据层单一事实源）、`_proc_br_texts`（proc 的 source_ids + Then br_refs 解析引用 BR，RO-BR/BR 归一化）、`_is_rule_noise_given`（state=="规则适用前提满足" 且 desc 不含任何被测 BR 原文 → 噪音）。
- Given 循环跳过噪音行；某 proc 的 Given 全为噪音 → 剥标题同源退化短语 `^[^，]*规则适用前提满足时，`（PROC-119 的 Given 保留故标题保留，判据同源）。
- `_sep_blank` 守卫：Given 块整体跳过时防止连续空行（顺带修 27 处 ㉖ 管理类净化留下的既存双空行）。

**证据（数据层全量 + 渲染回归）**：
- JSON 全量 257 条 `规则适用前提满足`（含实例 .N）：desc 含被测 BR 原文 **19 条**（6 基础 PROC）、纯 `相关数据已准备` 噪音 **238 条**、BR 解析落空 **0**——无灰色带。
- 6 条 `规则：` PROC（PROC-119/184/230/235/262/263）相对提交基线**零 diff**，Given+When+Then 完整。
- `相关数据已准备` 0 残留；`规则适用前提满足时` 标题 1（PROC-119，正确）；连续空行 0。
- 确定性双跑 SHA-256 一致；`python -m scripts.tier2_verify` ALL PASS（JSON 数据不动）；py_compile 通过。纯渲染层，回放路径 `scripts/s1_fix_replay.py` 不涉及。

**边界**：负向模板 PROC 的 When `尝试执行被规则禁止的…` 保持；与 ㉙（规则类 When 行同义反复删除）互不影响。判别器保守兜底：BR 解析落空 → 保留（不冒丢规则风险）。

---

## 2026-08-10 ㉞ ⑧ 遗留 entry=2 锚定：Strategy 0 消费 ref_state_dimension（谓词状态引用）

**决策**：关闭 ⑧ 遗留"entry=2 TO 锚定修复（Strategy 0 消费 ref_state_dimension）"。两点分开对待：
- **entry=2 的数值**：即 E-SCORE 入口相位，已由 ⑰（08-07）修复——`_compute_entry_phase` Strategy 0 优先读 `preconditions[].ref`，E-SCORE.打分状态 {2,3,4}→{3,4,5}（T-034 引用 待评审=P2，+1=3）。本条目不重复改值。
- **点名的机制**（⑧ 写时作者以为的修复通道）：Strategy 0 **消费 constraint_predicate 的结构化状态引用**，`ref_state_dimension` 为首要机制——此前从未实现，`preconditions[].ref` 只覆盖 type=state_ref 前提，type=constraint 前提的状态引用（field_equals 的 ref_state_dimension / completion.target / selection_range.source_state / occurrence_limit.on）在 Strategy 0 完全漏采。

**实现（共享派生，单一真相源）**：
- `context/constraint_fields.py` 新增 `iter_predicate_state_refs(pred)`：遍历谓词树产出结构化状态引用 (entity, dimension, state)，与 `predicate_phase_lower_bound` 同源（field_*+ref_state_dimension → 值解析回状态维度；time_limit/selection_range/completion → 直接状态；occurrence_limit → on 的 to/from；negation/conjunction/disjunction/when 递归）。
- `nodes/s0_topology.py` `_compute_entry_phase` Strategy 0 追加谓词引用扫描：命中主实体主维度状态 → 计入入口门禁（max 组合，与 preconditions[].ref 同语义；多引用各为门禁取最晚）。phase_anchor 是前置级标记，谓词树无此标记。

**当前模型零行为变化（诚实声明）**：全模型 ref_state_dimension 仅 E-PLAN.暂停前计划状态（T-022/023/024，主实体自引用），**无依赖实体 TO 携带谓词状态引用**；entry 计算维度（E-ORG/E-SCORE/E-PROJ.项目阶段/E-USER）均不触发新路径。机制以 `scripts/v33_ref_state_dimension_entry.py` 回归探针锁定（合成依赖 TO 证明非死代码：谓词引用 评审中 → entry 3+1=4；非主维度引用不抬升；与前置 ref 取 max）。

**验证结果**：全管线确定性重跑，engine_state 11 键与提交基线**字节一致**（DIFF KEYS=NONE）；procedures 772/772、errors=0；Gate-S signature `6252476661b4` 不变（V10 fail=3 为 DECISIONS ⑭ 预期）、spec_lint 0 errors/0 warnings。

---

## 2026-08-10 ㉝ When 事件不再携带「目标状态」注解 + Given 括号回显保留（溯源文本）

**决策**：`nodes/s1_generation.py` `_derive_business_event` 移除 `（目标状态：X）` 后缀。目标状态是 **Then 的断言内容**（`状态转换为X` / `状态流转：A→X`），同动作多目标实例（重启评审计划 → 待评审/评审中/已完成）由 Given 分支条件消歧——When 事件标签重复目标状态对执行人员是干扰（user 指正：the Then 已有、上下文已知），且**无下游消费者**读取该注解（validators/schema/metadata 均不依赖；仅 `main.py:1208` 检查 "超时"、`schema.py:259` 检查非空）。

**实现**：
- `_derive_business_event` 删除 to_state 追加分支（原 line 352-354），docstring 更新。Type1 主路径/时间边界路径均受影响；invalid 路径（尝试…已过期，无 to_state）本就不带注解。
- `scripts/s1_fix_replay.py` `_content_key` 新增 `_norm_event` 剥离 `（目标状态：X）` 后缀——归档 when.event 带后缀、回放新事件不带，两侧归一才能匹配，否则 title overlay 全失配。

**验证（Gate-S）**：回放 772 procs 双跑 SHA-256 字节一致（`d2dcd6de…`）；Gate-S verdict 与归档**逐字节一致**（signature `6252476661b4`，guard=0，coverage_misses=3 不变，V07 empty/unknown/no_permission=0）；overlay 772/0。canonical 已提升。仅剩 2 处 "目标状态" 在 PROC-224/233 BR 规则名内（SRS 原文，须保留）。

**Given 括号回显保留（user 定调）**：`(评审计划处于暂停状态且暂停前为已完成)` 由 `状态=暂停` + `分支条件` 各重写一次，是回显；但 paren 是 **SRS 前置原文溯源文本**。实测 782 个 state desc：401 独有信息（必须留）、381 提及状态（混合）、5 分支回显——无干净通用剥离法（语义判断会误杀 401 条，或需文本启发式），**保留原样**。

---

## 2026-08-10 ㉜ T-002 分支拆分 + overlay 改结构键（title-only）+ prohibit_keywords 数据修正

**决策**：T-002（待选入→已选入，唯一 branch_path=[] 且 compound predicate 的 TO）按 项目评级 拆 3 变体；overlay 从 temp_id 主键改**结构键 title-only**（actor 不再 overlay）；prohibit_keywords 去掉频次限制短语（"只有"是频次限制词，非禁止词）。

**T-002 拆分（`scripts/t2_branch_split.py`，纯数据驱动，零硬编码）**：从 constraint_predicate 结构派生变体——negation(评级=差)→T-002[a]（negative_test，5 实例），occurrence_limit(评级=不合格,limit=1)→T-002[b]（branch，5 实例），catch-all（全量值减约束值 join "/" → "优秀/良好/合格"）→T-002[c]（branch，5 实例）。变体序按 parts 出现顺序（差 在 不合格 前），ID [a][b][c] 后缀；constraint_predicate 与 branch_path 职责正交（branch_path 是分支唯一归属）。`_context.transition_splits`、branch_dimensions 各加 3 分支，RO-IT-001 absorbed_by_transition 按 reason 关键词路由到 T-002[a]（差）。字节精确 CRLF 写回，idempotent。**t3_occ_limit_detach.py 退役**（拆分后 occurrence_limit 在 T-002[b] given 里是合法归属，不再串线）。

**overlay 改结构键（`scripts/s1_fix_replay.py`，根因修复）**：T-002 拆分致 temp_id 重编号（+42/-32），temp_id 主键 overlay 错配 → 483/720 公共 temp_id 的 actor/title 被污染 → V07 65 no_permission。**证据链**：重跑前 S1 的 actor 已是模型确定性派生（762/762 与归档零 diff），overlay actor 纯属多余且是污染源；title 是 LLM 产物（重跑为 None）才需补。改后 overlay 只补 title，内容键 =（source_ids 归一化 T-XXX[a]→T-XXX、obligation_type、entity、dimension、when.event、when.action、thens 结构），翻译空间匹配（archived 已翻译，replayed 先翻译副本），组内按实例号对齐（同组 title 可发散，如 PROC-056.5 ≠ .1-.4）。拆分新增的 T-002[b]/[c] 正向变体无归档标题，title 留 None（诚实，无 LLM 可补）。

**prohibit_keywords 数据修正（guard 极性误判根因）**：`s1_generation.py:1541-1582` guard 极性把含 `prohibit_keywords` 短语的 RO-BR desc 判为禁止 → RO-BR-012 "本阶段不合格评价结果的项目，只有 1 次选入机会" 误判 T-002[b] negative_test。该短语是**频次限制**非禁止（"只有"勿入 strip/prohibit 正则）→ 从 `srs_data/struct_srs.py` 与模型 `_context.prohibition_config` 各删 1 条（30→29），sets 校验相等。拆分前被"差"前置条件掩盖（整体负例先行，guard 不触发），拆分后暴露。

**验证（Gate-S，`verify/validators.py`）**：V01-V09 全 PASS，V10 fail=3（coverage_misses T-013/EO-CRU-001/026/RO-IT-001，与归档完全一致）；V07 `empty_actor=0, unknown_actor=0, no_permission=0`。T-002 分支 given 隔离：T-002[a] 仅"差不可选入"，T-002[b] 仅"只有 1 次选入机会"，T-002[c] 无 constraint。回放 772 procs（762→772，+10 正向变体），双跑 SHA-256 一致，fixpoint 验证（回放提升后的 canonical 再回放字节一致）。canonical 已提升（`p3_agent_output.s1fix.*` → `p3_agent_output.*`），verdict.json 已更新（sig 6252476661b4）。

**guard 极性改结构优先（`s1_generation.py`，user 定调）**：guard 直接读 `constraint_predicate.type`——含 `negation` 节点 → 结构性负向（T-002[a]/T-036），不再依赖关键词文本匹配；同时 `_prohibit_kw` 默认兜底去掉"只有"（line 1549 默认 `["不可","不能","禁止","不得","不允许","无法","无权","只能","仅限","才可"]`）。**关键约束：无 negation 节点但真实负向的 TO（T-038/039/043，predicate 为 `{}`/aggregate_count）保留关键词文本兜底**——纯结构读取会把它们误翻成正向（已审计：它们负向来自 RO-BR-044/033，predicate 无 negation）。**不设 occurrence_limit 结构豁免**（user 指正：数据修正已足，勿叠加防护）。行为中性验证：回放 SHA `b9ab99...` 与 canonical 字节一致，Gate-S V01-V09 PASS / V10 fail=3 不变。

---

## 2026-08-10 ㉛ S1 else 兜底按 ref 类型分流 + given_type 字段——渲染层纯格式选择器（回放重跑）

**决策**：S1 修复从渲染层搬回数据层（用户定调："S1 修复不能把这个错误从渲染层搬到数据层"）。`nodes/s1_generation.py` else 兜底按 ref 类型分流前置条件；`models/schema.py` GivenClause 增加 `given_type` 字段；`main.py` 渲染层变纯格式选择器，不再文本匹配/反查 coverage_model。**回放重跑**（决策 1 选 A）从归档 `engine_state` + `coverage_obligations.json` 重建 AgentState，确定性重跑 S1→S4，跳过全部 LLM。

**根因**：旧 else 兜底把所有非 state_ref/event_ref 前置（含 constraint、跨维度 state_ref）dump 进 `givens[0].description`。结构化 ref 只在 `_phase_precondition_bound` 用于相位计算，givens 里丢失 → 渲染层 5 条规则/477 处干预反向补偿（约束文本从 desc 拆"约束："行、跨维度纯状态提升为独立行、流转形态 skip 留括号）。"你怎么知道 477 处之后没有第六个模式？"

**S1 分流（s1_generation.py `_make_given` + givens 循环）**：
- `constraint` 前置 → 独立 `given_type="constraint"` given（state 为空，desc=原文）。
- 跨维度 `state_ref`（ref.dimension ≠ 转换维度）：纯状态形态 → `given_type="state"` 独立 given（ref.state=前置态）；**流转形态**（`_FLOW_RE = 由[^;]*变为|变为|转为`）→ `given_type="flow"` 独立 given（ref.state=目标态，desc 保留原文，**不**提升为 `状态 = X`——语义串线）。
- 同维度 state_ref → 并进 givens[0].desc（不变）；event_ref → event given；分支变体 → `given_type="branch"`。
- 正向变体 strip：禁止语义 constraint given 整个删除（非剥 desc 文本）。

**given_type 语义（schema.py GivenClause）**：`state`→`{target} 状态 = {state} ({desc})`；`event`→同 state 格式；`flow`→`{target} 流转：{desc}`；`constraint`→`约束：{desc}`；`branch`→`分支条件：{value}`。state/event/branch 必须 state 非空；constraint/flow 允许空。

**决策 2（actor/title overlay）**：不归档 action_classification；S1 注入空 stub 跳过动作分类 LLM；重跑后按 `temp_id` 主键 overlay 归档的 `when.actor`/`title`（762/762 命中，0 actor/title diff）。

**T-002**：S1 修复后 occurrence_limit 约束成为独立 constraint given；`scripts/t3_occ_limit_detach.py` 更新为按 `given_type=="constraint"` 且 desc 精确相等**删除整个 given 条目**（非剥 desc 分句），断言恰好 10 处（PROC-133.1-.5 × PROC-134.1-.5），目标族外命中即中止。

**确定性修复（两个隐坑）**：
1. **source_ids 顺序抖动**：`list(set(...))` 四处在 s1_generation.py 合并去重（3829/3834/3883/3906 附近）迭代序随 PYTHONHASHSEED 抖动 → 改 `list(dict.fromkeys(...))`（保序去重，主流程 ID 在前）。temp_id 集不变，仅源 ID 顺序稳定。
2. **约束行自去重丢失**：渲染层 `other_given_texts` 由 `givens[1:]` 构建，含 constraint given 自身 → 渲染某条约束时其 desc 命中自己的条目 → 全部约束行丢失（0 约束行）。修复：`other_given_texts` 排除 `given_type=="constraint"` 条目（只与状态/流转/分支 given 的 desc 比对）。

**验证（确定性 Engine State，不信 LLM）**：
- 回放 762 procs，temp_id diff +0/-0，overlay 762/762 命中，actor/title 零 diff。
- 双跑 SHA-256 一致（JSON+MD），确定性 PASS。
- 渲染信息零丢失：archived MD value 片段 556 → replay 557，0 片段 under-counted；0 空括号。
- 流转形态从状态行括号拆为独立 `{target} 流转：{原文}`（18 base 处）；约束行 39=39、分支 41=41 与 archived 一致；覆盖需求（source_ids）顺序归一为保序去重序。
- schema 校验 762/762 valid；Gate-S V01–V10 与 archived verdict 逐项零 diff（coverage_misses=3 系 pre-existing，非回归）。

**边界**：实例副本（.N）不渲染 MD 块（archived 同为 275 块），故实例上的 constraint/flow given 不进 MD——既有行为，非回归。T-002 分支拆分（决策）另行。

**提升 canonical（用户已批准）**：s1fix 经审阅后复制为 `p3_agent_output.json/.md`（字节一致，cmp 确认），s1fix staging 文件已删。提升前修复 statistics 一致性：`type_counts` 由 type_label 改为按 **obligation_type** 映射（与 main.py 同构，`1→Type1(Transition)`…），剔除 `_replay_meta`（回放诊断字段），信封与真实流水线完全一致。提升后再次确定性双跑 PASS、schema 762/762、Gate-S V01–V10 零 diff。occurrence_limit 规则确认无残留（PROC-133/134 given 干净，专属覆盖 PROC-181 保留规则文本）。

---

## 2026-08-10 ㉚ 业务定位模块标签：`基础数据维护` → `基础数据-<实体>`（实体从 phase_basis 捕获）

**决策**：用户质疑业务定位里的 `基础数据维护` 太笼统，希望体现具体实体（如 基础数据-专家）。

**根因**：`基础数据维护` 是 phase_labeler 的**机制形态直译**（`render_registry.py` `PHASE_MECHANISM_CN["base_data_setup_phase"]`）。phase_basis 实为 `base_data_setup_phase.<实体>.<相位>`（如 `base_data_setup_phase.专家.0`，s1_generation.py:881 生成），`_BASE_SETUP_RE` 正则**本就捕获实体**（group(1)），但旧代码只用它做匹配、返回固定直译，实体信息被丢弃。

**修复（纯渲染层，context/render_registry.py）**：
1. 注册表值 `"base_data_setup_phase"` 由 `"基础数据维护"` 改为 `"基础数据"`；
2. `build_phase_labeler` 中 `_BASE_SETUP_RE` 分支改为 `f"基础数据-{_cn(m.group(1))}"`——实体从 phase_basis 捕获并经 `_cn` 归一（E-XXX id 或中文名均可），**不另立实体清单**；其余机制形态（前置条件创建/默认阶段）无实体后缀，保持直译。

**证据**：28 条全部变为 `基础数据-<实体>`（专家10/超时设置6/分数限值4/角色3/用户2/日志2/机构1，与 phase_basis 分布完全一致）；`基础数据维护` 0 残留；确定性双跑 True；tier2_verify ALL PASS（JSON 数据不动）；py_compile 通过。

**边界**：仅 base_data_setup_phase 机制形态带实体后缀；实体形态（状态锚定）本就返回实体模块名（项目/评审计划/用户/机构），不受影响。

## 2026-08-10 ㉙ 规则类 When 行删除：`按规则"…"执行操作事件` 与 Then 同义反复

**决策**：用户质疑 `1. 按规则"在已选入的项目中进行专家回避项目设置…"执行操作事件` 是否有必要。全量核验确认**删除无歧义**。

**证据链**：
1. **87 条规则用例**（Type7 standalone BR，RO-BR-* 义务），When event 均为 `按规则"{br_desc}"执行操作事件` 模板（`nodes/s1_generation.py:3214-3215`，action 同文本少"事件"两字 → `_dedupe_when_action` 子串规则 1 保留带"事件"的 event）。
2. **87/87 规则文本完整重复在 Then 的 `[BR]正面:` 期望中**（`m.group(1) in then_text` 全命中）——When 行零独立信息。
3. S1 自身注释把此形态称为 **tautological (同义反复)、unexecutable (不可执行)**（`nodes/s1_generation.py:3099`），该注释描述的正是这种"When 与 Then 同文本"的退化形态。
4. 87 条 actor 全为空（无操作者信息丢失）；81 条无 operation_hints（When 唯一一行即规则行）；6 条 time_sensitive 带 3 个时钟触发 hint（PROC-044/045/046/095/223/241，When 是 3 hint + 规则行）。

**实施（纯渲染层，main.py `_generate_markdown` When 块）**：判定 `event_shown` 匹配 `^按规则"(.*)"执行操作事件$` 且引号内文本出现在该用例 Then 期望文本中 → 跳过该 event 行。无硬编码规则词汇（不建规则表/关键词表），纯模板正则 + 文本包含关系。When 块重写为 `when_steps` 列表：hints 全部入列，非同义反复的 event 追加为最后一步；`when_steps` 为空则不渲染 `**When**` 头（81 条规则用例 → Given+Then 无 When）。

**证据**：`按规则` 0 残留；When 块 275 → 194（81 条规则用例整块消失）；步进校验 0 异常；PROC-010（无 hint）→ Given+Then，PROC-044（有 hint）→ 保留 3 个时钟触发步；确定性双跑 True；`scripts/tier2_verify.py` ALL PASS（JSON 数据不动）；py_compile 通过。

**边界**：`尝试执行被规则禁止的…操作`/`尝试违反规则操作事件`（PROC-038/117/182/228/233 等负面规则用例）When 是**可执行操作**，不匹配规则模板，**不受影响**。

## 2026-08-10 ㉘ When 行 target（操作对象）前置删除：无信息丢失 + 消执行者歧义

**决策**：用户追问 `2. 用户 修改角色` 前置的"用户"是什么。经查是 `when.target` 操作对象（PROC-022 / EO-ATC-008 / 4.11.1 用户管理，E-USER 系统用户——被改角色的那个用户，非执行者，actor 为空）。中文读法 "用户 修改角色" 天然被读成"用户(主语)修改角色"，把**宾语当成了执行者**，是歧义。用户提议：删除对象前缀，若不影响无歧义则删。

**全量核验（渲染前判定，先证后改）**：275 个 When 块中 **172 条保留 target 前缀**，逐条检查：
1. **实体可恢复性**：target 实体段（复合 target 取首段，如 `机构.机构状态`→机构）或末段是否已出现在该 proc 的 Given/Then 文本 → **0 缺失**（172 全可恢复）。
2. **上下文唯一性**：target 实体不在事件文本、且 Given/Then 出现其它实体时是否歧义 → 仅 4 条（PROC-219 评审计划/项目；PROC-268/269/270 附件/项目），逐条复核**全部安全**：PROC-219 的 Given 已点名 `评审计划.计划状态=已完成`+`评审计划超时类型=归档超时`，When `归档超时` 直接对应 Given；PROC-268/269/270 的 Then 点名 `附件 建议书…上传到数据库`。

**结论**：删除 When 前置 target **零信息丢失**（对象由 Given/Then 上下文确定），且**消除了"宾语被读成执行者"的歧义**——When 只剩动作本身（`修改角色` / `新增用户（目标状态：未锁定） by 系统管理员`）。

**实施（纯渲染层）**：`main.py _generate_markdown` When 行不再拼接 `target_str`；删除已无调用点的 `_dedupe_when_target`（及其在 `_dedupe_then_target` docstring 中的引用，改为"纯文本包含判定"）。

**证据**：前置 target 形态（`专家 修改`/`用户 修改`/`机构.机构状态 添加`/`评审计划.计划状态 建立`/`附件 上传`）全量 grep **0 残留**；When 块 275 个序号连续校验 0 异常；`操作步骤`/依赖 `.N` 0 残留；确定性双跑 True；py_compile 通过；tier2_verify ALL PASS（JSON 数据不动）。

**边界**：Then 行 target（`用户.角色 显示为修改后的值`）保留——主语仍需明确；`_dedupe_then_target` 的包含省略规则不变。

## 2026-08-10 ㉗ When 块重构：操作提示前置 + 有序清单（去"操作步骤N"标签）

**决策**：用户两点反馈——① `**When**` 里 `操作步骤1：导航至专家页面` 的步骤拼接方式需要调整：操作提示应是**第一行**、event **第二行**；② 去掉 `操作步骤N：` 前缀，按执行顺序排列即可，"前面加个序号也行"。

**修复（纯渲染层，main.py `_generate_markdown` When 块）**：When 重排为按执行顺序的**有序清单**，序号代替 `操作步骤N：` 标签：

```markdown
**When**
1. 导航至专家页面
2. 新增专家
```

- 操作提示（`operation_hints`）全部列在 event 之前，event 为最后一步；多提示（time_sensitive 3 提示：clock_injection/db_time_update/scheduler_manual_trigger）依序展开在 1..3，event 落第 4 步。
- 无提示用例（451 基础用例）event 为第 1 步（`1. {event}`）。
- event 行保留既有去重与修饰不变：`_dedupe_when_action`/`_dedupe_when_target`、`actor`、`[action]` 括号规则原样。
- 实现：`step_no` 计数器，先逐条 hint 输出 `{step_no}. {hint}`，最后输出 `{step_no+1}. {event 行}`。

**证据**：`操作步骤` 文本 0 残留；275 个 When 块序号**连续递增校验 0 异常**（脚本扫描每个 When 块，行首 `^\d+\. ` 必须从 1 步进，event 是块内最后一条）；三形态抽查正确（CRUD 1 提示→`1.导航 / 2.event`；time_sensitive 3 提示→`1..3 提示 / 4.event`；无提示→`1.event`）；确定性双跑哈希一致；`scripts/tier2_verify.py` ALL PASS（JSON 数据与哨兵不动，`('mgmt','存在'):39` 不变）；py_compile 通过。

## 2026-08-10 ㉖ 管理类兜底 Given（存在/操作入口可用）渲染层净化

**决策**：用户反馈 `专家 状态 = 存在 (操作入口可用)` 这类前置条件无用。经查这是 **Tier 2 领域前置对管理类实体（topology_level 0：专家/角色/机构/用户/日志/超时设置/分数限值）的兜底哨兵**——S1 Type5 非 VE 分支（`nodes/s1_generation.py:2474-2478`）调 `object_existence()`（`context/domain_precondition.py`），判别器 `topology_levels > 0` 只命中业务生命周期对象（E-PROJ/E-PLAN/E-ATT/E-SCORE），管理类返回 None → 落 `state="存在", description="操作入口可用"` 弱 Given。DECISIONS ⑳ 曾判定"管理类保持 =存在 合理"（作为 tier2_verify 哨兵），但该 Given 对增删改查无测试价值（新增时"存在"语义矛盾，编辑/删除/查询时是废话）。

**修复（纯渲染层，JSON 数据与哨兵不动）**：
1. **Given 块**：`state=="存在"` 且 desc（剥 `[实例 N]` 后）`=="操作入口可用"` 的行跳过；全被跳过则整个 `**Given**` 块不渲染 → 27 个管理类用例（专家7+机构3+用户9+角色3+日志2+超时设置1+分数限值2）变成 When+Then。
2. **标题**：判据与 Given 净化相同（该 proc 的 Given 全为兜底哨兵）→ 剥 LLM 标题里同源的退化条件短语 `操作入口可用时，` / `<实体>存在时，`（`re.sub(r"^(?:操作入口可用|[^，]+存在)时，", "", title)`，8 条：5 操作入口可用 + 3 角色存在），不另立实体清单。

**证据**：`操作入口可用`/`存在时` 0 残留；27 用例 When/Then 完整、0 孤立标题；非兜底 Given（ATC 配置值/转换 `(初始)`/分支条件如 评审组人数=5）完好；确定性双跑哈希一致；`scripts/tier2_verify.py` ALL PASS（JSON 数据里 `('mgmt','存在'):39` 哨兵原样保留，生命周期 Given 分布 待选入 120/已建立 8/未打分 4 与依赖边 1109/41 全不变）；py_compile 通过。

**边界**：`规则适用前提满足` Given（PROC-010/038 等规则类，desc 带实际规则前提）是另一形态，**未动**——若用户也认为冗余需另行决策。

## 2026-08-07 ㉕ 标题实例徽标全删 + Then 侧 target 冗余省略（与 When 同判据）

**决策**：用户两点反馈（标题后的实例个数如 ×5 不需要了 / 上次只处理了 When 没处理 Then），渲染层两处净化：

1. **实例书签全部移除**：标题 `(×N)` 徽标删除、顶部 `**多实例**` 图例删除（徽标没了图例成孤儿）、Given 描述前导 `[实例 N]` 标签剥除（`re.sub(r"^\[实例 \d+\]\s*", "", desc)`）。实例折叠逻辑保留（按 base 折叠 .N，渲染 procs[0] 规范例）——实例纯重复，可读文档展示一条规范用例，JSON 的 .N 副本原样保留给执行工具。275 标题 `### PROC-272：…` 无任何实例痕迹。
2. **Then 侧 target 冗余省略**：`_dedupe_then_target` 升级为返回 `(target_shown, exp_shown)` 二元组，两条规则顺序判定——① target 为限定链且 exp 以其末段开头 → 裁 exp 前导段、target 保留作主语（既有行为，如 专家.技术领域 + 技术领域显示为… → 专家.技术领域 显示为…）；② target 或其末段已在 exp 文本中出现（PROC-272 Then `附件 显示项目附件集中查看页面`，"附件" 藏在 "项目附件" 里；或 专家.技术领域 + "校验失败，提示'技术领域选择不在A-J范围内'"）→ target 完全冗余省略。判据与 `_dedupe_when_target` 完全一致。

**补充（依赖引用 .N 归一）**：实例折叠后依赖/弱依赖对具体实例的引用（如 `**依赖**：PROC-057.1`）展示时归一为基例 id——新增 `_display_id`（`re.sub(r"\.\d+$", "", s)`），`**依赖**`/`**弱依赖**` 行逐项归一。纯展示归一，不碰 JSON 数据；实例纯重复，语义等价。175 行依赖/弱依赖 0 残留 .N，归一后 0 悬空引用（每条 PROC-XXX 均指向 doc 实际标题）。级联链数据里为 0，无需处理。

**证据**：实例痕迹 0 残留（×N 徽标 / [实例 N] / 多实例图例 / 依赖 .N 全 0）；Then target 省略 416 条（312 全文在 exp + 104 末段在 exp，与扫描预测吻合），前缀裁剪 156 条保留既有行为，921 条保留；104 条限定链省略逐条核对全部安全（exp 自含 target 末段文本，校验提示/状态断言自成一体，无实体语境丢失）；PROC-272 渲染 `**When** - 查看项目附件` / `**Then** - 显示项目附件集中查看页面 (behavior)`；确定性双跑哈希一致；py_compile 通过。

## 2026-08-07 ㉔ When 行冗余操作对象省略（PROC-272 "附件 查看项目附件"）

**决策**：When 行前导 target（操作对象）若已出现在 event 文本中则省略。用户反馈 PROC-272 渲染为 `附件 查看项目附件`（读作"附件查看项目附件"）。新增 `_dedupe_when_target(target, event)`：target 或其最后一段（复合 target 如 项目.项目状态 取 "项目状态"）是 event 子串 → 省略前导 target。纯文本关系判定，无硬编码实体/操作名。

**根因**：S1 对 query/crud 操作（EO-CRU-058 查看项目附件，entity=附件）设 when.target=实体名，而操作名本身已含操作对象 → "附件 查看项目附件" 冗余。

**证据**：762 条 When 中 target 全量在 event 内 275 条 + 末段在 event 内 25 条被省略，462 条保留（专家 修改技术领域、评审计划 尝试执行从…等 target 不在 event 内的不受影响）；PROC-272 渲染为 `查看项目附件`；确定性双跑一致；py_compile 通过；无空 When、无重复对象残留。

## 2026-08-07 ㉓ 阶段标签粗化为模块级 + 删阶段依据行 + 删逐用例多实例描述

**决策**：用户三点反馈（阶段不用那么细 / 阶段依据有的有有的没有 / 多实例描述已多余），渲染层三处简化，全部保留数据：

1. **阶段标签粗化为模块级**：`context/render_registry.py` `build_phase_labeler` 从"实体·状态"（26 种细标签，如 评审计划·取消结束/结束/超时结束）简化为粗粒度**模块**（8 种：评审计划/项目/用户/机构/打分 + 机制直译 基础数据维护/默认阶段/前置条件创建）。实体形态只返回实体中文模块名，机制形态返回跨实体直译。**删掉了整个相位号→状态反查逻辑**（_resolve/_states_at/_terminal/_initial/_join_states/_STATE_REF_RE 全部移除），labeler 从 ~150 行降到 ~50 行，仍全数据驱动。
2. **删 `**阶段依据**` 行**：根因 `phase_basis_debug` 过滤（粗启发式形态被隐藏，139/275 显示）。这是引擎 traceability（原始 basis 字符串），非读者信息；结合模块级方向整行删除。`phase_basis`/`phase_basis_debug` 原样留在 JSON，schema 未动；`phase_basis` 仍被 labeler 消费派生模块标签。`phase_basis_debug` 无逻辑消费方了，作为 schema 字段保留无害。
3. **删逐用例 `**多实例**` 描述**：根因 md 折叠 .1/.2 时产生的冗余展开说明。实测 241 个多实例组**全部是纯重复**（差异仅 temp_id 与 Given 描述 [实例 1]/[实例 2] 标签，S4 multi_reason=`dim_count=1 instances=2`），JSON 已拆成 .1/.2。删除逐用例 boilerplate，保留 ×N 徽标 + 顶部图例。

**证据**：8 种模块标签覆盖 762 条；阶段依据 0 残留；逐用例多实例 0 残留（图例保留）；275 PROC 全带模块标签、无 "第N阶段" fallback 残留；确定性双跑哈希一致；py_compile 通过。

## 2026-08-07 ㉒ PROC-001 三处渲染去重 + EO-ATC source_ref 透传

**决策**：针对 PROC-001 的三条用户反馈，渲染层净化（不动 JSON）+ P2 数据源修复，全部数据驱动、无硬编码：

1. **覆盖需求缺 source_ref**：`context/generate_obligation_model.py` EO-ATC 循环的 `source_ref` 由 `None` 改为从实体**首条操作的 source_ref** 透传（`_entity_config_section_ref(e)`）。P1 属性字段不携带章节信息，但属性所属实体的操作携带（如 4.10 专家管理）。17 条 EO-ATC 全部命中，无 None 残留。
2. **When 名词框架重复**（"技术领域配置变更事件 [修改技术领域] 不是一回事么"）：`_dedupe_when_action` 改为返回 `(event, action)` 元组，规则顺序 = 空/相等/**子串** → **名词框架 event**（正则 `.*事件(?:\([^)]*\))?$`，覆盖配置变更/转换/已过期三类）取 action 作 When → **子序列**（逐字符，完全冗余）省略方括号。按规则"…"执行操作事件 因 action 是子串先命中，保留带 BR 文本的 event，不误伤。
3. **Then 前缀重复**（"专家.技术领域 技术领域显示为… 技术领域又重复了"）：新增 `_dedupe_then_target`，target 为 实体.属性 限定链且 expectation 以最后点段开头时裁掉前导段。

**证据**：
- P2 确定性：temp diff 只改 17 条 EO-ATC source_ref + 17 条 judgment 文本 + `generated_at` 时间戳，结构性内容零漂移。
- 渲染回归：762 条 When 全部去重（substring=626 / nominal→action=74 / subsequence=62 / bracket_kept=0），Then 裁剪 156/1493；`配置变更事件`/`转换事件`/`事件(已过期)` 三个名词框架短语在 md 全局 0 残留；确定性双跑哈希一致；py_compile 通过。
- 事前全量扫描确认安全：含"事件"且与 action 非子串非子序列的 event 只有配置变更(34)/转换(14)两类；Then 最后点段全是明确属性/状态词（项目状态/计划状态/技术领域…），无歧义。

## 2026-08-07 ㉑ ⑤ 排期项作废——相位反转降级前提已由 ⑬ 达成,不实施

**决策**：⑤（S3 phase guard 对 backward/resume 边豁免相位反转降级）**不实施**，落档为"已由 ⑬ 达成"。⑤ 于 08-06 排期（weak_dependency 下游行为=弱化消费已确认）；本 session 实施前置核实时发现其设计前提已被 08-07 ⑬ 的结构化 state_ref 相位抬升消除。

**证据（探针 `scripts/t5_probe.py` + 内联 probe，确定性 Engine State）**：
1. **相位反转降级条件 0 次触发**：全图扫所有 transition-upstream 边，`dep_phase > my_phase`（`s3_dependency.py:276-283` 降级分支，origin=`transition_upstream_phase_inversion`）**从未发生**。当前 200 条 weak 边 origin 全为 `weak_side_effect`（副作用跨实体链 + Type8 规则实体链，`s3_dependency.py:430/468`），0 条是 ⑤ 要豁免的那种。
2. **⑤ 点名的残留缺口已关闭**：`T-012 回滚不保证排在 T-016 后` → 实测 T-011（PROC-218, P5）硬依赖 [T-001, T-005, T-032]；**T-012（PROC-198, P5）硬依赖含 T-016**（PROC-197, P2）——拓扑排序强制 T-016 在前，V01=0。因果顺序已由硬依赖强制。
3. **剩余 22 条涉及 backward/resume 的弱边全为 `weak_side_effect` 副作用链接**（T-016 取消→weak T-011 回退、T-035→weak T-025/026 恢复、T-033→weak T-011/T-012），语义正确（副作用"由该 proc 落实"，非排序前提），不属 ⑤ 范畴。

**根因（⑤ 决策早于 ⑬）**：⑤ 于 08-06 定案时，回退 TO 相位偏低（T-011/T-012 曾在 P2/P3），其上游触发（T-032 归档 P5 / T-016 取消）相位更高 → 反转 → 降级 weak → 顺序不强制。⑬（08-07）用结构化 state_ref 把回退 TO 抬到 P4/P5（T-008/T-010→P4、T-011/T-012→P5）并补 Guard 6 锚定边，使上游边恒满足 `dep_phase ≤ my_phase`，反转条件**结构性消失**。⑤ 要修的正是 ⑬ 已消除的状态。

**结论**：⑤ 不实施，不引入死代码。弱依赖降级机制（`weak_dependencies` + `weak_origins` 审计可见）保留现状。**遗留风险记录**：若未来 P1/P2 数据回潮重现该失败模式（pre-⑬ 真实发生过），反转降级会再次静默弱化回退边且 V01 不拦——届时按 ⑤ 设计补豁免（direction∈(backward,resume) → 保持 hard）即可，本条目为决策凭证。

---

## 2026-08-07 ⑳ Tier 2 领域前置机制——实施完成落档

**决策**：⑱ 排期的 Tier 2（CRUD/查看类义务缺"前置对象必须已存在"领域先决）本 session 实施完成。采用仓库既有**共享派生模块**模式（`context/domain_precondition.py`，与 `entity_operators`/`time_control`/`constraint_fields` 同构，单一事实源），S1 与 S3 各显式接线。

**与评审建议的关键偏差（批判性评估后修正）**：评审建议 P2 Step 2.5d 注入 + 零代码改动消费，经代码阅读**证伪**——① EO-CRU 义务**不流经** `_resolve_phase_for_transition`（Type5 内联逻辑），P2 注入无消费端；② Guard 6 的 `_resolve_to` 对 EO source_ids 返回 None（仅 TO source_ids 进 Guard 6），EO-CRU 程序不享受既有依赖通道；③ 真零代码需要 schema 改动（EO 无 preconditions 字段）。故不走 P2 注入，改显式 S1/S3 两处接线，全部数据驱动。

**机制（第一性原理，无名字硬编码）**：
- **判别器 = S0 `topology_levels > 0`**（{E-PLAN:1, E-PROJ:1, E-ATT:2, E-SCORE:1} 精确命中 4 目标实体；管理类全 0，保持 `=存在` 合理不变）。"有创建转换"非判别器（E-ORG/E-USER 有创建转换但是管理类）。
- **存在锚定 = 创建转换（from=None）**；E-PROJ 双创建转换（T-001 项目状态→待选入 P0、T-013 项目阶段→开题）锚**最早 to_state 相位**（待选入）；E-ATT 无自身创建转换 → composition 父 E-PROJ；同维创建转换**全绑**（T-015[a/b/c]），异维（T-013）不绑。
- **三个接入点**：① S1 Type5 弱 Given `=存在` 替换为 `X已存在，处于Y状态`（中文名经 entity_name_map 反查，**修正了方向 bug**——`_build_entity_name_map` 返回中文→E-XXX，须 `{v:k}` 反查）；② S1 相位底 = 创建 proc 实际相位（`_creation_proc_phase` proc 查表，**非文本重推导**——"处于已选入状态"不匹配相位正则但实际创建相位是 1）；③ S3 **Guard 7** 绑定 EO-CRU proc → 锚定创建转换（跳过 audit_rejection、相位单调性约束），Guard 6 保持只处理 TO。

**验证（确定性 Engine State，非 P3 LLM 文本）**：`scripts/tier2_verify.py` 全断言 PASS——删除项目→`待选入`+T-001 dep；查看评审计划→`已建立`+phase 1+T-015[a/b/c] dep；查看评分细则→`未打分`+T-034 dep；上传建议书→target E-PROJ+`待选入`+T-001 dep；管理类 EO-CRU-045 保持 `存在`+无领域前置依赖；V01 0 违例；errors=0。量化：lifecycle 弱 Given 分布 **待选入 120 / 已建立 8 / 未打分 4**，管理类 `存在` 39 不变；依赖边 +41 domain_precond（总 1109）。**确定性双跑**：PYTHONHASHSEED 0 vs 999，S0→S3 业务数据 byte-identical。v32_check 回归：V01=0，⑬ focus TO（T-007/008/010/011/012/014）相位全 SAME。

**已知边界**：① 计数 29 实体（项目 19+附件 5+计划 4+打分 1）vs ⑱ 的 28——差额 EO-CRU-009 通用"新增"并入项目生命周期（19 vs 18），取保守一侧；② PROC-087 查看打分记录用 `未打分` 锚定（has_data 与 exists 二义，首版取 exists/未打分 兜底，语义 ⑭ 记录一致）；③ 相位直方图整体 4→5 漂移系 ⑰ S0 Strategy 0 的 E-SCORE {2,3,4}→{3,4,5} 累积 vs 过期磁盘基线，非 Tier 2 引入（tier2_verify 已单独量化，E-PLAN 0→1、E-SCORE 0→3 为本轮唯二相位移动）。

**文件**：`context/domain_precondition.py`（新，共享派生模块）；`nodes/s1_generation.py`（Type5 Given+相位底，含 name-map 方向修正）；`nodes/s3_dependency.py`（Guard 7）；`scripts/tier2_verify.py` / `scripts/tier2_determinism.py`（新，验证探针）。架构评审建议作废（P2 注入路径，见上偏差），不做。

---

## 2026-08-07 ⑲ P3 渲染 `**阶段依据**` 行丢失——debug 分类器误杀依赖实体精确锚定

**用户报告**:`p3_agent_output.md` 里 PROC-137（T-006 全部专家提交打分，`项目.项目状态 评审中→待归档`）"丢失了阶段这一前提"——没有 `**阶段依据**` 行，而同文件的 PROC-139 有 `phase_table.计划状态.暂停`。

**诊断**:相位**从未丢失**——PROC-137 的 Engine State `_S2_fields.phase=4`（待归档→P4，正确），丢失的只是**渲染层打印**。main.py:563 仅在 `phase_basis and not phase_basis_debug` 时打印该行；PROC-137 的 basis 是 `dep_state_phase_map.项目.项目状态.待归档`，被 `_is_debug_phase_basis`（s1_generation.py:253）误判为 debug。

**根因（第一性原理：分类器按"锚定前缀"而非"启发式标记"分类）**:`_DEBUG_BASIS_PATTERNS`（commit 2b921cc）本意是隐藏引擎启发式/聚合推导的 basis（min/max/兜底/父锚/VE/配置），保留精确状态锚定（`phase_table.计划状态.待启动`）。但列表里 `"dep_state_phase_map."` 是**锚定前缀**而非启发式标记——它把依赖实体上同样精确的逐状态锚定 `dep_state_phase_map.X.维度.状态` 及其 `→ bumped to PN (state_ref ...)` 抬升注释一并误杀。粗粒度形式其实只有 `dep_state_phase_map.X.min_phase` 一种，已由独立模式 `".min_phase"` 覆盖，`"dep_state_phase_map."` 完全冗余且有害。

**解法**:从 `_DEBUG_BASIS_PATTERNS` 删除 `"dep_state_phase_map."`，只按启发式标记分类（`.min_phase` 继续兜住粗粒度）。仅影响渲染标记 `phase_basis_debug`，**不触碰任何相位值**，Engine State 确定性无损。

**验证**:对 p3_agent_output.json 全量 762 过程重分类——debug 标记 583→424，159 条精确锚定恢复显示；PROC-137 basis `dep_state_phase_map.项目.项目状态.待归档` 恢复（False）；粗粒度（`.min_phase`/`max_phase`/`fallback`/`parent`/`VE`/`config`）全部仍隐藏；新显示的 50 类 basis 全部为精确锚定或抬升注释。

---

## 2026-08-07 ⑱ Tier 2 领域前置机制——诊断完成、落档待新 session 实施

**决策**：⑭ 排期的 Tier 2（CRUD/查看类义务缺"前置对象必须已存在"领域先决）经本 session 完整诊断后**确认是当前最高优先级 todo**，但本 session 上下文已近窗口上限（已压缩 1 次 + 完成 P2 去硬编码 ⑯ + S0 Strategy 0 ⑰），**迁移交接**。完整诊断+方案+验证方法落档于 `context/TIER2_DOMAIN_PRECONDITION_HANDOFF.md`，新 session 直接接手。

**诊断结论（已探针验证）**：
- 数据层信号已就位：P2 已产出 `precondition_state_refs`（48/70 TO，结构化 `{entity,dimension,state,raw_text,pattern}`），但它是**状态转移前置**（对象处于X态才可做Y），不是"对象须存在"先决——缺口就在此。
- 影响面量化（275 TC）：弱 Given（`=存在`/`=初始`/`操作入口可用`）56 个（20%）；**真问题约 28 个**（项目18+附件5+评审计划4+打分1），集中在业务生命周期对象的 CRUD/查看类；管理类（专家/角色/日志/配置）"=存在"是合理的，不做领域前置。
- 方案第一性原理：表面层=CRUD/查看义务→作用对象须先存在（义务类型+实体函数，非名字硬编码）；数据层=`precondition_state_refs`+对象创建转换（from=None）；接入 S1 Given 生成 + S3 Guard 6 依赖 + 相位不早于对象创建相位。
- 验证：全管线确定性 Engine State 对比（P3 LLM 随机不可比）；目标断言 TC-083 Given 含"计划已建立"、TC-132 含"打分已生成"、V01 0 违例、errors=0。

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
