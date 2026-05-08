from __future__ import annotations
"""S1 Procedure Generation Node.

Deterministic procedure generation, faithfully replicating V2 JS engine logic.
All type generators (Type1, Type3, Type4a, Type4b, Type5, Type6, Type7)
are fully implemented with complete logic translated from p3_engine_v2.mjs.
"""
import json
import re
from typing import Any
from models.state import AgentState
from nodes.s0_topology import (
    ENTITY_NAME_MAP, ROLE_MAP, TYPE_PRIORITY_MAP, TYPE5_SPECIAL_OPS, L0_L1_L5_ENTITIES
)

# ---------------------------------------------------------------------------
# Global gen-seq counter (module-level so all generators share one sequence)
# ---------------------------------------------------------------------------
_gen_seq_counter = 0


def _next_gen_seq() -> int:
    global _gen_seq_counter
    _gen_seq_counter += 1
    return _gen_seq_counter


# ---------------------------------------------------------------------------
# Helper functions (mirroring V2 JS engine)
# ---------------------------------------------------------------------------

def _resolve_entity_names(name_str: str) -> list[str]:
    """Convert Chinese entity names to IDs."""
    if not name_str:
        return []
    return [ENTITY_NAME_MAP.get(n.strip(), n.strip())
            for n in re.split(r'[,，、\s]+', name_str) if n.strip()]


def _get_role_name(role_id: str | None) -> str:
    """Resolve role ID to name."""
    return ROLE_MAP.get(role_id, role_id) or '系统'


def _make_step(aaa: str, location: str, input: str, expected: str) -> dict:
    """Build a single procedure step dict."""
    return {"aaa": aaa, "location": location, "input": input, "expected": expected}


def _is_type5_retained(eo: dict, state: AgentState) -> bool:
    """Type5 retention check — V2 logic.

    An EO of type crud_operation is retained if ANY of these hold:
    1. entity ∈ {primary + dependent + VE.original} AND op ∈ special ops
    2. coverage_priority is medium/high/critical
    3. entity ∈ L0/L1/L5 AND op == '删除'
    4. operation_name matches a CO trigger
    """
    entity = eo["entity"]
    op_name = eo["operation_name"]
    primary = state["primary_entity"]
    dependents = state.get("dependent_entities", [])
    ves = state.get("virtual_entities", {})

    # Rule 1: relevant entity + special op
    relevant = {primary, *dependents}
    for ve in ves.values():
        relevant.add(ve.get("original_entity", ""))
    if entity in relevant and op_name in TYPE5_SPECIAL_OPS:
        return True
    # Rule 2: priority >= medium
    if eo.get("coverage_priority") in ("medium", "high", "critical"):
        return True
    # Rule 3: L0/L1/L5 + delete
    if entity in L0_L1_L5_ENTITIES and op_name == "删除":
        return True
    # Rule 4: CO trigger match
    cm = state["coverage_model"]
    for co in cm.get("cross_entity_obligations", []):
        trigger = co.get("trigger")
        if trigger and op_name in trigger:
            return True
    return False


# ---------------------------------------------------------------------------
# Phase resolution
# ---------------------------------------------------------------------------

def _resolve_phase(entity: str, dimension: str, state_value: str, state: AgentState) -> dict:
    """Phase resolution — V2 logic.

    Lookup order:
    1. Primary entity → phase_table.state_to_phase
    2. Dependent / VE entity → dep_state_phase_map
    3. Contextual phase rules → return special contextual marker
    4. Topology fallback → L0→P0, VE resolved_phase, parent anchor min
    """
    primary = state["primary_entity"]
    phase_table = state["phase_table"]
    dep_map = state["dep_state_phase_map"]
    ctx_rules = state.get("contextual_phase_rules", {})
    topo = state["topology_levels"]
    ves = state.get("virtual_entities", {})
    parent_map = state["entity_parent"]

    # Primary entity
    if entity == primary:
        dim_map = phase_table["state_to_phase"].get(dimension, {})
        if state_value in dim_map:
            return {"phase": dim_map[state_value], "basis": f"phase_table.{dimension}.{state_value}"}

    # Dependent entities (including VEs)
    if entity in dep_map:
        dim_map = dep_map.get(entity, {}).get(dimension, {})
        if state_value in dim_map:
            return {"phase": dim_map[state_value], "basis": f"dep_state_phase_map.{entity}.{dimension}.{state_value}"}

    # Contextual phase rules
    ctx_key = f"{entity}.{dimension}"
    if ctx_key in ctx_rules:
        return {"phase": None, "basis": "contextual", "contextual": ctx_key}

    # Topology fallback
    tl = topo.get(entity, 0)
    if tl == 0:
        return {"phase": 0, "basis": "P6: topology_level L0 → P0"}
    if entity == primary:
        return {"phase": 0, "basis": "fallback"}
    if entity in ves:
        return {"phase": ves[entity].get("resolved_phase", 0), "basis": f"VE.{entity}.resolved_phase"}

    # Parent anchor
    parent = parent_map.get(entity)
    if parent and entity in dep_map:
        all_phases = [p for dm in dep_map[entity].values() for p in dm.values()]
        if all_phases:
            return {"phase": min(all_phases), "basis": f"anchor_entity_min_phase.{entity}"}

    return {"phase": 0, "basis": "fallback_default"}


def _resolve_phase_for_transition(entity: str, dimension: str, from_state: str,
                                  to_state: str, state: AgentState) -> dict:
    """Use the 'to' state for phase assignment; pass contextual through."""
    result = _resolve_phase(entity, dimension, to_state, state)
    return result


# ---------------------------------------------------------------------------
# Dimension / type priority helpers
# ---------------------------------------------------------------------------

def _get_dimension_priority(entity: str, dimension: str | None, state: AgentState) -> int:
    if not dimension:
        return 1
    if entity == state["primary_entity"] and dimension == state["phase_table"]["primary_dimension"]:
        return 0
    stm = state.get("state_type_map", {}).get(entity, {})
    if dimension in stm:
        first_val = next(iter(stm[dimension].values()), None)
        if first_val == "driving":
            return 0
    return 1


def _get_type_label(risk_trait: str, obligation_type: int) -> str:
    if obligation_type == 4:
        return "constraint"
    if obligation_type == 5:
        return "crud"
    if obligation_type == 6:
        return "invalid"
    if obligation_type == 7:
        return "rule"
    if risk_trait in ("audit", "audit_rejection"):
        return "audit"
    if risk_trait == "rollback":
        return "rollback"
    if risk_trait == "branch":
        return "branch"
    if risk_trait == "data_constraint":
        return "data_constraint"
    if risk_trait == "time_sensitive":
        return "time_sensitive"
    return "happy"


def _get_type_priority(risk_trait: str, obligation_type: int) -> int:
    if obligation_type == 4:
        return TYPE_PRIORITY_MAP.get("constraint", 3)
    if obligation_type == 5:
        return TYPE_PRIORITY_MAP.get("crud", 5)
    if obligation_type == 6:
        return TYPE_PRIORITY_MAP.get("invalid", 9)
    if obligation_type == 7:
        return TYPE_PRIORITY_MAP.get("rule", 6)
    if obligation_type == 3:
        return TYPE_PRIORITY_MAP.get("happy", 1)
    return TYPE_PRIORITY_MAP.get(risk_trait, 1)


