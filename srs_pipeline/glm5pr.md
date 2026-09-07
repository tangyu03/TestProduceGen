# 需求文档 → Python DSL 转换

## 0 总则

1. 实体/状态/转换由 §2 事件台账推导，判据唯一，无模式枚举。
2. 机械项由框架校验（§5 修复）；语义项由你负责（台账完备/情形分合/分类/因果鉴别/标注诚实）。
3. 顺序：§2 台账 → Step 1 实体 → Step 2 分支 → Step 3 转换 → Step 4 约束；每步以上一步产物为输入，推导中发现漏事件可回补台账重推。
4. `build()` 一经写出，仅框架回喂可改；动词/权限回写不算回修。装配期归一（编号移交、target_transition 回填、角色引用归一）框架自理，作者免回填。

## 1 契约

- 术语：XC＝跨实体约束（`add_xc` 产物）；BR＝业务规则（`add_br` 产物）；镜像＝跨实体 precondition 复制为 XC；事件台账＝`build()` 内的 `add_event` 调用序列，是数据文件本体；编号移交＝数据文件只写局部标签，正式编号由框架分配。
- 输出：`srs_data/<文档名>.py`，单 `build()`，头为 `add_event` 序列。形态三种：数据文件 / critical 中断 JSON / 断点锚点。`build()` 内仅骨架与 API 调用。
- 骨架逐字保留（docstring、import、build 头尾、DomainModel 绑定、台账段位）：

```python
"""<文档名> 需求数据。"""
from srs_pipeline import DomainModel, N, attr, op, precond, state_ref

def build() -> DomainModel:
    m = DomainModel(source="<文件名，无则填 未命名文档>", document_scope="<章节号清单>")
    # ===== 事件台账（§2）=====
    m.set_prohibition_config(config={...})
    # Step 1→4
    return m
```

- 元数据结构化落盘供框架校验。document_scope＝章节号清单（"§19.1；§19.3；§20.2–§20.11"，平行流程差异说明附后）；产物 source_ref 须落在声明章节内；收缩平行流程 → 分支降属性或补最小链，差异注于 scope。
- 编号：事件 `e01…`、转换 `t01…`、XC `x01…`、BR `b01…`、invalid `i01…`、角色 `r01…`（小写无横线）；实体 ID＝`E-{2~6 字母缩写}`；角色 id 直接落盘，引用一律走 `name`。
- API 全用关键字参数，唯一例外 `state_ref` 三参同型可位置式。
- source_ref 非空且可定位原文，子项号真实，复合引用以 `；` 分隔。XC 继承宿主 source_ref：镜像/联动取 `source_transition` 所指转换的 ref；4.5判取持有对应 precondition 的转换的 ref。
- critical（枚举缺失无推据/核心矛盾不可取舍）→ 立即停止，仅输出中断 JSON；其余 minor 假设填充＋inferred；口径不一致但不构成矛盾 → 两口径并列写入 `note={"ambiguity": "..."}`，由框架收集。截断续传锚点：`断点位置: Step {N} | 已完成: {标签列表} | 下一个待处理: {标签及未完成字段}`。
- 回写：Step 1–4 发现新动词/新角色/操作归属，在当前位置插入追加调用（注释标来源 Step）；`action_verbs` 追加去重，`permission` 同角色取并集。
- inferred 标注（推断与依据成对落盘）：

| 推断对象 | 标注方式 |
|---|---|
| 状态值 | 维度级 `inferred` 列表＋维度级 `note` 写依据 |
| attr / op | `N(inferred=True, comment="依据…")` |
| 转换/结构/BR | `note={"inferred": True, "comment": "依据…"}` |
| XC / IT | 无 note，由源转换/源规则继承 |

- 判定自报：direction 注命中级次（⓪–⑤）；结构四元注 a/b/c/d；分支三型注型别序号（①②③，写入 evidence）；op category 命中 ①–④ 特殊类时注序号；BR restrictive=True 时 note 注命中强制原词（如"必须"、"每天上午9点"）。
- 铁律：文档即数据（矛盾→critical）；空值规范（缺省 `[]`，critical 豁免）；不脑补（推断标注）；字符原样转录。

## 2 事件台账

事件＝业务动作使某主体情形空间变化的记录，每事件一条 `add_event` 调用：

```python
m.add_event(eid, entity=E-ID, dimension, action, actor, precondition, consequence, source_ref)
```

