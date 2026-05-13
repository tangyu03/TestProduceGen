"""S2 Phase Assignment & Sorting Node.

Deterministic phase resolution and sort-key computation, faithfully
replicating the V2 JS engine's S2 stage.
"""
import copy
from typing import Any
from models.state import AgentState


def s2_sorting_node(state: AgentState) -> dict:
    """S2: Assign phases (if not already done in S1) and sort procedures.

    Since V2 already assigns phases during S1 generation, this node primarily:
    1. Resolves any remaining contextual phase rules (P4-ctx) by expanding procedures
    2. Ensures all phases are non-null (fallback = 0)
    3. Sets phase_name from phase_table
    4. Computes sort_key = [phase, topology_level, operation_lifecycle, type_priority, chain_depth, dimension_priority, gen_seq]
    5. Sorts procedures by sort_key
    6. Re-assigns sequential IDs (PROC-001, PROC-002, ...)

    Contextual phase rule expansion is handled in S1 (_apply_contextual_phase_rules),
    so this node mainly finalises sort_key and re-IDs.
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
            ctx_key = s2.get("context") or f"{proc['entity']}.{proc.get('dimension', '')}"
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

                    # Add context annotation to first step
                    if expanded["steps"]:
                        expanded["steps"][0]["input"] = (
                            f"[{rule.get('context', '')}] {expanded['steps'][0]['input']}"
                        )

                    procs_to_add.append(expanded)
            else:
                # No rule found — try upstream anchoring fallback
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

        # Ensure phase is non-null
        if s2.get("phase") is None:
            tl = s2.get("topology_level", 0)
            if tl == 0:
                s2["phase"] = 0
                s2["phase_basis"] = s2.get("phase_basis") or "P6: topology_level L0 → P0"
            else:
                s2["phase"] = 0
                s2["phase_basis"] = s2.get("phase_basis") or "fallback"

        # Set phase_name
        phase_names = phase_table.get("phase_names", [])
        phase = s2["phase"]
        s2["phase_name"] = phase_names[phase] if phase < len(phase_names) else f"P{phase}"

        # Build sort_key:
        # [phase, topology_level, operation_lifecycle, type_priority, chain_depth, dimension_priority, gen_seq]
        s2["sort_key"] = [
            s2.get("phase", 0),
            s2.get("topology_level", 0),
            s2.get("operation_lifecycle", 1),
            s2.get("type_priority", 1),
            s2.get("chain_depth", 0),
            s2.get("dimension_priority", 1),
            proc.get("gen_seq", 0),
        ]

    # ── Sort by sort_key ──
    procedures.sort(key=lambda p: p.get("_S2_fields", {}).get("sort_key", []))

    # ── Re-assign sequential IDs ──
    id_map: dict[str, str] = {}
    for i, proc in enumerate(procedures, 1):
        old_id = proc["temp_id"]
        new_id = f"PROC-{i:03d}"
        id_map[old_id] = new_id
        proc["temp_id"] = new_id

    # Update dependency references in S3 fields
    for proc in procedures:
        s3 = proc.get("_S3_fields", {})
        s3["dependencies"] = [id_map.get(d, d) for d in s3.get("dependencies", [])]
        s3["weak_dependencies"] = [id_map.get(d, d) for d in s3.get("weak_dependencies", [])]

    # Update any audit_rejection dependency references that were set in S1
    # (they use temp_ids like PROC-T1-N which should now be mapped)
    # Already handled by the id_map above.

    warnings.append(f"S2 sorted {len(procedures)} procedures, assigned sequential IDs")

    return {
        "procedures": procedures,
        "sorted_procedures": procedures,
        "warnings": warnings,
        "current_stage": "s2",
    }