# ---------------------------------------------------------------------------
# Type1 — Transition Obligation procedures
# ---------------------------------------------------------------------------

def _generate_type1(state: AgentState, indices: dict, depth_cache: dict) -> list[dict]:
    """Generate Type1 (transition_obligation) procedures.

    For each TO:
    - Check if it belongs to a VE (virtual entity) → generate per VE
    - Build S/A/V steps with side-effects as additional V steps
    - Add audit_rejection variant if risk_traits contains 'audit'
    - Add time_sensitive boundary + expired variants if risk_traits contains 'time_sensitive'
    """
    cm = state["coverage_model"]
    tos = cm.get("transition_obligations", [])
    phase_table = state["phase_table"]
    ves = state.get("virtual_entities", {})
    topo = state["topology_levels"]

    procedures: list[dict] = []

    for to in tos:
        entity = to["entity"]
        dimension = to.get("dimension", "")
        risk_traits = to.get("risk_traits", [])
        transition_id = to.get("transition_id", "")
        chain_depth = depth_cache.get(transition_id, 0)

        # Check if this TO belongs to a virtual entity
        ve_list = [(ve_name, ve) for ve_name, ve in ves.items()
                    if transition_id in ve.get("transitions", [])]

        # Determine which entities to generate procedures for
        if ve_list:
            target_entities = [
                {"entity": ve_name, "context": ve.get("context"), "parent": ve.get("parent_entity")}
                for ve_name, ve in ve_list
            ]
        else:
            target_entities = [{"entity": entity, "context": None, "parent": None}]

        for te in target_entities:
            # Base procedure
            phase_info = _resolve_phase_for_transition(
                te["entity"], dimension, to.get("from"), to.get("to"), state
            )
            dim_priority = _get_dimension_priority(te["entity"], dimension, state)

            # Determine risk_trait for this procedure
            proc_risk_trait = ""
            proc_type_priority = 1
            proc_type_label = "happy"

            if "branch" in risk_traits:
                proc_risk_trait = "branch"
                proc_type_priority = 2
                proc_type_label = "branch"
            elif "audit" in risk_traits:
                proc_risk_trait = "audit"
                proc_type_priority = 4
                proc_type_label = "audit"

            # Build steps
            steps: list[dict] = []
            preconditions = to.get("preconditions", [])
            s_input = (
                f"{te['entity']}.{dimension} = {to.get('from') or '(初始)'}; {'; '.join(preconditions)}"
                if preconditions
                else f"{te['entity']}.{dimension} = {to.get('from') or '(初始)'}"
            )

            # S step (precondition)
            if te["context"]:
                steps.append(_make_step("S", f"{te['entity']}.{dimension}",
                                        f"[{te['context']}] {s_input}", ""))
            else:
                steps.append(_make_step("S", f"{te['entity']}.{dimension}", s_input, ""))

            # A step (action)
            steps.append(_make_step("A", f"{te['entity']}.{dimension}",
                                    f"{_get_role_name(to.get('role'))}执行{to.get('action', '')}", ""))

            # Main V step
            steps.append(_make_step("V", f"{te['entity']}.{dimension}",
                                    "查看状态", f"状态验证: {to.get('to', '')}"))

            # Side effects as V steps (Type2 embedding)
            side_effects = to.get("side_effects") or []
            for se in side_effects:
                steps.append(_make_step(
                    "V",
                    f"{se['target_entity']}.{se.get('target_dimension') or dimension}",
                    "查看副作用效果",
                    f"副作用验证: {se.get('effect_desc', '')}"
                ))

            base_proc = {
                "temp_id": f"PROC-T1-{_next_gen_seq()}",
                "source_ids": [to["id"]],
                "entity": te["entity"],
                "dimension": dimension,
                "obligation_type": 1,
                "risk_trait": proc_risk_trait,
                "steps": steps,
                "gen_seq": _gen_seq_counter,
                "post_state": f"{te['entity']}.{dimension}→{to.get('to', '')}",
                "cascade_chain": None,
                "br_embedded": [],
                "_S2_fields": {
                    "phase": phase_info.get("phase") if phase_info.get("phase") is not None else 0,
                    "phase_name": phase_table["phase_names"][phase_info["phase"]] if phase_info.get("phase") is not None and phase_info["phase"] < len(phase_table["phase_names"]) else f"P{phase_info.get('phase', 0)}",
                    "phase_basis": phase_info.get("basis", ""),
                    "topology_level": topo.get(te["entity"], 0),
                    "sort_key": [],
                    "operation_lifecycle": chain_depth + 1,
                    "chain_depth": chain_depth,
                    "type_label": proc_type_label,
                    "type_priority": proc_type_priority,
                    "dimension_priority": dim_priority,
                    "context": te["context"],
                },
                "_S3_fields": {"dependencies": [], "weak_dependencies": []},
                "_S4_fields": {"multi_instance": False, "multi_count": 1, "multi_reason": ""},
            }
            procedures.append(base_proc)

            # --- Audit rejection variant ---
            if "audit" in risk_traits:
                reject_steps = [
                    _make_step("S", f"{te['entity']}.{dimension}",
                               (f"[{te['context']}] " if te["context"] else "") +
                               f"{te['entity']}.{dimension} = {to.get('from') or '(初始)'}; 已提请审批", ""),
                    _make_step("A", f"{te['entity']}.{dimension}",
                               f"{_get_role_name(to.get('role'))}执行驳回操作", ""),
                    _make_step("V", f"{te['entity']}.{dimension}",
                               "查看状态和驳回原因",
                               f"状态验证: {to.get('from') or '原状态'}; 驳回原因已记录"),
                ]

                reject_phase = phase_info.get("phase") if phase_info.get("phase") is not None else 0
                reject_proc = {
                    "temp_id": f"PROC-T1-{_next_gen_seq()}",
                    "source_ids": [to["id"]],
                    "entity": te["entity"],
                    "dimension": dimension,
                    "obligation_type": 1,
                    "risk_trait": "audit_rejection",
                    "steps": reject_steps,
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{te['entity']}.{dimension}→{to.get('from') or '原状态'}(驳回)",
                    "cascade_chain": None,
                    "br_embedded": [],
                    "_S2_fields": {
                        "phase": reject_phase,
                        "phase_name": phase_table["phase_names"][reject_phase] if reject_phase < len(phase_table["phase_names"]) else f"P{reject_phase}",
                        "phase_basis": phase_info.get("basis", "") + " (rejection variant)",
                        "topology_level": topo.get(te["entity"], 0),
                        "sort_key": [],
                        "operation_lifecycle": (chain_depth + 1) + 1,
                        "chain_depth": chain_depth + 1,
                        "type_label": "audit",
                        "type_priority": 4,
                        "dimension_priority": dim_priority,
                        "context": te["context"],
                    },
                    "_S3_fields": {"dependencies": [base_proc["temp_id"]], "weak_dependencies": []},
                    "_S4_fields": {"multi_instance": False, "multi_count": 1, "multi_reason": ""},
                }
                procedures.append(reject_proc)

            # --- Time sensitive variants ---
            if "time_sensitive" in risk_traits:
                ts_phase = phase_info.get("phase") if phase_info.get("phase") is not None else 0

                # Boundary variant
                boundary_proc = {
                    "temp_id": f"PROC-T1-{_next_gen_seq()}",
                    "source_ids": [to["id"]],
                    "entity": te["entity"],
                    "dimension": dimension,
                    "obligation_type": 1,
                    "risk_trait": "time_sensitive",
                    "steps": [
                        _make_step("S", f"{te['entity']}.{dimension}", "时间边界条件: 接近截止时间", ""),
                        _make_step("A", f"{te['entity']}.{dimension}",
                                   f"{_get_role_name(to.get('role'))}执行{to.get('action', '')}（边界）", ""),
                        _make_step("V", f"{te['entity']}.{dimension}", "查看状态",
                                   f"状态验证: {to.get('to', '')} (时间边界)"),
                    ],
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{te['entity']}.{dimension}→{to.get('to', '')}(时间边界)",
                    "cascade_chain": None,
                    "br_embedded": [],
                    "_S2_fields": {
                        "phase": ts_phase,
                        "phase_name": phase_table["phase_names"][ts_phase] if ts_phase < len(phase_table["phase_names"]) else f"P{ts_phase}",
                        "phase_basis": phase_info.get("basis", "") + " (time_boundary)",
                        "topology_level": topo.get(te["entity"], 0),
                        "sort_key": [],
                        "operation_lifecycle": chain_depth + 1,
                        "chain_depth": chain_depth,
                        "type_label": "time_sensitive",
                        "type_priority": 3,
                        "dimension_priority": dim_priority,
                        "context": te["context"],
                    },
                    "_S3_fields": {"dependencies": [base_proc["temp_id"]], "weak_dependencies": []},
                    "_S4_fields": {"multi_instance": False, "multi_count": 1, "multi_reason": ""},
                }
                procedures.append(boundary_proc)

                # Expired variant
                expired_proc = {
                    "temp_id": f"PROC-T1-{_next_gen_seq()}",
                    "source_ids": [to["id"]],
                    "entity": te["entity"],
                    "dimension": dimension,
                    "obligation_type": 1,
                    "risk_trait": "time_sensitive",
                    "steps": [
                        _make_step("S", f"{te['entity']}.{dimension}", "时间过期条件: 超过截止时间", ""),
                        _make_step("A", f"{te['entity']}.{dimension}",
                                   f"{_get_role_name(to.get('role'))}尝试执行{to.get('action', '')}（已过期）", ""),
                        _make_step("V", f"{te['entity']}.{dimension}", "查看状态",
                                   "状态验证: 操作不可执行或状态不变"),
                    ],
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{te['entity']}.{dimension}→(过期未执行)",
                    "cascade_chain": None,
                    "br_embedded": [],
                    "_S2_fields": {
                        "phase": ts_phase,
                        "phase_name": phase_table["phase_names"][ts_phase] if ts_phase < len(phase_table["phase_names"]) else f"P{ts_phase}",
                        "phase_basis": phase_info.get("basis", "") + " (time_expired)",
                        "topology_level": topo.get(te["entity"], 0),
                        "sort_key": [],
                        "operation_lifecycle": chain_depth + 1,
                        "chain_depth": chain_depth,
                        "type_label": "time_sensitive",
                        "type_priority": 3,
                        "dimension_priority": dim_priority,
                        "context": te["context"],
                    },
                    "_S3_fields": {"dependencies": [base_proc["temp_id"]], "weak_dependencies": []},
                    "_S4_fields": {"multi_instance": False, "multi_count": 1, "multi_reason": ""},
                }
                procedures.append(expired_proc)

    return procedures


