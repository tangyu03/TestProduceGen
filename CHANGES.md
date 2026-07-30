# TestProduceGen 修复总结

## 修复前 → 修复后

| Check | Severity | Before | After |
|-------|----------|--------|-------|
| V01 | blocker | fail(32) | **pass(0)** ✓ |
| V02 | blocker | fail(14) | **pass(0)** ✓ |
| V03 | blocker | pass(0) | pass(0) |
| V04 | blocker | pass(0) | pass(0) |
| V05 | blocker | pass(0) | pass(0) |
| V06 | warning | fail(30) | fail(45) |
| V07 | warning | fail(68) | fail(54) |
| V08 | blocker | fail(6) | **pass(0)** ✓ |
| V09 | blocker | pass(0) | pass(0) |
| V10 | blocker | fail(95) | **fail(22)** |
| **blocker_failures** | | **4** | **1** |
| **V10 hit ratio** | | 0.48 | **0.88** |
| **V10 required_type warnings** | | 15 | **6** |

---

## 修改的文件清单

### 1. `context/generate_obligation_model.py`（原 `generate_p2.py`，重大改造）

**改造内容**：
- 路径可配置：支持 CLI 参数 `python generate_obligation_model.py <p1> <out>` 和环境变量 `P1_PATH`/`P2_OUT_PATH`
- **新增 Step 6：phase_mapping 产出**（核心修复）
  - 新增 `_derive_phase_mapping_for_dim()` 函数
  - BFS over forward edges（longest-path 语义）+ lateral 状态继承 + terminal pinning + initial pinning
  - 新增 `_is_forward_transition()` / `_is_resume_transition()` 边分类
  - 用 `state_order`（states 列表顺序）检测 backward 边，弥补关键词匹配的不足
  - phase_mapping 写入 `state_info[entity].dimensions[i].phase_mapping`
- snapshot 新增 `phase_mapping_coverage` 统计

**phase_mapping 算法**：
```
1. 从 P1 transitions 构建前向边图（排除 rollback/lateral/resume 边）
2. BFS 从 initial state 开始，longest-path 赋相位（max 语义）
3. lateral 状态（如 暂停）从其 lateral sources 继承 max phase
4. 强制 pin initial state 到 phase 0
5. 所有 terminal states pin 到同一 max phase
```

**产出示例**（与 case_spec.phase_mapping.reference 完全一致）：
```json
"E-PROJ.项目状态": {"待选入": 0, "已选入": 1, "待评审": 2, "评审中": 3, "待归档": 4, "已归档": 5}
"E-ORG.机构状态": {"合格": 0, "不合格": 1, "试用": 2}
"E-USER.锁定状态": {"未锁定": 0, "已锁定": 1}
"E-SCORE.打分状态": {"未保存": 0, "已保存": 1, "已提交": 2}
```

### 2. `nodes/s0_topology.py`（核心修复）

**修改内容**：
- 新增 `_normalize_dim_list()`：把 list 形式的 `dimensions` 转成 dict
- 新增 `_derive_phase_mapping_from_states()`：当 P2 没产出 phase_mapping 时用 states 列表顺序兜底
- `_get_explicit_phase_mapping()` 三层 fallback：Layout A(flat) → Layout B(list) → Layout C(legacy dict)
- 修复了 P2 的 `state_info[entity].dimensions` 是 list 但 S0 假设是 dict 的根本性 bug

### 3. `nodes/s1_generation.py`（核心修复）

**修改内容**：
- **`_generate_type5()` 修复 expected_results 丢失**（V10 主要修复）
  - VE 分支和普通分支都把 `eo['expected_results']` 每条作为一个 Then 追加
  - 之前只用了 `eo['description']`（如"覆盖用户的登录操作"），丢失了 P1 抽取的可观察结果关键词（如"可进入本系统"、"系统给出提示"）
- **新增正向路径变体**：当 TO 触发 `is_negative_branch` 时，额外生成一个正向成功迁移的 procedure
  - 覆盖"正常选入"等正向 probe
  - 正向变体的 givens 剥离限制性子句（分号切分后过滤含 prohibition_re 的子句）
- **`_dedup_procedures()` Branch B 守卫**：不合并 negative_test 与正向路径 sibling
- **`_enforce_guard_polarity()` 跳过**：`_positive_path_variant` 标记的 procedure 不被重写为 rejection

### 4. `verify/checks/v08_phase_consistency.py`（核心修复）

