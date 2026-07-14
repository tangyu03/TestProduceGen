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
    _build_entity_name_map, _build_role_map, _build_managed_entities,
    TYPE_PRIORITY_MAP, TYPE5_SPECIAL_OPS,
)
from nodes.field_validation import parse_entity_constraints, enrich_procedure_steps
from nodes.signal_validation import generate_signal_v_steps

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

def _resolve_entity_names(name_str, entity_name_map: dict | None = None) -> list[str]:
    """Convert Chinese entity names or IDs to canonical IDs using dynamic map.

    Accepts either a comma-separated string (old ``entities`` format) or a
    list (new ``entities_involved`` format).
    """
    if not name_str:
        return []
    if entity_name_map is None:
        entity_name_map = {}
    # Normalise to list
    if isinstance(name_str, list):
        items = name_str
    else:
        items = re.split(r'[,，、\s]+', str(name_str))
    return [entity_name_map.get(n.strip(), n.strip())
            for n in items if n.strip()]


def _get_role_name(role_id: str | None, action: str = '', entity: str = '',
                   state: AgentState | None = None) -> str:
    """I21: Resolve role with LLM-classified human-decision fallback chain.

    Replaces the legacy HUMAN_DECISION_KEYWORDS hardcoded list with an
    LLM-based action classification (cached in ``state['action_classification']``).
    The classification is performed once at S1 start by
    ``_classify_actions_via_llm`` and stored as ``{action_text: "human"|"system"}``.
    """
    # Build role_map dynamically from coverage_model._context
    role_map = _build_role_map(state.get('coverage_model', {})) if state else {}
    base = role_map.get(role_id, role_id) or '系统'

    if role_id and role_id != 'system' and base != '系统':
        return base

    # BDD: LLM-based action classification (replaces HUMAN_DECISION_KEYWORDS)
    # Read from state['action_classification'] — a dict {action_text: "human"|"system"}
    # populated once at S1 start by _classify_actions_via_llm.
    action_cls = state.get('action_classification', {}) if state else {}
    action_type = action_cls.get(action, '')
    has_human_kw = action_type == 'human'
    has_auto_kw = action_type == 'system'

    def _role_lookup(roles_data, key: str) -> str | None:
        """Look up role by entity key, handling both list and dict formats."""
        if isinstance(roles_data, dict):
            return roles_data.get(key)
        if isinstance(roles_data, list):
            for item in roles_data:
                if isinstance(item, dict):
                    if item.get('entity') == key or item.get('id') == key:
                        return item.get('role') or item.get('name') or item.get(key)
            for item in roles_data:
                if isinstance(item, dict) and key in item:
                    return item[key]
        return None

    if has_human_kw:
        if state:
            ep = state.get('entity_parent', {})
            parent = ep.get(entity)
            if parent:
                ctx = state.get('coverage_model', {}).get('_context', {})
                roles = ctx.get('roles', {})
                parent_role = _role_lookup(roles, parent)
                if parent_role and parent_role != 'system':
                    return role_map.get(parent_role, parent_role)

            upstream_map = state.get('transition_upstream_map', {})
            tos = state.get('coverage_model', {}).get('transition_obligations', [])
            to_by_tid = {t.get('transition_id'): t for t in tos if t.get('transition_id')}
            for tid, ups in upstream_map.items():
                t = to_by_tid.get(tid)
                if t and t.get('entity') == entity:
                    for uid in ups:
                        ut = to_by_tid.get(uid)
                        if ut and ut.get('entity') != entity:
                            ctx = state.get('coverage_model', {}).get('_context', {})
                            r = _role_lookup(ctx.get('roles', {}), ut.get('entity', ''))
                            if r and r != 'system':
                                return role_map.get(r, r)

        return '[待确认角色]'

    if has_auto_kw or role_id == 'system':
        return '系统'

    # BDD: creation transitions (from_state is None) → system role.
    # Previously hardcoded `action == '创建'` — replaced with structural check
    # on the TO's from_state, passed in via the `to` dict context.
    # Fallback: if no action info at all, assume system.
    if not action:
        return '系统'

    return base


def _make_given(target: str, state: str, description: str = "") -> dict:
    """Build a BDD Given clause (business-state precondition).

    ``state`` must be a business state value (e.g. "待审批"), NOT a UI
    navigation instruction.  ``description`` is optional context (e.g.
    VE scenario label).
    """
    return {"target": target, "state": state, "description": description}


def _make_when(target: str, event: str, actor: str = "", action: str = "") -> dict:
    """Build a BDD When clause (business event under test).

    ``event`` describes the business occurrence (declarative, e.g.
    "审批通过事件触发"), NOT the mechanical action.  ``actor`` and
    ``action`` carry concrete execution info.
    """
    return {"target": target, "event": event, "actor": actor, "action": action}


def _make_then(target: str, expectation: str,
               kind: str = "state",
               br_refs: list[str] | None = None,
               cross_refs: list[str] | None = None) -> dict:
    """Build a BDD Then clause (observable business outcome).

    ``expectation`` must be a concrete, non-tautological observable
    (I19: forbidden values include "查看效果", "验证差异").
    ``kind`` ∈ {"state", "behavior", "prompt"}.
    """
    return {
        "target": target,
        "expectation": expectation,
        "kind": kind,
        "br_refs": br_refs or [],
        "cross_refs": cross_refs or [],
    }


# ── Business event derivation ────────────────────────────────────────────
#
# Convert a mechanical action into a natural business event description.
# This is the single place where When.event text is shaped — keeps the
# "事件触发" suffix out of the BDD spec.
#
# Design principle: NO hardcoded business verbs.  The function only does
# generic text cleanup (strip "事件触发" suffix) + optional state-context
# annotation when from/to states are known.  Works for any business domain.


def _derive_business_event(action: str, from_state: str = "", to_state: str = "") -> str:
    """Derive a natural business-event description from a mechanical action.

    Instead of "机构新增/修改实验室信息事件触发", produce "机构新增/修改实验室信息".

    For state transitions, if from_state and to_state are available and
    meaningful, the event can reference the target state:
      action="提交审核", to_state="待审核" → "提交审核（目标状态：待审核）"

    Generic — no hardcoded business keywords.  Only does:
      1. Strip mechanical "事件触发" suffix
      2. If action is empty, describe via from→to state change
      3. If to_state is known and meaningful, append target-state context
    """
    if not action:
        if from_state and to_state and from_state != to_state:
            return f"状态从{from_state}变更为{to_state}"
        return "状态转换"

    # If the action already contains "事件触发", strip it
    cleaned = action.replace("事件触发", "").strip()
    if not cleaned:
        return "状态转换"

    # Append target-state context when the to_state is meaningful (not initial)
    if to_state and to_state != "(初始)" and to_state != from_state:
        return f"{cleaned}（目标状态：{to_state}）"

    return cleaned


def _derive_rejection_action(original_action: str) -> str:
    """Derive the rejection-variant action from the original TO action.

    Generic — no hardcoded "驳回" verb.  Strategy:
      1. If action contains "通过" → replace with "驳回" (审核通过 → 审核驳回)
      2. If action contains "批准" → replace with "驳回" (立项批准 → 立项驳回)
      3. If action contains "同意" → replace with "驳回"
      4. Otherwise → append "（驳回）" to the original action

    This keeps the rejection action semantically aligned with the original
    business operation rather than a generic "驳回".
    """
    if not original_action:
        return "驳回"
    cleaned = _strip_branch_suffix(original_action)
    for approve_kw in ("通过", "批准", "同意", "确认"):
        if approve_kw in cleaned:
            return cleaned.replace(approve_kw, "驳回")
    return f"{cleaned}（驳回）"


# ── Branch dimension extraction (generic, not hardcoded) ─────────────────
#
# P2 may split a single business transition into multiple TOs by branch
# dimension (e.g. T-030a / T-030b split by 项目类型=能力验证/测量审核).
# The branch info lives in two places:
#   1. coverage_model._context.branch_dimensions — the canonical source:
#      {entity, dimension, branches: [{value, target_transition}]}
#   2. TO.action text — P2 sometimes appends "[维度=值]" suffix as a marker
#
# S1 should:
#   - read branch_dimensions to find which branch value applies to this TO
#   - emit a Given clause for the branch dimension (so BDD spec shows the branch)
#   - strip the "[维度=值]" suffix from action (it's a P2 marker, not spec)
#
# This is GENERIC: works for any branch dimension (项目类型, 评分方式, 评价人员角色,
# 消息发送接收人范围, etc.), not hardcoded to 项目类型.

# Regex to strip "[维度=值]" or "[维度=值1/值2]" suffix from action text
_BRANCH_SUFFIX_RE = re.compile(r'\s*\[[^\]]+=[^\]]+\]\s*$')


def _strip_branch_suffix(action: str) -> str:
    """Remove trailing [维度=值] markers from action text.

    Examples:
        "发出样品 [项目类型=能力验证]" → "发出样品"
        "发放样品与作业指导书 [项目类型=测量审核]" → "发放样品与作业指导书"
        "立项批准 [项目类型=能力验证/测量审核]" → "立项批准"
    """
    if not action:
        return action
    cleaned = action
    while _BRANCH_SUFFIX_RE.search(cleaned):
        cleaned = _BRANCH_SUFFIX_RE.sub('', cleaned).strip()
    return cleaned