- action＝原文动作短语逐字：主语线索承载 actor 语义（"机构新增实验室信息"保留原文，不改写为"实验室新增"）。
- consequence：在情形空间取值（停留原情形也算落点，落为自环）。
- precondition＝自身状态值，或 `自身状态值；E-ID.状态值`（跨主体门禁；门禁值取同动作拆行事件中对应分支的 consequence），无内容填字符串 `"初始"`。
- 落点判定（按序）：① 动作使某主体情形空间变化 → 记该 (entity, dimension)；变化落在其他实体上 → 记那个实体。② 仅创建记录且该实体无状态面 → 非事件，转③。③ 无情形落点 → 用户可执行操作入 Step 1 operations；约束措辞入 Step 4 BR；系统行为（定时/自动触发、无状态落点，如"到期提醒"）入 Step 4 BR（notification/timing）。
- 粒度：一事件一 (entity, dimension)；一动作多状态面 → 拆行，每状态面一条 `add_event`，action 与 actor 相同，关联仅由转换 note 互引承载。
- 表格列：状态列取值随行动作变化 → 逐行逐列登记事件（entity＝状态面承载主体的 E-ID）。单元格多值双形态：顿号并列（"已核查、待发样"）＝快照，逐值登记落点；斜杠（"待核查/无需还样"）＝或语义分支值，逐值拆行登记。自环事件仅落动作的业务对象维度，行内其他列未变值按门禁判定写入 precondition，不立事件；他实体状态列的驻留值为动作对象/输入前提 → precondition；创建缺失 → minor 补一条创建事件（inferred 写依据）。台账完备性是根本职责，无机械兜底。

## Step 1 实体

### 1.0 词表 → `m.set_prohibition_config()`

`action_verbs`＝动作列动词词根（去名词成分，含复合动词）；操作动词经回写补入；无判别力词根（操作/处理/进行类）不入。`prohibit_keywords`＝复杂否定短语；`config` 仅含两键。

### 1.1 角色 → `m.add_role()` / `m.add_permission()`

来源 actor ∪ 权限章节；id=r01…；name＝原文逐字复制；无执行者 → readonly；system 不入 roles。permission 的 operations＝具体操作名（限 session/ui/file/query/config 及不改状态 crud）。

### 1.2 分组

entity 列即分组结果；分组唯一依据是原文命名；有状态变更事件的分组 → core 候选，仅 CRUD/配置 → managed 候选；多维度逐维推导；确认 E-ID 映射。

### 1.3 状态推导

为每个事件写出前置情形＝precondition＋先前 consequence。分合判据：

| 比较 | 结果 |
|---|---|
| Accept(S₁)≠Accept(S₂) | 分立 |
| Accept 相同，逐动作比后果 | 后果异→分立；全同→合并 |
| Accept 皆 ∅ | 比终局语义：异→分立；同→复核 |

- 命名：枚举行原词 > 散见原词（note 出处）> 语义命名（入 inferred，成对标注）。
- states 顺序＝原文枚举顺序（序判③④的比较基准）；states 值域＝文档枚举表值 ∪ 台账推导值。**状态面唯一承载**：一个状态面仅建在一个实体名下；枚举维度经裁决由他实体承载 → 建维时 note 注明"并入 E-XXX.<维度>"，无并入关系且无事件 → 按孤岛处置。
- initial＝创建事件落入的状态；每个已建模维度（≥1 转换）有 `frm=None` 创建转换；零转换声明＝枚举备份/孤岛，不要求创建转换（框架降级警告）。
- **图完整性（无出边闭合）**：states 值无出边 → 三选一——回 §2 补事件重跑 / 入 terminal / 孤岛标注，非终态同样适用；文档具名终态但推导有出边 → 以推导为准＋note 说明。
- 孤岛（枚举但无事件覆盖）：入 states＋note"枚举但无事件覆盖"，原样保留（框架降级警告）。
- 事件仅变更属性 → 不立状态，入 operations 或同状态自环。

### 1.4 实体

