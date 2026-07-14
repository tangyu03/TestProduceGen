from __future__ import annotations
"""S3 Dependency Binding Node — v3 with I23 business temporal guards.

Implements:
- Strong: transition upstream + same-dim chain ordering + CO enabler + VE.co_ids
- Weak: cross-entity side_effects (filtered by target state)
- I23: Business temporal guards (5 rules)
- Cycle detection via graph_algo.break_cycles()
- Final topological sort (deps-first, sort_key tiebreaker) + sequential ID assignment
"""
import re

from models.state import AgentState
from tools.graph_algo import break_cycles, topological_sort_procedures


# ── Precondition state extraction (for Guard 6) ──────────────────────────
#
# TO.preconditions are free-form Chinese strings like:
#   "报名记录状态为报名成功"
#   "项目样品状态为已核查"
#   "报名记录样品状态推进(待发样->待收样->已收样)"
#   "项目状态为已结束"
#
# We extract the state value after "为" or after "状态" keywords, so we can
# match them against other procedures' post_state values.

# Pattern: capture state value after "为" or after "状态="
_PRECONDITION_STATE_RE = re.compile(
    r'(?:为|=)\s*[\u201c\u2018\"\']?([^\u201d\u2019\"\'，,；;（(（\s]+)[\u201d\u2019\"\']?'
)


