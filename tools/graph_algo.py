"""Graph algorithm utilities for P3 Agent Engine.

Replaces the chain depth calculation and cycle detection from the
original JavaScript V2 engine with NetworkX-based implementations.
"""
from __future__ import annotations

import networkx as nx
from typing import Optional


def detect_cycles_in_dependencies(procedures: list[dict]) -> list[list[str]]:
    """Detect cycles in procedure dependencies using NetworkX.

    Args:
        procedures: List of procedure dicts, each with a ``temp_id`` key
            and an ``_S3_fields`` dict containing ``dependencies`` and
            ``weak_dependencies`` lists.

    Returns:
        List of cycles, where each cycle is a list of temp_ids.
    """
    G = nx.DiGraph()
    for proc in procedures:
        G.add_node(proc["temp_id"])
        for dep_id in proc.get("_S3_fields", {}).get("dependencies", []):
            G.add_edge(dep_id, proc["temp_id"])
        for dep_id in proc.get("_S3_fields", {}).get("weak_dependencies", []):
            G.add_edge(dep_id, proc["temp_id"])

    try:
        cycle_edges = nx.find_cycle(G)
        cycle_nodes = [edge[0] for edge in cycle_edges]
        return [cycle_nodes]
    except nx.NetworkXNoCycle:
        return []


def break_cycles(procedures: list[dict]) -> tuple[list[dict], list[str]]:
    """Break dependency cycles by removing weakest dependencies.

    v29 #3: Confidence-based cycle breaking.
    ─────────────────────────────────────────────────────────────────────
    Replaces chain_depth-based ranking with causal confidence ranking.
    Each dep carries an `origin` string (recorded by S3 when the dep was
    added) that maps to a confidence score (see s3_dependency.DEP_CONFIDENCE):

        5  transition_upstream  (causal chain — authoritative)
        5  guard1_state_pred    (exact state-machine predecessor)
        4  co_enabler           (CO enabler_state binding)
        4  ve_co_ids            (Virtual entity CO binding)
        3  chain_ordering       (same-dim sort_key ordering)
        3  guard5_create_use    (create-before-use heuristic)
        2  guard6_precond       (precondition TEXT matching — fragile)
        1  weak_side_effect     (weak dep)

    Category priority (unchanged from v28):
      0  weak deps — always safe to remove first
      1  same-entity strong deps — prefer to keep
      2  cross-entity strong deps — keep if possible

    Within a category, prefer removing deps with LOWER confidence.
    Confidence ties are broken by chain_depth (deeper = preferentially
    removed) to preserve v28 behavior as a last-resort tiebreaker.

    Args:
        procedures: List of procedure dicts to fix. Mutated in place.

    Returns:
        (fixed_procedures, removal_log) where removal_log is a list of
        human-readable strings describing what was removed.
    """
    import networkx as nx

    # Confidence map — kept in sync with s3_dependency.DEP_CONFIDENCE.
    # Inlined here to avoid a circular import (s3_dependency imports
    # break_cycles from this module).
    # 2026-08-14: co_enabler_both_lateral / co_enabler_phase_inversion 必须
    # 同时注册——缺失任一都会 conf 归 0, break_cycles 优先剪 CO 弱边、恢复
    # 倒退边 (实测)。双表同步是已知维护陷阱, 详见 DECISIONS。
    DEP_CONFIDENCE = {
        "transition_upstream": 5,
        "guard1_state_pred": 5,
        "co_enabler": 4,
        "co_enabler_both_lateral": 4,
        "co_enabler_phase_inversion": 4,
        "ve_co_ids": 4,
        "chain_ordering": 3,
        "guard5_create_use": 3,
        "guard6_precond": 2,
        "weak_side_effect": 1,
        "guard2_constraint_gate": 3,  # rare/no-op in practice
    }

    def _confidence(origin: str) -> int:
        return DEP_CONFIDENCE.get(origin, 0)

    warnings: list[str] = []

    proc_by_id = {p["temp_id"]: p for p in procedures}

    def _is_cross_entity(proc_id: str, dep_id: str) -> bool:
        p_entity = proc_by_id.get(proc_id, {}).get("entity", "")
        d_entity = proc_by_id.get(dep_id, {}).get("entity", "")
        return p_entity != d_entity

    def _origin_of(proc_id: str, dep_id: str, is_weak: bool) -> str:
        """Look up the origin of a dep. Falls back to 'weak_side_effect'
        for weak deps with no recorded origin, and 'chain_ordering' for
        strong deps with no recorded origin (v28 compatibility)."""
        s3 = proc_by_id.get(proc_id, {}).get("_S3_fields", {})
        if is_weak:
            return s3.get("weak_origins", {}).get(dep_id, "weak_side_effect")
        return s3.get("dep_origins", {}).get(dep_id, "chain_ordering")

    max_cycles = len(procedures) * 3  # generous upper bound for dense graphs
    broke_count = 0

    for _ in range(max_cycles):
        # Build fresh graph
        G = nx.DiGraph()
        for proc in procedures:
            G.add_node(proc["temp_id"])
            for dep_id in proc.get("_S3_fields", {}).get("dependencies", []):
                G.add_edge(dep_id, proc["temp_id"])
            for dep_id in proc.get("_S3_fields", {}).get("weak_dependencies", []):
                G.add_edge(dep_id, proc["temp_id"])

        try:
            cycle_edges = nx.find_cycle(G)
        except nx.NetworkXNoCycle:
            break  # No more cycles

        cycle_nodes = list({edge[0] for edge in cycle_edges})

        # Build removal candidates for this cycle.
        # Tuple layout: (category, confidence, -depth, dep_id, proc_id)
        # → sorted ascending; first element = lowest category (weak first),
        #   then lowest confidence (prefer cut), then deepest chain_depth
        #   (prefer cut, v28 behavior preserved as tiebreaker).
        candidates: list[tuple[int, int, int, str, str]] = []

        for proc_id in cycle_nodes:
            proc = proc_by_id.get(proc_id)
            if not proc:
                continue
            s2 = proc.get("_S2_fields", {})
            depth = s2.get("chain_depth", 0)

            for dep_id in proc.get("_S3_fields", {}).get("weak_dependencies", []):
                if dep_id in cycle_nodes:
                    origin = _origin_of(proc_id, dep_id, is_weak=True)
                    conf = _confidence(origin)
                    candidates.append((0, conf, -depth, dep_id, proc_id))

            for dep_id in proc.get("_S3_fields", {}).get("dependencies", []):
                if dep_id in cycle_nodes:
                    cross = _is_cross_entity(proc_id, dep_id)
                    category = 2 if cross else 1
                    origin = _origin_of(proc_id, dep_id, is_weak=False)
                    conf = _confidence(origin)
                    candidates.append((category, conf, -depth, dep_id, proc_id))

        candidates.sort()

        if not candidates:
            warnings.append(f"Cannot break cycle (no removable candidates): {cycle_nodes[:5]}...")
            break

        # Remove the best candidate: lowest category → lowest confidence → deepest chain_depth
        # NOTE: ascending on +confidence (not -confidence) is deliberate — ascending
        # on -confidence selected the HIGHEST-confidence edge for removal, the
        # inverse of the documented intent, silently destroying authoritative
        # deps (guard1/transition_upstream) whenever a cycle mixed edge types.
        category, conf, _, dep_id, proc_id = candidates[0]
        proc = proc_by_id[proc_id]
        cat_name = {0: "weak", 1: "same-entity strong", 2: "cross-entity strong"}.get(category, "unknown")
        origin = _origin_of(proc_id, dep_id, is_weak=(category == 0))

        if dep_id in proc.get("_S3_fields", {}).get("weak_dependencies", []):
            proc["_S3_fields"]["weak_dependencies"].remove(dep_id)
        else:
            proc["_S3_fields"]["dependencies"].remove(dep_id)
        # 同一 dep 可能在两个 origin 表中都登记过: 弱依赖在加入 weak_dependencies
        # 时经 _record_origin(mid, "weak_side_effect") 双写进 dep_origins(置信降级)。
        # 只弹本分支的表会留下幽灵键——V01 把 dep_origins 键当硬边读, 残留环因此
        # 永远剪不干净。故无论从哪个列表剪除, 两个 origin 表都同步 pop。
        proc["_S3_fields"].get("dep_origins", {}).pop(dep_id, None)
        proc["_S3_fields"].get("weak_origins", {}).pop(dep_id, None)

        warnings.append(
            f"Cycle break: removed {cat_name} dependency {dep_id} from {proc_id} "
            f"(origin={origin}, confidence={conf}, depth={-candidates[0][2]})"
        )
        broke_count += 1

    return procedures, warnings