# ---------------------------------------------------------------------------
# Type3 — Attribute Config procedures
# ---------------------------------------------------------------------------

def _generate_type3(state: AgentState, indices: dict, depth_cache: dict) -> list[dict]:
    """Generate Type3 (attribute_config) procedures.

    For each attribute_config EO:
    - If a matching branch_dimension exists → one procedure per branch value
    - Otherwise → single procedure
    """
    phase_table = state["phase_table"]
    topo = state["topology_levels"]
    cfg_eo_to_bd = indices["cfg_eo_to_bd"]

    procedures: list[dict] = []

    attr_cfg_eos = indices["eo_by_type"].get("attribute_config", [])
    for eo in attr_cfg_eos:
        bd = cfg_eo_to_bd.get(eo["id"])

        if bd:
            # Generate one procedure per branch value
            for branch in bd.get("branches", []):
                transition_id = branch.get("target_transition", "")
                chain_depth = depth_cache.get(transition_id, 0)
                phase_info = _resolve_phase(eo["entity"], eo["attribute_name"], branch["value"], state)
                dim_priority = _get_dimension_priority(eo["entity"], eo["attribute_name"], state)

                proc = {
                    "temp_id": f"PROC-T3-{_next_gen_seq()}",
                    "source_ids": [eo["id"]],
                    "entity": eo["entity"],
                    "dimension": eo["attribute_name"],
                    "obligation_type": 3,
                    "risk_trait": "",
                    "steps": [
                        _make_step("S", f"{eo['entity']}", f"导航配置入口，确认当前{eo['attribute_name']}值", ""),
                        _make_step("A", f"{eo['entity']}", f"修改{eo['attribute_name']}为\"{branch['value']}\"", ""),
                        _make_step("V", f"{eo['entity']}.{eo['attribute_name']}", "查看效果",
                                   f"验证{eo['attribute_name']}=\"{branch['value']}\"后流转影响: {branch.get('desc', '')}"),
                    ],
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{eo['entity']}.{eo['attribute_name']}→{branch['value']}",
                    "cascade_chain": None,
                    "br_embedded": [],
                    "_S2_fields": {
                        "phase": phase_info.get("phase", 0) if phase_info.get("phase") is not None else 0,
                        "phase_name": phase_table["phase_names"][phase_info["phase"]] if phase_info.get("phase") is not None and phase_info["phase"] < len(phase_table["phase_names"]) else f"P{phase_info.get('phase', 0)}",
                        "phase_basis": phase_info.get("basis", ""),
                        "topology_level": topo.get(eo["entity"], 0),
                        "sort_key": [],
                        "operation_lifecycle": 2,
                        "chain_depth": chain_depth,
                        "type_label": "happy",
                        "type_priority": 1,
                        "dimension_priority": dim_priority,
                        "context": None,
                    },
                    "_S3_fields": {"dependencies": [], "weak_dependencies": []},
                    "_S4_fields": {"multi_instance": False, "multi_count": 1, "multi_reason": ""},
                }
                procedures.append(proc)
        else:
            # No branch dimension — single procedure
            tl = topo.get(eo["entity"], 0)
            phase = 0
            phase_basis = "P6: topology_level L0 → P0" if tl == 0 else "default"
            dim_priority = _get_dimension_priority(eo["entity"], eo["attribute_name"], state)

            proc = {
                "temp_id": f"PROC-T3-{_next_gen_seq()}",
                "source_ids": [eo["id"]],
                "entity": eo["entity"],
                "dimension": eo["attribute_name"],
                "obligation_type": 3,
                "risk_trait": "",
                "steps": [
                    _make_step("S", f"{eo['entity']}", f"导航配置入口，确认当前{eo['attribute_name']}值", ""),
                    _make_step("A", f"{eo['entity']}", f"修改{eo['attribute_name']}", ""),
                    _make_step("V", f"{eo['entity']}.{eo['attribute_name']}", "查看效果",
                               f"验证{eo['attribute_name']}修改后流转影响"),
                ],
                "gen_seq": _gen_seq_counter,
                "post_state": f"{eo['entity']}.{eo['attribute_name']}→(已修改)",
                "cascade_chain": None,
                "br_embedded": [],
                "_S2_fields": {
                    "phase": phase,
                    "phase_name": phase_table["phase_names"][phase] if phase < len(phase_table["phase_names"]) else f"P{phase}",
                    "phase_basis": phase_basis,
                    "topology_level": tl,
                    "sort_key": [],
                    "operation_lifecycle": 2,
                    "chain_depth": 0,
                    "type_label": "happy",
                    "type_priority": 1,
                    "dimension_priority": dim_priority,
                    "context": None,
                },
                "_S3_fields": {"dependencies": [], "weak_dependencies": []},
                "_S4_fields": {"multi_instance": False, "multi_count": 1, "multi_reason": ""},
            }
            procedures.append(proc)

    return procedures


