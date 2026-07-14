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


def s2_sorting_node(state: AgentState) -> dict:
    """S2: Assign phases and compute sort_key metadata.

    1. Resolves any remaining contextual phase rules (P4-ctx) by expanding procedures
    2. Ensures all phases are non-null (fallback = 0)
    3. Sets phase_name from phase_table
    4. Computes sort_key = [phase, topology_level, flow_layer, type_priority,
       operation_lifecycle, chain_depth, dimension_priority, gen_seq]

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

        # Build sort_key — 7-dimensional:
        # [phase, type_priority, chain_depth, topology_level,
        #  operation_lifecycle, dimension_priority, gen_seq]
        #
        # Dimension order is derived from first principles:
        # 1. phase — macro business timeline (报名 before 发样 before 归档)
        # 2. type_priority — primary flow (1-4) before auxiliary (5-6):
        #    separates the two semantic spaces so T7/8/9 chain_depth doesn't
        #    interleave with T1 chain_depth
        # 3. chain_depth — causal chain depth within same type group
        # 4. topology_level — entity hierarchy (primary before dependent)
        # 5. operation_lifecycle — create(1) < modify(2) < transition(3) < terminate(4)
        # 6. dimension_priority — primary dimension(0) before secondary(1)
        # 7. gen_seq — stable tiebreaker
        #
        # Type7/8/9 have op_lifecycle=0 (don't compete with Type1's 1-4).
        ot = proc.get("obligation_type", 0)
        if ot in (7, 8, 9):
            op_lifecycle = 0
        else:
            op_lifecycle = s2.get("operation_lifecycle", 1)

        s2["sort_key"] = [
            s2.get("phase", 0),
            s2.get("type_priority", 1),
            s2.get("chain_depth", 0),
            s2.get("topology_level", 0),
            op_lifecycle,
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