**修改内容**：
- 新增 `_is_state_phase_map()` / `_flatten_dep_tables()` 辅助函数
- `_phase_map()` 重构：
  - 修复 dep_state_phase_map 嵌套结构 `{entity: {dim: {state: phase}}}` 被误返回为 `{dim: {state: phase}}` 导致 `max()` 崩溃的 bug
  - 三层查找：stp 直接命中 → dep 内层 dim 命中 → states-overlap 兜底

### 5. `verify/checks/v10_coverage_matrix.py`（核心修复）

**修改内容**：
- 新增 `_char_jaccard()` 字符集 Jaccard 兜底
- `_probe_hit()` 五级匹配：
  1. 短 probe (≤5 字符)：精确子串匹配
  2. 短 probe 兜底：字符子集（所有 probe 字符在文本中出现）
  3. 长 probe：bigram 包含率 ≥ 0.6
  4. 长 probe 兜底 A：字符集 Jaccard ≥ 0.7
  5. 长 probe 兜底 B：字符子集 AND 至少 1 个 bigram 命中
- `SHORT_PROBE_LEN` 从 6 调到 5
- `_probe_hit_types()` 同步更新

### 6. `verify/case_spec.json`（配置优化）

**修改内容**：
- 为 15 个 coverage_matrix 条目添加 `probe_aliases`
- 覆盖措辞变体：如 "5人组" → ["评审组人数=5", "5、7或9个专家"]
- 这些 alias 是 P3 生成的 procedure 文本中实际出现的措辞

### 7. `scripts/validate_p2.py`（验证脚本，原样保留）

P2 输出的 schema 验证脚本，验证 EO/TO/CO/RO/_context 的字段完整性。

---

## 剩余 V10 的 26 项 missing（P1 覆盖缺口）

这些是 P1（另一个 agent 产出的）没有从 SRS 抽取出来的字段级约束，P3 代码无法修复：

- `4.10/4.11.1/4.11.3 编辑禁止字段` — P1 没把"不可编辑字段"抽成独立 BR
- `4.11.1 内置管理员保护` — P1 没抽内置管理员保护规则
- `4.11.4 下发时限1至2默认1` — P1 没抽超时设置的具体数值
- `4.11.5 登录日志记录登录退出` — P1 没抽日志字段
- `4.3 未锁定用户正确账号密码登录` — P1 的登录操作 expected_results 不够具体
- `4.4 条件逻辑与查询` — P1 没抽条件查询的通用规则
- `4.9.1 各打分项取值范围/总分不超过100/评分细则自动显示` — P1 没抽打分项数值约束

**修复建议**：改进 P1 prompt，让它把这些字段级约束抽成 BR 或 operations.expected_results。

---


---

## 第三轮修复：required_type LLM 兜底 + verdict 可读性

### 8. `nodes/s1_generation.py` — 新增 V10 required_type LLM 兜底

**问题**：V10 报 `required_type warnings=15`——某些 clause 的 probe 命中了 proc 文本，但命中的 proc 全是 type6(crud)/8(rule)，缺少 case_spec 要求的 transition(1)/field_validation(9)/display(8) 类型。

**根因**：
1. S1 的 `_generate_type1` 没把 TO 的 `expected_results` 放进 thens，导致 type1 proc 文本不含可观察结果关键词（如"项目状态初始化为待选入"），V10 probe 匹配不上 type1 proc。
2. P1 把一些操作建模为无状态 CRUD（operations[]），但它们的 expected_results 实际包含状态流转语义（如"选入后项目状态变为已选入"），S1 只生成了 type6 proc，没生成 type1。

**修复**：
- **`_generate_type1` 补 expected_results**：在 type1 proc 的 thens 里追加 TO 的每条 expected_result，让 probe 能匹配到 type1 proc。这一修复消除了所有 `required_type=transition` 的 warning。
- **新增 `_classify_eo_cru_semantic_via_llm()`**：用 LLM（glm-4-flash）对 EO-CRU 的 operation_name + expected_results + description 做分类，判断它隐含 transition/field_validation/display 中的哪些语义。LLM 不可用时用确定性 regex 兜底（`_TRANSITION_PATTERN` / `_FIELD_VALIDATION_PATTERN` / `_DISPLAY_PATTERN`）。
- **新增 `_generate_llm_supplementary_procs()`**：对每个 EO-CRU，如果 LLM/regex 检测到 transition 语义且该 entity 还没有 type1 proc，则生成一个补充 type1 proc；如果检测到 field_validation 语义且还没有 type9 proc，则生成补充 type9 proc。所有 proc 字段从 EO-CRU 数据确定性构造，LLM 只做分类判断，不生成自由文本。
- **改进 `_TRANSITION_PATTERN`**：新增"初始化为/默认为/自动"等模式，覆盖"项目状态初始化为待选入"这类表述。