- 分类（交集归 core）：core＝状态枚举/多步骤多角色/状态自主/审批链/独立载体/可独立循环；managed＝管理员 CRUD/配置字典/状态简单。
- tags：`approvable`＝存在审批类转换；`multi-state`＝≥2 状态维度；`expirable`＝存在失效/过期转换或 BR；`collaborative`＝多角色操作同一状态维度（转换层多执行者写 role 列表）；`configurable`＝存在 is_config 属性。
- operations：op 名称同一实体内唯一；通知语义由 BR 承载；category ①file②session③ui④config＞crud＞query；`expected_results` ≥1 逐字取原文可观察结果，未述补＋inferred；note.role 必填；op note 只写 role 与操作语境注释；op-转换关联在 3.3 经 `link_op_transition` 登记。

### 1.5 结构关系 → `m.add_structural()`

`cardinality ∈ {"1:1", "1:N", "M:N"}`（父→子视角）；M:N 无方向动词按叙述顺序定 frm/to。四元判定（首条命中 a→b→c→d，成套取自同一行）：

| 判定 | relation_type | ownership_dimension |
|---|---|---|
| (a) A 为 B 提供配置/模板/分类，B 独立创建 | reference | configuration_source |
| (b) B 无独立创建，A 创建时 B 自动入 initial，每条 A 必有 B | composition | business_ownership |
| (c) B 有独立创建流程，B 是 core 流程实体（type=core 且有 dependent），A 为其业务归属容器 | composition | business_ownership |
| (d) B 有独立创建流程/前置条件/可能永不创建，且不满足 (c) | reference | configuration_source |

(c) 先于 (d)；A 仅为发起人/持有人/操作对象 → 降 (d)；B 核心产出属第三方 C → 改 C→B；判 (b) 且 1:1 → 复核"每条 A 必有 B"，可能无 B → 归 (d)。dependent 三步：①文档直写 B 的下级实体 → 有；②未写 → 按 (d)＋`confidence=medium`；③后续揭示 → 升级 (c)，confidence 保持 medium。`management_dimension` 必须复核并写 comment。

**(b) 伴随创建编码契约**：判 (b) 实体的创建转换（frm=None）一律携指向父实体已存在态的 `state_ref` 前置，不论业务上是否另有门禁（一个前置可身兼门禁与伴随证据两职）。此为编码约定，非业务要求，不必另找理由。锚点必须指向父实体实际持有该状态的维度；

## Step 2 分支

三型（型别序号写入 evidence）：① 配置型（is_config 属性：创建时定、互斥、影响后续）/ ② 运行时选择型（"根据…选择/分为…情况"）/ ③ 隐式分支（表格/权重表列维度、多 BR 共同体现的取值维度）。

准入判据＝可锚定转换：影响状态机路径或转换结果的取值维度才是分支维度，纯查询/筛选仅作实体属性。分支 values＝文档命名的条件/情形；状态落点值不作分支值（落点差异经转换分立承载）；角色差异由转换 role 字段承载。注册前逐 value 自查台账锚点：value 路径在台账无事件 → 维度降为实体属性，或按 document_scope 补最小创建链。

target_transition＝语义描述，以目标转换 action 词为锚（如"能力验证计划发布转换"）；同动作多转换时括注 frm→to 或分支值消歧。指向规则：路径分歧各 value 指向该分支路径**首条（创建）转换**，结果差异各 value 指向共用转换；只锚首条，后续转换归属由转换层 `branch_values` 承载（§3.1 归属铁律），不在 branches 重复。框架自动匹配精确 tid，模型免回填。

## Step 3 转换与因果

### 3.1 转换 → `m.add_trans()`

转换＝已登记状态空间上的边，台账每条事件在其 (entity, dimension) 上落一条转换。构造前提：entity 已登记；dimension ∈ 该实体维度；frm/to ∈ 该维度 states；frm=None 仅限创建转换（to＝initial）。必填：`tid, action, role, preconditions, expected_results, traits, direction, priority, source_ref`。`note.comment` 引用事件 id。

**多状态面出生值契约**：创建转换（frm=None）的 `to` 只覆盖本维度 initial；同一动作若同时建立同实体**其他**状态维度的出生值（平行流程型各分支创建面常见），必须在本条 `expected_results` 逐面声明「{维度名}初始为{值}」（如受理报名同时使预通知状态出生为未发送 → expected_results 含「预通知状态初始为未发送」）。该声明是消费转换在本分支唯一的创建根依据，漏声明 → 下游消费该状态的转换在本分支无生产者可挂（S1 会报「初始出生点未声明」告警）。声明只落一处：承载该出生动作的创建转换。