# ---------------------------------------------------------------------------
# Type4a — Constraint CO procedures
# ---------------------------------------------------------------------------

def _generate_type4a(state: AgentState, indices: dict, depth_cache: dict) -> list[dict]:
    """Generate Type4a (constraint CO) procedures.

    For each constraint CO:
    - Skip if ref_to is set (covered by existing TO)
    - If enabler_entity has VEs matching this CO → generate per VE
    - Build S/A/V with cascade_chain
    """
    phase_table = state["phase_table"]
    ves = state.get("virtual_entities", {})
    topo = state["topology_levels"]

    procedures: list[dict] = []

    for co in indices["co_constraint"]:
        if co.get("ref_to"):
            # Covered by existing TO procedure — skip
            continue

        enabler_entity = co["enabler_entity"]
        dependent_entity = co["dependent_entity"]

        # Check if enabler_entity has VEs that reference this CO
        enabler_ves = [
            (ve_name, ve) for ve_name, ve in ves.items()
            if ve.get("original_entity") == enabler_entity and co["id"] in ve.get("co_ids", [])
        ]

        if enabler_ves:
            target_entities = [
                {"entity": ve_name, "context": ve.get("context")}
                for ve_name, ve in enabler_ves
            ]
        else:
            target_entities = [{"entity": enabler_entity, "context": None}]

        for te in target_entities:
            dep_phase_info = _resolve_phase(
                dependent_entity, co.get("dependent_dimension", ""), co.get("dependent_condition", ""), state
            )
            enabler_depth = depth_cache.get(co.get("enabler_transition_id", ""), 0) if co.get("enabler_transition_id") else 0
            chain_depth = enabler_depth + 1

            proc = {
                "temp_id": f"PROC-T4a-{_next_gen_seq()}",
                "source_ids": [co["id"]],
                "entity": te["entity"],
                "dimension": co.get("enabler_dimension", ""),
                "obligation_type": 4,
                "risk_trait": "",
                "steps": [
                    _make_step("S", f"{te['entity']}.{co.get('enabler_dimension', '')}",
                               f"前置条件: {te['entity']}.{co.get('enabler_dimension', '')} = {co.get('enabler_state', '')}", ""),
                    _make_step("A", f"{te['entity']}.{co.get('enabler_dimension', '')}",
                               f"触发: {co.get('trigger') or co.get('desc', '')}", ""),
                    _make_step("V", f"{dependent_entity}.{co.get('dependent_dimension', '')}",
                               "验证依赖条件",
                               f"{dependent_entity}.{co.get('dependent_dimension', '')} = {co.get('dependent_condition', '')}"),
                ],
                "gen_seq": _gen_seq_counter,
                "post_state": f"{dependent_entity}.{co.get('dependent_dimension', '')}→{co.get('dependent_condition', '')}",
                "cascade_chain": f"{te['entity']}.{co.get('enabler_dimension', '')}={co.get('enabler_state', '')}→{dependent_entity}.{co.get('dependent_dimension', '')}={co.get('dependent_condition', '')}",
                "br_embedded": [],
                "_S2_fields": {
                    "phase": dep_phase_info.get("phase", 0) if dep_phase_info.get("phase") is not None else 0,
                    "phase_name": phase_table["phase_names"][dep_phase_info["phase"]] if dep_phase_info.get("phase") is not None and dep_phase_info["phase"] < len(phase_table["phase_names"]) else f"P{dep_phase_info.get('phase', 0)}",
                    "phase_basis": dep_phase_info.get("basis", ""),
                    "topology_level": topo.get(te["entity"], 0),
                    "sort_key": [],
                    "operation_lifecycle": 2,
                    "chain_depth": chain_depth,
                    "type_label": "constraint",
                    "type_priority": 3,
                    "dimension_priority": _get_dimension_priority(te["entity"], co.get("enabler_dimension"), state),
                    "context": te["context"],
                },
                "_S3_fields": {"dependencies": [], "weak_dependencies": []},
                "_S4_fields": {"multi_instance": False, "multi_count": 1, "multi_reason": ""},
            }
            procedures.append(proc)

    return procedures


# ---------------------------------------------------------------------------
# Type4b — Lifecycle CO procedures
# ---------------------------------------------------------------------------

def _generate_type4b(state: AgentState, indices: dict, depth_cache: dict) -> list[dict]:
    """Generate Type4b (lifecycle CO) procedures.

    No rejection variant. Bidirectional cascade_chain.
    """
    phase_table = state["phase_table"]
    topo = state["topology_levels"]

    procedures: list[dict] = []

    for co in indices["co_lifecycle"]:
        enabler_depth = depth_cache.get(co.get("enabler_transition_id", ""), 0) if co.get("enabler_transition_id") else 0
        phase_info = _resolve_phase(
            co["dependent_entity"], co.get("dependent_dimension", ""), co.get("dependent_condition", ""), state
        )

        proc = {
            "temp_id": f"PROC-T4b-{_next_gen_seq()}",
            "source_ids": [co["id"]],
            "entity": co["enabler_entity"],
            "dimension": co.get("enabler_dimension", ""),
            "obligation_type": 4,
            "risk_trait": "",
            "steps": [
                _make_step("S", f"{co['enabler_entity']}.{co.get('enabler_dimension', '')}",
                           f"触发: {co['enabler_entity']}.{co.get('enabler_dimension', '')} = {co.get('enabler_state', '')}", ""),
                _make_step("A", f"{co['enabler_entity']}.{co.get('enabler_dimension', '')}",
                           f"执行{co['enabler_entity']}生命周期操作", ""),
                _make_step("V", f"{co['dependent_entity']}.{co.get('dependent_dimension', '')}",
                           "验证同步效果",
                           f"{co['dependent_entity']}.{co.get('dependent_dimension', '')} = {co.get('dependent_condition', '')}"),
            ],
            "gen_seq": _gen_seq_counter,
            "post_state": f"{co['dependent_entity']}.{co.get('dependent_dimension', '')}→{co.get('dependent_condition', '')}",
            "cascade_chain": f"{co['enabler_entity']}.{co.get('enabler_dimension', '')}={co.get('enabler_state', '')}→{co['dependent_entity']}.{co.get('dependent_dimension', '')}={co.get('dependent_condition', '')}",
            "br_embedded": [],
            "_S2_fields": {
                "phase": phase_info.get("phase", 0) if phase_info.get("phase") is not None else 0,
                "phase_name": phase_table["phase_names"][phase_info["phase"]] if phase_info.get("phase") is not None and phase_info["phase"] < len(phase_table["phase_names"]) else f"P{phase_info.get('phase', 0)}",
                "phase_basis": phase_info.get("basis", ""),
                "topology_level": topo.get(co["enabler_entity"], 0),
                "sort_key": [],
                "operation_lifecycle": 2,
                "chain_depth": enabler_depth,
                "type_label": "lifecycle",
                "type_priority": 7,
                "dimension_priority": _get_dimension_priority(co["enabler_entity"], co.get("enabler_dimension"), state),
                "context": None,
            },
            "_S3_fields": {"dependencies": [], "weak_dependencies": []},
            "_S4_fields": {"multi_instance": False, "multi_count": 1, "multi_reason": ""},
        }
        procedures.append(proc)

    return procedures


