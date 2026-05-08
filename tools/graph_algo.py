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

    cycles = list(nx.simple_cycles(G))
    return cycles


def break_cycles(procedures: list[dict]) -> tuple[list[dict], list[str]]:
    """Break dependency cycles by removing weakest dependencies.

    Strategy: remove weak deps first (highest chain_depth), then strong deps.

    Args:
        procedures: List of procedure dicts to fix. These are mutated
            in place.

    Returns:
        A tuple of (fixed_procedures, removal_log) where removal_log is
        a list of human-readable strings describing what was removed.
    """
    warnings: list[str] = []
    max_iterations = len(procedures)

    for _ in range(max_iterations):
        cycles = detect_cycles_in_dependencies(procedures)
        if not cycles:
            break

        cycle = cycles[0]
        # Try to break by removing a weak dependency in the cycle
        broke = False
        for proc in procedures:
            if proc["temp_id"] not in cycle:
                continue
            weak_deps = proc["_S3_fields"]["weak_dependencies"]
            if weak_deps:
                # Remove the weak dep with highest chain_depth
                removed = weak_deps.pop()
                warnings.append(
                    f"Cycle break: removed weak dependency {removed} from {proc['temp_id']}"
                )
                broke = True
                break

        if not broke:
            # Remove a strong dependency (highest chain_depth)
            for proc in procedures:
                if proc["temp_id"] not in cycle:
                    continue
                strong_deps = proc["_S3_fields"]["dependencies"]
                if strong_deps:
                    removed = strong_deps.pop()
                    warnings.append(
                        f"Cycle break: removed strong dependency {removed} from {proc['temp_id']}"
                    )
                    broke = True
                    break

        if not broke:
            warnings.append(f"Cannot break cycle: {cycle}")
            break

    return procedures, warnings


def topological_sort_procedures(
    procedures: list[dict],
    sort_key_field: str = "_S2_fields",
) -> list[dict]:
    """Sort procedures by sort_key while respecting dependency order.

    Uses topological sort on dependencies, then by sort_key within each
    level.

    Args:
        procedures: List of procedure dicts to sort.
        sort_key_field: The field name containing the ``sort_key`` list
            (default ``_S2_fields``).

    Returns:
        A new list of procedures sorted in topological order, with
        sort_key as a tiebreaker within the same topological level.
    """
    G = nx.DiGraph()
    for proc in procedures:
        G.add_node(proc["temp_id"])
        for dep_id in proc.get("_S3_fields", {}).get("dependencies", []):
            G.add_edge(dep_id, proc["temp_id"])

    try:
        topo_order = list(nx.topological_sort(G))
    except nx.NetworkXUnfeasible:
        # Fallback to sort_key only
        topo_order = [p["temp_id"] for p in procedures]

    # Create ordering map
    order_map = {tid: i for i, tid in enumerate(topo_order)}

    # Sort by topological order, then by sort_key within same level
    def sort_key(proc: dict) -> tuple[int, list]:
        topo_idx = order_map.get(proc["temp_id"], 999999)
        sk = proc.get(sort_key_field, {}).get("sort_key", [])
        return (topo_idx, sk)

    return sorted(procedures, key=sort_key)
