"""S3 Dependency Binding Node.

Deterministic dependency binding between procedures, faithfully replicating
the V2 JS engine's S3 stage. Optimized for O(n log n) performance.
"""
from models.state import AgentState


def s3_dependency_node(state: AgentState) -> dict:
    """S3: Bind dependencies between procedures.
    
    Two types of dependencies:
    - Strong: transition dependency (upstream_map) + sequential (same entity/dim, lower chain_depth)
    - Weak: cross-entity side_effects (TO.side_effects → target_entity reference)
    
    Cycle detection uses a lightweight DFS instead of NetworkX simple_cycles.
    """
    procedures = list(state.get("procedures", []))
    warnings = list(state.get("warnings", []))
    errors = list(state.get("errors", []))
    
    upstream_map = state["transition_upstream_map"]
    cm = state["coverage_model"]
    tos = cm.get("transition_obligations", [])
    cos = cm.get("cross_entity_obligations", [])
    
    # Build procedure lookup indices (O(n))
    proc_by_id = {p["temp_id"]: p for p in procedures}
    proc_by_entity = {}  # entity → [proc]
    for proc in procedures:
        proc_by_entity.setdefault(proc["entity"], []).append(proc)
    
    # Build TO lookup by ID
    to_by_id = {to["id"]: to for to in tos}
    
    # Build transition_id → proc_ids mapping (O(n))
    trans_id_to_proc_ids = {}
    for proc in procedures:
        for sid in proc.get("source_ids", []):
            to = to_by_id.get(sid)
            if to and to.get("transition_id"):
                trans_id_to_proc_ids.setdefault(to["transition_id"], []).append(proc["temp_id"])
    
    # Build CO id → proc_ids mapping
    co_by_id = {co["id"]: co for co in cos}
    
    # Build enabler state → proc_ids mapping for CO dependencies (O(n))
    enabler_state_to_procs = {}  # (entity, state_in_post) → [proc_id]
    for proc in procedures:
        post = proc.get("post_state", "")
        entity = proc["entity"]
        # Parse post_state format: "E-PRJ.项目状态→待开始"
        if "→" in post:
            state_part = post.split("→")[-1].split("(")[0].strip()
            key = (entity, state_part)
            enabler_state_to_procs.setdefault(key, []).append(proc["temp_id"])
    
    # Entity + dimension → sorted proc ids for same-dimension chain ordering
    entity_dim_procs = {}
    for proc in procedures:
        if proc.get("dimension"):
            key = f"{proc['entity']}.{proc['dimension']}"
            entity_dim_procs.setdefault(key, []).append(proc["temp_id"])
    
    # ── Assign strong dependencies ──
    for proc in procedures:
        s3 = proc.get("_S3_fields", {})
        deps = set(s3.get("dependencies", []))
        
        # 1. Transition upstream dependencies (O(k) per proc)
        for sid in proc.get("source_ids", []):
            to = to_by_id.get(sid)
            if not to or not to.get("transition_id"):
                continue
            tid = to["transition_id"]
            for up_tid in upstream_map.get(tid, []):
                for up_proc_id in trans_id_to_proc_ids.get(up_tid, []):
                    if up_proc_id != proc["temp_id"]:
                        deps.add(up_proc_id)
        
        # 2. Same-entity same-dimension chain depth ordering (O(log n))
        if proc.get("dimension"):
            key = f"{proc['entity']}.{proc['dimension']}"
            same_dim_procs = entity_dim_procs.get(key, [])
            try:
                proc_idx = same_dim_procs.index(proc["temp_id"])
                if proc_idx > 0:
                    deps.add(same_dim_procs[proc_idx - 1])
            except ValueError:
                pass
        
        # 3. CO dependency — enabler proc is a dependency (O(k) lookup instead of O(n) scan)
        for sid in proc.get("source_ids", []):
            co = co_by_id.get(sid)
            if co:
                enabler_entity = co.get("enabler_entity")
                enabler_state = co.get("enabler_state")
                if enabler_entity and enabler_state:
                    # Direct lookup instead of scanning all procedures
                    key = (enabler_entity, enabler_state)
                    for match_id in enabler_state_to_procs.get(key, []):
                        if match_id != proc["temp_id"]:
                            deps.add(match_id)
        
        s3["dependencies"] = list(deps)
    
    # ── Assign weak dependencies (side_effects) ──
    # Build entity → proc_ids mapping for quick lookup
    entity_to_proc_ids = {}
    for proc in procedures:
        entity_to_proc_ids.setdefault(proc["entity"], []).append(proc["temp_id"])
    
    for proc in procedures:
        s3 = proc.get("_S3_fields", {})
        weak = set(s3.get("weak_dependencies", []))
        
        for sid in proc.get("source_ids", []):
            to = to_by_id.get(sid)
            if not to:
                continue
            for se in to.get("side_effects", []):
                target_entity = se.get("target_entity")
                if not target_entity:
                    continue
                # Direct lookup instead of scanning all procedures
                for other_id in entity_to_proc_ids.get(target_entity, []):
                    if other_id != proc["temp_id"]:
                        weak.add(other_id)
        
        s3["weak_dependencies"] = list(weak)
    
    # ── Lightweight cycle detection using DFS ──
    # Build adjacency list
    adj = {}
    for proc in procedures:
        pid = proc["temp_id"]
        adj[pid] = []
        for dep_id in proc.get("_S3_fields", {}).get("dependencies", []):
            adj[pid].append(dep_id)
        for dep_id in proc.get("_S3_fields", {}).get("weak_dependencies", []):
            adj[pid].append(dep_id)
    
    # DFS cycle detection
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {pid: WHITE for pid in adj}
    cycle_edges = []
    
    def dfs_cycle(node, path):
        color[node] = GRAY
        path.append(node)
        for neighbor in adj.get(node, []):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                # Found cycle - record it
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:]
                cycle_edges.append(cycle)
            elif color[neighbor] == WHITE:
                dfs_cycle(neighbor, path)
        path.pop()
        color[node] = BLACK
    
    for pid in list(adj.keys()):
        if color.get(pid) == WHITE:
            dfs_cycle(pid, [])
    
    if cycle_edges:
        # Break cycles by removing weakest deps
        warnings.append(f"S3 detected {len(cycle_edges)} dependency cycles")
        for cycle in cycle_edges[:10]:  # Limit to first 10 cycles
            # Try removing a weak dependency first
            broken = False
            for pid in cycle:
                proc = proc_by_id.get(pid)
                if not proc:
                    continue
                weak_deps = proc["_S3_fields"].get("weak_dependencies", [])
                if weak_deps:
                    removed = weak_deps.pop()
                    warnings.append(f"  Cycle break: removed weak dep {removed} from {pid}")
                    broken = True
                    break
            if not broken:
                # Remove a strong dependency
                for pid in cycle:
                    proc = proc_by_id.get(pid)
                    if not proc:
                        continue
                    strong_deps = proc["_S3_fields"].get("dependencies", [])
                    if strong_deps:
                        removed = strong_deps.pop()
                        warnings.append(f"  Cycle break: removed strong dep {removed} from {pid}")
                        broken = True
                        break
    
    # Dependency stats
    has_strong = sum(1 for p in procedures if p.get("_S3_fields", {}).get("dependencies"))
    has_weak = sum(1 for p in procedures if p.get("_S3_fields", {}).get("weak_dependencies"))
    warnings.append(f"S3 bound dependencies: {has_strong} with strong, {has_weak} with weak")
    
    return {
        "procedures": procedures,
        "warnings": warnings,
        "current_stage": "s3",
    }