def _extract_branch_givens(
    to: dict, coverage_model: dict
) -> list[dict]:
    """Extract branch-dimension Given clauses for a TO.

    Two sources (merged, deduped):
      1. coverage_model._context.branch_dimensions — canonical, matched by
         target_transition prefix (e.g. target=T-001, to_id=T-001a → match).
         Entity filter is NOT applied because branch_dimensions may record
         only the primary entity (E-PROJ) while branch TOs exist on other
         entities (E-REG, E-ARC).
      2. TO.action text "[维度=值]" suffix — fallback when branch_dimensions
         is incomplete.  P2 appends this marker to branched TOs.

    This is GENERIC: works for any branch dimension (项目类型, 评分方式,
    评价人员角色, 消息发送接收人范围, etc.), no hardcoded dimension names.
    """
    if not to:
        return []
    to_id = to.get("id", "") or to.get("transition_id", "")
    to_entity = to.get("entity", "")
    to_action = to.get("action", "")
    givens: list[dict] = []
    seen_dims: set[str] = set()

    # ── Source 1: branch_dimensions (canonical) ──
    bds = coverage_model.get("_context", {}).get("branch_dimensions", [])
    for bd in bds:
        bd_entity = bd.get("entity", "")
        bd_dim = bd.get("dimension", "")
        # Match by target_transition prefix (no entity filter — branch may
        # apply to dependent entities too, e.g. E-REG.报名记录样品状态)
        for branch in bd.get("branches", []):
            target_tid = branch.get("target_transition", "")
            branch_value = branch.get("value", "")
            if target_tid and to_id.startswith(target_tid) and to_id != target_tid:
                givens.append(_make_given(
                    target=f"{bd_entity}.{bd_dim}",
                    state=branch_value,
                    description=f"分支条件: {bd_dim}={branch_value}",
                ))
                seen_dims.add(bd_dim)
                break

    # ── Source 2: action "[维度=值]" suffix (fallback) ──
    # Pattern: [项目类型=能力验证] or [评分方式=分值, 评价人员角色=评价成员]
    for m in re.finditer(r'\[([^\]]+)\]', to_action):
        content = m.group(1)
        # Split by comma (Chinese or ASCII) for multi-dimension branches
        for part in re.split(r'[,，]', content):
            if '=' in part:
                dim_name, dim_value = part.split('=', 1)
                dim_name = dim_name.strip()
                dim_value = dim_value.strip()
                if dim_name and dim_value and dim_name not in seen_dims:
                    givens.append(_make_given(
                        target=f"{to_entity}.{dim_name}",
                        state=dim_value,
                        description=f"分支条件: {dim_name}={dim_value}",
                    ))
                    seen_dims.add(dim_name)
    return givens


def _enrich_thens(entity_id: str, action: str, thens: list[dict],
                  constraint_steps: dict[str, list[dict]]) -> list[dict]:
    """Append field-validation Thens to a procedure's thens list.

    field_validation now emits ThenClause dicts directly (target/expectation/
    kind/br_refs/cross_refs), so we just extend ``thens`` with them.
    """
    from nodes.field_validation import should_enrich
    if not should_enrich(action):
        return thens
    extra = constraint_steps.get(entity_id, [])
    for then_clause in extra:
        # Already in ThenClause format — append directly
        if then_clause.get("expectation"):
            thens.append(then_clause)
    return thens


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

    # Rule 1: relevant entity + special op (configurable via coverage_model)
    # BDD: TYPE5_SPECIAL_OPS is now read from coverage_model._context.type5_special_ops
    # instead of being a hardcoded business keyword list.
    cm = state["coverage_model"]
    special_ops = set(cm.get("_context", {}).get("type5_special_ops", [])) | TYPE5_SPECIAL_OPS
    relevant = {primary, *dependents}
    for ve in ves.values():
        relevant.add(ve.get("original_entity", ""))
    if entity in relevant and op_name in special_ops:
        return True
    # Rule 2: priority >= medium
    if eo.get("coverage_priority") in ("medium", "high", "critical"):
        return True
    # Rule 3: L0/L1/L5 + delete
    # BDD: "删除" is now configurable via type5_special_ops; if not configured,
    # check topology_level for L0/L1/L5 entities with any delete-like op.
    topology_levels = state.get("topology_levels", {})
    tl = topology_levels.get(entity, -1)
    delete_ops = {"删除", "remove", "delete"} | special_ops
    if tl in (0, 1, 5) and any(d in op_name for d in delete_ops):
        return True
    # Rule 4: CO trigger match
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


def _resolve_phase_for_non_transition(state: dict, entity: str) -> dict:
    """Derive a sensible phase for non-transition procedures (Type3, Type7, etc.)

    Uses the entity's dep_state_phase_map maximum non-zero phase so rules,
    attribute configs, and other non-transition procedures sort near the
    entity's later business stage. Using max ensures the system state
    prerequisites exist before the rule is tested (better too late than too early).
    """
    primary = state["primary_entity"]
    dep_map = state.get("dep_state_phase_map", {})
    phase_table = state.get("phase_table", {})

    if entity == primary:
        all_p = [p for dm in phase_table.get("state_to_phase", {}).values() for p in dm.values()]
        if all_p:
            non_zero = [p for p in all_p if p > 0]
            p = max(non_zero) if non_zero else max(all_p)
            return {"phase": p, "basis": f"primary_entity_max_phase.{p}"}
        return {"phase": 0, "basis": "primary_entity_default"}

    if entity in dep_map:
        all_p = [p for dm in dep_map[entity].values() for p in dm.values()]
        if all_p:
            non_zero = [p for p in all_p if p > 0]
            p = max(non_zero) if non_zero else max(all_p)
            return {"phase": p, "basis": f"dep_map_max_phase.{entity}.{p}"}
        # Empty dep_map — fall through to parent-chain logic below

    # Entity absent from dep_map (or has empty dep_map):
    # Config entities (tagged "configurable" without multi-state) are
    # foundational setup like E-TESTITEM — they should stay at P0 rather
    # than being pushed to the parent's late lifecycle phase.
    ctx = state.get("coverage_model", {}).get("_context", {})
    entity_details = ctx.get("entity_details", [])
    if isinstance(entity_details, dict):
        entity_details = list(entity_details.values())
    entity_tags = []
    for e in entity_details:
        if e.get("id") == entity:
            entity_tags = e.get("tags", [])
            break
    is_config_only = "configurable" in entity_tags and "multi-state" not in entity_tags
    if is_config_only:
        return {"phase": 0, "basis": f"config_entity.{entity}"}

    # Follow entity_parent chain to find a parent with phase info.
    parent_map = state.get("entity_parent", {})
    parent = entity
    while parent:
        parent = parent_map.get(parent)
        if not parent:
            break
        if parent in dep_map:
            all_p = [p for dm in dep_map[parent].values() for p in dm.values()]
            if all_p:
                non_zero = [p for p in all_p if p > 0]
                p = max(non_zero) if non_zero else max(all_p)
                return {"phase": p, "basis": f"parent_phase.{parent}.{p} (via chain from {entity})"}
        if parent == primary:
            all_p = [p for dm in phase_table.get("state_to_phase", {}).values() for p in dm.values()]
            if all_p:
                non_zero = [p for p in all_p if p > 0]
                p = max(non_zero) if non_zero else max(all_p)
                return {"phase": p, "basis": f"parent_primary_phase.{parent}.{p} (via chain from {entity})"}
        # Continue walking up the chain

    return {"phase": 0, "basis": f"fallback_default.{entity}"}


def _resolve_phase_for_transition(entity: str, dimension: str, from_state: str,
                                  to_state: str, state: AgentState,
                                  is_rollback: bool = False) -> dict:
    """Phase assignment for transition procedures.

    Forward edges: phase = to_state's phase (entering a new stage).
    Rollback edges: phase = from_state's phase (backward transition stays
        at the stage where it was triggered, e.g. 评价确认中→评价中
        happens at phase 5, not phase 4).
    """
    if is_rollback and from_state:
        result = _resolve_phase(entity, dimension, from_state, state)
        if result.get("phase", 0) > 0:
            return result
    return _resolve_phase(entity, dimension, to_state, state)


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
    """Map obligation_type to type label per S1.0 type table."""
    if obligation_type == 4:
        return "constraint"          # Type4a
    if obligation_type == 5:
        return "lifecycle"           # Type4b
    if obligation_type == 6:
        return "crud"                # Type5
    if obligation_type == 7:
        return "invalid"             # Type6
    if obligation_type == 8:
        return "rule"                # Type7 standalone
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
    """Map obligation_type to type_priority per sort_key spec."""
    if obligation_type == 4:
        return TYPE_PRIORITY_MAP.get("constraint", 3)   # Type4a
    if obligation_type == 5:
        return TYPE_PRIORITY_MAP.get("lifecycle", 7)    # Type4b
    if obligation_type == 6:
        return TYPE_PRIORITY_MAP.get("crud", 5)          # Type5
    if obligation_type == 7:
        return TYPE_PRIORITY_MAP.get("invalid", 9)       # Type6
    if obligation_type == 8:
        return TYPE_PRIORITY_MAP.get("rule", 6)          # Type7
    if obligation_type == 3:
        return TYPE_PRIORITY_MAP.get("happy", 1)         # Type3
    return TYPE_PRIORITY_MAP.get(risk_trait, 1)


# ---------------------------------------------------------------------------
# Type1 — Transition Obligation procedures
# ---------------------------------------------------------------------------