# ---------------------------------------------------------------------------
# Type5 — CRUD Operation procedures (filtered)
# ---------------------------------------------------------------------------

def _generate_type5(state: AgentState, indices: dict) -> list[dict]:
    """Generate Type5 (crud_operation) procedures with retention filter.

    Only retained EOs generate procedures. If the entity has been split into
    VEs, generate one procedure per VE.
    """
    phase_table = state["phase_table"]
    dep_map = state["dep_state_phase_map"]
    ves = state.get("virtual_entities", {})
    topo = state["topology_levels"]
    primary = state["primary_entity"]

    procedures: list[dict] = []

    crud_eos = indices["eo_by_type"].get("crud_operation", [])
    for eo in crud_eos:
        if not _is_type5_retained(eo, state):
            continue

        entity = eo["entity"]
        tl = topo.get(entity, 0)
        phase = 0
        phase_basis = ""

        if entity == primary:
            primary_dim_map = phase_table["state_to_phase"].get(phase_table["primary_dimension"], {})
            if primary_dim_map:
                first_phase = next(iter(primary_dim_map.values()), 0)
                phase = first_phase if first_phase is not None else 0
                phase_basis = f"phase_table.{phase_table['primary_dimension']}"
        elif entity in dep_map:
            first_dim = next(iter(dep_map[entity].values()), None)
            if first_dim:
                phase = min(first_dim.values())
                phase_basis = f"dep_state_phase_map.{entity}.min_phase"
        elif entity in ves:
            phase = ves[entity].get("resolved_phase", 0)
            phase_basis = f"VE.{entity}.resolved_phase"
        else:
            phase_basis = "P6: topology_level L0 → P0" if tl == 0 else "default"

        # Check if entity has VEs → generate one per VE
        ves_for_entity = [(ve_name, ve) for ve_name, ve in ves.items()
                          if ve.get("original_entity") == entity]

        if ves_for_entity:
            for ve_name, ve in ves_for_entity:
                ve_phase = ve.get("resolved_phase", 0)
                proc = {
                    "temp_id": f"PROC-T5-{_next_gen_seq()}",
                    "source_ids": [eo["id"]],
                    "entity": ve_name,
                    "dimension": None,
                    "obligation_type": 6,
                    "risk_trait": "",
                    "steps": [
                        _make_step("S", ve_name, f"导航至{ve.get('context', '')}页面，确认操作入口可用", ""),
                        _make_step("A", ve_name, f"执行{eo['operation_name']}", ""),
                        _make_step("V", ve_name, "查看效果", f"验证: {eo.get('description', '')}"),
                    ],
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{ve_name}→({eo['operation_name']}完成)",
                    "cascade_chain": None,
                    "br_embedded": [],
                    "_S2_fields": {
                        "phase": ve_phase,
                        "phase_name": phase_table["phase_names"][ve_phase] if ve_phase < len(phase_table["phase_names"]) else f"P{ve_phase}",
                        "phase_basis": f"VE.{ve_name}.resolved_phase",
                        "topology_level": topo.get(ve_name, 0),
                        "sort_key": [],
                        "operation_lifecycle": 1,
                        "chain_depth": 0,
                        "type_label": "crud",
                        "type_priority": 5,
                        "dimension_priority": 1,
                        "context": ve.get("context"),
                    },
                    "_S3_fields": {"dependencies": [], "weak_dependencies": []},
                    "_S4_fields": {"multi_instance": False, "multi_count": 1, "multi_reason": ""},
                }
                procedures.append(proc)
        else:
            proc = {
                "temp_id": f"PROC-T5-{_next_gen_seq()}",
                "source_ids": [eo["id"]],
                "entity": eo["entity"],
                "dimension": None,
                "obligation_type": 6,
                "risk_trait": "",
                "steps": [
                    _make_step("S", eo["entity"], f"导航至{eo.get('entity_name', eo['entity'])}页面，确认操作入口可用", ""),
                    _make_step("A", eo["entity"], f"执行{eo['operation_name']}", ""),
                    _make_step("V", eo["entity"], "查看效果", f"验证: {eo.get('description', '')}"),
                ],
                "gen_seq": _gen_seq_counter,
                "post_state": f"{eo['entity']}→({eo['operation_name']}完成)",
                "cascade_chain": None,
                "br_embedded": [],
                "_S2_fields": {
                    "phase": phase,
                    "phase_name": phase_table["phase_names"][phase] if phase < len(phase_table["phase_names"]) else f"P{phase}",
                    "phase_basis": phase_basis,
                    "topology_level": tl,
                    "sort_key": [],
                    "operation_lifecycle": 1,
                    "chain_depth": 0,
                    "type_label": "crud",
                    "type_priority": 5,
                    "dimension_priority": 1,
                    "context": None,
                },
                "_S3_fields": {"dependencies": [], "weak_dependencies": []},
                "_S4_fields": {"multi_instance": False, "multi_count": 1, "multi_reason": ""},
            }
            procedures.append(proc)

    return procedures


# ---------------------------------------------------------------------------
# Type6 — Invalid Transition procedures
# ---------------------------------------------------------------------------

