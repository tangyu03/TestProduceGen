"""S0 Topology Discovery Node — Deterministic Implementation (V3).

Implements all sub-stages S0.1–S0.7, aligned with V2 JS engine gold standard:
  S0.1: Relation loading (structural_relations + transition_relations)
  S0.2: Primary entity identification
  S0.3: Phase table derivation (longest-path DAG, not BFS shortest-path)
  S0.4: Dependent entity detection (entity_parent, dependency_depth)
  S0.5: Topology levels
  S0.6: Upstream map rebuilding
  S0.7: Virtual entity decomposition (CO-causal multi-parent, not structural)

Falls back to LLM only if deterministic computation fails.
No dependency on pre-computed p3_s2_s3_s4_result.json.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from models.state import AgentState


# ---------------------------------------------------------------------------
# Dynamic map builders — read from coverage_model._context at runtime
# ---------------------------------------------------------------------------

def _build_entity_name_map(cm: dict) -> dict[str, str]:
    """Build Chinese-name → entity-ID map from coverage_model._context.entity_details."""
    ctx = cm.get('_context', {})
    return {e['name']: e['id'] for e in ctx.get('entity_details', []) if e.get('name') and e.get('id')}


def _build_role_map(cm: dict) -> dict[str, str]:
    """Build role-ID → role-name map from coverage_model._context.roles."""
    ctx = cm.get('_context', {})
    m = {r['id']: r['name'] for r in ctx.get('roles', []) if r.get('id') and r.get('name')}
    m['system'] = '系统'
    return m


def _build_managed_entities(cm: dict) -> set[str]:
    """Build set of entity IDs with type='managed' (L0 candidates).

    These are configurable/independent entities that are not part of the
    primary entity's dependency chain — equivalent to the old hardcoded
    L0_L1_L5_ENTITIES.
    """
    ctx = cm.get('_context', {})
    return {e['id'] for e in ctx.get('entity_details', []) if e.get('type') == 'managed'}


# ---------------------------------------------------------------------------
# Domain-constant maps (truly invariant across projects)
# ---------------------------------------------------------------------------

HUMAN_DECISION_KEYWORDS = {
    '审核', '审批', '确认', '收款', '付款', '核验',
    '发样', '收样', '退回', '驳回', '撤销', '签订', '签署', '发布'
}

AUTO_KEYWORDS = {'初始化', '自动', '同步', '驱动', '触发条件'}

TYPE_PRIORITY_MAP = {
    'happy': 1, 'branch': 2, 'constraint': 3, 'audit': 4,
    'crud': 5, 'rule': 6, 'lifecycle': 7, 'cross': 8, 'invalid': 9,
    'data_constraint': 3, 'time_sensitive': 3, 'rollback': 4,
    'negative': 9, 'audit_rejection': 4
}

TYPE5_SPECIAL_OPS = {'删除', '审核', '状态变更', '撤销', '退回', '退款', '发布'}


# ---------------------------------------------------------------------------
# S0.1: Relation loading
# ---------------------------------------------------------------------------

def _load_relations(cm: dict) -> tuple[list[dict], list[dict]]:
    """S0.1: Load structural_relations and transition_relations from _context."""
    ctx = cm.get('_context', {})
    structural = ctx.get('structural_relations', [])
    transition = ctx.get('transition_relations', [])

    seen: dict[tuple, dict] = {}
    for rel in structural:
        key = (rel.get('from'), rel.get('to'))
        if key not in seen or rel.get('confidence', '') == 'high':
            seen[key] = rel
    deduped_structural = list(seen.values())

    return deduped_structural, transition


# ---------------------------------------------------------------------------
# S0.2: Primary entity identification
# ---------------------------------------------------------------------------

def _identify_primary_entity(
    structural: list[dict],
    transition: list[dict],
    tos: list[dict],
) -> str:
    """S0.2: Identify primary_entity by weighted frequency on structural from-side.

    Weights: high=2, medium=1, low=0.5. transition_relations not counted.
    Tie-break: multi-state > longest chain. Container-priority override.
    """
    freq: dict[str, float] = defaultdict(float)
    entity_has_multi_state: dict[str, bool] = {}

    for rel in structural:
        f = rel.get('from', '')
        if not f:
            continue
        w = {'high': 2, 'medium': 1, 'low': 0.5}.get(rel.get('confidence', 'low'), 0.5)
        freq[f] += w

    for to in tos:
        e = to.get('entity', '')
        dim = to.get('dimension', '')
        if dim:
            entity_has_multi_state[e] = True

    if not freq:
        if tos:
            return tos[0].get('entity', '')
        return ''

    candidates = sorted(freq.keys(), key=lambda e: freq[e], reverse=True)

    if len(candidates) == 1:
        primary = candidates[0]
    else:
        top_freq = freq[candidates[0]]
        top_group = [c for c in candidates if freq[c] == top_freq]
        if len(top_group) > 1:
            top_group.sort(key=lambda e: (entity_has_multi_state.get(e, False), freq[e]), reverse=True)
        primary = top_group[0]

    # Container-priority override: if a child has initial transitions, keep parent
    for candidate in candidates:
        if candidate == primary:
            continue
        is_child = any(
            r.get('from') == primary and r.get('to') == candidate
            and r.get('relation_type') == 'composition'
            for r in structural
        )
        if not is_child:
            continue
        p_multi = entity_has_multi_state.get(primary, False)
        c_multi = entity_has_multi_state.get(candidate, False)
        if p_multi and not c_multi:
            pass
        elif freq[primary] >= freq[candidate] * 0.5 and p_multi:
            pass
        else:
            continue
        c_null_froms = [t for t in tos if t.get('entity') == candidate and t.get('from') is None]
        if not c_null_froms:
            continue
        break  # keep primary as-is

    return primary


# ---------------------------------------------------------------------------
# S0.3: Phase table derivation (LONGEST PATH IN DAG)
# ---------------------------------------------------------------------------

def _derive_phase_table(primary: str, tos: list[dict], cos: list[dict]) -> dict:
    """Derive primary_dimension and state_to_phase via longest-path in DAG.

    Uses longest path (not BFS shortest path) so that skip-transitions
    (e.g., 待开始→进行中) do NOT collapse phases. Each state on the main
    progression line gets its own phase number.

    Algorithm:
    1. Build DAG of states from transitions (from → to edges)
    2. Find initial states (from=null)
    3. Topological sort, assign phase = max(predecessor_phases) + 1
    """
    # Determine primary_dimension
    dim_freq: dict[str, int] = defaultdict(int)
    for co in cos:
        if co.get('causal_type') == 'constraint' and co.get('enabler_entity') == primary:
            dim = co.get('enabler_dimension', '')
            if dim:
                dim_freq[dim] += 1

    if dim_freq:
        primary_dimension = max(dim_freq, key=dim_freq.get)
    else:
        dim_state_count: dict[str, int] = defaultdict(int)
        for to in tos:
            if to.get('entity') == primary and to.get('dimension'):
                dim_state_count[to['dimension']] += 1
        primary_dimension = max(dim_state_count, key=dim_state_count.get) if dim_state_count else ''

    primary_tos = [t for t in tos if t.get('entity') == primary and t.get('dimension') == primary_dimension]

    state_to_phase: dict[str, dict[str, int]] = {primary_dimension: {}}
    if not primary_tos:
        phase_names = ['P0']
        return {
            'primary_dimension': primary_dimension,
            'state_to_phase': state_to_phase,
            'phase_names': phase_names,
            'phase_count': 1,
        }

    # Build DAG and find initial states
    graph: dict[str, list[str]] = defaultdict(list)  # from → [to]
    in_degree: dict[str, int] = defaultdict(int)
    all_states = set()
    initial_states = set()

    for to in primary_tos:
        f = to.get('from')
        t = to.get('to')
        if t:
            all_states.add(t)
        if f:
            all_states.add(f)
            graph[f].append(t)
            in_degree[t] = in_degree.get(t, 0) + 1
        else:
            initial_states.add(t)
            all_states.add(t)

    # Ensure all states have in_degree entry
    for s in all_states:
        if s not in in_degree:
            in_degree[s] = 0

    # Longest path via topological sort
    phase_map: dict[str, int] = {s: 0 for s in initial_states}

    # Kahn's algorithm for topological sort with longest path tracking
    queue = deque([s for s in all_states if in_degree.get(s, 0) == 0])
    topo_order = []
    remaining_in = dict(in_degree)

    while queue:
        node = queue.popleft()
        topo_order.append(node)
        if node not in phase_map:
            phase_map[node] = 0
        for nxt in graph.get(node, []):
            # Longest path: take max of all predecessor phases + 1
            phase_map[nxt] = max(phase_map.get(nxt, 0), phase_map[node] + 1)
            remaining_in[nxt] = remaining_in.get(nxt, 1) - 1
            if remaining_in.get(nxt, 0) <= 0:
                queue.append(nxt)

    # Handle any unvisited states (cycles or disconnected)
    for s in all_states:
        if s not in phase_map:
            phase_map[s] = 0

    max_phase = max(phase_map.values()) if phase_map else 0
    phase_names = [f'P{i}' for i in range(max_phase + 1)]

    state_to_phase = {primary_dimension: phase_map}

    return {
        'primary_entity': primary,
        'primary_dimension': primary_dimension,
        'state_to_phase': state_to_phase,
        'phase_names': phase_names,
        'phase_count': max_phase + 1,
    }


def _classify_state_types(tos: list[dict], primary: str) -> dict[str, dict[str, dict[str, str]]]:
    """S0.3 step 5: Classify states as driving/side_effect.

    A state is side_effect if ALL transitions reaching it are rollback/rejection
    paths.  If ANY driving transition reaches the state, it is driving.

    Detection sources (in priority order):
    1. risk_traits / traits field containing 'rollback'
    2. desc / description / action field containing side-effect keywords
    """
    state_type_map: dict[str, dict[str, dict[str, str]]] = defaultdict(lambda: defaultdict(dict))
    side_effect_keywords = {'退', '撤销', '退款', '驳回'}

    # Two-pass: first collect which states have at least one driving inbound
    driving_states: dict[tuple[str, str, str], bool] = {}  # (entity, dim, target) → has_driving

    for to in tos:
        entity = to.get('entity', '')
        dim = to.get('dimension', '')
        target = to.get('to', '')
        if not target:
            continue

        # Check multiple fields for side-effect signals
        desc = to.get('desc', '') or to.get('description', '') or ''
        action = to.get('action', '') or ''
        risk_traits = to.get('risk_traits', []) or to.get('traits', []) or []

        is_se = (
            any(kw in desc for kw in side_effect_keywords)
            or any(kw in action for kw in side_effect_keywords)
            or 'rollback' in risk_traits
        )

        if entity == primary:
            state_type_map[entity][dim][target] = 'driving'
            continue

        key = (entity, dim, target)
        if not is_se:
            # This transition reaches the state as driving
            driving_states[key] = True

    # Second pass: classify each (entity, dim, target)
    for to in tos:
        entity = to.get('entity', '')
        dim = to.get('dimension', '')
        target = to.get('to', '')
        if not target or entity == primary:
            continue

        key = (entity, dim, target)
        # If ANY transition reaches this state as driving → driving
        # Only side_effect if ALL inbound transitions are rollback/rejection
        if driving_states.get(key):
            state_type_map[entity][dim][target] = 'driving'
        else:
            state_type_map[entity][dim][target] = 'side_effect'

    return dict(state_type_map)


def _derive_dep_state_phase_map(
    primary: str,
    phase_table: dict,
    tos: list[dict],
    dependent_entities: list[str],
    entity_parent: dict,
    state_type_map: dict,
    transition_upstream_map: dict,
    virtual_entities: dict,
    cos: list[dict] = None,
) -> tuple[dict, dict]:
    """S0.3 step 3: Dependent entity phase mapping via anchor-entity method.

    Returns (dep_state_phase_map, contextual_phase_rules).
    """
    dep_map: dict[str, dict[str, dict[str, int]]] = {}
    ctx_rules: dict[str, dict] = {}

    all_entities = list(dependent_entities) + list(virtual_entities.keys())

    for entity in all_entities:
        if entity == primary:
            continue

        is_ve = entity in virtual_entities
        ve_info = virtual_entities.get(entity, {})
        anchor = ve_info.get('parent_entity') if is_ve else entity_parent.get(entity)

        if not anchor:
            dep_map[entity] = {}
            continue

        # For VEs: all states share the resolved_phase (flat mapping)
        # VE is a projection of original entity in a specific context,
        # not an independent state machine
        if is_ve:
            actual_entity = ve_info.get('original_entity', entity)
            entity_tos = [t for t in tos if t.get('entity') == actual_entity]
            dim_map: dict[str, dict[str, int]] = defaultdict(dict)
            for to in entity_tos:
                dim = to.get('dimension', '')
                target = to.get('to', '')
                if dim and target:
                    # All VE states get the same phase (resolved_phase)
                    # Will be updated after dep_state_phase_map is computed
                    dim_map[dim][target] = 0  # placeholder, updated by _resolve_ve_phases
            dep_map[entity] = dict(dim_map)
            continue

        # For non-VE entities, compute phase via longest-path DAG
        entity_tos = [t for t in tos if t.get('entity') == entity]
        dim_map: dict[str, dict[str, int]] = defaultdict(dict)
        dim_tos: dict[str, list[dict]] = defaultdict(list)
        for to in entity_tos:
            dim = to.get('dimension', '')
            if dim:
                dim_tos[dim].append(to)

        for dim, dim_transitions in dim_tos.items():
            # Build state graph for this dimension, keyed by (from_state, to_state)
            # so we can look up whether a specific edge is a rollback.
            state_graph: dict[str, list[str]] = defaultdict(list)
            edge_is_se: dict[tuple[str, str], bool] = {}  # (from, to) → is_side_effect
            initial_states = set()
            all_states = set()

            se_keywords = {'退', '撤销', '退款', '驳回'}

            for to in dim_transitions:
                f = to.get('from')
                t = to.get('to')
                if t:
                    all_states.add(t)
                if f:
                    all_states.add(f)
                    state_graph[f].append(t)
                    # Classify THIS TRANSITION (not the target state) as side_effect
                    desc = to.get('desc', '') or to.get('description', '') or ''
                    action = to.get('action', '') or ''
                    traits = to.get('risk_traits', []) or to.get('traits', []) or []
                    is_se = (
                        any(kw in desc for kw in se_keywords)
                        or any(kw in action for kw in se_keywords)
                        or 'rollback' in traits
                    )
                    edge_is_se[(f, t)] = is_se
                else:
                    initial_states.add(t)
                    all_states.add(t)

            # Determine entry phase for initial states via upstream anchoring
            entry_phase = _compute_entry_phase(entity, anchor, dim, tos, phase_table, dep_map, transition_upstream_map, cos=cos)

            # Use Bellman-Ford iterative propagation (handles cycles naturally).
            # Rollback/side_effect edges only assign phase to UNASSIGNED targets
            # (at source's phase level) and NEVER increase an already-assigned
            # target.  This prevents cycle inflation: a cycle like
            # 待评价→评价中(driving)→待评价(rollback) has net increment > 0
            # if rollback simply uses increment=0, because max() keeps pushing
            # the driving side up.  By refusing to increase already-assigned
            # states via rollback edges, the cycle converges.
            UNASSIGNED = -1
            state_phase: dict[str, int] = {s: UNASSIGNED for s in all_states}
            for s in initial_states:
                state_phase[s] = entry_phase

            changed = True
            max_iterations = len(all_states) * 2
            iterations = 0
            while changed and iterations < max_iterations:
                changed = False
                iterations += 1
                for f_state, successors in state_graph.items():
                    if state_phase[f_state] == UNASSIGNED:
                        continue  # predecessor not yet reachable
                    for nxt in successors:
                        is_se = edge_is_se.get((f_state, nxt), False)
                        if is_se:
                            # Rollback/side-effect edge: only assign phase to
                            # unvisited targets (at source's level).  Never
                            # increase an already-assigned target's phase.
                            if state_phase[nxt] == UNASSIGNED:
                                state_phase[nxt] = state_phase[f_state]
                                changed = True
                        else:
                            # Driving edge: forward propagation with +1
                            new_phase = state_phase[f_state] + 1
                            if new_phase > state_phase[nxt]:
                                state_phase[nxt] = new_phase
                                changed = True

            # Fill any remaining unreachable states with entry_phase
            for s in all_states:
                if state_phase[s] == UNASSIGNED:
                    state_phase[s] = entry_phase

            dim_map[dim] = dict(state_phase)

        dep_map[entity] = dict(dim_map)

    # Detect contextual phase rules (multi-context dimensions)
    ctx_rules = _detect_contextual_phase_rules(primary, tos, dep_map, entity_parent, phase_table, transition_upstream_map)

    return dep_map, ctx_rules


def _compute_entry_phase(
    entity: str,
    anchor: str,
    dim: str,
    tos: list[dict],
    phase_table: dict,
    dep_map: dict,
    transition_upstream_map: dict,
    structural: list[dict] = None,
    cos: list[dict] = None,
) -> int:
    """Compute entry phase for a dependent entity's dimension.

    Strategy:
    1. If anchor has transitions that create entity, use that phase
    2. Use CO constraints to determine when entity becomes active
    3. Use structural relation to infer the phase when parent creates child
    4. Fallback: anchor's min phase
    """
    # Strategy 1: Find the phase when anchor creates/activates entity
    # Look for anchor transitions that point to entity creation (from=None)
    if cos:
        for co in cos:
            if co.get('dependent_entity') == entity and co.get('enabler_entity') == anchor:
                # CO says: when anchor reaches enabler_state, entity enters dep_condition
                enabler_dim = co.get('enabler_dimension', '')
                enabler_state = co.get('enabler_state', '')
                if anchor == phase_table.get('primary_entity', '') or anchor in phase_table.get('state_to_phase', {}):
                    anchor_map = phase_table['state_to_phase'].get(enabler_dim, {})
                    if enabler_state in anchor_map:
                        return anchor_map[enabler_state]
                if anchor in dep_map and enabler_dim in dep_map.get(anchor, {}):
                    if enabler_state in dep_map[anchor][enabler_dim]:
                        return dep_map[anchor][enabler_dim][enabler_state]

    # Strategy 2: Find initial transitions with upstream anchoring
    entity_dim_tos = [t for t in tos if t.get('entity') == entity and t.get('dimension') == dim and t.get('from') is None]
    for to in entity_dim_tos:
        tid = to.get('transition_id', '')
        upstreams = transition_upstream_map.get(tid, [])
        for utid in upstreams:
            ut = next((x for x in tos if x.get('transition_id') == utid), None)
            if ut and ut.get('entity') == anchor:
                anchor_dim = ut.get('dimension', '')
                a_pm = _get_anchor_phase(anchor, anchor_dim, phase_table, dep_map)
                if a_pm:
                    ut_to_phase = a_pm.get(ut.get('to'))
                    if ut_to_phase is not None:
                        return ut_to_phase

    # Strategy 3: For structural composition (anchor→entity), entity becomes active
    # when anchor reaches the state that creates it.
    if anchor == phase_table.get('primary_entity', '') or anchor in phase_table.get('state_to_phase', {}):
        # Get anchor's primary dimension phases
        primary_dim = phase_table.get('primary_dimension', '')
        anchor_map = phase_table.get('state_to_phase', {}).get(primary_dim, {})
        if anchor_map:
            # Entity appears at the earliest phase where anchor has a child-creating action
            # Heuristic: first phase after initial state (P1)
            non_zero_phases = [p for p in anchor_map.values() if p > 0]
            if non_zero_phases:
                return min(non_zero_phases)
            return min(anchor_map.values())

    # Strategy 4: anchor is in dep_map
    if anchor in dep_map:
        all_phases = [p for dm in dep_map[anchor].values() for p in dm.values()]
        if all_phases:
            non_zero = [p for p in all_phases if p > 0]
            return min(non_zero) if non_zero else min(all_phases)

    return 0


def _get_anchor_phase(anchor: str, dim: str, phase_table: dict, dep_map: dict) -> dict[str, int]:
    """Get phase mapping for anchor entity on a given dimension."""
    # phase_table.state_to_phase is keyed by dimension name, not entity name
    # Primary entity's phases are stored directly
    if anchor == phase_table.get('primary_entity', ''):
        return phase_table.get('state_to_phase', {}).get(dim, {})
    if anchor in dep_map and dim in dep_map.get(anchor, {}):
        return dep_map[anchor][dim]
    return {}


def _get_anchor_phase_for_entity(anchor: str, phase_table: dict, dep_map: dict) -> int:
    """Get minimum phase for anchor entity."""
    if anchor == phase_table.get('primary_entity', ''):
        all_phases = [p for dm in phase_table.get('state_to_phase', {}).values() for p in dm.values()]
        return min(all_phases) if all_phases else 0
    if anchor in dep_map:
        all_phases = [p for dm in dep_map[anchor].values() for p in dm.values()]
        return min(all_phases) if all_phases else 0
    return 0


def _detect_contextual_phase_rules(
    primary: str,
    tos: list[dict],
    dep_map: dict,
    entity_parent: dict,
    phase_table: dict,
    transition_upstream_map: dict,
) -> dict[str, dict]:
    """Detect dimensions where same state values map to different phases based on context.

    Example: E-REG.通知状态 has different triggers at different phases.
    """
    ctx_rules: dict[str, dict] = {}

    # For each entity in dep_map, check if any dimension has transitions
    # triggered by different upstream sources at different phases
    for entity, dims in dep_map.items():
        for dim, state_phases in dims.items():
            # Find transitions for this entity.dim
            dim_tos = [t for t in tos if t.get('entity') == entity and t.get('dimension') == dim]
            if not dim_tos:
                continue

            # Check if any transition with from=null has multiple upstream sources
            # that map to different phases
            trigger_sources: dict[str, list[dict]] = defaultdict(list)
            for to in dim_tos:
                if to.get('from') is None:
                    tid = to.get('transition_id', '')
                    upstreams = transition_upstream_map.get(tid, [])
                    for utid in upstreams:
                        ut = next((x for x in tos if x.get('transition_id') == utid), None)
                        if ut:
                            trigger_sources[ut.get('entity', '')].append({
                                'transition': to,
                                'upstream': ut,
                            })

            if len(trigger_sources) >= 2:
                # Multiple trigger sources — potential contextual dimension
                # Check if they resolve to different phases
                source_phases = {}
                for src_entity, entries in trigger_sources.items():
                    src_phase = _get_anchor_phase_for_entity(src_entity, phase_table, dep_map)
                    source_phases[src_entity] = src_phase

                unique_phases = set(source_phases.values())
                if len(unique_phases) >= 2:
                    rules = []
                    for src_entity, entries in sorted(trigger_sources.items()):
                        src_phase = source_phases[src_entity]
                        # Find a descriptive context from the upstream transitions
                        context = f"{src_entity}触发"
                        for entry in entries:
                            ut = entry['upstream']
                            action = ut.get('action', '')
                            if action:
                                context = action
                                break
                        rules.append({
                            'trigger_source': f"{src_entity}.{entries[0]['upstream'].get('dimension', '')}={entries[0]['upstream'].get('to', '')}",
                            'resolved_phase': src_phase,
                            'context': context,
                            'rationale': f"由{src_entity}触发",
                        })

                    ctx_key = f"{entity}.{dim}"
                    ctx_rules[ctx_key] = {
                        'strategy': 'upstream_anchor',
                        'description': f'{entity}.{dim}是同一实体内的维度级多场景维度。不同类型的操作由不同阶段的上游触发，同一状态值在不同场景下归属不同阶段。',
                        'rules': rules,
                        'default_phase': None,
                        'fallback': 'anchor_entity_min_phase',
                    }

    return ctx_rules


# ---------------------------------------------------------------------------
# S0.4: Dependent entity detection
# ---------------------------------------------------------------------------

def _detect_dependent_entities(
    primary: str,
    structural: list[dict],
    transition: list[dict],
    tos: list[dict],
    eos: list[dict],
    cos: list[dict],
) -> tuple[list[str], dict, dict]:
    """S0.4: Detect dependent_entities, entity_parent, dependency_depth.

    Rules aligned with V2 gold standard:
    - Entity with composition relation from primary → dependent, parent=primary
    - Entity with composition relation from dependent → dependent, parent=that_dep
    - Reference relations also count for parent assignment
    - L0 entities (E-LAB, E-STD, etc.) are NOT dependent if they have no
      structural composition parent pointing to them from primary/dependents
    - When entity has multiple composition parents, prefer the one closest to primary
    - entity_parent uses the structural relation's 'from' field
    """
    entity_parent: dict[str, str] = {}

    # Build candidate parents from structural relations
    composition_parents: dict[str, list[tuple[str, str]]] = defaultdict(list)
    reference_parents: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for rel in structural:
        f = rel.get('from', '')
        t = rel.get('to', '')
        rtype = rel.get('relation_type', '')
        conf = rel.get('confidence', '')

        if t == primary or f == t:
            continue

        if rtype == 'composition' and conf == 'high':
            composition_parents[t].append((f, rtype))
        elif rtype == 'reference' and conf == 'high':
            reference_parents[t].append((f, rtype))

    # Determine entity_tos presence
    entity_tos: dict[str, list] = defaultdict(list)
    for to in tos:
        entity_tos[to.get('entity', '')].append(to)

    # Step 1: Determine dependent entities from composition relations
    # An entity is dependent if it has a composition parent that is primary or another dependent
    dependent: list[str] = []

    # Process composition parents — priority: primary first, then dependents
    # First, entities where primary is a composition parent
    for entity, parents in composition_parents.items():
        if entity == primary:
            continue

        # Choose the best parent: prefer primary, then already-known dependents
        best_parent = None
        parent_candidates = [p for p, _ in parents]

        if primary in parent_candidates:
            best_parent = primary
        elif parent_candidates:
            best_parent = parent_candidates[0]

        if best_parent:
            dependent.append(entity)
            entity_parent[entity] = best_parent

    # Resolve multi-parent entities:
    # If entity has BOTH primary and a non-primary dependent as composition parents,
    # keep primary (e.g., E-VRF has E-PRJ and E-REG both as composition → parent=E-PRJ)
    # If entity has a non-primary dependent as composition parent and primary is only
    # a reference parent, prefer composition (e.g., E-EVAL has E-REG composition,
    # E-PRJ reference → parent=E-REG)
    for entity in list(dependent):
        if entity in composition_parents:
            comp_parents = [p for p, _ in composition_parents[entity]]
            # If primary is already a composition parent, keep it
            if primary in comp_parents:
                continue  # primary is already the parent, no change needed
            # If a non-primary dependent is a composition parent, use it
            non_primary_comp = [p for p in comp_parents if p != primary and p in dependent]
            if non_primary_comp:
                entity_parent[entity] = non_primary_comp[0]

    # Step 2: Entities with only reference relations from primary/dependents
    for entity, parents in reference_parents.items():
        if entity == primary or entity in dependent:
            continue
        if not entity_tos.get(entity):
            continue

        for parent, _ in parents:
            if parent == primary or parent in dependent:
                dependent.append(entity)
                entity_parent[entity] = parent
                break

    # Compute dependency_depth
    dependency_depth: dict[str, int] = {primary: 0}
    queue = deque([primary])
    while queue:
        cur = queue.popleft()
        for e, p in entity_parent.items():
            if p == cur and e not in dependency_depth:
                dependency_depth[e] = dependency_depth[cur] + 1
                queue.append(e)

    for e in dependent:
        if e not in dependency_depth:
            dependency_depth[e] = 1

    return dependent, entity_parent, dependency_depth


# ---------------------------------------------------------------------------
# S0.5: Topology levels
# ---------------------------------------------------------------------------

def _compute_topology_levels(
    primary: str,
    dependent_entities: list[str],
    entity_parent: dict,
    dependency_depth: dict,
    structural: list[dict],
    transition: list[dict],
    all_entities: set[str],
    virtual_entities: dict,
    managed_entities: set[str] | None = None,
) -> dict[str, int]:
    """S0.5: Compute topology_levels aligned with V2 gold standard.

    Level assignment:
    - L0: Entities with no transitions and no structural parent (E-STD, E-CATE, E-PTYPE, E-ITEM, E-ANNOUNCE, E-FAQ, E-MSG)
    - L0: E-LAB (independent entity with own transitions but no structural parent to primary)
    - L1: Entities that reference primary (E-PTYPE)
    - L2: Primary entity
    - L3: Direct dependents (depth=1)
    - L4: Indirect dependents (depth=2+)
    - L5: Other entities not yet assigned
    """
    levels: dict[str, int] = {}

    # Primary is L2
    levels[primary] = 2

    # Assign L0 to entities with no transitions and no structural child-of-primary relation
    # (handled below in the main loop)

    # Assign dependent entities based on depth
    for e in dependent_entities:
        d = dependency_depth.get(e, 1)
        if d == 1:
            levels[e] = 3
        elif d == 2:
            levels[e] = 4
        else:
            levels[e] = min(d + 2, 4)

    # Assign VEs
    for ve_name, ve in virtual_entities.items():
        parent = ve.get('parent_entity', '')
        if parent in levels:
            levels[ve_name] = levels[parent] + 1
        else:
            levels[ve_name] = 3

    # Assign entities that reference primary (L1)
    for rel in structural:
        f = rel.get('from', '')
        t = rel.get('to', '')
        if t == primary and f not in levels:
            levels[f] = 1

    # Assign L0 to entities not in dependency chain
    # Entities with no structural parent pointing to primary/dependents
    for e in all_entities:
        if e in levels:
            continue
        # Check if entity is referenced as a structural child
        is_child = any(
            r.get('to') == e and r.get('from') in levels and r.get('relation_type') in ('composition', 'reference')
            for r in structural
        )
        if is_child:
            # Assign based on parent level
            for r in structural:
                if r.get('to') == e and r.get('from') in levels:
                    parent_level = levels[r['from']]
                    if r.get('relation_type') == 'composition' and parent_level >= 2:
                        levels[e] = parent_level + 1
                    else:
                        levels[e] = 0  # reference/hierarchy → L0
                    break
        else:
            # No structural relation → L0 (configurable / independent)
            levels[e] = 0

    # Override: entities that are managed (type='managed' in _context) → L0
    if managed_entities is None:
        managed_entities = set()
    for e in managed_entities:
        if e not in levels:
            levels[e] = 0

    return levels


# ---------------------------------------------------------------------------
# S0.6: Upstream map rebuilding
# ---------------------------------------------------------------------------

def _rebuild_upstream_map(
    tos: list[dict],
    transition: list[dict],
    cos: list[dict],
) -> dict[str, list[str]]:
    """S0.6: Rebuild transition_upstream_map from three sources."""
    upstream_map: dict[str, list[str]] = defaultdict(list)

    to_by_tid = {t.get('transition_id'): t for t in tos if t.get('transition_id')}

    entity_dim_tos: dict[tuple, list[dict]] = defaultdict(list)
    for to in tos:
        key = (to.get('entity'), to.get('dimension'))
        entity_dim_tos[key].append(to)

    # Source 1: Same-entity same-dimension chain ordering
    for (entity, dim), dim_tos in entity_dim_tos.items():
        for t1 in dim_tos:
            t1_from = t1.get('from')
            t1_tid = t1.get('transition_id')
            if not t1_tid:
                continue
            for t2 in dim_tos:
                if t2.get('transition_id') == t1_tid:
                    continue
                if t2.get('to') == t1_from and t2.get('transition_id'):
                    upstream_map[t1_tid].append(t2['transition_id'])

    # Source 2: transition_relations evidence
    for tr in transition:
        ev = tr.get('evidence_transitions', []) or []
        from_tids = [t for t in ev if t in to_by_tid and to_by_tid[t].get('entity') == tr.get('from')]
        to_tids = [t for t in ev if t in to_by_tid and to_by_tid[t].get('entity') == tr.get('to')]
        for to_tid in to_tids:
            upstream_map[to_tid].extend(from_tids)

    # Source 3: CO enabler → dependent transition
    for co in cos:
        et = co.get('enabler_transition_id')
        dt = co.get('dependent_transition_id')
        if et and dt:
            upstream_map[dt].append(et)

    # Deduplicate
    for tid in upstream_map:
        upstream_map[tid] = list(set(upstream_map[tid]))

    # Also ensure transitions with no upstreams get an empty list
    for to in tos:
        tid = to.get('transition_id', '')
        if tid and tid not in upstream_map:
            upstream_map[tid] = []

    return dict(upstream_map)


# ---------------------------------------------------------------------------
# S0.7: Virtual entity decomposition (CO-causal based)
# ---------------------------------------------------------------------------

def _decompose_virtual_entities(
    primary: str,
    structural: list[dict],
    cos: list[dict],
    tos: list[dict],
    dependent_entities: list[str],
    topology_levels: dict,
    entity_parent: dict,
) -> dict:
    """S0.7: Virtual entity decomposition based on CO causal multi-parent.

    V2 gold standard rules:
    1. Only entities that are CO enablers with >=2 COs targeting DIFFERENT
       dependent_entities get decomposed into VEs.
    2. Entities that are already dependent_entities (like E-REG) do NOT get
       decomposed — their COs are internal dimension-level constraints.
    3. Each unique (dependent_entity) context creates a separate VE.
    4. When COs share the same dependent_entity but different dependent_conditions,
       they are grouped into the same VE (e.g., CO-006 and CO-012 both → E-REG).
    5. VE parent = the CO's dependent_entity (the entity that triggers this VE).

    Examples:
    - E-APPR: CO-001→E-PRJ, CO-006→E-REG, CO-007→E-LAB, CO-012→E-REG
      → E-APPRA(parent=E-LAB), E-APPRB(parent=E-PRJ), E-APPRC(parent=E-REG, co_ids=[CO-006,CO-012])
      Wait, gold has E-APPRC and E-APPRD both parent=E-REG but different contexts.
      Actually CO-006 and CO-012 point to E-REG but with different dependent_conditions.
      → E-APPRC(parent=E-REG, co_ids=[CO-006]), E-APPRD(parent=E-REG, co_ids=[CO-012])
    - E-VRF: CO-003→E-REG, CO-004→E-PRJ
      → E-VRFA(parent=E-PRJ), E-VRFB(parent=E-REG)
    """
    virtual_entities: dict[str, dict] = {}

    # Group COs by enabler_entity
    co_by_enabler: dict[str, list[dict]] = defaultdict(list)
    for co in cos:
        ee = co.get('enabler_entity', '')
        if ee and ee != primary:
            co_by_enabler[ee].append(co)

    # Process entities that are CO enablers
    # Only decompose entities that are NOT dependent entities themselves
    # (E-REG is a dependent entity and does NOT get VEs)
    for entity, co_list in co_by_enabler.items():
        # Note: entities that are both dependent AND CO enablers (like E-APPR, E-VRF)
        # DO get decomposed into VEs. Only skip entities whose COs are
        # purely internal dimension-level constraints (like E-REG).
        # Heuristic: skip if entity is a dependent AND its CO dependent_entities
        # are all within the primary entity hierarchy (not cross-cutting)
        if entity in dependent_entities:
            # Check if this entity's COs point to >=2 different dependent entities
            # that span across the hierarchy
            co_dep_entities = set(co.get('dependent_entity', '') for co in co_list)
            # If COs only target primary or itself, it's internal → skip
            # For VE decomposition, we need >=2 UNIQUE dependent entities (including primary)
            if len(co_dep_entities) < 2:
                continue  # Not enough diversity → skip
            # If all dependent entities are the same as the entity itself → skip
            if co_dep_entities == {entity}:
                continue

        if len(co_list) < 2:
            continue

        # Group COs by (dependent_entity, dependent_condition) for unique contexts
        # But in gold standard, CO-006 and CO-012 (both →E-REG) create SEPARATE VEs
        # because they have different dependent_conditions (报告审核中 vs 报告已发布)
        # So we group by dependent_entity only if same condition
        dep_entity_groups: dict[str, list[dict]] = defaultdict(list)

        for co in co_list:
            de = co.get('dependent_entity', '')
            dep_entity_groups[de].append(co)

        # Check if there are >=2 unique dependent entities
        unique_dep_entities = set(dep_entity_groups.keys())
        if len(unique_dep_entities) < 2:
            continue

        # Additional check: VE decomposition is for entities where the SAME
        # state/dimension acts as a cross-cutting constraint on different entities.
        # E-APPR: "审批状态=已通过" constrains E-PRJ, E-REG, E-LAB → cross-cutting → VEs
        # E-VRF: "核验状态=已通过" constrains E-REG, E-PRJ → cross-cutting → VEs
        # E-REG: different states ("报名成功", "费用已缴费") constrain different entities
        # → NOT cross-cutting, just normal multi-dimension → skip
        # Check: are all COs using the SAME enabler_dimension + enabler_state?
        enabler_keys = set()
        for co in co_list:
            key = (co.get('enabler_dimension', ''), co.get('enabler_state', ''))
            enabler_keys.add(key)
        if len(enabler_keys) > 1:
            # Multiple different enabler states → normal multi-dimension constraints
            # Only decompose if there's at least one shared enabler state that constrains >=2 entities
            shared_state_deps: dict[tuple, set[str]] = defaultdict(set)
            for co in co_list:
                key = (co.get('enabler_dimension', ''), co.get('enabler_state', ''))
                shared_state_deps[key].add(co.get('dependent_entity', ''))
            has_cross_cutting = any(len(deps) >= 2 for deps in shared_state_deps.values())
            if not has_cross_cutting:
                continue

        # Get entity's transitions
        entity_tids = [t.get('transition_id') for t in tos
                       if t.get('entity') == entity and t.get('transition_id')]

        # Create one VE per CO (each CO is a unique context)
        ve_index = 0
        for dep_entity in sorted(dep_entity_groups.keys()):
            co_group = dep_entity_groups[dep_entity]

            # If multiple COs target the same dep_entity with different conditions,
            # create separate VEs for each (like E-APPRC for CO-006, E-APPRD for CO-012)
            if len(co_group) == 1:
                co = co_group[0]
                ve_name = f"{entity}{chr(65 + ve_index)}"
                ve_index += 1

                trigger = co.get('trigger', '') or co.get('desc', '') or ''
                context_desc = trigger.split('(')[0].split('→')[0].strip() if trigger else f"归属{dep_entity}"

                virtual_entities[ve_name] = {
                    'original_entity': entity,
                    'parent_entity': dep_entity,
                    'transitions': entity_tids,
                    'trigger_source': dep_entity,
                    'context': context_desc,
                    'co_ids': [co.get('id')],
                    'resolved_phase': 0,
                }
            else:
                # Multiple COs to same dep_entity → one VE per CO
                for co in co_group:
                    ve_name = f"{entity}{chr(65 + ve_index)}"
                    ve_index += 1

                    trigger = co.get('trigger', '') or co.get('desc', '') or ''
                    context_desc = trigger.split('(')[0].split('→')[0].strip() if trigger else f"归属{dep_entity}"

                    virtual_entities[ve_name] = {
                        'original_entity': entity,
                        'parent_entity': dep_entity,
                        'transitions': entity_tids,
                        'trigger_source': dep_entity,
                        'context': context_desc,
                        'co_ids': [co.get('id')],
                        'resolved_phase': 0,
                    }

    # Also check for structural multi-parent entities with COs (like E-VRF)
    # E-VRF has composition from both E-PRJ and E-REG, and is a CO enabler
    # It should already be handled above if it has >=2 COs
    # But let's also check entities that have structural multi-parent
    # and are CO enablers (even if only 1 CO per parent)
    for entity in set(to.get('entity', '') for to in tos):
        # Skip if already has VEs created from this entity
        entity_has_ve = any(ve['original_entity'] == entity for ve in virtual_entities.values())
        if entity_has_ve or entity == primary:
            continue
        # Skip core dependent entities (E-REG etc.) — they don't get VE decomposition
        if entity in dependent_entities:
            continue

        # Must be a CO enabler
        if entity not in co_by_enabler:
            continue

        # Check structural multi-parent (composition relations)
        entity_comp_parents = [
            r.get('from') for r in structural
            if r.get('to') == entity and r.get('relation_type') == 'composition'
        ]

        if len(entity_comp_parents) < 2:
            continue

        # Get COs for this entity
        entity_cos = co_by_enabler.get(entity, [])
        if not entity_cos:
            continue

        # Get transitions
        entity_tids = [t.get('transition_id') for t in tos
                       if t.get('entity') == entity and t.get('transition_id')]

        # Create one VE per CO
        ve_index = len(virtual_entities)
        for co in entity_cos:
            dep_entity = co.get('dependent_entity', '')

            # Check if VE for this (entity, dep_entity) pair already exists
            existing = [vn for vn, ve in virtual_entities.items()
                        if ve['original_entity'] == entity and ve['parent_entity'] == dep_entity]
            if existing:
                # Add co_id to existing VE
                virtual_entities[existing[0]]['co_ids'].append(co.get('id'))
                continue

            ve_name = f"{entity}{chr(65 + ve_index)}"
            ve_index += 1

            trigger = co.get('trigger', '') or co.get('desc', '') or ''
            context_desc = trigger.split('(')[0].split('→')[0].strip() if trigger else f"归属{dep_entity}"

            virtual_entities[ve_name] = {
                'original_entity': entity,
                'parent_entity': dep_entity,
                'transitions': entity_tids,
                'trigger_source': dep_entity,
                'context': context_desc,
                'co_ids': [co.get('id')],
                'resolved_phase': 0,
            }

    # Remove VEs where parent == original (self-reference)
    to_remove = [vn for vn, ve in virtual_entities.items() if ve['parent_entity'] == ve['original_entity']]
    for vn in to_remove:
        del virtual_entities[vn]

    return virtual_entities


def _resolve_ve_phases(
    virtual_entities: dict,
    dep_state_phase_map: dict,
    phase_table: dict,
    tos: list[dict],
    cos: list[dict],
) -> tuple[dict, dict]:
    """Resolve VE resolved_phase after dep_state_phase_map is computed.

    For each VE, resolved_phase is determined by looking up the phase of
    the CO's dependent_condition in the parent_entity's phase map.
    Also updates dep_state_phase_map so all VE states share the resolved_phase.
    """
    # Build CO lookup
    co_by_id = {co.get('id'): co for co in cos}

    for ve_name, ve in virtual_entities.items():
        parent = ve.get('parent_entity', '')
        co_ids = ve.get('co_ids', [])

        # Try to find phase from CO's dependent_condition
        resolved = False
        for co_id in co_ids:
            co = co_by_id.get(co_id)
            if not co:
                continue
            dep_entity = co.get('dependent_entity', '')
            dep_dim = co.get('dependent_dimension', '')
            dep_cond = co.get('dependent_condition', '')

            # Look up in dep_state_phase_map
            if dep_entity in dep_state_phase_map:
                entity_map = dep_state_phase_map[dep_entity]
                if dep_dim in entity_map and dep_cond in entity_map[dep_dim]:
                    ve['resolved_phase'] = entity_map[dep_dim][dep_cond]
                    resolved = True
                    break
                # Try any dimension
                for dim, state_map in entity_map.items():
                    if dep_cond in state_map:
                        ve['resolved_phase'] = state_map[dep_cond]
                        resolved = True
                        break
                if resolved:
                    break

            # Look up in phase_table (for primary entity)
            if dep_entity == phase_table.get('primary_entity', ''):
                for dim, state_map in phase_table.get('state_to_phase', {}).items():
                    if dep_cond in state_map:
                        ve['resolved_phase'] = state_map[dep_cond]
                        resolved = True
                        break
                if resolved:
                    break

        if resolved:
            # Update all VE states in dep_state_phase_map to resolved_phase
            if ve_name in dep_state_phase_map:
                for dim, state_map in dep_state_phase_map[ve_name].items():
                    for state in state_map:
                        state_map[state] = ve['resolved_phase']
            continue

        # Fallback: use parent entity's min phase
        if parent in dep_state_phase_map:
            all_phases = [p for dm in dep_state_phase_map[parent].values() for p in dm.values()]
            if all_phases:
                ve['resolved_phase'] = min(all_phases)
                if ve_name in dep_state_phase_map:
                    for dim, state_map in dep_state_phase_map[ve_name].items():
                        for state in state_map:
                            state_map[state] = ve['resolved_phase']
                continue

        if parent == phase_table.get('primary_entity', ''):
            primary_dim = phase_table.get('primary_dimension', '')
            dim_map = phase_table.get('state_to_phase', {}).get(primary_dim, {})
            if dim_map:
                ve['resolved_phase'] = min(dim_map.values())
                if ve_name in dep_state_phase_map:
                    for dim, state_map in dep_state_phase_map[ve_name].items():
                        for state in state_map:
                            state_map[state] = ve['resolved_phase']
                continue

        ve['resolved_phase'] = 0

    return virtual_entities, dep_state_phase_map


# ---------------------------------------------------------------------------
# Main S0 node
# ---------------------------------------------------------------------------

def s0_topology_node(state: AgentState) -> dict:
    """S0 Topology Discovery node — deterministic implementation.

    Strategy:
    1. Deterministic computation of all S0.1–S0.7 fields
    2. Fallback: try LLM if deterministic fails
    3. Validate with schema
    """
    warnings = list(state.get("warnings", []))
    errors = list(state.get("errors", []))

    cm_path = state["coverage_model_path"]
    with open(cm_path, 'r', encoding='utf-8') as f:
        cm_data = json.load(f)
    coverage_model = cm_data.get('coverage_model', cm_data)

    try:
        result = _compute_s0_deterministic(coverage_model, warnings)
    except Exception as e:
        warnings.append(f"S0 deterministic computation failed: {e}, trying LLM fallback")
        try:
            from tools.llm_client import LLMClient
            from prompts.s0_prompt import S0_SYSTEM_PROMPT, S0_USER_PROMPT_TEMPLATE
            import asyncio
            client = LLMClient()
            user_msg = S0_USER_PROMPT_TEMPLATE.format(
                coverage_model_json=json.dumps(coverage_model, ensure_ascii=False, indent=2)
            )
            result = asyncio.run(client.chat_json(S0_SYSTEM_PROMPT, user_msg))
        except Exception as e2:
            errors.append(f"S0 fallback also failed: {e2}")
            return {"errors": errors, "current_stage": "s0_failed"}

    try:
        from models.schema import validate_engine_state
        validated = validate_engine_state(result)
        warnings.append(f"S0 validated: primary_entity={validated.primary_entity}, phases={validated.phase_table.phase_count}")
    except Exception as e:
        warnings.append(f"S0 validation warning: {e}")

    return {
        "primary_entity": result.get("primary_entity"),
        "phase_table": result.get("phase_table"),
        "dep_state_phase_map": result.get("dep_state_phase_map", {}),
        "contextual_phase_rules": result.get("contextual_phase_rules", {}),
        "state_type_map": result.get("state_type_map", {}),
        "dependent_entities": result.get("dependent_entities", []),
        "entity_parent": result.get("entity_parent", {}),
        "dependency_depth": result.get("dependency_depth", {}),
        "topology_levels": result.get("topology_levels", {}),
        "virtual_entities": result.get("virtual_entities", {}),
        "transition_upstream_map": result.get("transition_upstream_map", {}),
        "coverage_model": coverage_model,
        "warnings": warnings,
        "errors": errors,
        "current_stage": "s0",
    }


def _compute_s0_deterministic(cm: dict, warnings: list[str]) -> dict:
    """Full deterministic S0 computation from empty state."""
    tos = cm.get('transition_obligations', [])
    eos = cm.get('entity_obligations', [])
    cos = cm.get('cross_entity_obligations', [])
    ros = cm.get('constraint_obligations', [])

    structural, transition = _load_relations(cm)

    # S0.2: Primary entity
    primary = _identify_primary_entity(structural, transition, tos)
    if not primary:
        raise ValueError("S0.2: Could not identify primary_entity")
    warnings.append(f"S0.2: primary_entity={primary}")

    # S0.3: Phase table (longest path)
    phase_table = _derive_phase_table(primary, tos, cos)
    warnings.append(f"S0.3: primary_dimension={phase_table['primary_dimension']}, phase_count={phase_table['phase_count']}")

    # S0.4: Dependent entities
    dependent_entities, entity_parent, dependency_depth = _detect_dependent_entities(
        primary, structural, transition, tos, eos, cos
    )
    warnings.append(f"S0.4: {len(dependent_entities)} dependent entities: {dependent_entities}")

    # Collect all entities
    all_entities = set()
    for to in tos:
        all_entities.add(to.get('entity', ''))
    for eo in eos:
        all_entities.add(eo.get('entity', ''))
    for rel in structural:
        all_entities.add(rel.get('from', ''))
        all_entities.add(rel.get('to', ''))

    # Add all entities to dependency_depth (L0 entities get depth=0)
    for e in all_entities:
        if e not in dependency_depth:
            dependency_depth[e] = 0

    # S0.7: Virtual entity decomposition (CO-causal based)
    virtual_entities = _decompose_virtual_entities(
        primary, structural, cos, tos, dependent_entities, {}, entity_parent
    )

    # Add VEs to dependency_depth
    for ve_name, ve in virtual_entities.items():
        parent = ve.get('parent_entity', '')
        if parent in dependency_depth:
            dependency_depth[ve_name] = dependency_depth[parent] + 1
        else:
            dependency_depth[ve_name] = 1

    # Build dynamic maps from coverage_model._context
    managed_entities = _build_managed_entities(cm)

    # S0.5: Topology levels (needs VEs + managed_entities)
    topology_levels = _compute_topology_levels(
        primary, dependent_entities, entity_parent, dependency_depth,
        structural, transition, all_entities, virtual_entities,
        managed_entities=managed_entities
    )
    warnings.append(f"S0.5: topology_levels computed for {len(topology_levels)} entities")

    # S0.6: Upstream map
    transition_upstream_map = _rebuild_upstream_map(tos, transition, cos)
    warnings.append(f"S0.6: upstream_map with {len(transition_upstream_map)} entries")

    # State type map
    state_type_map = _classify_state_types(tos, primary)

    # Dep state phase map (depends on VEs)
    dep_state_phase_map, contextual_phase_rules = _derive_dep_state_phase_map(
        primary, phase_table, tos, dependent_entities, entity_parent,
        state_type_map, transition_upstream_map, virtual_entities, cos=cos
    )

    # Resolve VE phases AFTER dep_state_phase_map is computed
    virtual_entities, dep_state_phase_map = _resolve_ve_phases(virtual_entities, dep_state_phase_map, phase_table, tos, cos)

    if virtual_entities:
        # Recompute topology_levels with resolved VE phases
        topology_levels = _compute_topology_levels(
            primary, dependent_entities, entity_parent, dependency_depth,
            structural, transition, all_entities, virtual_entities,
            managed_entities=managed_entities
        )
        warnings.append(f"S0.7: {len(virtual_entities)} virtual entities: {list(virtual_entities.keys())}")

    return {
        'primary_entity': primary,
        'phase_table': phase_table,
        'dep_state_phase_map': dep_state_phase_map,
        'contextual_phase_rules': contextual_phase_rules,
        'state_type_map': state_type_map,
        'dependent_entities': dependent_entities,
        'entity_parent': entity_parent,
        'dependency_depth': dependency_depth,
        'topology_levels': topology_levels,
        'virtual_entities': virtual_entities,
        'transition_upstream_map': transition_upstream_map,
    }