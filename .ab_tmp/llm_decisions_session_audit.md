# 本 session 影响 LLM 的决策审计单（2026-09-08）

范围：v13 依赖评审会话中，**改变上游 LLM 生成预期**或**新增对 LLM 输出的确定性校验**的全部决策。
分层：A = prompt 契约（直接进 LLM 上下文）；B = 数据锚点（LLM 再生时的对齐样例）；
C = 确定性校验（LLM 输出的回归网）；D = 不影响 LLM 但需知悉的边界。

---

## A. Prompt 契约层（srs_pipeline/glm5pr.md）

### A1. 多状态面出生值契约（:127，转换构造段之后新增）

**契约原文（逐字）：**

> **多状态面出生值契约**：创建转换（frm=None）的 `to` 只覆盖本维度 initial；同一动作若同时建立同实体**其他**状态维度的出生值（平行流程型各分支创建面常见），必须在本条 `expected_results` 逐面声明「{维度名}初始为{值}」（如受理报名同时使预通知状态出生为未发送 → expected_results 含「预通知状态初始为未发送」）。该声明是消费转换在本分支唯一的创建根依据，漏声明 → 下游消费该状态的转换在本分支无生产者可挂（S1 会报「初始出生点未声明」告警）。声明只落一处：承载该出生动作的创建转换。

- **对 LLM 的要求**：创建转换的 `to` 只声明本维度；同动作建立的其他状态面出生值逐面写「{维度名}初始为{值}」进 expected_results；声明只落承载动作的创建转换一处（不重复）。
- **证据依据**：19.3 测量审核流中预通知状态出生点=项目创建（受理报名动作），无独立宿主动作；镜像 t07 能力验证面的初始化声明。
- **违规捕获**：C1（防线②）。
- **阴性夹具**：`.ab_tmp/no_t40line_cov.json`（删掉 t40 该行后的 coverage 模型，恰好命中 1 条告警）——验证告警网有效性用。

### A2. 共享状态面分支单据身份契约（:129，紧随 A1 新增）

**契约原文（逐字）：**

> **共享状态面分支单据身份契约**：「预通知」「通知」等是**载体类别词**，其下实义单据分支各异（能力验证＝能力验证计划邀请函/通知；测量审核＝作业指导书，SRS 19.1 行11 发送动作原文即「样品发放,作业指导书发送」）。凡 (a) 建立或承载分支实义单据的转换、(b) **跨分支共用动作且起点不同**（同action不同frm，如「能力验证预通知」从未发送直发 vs 已审核后发出），必须：`note` 声明 `doc_identity`＝本分支实义单据；`expected_results` 用限定名指称（「作业指导书/预通知发送」，勿写笼统「预通知发送」）。动作名沿用系统功能词**不改名**（同action不同frm 平行为建模语义）；分支归属由 branch_values 承载。漏声明 → S1 报「跨分支借用动作未声明单据身份」告警。

- **对 LLM 的三条要求**：
  1. 载体类别词（预通知/通知）不得单独指称单据——expected_results 用限定名（「作业指导书/预通知发送」）；
  2. 两类转换必须 `note.doc_identity` 声明：(a) 建立/承载分支实义单据的转换；(b) 跨分支共用动作且起点不同（同action不同frm）；
  3. **动作名不改**——「能力验证预通知」是系统功能词，t14/t50、t16/t65 的同action不同frm 平行是建模语义；分支归属由 branch_values 承载，不在动作名里编码。
- **证据依据**：兄弟 DSL（同一 SRS 的独立捕获，`网数中心…需求分析与设计 (1).py:388`）E-YT 实体名「预通知」desc=「能力验证计划预通知、作业指导书等通知类载体」、attr 通知类型=「预通知/作业指导书/结果通知单等」；:98-99 19.1 行11 动作原文「样品发放,作业指导书发送」→ 通知状态 已确认。
- **已考虑并否决的替代**：给测量审核分支的动作改名（如「发送作业指导书」）——否决，理由：发明 SRS 不存在的动作词；破坏同action不同frm 平行结构与 S1-a 同动作分组语义。**如你审计后想走改名路线，需同步改 A2 契约第 3 条与 C2 判据。**
- **违规捕获**：C2（防线③）。

### A3. op() API 签名对齐（:225）

- **决策**：glm5pr 的 op() 签名此前缺 4 个参数（linked_transitions / stage_hint / form_fields / page），与 builders.py:24 实际实现脱节。已逐字对齐并文档化。
- **对 LLM 的要求**（契约原文要点）：
  - `linked_transitions=[tid…]`＝3.3 link_op_transition 的同义内联（**二选一**，勿双写）；
  - `stage_hint`＝无状态前置操作（file/数据类等，相位被钉死在对象创建态时）的阶段挂载提示，二选一：`{"anchor_state": {"entity","dimension","state"}}`（锚定该状态相位并追加其 restatement Given）或 `{"min_phase": N}`（相位下限）；语义＝max(当前相位, 提示相位)，**只上提不前移**；anchor_state 须指向已建模状态；
  - `form_fields=[字段名…]`＝表单字段清单覆盖；`page=页面名`＝Type5 导航页面覆盖。