`traits`：`audit`＝留痕要求；`rollback`＝回退/撤销；`branch`＝分支转换（路径分歧/结果差异均标）；`time_sensitive`＝超时/时限触发；`data_constraint`＝执行前置数据校验。

侧挂状态＝文档以挂起/暂停/停用/恢复语义命名的状态，或本维度已被某条 lateral 转换指向的状态。

direction（首条命中）：
⓪ frm=None → forward，不再判。
① "回退/返回/驳回/退回"→ backward；"暂停/挂起/停用"→ lateral；"重启/恢复/启用"→ resume；自环（frm==to）跳过本级直接按⑤判——自环无状态迁移，方向词描述动作内容。
② to 为侧挂 → lateral；frm 为侧挂 → resume（to 侧先判，均为侧挂回①）；无锚点且确需侧挂 → lateral＋inferred 注依据。
③ frm 先于 to → forward；④ 后于 → backward。
⑤ 仅自环 → forward＋inferred。
③④与业务语义冲突（循环状态机）→ 语义优先，comment 记"序判{③|④}，语义{取值}（理由）"。

priority：P0＝主流程必经；P1＝分支/回退/驳回等业务必需非主路径；P2＝辅助/低频/易用性；无法判定 → P1＋inferred。

**分支落盘**（同一动作因分支值立出不同转换）：
- 路径分歧（中间态或落点不同）→ 分立多条：各携对应分支值 precondition（ptype=constraint）、声明 `branch_values=[本条仅在的分支值]`、role 取该分支执行者、标签同根后缀（t02/t02b）、traits 含 `branch`、note.branch_dimension 填维度名。
- 结果差异（路径与落点均同、仅结果措辞异）→ 共用一条：expected_results 逐值用"若{维度}={值}，则…"，traits 含 `branch`，不声明 branch_values。
- **归属铁律**：branch_values＝转换的生命周期身份（声明后 P2 不再为其 all-values 展开，S0/S1 相位在归属分支 lifecycle 链内取值）。自查：(frm,to) 路径仅在单一分支值的流程表/叙述出现 → 必须声明；两分支皆有该动作与路径 → 共享不声明。**平行流程型**（同一维度在多章节各有完整生命周期，且创建转换落点次序互逆）：除两条创建转换互为分立外，各分支全部后续推进转换均须声明 branch_values，仅两分支共有收尾动作共享；漏声明 → 他分支子图被污染成环，相位链退化为枚举序。

### 3.2 preconditions → `precond(text, ptype, ref, note)`

先 state_ref 匹配；跨主体门禁（E-ID.状态值）落 state_ref 全锚点；含否定词同判；状态值无法消歧才降级 constraint，note 写降级理由；跨实体同名状态按 source_ref 位置就近归属。

| 条件 | ptype | ref | note |
|---|---|---|---|
| 状态值可匹配到 (实体, 维度)，含跨主体门禁 | `state_ref` | `state_ref(entity,dimension,state)` | 缺省 |
| 状态值无法消歧 | `constraint` | null | `{"comment": "降级理由…"}` |
| 分支维度取值条件 | `constraint` | null | `{"comment": "分支值条件"}` |
| 独立业务事件已完成（一次性完成信号；持续状态门禁走 state_ref） | `event_ref` | null | 缺省 |
| 含"不可/不得/禁止/累计/按X计算" | `constraint` | null | 缺省 |

### 3.3 自检

- **op-转换关联**：有状态迁移语义的操作经 `m.link_op_transition(entity=…, op=…, transitions=[…])` 登记——对照本实体 add_trans 声明逐条登记，依据＝action 语义＋frm→to 方向；跨实体转换在 note 点名目标实体；无对应者不调用。
- **回写**：遗漏动词/权限按回写协议追加。

### 3.4 因果 → `m.add_causal()` 与鉴别

frm/to＝实体 ID，描述 X 的变化直接致 Y 的变化；两实体间的顺序门禁由 precondition/XC 表达。每案依序过 Q1→Q2→Q3，命中即止：
- Q1：X 变直接致 Y 变？Y 需额外操作 → 约束，标 `[待写入: Step4 XC]`。
- Q2：门禁已由 Y 侧 precondition 或既有 XC 表达？已表达 → 止于 Q2，不写因果、不标记。
- Q3：上级作下级门禁 → 约束（标记 `[待写入]`）；下级全完成上级自动推进 → 因果。

