## 目标

将需求文档转化为结构化 Python DSL，框架组装校验后产出 JSON。Step 1→6 顺序执行，不可跳步；仅 4.4 可回修前序产物（含通用回写协议覆盖的 `action_verbs` 与 `permission`）。

---

## 术语

- **当前实体**：当前转换的 entity。
- **XC**：cross_entity。
- **BR**：business_rules。
- **镜像**：跨实体 precondition 复制为 XC。
- **穿透**：分支维度在 T/XC/BR 三层均有体现。
- **驱动方→被驱动方**：记 `transition_relations` 的 `frm/to`。
- **局部标签**：小写占位编号 `t01/x01/b01/i01`，正式编号由框架分配。

---

## 输入契约

- `source_ref` 格式：`章节号+标题`；无章节用原文片段（≤30 字），一律非空。
- XC 继承宿主 `source_ref`（镜像/联动继承 `source_transition` 指向的转换，4.6 判约束继承含对应 precondition 的转换）。
- XC/IT 无 `note` 字段。

---

## 铁律（仲裁：G1>G2>G3，组内小号优先；中断输出>铁律9；铁律10>4.4补边）

### G1

- **4 字符安全**：一律写原文，禁止手工预转义。
- **9 空值规范**：字段必须存在，无内容传 `[]` 或缺省（critical 中断豁免）。

### G2

- **2 不脑补**：仅记录文档提及或可合理推导的内容。
- **5 动态中断**：critical→仅输出中断 JSON；minor→假设填充 + `inferred=True` + `comment` 写明。
- **7 约束≠因果**：门禁/前置不是因果；跨实体因果必过 4.6 鉴别。
- **10 终态语义**：`frm` 不得为终态；终态有出边→该状态非终态，复核 terminal。

### G3

- **1 推断标注**：`inferred=True` 且 `comment` 写依据。
- **3 结构行为解耦**：`structural_relations` 无因果语义。
- **6 组织维度≠业务归属**（按 Step 2 判定）。
- **8 trigger_source 优先级**：`cross_entity > action > expected_results > desc > business_rule > bidi_coupling`；同 `(frm,to)` 写入前去重仅升级，`desc/trigger` 以 `;` 合并，`evidence` 并集，`rollback` 取或。
- **11 结构关系三元分类**（Step 2）。
- **12 preconditions 结构化**（`precond`/`state_ref`），禁止纯字符串。
- **13 操作归位**：无状态操作只入 `operations`；改状态操作必入 `transitions`（`operations` 记 crud 作索引不重复）；必须/不得类只入 BR。
- **14 编号移交+状态值原文**：编号一律局部标签；状态维度名与状态值逐字取自原文，禁止改写/概括/近义替换。

---

## 通用回写协议

适用对象：`action_verbs`（Step 0）和 `permission`（Step 0.5）。

- **允许追加**：Step 1–5 中发现新动词、新角色或操作归属时，可增量回写，不算跳步。
- **标注方式**：
  ```python
  N(inferred=True, comment="Step X 发现新动词'归档'，回写 action_verbs")
  N(inferred=True, comment="Step X 发现...，回写 permission")
  ```
- **合并语义**：`action_verbs` 追加去重；`permission` 同一角色多次调用时框架自动合并 operations 并集。
- **框架兜底**：Step 6 做覆盖率校验（warning 级）。

---

## 流水线

### Step 0：项目操作词汇 → `m.set_prohibition_config()`

作用：建立动词种子词表，供框架识别与粗筛。

**配置项**：

| 字段 | 说明 |
|---|---|
| `action_verbs`（必填） | 去宾语、去重后的动词词根；同义簇只录代表词。 |
| `prohibit_keywords`（可选） | 仅收录复杂否定短语：带量化、条件、复合动词组合。简单否定由框架自动派生。 |
| `negation_prefixes`（可选） | `prefix + verb` 组合匹配，默认含常用否定前缀。 |
| `transition_indicators`（可选） | 状态转移信号词。 |
| `success_hints`（可选） | 成功信号词，辅助 audit 标记。 |

示例：

```python
m.set_prohibition_config({
    "action_verbs": ["选入", "纳入", "启动", "提交", "保存", "删除", "修改", "新增",
                     "审批", "批准", "通过", "归档", "重启", "暂停", "结束", "发放",
                     "退出", "登录", "操作", "编辑", "查看", "分配", "入选", "进入",
                     "选为", "选择", "执行"],
    "prohibit_keywords": [
        "不能连续3天",
        "不超过3次",
        "不能提为试用",
    ],
})
```

---

### Step 0.5：角色→可执行操作权限 → `m.add_permission()`