def preconditions_extract_states(precond: str) -> list[str]:
    """Extract referenced state values from a single precondition string.

    Examples:
        "报名记录状态为报名成功" → ["报名成功"]
        "项目样品状态为已核查" → ["已核查"]
        "报名记录样品状态推进(待发样->待收样->已收样)" → ["待发样", "待收样", "已收样"]
        "项目状态为已结束" → ["已结束"]
    """
    if not precond or not isinstance(precond, str):
        return []
    results: list[str] = []
    # Strategy 1: "为XXX" or "=XXX" patterns
    for m in _PRECONDITION_STATE_RE.finditer(precond):
        val = m.group(1).strip()
        if val and len(val) >= 2 and val not in ("null", "None", "无", "初始"):
            results.append(val)
    # Strategy 2: arrow-separated states like "待发样->待收样->已收样"
    if "->" in precond or "→" in precond:
        normalized = precond.replace("→", "->")
        for chunk in normalized.split("->"):
            chunk = chunk.strip()
            # Strip leading/trailing punctuation
            chunk = re.sub(r'^[（(]+\s*', '', chunk)
            chunk = re.sub(r'\s*[）)]*$', '', chunk)
            if chunk and len(chunk) >= 2 and chunk not in results:
                results.append(chunk)
    return results



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

    # Helper: sort dependency IDs by gen_seq (lower = more foundational = first).
    # gen_seq reflects the order procedures were generated in S1, which follows
    # CREATE → UPDATE → DELETE lifecycle. This makes dependency lists read in
    # a natural "prerequisites first" order.
    def _sort_deps(dep_ids: set) -> list:
        return sorted(dep_ids, key=lambda did: proc_by_id.get(did, {}).get("gen_seq", 999))

    to_by_id = {to["id"]: to for to in tos}
    # Also index by transition_id — source_ids may use either convention
    to_by_tid = {to["transition_id"]: to for to in tos if to.get("transition_id")}
    co_by_id = {co["id"]: co for co in cos}

    def _resolve_to(sid: str) -> dict | None:
        """Resolve a source_id to its transition obligation.

        Tries: exact match (id or transition_id), then strips branch suffix
        (e.g. "T-001a" → "T-001") since branch-variant source_ids may not
        have their own TO entry.
        """
        result = to_by_id.get(sid) or to_by_tid.get(sid)
        if result:
            return result
        # Strip trailing lowercase letter (branch suffix)
        base = re.sub(r'[a-z]$', '', sid)
        if base != sid:
            return to_by_id.get(base) or to_by_tid.get(base)
        return None

    trans_id_to_proc_ids: dict[str, list] = {}
    for proc in procedures:
        for sid in proc.get("source_ids", []):
            to = _resolve_to(sid)
            if to and to.get("transition_id"):
                trans_id_to_proc_ids.setdefault(to["transition_id"], []).append(proc["temp_id"])

    enabler_state_to_procs: dict[tuple, list] = {}
    for proc in procedures:
        post = proc.get("post_state", "")
        entity = proc["entity"]
        # Exclude rejection variants from enabler_state index — their post_state
        # "待开始(驳回)" is NOT "待开始" and should not be matched as enabler.
        if proc.get("risk_trait") == "audit_rejection":
            continue
        if "→" in post:
            state_part = post.split("→")[-1].strip()
            enabler_state_to_procs.setdefault((entity, state_part), []).append(proc["temp_id"])

    entity_dim_procs: dict[str, list] = {}
    for proc in procedures:
        if proc.get("dimension"):
            entity_dim_procs.setdefault(f"{proc['entity']}.{proc['dimension']}", []).append(proc["temp_id"])

    # ── I23: Business temporal guards (run FIRST — state-machine deps take priority) ──
    _apply_temporal_guards(procedures, proc_by_id, proc_by_entity, co_by_id, cm)

    # ── Strong dependencies ──
    for proc in procedures:
        s3 = proc.get("_S3_fields", {})
        deps = set(s3.get("dependencies", []))
        # Transition upstream deps are protected from cycle breaking.
        # They represent real business dependencies from the transition graph
        # and should never be removed. Stored separately and merged back after
        # break_cycles to preserve them through the cycle resolution process.
        # Guard 1 deps (state machine predecessor) are also protected.
        upstream_deps = set(s3.get("upstream_deps", []))
        upstream_deps |= set(s3.get("guard1_deps", []))
        # Remove guard1 deps from regular deps (they're now protected)
        deps -= set(s3.get("guard1_deps", []))

        # 1. Transition upstream
        # For each upstream transition, pick the most specific matching
        # procedure (fewest source_ids). This avoids pulling in mega-procedures
        # created by S1.10 dedup that bundle unrelated transitions alongside
        # the matching one (e.g. T-030a bundled with T-016/T-011 pulls T-031
        # far to the right).
        #
        # Phase guard: skip upstream deps that would create phase violations
        # (dep phase > proc phase).  Transition upstream_map is built from
        # transition_id chains which may span entities at different phases.
        # Only accept deps that don't break phase ordering.
        my_phase = proc.get("_S2_fields", {}).get("phase", 0)
        for sid in proc.get("source_ids", []):
            to = _resolve_to(sid)
            if not to or not to.get("transition_id"):
                continue
            tid = to["transition_id"]
            for up_tid in upstream_map.get(tid, []):
                candidates = trans_id_to_proc_ids.get(up_tid, [])
                if not candidates:
                    continue
                # Pick the most specific procedure: fewest source_ids = best match
                if len(candidates) == 1:
                    best = candidates[0]
                else:
                    best = min(candidates, key=lambda cid:
                        len(proc_by_id.get(cid, {}).get("source_ids", [])))
                if best == proc["temp_id"]:
                    continue
                # Phase guard: skip if dep is in a later phase (would break ordering)
                dep_p = proc_by_id.get(best, {})
                dep_phase = dep_p.get("_S2_fields", {}).get("phase", 0)
                if dep_phase > my_phase:
                    continue
                upstream_deps.add(best)

        # 2. Same-entity same-dimension chain ordering
        # Sort same-dim procedures by sort_key for deterministic chain
        # (independent of input list order, which may be arbitrary from S1)
        # I23-fix: validate that the predecessor's post_state feeds into this
        # procedure's from_state. Three cases:
        #   a) curr has no from_state → independent op (attr change, rule, gate)
        #      → skip chain (no meaningful state predecessor)
        #   b) curr is creation (from=初始/None) → root of chain → skip
        #   c) curr.from_state == prev.post_state → valid chain → add dep
        #   d) states don't match → skip (Guard 1 handles real state deps)
        if proc.get("dimension"):
            key = f"{proc['entity']}.{proc['dimension']}"
            same_dim_ids = entity_dim_procs.get(key, [])
            same_dim_sorted = sorted(
                same_dim_ids,
                key=lambda tid: (
                    proc_by_id.get(tid, {}).get("_S2_fields", {}).get("sort_key", [])
                ),
            )
            try:
                idx = same_dim_sorted.index(proc["temp_id"])
                if idx > 0:
                    prev_id = same_dim_sorted[idx - 1]
                    prev_proc = proc_by_id.get(prev_id, {})
                    # BDD: extract from_state from givens[0].state directly
                    # (was: parsing S-step input string in legacy AAA model)
                    curr_from_state = None
                    givens = proc.get("givens", [])
                    if givens:
                        curr_from_state = givens[0].get("state", "")
                    # Extract predecessor's post_state value (exact, no truncation)
                    prev_post = prev_proc.get("post_state", "")
                    prev_post_val = None
                    if "→" in prev_post:
                        prev_post_val = prev_post.split("→")[-1].strip()
                    # ── State-connection validation ──
                    if curr_from_state is None:
                        pass  # case (a): independent op — no chain predecessor
                    elif curr_from_state in ("(初始)", "(None)", "None", ""):
                        pass  # case (b): creation from null — root of chain
                    elif prev_post_val and curr_from_state == prev_post_val:
                        # case (c): valid state chain — but skip if prev already
                        # depends on curr (Guard 1 created the reverse edge).
                        # Adding both directions would create a cycle (e.g. 启用↔停用).
                        prev_deps = prev_proc.get("_S3_fields", {}).get("dependencies", [])
                        if proc["temp_id"] not in prev_deps:
                            deps.add(prev_id)
                    else:
                        pass  # case (d): states don't match
            except ValueError:
                pass

        # 3. CO enabler dependency
        # Phase guard: skip CO enabler deps that would create phase violations.
        for sid in proc.get("source_ids", []):
            co = co_by_id.get(sid)
            if co:
                ee = co.get("enabler_entity")
                es = co.get("enabler_state")
                if ee and es:
                    for mid in enabler_state_to_procs.get((ee, es), []):
                        if mid != proc["temp_id"]:
                            # Phase guard
                            dep_p = proc_by_id.get(mid, {})
                            dep_phase = dep_p.get("_S2_fields", {}).get("phase", 0)
                            if dep_phase > my_phase:
                                continue
                            deps.add(mid)

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

        s3["dependencies"] = _sort_deps(deps)
        s3["upstream_deps"] = _sort_deps(upstream_deps)

    # ── Weak dependencies (side_effects — filtered by target state) ──
    for proc in procedures:
        s3 = proc.get("_S3_fields", {})
        weak = set(s3.get("weak_dependencies", []))

        for sid in proc.get("source_ids", []):
            to = _resolve_to(sid)
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
                    # BDD: only state-transition / CRUD / config procedures are
                    # valid weak-dep targets.  Rule-validation (Type7/8) and
                    # field-validation (Type9) describe business rules, not
                    # state changes — they should not be weak-dep targets of
                    # side_effect chains.
                    if other.get("obligation_type") in (7, 8, 9):
                        continue
                    # Exclude rejection variants from weak-dep targets
                    if other.get("risk_trait") == "audit_rejection":
                        continue
                    if td and other.get("dimension") != td:
                        continue
                    if effect and other.get("post_state"):
                        post_st = other["post_state"].split("→")[-1].strip() if "→" in other["post_state"] else ""
                        if post_st and post_st not in effect:
                            continue
                    weak.add(other["temp_id"])

        # Independent Type7: weak dep to non-primary entity's closest phase proc
        if proc.get("obligation_type") == 8:
            # BUGFIX #20: hoist cm.get out of the source_ids loop
            ros_all = cm.get("constraint_obligations", [])
            for sid in proc.get("source_ids", []):
                for r in ros_all:
                    if r.get("id") == sid or r.get("constraint_id") == sid:
                        entities_raw = r.get("entities_involved", r.get("entities", ""))
                        # BUGFIX #9: handle Chinese commas/顿号 via regex split
                        if isinstance(entities_raw, list):
                            br_entities = entities_raw
                        elif isinstance(entities_raw, str):
                            br_entities = re.split(r'[,，、\s]+', entities_raw)
                        else:
                            br_entities = []
                        for be in br_entities[1:]:
                            be = be.strip()
                            if be in proc_by_entity:
                                # BDD: only state-transition / CRUD / config
                                # procedures are valid weak-dep targets.
                                # Exclude Type7/8/9 (rule/field validation).
                                candidates = [
                                    p for p in proc_by_entity[be]
                                    if p.get("obligation_type") not in (7, 8, 9)
                                ]
                                if candidates:
                                    closest = min(candidates,
                                                  key=lambda p: p.get("_S2_fields", {}).get("phase", 999))
                                    if closest:
                                        weak.add(closest["temp_id"])

        s3["weak_dependencies"] = _sort_deps(weak)

    # ── Merge ALL deps into one list BEFORE cycle breaking ──
    # upstream_deps and guard1_deps represent real business constraints
    # (transition graph edges). They must be part of the dependency graph
    # for cycle detection; otherwise cycle breaking works on an incomplete
    # graph and the Kahn sort discovers residual cycles from the unmerged edges.
    for proc in procedures:
        s3 = proc.get("_S3_fields", {})
        all_deps = set(s3.get("dependencies", []))
        for ud in s3.get("upstream_deps", []):
            all_deps.add(ud)
        for gd in s3.get("guard1_deps", []):
            all_deps.add(gd)
        s3["dependencies"] = _sort_deps(all_deps)
        # Clear the now-merged fields so downstream code doesn't double-count
        s3["upstream_deps"] = []
        s3["guard1_deps"] = []

    # ── Cycle detection & breaking via graph_algo ──
    procedures, cycle_warnings = break_cycles(procedures)
    warnings.extend(cycle_warnings)

    # ── Final topological sort respecting dependency graph ──
    # Kahn algorithm naturally handles cross-phase deps: dependencies are
    # hard constraints, sort_key is only a tiebreaker among procedures
    # at the same topological level.
    procedures = topological_sort_procedures(procedures)

    # ── Re-assign sequential IDs based on final topological order ──
    id_map: dict[str, str] = {}
    for i, proc in enumerate(procedures, 1):
        old_id = proc["temp_id"]
        new_id = f"PROC-{i:03d}"
        id_map[old_id] = new_id
        proc["temp_id"] = new_id

    # Update all dependency references to use new IDs, sorted by PROC number.
    # Sorting by PROC number ensures foundational procedures (earlier in the
    # final topo order = lower PROC number) appear first in dependency lists.
    def _proc_num(dep_id: str) -> int:
        try:
            return int(dep_id.split("-")[1].split(".")[0])
        except (IndexError, ValueError):
            return 999

    for proc in procedures:
        s3_final = proc.get("_S3_fields", {})
        # BDD: filter out dangling deps (referencing procedures removed by
        # S1 dedup or S3 cycle-break) before rewriting IDs.
        valid_deps = [d for d in s3_final.get("dependencies", []) if d in id_map]
        s3_final["dependencies"] = sorted(
            [id_map.get(d, d) for d in valid_deps],
            key=_proc_num,
        )
        valid_weak = [d for d in s3_final.get("weak_dependencies", []) if d in id_map]
        s3_final["weak_dependencies"] = sorted(
            [id_map.get(d, d) for d in valid_weak],
            key=_proc_num,
        )

    has_strong = sum(1 for p in procedures if p.get("_S3_fields", {}).get("dependencies"))
    has_weak = sum(1 for p in procedures if p.get("_S3_fields", {}).get("weak_dependencies"))
    warnings.append(
        f"S3 bound dependencies ({has_strong} strong, {has_weak} weak), "
        f"topological sort complete, {len(procedures)} procedures re-ID'd"
    )

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
    cm: dict,
):
    """I23: Apply 5 business temporal guard rules as implicit strong dependencies."""
    for proc in procedures:
        s3 = proc.get("_S3_fields", {})
        deps = set(s3.get("dependencies", []))
        # Guard 1 deps are protected like upstream_deps (real business deps)
        guard1_deps = set(s3.get("guard1_deps", []))
        entity = proc["entity"]
        dim = proc.get("dimension", "")
        s2 = proc.get("_S2_fields", {})

        # Guard 1: State machine predecessor priority
        #
        # Design principle: use ONLY structural signals, not text matching.
        # The from_state comes from givens[0].state (set by S1 from TO.from).
        # We match it against other procedures' post_state EXACTLY.
        #
        # Strategy B (substring matching of post_state in description text)
        # has been REMOVED — it caused false positives where a phase 0 proc's
        # description happened to contain a phase 4 proc's post_state string,
        # creating cross-phase dependencies that broke ordering.
        #
        # Rules:
        # 1. EXCLUDE rejection variants — "待开始(驳回)" is NOT "待开始"
        # 2. EXACT match only — post_state must equal from_state exactly
        s_steps = proc.get("givens", [])
        for s_step in s_steps:
            from_state = s_step.get("state", "")
            # Only use explicit state value (Strategy A)
            if not from_state or from_state in ("(初始)", "(None)", "None", ""):
                continue
            for other in proc_by_entity.get(entity, []):
                if other["temp_id"] == proc["temp_id"]:
                    continue
                # Exclude rejection variants
                if other.get("risk_trait") == "audit_rejection":
                    continue
                post = other.get("post_state", "")
                if "→" in post:
                    post_state_val = post.split("→")[-1].strip()
                    if post_state_val == from_state:
                        # Check reverse: if other already depends on proc, skip
                        other_deps = other.get("_S3_fields", {}).get("dependencies", [])
                        if proc["temp_id"] in other_deps:
                            continue  # bidirectional inverse — skip
                        guard1_deps.add(other["temp_id"])

        # Guard 2: Constraint gate (Type4a) before Type1
        if proc.get("obligation_type") == 1:
            # BDD: read precondition text from givens[0].description
            s_input = ""
            givens = proc.get("givens", [])
            if givens:
                s_input = givens[0].get("description", "") + " " + givens[0].get("state", "")
            for other in proc_by_entity.get(entity, []):
                # BDD: Type4a no longer generated — this guard is a no-op now.
                # CO ordering is handled by the CO enabler dependency (section 3).
                # Kept for documentation; will never match since ot=4 procs don't exist.
                if other.get("obligation_type") == 4 and other["temp_id"] != proc["temp_id"]:
                    co = co_by_id.get(other.get("source_ids", [""])[0]) if other.get("source_ids") else None
                    if co and co.get("dependent_condition") and co.get("dependent_condition") in s_input:
                        deps.add(other["temp_id"])

        # Guard 5: Create-before-use (from==null creation before any modify/use)
        # More comprehensive: check if this proc's from-state matches a create proc's to-state
        is_creation = s2.get("operation_lifecycle") == 1
        if not is_creation and dim:
            for other in proc_by_entity.get(entity, []):
                if other["temp_id"] == proc["temp_id"]:
                    continue
                other_ol = other.get("_S2_fields", {}).get("operation_lifecycle", 0)
                # Creation proc: operation_lifecycle==1 or from=null in S step
                is_other_creation = other_ol == 1
                if not is_other_creation:
                    # BDD: check if other's givens[0].state indicates creation (from=null)
                    other_givens = other.get("givens", [])
                    if other_givens:
                        state_val = other_givens[0].get("state", "")
                        desc_val = other_givens[0].get("description", "")
                        if "(初始)" in state_val or "(初始)" in desc_val or "= None" in desc_val or "from=null" in desc_val.lower():
                            is_other_creation = True
                if is_other_creation and other.get("dimension") == dim:
                    # I25-fix: Type4b lifecycle procedures are side-effects of the
                    # enabler transition, not prerequisites. The architecture says
                    # "创建后同步创建" — lifecycle creation happens AFTER, not before.
                    if other.get("obligation_type") == 5:  # Type4b = lifecycle
                        continue
                    deps.add(other["temp_id"])

        # ── Guard 6: Cross-dimension precondition state dependency ──
        #
        # Design principle: structural signals only, strict matching.
        #
        # 1. SAME ENTITY ONLY: cross-entity dependencies are handled by CO
        #    (cross_entity_obligations) and upstream_map, NOT by Guard 6 text
        #    matching.  Guard 6 only resolves same-entity cross-DIMENSION deps
        #    (e.g. E-REG.报名记录状态=报名成功 → E-REG.报名记录样品状态推进).
        #
        # 2. EXCLUDE rejection variants: "待开始(驳回)" is NOT "待开始".
        #
        # 3. EXCLUDE fuzzy state references: "报名成功或之后" contains "或"
        #    — skip (state range, not precise state).
        #
        # 4. EXACT match only: post_state must equal prec_state exactly.
        tos_all = cm.get("transition_obligations", [])
        for sid in proc.get("source_ids", []):
            to = next((t for t in tos_all if t.get("id") == sid), None)
            if not to:
                continue
            preconds = to.get("preconditions", []) or []
            for prec_text in preconds:
                for prec_state in preconditions_extract_states(prec_text):
                    # Skip fuzzy state references
                    if "或" in prec_state:
                        continue
                    # Search ONLY same-entity procedures (cross-dimension, not cross-entity)
                    for other in proc_by_entity.get(entity, []):
                        if other["temp_id"] == proc["temp_id"]:
                            continue
                        # Exclude rejection variants
                        if other.get("risk_trait") == "audit_rejection":
                            continue
                        post = other.get("post_state", "")
                        if "→" not in post:
                            continue
                        # EXACT match
                        post_val = post.split("→")[-1].strip()
                        if post_val and post_val == prec_state and post_val != "(初始)":
                            # Skip same-dimension (Guard 1 handles those)
                            if other.get("dimension") == dim:
                                continue
                            deps.add(other["temp_id"])

        s3["dependencies"] = sorted(deps, key=lambda did: proc_by_id.get(did, {}).get("gen_seq", 999))
        s3["guard1_deps"] = sorted(guard1_deps, key=lambda did: proc_by_id.get(did, {}).get("gen_seq", 999))