来源表：`desc`（显式句式 B 完成后 A 变）/ `expected_results`（含 E2 影响）/ `action`（preconditions 含 E1 的 state_ref）/ `bidi_coupling`。`evidence_transitions`：desc/business_rule 可空（comment 注明位置），其余必填局部标签。confidence：显式 high，推导 medium，修补≤medium。写入前扫描已有 add_causal，同 (frm,to) 去重仅升级：desc/trigger 以 `;` 合并、evidence_transitions 并集、rollback 取或；add_causal 无 causal_pairs 参数。

## Step 4 约束

回访：①检索 `[待写入` 逐条兑现为 XC；②核对 prohibit_keywords——每条短语须有产物 source_ref 可定位；③核对 document_scope——产物 source_ref 均落在声明章节内。

invalid → `m.add_invalid()`：仅明文禁止的状态转换（"不允许/不可以从X到Y"）。

XC → `m.add_xc()`：`xc_source ∈ {镜像, 联动, 4.5判, 分支差异}`（4.5判对应 3.4 鉴别判为约束）；source_transition 一律填生产者转换（达 source_state 的转换）；镜像 XC 可省略（框架补）。target_transition：镜像/联动必填（联动 target_condition＝该转换的 to 新值），4.5判可空（desc 含 BR 标签），分支差异可缺省。

BR → `m.add_br()`：仅规范性约束句生成（纯描述性叙述不生成）；一句一 BR。三字段各自判定：
- **category**＝管什么：`validation`（默认）/`computation`/`authorization`/`timing`/`notification`/`usability`/`display`；纯限制性规则（不属任何业务域）→ `restrictive`。
- **restrictive**＝强制约束：desc 含强制措辞（必须/不得/仅当/禁止/不能/不可/不超过，及"X日内/X次以内"类量化）→ True，note 注命中原词；支持性/功能性规则缺省 False。enforcement 免传（框架从 restrictive 派生）。
- authorization → 角色放 note.role（name 列表）。多实体 BR 必填 constrained_entity（增删改→操作对象实体；对称规则→任一＋"代表实体"；单实体不填）。Step 2 注册的分支维度若在本步产 BR → 该 BR 的 branch_dimensions 含此维度（desc 含维度名或分支值作钩子）。系统行为 BR 的 entities_involved＝作用目标业务实体。

## 5 修复

回喂格式：`[{"check": "<校验码>", "labels": ["t07"], "expected": "…"}]`。最小修复：只改回喂点名项；修补 confidence≤medium；根源漏事件 → 先补 `add_event` 再补转换（回喂触发的补事件是合法回修）。

CLI：critical 中断时回喂 JSON 默认控制台打印（不落盘，`--feedback <路径>` 可选落盘），由 `build_feedback` 确定性生成（check＝校验码，labels＝消息文本抽取的候选/被修条目，expected＝修法指引全文）；将打印 JSON 投给 LLM 触发再生成，勿手工改数据文件。

分支回填偏差（target_transition 语义描述无唯一候选）：正常完成路径若 `meta.branch_tt_deviations` 非空，控制台打印 §5 格式偏差回喂（check=BRANCH_TT_DEVIATION，expected 写明"按 action 词锚重写描述"），计入校验报告 C31 warning（`--strict` 门禁）；偏差属优雅降级（P2 走 all-values 兜底），warn 级不断中断。

## 6 API

