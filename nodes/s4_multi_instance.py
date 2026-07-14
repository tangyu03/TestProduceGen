"""S4 Multi-Instance Expansion Node — V4.

Implements:
  5.1: Instance count formula min(dim_count+1, 5) (was 3)
  5.2: Dependent entity parent-chain multiplication
  5.3: VE independent dim_count (only dimensions in VE's transitions)
  5.4: Actual instance expansion (PROC-NNN.{序号})
  5.5: Orthogonal expansion truncation (branch > config > 传导)
"""
from __future__ import annotations

import copy
import re

from models.state import AgentState


# Reverse the entity_name_map (name -> id) that S0/S1 build from
# coverage_model._context.entity_details; used by Type7 to resolve
# Chinese entity names found in BR.entities_involved.
def _build_name_to_id_map(cm: dict) -> dict[str, str]:
    """Build {chinese_name: entity_id} map from coverage_model._context.entity_details."""
    name_to_id: dict[str, str] = {}
    for e in cm.get("_context", {}).get("entity_details", []):
        eid = e.get("id") or e.get("entity_id")
        ename = e.get("name") or e.get("entity_name")
        if eid and ename:
            name_to_id[ename] = eid
    return name_to_id


def s4_multi_instance_node(state: AgentState) -> dict:
    """S4: Multi-instance determination and expansion.

    Computes per-entity instance counts, then duplicates procedures
    with PROC-NNN.{instance} IDs.
    """
    procedures = list(state.get("procedures", []))
    warnings = list(state.get("warnings", []))
    errors = list(state.get("errors", []))

    primary = state.get("primary_entity", "")
    dep_entities = state.get("dependent_entities", [])
    entity_parent = state.get("entity_parent", {})
    dependency_depth = state.get("dependency_depth", {})
    ves = state.get("virtual_entities", {})
    cm = state.get("coverage_model", {})
    tos = cm.get("transition_obligations", [])
    name_to_id = _build_name_to_id_map(cm)

    # ── Entity dimension counts ──
    entity_dim_count: dict[str, int] = {}
    for to in tos:
        e = to.get("entity", "")
        d = to.get("dimension", "")
        if d:
            entity_dim_count.setdefault(e, set()).add(d)
    for e in entity_dim_count:
        entity_dim_count[e] = len(entity_dim_count[e])

    # 5.3: VE dim_count — only dimensions in VE's transitions
    ve_dim_count: dict[str, int] = {}
    for ve_name, ve in ves.items():
        orig = ve.get("original_entity", "")
        ve_transition_ids = set(ve.get("transitions", []))
        ve_dims = set()
        for to in tos:
            if to.get("transition_id") in ve_transition_ids and to.get("dimension"):
                ve_dims.add(to["dimension"])
        ve_dim_count[ve_name] = len(ve_dims) if ve_dims else entity_dim_count.get(orig, 0)

    # ── 5.1: Instance count formula: max(1, min(dim_count + 1, 5)) ──
    entity_instances: dict[str, int] = {}

    def _calc_base_instances(entity: str) -> int:
        """Calculate base instance count for an entity (without parent multiplication)."""
        if entity in ves:
            dc = ve_dim_count.get(entity, 0)
        else:
            dc = entity_dim_count.get(entity, 0)
        return max(1, min(dc + 1, 5))

    # Compute in topological order so parents are computed before children
    # Primary first
    entity_instances[primary] = _calc_base_instances(primary)

    # Dependents in BFS order (by dependency_depth)
    sorted_deps = sorted(dep_entities, key=lambda e: dependency_depth.get(e, 999))
    for entity in sorted_deps:
        base = _calc_base_instances(entity)
        parent = entity_parent.get(entity)
        # 5.2: Parent-chain multiplication
        if parent and parent in entity_instances:
            entity_instances[entity] = entity_instances[parent] * base
        else:
            entity_instances[entity] = base

    # VEs: parent_instance × VE_base
    for ve_name, ve in ves.items():
        base = _calc_base_instances(ve_name)
        parent = ve.get("parent_entity", "")
        if parent and parent in entity_instances:
            entity_instances[ve_name] = entity_instances[parent] * base
        else:
            entity_instances[ve_name] = base

    # Other entities
    for to in tos:
        e = to.get("entity", "")
        if e and e not in entity_instances:
            entity_instances[e] = _calc_base_instances(e)

    # ── 5.4: Actual instance expansion (PROC-NNN.{序号}) ──
    expanded = []
    for proc in procedures:
        s4 = proc.get("_S4_fields", {})
        entity = proc["entity"]
        ot = proc.get("obligation_type", 0)

        # Determine instance count
        count = 1
        if ot == 8:  # Type7 standalone: use BR.entities_involved[0]
            first_entity = entity
            for sid in proc.get("source_ids", []):
                for ro in cm.get("constraint_obligations", []):
                    if ro.get("id") == sid or ro.get("constraint_id") == sid:
                        entities_raw = ro.get("entities_involved", ro.get("entities", []))
                        # BUGFIX #8: entities_involved may contain Chinese
                        # names (e.g. "项目") instead of entity IDs (e.g.
                        # "E-PRJ").  Resolve to IDs via name_to_id map.
                        # BUGFIX #9: also handle Chinese commas/顿号.
                        if isinstance(entities_raw, list) and entities_raw:
                            items = entities_raw
                        elif isinstance(entities_raw, str) and entities_raw.strip():
                            items = re.split(r'[,，、\s]+', entities_raw)
                        else:
                            items = []
                        if items:
                            first_raw = str(items[0]).strip()
                            first_entity = name_to_id.get(first_raw, first_raw)
                        break
            count = entity_instances.get(first_entity, 1)
        else:
            count = entity_instances.get(entity, 1)

        # Embedded BRs inherit host multi_count
        has_embedded_brs = bool(proc.get("embedded_brs", []))
        if has_embedded_brs and count <= 1:
            count = 1

        # 5.5: Orthogonal expansion truncation — cap at 5
        count = min(count, 5)

        s4["multi_count"] = count
        s4["multi_instance"] = count > 1
        dim_count = entity_dim_count.get(entity, 0)
        if entity in ves:
            dim_count = ve_dim_count.get(entity, dim_count)
        s4["multi_reason"] = (
            f"entity={entity} dim_count={dim_count} instances={count}"
        )

        # Duplicate procedures for multi-instance
        # BUGFIX #23: moved `import copy` to module top (was inside loop)
        base_id = proc["temp_id"]
        for instance_num in range(1, count + 1):
            instance_proc = copy.deepcopy(proc)
            if count > 1:
                instance_proc["temp_id"] = f"{base_id}.{instance_num}"
            instance_proc["_S4_fields"] = dict(s4)
            instance_proc["_S4_fields"]["multi_count"] = count
            expanded.append(instance_proc)

    multi_expanded = sum(1 for p in expanded if p.get("_S4_fields", {}).get("multi_instance"))
    total_instances = len(expanded)
    warnings.append(
        f"S4: {total_instances} total instances ({multi_expanded} procedures with multi-instance), "
        f"entity_instances={entity_instances}"
    )

    # ── Dependency reference repair ──
    # When a procedure is multi-instance-expanded, its original temp_id (e.g.
    # "PROC-001") is replaced by suffixed IDs ("PROC-001.1", "PROC-001.2").
    # S3 dependencies that referenced the original ID become dangling.
    # Fix: rewrite dependency references — original ID → all instance IDs.
    # Single-instance procedures (count==1) keep their original ID, no fix needed.
    expanded_ids_by_base: dict[str, list[str]] = {}
    for p in expanded:
        tid = p["temp_id"]
        if "." in tid:
            base, _ = tid.rsplit(".", 1)
            expanded_ids_by_base.setdefault(base, []).append(tid)
    if expanded_ids_by_base:
        for p in expanded:
            s3 = p.get("_S3_fields", {})
            for field in ("dependencies", "weak_dependencies"):
                deps = s3.get(field, [])
                if not deps:
                    continue
                new_deps: list[str] = []
                seen: set[str] = set()
                for d in deps:
                    if d in expanded_ids_by_base:
                        # Replace original ID with all instance IDs
                        for inst_id in expanded_ids_by_base[d]:
                            if inst_id != p["temp_id"] and inst_id not in seen:
                                new_deps.append(inst_id)
                                seen.add(inst_id)
                    elif d not in seen and d != p["temp_id"]:
                        new_deps.append(d)
                        seen.add(d)
                s3[field] = new_deps

    return {
        "procedures": expanded,
        "entity_instance_counts": entity_instances,
        "warnings": warnings,
        "errors": errors,
        "current_stage": "s4",
    }