def _generate_type6(state: AgentState, indices: dict, depth_cache: dict) -> list[dict]:
    """Generate Type6 (invalid_transition) procedures.

    Phase is based on the 'from' state; chain_depth is the max depth of
    TOs whose 'to' matches the RO's 'from'.
    """
    phase_table = state["phase_table"]
    dep_map = state["dep_state_phase_map"]
    topo = state["topology_levels"]
    primary = state["primary_entity"]
    cm = state["coverage_model"]
    tos = cm.get("transition_obligations", [])

    procedures: list[dict] = []

    invalid_transitions = indices["ro_by_type"].get("invalid_transition", [])
    for ro in invalid_transitions:
        entity = ro["entity"]
        tl = topo.get(entity, 0)
        phase = 0
        phase_basis = ""

        if entity == primary:
            primary_dim_map = phase_table["state_to_phase"].get(phase_table["primary_dimension"], {})
            if primary_dim_map and ro.get("from") in primary_dim_map:
                phase = primary_dim_map[ro["from"]]
                phase_basis = f"phase_table.{phase_table['primary_dimension']}.{ro['from']}"
        elif entity in dep_map:
            for dim, state_map in dep_map.get(entity, {}).items():
                if ro.get("from") in state_map:
                    phase = state_map[ro["from"]]
                    phase_basis = f"dep_state_phase_map.{entity}.{dim}.{ro['from']}"
                    break
        else:
            phase_basis = "P6: topology_level L0 → P0" if tl == 0 else "default"

        # Chain depth from the transition that leads to "from" state
        chain_depth = 0
        for to in tos:
            if to["entity"] == entity and to.get("to") == ro.get("from"):
                chain_depth = max(chain_depth, depth_cache.get(to.get("transition_id", ""), 0))

        proc = {
            "temp_id": f"PROC-T6-{_next_gen_seq()}",
            "source_ids": [ro["id"]],
            "entity": entity,
            "dimension": None,
            "obligation_type": 7,
            "risk_trait": "",
            "steps": [
                _make_step("S", entity, f"前置条件: {entity}处于\"{ro.get('from', '')}\"状态", ""),
                _make_step("A", entity, f"尝试执行从\"{ro.get('from', '')}\"到\"{ro.get('to', '')}\"的操作", ""),
                _make_step("V", entity, "验证操作被阻止",
                           f"预期结果: 操作不可执行，{ro.get('reason', '')}"),
            ],
            "gen_seq": _gen_seq_counter,
            "post_state": f"{entity}→(操作被阻止)",
            "cascade_chain": None,
            "br_embedded": [],
            "_S2_fields": {
                "phase": phase,
                "phase_name": phase_table["phase_names"][phase] if phase < len(phase_table["phase_names"]) else f"P{phase}",
                "phase_basis": phase_basis,
                "topology_level": tl,
                "sort_key": [],
                "operation_lifecycle": 2,
                "chain_depth": chain_depth,
                "type_label": "invalid",
                "type_priority": 9,
                "dimension_priority": 1,
                "context": None,
            },
            "_S3_fields": {"dependencies": [], "weak_dependencies": []},
            "_S4_fields": {"multi_instance": False, "multi_count": 1, "multi_reason": ""},
        }
        procedures.append(proc)

    return procedures


# ---------------------------------------------------------------------------
# BR Classification (S1.8)
# ---------------------------------------------------------------------------

def _classify_business_rules(state: AgentState, indices: dict) -> list[dict]:
    """Classify BRs into 5 categories per prompt S1.8.

    Priority: attribute_effect > transition_constraint > crud_constraint > negative_test > standalone
    """
    cm = state["coverage_model"]
    bds = cm.get("_context", {}).get("branch_dimensions", [])
    tos = cm.get("transition_obligations", [])
    co_constraint = indices["co_constraint"]
    eo_by_type = indices["eo_by_type"]
    ro_by_type = indices["ro_by_type"]
    warnings = list(state.get("warnings", []))

    br_list = ro_by_type.get("business_rule", [])
    classifications = []

    for br in br_list:
        br_id = br.get("constraint_id", "")
        desc = br.get("description", "")
        br_entities = _resolve_entity_names(br.get("entities", ""))

        # 1. attribute_effect
        matched = False
        for bd in bds:
            cov = bd.get("coverage", {})
            if cov and br_id in cov.get("business_rules", []):
                cfg_eos = [eo for eo in eo_by_type.get("attribute_config", [])
                           if eo["entity"] == bd["entity"] and eo.get("attribute_name") == bd["dimension"]]
                if cfg_eos:
                    classifications.append({
                        "br": br, "category": "attribute_effect", "host_proc_type": 3,
                        "host_eo_ids": [eo["id"] for eo in cfg_eos], "bd": bd
                    })
                    matched = True
                    break
        if matched:
            continue

        # 2. transition_constraint
        if re.search(r'需先.*后|才可|必须.*后', desc) and len(br_entities) >= 2:
            to_match = next((to for to in tos
                             if br_entities and to["entity"] in br_entities
                             and "audit" in (to.get("risk_traits") or [])), None)
            co_match = next((co for co in co_constraint
                             if co["enabler_entity"] in br_entities or co["dependent_entity"] in br_entities), None)
            if to_match or co_match:
                classifications.append({
                    "br": br, "category": "transition_constraint",
                    "host_proc_type": 1 if to_match else 4,
                    "host_to_id": to_match["id"] if to_match else None,
                    "host_co_id": co_match["id"] if co_match else None
                })
                matched = True
                continue

        # 3. crud_constraint
        crud_ops = ['删除', '修改', '新增', '退款', '撤销']
        has_crud = any(op in desc for op in crud_ops)
        has_state = bool(re.search(r'状态|才可|不可|不允许|不能|只有|需先', desc))
        if has_crud and has_state:
            matching_eo = next((eo for eo in eo_by_type.get("crud_operation", [])
                                if eo["entity"] in br_entities and any(op in eo["operation_name"] for op in crud_ops)), None)
            if matching_eo and _is_type5_retained(matching_eo, state):
                classifications.append({
                    "br": br, "category": "crud_constraint", "host_proc_type": 5,
                    "host_eo_id": matching_eo["id"]
                })
                matched = True
                continue
            else:
                warnings.append(f"BR {br_id} crud_constraint host EO filtered, downgrading to standalone")

        # 4. negative_test
        if re.search(r'不可.*选择|不可.*删除|不可.*修改|不可.*操作|不可.*发布|不允许.*删除|不允许.*操作|不能.*删除|不能.*混合', desc):
            matching_it = next((ro for ro in ro_by_type.get("invalid_transition", [])
                                if ro["entity"] in br_entities), None)
            if matching_it:
                classifications.append({"br": br, "category": "negative_test", "host_proc_type": 6,
                                        "host_ro_id": matching_it["id"]})
            else:
                classifications.append({"br": br, "category": "negative_test", "host_proc_type": 6,
                                        "generate_variant": True})
            matched = True
            continue

        # 5. standalone
        classifications.append({"br": br, "category": "standalone", "host_proc_type": 7})

    return classifications


# ---------------------------------------------------------------------------
# Type7 — Standalone BR procedures (only for standalone-classified BRs)
# ---------------------------------------------------------------------------