```python
m = DomainModel(source, document_scope)  # document_scope＝章节号清单
m.add_event(eid, entity, dimension, action, actor, precondition, consequence, source_ref)
# entity 用 E-ID；precondition＝"自身状态值"、"自身状态值；E-ID.状态值"（跨主体门禁）或"初始"
m.set_prohibition_config(config)           # 限调一次
m.add_action_verbs(verbs); m.add_prohibit_keywords(keywords)
m.add_role(id, name, readonly=False)       # name＝原文角色名逐字复制
m.add_permission(role, operations)         # role 用 name；operations 填具体操作名
m.add_entity(id, name, desc, type="core", tags, attributes, state_dimensions, operations)
# state_dimensions 元素（键名精确 dimension_name）：
#   {"dimension_name": "项目状态", "states": ["待开始", "报名中"],
#    "initial": "待开始", "terminal": ["已结束"],
#    "inferred": ["进行中"], "note": {"comment": "依据…"}}
m.add_structural(frm, to, relation_type, cardinality, ownership_dimension, desc, confidence="high", note=None)
m.add_branch_dimension(dimension, entity, values, impact_scope, evidence, branches)
m.add_trans(tid, entity, dimension, frm, to, action, role, preconditions, expected_results, traits, direction, priority, source_ref, note=None, branch_values=None)
# branch_values＝分支归属（生命周期身份）：仅在哪些分支值下存在；
# 空/缺省＝共享模板（每个分支值下都实例化）或非分支转换。见 §3.1 归属铁律。
m.add_causal(frm, to, desc, trigger, trigger_source, evidence_transitions=None, rollback_propagation=False, confidence="high", note=None)  # frm/to＝实体 ID
m.add_invalid(iid, entity, frm, to, reason, source_ref)
m.add_xc(xid, source_entity, source_transition, source_state, target_entity, target_dimension, target_condition, desc, source_ref, target_transition=None, xc_source)
m.add_br(bid, category, desc, entities_involved, source_ref, restrictive=False, note=None, constrained_entity=None, branch_dimensions=None)
# category 八值见 Step 4；restrictive＝强制约束 bool（True 时 note 注命中原词）；enforcement 免传（框架从 restrictive 派生）
m.link_op_transition(entity, op, transitions, note=None)
# op→转换关联；3.3 时点追加（转换已落盘）；transitions＝tid 列表；跨实体关联 note 点名目标实体

N(inferred=False, comment="", conflict="", branch_dimension="", role=None)
attr(name, desc, is_config=False)
op(name, category, expected_results, source_ref, note=None)
precond(text, ptype, ref=None, note=None)
state_ref(entity, dimension, state)
```

## 7 专项

- 分支分立/共用/归属自查见 §3.1 分支落盘。
- system 触发：超时/自动触发且改变状态的事件 role="system"，traits 可含 `time_sensitive`，走完整推导。

## 8 示例