作用：声明无状态操作权限。

- 仅声明 `session/ui/file/query/config` 及不改状态的 crud；转换型操作由 `transitions.role` 承载，此处不声明。
- `role` 与 Step 4.3 的 `name` 逐字对齐。
- 范围约束由授权类 BR 承载，不在 `permission` 中声明。

写入前 □：
- `role` 名是否与用例 actor 一致？
- `operations` 中是否有转换型操作？（有则移除）

示例：

```python
m.add_permission("机构管理员", ["编辑项目", "查看项目", "查询项目",
                                "查看项目附件", "上传附件", "下载附件"])
m.add_permission("评审管理员", ["编辑专家", "查询专家", "回避项目设置"])
```

---

### Step 1：实体 → `m.add_entity()`

生效铁律：2、13、14。

**分类**：

| 类型 | 判定标准 |
|---|---|
| core | 状态枚举/多步骤多角色流程/状态自主；或多角色审批链/独立业务载体/可独立循环 |
| managed | 管理员 CRUD/配置字典/状态简单 |
| 交集 | 归 core |

**属性**：

- 静态特征；影响流转分支的标 `is_config=True`。
- `desc` 完整转录全部约束（范围/长度/格式/必填/唯一/默认/不可编辑），分号分隔。

**状态维度**：

- 维度名与状态值逐字复制原文。
- 原文无枚举行时取原文原词，并在 `note` 注明出处。

**tags**：

- 按需标注：`approvable` / `multi-state` / `expirable` / `collaborative` / `configurable`。

**operations**：

- 扫描全部用户可执行操作（含通用功能/易用性章节）。
- `category` 枚举：`session/ui/file/query/crud/config`。
- `expected_results` ≥1，逐字取原文可观察结果（含提示语）。
- 原文未述：以操作名短语补 + `inferred`。

写入前 □：
- 操作的动词词根是否在 `action_verbs` 中？不在→通用回写协议。
- `expected_results` 是否逐字取原文？
- 同名操作是否已登记？

---

### Step 2：结构关系 → `m.add_structural()`

生效铁律：3、6、11。

- `frm` = 父/拥有方；`cardinality` 父→子视角，永不 N:1。
- M:N 无方向动词按叙述顺序并注明。

**三元分类（按序首条命中）**：

| 判定条件 | `relation_type` | `ownership_dimension` | 备注 |
|---|---|---|---|
| (a) A 为 B 提供配置/模板/分类，B 独立创建 | reference | configuration_source | |
| (b) B 无独立创建，A 创建时 B 自动入 initial，每条 A 必有 B | composition | business_ownership | |
| (c) B 有独立创建流程/前置条件/可能永不创建 | reference | configuration_source | |
| B 核心产出属第三方 C | — | — | 改 C→B（以 C 为 frm） |
| 判 (b) 且 1:1 | — | — | 复核"每条 A 必有 B"，可能无 B→归 (c) |

联动约束：`composition ↔ business_ownership`、`reference ↔ configuration_source`；`management_dimension` 必须复核并在 `comment` 写结论。

---

### Step 3：分支维度 → `m.add_branch_dimension()`

生效铁律：2。

**三型**：

| 类型 | 识别标准 |
|---|---|
| 配置型 | `is_config` 属性，创建时定、互斥、影响后续 |
| 运行时选择型 | "根据…选择/分为…情况" |
| 隐式分支 | 表格/权重表列维度、多 BR 共同体现的取值维度 |

```python
m.add_branch_dimension(
    dimension="...",
    entity="...",
    values=[...],
    impact_scope="...",
    evidence="...",
    branches=[{"value": "...", "target_transition": "t01", "desc": "..."}],
)
```

- `coverage` 不填，框架回填。
- 每个分支维度在 Step 5 中需 ≥1 条 BR 含 `branch_dimension`。

---

### Step 4：转换与因果

#### 4.1 转换 → `m.add_trans()`

生效铁律：10、14。

必填字段：`tid, entity, dimension, frm, to, action, role, preconditions, expected_results, traits, direction, priority, source_ref`。

- `traits` ∈ `[audit, rollback, branch, time_sensitive, data_constraint]`
- `priority` ∈ `[P0, P1, P2]`
- `direction` ∈ `[forward, backward, lateral, resume]`

**direction 判定（首条命中）**：

| 条件 | direction |
|---|---|
| 文档含"回退/返回/暂停/重启"等词 | 按文档 |
| `to` 或 `frm` 为侧挂状态 | `lateral` / `resume` |
| `frm` 在 `states` 列表先于 `to` | `forward` |
| `frm` 在 `states` 列表后于 `to` | `backward` |
| 以上均不满足 | `inferred=True`，comment 写依据 |