def _generate_type1(state: AgentState, indices: dict, depth_cache: dict) -> list[dict]:
    """Generate Type1 (transition_obligation) procedures — BDD style.

    For each TO:
    - Check if it belongs to a VE (virtual entity) → generate per VE
    - Build Given/When/Then clauses with side-effects as additional Thens
    - Add audit_rejection variant if risk_traits contains 'audit'
    - Add time_sensitive boundary + expired variants if risk_traits contains 'time_sensitive'

    BDD mapping (from AAA):
      Old S step → Given(target=entity.dim, state=from_state)
      Old A step → When(event=action_desc, actor=role, action=action)
      Old V step → Then(target=entity.dim, expectation=to_state, kind="state")
      Old side-effect V → Then(target=target.dim, expectation=effect_desc, kind="behavior")
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
            # BDD: rollback edges use from_state's phase, forward edges use to_state's
            to_traits = to.get("risk_traits", []) or to.get("traits", []) or []
            is_rollback = "rollback" in to_traits
            phase_info = _resolve_phase_for_transition(
                te["entity"], dimension, to.get("from"), to.get("to"), state,
                is_rollback=is_rollback,
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
            elif "rollback" in risk_traits:
                proc_risk_trait = "rollback"
                proc_type_priority = 4
                proc_type_label = "rollback"

            # ── Build BDD clauses ──
            loc = f"{te['entity']}.{dimension}"
            from_state = to.get('from') or '(初始)'
            to_state = to.get('to', '')
            action = to.get('action', '')
            preconditions = to.get("preconditions", [])

            # Given: business state precondition (NOT "导航配置入口")
            given_desc = te["context"] or ""
            if preconditions:
                given_desc = (given_desc + ("; " if given_desc else "") +
                              "; ".join(preconditions))
            givens: list[dict] = [
                _make_given(target=loc, state=from_state, description=given_desc)
            ]
            # BDD: append branch-dimension Givens (generic, from branch_dimensions)
            # e.g. Given: E-PROJ.项目类型 = 能力验证 (分支条件)
            givens.extend(_extract_branch_givens(to, cm))

            # When: business event (declarative) + actor + action
            # BDD: strip "[维度=值]" suffix from action — it's a P2 marker, not spec
            role = _get_role_name(to.get('role'), action, entity, state)
            clean_action = _strip_branch_suffix(action)
            event_desc = _derive_business_event(clean_action, from_state, to_state)
            when: dict = _make_when(
                target=loc, event=event_desc, actor=role, action=clean_action
            )

            # Thens: main observable + side effects + rollback
            thens: list[dict] = []
            if to.get('from') and to.get('from') == to.get('to'):
                # Self-loop: observe the effect (not state change)
                er = (to.get('expected_results') or [''])[0] if to.get('expected_results') else '效果生效'
                thens.append(_make_then(
                    target=loc, expectation=er, kind="behavior"
                ))
            else:
                thens.append(_make_then(
                    target=loc, expectation=f"状态转换为{to_state}", kind="state"
                ))

            # Side effects as additional Thens (Type2 embedding) — I20: ≤1 hop
            cos = cm.get("cross_entity_obligations", [])
            side_effects = to.get("side_effects") or []
            for se in side_effects:
                target = se.get('target_entity', '')
                se_target_dim = se.get('target_dimension') or dimension
                se_loc = f"{target}.{se_target_dim}"
                effect_desc = se.get('effect_desc', '')
                # (a) Same entity → add directly
                if target == entity:
                    thens.append(_make_then(
                        target=se_loc, expectation=effect_desc, kind="behavior"
                    ))
                else:
                    # (b) Cross-entity with direct CO link → add with causal check
                    direct_co = next((co for co in cos
                                      if co.get('enabler_entity') == entity
                                      and co.get('dependent_entity') == target), None)
                    if direct_co:
                        dep_cond = direct_co.get('dependent_condition', '')
                        if dep_cond and effect_desc and dep_cond in effect_desc:
                            thens.append(_make_then(
                                target=se_loc, expectation=effect_desc, kind="behavior"
                            ))
                    # (c) No direct CO → skip (indirect causal, covered by own entity)

            # operation_lifecycle: 1=创建(from==null) 2=修改(from==to) 3=流转(from≠to) 4=终止(rollback)
            if to.get('from') is None:
                op_lifecycle = 1  # 创建
            elif to.get('from') == to.get('to'):
                op_lifecycle = 2  # 修改
            elif "rollback" in risk_traits:
                op_lifecycle = 4  # 终止
            else:
                op_lifecycle = 3  # 流转

            # --- data_constraint: skip if has branch ---
            if "data_constraint" in risk_traits:
                has_branch = any(
                    bd.get('entity') == entity and bd.get('dimension') == dimension
                    for bd in cm.get('_context', {}).get('branch_dimensions', [])
                )
                if has_branch:
                    continue

            # --- rollback: embed as additional Then ---
            if "rollback" in risk_traits:
                thens.append(_make_then(
                    target=loc,
                    expectation="状态可回退至前驱状态",
                    kind="behavior"
                ))

            # BDD: field_validation Thens are NO LONGER injected into Type1.
            # They are generated as independent Type9 procedures instead,
            # so each procedure describes exactly one business behaviour.
            # (was: _enrich_thens(entity, action, thens, constraint_steps))

            phase_val = phase_info.get("phase") if phase_info.get("phase") is not None else 0
            phase_name = (phase_table["phase_names"][phase_val]
                          if phase_val < len(phase_table["phase_names"])
                          else f"P{phase_val}")

            base_proc = {
                "temp_id": f"PROC-T1-{_next_gen_seq()}",
                "source_ids": [to["id"]],
                "entity": te["entity"],
                "dimension": dimension,
                "obligation_type": 1,
                "risk_trait": proc_risk_trait,
                "givens": givens,
                "when": when,
                "thens": thens,
                "operation_hints": [],  # execution details, kept separate from spec
                "gen_seq": _gen_seq_counter,
                "post_state": f"{te['entity']}.{dimension}→{to_state}",
                "cascade_chain": None,
                "embedded_brs": [],
                "_S2_fields": {
                    "phase": phase_val,
                    "phase_name": phase_name,
                    "phase_basis": phase_info.get("basis", ""),
                    "topology_level": topo.get(te["entity"], 0),
                    "sort_key": [],
                    "operation_lifecycle": op_lifecycle,
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

            # --- Audit rejection variant --- I21: role fallback for rejection
            if "audit" in risk_traits:
                reject_action = _derive_rejection_action(action)
                reject_role = _get_role_name(to.get('role'), reject_action, entity, state)
                reject_givens = [
                    _make_given(
                        target=loc,
                        state=from_state,
                        description=(f"[{te['context']}] " if te["context"] else "") +
                                    "已提请审批",
                    )
                ]
                reject_when = _make_when(
                    target=loc, event=_derive_business_event(reject_action, from_state),
                    actor=reject_role, action=reject_action
                )
                reject_thens = [
                    _make_then(
                        target=loc,
                        expectation=f"状态回退至{from_state}且驳回原因已记录",
                        kind="state",
                    )
                ]
                reject_proc = {
                    "temp_id": f"PROC-T1-{_next_gen_seq()}",
                    "source_ids": [to["id"]],
                    "entity": te["entity"],
                    "dimension": dimension,
                    "obligation_type": 1,
                    "risk_trait": "audit_rejection",
                    "givens": reject_givens,
                    "when": reject_when,
                    "thens": reject_thens,
                    "operation_hints": [],
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{te['entity']}.{dimension}→{from_state}(驳回)",
                    "cascade_chain": None,
                    "embedded_brs": [],
                    "_S2_fields": {
                        "phase": phase_val,
                        "phase_name": phase_name,
                        "phase_basis": phase_info.get("basis", "") + " (rejection variant)",
                        "topology_level": topo.get(te["entity"], 0),
                        "sort_key": [],
                        "operation_lifecycle": 4,  # 4=终止 (rejection)
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
                # Boundary variant
                boundary_givens = [
                    _make_given(target=loc, state=from_state,
                                description="时间边界条件: 接近截止时间")
                ]
                boundary_when = _make_when(
                    target=loc, event=_derive_business_event(f"{action}(时间边界)", from_state, to_state),
                    actor=role, action=f"{action}(边界)"
                )
                boundary_thens = [
                    _make_then(target=loc,
                               expectation=f"状态转换为{to_state}(时间边界生效)",
                               kind="state")
                ]
                boundary_proc = {
                    "temp_id": f"PROC-T1-{_next_gen_seq()}",
                    "source_ids": [to["id"]],
                    "entity": te["entity"],
                    "dimension": dimension,
                    "obligation_type": 1,
                    "risk_trait": "time_sensitive",
                    "givens": boundary_givens,
                    "when": boundary_when,
                    "thens": boundary_thens,
                    "operation_hints": [],
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{te['entity']}.{dimension}→{to_state}(时间边界)",
                    "cascade_chain": None,
                    "embedded_brs": [],
                    "_S2_fields": {
                        "phase": phase_val,
                        "phase_name": phase_name,
                        "phase_basis": phase_info.get("basis", "") + " (time_boundary)",
                        "topology_level": topo.get(te["entity"], 0),
                        "sort_key": [],
                        "operation_lifecycle": op_lifecycle,
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
                expired_givens = [
                    _make_given(target=loc, state=from_state,
                                description="时间过期条件: 超过截止时间")
                ]
                expired_when = _make_when(
                    target=loc, event=f"尝试{action}事件(已过期)",
                    actor=role, action=f"尝试{action}(已过期)"
                )
                expired_thens = [
                    _make_then(target=loc,
                               expectation="操作不可执行或状态不变",
                               kind="behavior")
                ]
                expired_proc = {
                    "temp_id": f"PROC-T1-{_next_gen_seq()}",
                    "source_ids": [to["id"]],
                    "entity": te["entity"],
                    "dimension": dimension,
                    "obligation_type": 1,
                    "risk_trait": "time_sensitive",
                    "givens": expired_givens,
                    "when": expired_when,
                    "thens": expired_thens,
                    "operation_hints": [],
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{te['entity']}.{dimension}→(过期未执行)",
                    "cascade_chain": None,
                    "embedded_brs": [],
                    "_S2_fields": {
                        "phase": phase_val,
                        "phase_name": phase_name,
                        "phase_basis": phase_info.get("basis", "") + " (time_expired)",
                        "topology_level": topo.get(te["entity"], 0),
                        "sort_key": [],
                        "operation_lifecycle": op_lifecycle,
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

def _type3_then_expectation(eo: dict, branch: dict, state: AgentState) -> tuple[str, str, list[str]]:
    """I19: Generate non-tautological Then expectation for Type3.

    Returns (expectation, kind, br_refs).
    Priority: ① BR effect → ② branch path condition → ③ display value
    """
    attr = eo.get('attribute_name', '')
    val = branch.get('value', '')
    bds = state.get('coverage_model', {}).get('_context', {}).get('branch_dimensions', [])
    for bd in bds:
        if bd.get('entity') == eo['entity'] and bd.get('dimension') == attr:
            brs = bd.get('business_rules', []) or bd.get('coverage', {}).get('business_rules', [])
            for br_id in brs:
                return (f"配置{attr}={val}的效果已生效", "behavior", [br_id])
            bp = bd.get('branch_path') or branch.get('desc', '')
            if bp:
                return (f"{bp}已生效，{attr}可见{val}对应选项", "behavior", [])
    return (f"{attr}显示为{val}", "state", [])


def _generate_type3(state: AgentState, indices: dict, depth_cache: dict) -> list[dict]:
    """Generate Type3 (attribute_config) procedures — BDD style.

    For each attribute_config EO:
    - If a matching branch_dimension exists → one procedure per branch value
    - Otherwise → single procedure

    BDD mapping:
      Old "导航配置入口" → operation_hint (NOT a Given)
      Given: entity has current attribute value (business state)
      When: attribute change event fires
      Then: observable effect (BR effect / branch path / display value)
    """
    phase_table = state["phase_table"]
    topo = state["topology_levels"]
    cfg_eo_to_bd = indices["cfg_eo_to_bd"]

    procedures: list[dict] = []

    attr_cfg_eos = indices["eo_by_type"].get("attribute_config", [])
    for eo in attr_cfg_eos:
        bd = cfg_eo_to_bd.get(eo["id"])
        attr = eo.get('attribute_name', '')

        if bd:
            # Generate one procedure per branch value
            for branch in bd.get("branches", []):
                transition_id = branch.get("target_transition", "")
                chain_depth = depth_cache.get(transition_id, 0)
                phase_info = _resolve_phase(eo["entity"], attr, branch["value"], state)
                dim_priority = _get_dimension_priority(eo["entity"], attr, state)

                val = branch['value']
                exp, kind, br_refs = _type3_then_expectation(eo, branch, state)
                givens = [_make_given(
                    target=eo['entity'],
                    state=f"{attr}为当前值",
                    description=f"当前{attr}配置值",
                )]
                when = _make_when(
                    target=eo['entity'],
                    event=f"{attr}配置变更为{val}事件",
                    action=f"修改{attr}为{val}",
                )
                thens = [_make_then(
                    target=f"{eo['entity']}.{attr}",
                    expectation=exp, kind=kind, br_refs=br_refs,
                )]
                # operation_hint carries the UI navigation detail
                op_hints = [f"导航至{eo['entity']}配置入口"]

                phase_val = phase_info.get("phase") or 0
                phase_name = (phase_table["phase_names"][phase_val]
                              if phase_val < len(phase_table["phase_names"]) else f"P{phase_val}")

                proc = {
                    "temp_id": f"PROC-T3-{_next_gen_seq()}",
                    "source_ids": [eo["id"]],
                    "entity": eo["entity"],
                    "dimension": attr,
                    "obligation_type": 3,
                    "risk_trait": "",
                    "givens": givens,
                    "when": when,
                    "thens": thens,
                    "operation_hints": op_hints,
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{eo['entity']}.{attr}→{val}",
                    "cascade_chain": None,
                    "embedded_brs": list(br_refs),
                    "_S2_fields": {
                        "phase": phase_val,
                        "phase_name": phase_name,
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
                # BDD: field_validation moved to independent Type9 procedures
                # (was: _enrich_thens(eo["entity"], ..., proc["thens"], ...))
                procedures.append(proc)
        else:
            tl = topo.get(eo["entity"], 0)
            phase_res = _resolve_phase_for_non_transition(state, eo["entity"])
            phase = phase_res["phase"]
            phase_basis = phase_res["basis"]
            dim_priority = _get_dimension_priority(eo["entity"], attr, state)

            givens = [_make_given(
                target=eo['entity'],
                state=f"{attr}为当前值",
                description=f"当前{attr}配置值",
            )]
            when = _make_when(
                target=eo['entity'],
                event=f"{attr}配置变更事件",
                action=f"修改{attr}",
            )
            thens = [_make_then(
                target=f"{eo['entity']}.{attr}",
                expectation=f"{attr}显示为修改后的值",
                kind="state",
            )]
            op_hints = [f"导航至{eo['entity']}配置入口"]

            phase_name = (phase_table["phase_names"][phase]
                          if phase < len(phase_table["phase_names"]) else f"P{phase}")

            proc = {
                "temp_id": f"PROC-T3-{_next_gen_seq()}",
                "source_ids": [eo["id"]],
                "entity": eo["entity"],
                "dimension": attr,
                "obligation_type": 3,
                "risk_trait": "",
                "givens": givens,
                "when": when,
                "thens": thens,
                "operation_hints": op_hints,
                "gen_seq": _gen_seq_counter,
                "post_state": f"{eo['entity']}.{attr}→(已修改)",
                "cascade_chain": None,
                "embedded_brs": [],
                "_S2_fields": {
                    "phase": phase,
                    "phase_name": phase_name,
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
            # BDD: field_validation moved to independent Type9 procedures
            # (was: _enrich_thens(eo["entity"], ..., proc["thens"], ...))
            procedures.append(proc)

    return procedures


# ---------------------------------------------------------------------------
# Type4a/4b — REMOVED: CO used only for ordering, not for generation
# ---------------------------------------------------------------------------
# Type4a (constraint CO) and Type4b (lifecycle CO) procedures have been
# removed.  They were redundant — their enabler and dependent state
# transitions are already covered by Type1 procedures, and their own Then
# said "此条件已在T-XXX前置条件中体现".
#
# CO (cross_entity_obligations) is now used ONLY in S3 for dependency
# ordering: enabler's Type1 procedure must precede dependent's Type1.
# No procedures are generated from CO.


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
            else:
                # Empty dep_map — use parent chain
                phase_res = _resolve_phase_for_non_transition(state, entity)
                phase = phase_res["phase"]
                phase_basis = phase_res["basis"]
        elif entity in ves:
            phase = ves[entity].get("resolved_phase", 0)
            phase_basis = f"VE.{entity}.resolved_phase"
        else:
            phase_res = _resolve_phase_for_non_transition(state, entity)
            phase = phase_res["phase"]
            phase_basis = phase_res["basis"]

        # Check if entity has VEs → generate one per VE
        ves_for_entity = [(ve_name, ve) for ve_name, ve in ves.items()
                          if ve.get("original_entity") == entity]

        if ves_for_entity:
            for ve_name, ve in ves_for_entity:
                ve_phase = ve.get("resolved_phase", 0)
                op_name = eo['operation_name']
                op_desc = eo.get('description', '')
                givens = [_make_given(
                    target=ve_name, state="存在",
                    description=f"操作入口可用",
                )]
                when = _make_when(
                    target=ve_name,
                    event=_derive_business_event(op_name),
                    action=f"执行{op_name}",
                )
                thens = [_make_then(
                    target=ve_name,
                    expectation=op_desc or f"{op_name}完成",
                    kind="behavior",
                )]
                op_hints = [f"导航至{ve.get('context', '')}页面"]

                ve_phase_name = (phase_table["phase_names"][ve_phase]
                                 if ve_phase < len(phase_table["phase_names"]) else f"P{ve_phase}")

                proc = {
                    "temp_id": f"PROC-T5-{_next_gen_seq()}",
                    "source_ids": [eo["id"]],
                    "entity": ve_name,
                    "dimension": None,
                    "obligation_type": 6,
                    "risk_trait": "",
                    "givens": givens,
                    "when": when,
                    "thens": thens,
                    "operation_hints": op_hints,
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{ve_name}→({op_name}完成)",
                    "cascade_chain": None,
                    "embedded_brs": [],
                    "_S2_fields": {
                        "phase": ve_phase,
                        "phase_name": ve_phase_name,
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
                # BDD: field_validation moved to independent Type9 procedures
                procedures.append(proc)
        else:
            op_name = eo['operation_name']
            op_desc = eo.get('description', '')
            entity_name = eo.get('entity_name', entity)
            givens = [_make_given(
                target=entity, state="存在",
                description="操作入口可用",
            )]
            when = _make_when(
                target=entity,
                event=_derive_business_event(op_name),
                action=f"执行{op_name}",
            )
            thens = [_make_then(
                target=entity,
                expectation=op_desc or f"{op_name}完成",
                kind="behavior",
            )]
            op_hints = [f"导航至{entity_name}页面"]

            phase_name = (phase_table["phase_names"][phase]
                          if phase < len(phase_table["phase_names"]) else f"P{phase}")

            proc = {
                "temp_id": f"PROC-T5-{_next_gen_seq()}",
                "source_ids": [eo["id"]],
                "entity": entity,
                "dimension": None,
                "obligation_type": 6,
                "risk_trait": "",
                "givens": givens,
                "when": when,
                "thens": thens,
                "operation_hints": op_hints,
                "gen_seq": _gen_seq_counter,
                "post_state": f"{entity}→({op_name}完成)",
                "cascade_chain": None,
                "embedded_brs": [],
                "_S2_fields": {
                    "phase": phase,
                    "phase_name": phase_name,
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
            # BDD: field_validation moved to independent Type9 procedures
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
            # If dep_map exists but is empty or state not found, fall through
            if phase == 0 and not phase_basis:
                phase_res = _resolve_phase_for_non_transition(state, entity)
                phase = phase_res["phase"]
                phase_basis = phase_res["basis"]
        elif entity not in dep_map:
            # Entity absent from dep_map — try parent chain via helper
            phase_res = _resolve_phase_for_non_transition(state, entity)
            phase = phase_res["phase"]
            phase_basis = phase_res["basis"]

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
            "givens": [_make_given(
                target=entity, state=ro.get('from', ''),
                description=f"{entity}处于\"{ro.get('from', '')}\"状态",
            )],
            "when": _make_when(
                target=entity,
                event=f"尝试{ro.get('from', '')}→{ro.get('to', '')}转换事件",
                action=f"尝试执行从\"{ro.get('from', '')}\"到\"{ro.get('to', '')}\"的操作",
            ),
            "thens": [
                _make_then(
                    target=entity,
                    expectation=f"操作被拒绝，{ro.get('reason', '')}",
                    kind="prompt",
                ),
                _make_then(
                    target=entity,
                    expectation=f"状态仍为{ro.get('from', '')}",
                    kind="state",
                ),
            ],
            "operation_hints": [],
            "gen_seq": _gen_seq_counter,
            "post_state": f"{entity}→(操作被阻止)",
            "cascade_chain": None,
            "embedded_brs": [],
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
    """S1.8.1: Classify BRs with full degradation chain.

    Priority: attribute_effect > transition_constraint > crud_constraint > negative_test > standalone.
    If high-priority category has no host → downgrade to next, with warning.
    """
    cm = state["coverage_model"]
    bds = cm.get("_context", {}).get("branch_dimensions", [])
    tos = cm.get("transition_obligations", [])
    co_constraint = indices["co_constraint"]
    eo_by_type = indices["eo_by_type"]
    ro_by_type = indices["ro_by_type"]
    entity_name_map = indices.get("entity_name_map", {})
    warnings = list(state.get("warnings", []))

    br_list = ro_by_type.get("business_rule", [])
    classifications = []

    for br in br_list:
        br_id = br.get("constraint_id", "")
        desc = br.get("description", "")
        entities_raw = br.get("entities_involved", br.get("entities", ""))
        br_entities = _resolve_entity_names(entities_raw, entity_name_map)

        candidates = []

        # 1. attribute_effect
        for bd in bds:
            cov = bd.get("coverage", {})
            if cov and br_id in cov.get("business_rules", []):
                cfg_eos = [eo for eo in eo_by_type.get("attribute_config", [])
                           if eo["entity"] == bd["entity"] and eo.get("attribute_name") == bd["dimension"]]
                if cfg_eos:
                    candidates.append({
                        "category": "attribute_effect", "host_proc_type": 3,
                        "host_eo_ids": [eo["id"] for eo in cfg_eos], "bd": bd,
                        "priority": 1
                    })

        # 2. transition_constraint
        if re.search(r'需先.*后|才可|必须.*后', desc) and len(br_entities) >= 2:
            to_match = next((to for to in tos
                             if br_entities and to["entity"] in br_entities
                             and "audit" in (to.get("risk_traits") or [])), None)
            co_match = next((co for co in co_constraint
                             if co["enabler_entity"] in br_entities or co["dependent_entity"] in br_entities), None)
            if to_match or co_match:
                candidates.append({
                    "category": "transition_constraint",
                    "host_proc_type": 1 if to_match else 4,
                    "host_to_id": to_match["id"] if to_match else None,
                    "host_co_id": co_match["id"] if co_match else None,
                    "priority": 2
                })

        # 3. crud_constraint
        # BDD: crud_ops read from coverage_model._context (configurable)
        cm_ctx = cm.get("_context", {})
        crud_ops = set(cm_ctx.get("crud_ops", []))
        if not crud_ops:
            # Fallback: detect CRUD from BR description via LLM classification
            # For now, use a generic heuristic: any EO of type crud_operation
            # whose entity matches br_entities is a candidate
            crud_ops = set()
        has_crud = any(op in desc for op in crud_ops) if crud_ops else bool(
            eo_by_type.get("crud_operation") and
            any(eo["entity"] in br_entities for eo in eo_by_type.get("crud_operation", []))
        )
        has_state = bool(re.search(r'状态|才可|不可|不允许|不能|只有|需先', desc))
        if has_crud and has_state:
            matching_eo = next((eo for eo in eo_by_type.get("crud_operation", [])
                                if eo["entity"] in br_entities and (
                                    not crud_ops or any(op in eo["operation_name"] for op in crud_ops))), None)
            if matching_eo and _is_type5_retained(matching_eo, state):
                candidates.append({
                    "category": "crud_constraint", "host_proc_type": 5,
                    "host_eo_id": matching_eo["id"],
                    "priority": 3
                })

        # 4. negative_test
        if re.search(r'不可.*选择|不可.*删除|不可.*修改|不可.*操作|不可.*发布|不允许.*删除|不允许.*操作|不能.*删除|不能.*混合', desc):
            matching_it = next((ro for ro in ro_by_type.get("invalid_transition", [])
                                if ro["entity"] in br_entities), None)
            candidates.append({
                "category": "negative_test", "host_proc_type": 6,
                "host_ro_id": matching_it["id"] if matching_it else None,
                "generate_variant": matching_it is None,
                "priority": 4
            })

        candidates.sort(key=lambda c: c["priority"])

        chosen = None
        for cand in candidates:
            has_host = (
                cand.get("host_eo_ids") or cand.get("host_to_id") or
                cand.get("host_co_id") or cand.get("host_eo_id") or
                cand.get("host_ro_id") or cand.get("generate_variant")
            )
            if has_host:
                chosen = cand
                break
            else:
                warnings.append(f"BR {br_id}: {cand['category']} has no host, downgrading")

        if chosen:
            chosen["br"] = br
            classifications.append(chosen)
        else:
            classifications.append({"br": br, "category": "standalone", "host_proc_type": 7, "priority": 5})

    return classifications


# ---------------------------------------------------------------------------
# BR Description Decomposition (方案A: 原子V步拆解)
# ---------------------------------------------------------------------------

# Predicate keywords that signal an independent clause in Chinese business rules.
# These cover: prohibitions (不可/不能), obligations (必须/应), permissions (可/可以),
# entity descriptions (由/包含/记录), display behavior (展示/显示), and action verbs.
# ---------------------------------------------------------------------------
# LLM-based BR description decomposition (replaces _BR_PREDICATE_MARKERS)
# ---------------------------------------------------------------------------

_BR_DECOMPOSE_PROMPT = """你是一个业务规则拆解器。将复合业务规则描述拆解为原子断言。