```python
# 台账（创建事件；precondition 无内容填字符串"初始"）：
m.add_event(eid="e01", entity="E-XM", dimension="项目状态", action="设计方案编制",
            actor="策划人员", precondition="初始", consequence="待开始",
            source_ref="19.1方案设计阶段")

# 台账（跨主体门禁形态）：
# add_event("e49","E-PJ","评价状态","评价人员评价","评价人员","待评价；E-BMJL.结果已提交","评价中","20.7.1.2")
m.add_trans(
    tid="t22", entity="E-PJ", dimension="评价状态",
    frm="待评价", to="评价中", action="评价人员评价", role="评价人员",
    preconditions=[
        precond(text="评价处于待评价状态", ptype="state_ref",
                ref=state_ref("E-PJ", "评价状态", "待评价")),
        precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        precond(text="评价组长已完善测试项目及评价细则", ptype="event_ref"),
    ],
    expected_results=["评价状态变为评价中"],
    traits=[], direction="forward", priority="P0",
    source_ref="20.7.1.2协同评价",
    note={"comment": "源自 e49；③；跨主体门禁落 state_ref"},
)

# 台账：add_event("e03","E-TASK","任务状态","审批通过","一级审批员","待审批","审批通过","4.2审批流程")
m.add_trans(
    tid="t03", entity="E-TASK", dimension="任务状态",
    frm="待审批", to="审批通过", action="审批通过", role="一级审批员",
    preconditions=[precond(text="任务处于待审批状态", ptype="state_ref",
                           ref=state_ref("E-TASK", "任务状态", "待审批")),
                   precond(text="任务级别=B级", ptype="constraint",
                           note={"comment": "分支值条件"})],
    expected_results=["B级任务审批通过，状态变为审批通过"],
    traits=["branch"], direction="forward", priority="P0",
    source_ref="4.2审批流程",
    note={"branch_dimension": "任务级别", "comment": "源自 e03；路径分歧：B级分支，Step2 value=B级→本条"},
)
# t03b：待审批→待二级审批（C级，action=一级审批通过），同型续写（branch_values=["C级"]）

# 平行流程型归属铁律：分支专属转换必须声明 branch_values，防他分支子图成环：
m.add_trans(
    tid="t44", entity="E-XM", dimension="项目状态",
    frm="报名中", to="待开始", action="设计方案编制", role="策划人员",
    preconditions=[precond(text="项目处于报名中状态", ptype="state_ref",
                           ref=state_ref("E-XM", "项目状态", "报名中"))],
    expected_results=["项目状态变为待开始"],
    traits=["branch"], direction="forward", priority="P0",
    source_ref="19.3项目状态分析",
    branch_values=["测量审核"],
    note={"branch_dimension": "项目类型", "comment": "源自e44；序判④，语义forward（测量审核先受理报名后方案设计立项）；测量审核分支（与t01设计方案编制创建分立）"},
)
# 两分支共有的收尾动作（如发放结果报告和证书）→ 共享，不声明 branch_values

# 结果差异型（落点同，仅措辞异）：
m.add_trans(
    tid="t05", entity="E-PROJ", dimension="项目状态",
    frm="评审中", to="已评审", action="完成评审", role="system",
    preconditions=[precond(text="项目处于评审中状态", ptype="state_ref",
                           ref=state_ref("E-PROJ", "项目状态", "评审中"))],
    expected_results=["若评审方式=常规评审，则需专家打分完成后项目状态变为已评审",
                      "若评审方式=简易评审，则直接项目状态变为已评审"],
    traits=["branch"], direction="forward", priority="P0",
    source_ref="4.8.1 评审方式",
    note={"branch_dimension": "评审方式", "comment": "结果差异型：落点唯一"},
)

# direction 语义优先（循环状态机）：
m.add_trans(
    tid="t07", entity="E-YP", dimension="样品状态",
    frm="已核查", to="待核查", action="批次重置", role="样品管理员",
    preconditions=[precond(text="样品处于已核查状态", ptype="state_ref",
                           ref=state_ref("E-YP", "样品状态", "已核查"))],
    expected_results=["样品状态变为待核查，进入下一批次"],
    traits=[], direction="forward", priority="P1",
    source_ref="19.1实施阶段",
    note={"comment": "源自 e07；序判④，语义forward（循环状态机），语义优先"},
)

# op-转换关联（3.3 时点追加；op note 内不写 tid）：
m.link_op_transition(entity="E-FY", op="缴费单退款", transitions=["t22"])

# 因果（实体级）：
m.add_causal(
    frm="E-BMJL", to="E-JFTZ",
    desc="报名记录创建后系统自动初始化缴费通知单为未发送；报名审核通过后系统自动发送缴费通知单",
    trigger="报名记录创建/报名审核通过后缴费通知自动初始化与发送",
    trigger_source="expected_results",
    evidence_transitions=["t09", "t23", "t12", "t25"],
    rollback_propagation=False, confidence="high",
    note={"comment": "expected_results 明写'同时创建/变为'；门禁对照：'审核通过后方可缴费'不写因果（Y 需操作且 precondition 已表达）"},
)

# 联动 XC（生产者≠持有者；target_condition=新值）：
m.add_xc(xid="x04", source_entity="E-XM",
         source_transition="t02", source_state="报名中",
         target_entity="E-BMJL", target_dimension="报名记录状态",
         target_transition="t09", target_condition="报名待审核",
         xc_source="联动",
         desc="项目进入报名中后联动开启报名记录创建，新记录初始化为报名待审核",
         source_ref="19.1实施阶段")

# 系统行为 BR（restrictive=True 形态：量化强制触发，note 注命中原词；enforcement 免传）：
m.add_br(
    bid="b15", category="notification",
    desc="系统每天上午9点扫描证书信息，距到期时间等于30天时自动发送邮件提醒用户并抄送项目管理员",
    entities_involved=["E-BMJL"], source_ref="20.5.2.3", restrictive=True,
    note={"comment": "restrictive命中'每天上午9点'（量化强制触发）；category判通知；无状态落点，不入台账/operations"},
)

# 角色引用一律 name；note.role 多角色写列表；分支承载＝branch_dimensions 参数；支持性规则 restrictive 缺省：
m.add_permission(role="项目管理员", operations=["查询项目", "新增项目", "文件整理"])
m.add_br(
    bid="b23", category="computation",
    desc="评价支持分值和权重两种方式，分值按累加计算得分，权重按加权计算得分",
    entities_involved=["E-PJ"], source_ref="20.7.1项目列表",
    note={"role": ["评价人员"], "comment": "支持性规则，restrictive 缺省；category判计算衍生"},
    branch_dimensions=["评分方式"],
)
```