写入前 □：
- `action` 的动词词根是否在 `action_verbs` 中？不在→通用回写协议。
- `direction` 走了哪级判定？comment 注明。
- `frm` 是否为终态？

#### 4.2 preconditions → `precond(text, ptype, ref)`

生效铁律：12。

按序首条命中：

| 条件 | `ptype` | `ref` |
|---|---|---|
| 显式"实体.维度=状态"，状态值合法 | `state_ref` | `state_ref(entity,dimension,state)` |
| 仅状态值，匹配当前实体同维度 | `state_ref` | `state_ref(当前实体,dimension,state)` |
| 仅状态值，匹配他实体同维度 | `state_ref` | `state_ref(他实体,dimension,state)` |
| 跨实体"实体名+状态值"，消歧成功 | `state_ref` | `state_ref(...)` |
| 状态值不存在或无法消歧 | `constraint` | `null`，comment 注明降级 |
| 独立业务事件已完成 | `event_ref` | `null` |
| 含"不可/不得/禁止/累计/按X计算"等 | `constraint` | `null` |

`state_ref` 必填；`event_ref`/`constraint` 必须缺省 `null`，禁止传对象。

#### 4.3 角色 → `m.add_role()`

- 收录全部角色，未作执行者 `readonly=True`。
- `system` 保留不入 `roles`，role 可直接引用。

#### 4.4 自检（写入前完成）

- 非终态有出边。
- 孤立终态补入边：`frm` 必须非终态；优先业务合理源状态，补入转换标 `inferred=True` 并注明"终态可达性补入"；无非非终态可用→在 `note.conflict` 写"孤立终态[xxx]无非非终态入边"。
- 每维度有 `frm=None` 创建转换（跨维度初始化可拆建 + inferred 注明联动来源）。
- 分支覆盖。
- crud 操作 `note.comment` 回填对应局部标签（多个 `;` 分隔），无对应转换注明"无对应转换"及理由。
- 回写特权范围扩展至 Step 0 的 `action_verbs` 和 Step 0.5 的 `permission`。

#### 4.5 因果 → `m.add_causal()`

生效铁律：7、8。

写入前扫描已添加的 `add_causal`，同 `(frm,to)` 按铁律 8 去重。

**来源**：

| 来源 | `trigger_source` | `trigger` |
|---|---|---|
| 显式句式（B 完成后 A 变 / B 触发 A / A 依赖 B 完成） | `desc` | 原文 |
| `expected_results` 含对 E2 状态影响 | `expected_results` | 影响描述 |
| `preconditions` 含 `state_ref` 指向 E1 | `action` | 使 E1 进入该状态的 action |
| structural A→B 但 B 驱动 A | `bidi_coupling` | — |

- `evidence_transitions`：除 `desc`/`business_rule` 可空但 comment 注明位置外，其余必填局部标签。
- `rollback_propagation`：驱动方含 rollback 或文本含"退/撤销/驳回/拒绝"且被驱动方回退→`True`。
- `confidence`：显式 `high`，推导 `medium`，修补产物不得 `high`。

写入前 □：
- 同 `(frm,to)` 是否已存在？
- 每条因果是否过 4.6 鉴别？

#### 4.6 鉴别（每条因果写入前必过）

- **Q1**：X 变是否直接致 Y 变？（Y 需额外操作→约束）
- **Q2**：Y 侧 precondition 或 XC 已表达？→ 门禁不写入
- **Q3**：上级作下级门禁→约束；下级全完成上级自动推进→因果

判约束 → 标记 `[待写入: Step5 XC]`，`desc="由 Step 4.6 约束-因果鉴别确认…"`，Step 5 兑现。

---

### Step 5：约束补充

生效铁律：1、7。

- `invalid_transitions`：仅文档明确禁止时生成。
- `XC` 三来源：镜像 / 4.6 判约束 / 联动 / 分支差异。
- 框架对遗漏镜像自动补，但你应写全。

#### BR 字段正交

| 字段 | 取值 |
|---|---|
| `category` | `validation/computation/authorization/timing/notification/usability/display` |
| `signal_type` | 仅 `restrictive/usability/display/field_constraint` |

**信号映射**：

| 文本信号 | `category` | `signal_type` |
|---|---|---|
| 限制词（必须/不得/仅当/禁止/不能/不可/不超过） | validation/computation/authorization/timing/notification | `restrictive` |
| 陈述句（应提供/应支持/可） | `usability` | `usability` |
| 显示/展示 | `display` | `display` |
| 字段约束属性 | `validation` | `field_constraint` |

每个分支维度 ≥1 条 BR 含 `branch_dimension`；无信号不生成。