## 拆解原则
1. 分号（；）必拆——分隔独立规则
2. 逗号（，）仅当两侧都是独立断言时拆
3. 每个原子断言应是一个完整的、可独立验证的规则
4. 不要拆分枚举（如"启用/停用"）
5. 不要拆分从句（如"当X时，做Y"中的X是从句）

## 输出格式（JSONL）
{"id":"BR-原始ID","atoms":["原子断言1","原子断言2",...]}

只输出 JSONL，不要额外说明。"""


def _decompose_brs_via_llm(brs: list[dict]) -> dict[str, list[tuple[str, str]]]:
    """Decompose BR descriptions into atomic assertions via LLM.

    Args:
        brs: List of BR dicts (from constraint_obligations, type=business_rule)

    Returns:
        ``{br_id: [(sub_label, assertion_text), ...]}`` dict.
        On failure, returns empty dict — callers fall back to single-atom
        (no decomposition).
    """
    if not brs:
        return {}

    import os as _os
    api_base = _os.environ.get('LLM_API_BASE', 'https://open.bigmodel.cn/api/paas/v4').rstrip('/')
    api_key = _os.environ.get('LLM_API_KEY', '')
    model = _os.environ.get('LLM_BR_DECOMPOSE_MODEL', 'glm-4-flash')
    if not api_key:
        cfg_path = _os.path.join(_os.path.dirname(__file__), '..', 'config.json')
        try:
            import json as _json
            with open(cfg_path) as f:
                cfg = _json.load(f)
            llm_cfg = cfg.get('llm', {})
            api_base = llm_cfg.get('api_base', api_base).rstrip('/')
            api_key = llm_cfg.get('api_key', api_key)
            model = llm_cfg.get('br_decompose_model', model)
        except Exception:
            pass
    if not api_key:
        print('      [BR-DECOMPOSE] LLM_API_KEY not set — skipping BR decomposition')
        return {}

    # Build user prompt
    lines = ["请拆解以下业务规则：", ""]
    for i, br in enumerate(brs, 1):
        bid = br.get('constraint_id', br.get('id', f'BR-{i}'))
        desc = br.get('description', '')
        lines.append(f"{i}. ID={bid}")
        lines.append(f"   描述：{desc}")
    user_msg = "\n".join(lines)

    # Call LLM
    import urllib.request as _urllib
    import json as _json
    url = f'{api_base}/chat/completions'
    body = _json.dumps({
        'model': model,
        'messages': [
            {'role': 'system', 'content': _BR_DECOMPOSE_PROMPT},
            {'role': 'user', 'content': user_msg},
        ],
        'temperature': 0.1,
        'max_tokens': len(brs) * 200 + 200,
    }).encode('utf-8')
    req = _urllib.Request(url, data=body, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    })

    try:
        with _urllib.urlopen(req, timeout=180) as resp:
            data = _json.loads(resp.read().decode('utf-8'))
        raw = (data.get('choices') or [{}])[0].get('message', {}).get('content', '')
    except Exception as e:
        print(f'      [BR-DECOMPOSE] LLM call failed: {e}')
        return {}

    # Parse JSONL response
    result: dict[str, list[tuple[str, str]]] = {}
    for line in raw.split('\n'):
        line = line.strip()
        if not line or line.startswith('```'):
            continue
        try:
            obj = _json.loads(line)
            if isinstance(obj, dict) and 'id' in obj and 'atoms' in obj:
                bid = obj['id']
                atoms = obj['atoms']
                if isinstance(atoms, list) and atoms:
                    # Assign sub-labels (a, b, c, ...)
                    if len(atoms) == 1:
                        result[bid] = [(bid, atoms[0])]
                    else:
                        result[bid] = [
                            (f"{bid}{chr(ord('a') + i)}", a)
                            for i, a in enumerate(atoms)
                        ]
        except _json.JSONDecodeError:
            continue
    print(f'      [BR-DECOMPOSE] Decomposed {len(result)}/{len(brs)} BRs')
    return result


def _decompose_br_desc(br_id: str, br_desc: str,
                       llm_cache: dict | None = None) -> list[tuple[str, str]]:
    """Decompose a BR description into atomic assertions.

    Uses LLM cache (populated by _decompose_brs_via_llm at S1 start) if
    available; falls back to single-atom (no decomposition) otherwise.

    The legacy regex-based decomposition (_BR_PREDICATE_MARKERS etc.) has
    been removed — it was domain-specific Chinese keyword matching that
    couldn't be ported to other projects.
    """
    br_desc = (br_desc or '').strip()
    if not br_desc:
        return [(br_id, br_desc)]
    if llm_cache and br_id in llm_cache:
        return llm_cache[br_id]
    # Fallback: no decomposition
    return [(br_id, br_desc)]


# ---------------------------------------------------------------------------
# Type7 — Standalone BR procedures (only for standalone-classified BRs)
# ---------------------------------------------------------------------------

def _generate_type7_standalone(br_classifications: list[dict], state: AgentState,
                               depth_cache: dict | None = None,
                               entity_name_map: dict | None = None,
                               signal_v_steps: dict[str, list[dict]] | None = None) -> list[dict]:
    """Generate standalone Type7 procedures from standalone BRs only.

    When ``signal_v_steps`` is provided, LLM-generated V-steps are used
    in place of the deterministic template decomposition.
    """
    if signal_v_steps is None:
        signal_v_steps = {}
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
        entities_raw = br.get("entities_involved", br.get("entities", ""))
        br_entities = _resolve_entity_names(entities_raw, entity_name_map)
        primary_br_entity = br_entities[0] if br_entities else "E-PRJ"

        tl = topo.get(primary_br_entity, 0)
        phase_res = _resolve_phase_for_non_transition(state, primary_br_entity)
        phase = phase_res["phase"]
        phase_basis = phase_res["basis"]

        br_desc = br.get("description", "")
        enforcement = br.get("enforcement", "mandatory")
        br_category = bc.get("category", "standalone")

        # I11: Category-assisted V step focus
        category_focus = {
            "authorization": "验证权限控制: 无权限者不可操作",
            "computation": "验证计算逻辑: 输入→输出正确",
            "notification": "验证通知触发: 事件产生对应消息",
            "data_integrity": "验证数据约束: 边界值有效, 越界值被拒绝",
            "timing": "验证时间约束: 触发条件满足时生效, 延迟符合预期",
            "validation": "验证数据校验: 条件满足通过, 条件不满足被拒绝",
        }.get(br_category, "")

        # ── BDD clauses ──
        br_id = br.get('constraint_id', '')
        br_signal_type = br.get('signal_type', '')

        givens = [_make_given(
            target=primary_br_entity,
            state="规则适用前提满足",
            description=f"{', '.join(br_entities)}相关数据已准备",
        )]
        when = _make_when(
            target=primary_br_entity,
            event=f"按规则\"{br_desc}\"执行操作事件",
            action=f"按规则\"{br_desc}\"执行操作",
        )
        thens: list[dict] = []

        # Priority 1: LLM-generated signal-aware Thens
        llm_v_steps = signal_v_steps.get(br_id) if signal_v_steps else None
        if llm_v_steps:
            for vs in llm_v_steps:
                # BDD: vs is now a ThenClause dict (target/expectation/kind/br_refs/cross_refs)
                loc = vs.get("target", primary_br_entity)
                exp = vs.get("expectation", "")
                if not exp:
                    continue
                thens.append(_make_then(
                    target=loc,
                    expectation=exp,
                    kind=vs.get("kind", "behavior"),
                    br_refs=[br_id] + vs.get("br_refs", []),
                ))
        else:
            # Priority 2 fallback: deterministic decomposition (方案A)
            atoms = _decompose_br_desc(br_id, br_desc, state.get('br_decomposition', {}))
            if enforcement == "conditional":
                focus_hint = f" ({category_focus})" if category_focus else ""
                for sub_label, assertion in atoms:
                    thens.append(_make_then(
                        target=primary_br_entity,
                        expectation=f"[{sub_label}]正面: {assertion}{focus_hint}",
                        kind="behavior", br_refs=[sub_label],
                    ))
                    thens.append(_make_then(
                        target=primary_br_entity,
                        expectation=f"[{sub_label}]负面: 不满足条件时规则不触发",
                        kind="behavior", br_refs=[sub_label],
                    ))
            else:
                for sub_label, assertion in atoms:
                    thens.append(_make_then(
                        target=primary_br_entity,
                        expectation=f"[{sub_label}] {assertion}",
                        kind="behavior", br_refs=[sub_label],
                    ))

        # Try to find associated transition for chain depth
        chain_depth = 0
        for to in tos:
            if br_entities and to["entity"] in br_entities:
                t_depth = depth_cache.get(to.get("transition_id", ""), 0) if depth_cache else 0
                chain_depth = max(chain_depth, t_depth)

        proc = {
            "temp_id": f"PROC-T7-{_next_gen_seq()}",
            "source_ids": [br.get("id", br.get("constraint_id", ""))],
            "entity": primary_br_entity,
            "dimension": None,
            "obligation_type": 8,
            "risk_trait": "",
            "givens": givens,
            "when": when,
            "thens": thens,
            "operation_hints": [],
            "gen_seq": _gen_seq_counter,
            "post_state": f"{primary_br_entity}→(规则验证完成)",
            "cascade_chain": None,
            "embedded_brs": [],
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
# Type9 — Field Validation procedures (independent BDD scenarios)
# ---------------------------------------------------------------------------

def _generate_type9_field_validation(
    state: AgentState, indices: dict, depth_cache: dict
) -> list[dict]:
    """Generate independent Type9 procedures for field-level validation.

    Each entity that has field-validation constraints (boundary, format, etc.)
    gets ONE Type9 procedure.  This keeps Type1/3/5 procedures clean — they
    only describe the primary business behaviour (state transition / config /
    CRUD), while field validation becomes its own BDD scenario.

    BDD structure:
        Given: 实体处于可编辑状态（如"实验室信息录入页面"）
        When:  提交含违规值的表单
        Then:  [多个字段校验失败的可观察结果]
    """
    phase_table = state["phase_table"]
    topo = state["topology_levels"]
    dep_map = state["dep_state_phase_map"]
    primary = state["primary_entity"]
    ves = state.get("virtual_entities", {})
    constraint_steps = indices.get("constraint_steps", {})

    if not constraint_steps:
        return []

    procedures: list[dict] = []

    for entity_id, field_thens in constraint_steps.items():
        if not field_thens:
            continue

        # Resolve phase for this entity (same logic as Type5)
        tl = topo.get(entity_id, 0)
        phase = 0
        phase_basis = ""
        if entity_id == primary:
            primary_dim_map = phase_table["state_to_phase"].get(
                phase_table.get("primary_dimension", ""), {}
            )
            if primary_dim_map:
                first_phase = next(iter(primary_dim_map.values()), 0)
                phase = first_phase if first_phase is not None else 0
                phase_basis = f"phase_table.{phase_table.get('primary_dimension', '')}"
        elif entity_id in dep_map:
            first_dim = next(iter(dep_map[entity_id].values()), None)
            if first_dim:
                phase = min(first_dim.values())
                phase_basis = f"dep_state_phase_map.{entity_id}.min_phase"
            else:
                phase_res = _resolve_phase_for_non_transition(state, entity_id)
                phase = phase_res["phase"]
                phase_basis = phase_res["basis"]
        elif entity_id in ves:
            phase = ves[entity_id].get("resolved_phase", 0)
            phase_basis = f"VE.{entity_id}.resolved_phase"
        else:
            phase_res = _resolve_phase_for_non_transition(state, entity_id)
            phase = phase_res["phase"]
            phase_basis = phase_res["basis"]

        phase_name = (phase_table.get("phase_names", ["P0"])[phase]
                      if phase < len(phase_table.get("phase_names", []))
                      else f"P{phase}")

        # Build BDD clauses
        givens = [_make_given(
            target=entity_id,
            state="可编辑",
            description=f"{entity_id}信息录入页面已打开",
        )]
        when = _make_when(
            target=entity_id,
            event=f"提交含违规值的{entity_id}表单",
            actor="操作员",
            action="提交含违规值的表单",
        )
        # Thens: all field-validation ThenClauses for this entity
        thens = list(field_thens)

        # Operation hint: navigate to the entity's edit page
        op_hints = [f"导航至{entity_id}新增/编辑页面"]

        proc = {
            "temp_id": f"PROC-T9-{_next_gen_seq()}",
            "source_ids": [f"FIELD-VAL-{entity_id}"],
            "entity": entity_id,
            "dimension": None,
            "obligation_type": 9,  # Type9 = field_validation
            "risk_trait": "field_validation",
            "givens": givens,
            "when": when,
            "thens": thens,
            "operation_hints": op_hints,
            "gen_seq": _gen_seq_counter,
            "post_state": f"{entity_id}→(校验失败，表单未提交)",
            "cascade_chain": None,
            "embedded_brs": [],
            "_S2_fields": {
                "phase": phase,
                "phase_name": phase_name,
                "phase_basis": phase_basis or f"field_validation.{entity_id}",
                "topology_level": tl,
                "sort_key": [],
                "operation_lifecycle": 2,  # 2=修改 (edit-form validation)
                "chain_depth": 0,
                "type_label": "field_validation",
                "type_priority": 5,  # same as crud
                "dimension_priority": 1,
                "context": None,
            },
            "_S3_fields": {"dependencies": [], "weak_dependencies": []},
            "_S4_fields": {"multi_instance": False, "multi_count": 1, "multi_reason": ""},
        }
        procedures.append(proc)

    return procedures

def _embed_brs(procedures: list[dict], br_classifications: list[dict],
               state: AgentState, entity_name_map: dict | None = None,
               signal_v_steps: dict[str, list[dict]] | None = None) -> list[dict]:
    """Embed non-standalone BRs into host procedures as V steps.

    When ``signal_v_steps`` is provided, LLM-generated V-steps replace the
    deterministic template decomposition for embedded BR V-steps.
    """
    dep_map = state["dep_state_phase_map"]
    topo = state["topology_levels"]
    phase_table = state["phase_table"]
    warnings = list(state.get("warnings", []))
    total_embedded = 0

    if signal_v_steps is None:
        signal_v_steps = {}

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
            entities_raw = br.get("entities_involved", br.get("entities", ""))
            br_entities = _resolve_entity_names(entities_raw, entity_name_map)
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
                    "givens": [_make_given(
                        target=primary_br_entity,
                        state="规则适用前提满足",
                        description=f"{prohibited}相关数据已准备",
                    )],
                    "when": _make_when(
                        target=primary_br_entity,
                        event="尝试违反规则操作事件",
                        action="尝试违反规则操作",
                    ),
                    "thens": [_make_then(
                        target=primary_br_entity,
                        expectation=br_desc,
                        kind="prompt",
                        br_refs=[br_id],
                    )],
                    "operation_hints": [],
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{primary_br_entity}→(操作被阻止)",
                    "cascade_chain": None,
                    "embedded_brs": [],
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

        # Embed Thens into host procedures
        # Priority 1: LLM-generated signal-aware Thens
        # Priority 2: deterministic decomposition fallback (方案A)
        for proc in host_procs:
            entity = proc["entity"]
            dimension = proc.get("dimension") or ""
            loc = f"{entity}.{dimension}" if dimension else entity
            entities_raw = br.get("entities_involved", br.get("entities", ""))
            br_entities = _resolve_entity_names(entities_raw, entity_name_map)
            cross_refs = [e for e in br_entities if e != entity] if len(br_entities) > 1 else []

            llm_v_steps = signal_v_steps.get(br_id) if signal_v_steps else None
            if llm_v_steps:
                for vs in llm_v_steps:
                    # BDD: vs is now a ThenClause dict
                    vs_loc = vs.get("target", loc)
                    vs_exp = vs.get("expectation", "")
                    if not vs_exp:
                        continue
                    proc["thens"].append(_make_then(
                        target=vs_loc,
                        expectation=vs_exp,
                        kind=vs.get("kind", "behavior"),
                        br_refs=[br_id] + vs.get("br_refs", []),
                        cross_refs=cross_refs,
                    ))
            elif enforcement == "conditional":
                atoms = _decompose_br_desc(br_id, br_desc, state.get('br_decomposition', {}))
                for sub_label, assertion in atoms:
                    proc["thens"].append(_make_then(
                        target=loc,
                        expectation=f"[{sub_label}]正面: {assertion}",
                        kind="behavior", br_refs=[sub_label], cross_refs=cross_refs,
                    ))
                    proc["thens"].append(_make_then(
                        target=loc,
                        expectation=f"[{sub_label}]负面: 不满足条件时规则不触发",
                        kind="behavior", br_refs=[sub_label], cross_refs=cross_refs,
                    ))
            else:
                atoms = _decompose_br_desc(br_id, br_desc, state.get('br_decomposition', {}))
                for sub_label, assertion in atoms:
                    proc["thens"].append(_make_then(
                        target=loc,
                        expectation=f"[{sub_label}] {assertion}",
                        kind="behavior", br_refs=[sub_label], cross_refs=cross_refs,
                    ))
            proc.setdefault("embedded_brs", []).append(br_id)
            total_embedded += 1

    return procedures


# ---------------------------------------------------------------------------
# S1.10 Procedure Dedup (I24)
# ---------------------------------------------------------------------------

def _dedup_procedures(procedures: list[dict], cos: list[dict], warnings: list[str]) -> list[dict]:
    """S1.10: Deduplicate procedures — BDD-aware merge.

    Compares procedures by their BDD structure:
    - Action similarity: based on ``when.action`` (not ``steps[1].input``)
    - From-state: extracted from ``givens[0].state`` (not S step input parsing)
    - Merge: secondary's Thens appended to primary's thens (deduped by expectation)

    Generic design — NO hardcoded business keywords:
    Two procedures are considered "complete duplicates" (Branch A) iff ALL of:
      1. same entity + same dimension
      2. same post_state (same from→to transition)
      3. same branch Givens (same branch scenario)
      4. normalized action text equal (whitespace/punctuation-insensitive)
    No keyword list — works for any business domain.
    """
    co_map = {}
    for co in cos:
        co_map.setdefault(co.get('enabler_entity', ''), []).append(co)
        co_map.setdefault(co.get('dependent_entity', ''), []).append(co)

    to_remove: set[str] = set()

    def _normalize_action(action: str) -> str:
        """Normalize action text for comparison: strip whitespace, punctuation,
        and branch suffixes.  No keyword matching — pure text normalization."""
        if not action:
            return ""
        # Strip branch suffixes like [项目类型=能力验证]
        cleaned = _strip_branch_suffix(action)
        # Remove all whitespace and common CJK/ASCII punctuation
        cleaned = re.sub(r'[\s\u3000，。、；：！？""''（）()【】《》〈〉…—_\\/]', '', cleaned)
        return cleaned.lower()

    def _branch_givens(p: dict) -> set[tuple]:
        """Extract branch-condition Givens as a comparable set."""
        return {
            (g.get("target", ""), g.get("state", ""))
            for g in p.get("givens", [])
            if "分支条件" in g.get("description", "")
        }

    for i, p1 in enumerate(procedures):
        if p1["temp_id"] in to_remove:
            continue
        for j in range(i + 1, len(procedures)):
            p2 = procedures[j]
            if p2["temp_id"] in to_remove:
                continue

            same_entity = p1["entity"] == p2["entity"]
            same_dim = p1.get("dimension") == p2.get("dimension")

            # BDD: branch-split procedures must NOT be merged
            if _branch_givens(p1) != _branch_givens(p2):
                continue

            # Generic action similarity: normalized text equality (no keywords)
            action1_norm = _normalize_action(p1.get("when", {}).get("action", ""))
            action2_norm = _normalize_action(p2.get("when", {}).get("action", ""))
            similar_action = bool(action1_norm) and action1_norm == action2_norm

            # ── Branch A: complete duplicate ──
            # Same entity + same dim + same post_state + same branch + same normalized action
            if (same_entity and same_dim and similar_action
                    and p1["post_state"] == p2["post_state"]):
                if len(p1.get("thens", [])) >= len(p2.get("thens", [])):
                    p1["source_ids"] = list(set(p1.get("source_ids", []) + p2.get("source_ids", [])))
                    to_remove.add(p2["temp_id"])
                    warnings.append(f"DEDUP: {p2['temp_id']} merged into {p1['temp_id']} (reason: 完全重复)")
                else:
                    p2["source_ids"] = list(set(p2.get("source_ids", []) + p1.get("source_ids", [])))
                    to_remove.add(p1["temp_id"])
                    warnings.append(f"DEDUP: {p1['temp_id']} merged into {p2['temp_id']} (reason: 完全重复)")
                continue

            # ── Branch B: same-entity causal merge ──
            if same_entity and similar_action and p1["post_state"] != p2["post_state"]:
                # BDD: extract from_state from givens[0].state directly
                p1_from = p1.get("givens", [{}])[0].get("state", "") if p1.get("givens") else ""
                p2_from = p2.get("givens", [{}])[0].get("state", "") if p2.get("givens") else ""
                if p1_from and p2_from and p1_from != p2_from:
                    continue
                p1_phase = p1.get('_S2_fields', {}).get('phase')
                p2_phase = p2.get('_S2_fields', {}).get('phase')
                if p1_phase is not None and p2_phase is not None and p1_phase != p2_phase:
                    continue

                p1_co_linked = any(
                    any(sid == co.get('enabler_transition_id') or sid == co.get('dependent_transition_id')
                        for co in cos if co.get('enabler_entity') == p1['entity'] or co.get('dependent_entity') == p1['entity'])
                    for sid in p1.get('source_ids', [])
                )
                p2_co_linked = any(
                    any(sid == co.get('enabler_transition_id') or sid == co.get('dependent_transition_id')
                        for co in cos if co.get('enabler_entity') == p2['entity'] or co.get('dependent_entity') == p2['entity'])
                    for sid in p2.get('source_ids', [])
                )
                if p1_co_linked and p2_co_linked:
                    primary_proc = p1 if p1["obligation_type"] <= p2["obligation_type"] else p2
                    secondary_proc = p2 if primary_proc is p1 else p1
                    # BDD: merge thens (dedupe by expectation text)
                    existing_exp = {t.get("expectation") for t in primary_proc.get("thens", [])}
                    for then in secondary_proc.get("thens", []):
                        if then.get("expectation") not in existing_exp:
                            primary_proc["thens"].append(then)
                            existing_exp.add(then.get("expectation"))
                    primary_proc["source_ids"] = list(set(primary_proc.get("source_ids", []) + secondary_proc.get("source_ids", [])))
                    to_remove.add(secondary_proc["temp_id"])
                    warnings.append(f"DEDUP: {secondary_proc['temp_id']} merged into {primary_proc['temp_id']} (reason: 同实体因果合并)")
                    continue

            # ── Branch C: cross-entity causal merge ──
            if not same_entity and similar_action:
                has_co = any(
                    co.get('enabler_entity') == p1['entity'] and co.get('dependent_entity') == p2['entity']
                    or co.get('enabler_entity') == p2['entity'] and co.get('dependent_entity') == p1['entity']
                    for co in co_map.get(p1['entity'], []) + co_map.get(p2['entity'], [])
                )
                p1_ph = p1.get('_S2_fields', {}).get('phase')
                p2_ph = p2.get('_S2_fields', {}).get('phase')
                if has_co and p1_ph is not None and p2_ph is not None and p1_ph == p2_ph:
                    primary_proc = p1 if p1["obligation_type"] <= p2["obligation_type"] else p2
                    secondary_proc = p2 if primary_proc is p1 else p1
                    existing_exp = {t.get("expectation") for t in primary_proc.get("thens", [])}
                    for then in secondary_proc.get("thens", []):
                        if then.get("expectation") not in existing_exp:
                            primary_proc["thens"].append(then)
                            existing_exp.add(then.get("expectation"))
                    primary_proc["source_ids"] = list(set(primary_proc.get("source_ids", []) + secondary_proc.get("source_ids", [])))
                    to_remove.add(secondary_proc["temp_id"])
                    warnings.append(f"DEDUP: {secondary_proc['temp_id']} merged into {primary_proc['temp_id']} (reason: 因果合并)")
                    continue

    return [p for p in procedures if p["temp_id"] not in to_remove]


# ---------------------------------------------------------------------------
# LLM-based action classification (replaces HUMAN_DECISION_KEYWORDS)
# ---------------------------------------------------------------------------

_ACTION_CLASSIFY_PROMPT = """你是一个业务动作分类器。判断每个动作是"人工决策"还是"系统自动"。