- **v13 现有 5 处 stage_hint 用例**（LLM 对齐样例）：EO-CRU-004→已结束、009/010→报告审核中、016→结果待提交、017→报名成功。

---

## B. 数据锚点层（srs_data/pt_srsv13.py — LLM 再生的对齐样例）

| # | 位置 | 改动 | 依据 |
|---|---|---|---|
| B1 | t40（:1240-1249）expected_results 增「项目创建后预通知状态初始为未发送」+ note 补出生点依据 | A1 契约实例 | 19.3 出生点=项目创建，镜像 t07 |
| B2 | t47 er「**作业指导书/**预通知审核通过…」、t48「**作业指导书/**预通知审核退回…」、t49「修改**作业指导书/**预通知后重新提交审核…」、t50「**作业指导书/**预通知发送…」、t65「发送已审核的**作业指导书/**预通知，项目状态变为进行中（推断）」 | A2 契约实例 1（限定名指称） | SRS 19.1 行11 原文点名作业指导书 |
| B3 | note.doc_identity 7 条：t01/t44=「设计方案」；t14/t16=「能力验证计划邀请函/通知」；t46/t50/t65=「作业指导书」 | A2 契约实例 2（身份声明） | 同上；t01/t44 为同action不同frm 签名对，两侧同值（设计方案） |
| B4 | t46/t50/t65/t14 note 补「本分支预通知实体=…与对侧相区分」语义说明 | 审计可读性 | 兄弟 DSL E-YT desc |

**守恒说明**：t40 出生行「项目创建后预通知状态初始为未发送」**未加限定名**——它是维度面出生声明（「预通知状态」＝面名），不是单据指称；A2 契约只约束单据动作指称。勿在 prompt 更新时误改此行（防线②判据依赖「初始+通知状态+未发送」子串同现）。

---

## C. 确定性校验层（nodes/s1_generation.py — LLM 输出的回归网）

### C1. `_warn_undeclared_birth_states`（防线②，:880；调用点 :4936）

- 触发：消费转换前置 state_ref (E,D,S) **无同分支 post_state 生产者**，且**无同分支创建转换** expected_results 含「初始」+D+S 子串声明 → `S1.初始出生点未声明: …`。
- 分支兼容口径与 S3 `_branch_compatible` 同源：空归属共享、非空须相交；消费 `_synth_branch_values`（**必须在 S1-a/S1-b 之后跑**）。
- 「预通知状态」⊃「通知状态」的子串命中是**有意放行**（CJK 无词界），勿"修复"。

### C2. `_warn_borrowed_action_doc_identity`（防线③，:944；调用点 :4940）

- 触发判据（全结构化，无词表硬编码）：(entity, dimension, action) 相同 + branch_values 归属组 ≥2 且两两互斥 + 各组 from 集合不全同（同action不同frm）→ 组内每个 TO 须有 `note.doc_identity`，缺失 → `S1.跨分支借用动作未声明单据身份: …`。
- 只消费 P1 级 branch_values 与 note，**与 S1-a/S1-b 无顺序依赖**；按 TO id 去重（P2 主TO/分支TO 拆分同 id 多实例）。
- v13 签名共 3 对：设计方案编制（t01/t44）、能力验证预通知×通知状态（t14/t50）、能力验证预通知×项目状态（t16/t65）。7 条 doc_identity 声明齐备后应 0 告警。

---

## D. 边界知悉（不影响 LLM 输出，但同 session 落地）

- **Fix H**（S1-b 闭包传播 own-only）：生命周期已归属生产者只传播自身归属——pipeline 内部，修 T-046 吸对侧分支值。
- **Fix I**（guard1 (from,to) 去重分桶并入 branch_values）：平行分支变体不塌缩——pipeline 内部。
- 两者详见 memory `s1b-propagate-own-only-guard1-pair-bucket`；39/39 断言脚本 `.ab_tmp/verify_v13_review2.py`（内容键控，与 title LLM 抖动无关）。

## 再生与验证步骤（手动）

```bash
python -m srs_pipeline.cli srs_data.pt_srsv13 -o pt_structuredv13.json        # P1.5
python context/generate_obligation_model.py pt_structuredv13.json pt_coverage_obligationsv13.json  # P2
python main.py pt_coverage_obligationsv13.json pt_outputv13.json              # S0-S4
python .ab_tmp/verify_v13_review2.py                                          # 39 断言
```

预期：P1.5/P2 0 error / 8 warning（全既有）；S1 两条告警 0 命中（声明齐备）；PROC-051/078/079 的 Then 出现「作业指导书/预通知」限定名。