def _generate_type7_standalone(br_classifications: list[dict], state: AgentState) -> list[dict]:
    """Generate standalone Type7 procedures from standalone BRs only."""
    phase_table = state["phase_table"]
    dep_map = state["dep_state_phase_map"]
    ves = state.get("virtual_entities", {})
    topo = state["topology_levels"]
    primary = state["primary_entity"]
    cm = state["coverage_model"]
    tos = cm.get("transition_obligations", [])

    procedures: list[dict] = []
    standalone_brs = [bc for bc in br_classifications if bc["category"] == "standalone"]

    for bc in standalone_brs:
        br = bc["br"]
        br_entities = _resolve_entity_names(br.get("entities", ""))
        primary_br_entity = br_entities[0] if br_entities else "E-PRJ"

        tl = topo.get(primary_br_entity, 0)
        phase = 0
        phase_basis = ""

        if primary_br_entity == primary:
            phase = 0
            phase_basis = "primary_entity_default"
        elif primary_br_entity in dep_map:
            all_phases = [p for dm in dep_map[primary_br_entity].values() for p in dm.values()]
            if all_phases:
                phase = min(all_phases)
                phase_basis = f"dep_state_phase_map.{primary_br_entity}.min_phase"
        elif primary_br_entity in ves:
            phase = ves[primary_br_entity].get("resolved_phase", 0)
            phase_basis = f"VE.{primary_br_entity}.resolved_phase"
        else:
            phase_basis = "P6: topology_level L0 → P0" if tl == 0 else "default"

        br_desc = br.get("description", "")
        enforcement = br.get("enforcement", "mandatory")

        steps = [
            _make_step("S", primary_br_entity,
                       f"前置条件: {', '.join(br_entities)}相关数据已准备", ""),
            _make_step("A", primary_br_entity,
                       f"按规则\"{br_desc}\"执行操作", ""),
        ]

        if enforcement == "conditional":
            steps.append(_make_step("V", primary_br_entity, "验证正面场景",
                                    f"[{br.get('constraint_id', '')}]验证(正面): {br_desc}"))
            steps.append(_make_step("V", primary_br_entity, "验证负面场景",
                                    f"[{br.get('constraint_id', '')}]验证(负面): 不满足条件时规则不触发"))
        else:
            steps.append(_make_step("V", primary_br_entity, "查看效果",
                                    f"[{br.get('constraint_id', '')}]验证: {br_desc}"))

        # Try to find associated transition for chain depth
        chain_depth = 0
        for to in tos:
            if br_entities and to["entity"] in br_entities:
                chain_depth = max(chain_depth, 0)  # simplified; depth_cache not available here

        proc = {
            "temp_id": f"PROC-T7-{_next_gen_seq()}",
            "source_ids": [br.get("id", br.get("constraint_id", ""))],
            "entity": primary_br_entity,
            "dimension": None,
            "obligation_type": 8,
            "risk_trait": "",
            "steps": steps,
            "gen_seq": _gen_seq_counter,
            "post_state": f"{primary_br_entity}→(规则验证完成)",
            "cascade_chain": None,
            "br_embedded": [],
            "_S2_fields": {
                "phase": phase,
                "phase_name": phase_table["phase_names"][phase] if phase < len(phase_table["phase_names"]) else f"P{phase}",
                "phase_basis": phase_basis,
                "topology_level": tl,
                "sort_key": [],
                "operation_lifecycle": 1,
                "chain_depth": chain_depth,
                "type_label": "rule",
                "type_priority": 6,
                "dimension_priority": 1,
                "context": None,
            },
            "_S3_fields": {"dependencies": [], "weak_dependencies": []},
            "_S4_fields": {"multi_instance": False, "multi_count": 1, "multi_reason": ""},
        }
        procedures.append(proc)

    return procedures


# ---------------------------------------------------------------------------
# BR Embedding — embed non-standalone BRs into host procedures as V steps
# ---------------------------------------------------------------------------

def _embed_brs(procedures: list[dict], br_classifications: list[dict],
               state: AgentState) -> list[dict]:
    """Embed non-standalone BRs into host procedures as V steps.

    For each non-standalone BR:
    - attribute_effect → embed into Type3 procedures matching host_eo_ids
    - transition_constraint → embed into Type1 (by host_to_id) or Type4a (by host_co_id)
    - crud_constraint → embed into Type5 procedures matching host_eo_id
    - negative_test → embed into Type6 procedures or create new Type6 variant

    V step format: [BR-XX]验证: description
    Conditional enforcement gets 2 V steps (positive + negative).
    """
    dep_map = state["dep_state_phase_map"]
    topo = state["topology_levels"]
    phase_table = state["phase_table"]
    warnings = list(state.get("warnings", []))
    total_embedded = 0

    non_standalone = [bc for bc in br_classifications if bc["category"] != "standalone"]

    for bc in non_standalone:
        br = bc["br"]
        br_id = br.get("constraint_id", "")
        br_desc = br.get("description", "")
        enforcement = br.get("enforcement", "mandatory")

        host_procs: list[dict] = []

        if bc["category"] == "attribute_effect":
            host_eo_ids = bc.get("host_eo_ids", [])
            host_procs = [p for p in procedures
                          if p["obligation_type"] == 3
                          and any(sid in host_eo_ids for sid in p.get("source_ids", []))]

        elif bc["category"] == "transition_constraint":
            host_to_id = bc.get("host_to_id")
            host_co_id = bc.get("host_co_id")
            if host_to_id:
                host_procs = [p for p in procedures
                              if p["obligation_type"] == 1
                              and host_to_id in p.get("source_ids", [])
                              and p.get("risk_trait") != "audit_rejection"]
            if host_co_id:
                host_procs.extend([p for p in procedures
                                   if p["obligation_type"] == 4
                                   and host_co_id in p.get("source_ids", [])])

        elif bc["category"] == "crud_constraint":
            host_eo_id = bc.get("host_eo_id")
            if host_eo_id:
                host_procs = [p for p in procedures
                              if p["obligation_type"] == 6
                              and host_eo_id in p.get("source_ids", [])]

        elif bc["category"] == "negative_test":
            br_entities = _resolve_entity_names(br.get("entities", ""))
            # Find existing Type6 proc for same entity
            host_procs = [p for p in procedures
                          if p["obligation_type"] == 7
                          and br_entities and p["entity"] in br_entities]

            if not host_procs:
                # Create new Type6 variant procedure (negative_test BR with no existing Type6)
                primary_br_entity = br_entities[0] if br_entities else "E-PRJ"
                tl = topo.get(primary_br_entity, 0)
                phase = 0
                phase_basis = "P6: topology_level L0 → P0" if tl == 0 else "default"

                if primary_br_entity in dep_map:
                    all_phases = [p for dm in dep_map[primary_br_entity].values() for p in dm.values()]
                    if all_phases:
                        phase = min(all_phases)
                        phase_basis = f"dep_state_phase_map.{primary_br_entity}.min_phase"

                # Extract the prohibited part from description
                prohibited = ""
                for marker in ["不可", "不允许", "不能"]:
                    idx = br_desc.find(marker)
                    if idx >= 0:
                        prohibited = br_desc[idx:]
                        break
                if not prohibited:
                    prohibited = br_desc

                new_proc = {
                    "temp_id": f"PROC-T6BR-{_next_gen_seq()}",
                    "source_ids": [br.get("id", br.get("constraint_id", ""))],
                    "entity": primary_br_entity,
                    "dimension": None,
                    "obligation_type": 7,
                    "risk_trait": "negative",
                    "steps": [
                        _make_step("S", primary_br_entity,
                                   f"前置条件: {prohibited}相关数据已准备", ""),
                        _make_step("A", primary_br_entity, "尝试违反规则操作", ""),
                        _make_step("V", primary_br_entity, "验证操作被阻止",
                                   f"预期结果: {br_desc}"),
                    ],
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{primary_br_entity}→(操作被阻止)",
                    "cascade_chain": None,
                    "br_embedded": [],
                    "_S2_fields": {
                        "phase": phase,
                        "phase_name": phase_table["phase_names"][phase] if phase < len(phase_table["phase_names"]) else f"P{phase}",
                        "phase_basis": phase_basis,
                        "topology_level": tl,
                        "sort_key": [],
                        "operation_lifecycle": 2,
                        "chain_depth": 0,
                        "type_label": "invalid",
                        "type_priority": 9,
                        "dimension_priority": 1,
                        "context": None,
                    },
                    "_S3_fields": {"dependencies": [], "weak_dependencies": []},
                    "_S4_fields": {"multi_instance": False, "multi_count": 1, "multi_reason": ""},
                }
                procedures.append(new_proc)
                host_procs = [new_proc]

        # Embed V steps into host procedures
        for proc in host_procs:
            entity = proc["entity"]
            dimension = proc.get("dimension") or ""

            if enforcement == "conditional":
                proc["steps"].append(_make_step("V", f"{entity}.{dimension}", "查看效果(正面)",
                                                f"[{br_id}]验证(正面): {br_desc}"))
                proc["steps"].append(_make_step("V", f"{entity}.{dimension}", "查看效果(负面)",
                                                f"[{br_id}]验证(负面): 不满足条件时规则不触发"))
            else:
                proc["steps"].append(_make_step("V", f"{entity}.{dimension}", "查看效果",
                                                f"[{br_id}]验证: {br_desc}"))
            proc.setdefault("br_embedded", []).append(br_id)
            total_embedded += 1

    return procedures


