"""Graph algorithm utilities for P3 Agent Engine.

Replaces the chain depth calculation and cycle detection from the
original JavaScript V2 engine with NetworkX-based implementations.
"""

import networkx as nx
from typing import Optional


def build_transition_graph(
    transition_upstream_map: dict[str, list[str]],
) -> nx.DiGraph:
    """Build a directed graph from the transition upstream map.

    Edges go from upstream → downstream (upstream must complete before
    downstream).

    Args:
        transition_upstream_map: Mapping of transition ID to its list of
            upstream transition IDs.

    Returns:
        A NetworkX directed graph representing the transition dependencies.
    """
    G = nx.DiGraph()
    for tid, upstreams in transition_upstream_map.items():
        G.add_node(tid)
        for uid in upstreams:
            G.add_edge(uid, tid)
    return G


def calc_chain_depth(
    transition_upstream_map: dict[str, list[str]],
    transition_id: str,
) -> int:
    """Calculate the chain depth for a transition using memoized DFS.

    Returns 0 for transitions with no upstreams, MAX(upstream_depth)+1
    otherwise. Handles cycles by returning 0 for currently-computing nodes.

    Args:
        transition_upstream_map: Mapping of transition ID to its list of
            upstream transition IDs.
        transition_id: The transition ID to compute depth for.

    Returns:
        The chain depth of the specified transition.
    """
    depth_cache: dict[str, int] = {}
    computing: set[str] = set()

    def _calc(tid: str) -> int:
        if tid in depth_cache:
            return depth_cache[tid]
        if tid in computing:
            return 0  # cycle guard
        computing.add(tid)
        upstreams = transition_upstream_map.get(tid, [])
        if not upstreams:
            depth = 0
        else:
            depth = max(_calc(uid) for uid in upstreams) + 1
        computing.discard(tid)
        depth_cache[tid] = depth
        return depth

    # Pre-compute all depths
    for tid in transition_upstream_map:
        _calc(tid)

    return depth_cache.get(transition_id, 0)


def calc_all_chain_depths(
    transition_upstream_map: dict[str, list[str]],
) -> dict[str, int]:
    """Calculate chain depths for all transitions.

    Args:
        transition_upstream_map: Mapping of transition ID to its list of
            upstream transition IDs.

    Returns:
        Dictionary mapping each transition ID to its chain depth.
    """
    depth_cache: dict[str, int] = {}
    computing: set[str] = set()

    def _calc(tid: str) -> int:
        if tid in depth_cache:
            return depth_cache[tid]
        if tid in computing:
            return 0
        computing.add(tid)
        upstreams = transition_upstream_map.get(tid, [])
        depth = max((_calc(uid) for uid in upstreams), default=-1) + 1
        computing.discard(tid)
        depth_cache[tid] = depth
        return depth

    for tid in transition_upstream_map:
        _calc(tid)
    return depth_cache


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

    Uses NetworkX to find ALL simple cycles, then removes one edge from
    each cycle to make the graph acyclic. Removal follows the same priority
    as the architecture's oscillation handler (I23):
      1. Weak deps — always safe to remove
      2. Same-entity strong deps (chain ordering) — lower priority to keep
      3. Cross-entity strong deps (transition upstream, CO enabler) — keep if possible
    Within each category, prefer removing deps with deeper chain_depth.

    Args:
        procedures: List of procedure dicts to fix. These are mutated in place.

    Returns:
        A tuple of (fixed_procedures, removal_log) where removal_log is
        a list of human-readable strings describing what was removed.
    """
    import networkx as nx

    warnings: list[str] = []

    proc_by_id = {p["temp_id"]: p for p in procedures}

    def _is_cross_entity(proc_id: str, dep_id: str) -> bool:
        p_entity = proc_by_id.get(proc_id, {}).get("entity", "")
        d_entity = proc_by_id.get(dep_id, {}).get("entity", "")
        return p_entity != d_entity

    # Iteratively find and break cycles one at a time.
    # Use a fresh graph on each iteration so we don't miss cycles that
    # depend on edges already removed from a cached NetworkX object.
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

        # Build removal candidates for this cycle
        candidates: list[tuple[int, int, str, str]] = []  # (category, -depth, dep_id, proc_id)

        for proc_id in cycle_nodes:
            proc = proc_by_id.get(proc_id)
            if not proc:
                continue
            s2 = proc.get("_S2_fields", {})
            depth = s2.get("chain_depth", 0)

            for dep_id in proc.get("_S3_fields", {}).get("weak_dependencies", []):
                if dep_id in cycle_nodes:
                    candidates.append((0, -depth, dep_id, proc_id))

            for dep_id in proc.get("_S3_fields", {}).get("dependencies", []):
                if dep_id in cycle_nodes:
                    cross = _is_cross_entity(proc_id, dep_id)
                    category = 2 if cross else 1
                    candidates.append((category, -depth, dep_id, proc_id))

        candidates.sort()

        if not candidates:
            warnings.append(f"Cannot break cycle (no removable candidates): {cycle_nodes[:5]}...")
            break

        # Remove the best candidate (lowest category, then highest depth)
        category, _, dep_id, proc_id = candidates[0]
        proc = proc_by_id[proc_id]
        cat_name = {0: "weak", 1: "same-entity strong", 2: "cross-entity strong"}.get(category, "unknown")

        if dep_id in proc.get("_S3_fields", {}).get("weak_dependencies", []):
            proc["_S3_fields"]["weak_dependencies"].remove(dep_id)
        else:
            proc["_S3_fields"]["dependencies"].remove(dep_id)

        warnings.append(
            f"Cycle break: removed {cat_name} dependency {dep_id} from {proc_id}"
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