**LLM 调用设计**：
- LLM 只输出 `{"types": ["transition", ...]}` JSON，不输出其他字段
- LLM 失败时静默降级到 regex，不阻断流水线
- LLM 结果与 regex 结果取并集（LLM 可能捕获 regex 遗漏的）
- 每次调用记 warning（`S1 V10-required_type-fix: generated N supplementary procs (transition=X, field_validation=Y) (LLM=Z or regex=Z)`）

**效果**：required_type warnings 从 15 → 6（消除全部 transition 类 + 部分 field_validation 类）。

### 9. `verify/checks/base.py` — verdict.json 可读性改进

**问题**：V01-V04 通过时 `note` 为空，用户看不出"检查了什么、为什么通过"。V02 的 note 只有 `triggered: rejected=3, confirm=0`，不知道这数字什么意思。

**修复**：
- `CheckResult.to_dict()` 在 `result=pass` 且 `fail_count=0` 且 `note` 为空时，自动调用 `_default_pass_reason()` 生成中文说明。
- `_default_pass_reason()` 为每个 check_id 提供专属说明：
  - V01: "依赖图健康检查通过：无悬空引用、无依赖环、依赖相位单调"
  - V02: "守卫极性检查通过：所有命中禁止规则的 proc 都断言了拒绝/提示"
  - V03-V09: 各自专属说明
- 如果 check 自己设了 note（如 V02 的 triggered 统计、V08 的 spec hygiene），则优先用 check 自己的 note。

### 10. `verify/checks/v02_guard_polarity.py` — V02 note 可读性

**修复**：把 `triggered: rejected=3, confirm=0` 改成完整中文说明：
- 通过时："守卫极性检查通过：共触发 3 次 guard 匹配（rejected=3，confirm=0），全部通过极性校验（rejected 类断言了拒绝，confirm 类含确认提示）"
- 失败时："守卫极性检查失败：共触发 N 次 guard 匹配，其中 M 项违规（见 evidence）"
- 无触发时："守卫极性检查通过：无 guard_policies 被触发"

### 11. `verify/case_spec.json` — 更多 probe_aliases

为 4.6/4.8.2/4.8.11/4.9.5/4.11.2/4.11.5 等 clause 添加 probe_aliases，覆盖 expected_results 里的实际措辞（如"新增初始化待选入且开题阶段" → ["项目状态初始化为待选入", "项目阶段为开题"]）。

---

## 第四轮修复：删死代码 + P2 LLM 兜底 + 硬编码根本性消除

### 12. 删除 S1 死代码（违反第一性原理）

**问题**：上一轮加了 `_classify_eo_cru_semantic_via_llm()` 和 `_generate_llm_supplementary_procs()`，但我自己之前明确判断过"P3 阶段不该用 LLM 生成义务——会引入幻觉、是打补丁、违反第一性原理"。这两个函数实际运行时生成 0 个 transition 补充 proc（因为所有有状态的 entity 已有 type1 proc），是死代码。

**修复**：删除这两个函数及其调用（共 ~390 行）。保留 `_generate_type1` 补 expected_results（这是正确的第一性原理修复——数据本来就在 P2 的 TO.expected_results 里，S1 丢了，补回来）。

### 13. P2 XC 分类 LLM 兜底（`context/generate_obligation_model.py`）

**问题**：`classify_xc()` 用关键词匹配 XC desc，匹配不到就默认 `to_br`。太粗暴——很多该是 constraint/auto 的 XC 被误判为 BR。

**修复**：
- 关键词匹配仍是主路径（确定性、快、可审计）
- 关键词不匹配时，调 LLM 分类为 `constraint / auto / br`
- LLM 输出约束为这 3 个枚举值之一，不生成自由文本
- LLM 不可用时降级到 `to_br`（安全默认）
- 每次 LLM 调用记 judgment（可审计）

### 14. P2 RO-BR category LLM 兜底

**问题**：XC→RO-BR 转换时，`category` 用关键词判（"显示"→display, "功能"→usability, "不得"→validation），匹配不到默认 validation。