## 分类标准
- **human**（人工决策）：动作需要人工判断/审批/确认/操作。如审核、审批、确认、签订、发布、驳回、退回、收款、付款、发样、收样、核验、撤销等需要人参与的动作。
- **system**（系统自动）：动作由系统自动执行。如初始化、创建、自动同步、驱动、触发条件、状态推进等无需人工干预的动作。

## 输出格式（JSONL，每行一个）
{"action":"动作文本","type":"human或system"}

只输出 JSONL，不要额外说明。"""


def _classify_actions_via_llm(actions: list[str]) -> dict[str, str]:
    """Classify a list of action texts as 'human' or 'system' via LLM.

    Returns ``{action_text: "human"|"system"}`` dict.
    On failure (no API key, LLM error), returns empty dict — callers
    fall back to treating all actions as 'system' (safe default).
    """
    if not actions:
        return {}
    # Dedupe
    unique = list(set(a for a in actions if a and a.strip()))
    if not unique:
        return {}

    # Load API config
    import os as _os
    api_base = _os.environ.get('LLM_API_BASE', 'https://open.bigmodel.cn/api/paas/v4').rstrip('/')
    api_key = _os.environ.get('LLM_API_KEY', '')
    model = _os.environ.get('LLM_ACTION_CLS_MODEL', 'glm-4-flash')
    if not api_key:
        cfg_path = _os.path.join(_os.path.dirname(__file__), '..', 'config.json')
        try:
            import json as _json
            with open(cfg_path) as f:
                cfg = _json.load(f)
            llm_cfg = cfg.get('llm', {})
            api_base = llm_cfg.get('api_base', api_base).rstrip('/')
            api_key = llm_cfg.get('api_key', api_key)
            model = llm_cfg.get('action_cls_model', model)
        except Exception:
            pass
    if not api_key:
        print('      [ACTION-CLS] LLM_API_KEY not set — skipping action classification')
        return {}

    # Build user prompt
    lines = ["请对以下动作逐一分类：", ""]
    for i, a in enumerate(unique, 1):
        lines.append(f"{i}. {a}")
    user_msg = "\n".join(lines)

    # Call LLM
    import urllib.request as _urllib
    import urllib.error as _urlerr
    import json as _json
    url = f'{api_base}/chat/completions'
    body = _json.dumps({
        'model': model,
        'messages': [
            {'role': 'system', 'content': _ACTION_CLASSIFY_PROMPT},
            {'role': 'user', 'content': user_msg},
        ],
        'temperature': 0.1,
        'max_tokens': len(unique) * 60 + 200,
    }).encode('utf-8')
    req = _urllib.Request(url, data=body, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    })

    try:
        with _urllib.urlopen(req, timeout=120) as resp:
            data = _json.loads(resp.read().decode('utf-8'))
        raw = (data.get('choices') or [{}])[0].get('message', {}).get('content', '')
    except Exception as e:
        print(f'      [ACTION-CLS] LLM call failed: {e}')
        return {}

    # Parse JSONL response
    result: dict[str, str] = {}
    for line in raw.split('\n'):
        line = line.strip()
        if not line or line.startswith('```'):
            continue
        try:
            obj = _json.loads(line)
            if isinstance(obj, dict) and 'action' in obj and 'type' in obj:
                a = obj['action']
                t = obj['type']
                if t in ('human', 'system'):
                    result[a] = t
        except _json.JSONDecodeError:
            continue
    print(f'      [ACTION-CLS] Classified {len(result)}/{len(unique)} actions')
    return result


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

    # ── LLM-based action classification (replaces HUMAN_DECISION_KEYWORDS) ──
    # Collect all unique action texts from TOs and classify them once.
    # Result is cached in state['action_classification'] and read by
    # _get_role_name for I21 role resolution.
    if 'action_classification' not in state:
        all_actions = [to.get('action', '') for to in tos if to.get('action')]
        # Also include CO triggers and suggested_actions
        for co in cos:
            if co.get('trigger'):
                all_actions.append(co['trigger'])
            if co.get('suggested_action'):
                all_actions.append(co['suggested_action'])
        action_cls = _classify_actions_via_llm(all_actions)
        state['action_classification'] = action_cls
        if action_cls:
            warnings.append(f"S1 action classification: {len(action_cls)} actions classified via LLM")
        else:
            warnings.append("S1 action classification: LLM unavailable, all actions treated as 'system'")

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

    # Build dynamic maps from coverage_model._context
    entity_name_map = _build_entity_name_map(cm)

    # Parse field-level validation constraint steps from entity_details
    entity_details = cm.get("_context", {}).get("entity_details", [])
    constraint_steps = parse_entity_constraints(entity_details)

    indices = {
        "eo_by_type": eo_by_type,
        "to_by_entity": to_by_entity,
        "co_constraint": co_constraint,
        "co_lifecycle": co_lifecycle,
        "ro_by_type": ro_by_type,
        "cfg_eo_to_bd": cfg_eo_to_bd,
        "entity_name_map": entity_name_map,
        "constraint_steps": constraint_steps,
    }

    # Calculate chain depths
    from tools.graph_algo import calc_all_chain_depths
    depth_cache = calc_all_chain_depths(state["transition_upstream_map"])

    # Generate procedures by type
    # BDD: Type4a/4b (constraint/lifecycle CO) are NO LONGER generated as
    # independent procedures.  CO's enabler and dependent state transitions
    # are already covered by Type1 procedures.  Type4a/4b were redundant —
    # their own Then said "此条件已在T-XXX前置条件中体现".
    # CO is now used ONLY for dependency ordering in S3 (not for generation).
    procedures: list[dict] = []
    procedures.extend(_generate_type1(state, indices, depth_cache))
    procedures.extend(_generate_type3(state, indices, depth_cache))
    procedures.extend(_generate_type5(state, indices))
    procedures.extend(_generate_type6(state, indices, depth_cache))
    # BDD: field_validation as independent Type9 procedures (not injected into Type1/3/5)
    procedures.extend(_generate_type9_field_validation(state, indices, depth_cache))

    # BR classification and embedding
    br_classifications = _classify_business_rules(state, indices)

    # ── LLM-based BR decomposition (replaces _BR_PREDICATE_MARKERS) ──
    # Decompose all business_rule ROs into atomic assertions once, cache
    # the result for Type7 generation and BR embedding.
    br_list = ro_by_type.get("business_rule", [])
    if 'br_decomposition' not in state:
        br_decomp = _decompose_brs_via_llm(br_list)
        state['br_decomposition'] = br_decomp
        if br_decomp:
            warnings.append(f"S1 BR decomposition: {len(br_decomp)} BRs decomposed via LLM")
        else:
            warnings.append("S1 BR decomposition: LLM unavailable, BRs not decomposed")

    # ── Signal-type-driven V-step generation via LLM ──────────────────────
    # TODO: 注释LLM验证步骤生成,聚焦排序正确性验证
    # signal_v_steps = generate_signal_v_steps(ros, entity_name_map)
    signal_v_steps = {}

    # Type7 standalone — pass signal_v_steps for LLM-enriched V-steps
    procedures.extend(_generate_type7_standalone(
        br_classifications, state, depth_cache, entity_name_map, signal_v_steps
    ))

    # BR embedding (non-standalone → V steps in host procedures)
    procedures = _embed_brs(procedures, br_classifications, state, entity_name_map, signal_v_steps)

    # S1.10 Dedup (I24)
    procedures = _dedup_procedures(procedures, cos, warnings)

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
    embedded_brs_count = sum(len(p.get("embedded_brs", [])) for p in procedures)

    warnings.append(f"S1 summary: standalone_type7={standalone_count}, embedded_brs={embedded_brs_count}, type5_filtered={len(type5_filtered)}")

    return {
        # BUGFIX #26: removed dead `hasattr(p, 'model_dump')` branch —
        # validate_procedures always returns Pydantic Procedure models.
        "procedures": [p.model_dump(by_alias=True) for p in valid_procs],
        "br_classifications": br_classifications,
        "type5_filtered": type5_filtered,
        "gen_seq_counter": _gen_seq_counter,
        "warnings": warnings,
        "errors": errors,
        "current_stage": "s1",
    }