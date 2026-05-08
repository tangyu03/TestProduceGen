"""S4 Multi-Instance Expansion Node.

Implements v3 S4: determines how many test instances each procedure needs
based on entity topology, dimension count, and virtual entity context.
"""
from __future__ import annotations

from models.state import AgentState


def s4_multi_instance_node(state: AgentState) -> dict:
    """S4: Multi-instance determination.

    Instance count rules:
    - Primary entity + multi-state: min(dim_count+1, 5)
    - Dependent entity: parent_instance × min(dim_count+1, 5)
    - Virtual entity: parent(VE.parent_entity instances) × min(VE.dim_count+1, 5)
    - Others: max(1, min(dim_count+1, 5))

    Embedded BRs inherit host multi_count.
    Independent Type7 uses BR.entities[0] entity count.
    """
    procedures = list(state.get("procedures", []))
    warnings = list(state.get("warnings", []))
    errors = list(state.get("errors", []))

    primary = state.get("primary_entity", "")
    dep_entities = state.get("dependent_entities", [])
    entity_parent = state.get("entity_parent", {})
    ves = state.get("virtual_entities", {})
    cm = state.get("coverage_model", {})
    tos = cm.get("transition_obligations", [])

    entity_dim_count: dict[str, int] = {}
    for to in tos:
        e = to.get("entity", "")
        d = to.get("dimension", "")
        if d:
            entity_dim_count.setdefault(e, set()).add(d)
    for e in entity_dim_count:
        entity_dim_count[e] = len(entity_dim_count[e])

    ve_original_dims: dict[str, int] = {}
    for ve_name, ve in ves.items():
        orig = ve.get("original_entity", "")
        ve_original_dims[ve_name] = entity_dim_count.get(orig, 0)

    entity_instances: dict[str, int] = {}

    def _calc_instances(entity: str) -> int:
        if entity in entity_instances:
            return entity_instances[entity]

        dc = entity_dim_count.get(entity, 0)
        base = min(dc + 1, 5)

        if entity == primary:
            count = base
        elif entity in ves:
            ve = ves[entity]
            parent = ve.get("parent_entity", "")
            parent_count = _calc_instances(parent) if parent else 1
            ve_dc = ve_original_dims.get(entity, dc)
            count = parent_count * min(ve_dc + 1, 5)
        elif entity in dep_entities:
            parent = entity_parent.get(entity, primary)
            parent_count = _calc_instances(parent) if parent else 1
            count = parent_count * base
        else:
            count = max(1, base)

        entity_instances[entity] = count
        return count

    _calc_instances(primary)

    expanded = []
    for proc in procedures:
        s4 = proc.get("_S4_fields", {})
        entity = proc["entity"]
        ot = proc.get("obligation_type", 0)

        if ot == 8:
            br_entities_str = ""
            for sid in proc.get("source_ids", []):
                for ro in cm.get("constraint_obligations", []):
                    if ro.get("id") == sid or ro.get("constraint_id") == sid:
                        br_entities_str = ro.get("entities", "")
                        break
            if br_entities_str:
                first_entity = br_entities_str.split(",")[0].strip() if isinstance(br_entities_str, str) else br_entities_str[0] if br_entities_str else entity
                first_entity = first_entity.strip()
                count = _calc_instances(first_entity)
            else:
                count = _calc_instances(entity)
        else:
            count = _calc_instances(entity)

        has_embedded_brs = bool(proc.get("embedded_brs", []))
        if has_embedded_brs and count <= 1:
            count = 1

        count = max(1, count)

        s4["multi_count"] = count
        s4["multi_instance"] = count > 1
        s4["multi_reason"] = f"entity={entity} dim_count={entity_dim_count.get(entity, 0)} instances={count}"

        if count > 1:
            for i in range(count):
                instance_proc = dict(proc)
                instance_proc["_S4_fields"] = dict(s4)
                instance_proc["temp_id"] = f"{proc['temp_id']}.{i + 1}"
                expanded.append(instance_proc)
            warnings.append(f"S4: {proc['temp_id']} expanded to {count} instances")
        else:
            expanded.append(proc)

    warnings.append(f"S4: {len(expanded)} procedures after multi-instance expansion")

    return {
        "procedures": expanded,
        "entity_instance_counts": entity_instances,
        "warnings": warnings,
        "errors": errors,
        "current_stage": "s4",
    }