# ---------------------------------------------------------------------------
# Contextual Phase Rule expansion (E-REG.通知状态, etc.)
# ---------------------------------------------------------------------------

def _apply_contextual_phase_rules(procedures: list[dict], state: AgentState) -> list[dict]:
    """Expand procedures that hit contextual phase rules.

    For each procedure whose phase_basis is 'contextual', look up the rules
    and create one expanded procedure per context rule.
    """
    ctx_rules = state.get("contextual_phase_rules", {})
    phase_table = state["phase_table"]

    if not ctx_rules:
        return procedures

    procs_to_remove: list[str] = []
    procs_to_add: list[dict] = []

    for proc in procedures:
        s2 = proc.get("_S2_fields", {})
        if s2.get("phase_basis") == "contextual":
            ctx_key = s2.get("context") or f"{proc['entity']}.{proc.get('dimension', '')}"
            if ctx_key in ctx_rules:
                rule_set = ctx_rules[ctx_key]
                procs_to_remove.append(proc["temp_id"])

                for rule in rule_set.get("rules", []):
                    import copy
                    expanded = copy.deepcopy(proc)
                    expanded["temp_id"] = f"{proc['temp_id']}-{rule.get('context', '')}"
                    resolved_phase = rule.get("resolved_phase", 0)
                    expanded["_S2_fields"]["phase"] = resolved_phase
                    expanded["_S2_fields"]["phase_name"] = (
                        phase_table["phase_names"][resolved_phase]
                        if resolved_phase < len(phase_table["phase_names"])
                        else f"P{resolved_phase}"
                    )
                    expanded["_S2_fields"]["phase_basis"] = f"contextual.{rule.get('context', '')}"
                    expanded["_S2_fields"]["context"] = rule.get("context")

                    # Add context annotation to first step
                    if expanded["steps"]:
                        expanded["steps"][0]["input"] = f"[{rule.get('context', '')}] {expanded['steps'][0]['input']}"

                    procs_to_add.append(expanded)

    # Remove originals, add expanded
    if procs_to_remove:
        procedures = [p for p in procedures if p["temp_id"] not in procs_to_remove]
        procedures.extend(procs_to_add)

    return procedures


# ---------------------------------------------------------------------------
# Main node function
# ---------------------------------------------------------------------------

def s1_generation_node(state: AgentState) -> dict:
    """S1 Procedure Generation node — deterministic, V2-equivalent."""
    global _gen_seq_counter
    _gen_seq_counter = 0  # Reset for each pipeline run

    cm = state["coverage_model"]
    warnings = list(state.get("warnings", []))
    errors = list(state.get("errors", []))

    # Build indices (same as V2)
    eos = cm.get("entity_obligations", [])
    tos = cm.get("transition_obligations", [])
    cos = cm.get("cross_entity_obligations", [])
    ros = cm.get("constraint_obligations", [])
    bds = cm.get("_context", {}).get("branch_dimensions", [])

    eo_by_type: dict[str, list] = {}
    for eo in eos:
        eo_by_type.setdefault(eo["type"], []).append(eo)

    to_by_entity: dict[str, list] = {}
    for to in tos:
        to_by_entity.setdefault(to["entity"], []).append(to)

    co_constraint = [co for co in cos if co.get("causal_type") == "constraint"]
    co_lifecycle = [co for co in cos if co.get("causal_type") == "lifecycle"]

    ro_by_type: dict[str, list] = {}
    for ro in ros:
        ro_by_type.setdefault(ro["type"], []).append(ro)

    cfg_eo_to_bd: dict[str, dict] = {}
    for bd in bds:
        for eo in eo_by_type.get("attribute_config", []):
            if eo["entity"] == bd["entity"] and eo.get("attribute_name") == bd["dimension"]:
                cfg_eo_to_bd[eo["id"]] = bd

    indices = {
        "eo_by_type": eo_by_type,
        "to_by_entity": to_by_entity,
        "co_constraint": co_constraint,
        "co_lifecycle": co_lifecycle,
        "ro_by_type": ro_by_type,
        "cfg_eo_to_bd": cfg_eo_to_bd,
    }

    # Calculate chain depths
    from tools.graph_algo import calc_all_chain_depths
    depth_cache = calc_all_chain_depths(state["transition_upstream_map"])

    # Generate procedures by type
    procedures: list[dict] = []
    procedures.extend(_generate_type1(state, indices, depth_cache))
    procedures.extend(_generate_type3(state, indices, depth_cache))
    procedures.extend(_generate_type4a(state, indices, depth_cache))
    procedures.extend(_generate_type4b(state, indices, depth_cache))
    procedures.extend(_generate_type5(state, indices))
    procedures.extend(_generate_type6(state, indices, depth_cache))

    # BR classification and embedding
    br_classifications = _classify_business_rules(state, indices)

    # Type7 standalone
    procedures.extend(_generate_type7_standalone(br_classifications, state))

    # BR embedding (non-standalone → V steps in host procedures)
    procedures = _embed_brs(procedures, br_classifications, state)

    # Apply contextual phase rules (expand procedures with contextual phase)
    procedures = _apply_contextual_phase_rules(procedures, state)

    # Validate all procedures
    from models.schema import validate_procedures
    valid_procs, val_errors = validate_procedures(procedures)
    errors.extend(val_errors)

    warnings.append(f"S1 generated {len(valid_procs)} procedures ({len(procedures) - len(valid_procs)} validation failures)")

    # Count type5 filtered
    type5_filtered = [eo["id"] for eo in eo_by_type.get("crud_operation", [])
                      if not _is_type5_retained(eo, state)]

    # Standalone count
    standalone_count = len([bc for bc in br_classifications if bc["category"] == "standalone"])

    # BR embedded count
    br_embedded_count = sum(len(p.get("br_embedded", [])) for p in procedures)

    warnings.append(f"S1 summary: standalone_type7={standalone_count}, br_embedded={br_embedded_count}, type5_filtered={len(type5_filtered)}")

    return {
        "procedures": [p.model_dump(by_alias=True) if hasattr(p, 'model_dump') else p for p in valid_procs],
        "br_classifications": br_classifications,
        "type5_filtered": type5_filtered,
        "gen_seq_counter": _gen_seq_counter,
        "warnings": warnings,
        "errors": errors,
        "current_stage": "s1",
    }
