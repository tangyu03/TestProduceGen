"""
Schema — Pydantic models for strong validation (invariant guards) in the
P3 Agent Engine.

Every stage transition (S0 → S1 → S2 → S3 → S4) should validate its output
against the corresponding model before writing into the global state pool.
This guarantees that downstream nodes always receive well-shaped data and
makes invariant violations fail fast with a clear error message.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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
        # Every phase index referenced in state_to_phase must be in range
        for state, phase_idx in self.state_to_phase.items():
            if not isinstance(phase_idx, int) or phase_idx < 0 or phase_idx >= self.phase_count:
                raise ValueError(
                    f"state_to_phase['{state}'] = {phase_idx} is out of range "
                    f"[0, {self.phase_count})"
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
    virtual_entities: dict = {}
    transition_upstream_map: dict

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
        return self


# ── S1 Models ────────────────────────────────────────────────────────────


class ProcedureStep(BaseModel):
    """A single step within a procedure (Action / Verify / Setup)."""

    aaa: Literal["A", "V", "S"]
    location: str
    input: str
    expected: str


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
    """A fully-enriched test procedure with S2/S3/S4 fields attached."""

    temp_id: str
    source_ids: list[str]
    entity: str
    dimension: Optional[str] = None
    obligation_type: int
    risk_trait: str
    steps: list[ProcedureStep]
    gen_seq: int
    post_state: str
    cascade_chain: Optional[str] = None
    embedded_brs: list = Field(default_factory=list, alias="embedded_brs")

    # Stage-attached fields (populated progressively)
    # Field names avoid leading underscores (Pydantic v2 restriction);
    # ``alias`` preserves the ``_S2_fields`` key used in the JSON/dict
    # representation so that round-tripping works transparently.
    S2_fields: "S2Fields" = Field(alias="_S2_fields")
    S3_fields: "S3Fields" = Field(alias="_S3_fields")
    S4_fields: "S4Fields" = Field(alias="_S4_fields")

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _check_step_invariants(self) -> "Procedure":
        aaa_list = [s.aaa for s in self.steps]
        has_action = "A" in aaa_list
        has_verify = "V" in aaa_list

        if not has_action:
            raise ValueError(
                f"Procedure {self.temp_id}: must contain at least one Action (A) step"
            )
        if not has_verify:
            raise ValueError(
                f"Procedure {self.temp_id}: must contain at least one Verify (V) step"
            )
        # A must come before the first V
        first_a = aaa_list.index("A")
        first_v = aaa_list.index("V")
        if first_v < first_a:
            raise ValueError(
                f"Procedure {self.temp_id}: first Action (A) at index {first_a} "
                f"must precede first Verify (V) at index {first_v}"
            )
        return self


# ── S2 Models ────────────────────────────────────────────────────────────


class S2Fields(BaseModel):
    """Sorting / ordering fields populated by S2."""

    phase: int
    phase_name: str
    phase_basis: str
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