def topological_sort_procedures(
    procedures: list[dict],
    sort_key_field: str = "_S2_fields",
) -> list[dict]:
    """Standard Kahn topological sort with sort_key as priority tiebreaker.

    Dependencies are hard constraints (A depends on B → B before A).
    sort_key defines the preferred order among procedures at the same
    topological "level" (i.e. whose dependencies are all satisfied).

    sort_key layout (from S2, 7-dimensional):
      [phase, topology_level, type_priority, operation_lifecycle,
       chain_depth, dimension_priority, gen_seq]

    Auxiliary validation (Type7/8/9) has op_lifecycle=0 and type_priority=5-6,
    so within the same phase they naturally sort after primary flow
    (Type1 op_lifecycle=1-4, type_priority=1-4) without needing a separate
    flow_layer dimension or phase-grouped sorting.
    """
    import heapq

    proc_by_id = {p["temp_id"]: p for p in procedures}

    def _sort_key(proc: dict) -> list:
        return list(proc.get(sort_key_field, {}).get("sort_key", []))

    # ── Build adjacency graph: dep_id → [dependent_ids] ──
    adjacency: dict[str, list[str]] = {p["temp_id"]: [] for p in procedures}
    in_degree: dict[str, int] = {p["temp_id"]: 0 for p in procedures}

    for proc in procedures:
        pid = proc["temp_id"]
        s3 = proc.get("_S3_fields", {})
        all_deps = s3.get("dependencies", [])
        for dep_id in all_deps:
            if dep_id in adjacency:
                adjacency[dep_id].append(pid)
                in_degree[pid] += 1

    # ── Kahn's algorithm with sort_key priority ──
    heap: list[tuple[tuple, str]] = []
    for proc in procedures:
        if in_degree[proc["temp_id"]] == 0:
            heapq.heappush(heap, (tuple(_sort_key(proc)), proc["temp_id"]))

    result: list[dict] = []
    while heap:
        _, pid = heapq.heappop(heap)
        result.append(proc_by_id[pid])
        for neighbor in adjacency.get(pid, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                heapq.heappush(heap, (tuple(_sort_key(proc_by_id[neighbor])), neighbor))

    # Fallback for remaining procs (cycles not broken)
    if len(result) < len(procedures):
        remaining = [p for p in procedures if p["temp_id"] not in
                     {r["temp_id"] for r in result}]
        remaining.sort(key=_sort_key)
        result.extend(remaining)

    return result
