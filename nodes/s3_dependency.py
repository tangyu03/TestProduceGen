"""S3 Dependency Binding Node — v3 with I23 business temporal guards.

Implements:
- Strong: transition upstream + same-dim chain ordering + CO enabler + VE.co_ids
- Weak: cross-entity side_effects (filtered by target state)
- I23: Business temporal guards (5 rules)
- Cycle detection via graph_algo.break_cycles()
"""
from models.state import AgentState
from tools.graph_algo import break_cycles


def s3_dependency_node(state: AgentState) -> dict:
    """S3: Bind dependencies between procedures."""
    procedures = list(state.get("procedures", []))
    warnings = list(state.get("warnings", []))
    errors = list(state.get("errors", []))

    upstream_map = state.get("transition_upstream_map", {})
    cm = state.get("coverage_model", {})
    tos = cm.get("transition_obligations", [])
    cos = cm.get("cross_entity_obligations", [])
    ves = state.get("virtual_entities", {})

    proc_by_id = {p["temp_id"]: p for p in procedures}
    proc_by_entity: dict[str, list] = {}
    for proc in procedures:
        proc_by_entity.setdefault(proc["entity"], []).append(proc)

    to_by_id = {to["id"]: to for to in tos}
    co_by_id = {co["id"]: co for co in cos}

    trans_id_to_proc_ids: dict[str, list] = {}
    for proc in procedures:
        for sid in proc.get("source_ids", []):
            to = to_by_id.get(sid)
            if to and to.get("transition_id"):
                trans_id_to_proc_ids.setdefault(to["transition_id"], []).append(proc["temp_id"])

    enabler_state_to_procs = {}  # (entity, dimension, state_in_post) → [proc_id]
    for proc in procedures:
        post = proc.get("post_state", "")
        entity = proc["entity"]
        dimension = proc.get("dimension") or ""
        if "→" in post:
            state_part = post.split("→")[-1].split("(")[0].strip()
            key = (entity, dimension, state_part)
            enabler_state_to_procs.setdefault(key, []).append(proc["temp_id"])

    entity_dim_procs: dict[str, list] = {}
    for proc in procedures:
        if proc.get("dimension"):
            entity_dim_procs.setdefault(f"{proc['entity']}.{proc['dimension']}", []).append(proc["temp_id"])

    # ── Strong dependencies ──
    for proc in procedures:
        s3 = proc.get("_S3_fields", {})
        deps = set(s3.get("dependencies", []))

        # 1. Transition upstream
        for sid in proc.get("source_ids", []):
            to = to_by_id.get(sid)
            if not to or not to.get("transition_id"):
                continue
            tid = to["transition_id"]
            for up_tid in upstream_map.get(tid, []):
                for up_proc_id in trans_id_to_proc_ids.get(up_tid, []):
                    if up_proc_id != proc["temp_id"]:
                        deps.add(up_proc_id)

        # 2. Same-entity same-dimension chain ordering
        if proc.get("dimension"):
            key = f"{proc['entity']}.{proc['dimension']}"
            same_dim = entity_dim_procs.get(key, [])
            try:
                idx = same_dim.index(proc["temp_id"])
                if idx > 0:
                    deps.add(same_dim[idx - 1])
            except ValueError:
                pass

        # 3. CO enabler dependency
        for sid in proc.get("source_ids", []):
            co = co_by_id.get(sid)
            if co:
                enabler_entity = co.get("enabler_entity")
                enabler_state = co.get("enabler_state")
                enabler_dimension = co.get("enabler_dimension", "")
                if enabler_entity and enabler_state:
                     key = (enabler_entity, enabler_dimension, enabler_state)
                     for match_id in enabler_state_to_procs.get(key, []):
                        if match_id != proc["temp_id"]:
                             deps.add(match_id)

        # 4. VE.co_ids dependency binding
        entity = proc["entity"]
        if entity in ves:
            ve = ves[entity]
            for co_id in ve.get("co_ids", []):
                co = co_by_id.get(co_id)
                if co:
                    ee = co.get("enabler_entity")
                    es = co.get("enabler_state")
                    if ee and es:
                        for mid in enabler_state_to_procs.get((ee, es), []):
                            if mid != proc["temp_id"]:
                                deps.add(mid)

        s3["dependencies"] = list(deps)

    # ── Weak dependencies (side_effects — filtered by target state) ──
    for proc in procedures:
        s3 = proc.get("_S3_fields", {})
        weak = set(s3.get("weak_dependencies", []))

        for sid in proc.get("source_ids", []):
            to = to_by_id.get(sid)
            if not to:
                continue
            for se in to.get("side_effects", []):
                te = se.get("target_entity")
                if not te or te == proc["entity"]:
                    continue
                td = se.get("target_dimension")
                effect = se.get("effect_desc", "")
                for other in proc_by_entity.get(te, []):
                    if other["temp_id"] == proc["temp_id"]:
                        continue
                    if td and other.get("dimension") != td:
                        continue
                    if effect and other.get("post_state"):
                        post_st = other["post_state"].split("→")[-1].split("(")[0].strip() if "→" in other["post_state"] else ""
                        if post_st and post_st not in effect:
                            continue
                    weak.add(other["temp_id"])

        # Independent Type7: weak dep to non-primary entity's closest phase proc
        if proc.get("obligation_type") == 8:
            for sid in proc.get("source_ids", []):
                ro = cm.get("constraint_obligations", [])
                for r in ro:
                    if r.get("id") == sid or r.get("constraint_id") == sid:
                        br_entities = r.get("entities", "").split(",") if isinstance(r.get("entities"), str) else r.get("entities", [])
                        for be in br_entities[1:]:
                            be = be.strip()
                            if be in proc_by_entity:
                                closest = min(proc_by_entity[be],
                                              key=lambda p: p.get("_S2_fields", {}).get("phase", 999),
                                              default=None)
                                if closest:
                                    weak.add(closest["temp_id"])

        s3["weak_dependencies"] = list(weak)

    # ── I23: Business temporal guards ──
    _apply_temporal_guards(procedures, proc_by_id, proc_by_entity, co_by_id, warnings)

    # ── Cycle detection & breaking via graph_algo ──
    procedures, cycle_warnings = break_cycles(procedures)
    warnings.extend(cycle_warnings)

    has_strong = sum(1 for p in procedures if p.get("_S3_fields", {}).get("dependencies"))
    has_weak = sum(1 for p in procedures if p.get("_S3_fields", {}).get("weak_dependencies"))
    warnings.append(f"S3 bound dependencies: {has_strong} with strong, {has_weak} with weak")

    return {
        "procedures": procedures,
        "dependency_graph": {"cycle_count": len(cycle_warnings)},
        "warnings": warnings,
        "errors": errors,
        "current_stage": "s3",
    }


