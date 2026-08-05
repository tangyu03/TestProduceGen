"""S2 Phase Assignment & Metadata Node.

Deterministic phase resolution and sort-key computation, faithfully
replicating the V2 JS engine's S2 stage.

IMPORTANT: This node does NOT sort procedures or assign final IDs.
Sorting and ID assignment happen at the end of S3 (dependency binding),
after the complete dependency graph is known. The sort_key computed here
serves as the tiebreaker within topological levels during final ordering.
"""
import copy
from typing import Any
from models.state import AgentState


def _entity_order_rank(cm: dict, topology_levels: dict, dependency_depth: dict) -> dict:
    """Entity ordering rank: 基础数据 → 主业务流 → 系统配置(尾部).

    Robust, domain-agnostic (C1):
      - 系统配置 tail: entities with NO state machine, NO transitions, and NOT
        composed into a core entity → 角色/日志/超时/分数限值 sort LAST.
      - Everything else orders by S0's topology_level (base data L0 before flow
        L1/L2), then dependency_depth (upstream before downstream).

    Returns a dict keyed by entity id AND Chinese name → rank.
    """
    ctx = cm.get("_context", {})
    details = ctx.get("entity_details", []) or []
    relations = ctx.get("structural_relations", []) or []
    state_info = ctx.get("state_info", {}) or {}
    to_entities = {t.get("entity") for t in cm.get("transition_obligations", []) or []}

    # config/audit tail: no state machine + no transitions + NO incoming
    # structural reference (provides configuration outward; never referenced as
    # a flow subject — unlike base reference data like 专家, which the flow
    # references via E-ORG→E-EXP / E-PLAN→E-EXP).
    incoming = {r.get("to") for r in relations if r.get("to")}
    config_ids = set()
    for ed in details:
        eid = ed.get("id", "")
        ndim = len(state_info.get(eid, {}).get("dimensions", []) or [])
        if ndim == 0 and eid not in to_entities and eid not in incoming:
            config_ids.add(eid)

    rank = {}
    # Non-config: topology_level first, then a multi-dimensional state machine
    # leads its level (the entity with the richest lifecycle is the flow lead —
    # e.g. 项目 has 项目状态+项目阶段, so it leads 评审计划), then dependency_depth.
    non_config = [ed.get("id") for ed in details if ed.get("id") and ed.get("id") not in config_ids]
    scored = []
    for eid in non_config:
        tl = topology_levels.get(eid, 9)
        ndim = len(state_info.get(eid, {}).get("dimensions", []) or [])
        dims_lead = 0 if ndim >= 2 else 100  # multi-dim entity leads its level
        dd = dependency_depth.get(eid, 9)
        scored.append((tl, dims_lead, dd, eid))
    scored.sort()
    for i, (_, _, _, eid) in enumerate(scored):
        rank[eid] = i
    # config tail after all flow entities
    off = len(scored)
    for i, eid in enumerate([ed.get("id") for ed in details if ed.get("id") in config_ids]):
        rank[eid] = off + 10 + i

    # procedures may reference entities by Chinese name — map both
    for ed in details:
        if ed.get("name"):
            rank[ed["name"]] = rank.get(ed.get("id"), 900)
    return rank