写入前 □：
- 4.6 判约束的 `[待写入: Step5 XC]` 是否已兑现？
- 每个分支维度是否 ≥1 条 BR 含 `branch_dimension`？
- 每条 BR 的 `signal_type` ∈ `{restrictive, usability, display, field_constraint}`？

---

### Step 6：机器校验

由框架执行，禁止代行。

校验项：引用完整性、状态结构、preconditions 结构、镜像完整性、分支穿透、structural 一致性、因果一致性、composition 同步性、跨模块对账、字符安全、空值规范、operations 完整性、direction 完整性、expected_results 对账、动词覆盖率、权限覆盖率。

**critical 清单**（命中即中断）：

1. 无 core 实体可建模
2. 主流程状态枚举完全缺失且无可推依据
3. 核心流程描述互相矛盾无法取舍
4. 输入为空或非需求文档
5. 框架校验修复失败（框架判定）

**中断协议**：

- **critical**：立即停，仅输出：
  ```json
  {"_meta": {"version":"19.2","generated_at":"...","source":"...","has_critical_ambiguity":true,"ambiguity_list":[...]}}
  ```
  澄清后从触发步骤重跑。
- **minor**：不暂停，假设填充 + `N(inferred=True, comment=...)`。
- 截断续传锚点：`断点位置: Step {N} | 已完成: {对象ID列表} | 下一个待处理: {对象ID及未完成字段}`。

---

## 输出形式

文件：`requirements_data/<文档名>.py`，有且仅有一个 `build()`。

```python
"""<文档名> 需求数据。"""

from srs_pipeline import DomainModel, N, attr, op, precond, state_ref


def build() -> DomainModel:
    m = DomainModel(source="<文件名，无则填 未命名文档>", document_scope="<覆盖范围>")

    m.set_prohibition_config({...})  # Step 0

    # Step 1→5 按顺序调用 ...
    return m
```

### 可用 API

```python
m.add_entity(id, name, desc, type="core", tags, attributes, state_dimensions, operations)
# dims 元素: {"dimension_name","states","initial","terminal","note"}

m.add_structural(frm, to, relation_type, cardinality, ownership_dimension, desc, confidence="high", note)

m.add_branch_dimension(dimension, entity, values, impact_scope, evidence, branches)

m.add_role(id, name, readonly=False)

m.add_trans(tid, entity, dimension, frm, to, action, role, preconditions, expected_results,
            traits, direction, priority, source_ref, note=None, sub_steps=None)

m.add_causal(frm, to, desc, trigger, trigger_source, evidence_transitions=None,
             rollback_propagation=False, confidence="high", note=None)

m.add_invalid(iid, entity, frm, to, reason, source_ref)

m.add_xc(xid, source_entity, source_transition, source_state, target_entity,
         target_dimension, target_condition, desc, source_ref)

m.add_br(bid, category, desc, entities_involved, source_ref, signal_type,
         severity="mandatory", note=None)

m.add_permission(role, operations)

m.set_prohibition_config(config)
```

### 辅助构造

```python
N(inferred=False, comment="", conflict="", branch_dimension="")
attr(name, desc, is_config=False)
op(name, category, expected_results, source_ref, note=None)
precond(text, ptype, ref=None)
state_ref(entity, dimension, state)
```

---

## 编号规则

- `tid=t01…`，`xc=x01…`，`br=b01…`，`it=i01…`（小写无横线）。
- 交叉引用均写局部标签。
- 实体 ID 格式：`E-{2~6 字母缩写}`（如 `E-TICKET`、`E-ORDER`），同一文档多次生成必须稳定。
- 调用顺序严格遵循文档叙述顺序。

---

## 示例

文档片段："项目选入的前置条件：项目处于待选入状态；结果通知单已上传；本阶段评价结果为差的项目不可选入。"

```python
m.add_trans(
    "t02", "E-PROJ", "项目状态", "待选入", "已选入", "项目选入", "R-001",
    [
        precond("项目处于待选入状态", "state_ref",
                state_ref("E-PROJ", "项目状态", "待选入")),
        precond("结果通知单已上传", "event_ref"),
        precond("本阶段评价结果为差的项目不可选入", "constraint"),
    ],
    ["选入后项目状态变为已选入"],
    [], "forward", "P0", "4.7.1 项目选入",
)
```

---

## 禁令

禁止输出以下内容：

- 手工转义
- 手写 `pipeline_trace/coverage/consistency_check/ambiguity_list/镜像兜底/正式编号/最终 JSON`
- 任何校验、统计、打印、文件读写、json 代码
- 除数据文件与锚点外的任何解释性内容