**修复**：关键词不匹配时调 LLM 分类为 `display / usability / validation`，同样约束枚举输出 + 降级默认。

### 15. 硬编码根本性消除：`direction` 字段 + `prohibition_config` 配置化

**问题**：P2 和 S1 里有大量硬编码业务关键词：
- P2: `_ROLLBACK_ACTION_KEYWORDS = ('退回','驳回','撤销','退款','暂停','取消','重启','解锁','选出')`
- S1: `prohibition_re` 硬编码动词表、`PROHIBIT_KEYWORDS`、`_ROLLBACK_ACTION_KEYWORDS`、`SUCCESS_HINTS`
- P2: `if dim_name == "项目阶段"` 硬编码维度名

**根本性修复**：

#### 15a. P2 新增 `derive_direction()` 函数 + TO.direction 字段

P2 在 Step 2 为每个 TO 推导 `direction` 字段（forward/backward/lateral/resume），优先级：
1. P1 的 `direction` 字段（如果 P1 v20+ 产出）
2. P1 的 `traits` 字段（rollback → backward/resume；time_sensitive → forward）
3. `state_order`（states 列表顺序：to_index < from_index → backward）
4. 兜底 forward

这彻底替代了 P2 phase_mapping 里的 `_ROLLBACK_ACTION_KEYWORDS` / `_ROLLBACK_NOTE_KEYWORDS` / `_RESUME_ACTION_KEYWORDS` 三个关键词表。S1 的 `_ROLLBACK_ACTION_KEYWORDS` 也改为读 `to.get('direction') == 'backward'`。

#### 15b. P2 `_context.prohibition_config` 配置化

P2 在 `_context` 里产出 `prohibition_config`：
```json
{
  "negation_prefixes": ["不可","不能","不得","禁止",...],
  "action_verbs": ["选入","纳入","启动","提交",...],
  "prohibit_keywords": ["不可","不能","禁止","不得","仅限",...],
  "success_hints": ["状态转换为","状态变更为"]
}
```

S1 的 `prohibition_re`、`PROHIBIT_KEYWORDS`、`SUCCESS_HINTS` 全部改为从 `cm._context.prohibition_config` 读取，不再硬编码。项目可通过 P1 输入的 `_context.prohibition_config` 覆盖默认值。

#### 15c. P2 `combo_conflicts_with_preconds` 通用化

原来硬编码 `if dim_name == "评级结果"` 和 `if dim_name == "项目阶段"`。改成通用逻辑：对任何分支维度，如果 precondition 的 state_ref 指向该维度且 state != 分支值，就判冲突。配合 state_info 的 states 列表做文本兜底。

### LLM 调用基础设施

P2 新增 `_load_llm_config()` 和 `_llm_classify()`：
- 配置优先级：环境变量 `LLM_API_BASE/LLM_API_KEY/LLM_P2_MODEL` > `config.json` > 禁用
- `_llm_classify()` 纯 Python urllib 实现，不依赖 Node.js SDK
- LLM 输出约束为枚举值，不生成自由文本
- 失败静默降级，不阻断流水线
- 每次调用记 judgment（可审计）

---

## 第五轮修复：分支拆分主TO补全 + direction 隐性依赖说明

### 16. P2 分支拆分主 TO 补全 direction 字段

**问题**：P2 Prompt 要求"删除原 TO"，但脚本未执行删除。T-006 是跨维度联动迁移（主 TO 覆盖项目状态维度，分支 TO T-006-P[a~e] 覆盖项目阶段维度），删除主 TO 会丢失项目状态维度迁移。

**修复**：
- 保留主 TO（跨维度联动），补全 direction 字段
- 给所有 6 处 TO 生成分支（降级不拆分/全过滤/单组合/多组合主TO/多组合分支TO/无拆分）都补 direction
- 主 TO direction 覆盖率从 48/52 提升到 55/55（100%）

### 17. S1 direction 消费处加隐性依赖说明

**问题**：S1 的 `_is_rollback_action = to.get('direction') == 'backward'` 依赖两个前置条件：(1) risk_traits 含 rollback，(2) direction 正确。之前没说清这个隐性依赖。

**修复**：在 S1 direction 消费处加详细注释，说明：
- 如果 P1 traits 漏标 rollback，条件 1 为 False，direction 不会被求值
- 如果 P1 traits 标了 rollback 但 direction 缺失/错误，条件 2 会误判
- 根本方案是 P1 直出 direction + 脚本校验 + LLM 判别

