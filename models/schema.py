"""
Schema — Pydantic models for strong validation (invariant guards) in the
P3 Agent Engine.

Every stage transition (S0 → S1 → S2 → S3 → S4) should validate its output
against the corresponding model before writing into the global state pool.
This guarantees that downstream nodes always receive well-shaped data and
makes invariant violations fail fast with a clear error message.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── 义务类型 (S1.0 类型总表, 单一事实源) ────────────────────────────────
# 语义表原文见 prompts/s1_prompt.py §类型总表。值是输出 JSON obligation_type
# 字段的数值契约, 校验器/排序/回放均按数值读取 — 故用 IntEnum (序列化值 =
# 裸 int, 双跑 SHA-256 字节不变), 禁止改成 str Enum。

class ObligationType(IntEnum):
    """Procedure.obligation_type 的取值域 (Type1-Type7 + Type9)。"""

    UNSPECIFIED = 0         # 缺失兜底 (get 默认 / 未分类)
    TRANSITION = 1          # Type1 transition_obligations (状态转换规程)
    SIDE_EFFECT = 2         # Type2 TO.side_effects (嵌入 Type1 的 V 步, 不独立生成)
    ATTRIBUTE_CONFIG = 3    # Type3 EO(attribute_config) 配置属性分支覆盖
    CONSTRAINT = 4          # Type4a CO(constraint) 前置门禁规程
    LIFECYCLE = 5           # Type4b CO(lifecycle) 生命周期绑定规程
    CRUD = 6                # Type5 EO(crud_operation) CRUD 操作规程
    INVALID = 7             # Type6 RO(invalid_transition) 非法转换验证
    RULE = 8                # Type7 RO(business_rule) 重分类 — 独立业务规则规程
    FIELD_VALIDATION = 9    # Type9 field_validation


_TYPE_LABELS = {
    ObligationType.TRANSITION: "Type1(Transition)",
    ObligationType.ATTRIBUTE_CONFIG: "Type3(Attribute)",
    ObligationType.CONSTRAINT: "Type4a(Constraint)",
    ObligationType.LIFECYCLE: "Type4b(Lifecycle)",
    ObligationType.CRUD: "Type5(CRUD)",
    ObligationType.INVALID: "Type6(Invalid)",
    ObligationType.RULE: "Type7(BR)",
}


def obligation_type_label(ot: int) -> str:
    """Type 展示名, 替代 main.py / s1_fix_replay.py 各自重复的 type_labels 字典。"""
    try:
        member = ObligationType(ot)
    except ValueError:
        return f"Type{ot}"
    return _TYPE_LABELS.get(member, f"Type{ot}")


# ── S0 Models ────────────────────────────────────────────────────────────


class PhaseTable(BaseModel):
    """Phase table produced by S0 for the primary entity."""

    primary_dimension: str
    state_to_phase: dict
    phase_names: list[str]
    phase_count: int

    @model_validator(mode="after")
    def _check_phase_consistency(self) -> "PhaseTable":
        # phase_count must equal the number of named phases
        if self.phase_count != len(self.phase_names):
            raise ValueError(
                f"phase_count ({self.phase_count}) != len(phase_names) ({len(self.phase_names)})"
            )
        # state_to_phase is nested: {dimension: {state_name: phase_idx}}
        # BUGFIX: previously iterated only the outer dict, treating the inner
        # dict (e.g. {"待开始": 0, ...}) as a phase_idx and rejecting it as
        # "not int / out of range".  Recurse into the inner dict.
        for dimension, state_map in self.state_to_phase.items():
            if not isinstance(state_map, dict):
                raise ValueError(
                    f"state_to_phase['{dimension}'] must be a dict of "
                    f"{{state_name: phase_idx}}, got {type(state_map).__name__}"
                )
            for state_name, phase_idx in state_map.items():
                if not isinstance(phase_idx, int) or phase_idx < 0 or phase_idx >= self.phase_count:
                    raise ValueError(
                        f"state_to_phase['{dimension}']['{state_name}'] = {phase_idx} "
                        f"is out of range [0, {self.phase_count})"
                    )
        return self


class EngineState(BaseModel):
    """Complete S0 output — the engine state that feeds S1."""

    primary_entity: str
    phase_table: PhaseTable
    dep_state_phase_map: dict
    contextual_phase_rules: dict = {}
    state_type_map: dict
    dependent_entities: list[str]
    entity_parent: dict
    dependency_depth: dict
    topology_levels: dict
    leaf_entity_ids: set = set()
    virtual_entities: dict = {}

    @model_validator(mode="after")
    def _check_primary_entity(self) -> "EngineState":
        if self.primary_entity not in self.topology_levels:
            raise ValueError(
                f"primary_entity '{self.primary_entity}' not found in topology_levels"
            )
        if self.primary_entity in self.dependent_entities:
            raise ValueError(
                f"primary_entity '{self.primary_entity}' must not appear in dependent_entities"
            )
        # I1: primary_dimension non-null + primary entity spans all phases
        if not self.phase_table.primary_dimension:
            raise ValueError("I1: primary_dimension is null")
        state_map = self.phase_table.state_to_phase.get(
            self.phase_table.primary_dimension, {}
        )
        if not state_map:
            raise ValueError(
                f"I1: primary entity '{self.primary_entity}' has no state-to-phase "
                f"mappings in primary_dimension '{self.phase_table.primary_dimension}'"
            )
        # I7: parent < child (dependency_depth)
        for child, parent in self.entity_parent.items():
            if parent and parent in self.dependency_depth and child in self.dependency_depth:
                p_depth = self.dependency_depth[parent]
                c_depth = self.dependency_depth[child]
                if p_depth >= c_depth and p_depth > 0:
                    raise ValueError(
                        f"I7: parent '{parent}' (depth={p_depth}) not shallower "
                        f"than child '{child}' (depth={c_depth})"
                    )
        # I8: VE parents unique and ≠ original_entity, co_ids non-empty
        ve_parents: dict[str, str] = {}
        for ve_name, ve in self.virtual_entities.items():
            parent = ve.get("parent_entity", "")
            original = ve.get("original_entity", "")
            if parent == original or parent == ve_name:
                raise ValueError(
                    f"I8: VE '{ve_name}' parent == original/self '{parent}'"
                )
            # Parents must be unique (no two VEs from same original→same parent)
            key = f"{original}→{parent}"
            if key in ve_parents:
                raise ValueError(
                    f"I8: VE '{ve_name}' has duplicate parent mapping '{key}' "
                    f"(already used by '{ve_parents[key]}')"
                )
            ve_parents[key] = ve_name
        # I14: contextual dimensions must not appear in dep_state_phase_map
        for ctx_key in self.contextual_phase_rules:
            parts = ctx_key.split(".", 1)
            if len(parts) == 2:
                entity, dim = parts[0], parts[1]
                if entity in self.dep_state_phase_map and dim in self.dep_state_phase_map[entity]:
                    raise ValueError(
                        f"I14: contextual dimension '{ctx_key}' still present "
                        f"in dep_state_phase_map"
                    )
        return self


# ── S1 Models (BDD: Given-When-Then) ─────────────────────────────────────


class GivenClause(BaseModel):
    """A business-state precondition (Given).

    Describes the business state that must hold before the When event
    fires.  This is NOT a UI navigation instruction — it is a declarative
    statement about the business world.
    """

    target: str               # "E-X.维度" — the business object
    state: str                # required state value (e.g. "待审批")
    description: str = ""     # human-readable context (e.g. VE scenario label)
    # 渲染格式选择器 (DECISIONS ㉛): S1 按前置类型路由, 渲染层纯格式分发, 不再文本匹配。
    #   "state"      → `{target} 状态 = {state} ({desc})`   主锚定/同维度/跨维度纯状态
    #   "event"      → 事件已完成断言, 独立 Given (同 state 格式)
    #   "flow"       → `{target} 流转：{desc}`   跨维度流转形态 (ref.state 是目标态)
    #   "constraint" → `约束：{desc}`             业务约束, 无前置态概念
    #   "branch"     → `分支条件：{value}`         分支维度 Given
    # constraint/flow 允许 state 为空 (无前置态); 其余类型 state 必须非空。
    given_type: str = "state"


class WhenClause(BaseModel):
    """The business event under test (When).

    Describes the business event that triggers the behavior — NOT the
    mechanical action ("点击按钮") but the business occurrence ("审批通过").
    A procedure has exactly one When (single behaviour under test).
    """

    target: str               # "E-X.维度" — where the event occurs
    event: str                # business event description (declarative)
    actor: str = ""           # role triggering the event (e.g. "实验室管理员")
    action: str = ""          # concrete action (optional, e.g. "审批通过")


class ThenClause(BaseModel):
    """An observable business outcome (Then).

    Describes a business-observable result — NOT a test assertion
    ("assertEqual(state, X)") but a statement of what an observer can see.
    Multiple Thens are allowed (one behavior → many observable effects).
    """

    target: str                       # "E-X.维度" — what is being observed
    expectation: str                  # expected observation (e.g. "状态=已通过")
    kind: Literal["state", "behavior", "prompt"] = "state"
    br_refs: list[str] = []           # embedded BR IDs (e.g. ["BR-03"])
    cross_refs: list[str] = []        # other entities involved in this observation
    dedup_group: str | None = None    # 渲染层去重标记(数据驱动,而非渲染层匹配文本):
                                      #   "transition_flow"   状态流转:from→to(保留)
                                      #   "transition_target" 状态转换为X(有 flow 时省略)
                                      #   "coverage_noise"    覆盖X的Y操作(无可观察结果)
    subsumed: bool = False            # S1 吸收标记: transition_target 状态行被同 target
                                      # 的 behavior 行完全包含(状态…为X)→ 渲染层省略。
                                      # 吸收判断在 S1 完成(数据层), 渲染层只消费标记。


class BRClassification(BaseModel):
    """Classification result for a business rule."""

    br_id: str
    category: Literal[
        "attribute_effect",
        "transition_constraint",
        "crud_constraint",
        "negative_test",
        "standalone",
    ]
    host_proc_type: int


class Procedure(BaseModel):
    """A BDD scenario: Given(s) — When — Then(s).

    Replaces the legacy flat ``steps: list[ProcedureStep]`` structure with
    three semantically-typed clause lists.  This enforces BDD structure at
    the schema level — a procedure cannot have a Then without a When, and
    operation details are kept separate from the business specification.
    """

    temp_id: str
    source_ids: list[str]
    entity: str
    dimension: Optional[str] = None
    obligation_type: int
    risk_trait: str

    # ── BDD clauses (replaces flat steps list) ──
    givens: list[GivenClause] = Field(default_factory=list)
    when: WhenClause
    thens: list[ThenClause]

    # ── Execution details (kept separate from spec) ──
    # UI navigation, button clicks, data entry — anything a test executor
    # needs but that is NOT part of the business specification.
    operation_hints: list[str] = Field(default_factory=list)

    # ── 时间控制声明 (V06) ──
    # 时间触发型用例须声明 mechanism ∈ {clock_injection, db_time_update,
    # scheduler_manual_trigger},骨架阶段 status 可为 "planned"。
    # S1 从时效语义推导,见 _derive_time_mechanism 的主触发机制。
    time_control: Optional[dict] = None

    gen_seq: int
    post_state: str
    cascade_chain: Optional[str] = None
    embedded_brs: list = Field(default_factory=list)

    # Stage-attached fields (populated progressively)
    S2_fields: "S2Fields" = Field(alias="_S2_fields")
    S3_fields: "S3Fields" = Field(alias="_S3_fields")
    S4_fields: "S4Fields" = Field(alias="_S4_fields")

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _check_bdd_invariants(self) -> "Procedure":
        """I2 (BDD): exactly one When, ≥1 Then, Givens describe business state.

        Legacy I2 only required A≥1, V≥1.  The BDD invariant is stronger:
          - When is mandatory and singular (one behaviour per procedure)
          - Thens ≥ 1 (must have at least one observable outcome)
          - Each Then must have a non-empty, non-tautological expectation
          - Givens are optional but, if present, must describe business
            state (not UI navigation)
        """
        # When is mandatory — enforced by schema (non-optional field),
        # but double-check here for clarity.
        if not self.when.event:
            raise ValueError(
                f"Procedure {self.temp_id}: When.event must be non-empty"
            )

        # Thens ≥ 1
        if not self.thens:
            raise ValueError(
                f"Procedure {self.temp_id}: must contain at least one Then clause"
            )

        # Each Then must have a meaningful expectation (I19: no tautology)
        forbidden_expectations = {
            "查看效果", "查看状态", "验证效果", "验证分支路径可达", "验证差异",
        }
        for i, then in enumerate(self.thens):
            if not then.expectation:
                raise ValueError(
                    f"Procedure {self.temp_id}: Then[{i}].expectation is empty"
                )
            if then.expectation in forbidden_expectations:
                raise ValueError(
                    f"Procedure {self.temp_id}: Then[{i}].expectation "
                    f"'{then.expectation}' is a forbidden tautology "
                    f"(I19: must be a concrete observable)"
                )

        # Givens must describe business state, not UI navigation.
        # given_type 分流 (DECISIONS ㉛): constraint/flow 是独立信息行 (业务约束/
        # 流转形态), 无前置态概念, 允许 state 为空; state/event/branch 必须携带前置态。
        nav_keywords = ("导航", "点击", "进入页面", "打开")
        _state_required = ("state", "event", "branch", "rule", "rule_noise", "restatement")
        for i, g in enumerate(self.givens):
            if g.given_type in _state_required and not g.state:
                raise ValueError(
                    f"Procedure {self.temp_id}: Given[{i}].state is empty "
                    f"(Given must describe a business state, not an action)"
                )
            if any(kw in g.description for kw in nav_keywords) and not g.state:
                raise ValueError(
                    f"Procedure {self.temp_id}: Given[{i}] looks like a UI "
                    f"navigation hint — move it to operation_hints"
                )

        return self


# ── S2 Models ────────────────────────────────────────────────────────────


class S2Fields(BaseModel):
    """Sorting / ordering fields populated by S2."""

    phase: int
    phase_name: str
    phase_basis: str
    phase_basis_debug: bool = False  # fallback/内部推导依据,渲染层应省略
    topology_level: int
    sort_key: list
    operation_lifecycle: int
    chain_depth: int
    type_label: str
    type_priority: int
    dimension_priority: int
    context: Optional[str] = None

    @field_validator("phase")
    @classmethod
    def _phase_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"phase must be >= 0, got {v}")
        return v

    @field_validator("type_priority")
    @classmethod
    def _type_priority_range(cls, v: int) -> int:
        if not (0 <= v <= 9):
            raise ValueError(f"type_priority must be in [0, 9], got {v}")
        return v

    @field_validator("dimension_priority")
    @classmethod
    def _dimension_priority_range(cls, v: int) -> int:
        if not (0 <= v <= 1):
            raise ValueError(f"dimension_priority must be 0 or 1, got {v}")
        return v


# ── S3 Models ────────────────────────────────────────────────────────────


class S3Fields(BaseModel):
    """Dependency fields populated by S3."""

    dependencies: list[str] = Field(default_factory=list)
    weak_dependencies: list[str] = Field(default_factory=list)


# ── S4 Models ────────────────────────────────────────────────────────────


class S4Fields(BaseModel):
    """Multi-instance fields populated by S4."""

    multi_instance: bool = False
    multi_count: int = 1
    multi_reason: str = ""

    @field_validator("multi_count")
    @classmethod
    def _multi_count_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"multi_count must be >= 1, got {v}")
        return v


# ── Validation helpers ───────────────────────────────────────────────────


def validate_engine_state(state_dict: dict) -> EngineState:
    """Validate a raw dict as an EngineState and return the parsed model.

    Raises ``pydantic.ValidationError`` on any invariant violation.
    """
    return EngineState.model_validate(state_dict)


def validate_procedure(proc_dict: dict) -> Procedure:
    """Validate a raw dict as a Procedure and return the parsed model.

    Raises ``pydantic.ValidationError`` on any invariant violation.
    """
    return Procedure.model_validate(proc_dict)


def validate_procedures(
    procedures: list[dict],
) -> tuple[list[Procedure], list[str]]:
    """Validate a list of raw procedure dicts.

    Returns
    -------
    (valid, errors)
        *valid* — list of successfully parsed ``Procedure`` models.
        *errors* — list of human-readable error strings for each failure.
    """
    valid: list[Procedure] = []
    errors: list[str] = []

    for idx, raw in enumerate(procedures):
        try:
            valid.append(Procedure.model_validate(raw))
        except Exception as exc:
            proc_id = raw.get("temp_id", f"<index {idx}>")
            errors.append(f"Procedure {proc_id}: {exc}")

    return valid, errors