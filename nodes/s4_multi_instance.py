"""S4 Multi-Instance Calculation Node — V2 Aligned.

V2 logic:
- Primary: min(dimCount + 1, 5)
- Dependent: getMultiCount(parent) * min(dimCount + 1, 5)
- VE: getMultiCount(ve.parent_entity) * min(dimCount + 1, 5)
- Other: max(1, min(dimCount + 1, 5))

No procedure expansion — only metadata annotation.
"""
from __future__ import annotations
from models.state import AgentState

FACTOR_CAP = 5  # V2 cap


def s4_multi_instance_node(state: AgentState) -> dict:
    procedures = list(state.get("procedures", []))
    warnings = list(state.get("warnings", []))
    errors = list(state.get("errors", []))

    primary = state.get("primary_entity", "")
    dep_entities = state.get("dependent_entities", [])
    entity_parent = state.get("entity_parent", {})
    ves = state.get("virtual_entities", {})
    cm = state.get("coverage_model", {})
    tos = cm.get("transition_obligations", [])

    # Compute entity_dim_count from transition_obligations
    entity_dim_count: dict[str, int] = {}
    for to in tos:
        e = to.get("entity", "")
        d = to.get("dimension", "")
        if d:
            entity_dim_count.setdefault(e, set()).add(d)
    for e in entity_dim_count:
        entity_dim_count[e] = len(entity_dim_count[e])

    # V2-aligned recursive getMultiCount with memoization
    entity_instances: dict[str, int] = {}

    def get_multi_count(entity: str) -> int:
        if entity in entity_instances:
            return entity_instances[entity]

        is_primary = (entity == primary)
        is_dep = entity in dep_entities
        is_ve = entity in ves

        # Resolve original entity's dim_count for VEs
        if is_ve:
            orig = ves[entity].get("original_entity", entity)
            dc = entity_dim_count.get(orig, 0)
        else:
            dc = entity_dim_count.get(entity, 0)

        factor = min(dc + 1, FACTOR_CAP)

        if is_primary:
            count = factor
        elif is_ve:
            parent = ves[entity].get("parent_entity", "")
            parent_inst = get_multi_count(parent) if parent else 1
            count = parent_inst * factor
        elif is_dep:
            parent = entity_parent.get(entity, "")
            parent_inst = get_multi_count(parent) if parent else 1
            count = parent_inst * factor
        else:
            count = max(1, factor)

        entity_instances[entity] = count
        return count

    # Pre-compute for all entities
    for to in tos:
        get_multi_count(to.get("entity", ""))
    for ve_name in ves:
        get_multi_count(ve_name)

    # Annotate procedures — NO expansion
    for proc in procedures:
        s4 = proc.get("_S4_fields", {})
        entity = proc["entity"]
        ot = proc.get("obligation_type", 0)

        # Independent Type7: use BR.entities[0] entity count
        if ot == 8:
            br_entities_str = ""
            for sid in proc.get("source_ids", []):
                for ro in cm.get("constraint_obligations", []):
                    if ro.get("id") == sid or ro.get("constraint_id") == sid:
                        br_entities_str = ro.get("entities", "")
                        break
            if br_entities_str:
                first_entity = br_entities_str.split(",")[0].strip() if isinstance(br_entities_str, str) else br_entities_str[0]
                count = get_multi_count(first_entity.strip())
            else:
                count = get_multi_count(entity)
        else:
            count = get_multi_count(entity)

        # Embedded BRs inherit host count
        has_embedded_brs = bool(proc.get("embedded_brs", []))
        if has_embedded_brs and count <= 1:
            count = 1

        count = max(1, count)
        s4["multi_count"] = count
        s4["multi_instance"] = count > 1

        # Build multi_reason matching V2 format
        is_primary = (entity == primary)
        is_dep = entity in dep_entities
        is_ve = entity in ves
        dc = entity_dim_count.get(entity, 0)

        if is_primary:
            s4["multi_reason"] = f"主实体: min(dim_count+1,5)={count}"
        elif is_ve:
            parent = ves[entity].get("parent_entity", "")
            parent_inst = get_multi_count(parent) if parent else 1
            s4["multi_reason"] = f"虚拟实体: parent({parent})={parent_inst} × min({dc}+1,5)={count}"
        elif is_dep:
            parent = entity_parent.get(entity, "")
            parent_inst = get_multi_count(parent) if parent else 1
            s4["multi_reason"] = f"依赖实体: parent({parent or 'none'})={parent_inst} × min({dc}+1,5)={count}"
        else:
            s4["multi_reason"] = f"max(1, min(dim_count+1,5))={count}" if count > 1 else ""

    warnings.append(f"S4: {len(procedures)} procedures annotated with multi-instance metadata")

    return {
        "procedures": procedures,
        "entity_instance_counts": entity_instances,
        "warnings": warnings,
        "errors": errors,
        "current_stage": "s4",
    }