def s2_sorting_node(state: AgentState) -> dict:
    """S2: Assign phases and compute sort_key metadata.

    1. Resolves any remaining contextual phase rules (P4-ctx) by expanding procedures
    2. Ensures all phases are non-null (fallback = 0)
    3. Sets phase_name from phase_table
    4. Computes sort_key = [phase, type_priority, entity_entry_phase, entity,
       dimension, chain_depth, topology_level, operation_lifecycle,
       dimension_priority, gen_seq]

    Final sorting (topological by dependencies, sort_key as tiebreaker)
    and sequential ID assignment happen in S3 after all dependencies are bound.
    """
    procedures = list(state.get("procedures", []))
    warnings = list(state.get("warnings", []))
    phase_table = state.get("phase_table", {})
    ctx_rules = state.get("contextual_phase_rules", {})
    upstream_map = state.get("transition_upstream_map", {})
    dep_state_phase_map = state.get("dep_state_phase_map", {})
    entity_parent = state.get("entity_parent", {})

    # ── Resolve any unresolved contextual phase rules ──
    procs_to_remove: list[str] = []
    procs_to_add: list[dict] = []

    for proc in procedures:
        s2 = proc.get("_S2_fields", {})
        if s2.get("phase_basis") == "contextual":
            # BUGFIX: previously read s2.get("context") — but "context" stores
            # the VE human-readable description (e.g. "归属E-REG"), not the
            # contextual_phase_rules key (e.g. "E-EVAL.状态").  Use the
            # "contextual" field which is set in s1_generation._resolve_phase
            # for that purpose.  Fall back to entity.dimension if missing.
            ctx_key = s2.get("contextual") or f"{proc['entity']}.{proc.get('dimension', '')}"
            if ctx_key in ctx_rules:
                rule_set = ctx_rules[ctx_key]
                procs_to_remove.append(proc["temp_id"])

                for rule in rule_set.get("rules", []):
                    expanded = copy.deepcopy(proc)
                    expanded["temp_id"] = f"{proc['temp_id']}-{rule.get('context', '')}"
                    resolved_phase = rule.get("resolved_phase", 0)
                    expanded["_S2_fields"]["phase"] = resolved_phase
                    expanded["_S2_fields"]["phase_name"] = (
                        phase_table.get("phase_names", ["P0"])[resolved_phase]
                        if resolved_phase < len(phase_table.get("phase_names", []))
                        else f"P{resolved_phase}"
                    )
                    expanded["_S2_fields"]["phase_basis"] = f"contextual.{rule.get('context', '')}"
                    expanded["_S2_fields"]["context"] = rule.get("context")

                    # BDD: annotate the first Given's description with the context label
                    # (was: steps[0]["input"] prefix in the legacy AAA model)
                    if expanded.get("givens"):
                        ctx = rule.get('context', '')
                        if ctx:
                            expanded["givens"][0]["description"] = (
                                f"[{ctx}] {expanded['givens'][0].get('description', '')}"
                            )

                    procs_to_add.append(expanded)
            else:
                # No rule found — try upstream anchoring fallback
                # NOTE: although S1 normally sets phase=0 when phase_info["phase"]
                # is None (so the `s2.get("phase") is None` check is mostly
                # defensive), keep this branch in case S1's contract changes.
                resolved = False
                if s2.get("phase") is None:
                    parent = entity_parent.get(proc["entity"])
                    if parent and parent in dep_state_phase_map:
                        all_phases = [
                            p for dm in dep_state_phase_map[parent].values()
                            for p in dm.values()
                        ]
                        if all_phases:
                            s2["phase"] = min(all_phases)
                            s2["phase_basis"] = f"P4-ctx fallback: anchor {parent} min phase"
                            resolved = True

                if not resolved and s2.get("phase") is None:
                    s2["phase"] = 0
                    s2["phase_basis"] = "contextual_fallback_default"

    # Remove expanded originals, add expansions
    if procs_to_remove:
        procedures = [p for p in procedures if p["temp_id"] not in procs_to_remove]
        procedures.extend(procs_to_add)

    # ── Finalise S2 fields and compute sort_key ──
    # Compute entity_entry_phase: the minimum phase across all states
    # in dep_state_phase_map for each entity.  This reflects when the
    # entity enters the business timeline — entities with earlier
    # entry_phase started their business flow earlier and should sort
    # before entities with later entry_phase within the same procedure phase.
    dep_map = state.get("dep_state_phase_map", {})
    entity_entry_phases: dict[str, int] = {}
    for ent, dim_maps in dep_map.items():
        all_phases = [p for dm in dim_maps.values() for p in dm.values()]
        if all_phases:
            entity_entry_phases[ent] = min(all_phases)
    # Primary entity's entry_phase = 0 (it defines the phase scale)
    primary_entity = state.get("primary_entity", "")
    if primary_entity:
        entity_entry_phases[primary_entity] = 0

    # v29 #16: topology_levels for sort_key
    # L0 entities (基础数据维护: 标准库/实验室/子领域) should sort BEFORE
    # L1 entities (主业务: 项目/报名记录) within the same phase.
    # This ensures base-data maintenance procedures (e.g. 启用标准库, 启用实验室)
    # are tested BEFORE project-creation procedures, matching the business
    # intuition that base data must exist before projects can reference it.
    topology_levels = state.get("topology_levels", {})
    dependency_depth = state.get("dependency_depth", {})

    # Build reverse map: entity_id → entity name (as appears in proc.entity)
    # S1 may translate entity IDs to Chinese names; we need both forms.
    entity_name_map: dict[str, str] = {}
    cm = state.get("coverage_model", {})
    for ed in cm.get("_context", {}).get("entity_details", []):
        eid = ed.get("id", "")
        ename = ed.get("name", "")
        if eid and ename:
            entity_name_map[eid] = ename
            entity_name_map[ename] = eid  # bidirectional

    # Fix B/C1: entity dependency order (基础数据 → 主业务流 → 系统配置尾部).
    # Replaces the old string/topology-level entity tiebreak: entities order by
    # S0 topology_level + dependency_depth (upstream before downstream), with
    # pure config/audit entities (分数限值/日志/角色/超时) sorted last.
    entity_order_rank = _entity_order_rank(cm, topology_levels, dependency_depth)

    def _topo_level_for_entity(ent_name_or_id: str) -> int:
        """Look up topology_level by entity name or ID."""
        if not ent_name_or_id:
            return 9  # unknown → sort last
        tl = topology_levels.get(ent_name_or_id)
        if tl is not None:
            return tl
        # Try reverse lookup (name → id → level)
        eid = entity_name_map.get(ent_name_or_id, "")
        if eid:
            tl = topology_levels.get(eid)
            if tl is not None:
                return tl
        return 9  # unknown → sort last

    for proc in procedures:
        s2 = proc.get("_S2_fields", {})

        # Ensure phase is non-null and phase_basis is non-empty (I5)
        if s2.get("phase") is None:
            tl = s2.get("topology_level", 0)
            if tl == 0:
                s2["phase"] = 0
                s2["phase_basis"] = s2.get("phase_basis") or "P6: topology_level L0 → P0"
            else:
                s2["phase"] = 0
                s2["phase_basis"] = s2.get("phase_basis") or "fallback"

        # I5: Ensure phase_basis is never empty
        if not s2.get("phase_basis"):
            s2["phase_basis"] = f"fallback: entity={proc['entity']} phase={s2['phase']}"

        # Set phase_name
        phase_names = phase_table.get("phase_names", [])
        phase = s2["phase"]
        s2["phase_name"] = phase_names[phase] if phase < len(phase_names) else f"P{phase}"

        # Build sort_key — 8-dimensional (v29 #16: +topology_level):
        # [phase, topology_level, entity_entry_phase, entity, dimension,
        #  obligation_type, dimension_priority, gen_seq]
        #
        # v29 #16: added topology_level as the 2nd dimension.
        # - L0 entities (基础数据维护: 标准库/实验室/子领域) sort BEFORE
        #   L1 entities (主业务: 项目/报名记录) within the same phase.
        # - This ensures base-data maintenance procedures are tested BEFORE
        #   project-creation procedures, matching business intuition.
        #
        # Removed (redundant with dependency DAG):
        # - chain_depth       : derived from transition_upstream_map, which is
        #                       already a hard constraint in S3 Kahn sort.
        # - operation_lifecycle: same-entity same-dim CREATE→UPDATE→DELETE is
        #                       covered by Guard 5; cross-dim has no business
        #                       necessity. Type7/8/9 vs Type1 separation is
        #                       already captured by obligation_type.
        # - type_priority     : fragmented same-type procedures into different
        #                       sort groups, breaking causal chains within a dim.
        #
        # sort_key is ONLY a tiebreaker among procedures at the same
        # topological level (whose deps are all satisfied). It must NOT
        # duplicate what the DAG already enforces.
        ot = proc.get("obligation_type", 0)

        proc_entity = proc.get("entity", "") or ""
        # Fix B/C1: entity dependency order (基础数据 → 主业务流 → 系统配置尾部).
        # Replaces topology_level + entity_entry_phase + entity-string keys.
        ent_rank = entity_order_rank.get(proc_entity, 900)

        # Dimension: empty dimension (T6 invalid / T7 rule / T9 field-validation)
        # sorts AFTER all real dimensions within the same entity+phase, so
        # "create main flow" (T1 with dimension) precedes "invalid delete" (T6
        # without dimension). Using a high sentinel string achieves this
        # without affecting real dimensions (any CJK str < '\uffff').
        raw_dim = proc.get("dimension", "") or ""
        dim_sort = raw_dim if raw_dim else "\uffff"

        s2["sort_key"] = [
            s2.get("phase", 0),
            ent_rank,  # entity dependency order (base data → main flow → config tail)
            dim_sort,
            ot,  # obligation_type: 1-7 primary, 8-9 auxiliary
            s2.get("dimension_priority", 1),
            proc.get("gen_seq", 0),
        ]

    warnings.append(
        f"S2 computed sort_key metadata for {len(procedures)} procedures "
        f"(final topological sort + ID assignment deferred to S3)"
    )

    return {
        "procedures": procedures,
        "sorted_procedures": procedures,
        "warnings": warnings,
        "current_stage": "s2",
    }