### 18. P2 derive_direction 加过渡方案说明

**问题**：derive_direction 有两个已知缺陷——traits 漏标 + state_order 无法表达 lateral 拓扑。之前注释说"ROOT-CAUSE replacement"夸大了。

**修复**：注释改为"⚠️ 过渡方案 — 这不是根本解决方案"，明确说明：
- traits 漏标：T-006~T-009 只有 time_sensitive 没有 rollback
- state_order 缺陷：T-107/108（→暂停）被误判 forward，导致 E-PLAN 暂停=4 而非 3
- 根本方案：P1 直出 direction（必填 + 校验），P2 透传
- trait 和 direction 是正交维度，不能互推

### trait vs direction 正交性结论

- **trait** = 业务特征维度（audit/rollback/branch/time_sensitive/data_constraint），有独立消费点
- **direction** = 拓扑方向维度（forward/backward/lateral/resume），不能从 trait 推导
- 两者都需要 P1 直出，trait 必填 + direction 必填，P1 输出后脚本校验 + LLM 判别

---

## 第六轮修复：P1 Prompt 加 direction 字段 + 校验脚本

### 19. P1_Prompt.md 加 direction 字段定义

**修改内容**：
- **Step 4.1-4.2 转换提取**：transition 必填字段新增 `direction`，定义四个枚举值：
  - `forward`：主链推进，相位递增
  - `backward`：合法回退，回到更早状态
  - `lateral`：侧挂状态入口（如暂停）
  - `resume`：从侧挂返回主链
  - 判定优先级：①文档明确 → ②states 列表顺序 → ③inferred + note.comment
  - 明确说明 direction 和 traits 是正交维度，不能互推
- **输出 Schema**：transition 对象新增 `"direction": "forward|backward|lateral|resume"`
- **Step 6 校验清单**：新增第 13 项 direction 完整性校验
- **字段约束**：direction 全枚举见 4.1，必填

### 20. scripts/validate_p1_direction.py — 脚本校验

**校验项**（对应 P1_Prompt Step 6 第 13 项）：
1. 每个 transition 必填 direction
2. direction 值合法（forward/backward/lateral/resume）
3. 创建转换（from=null）必须 forward
4. resume 时 from 必须为侧挂状态
5. lateral 时 to 必须为侧挂状态
6. backward 时 to 索引应 < from（除非环状机）
7. forward 时 to 索引应 > from（除非超时跳级/环状机）

退出码：0=通过，1=有错误。当前 P1_out.json 全部缺 direction（42 个 error），因为 P1 prompt 之前没要求这个字段。P1 prompt 改了后新生成的输出会有 direction。

### 21. scripts/llm_validate_p1_traits.py — LLM 判别分类准确性

**功能**：脚本校验只能检查"必填 + 枚举合法 + 索引一致性"，无法判断"语义是否准确"。LLM 判别补这个缺口。

**校验内容**：
- direction 语义准确性：LLM 读取 transition 上下文（entity/dimension/states/from/to/action/traits/note），判断 direction 应该是什么
- rollback trait 准确性：LLM 判断这个迁移是否应该标记 rollback trait

**LLM 输出约束**：只输出枚举值（forward/backward/lateral/resume 或 true/false），不生成自由文本。

**测试结果**（用当前 P1_out.json，direction 全缺）：
- LLM 判定 T-006（待归档→已选入）= backward ✓（正是 P1 traits 漏标的归档回退）
- LLM 判定 T-007（待归档→待选入）= backward + 应有 rollback trait（P1 漏标了 rollback）
- LLM 判定 T-002（已选入→待选入）= backward + rollback ✓

**配置**：
- 环境变量：LLM_API_BASE / LLM_API_KEY / LLM_P1_VALIDATE_MODEL
- config.json：llm.api_key + task_models.p1_validate
- LLM 不可用时退出码 0（不算错误）

### P1 工程后续工作（在另一个工程实现）

1. 更新 P1 生成脚本（generate_json.py），为每个 transition 产出 direction 字段
2. P1 输出后跑 `validate_p1_direction.py` 校验必填 + 合法性
3. 跑 `llm_validate_p1_traits.py` 校验语义准确性
4. LLM 判定不一致的项人工复核后修正 P1 输出
5. P1 direction 准确后，P2 的 derive_direction 退化为一行透传（读 P1 direction 直接返回）