def _apply_temporal_guards(
    procedures: list[dict],
    proc_by_id: dict,
    proc_by_entity: dict,
    co_by_id: dict,
    warnings: list[str],
):
    """I23: Apply 5 business temporal guard rules as implicit strong dependencies."""
    for proc in procedures:
        s3 = proc.get("_S3_fields", {})
        deps = set(s3.get("dependencies", []))
        entity = proc["entity"]
        dim = proc.get("dimension", "")
        s2 = proc.get("_S2_fields", {})

        # Guard 1: State machine predecessor priority
        # If proc's S-step references a from_state, find the proc whose post_state = from_state
        s_steps = [st for st in proc.get("steps", []) if st.get("aaa") == "S"]
        for s_step in s_steps:
            inp = s_step.get("input", "")
            if "=" in inp and dim:
                from_state = inp.split("=")[-1].strip().split(";")[0].strip()
                for other in proc_by_entity.get(entity, []):
                    if other["temp_id"] == proc["temp_id"]:
                        continue
                    post = other.get("post_state", "")
                    if "→" in post:
                        post_state_val = post.split("→")[-1].split("(")[0].strip()
                        if post_state_val == from_state:
                            deps.add(other["temp_id"])

        # Guard 2: Constraint gate (Type4a) before Type1
        if proc.get("obligation_type") == 1:
            s_input = ""
            for st in proc.get("steps", []):
                if st.get("aaa") == "S":
                    s_input = st.get("input", "")
                    break
            for other in proc_by_entity.get(entity, []):
                if other.get("obligation_type") == 4 and other["temp_id"] != proc["temp_id"]:
                    co = co_by_id.get(other.get("source_ids", [""])[0]) if other.get("source_ids") else None
                    if co and co.get("dependent_condition") and co.get("dependent_condition") in s_input:
                        deps.add(other["temp_id"])

        # Guard 3: Financial flow ordering
        fin_keywords = {'缴费', '付款', '收款', '费用', '付款凭证'}
        has_fin = any(kw in str(proc.get("steps", [])) for kw in fin_keywords)
        if has_fin:
            for other in proc_by_entity.get(entity, []):
                if other["temp_id"] == proc["temp_id"]:
                    continue
                other_fin = any(kw in str(other.get("steps", [])) for kw in fin_keywords)
                if other_fin:
                    other_ol = other.get("_S2_fields", {}).get("operation_lifecycle", 1)
                    my_ol = s2.get("operation_lifecycle", 1)
                    if other_ol < my_ol:
                        deps.add(other["temp_id"])

        # Guard 4: Audit flow ordering (submit → review → approve/reject)
        audit_keywords = {'提交', '审批中', '开始审批'}
        approve_keywords = {'审批同意', '审批通过', '驳回'}
        is_approve = any(kw in str(proc.get("steps", [])) for kw in approve_keywords)
        if is_approve:
            for other in proc_by_entity.get(entity, []):
                if other["temp_id"] == proc["temp_id"]:
                    continue
                is_submit = any(kw in str(other.get("steps", [])) for kw in audit_keywords)
                if is_submit:
                    deps.add(other["temp_id"])

        # Guard 5: Create-before-use (from==null creation before modify)
        is_creation = s2.get("operation_lifecycle") == 1
        if not is_creation and dim:
            for other in proc_by_entity.get(entity, []):
                if other["temp_id"] == proc["temp_id"]:
                    continue
                other_ol = other.get("_S2_fields", {}).get("operation_lifecycle", 0)
                if other_ol == 1:
                    deps.add(other["temp_id"])

        s3["dependencies"] = list(deps)
