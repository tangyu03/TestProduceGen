from __future__ import annotations
"""S0 Topology Discovery Node — Deterministic Implementation (V4).

Implements all sub-stages S0.1–S0.7:
  S0.1: Relation loading (structural_relations + transition_relations)
  S0.2: Primary entity identification (weighted freq + chain-length + E2 tiebreakers)
  S0.3: Phase table derivation (longest-path DAG, from-state补全, 从维度, G0.3/I14 enforcement)
  S0.4: Dependent entity detection (4-level signal classification, F/V/D, transitivity)
  S0.5: Topology levels (BFS backtracking, conflict resolution)
  S0.6: Upstream map rebuilding (3 sources merged)
  S0.7: Virtual entity decomposition (CO-causal + Structural multi-parent, E3 guards)

Falls back to LLM only if deterministic computation fails.
"""

import json
import os
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from models.state import AgentState


# ---------------------------------------------------------------------------
# Dynamic map builders — read from coverage_model._context at runtime
# ---------------------------------------------------------------------------

def _normalize_entities_list(ctx: dict) -> list[dict]:
    """Normalize entity_details to a list of dicts, handling both list and dict formats.

    Dict format:  {"E-XXX": {id, name, type, ...}, ...}
    List format:  [{id, name, type, ...}, ...]
    """
    details = ctx.get('entity_details', [])
    if isinstance(details, dict):
        return [v for v in details.values() if isinstance(v, dict)]
    if isinstance(details, list):
        return details
    return []


def _build_entity_name_map(cm: dict) -> dict[str, str]:
    """Build Chinese-name → entity-ID map from coverage_model._context.entity_details."""
    ctx = cm.get('_context', {})
    details = _normalize_entities_list(ctx)
    return {e['name']: e['id'] for e in details if e.get('name') and e.get('id')}


def _build_role_map(cm: dict) -> dict[str, str]:
    """Build role-ID → role-name map from coverage_model._context.roles."""
    ctx = cm.get('_context', {})
    roles = ctx.get('roles', [])
    if isinstance(roles, dict):
        roles = [v for v in roles.values() if isinstance(v, dict)]
    m = {r['id']: r['name'] for r in roles if r.get('id') and r.get('name')}
    m['system'] = '系统'
    return m


def _build_managed_entities(cm: dict) -> set[str]:
    """Build set of entity IDs with type='managed' (L0 candidates)."""
    ctx = cm.get('_context', {})
    details = _normalize_entities_list(ctx)
    return {e['id'] for e in details if e.get('type') == 'managed'}


# ---------------------------------------------------------------------------
# Domain-constant maps (truly invariant across projects)
# ---------------------------------------------------------------------------

# HUMAN_DECISION_KEYWORDS and AUTO_KEYWORDS have been removed.
# Action classification is now done via LLM in s1_generation._classify_actions_via_llm,
# replacing the hardcoded business keyword lists. This makes the engine
# portable to any business domain without code changes.

TYPE_PRIORITY_MAP = {
    'happy': 1, 'branch': 2, 'constraint': 3, 'audit': 4,
    'crud': 5, 'rule': 6, 'lifecycle': 7, 'cross': 8, 'invalid': 9,
    'data_constraint': 3, 'time_sensitive': 3, 'rollback': 4,
    'negative': 9, 'audit_rejection': 4
}

# TYPE5_SPECIAL_OPS is now read from coverage_model._context.type5_special_ops
# (configurable per project).  This fallback is empty — all crud operations
# are retained based on coverage_priority alone when no config is provided.
TYPE5_SPECIAL_OPS: set[str] = set()


# ---------------------------------------------------------------------------
# S0.1: Relation loading
# ---------------------------------------------------------------------------

def _load_relations(cm: dict) -> tuple[list[dict], list[dict]]:
    """S0.1: Load structural_relations and transition_relations from _context.

    G0.1: structural_relations 同{from,to}对取confidence最高者。
    """
    ctx = cm.get('_context', {})
    structural = ctx.get('structural_relations', [])
    transition = ctx.get('transition_relations', [])

    seen: dict[tuple, dict] = {}
    # G0.1: same {from,to} pair -> keep the relation with the HIGHEST confidence.
    # BUGFIX: previous logic only overrode when new confidence == 'high', which
    # silently kept a 'low' record when a later 'medium' (non-high) arrived.
    conf_rank = {'high': 3, 'medium': 2, 'low': 1, '': 0}
    for rel in structural:
        key = (rel.get('from'), rel.get('to'))
        new_rank = conf_rank.get(rel.get('confidence', ''), 0)
        if key not in seen or new_rank > conf_rank.get(seen[key].get('confidence', ''), 0):
            seen[key] = rel
    deduped_structural = list(seen.values())

    return deduped_structural, transition


# ---------------------------------------------------------------------------
# S0.2: Primary entity identification (E2 tiebreakers)
# ---------------------------------------------------------------------------

def _compute_chain_length(entity: str, tos: list[dict]) -> int:
    """Compute the longest chain of transitions for an entity.

    Used as E2 tiebreaker: prefer entity with longest state-transition chain.
    """
    entity_tos = [t for t in tos if t.get('entity') == entity]
    if not entity_tos:
        return 0

    # Build adjacency: from → [to]
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = defaultdict(int)
    all_states = set()
    initial = set()

    for to in entity_tos:
        f = to.get('from')
        t = to.get('to')
        # Guard: skip None/empty so they don't become dict keys
        f = f.strip() if isinstance(f, str) else (f if f else '')
        t = t.strip() if isinstance(t, str) else (t if t else '')
        if t:
            all_states.add(t)
        if f:
            all_states.add(f)
            if t:
                adj[f].append(t)
                in_degree[t] = in_degree.get(t, 0) + 1
        elif t:
            initial.add(t)

    if not all_states:
        return 0

    # Longest path via topological sort
    longest: dict[str, int] = {s: 1 for s in initial}
    for s in all_states:
        if s not in longest:
            longest[s] = 1

    # Kahn's algorithm
    q = deque([s for s in all_states if in_degree.get(s, 0) == 0])
    while q:
        node = q.popleft()
        for nxt in adj.get(node, []):
            longest[nxt] = max(longest.get(nxt, 1), longest[node] + 1)
            in_degree[nxt] = in_degree.get(nxt, 1) - 1
            if in_degree[nxt] <= 0:
                q.append(nxt)

    return max(longest.values()) if longest else 0


def _count_crud_operations(entity: str, eos: list[dict]) -> int:
    """Count CRUD operations for an entity (E2 tiebreaker: prefer fewer CRUD)."""
    return sum(1 for eo in eos
               if eo.get('entity') == entity and eo.get('type') == 'crud_operation')


def _count_dimensions(entity: str, tos: list[dict]) -> int:
    """Count distinct dimensions for an entity (E2 tiebreaker: prefer more dims)."""
    dims = set()
    for to in tos:
        if to.get('entity') == entity and to.get('dimension'):
            dims.add(to['dimension'])
    return len(dims)


def _identify_primary_entity(
    structural: list[dict],
    transition: list[dict],
    tos: list[dict],
    eos: list[dict] = None,
) -> str:
    """S0.2: Identify primary_entity by weighted frequency on structural from-side.

    Weights: high=2, medium=1, low=0.5. transition_relations not counted.

    Tie-break chain (E2):
      1. multi-state preferred
      2. longest state-transition chain
      3. driver-degree (upstream count + cross count), higher preferred
      4. fewer CRUD operations preferred
      5. more dimensions preferred

    Container-priority override applied after primary candidate selection.
    """
    if eos is None:
        eos = []

    freq: dict[str, float] = defaultdict(float)
    entity_has_multi_state: dict[str, bool] = {}
    entity_has_state_machine: dict[str, bool] = {}

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
        entity_has_state_machine[e] = True

    if not freq:
        if tos:
            return tos[0].get('entity', '')
        return ''

    # Sort candidates by multi-criteria tiebreaker (E2)
    candidate_scores = {}
    for e in freq:
        chain_len = _compute_chain_length(e, tos)
        multi_state = 1 if entity_has_multi_state.get(e, False) else 0
        crud_count = _count_crud_operations(e, eos)
        dim_count = _count_dimensions(e, tos)
        # Compute driver-degree: count of transitions where this entity is involved
        # as from-side in transition_relations + cross_entity references
        driver_degree = freq.get(e, 0)  # proxy: structural frequency
        candidate_scores[e] = {
            'freq': freq[e],
            'multi_state': multi_state,
            'chain_len': chain_len,
            'driver_degree': driver_degree,
            'crud_count': crud_count,
            'dim_count': dim_count,
        }

    candidates = sorted(
        freq.keys(),
        key=lambda e: (
            candidate_scores[e]['freq'],
            candidate_scores[e]['multi_state'],
            candidate_scores[e]['chain_len'],
            candidate_scores[e]['driver_degree'],
            -candidate_scores[e]['crud_count'],  # fewer CRUD → better
            candidate_scores[e]['dim_count'],
        ),
        reverse=True,
    )

    primary = candidates[0]

    # Container-priority override (E2): if a child entity has all its
    # initialization driven by the parent, keep parent.
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
        # Container priority triggers if:
        # - P has multi-state and C doesn't, OR
        # - P's freq ≥ 50% of C's and P has multi-state, OR
        # - Lifecycle inclusion: C's from=null transitions all have upstream from P
        override = False
        if p_multi and not c_multi:
            override = True
        elif freq[primary] >= freq[candidate] * 0.5 and p_multi:
            override = True
        else:
            c_null_froms = [t for t in tos if t.get('entity') == candidate and t.get('from') is None]
            if c_null_froms:
                # Check lifecycle inclusion via transition_relations:
                # "override" should require that AT LEAST ONE transition_relation
                # matches (to=candidate AND evidence contains one of C's
                # from-null transitions), AND every such match comes from
                # the primary entity.  Previously the default-True initialiser
                # caused override to fire even when ZERO matching relations
                # existed — a false-positive that flipped the primary entity.
                c_null_tids = [t.get('transition_id') for t in c_null_froms if t.get('transition_id')]
                matching_trs = [
                    tr for tr in transition
                    if tr.get('to') == candidate
                    and any(t in c_null_tids for t in (tr.get('evidence_transitions') or []))
                ]
                if matching_trs and all(tr.get('from') == primary for tr in matching_trs):
                    override = True
        if override:
            break  # keep primary as-is

    return primary


# ---------------------------------------------------------------------------
# S0.3: Phase table derivation (LONGEST PATH IN DAG)
# ---------------------------------------------------------------------------

def _derive_phase_table(primary: str, tos: list[dict], cos: list[dict]) -> dict:
    """Derive primary_dimension and state_to_phase via longest-path in DAG.

    Uses longest path (not BFS shortest path) so that skip-transitions
    (e.g., 待开始→进行中) do NOT collapse phases.
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
            'primary_entity': primary,
            'primary_dimension': primary_dimension,
            'state_to_phase': state_to_phase,
            'phase_names': phase_names,
            'phase_count': 1,
        }

    # Build DAG and find initial states
    graph: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = defaultdict(int)
    all_states = set()
    initial_states = set()

    for to in primary_tos:
        f = to.get('from')
        t = to.get('to')
        # Guard: skip None/empty so they don't become dict keys
        f = f.strip() if isinstance(f, str) else (f if f else '')
        t = t.strip() if isinstance(t, str) else (t if t else '')
        if t:
            all_states.add(t)
        if f:
            all_states.add(f)
            if t:
                graph[f].append(t)
                in_degree[t] = in_degree.get(t, 0) + 1
        elif t:
            initial_states.add(t)

    for s in all_states:
        if s not in in_degree:
            in_degree[s] = 0

    phase_map: dict[str, int] = {s: 0 for s in initial_states}
    queue = deque([s for s in all_states if in_degree.get(s, 0) == 0])
    remaining_in = dict(in_degree)

    while queue:
        node = queue.popleft()
        if node not in phase_map:
            phase_map[node] = 0
        for nxt in graph.get(node, []):
            phase_map[nxt] = max(phase_map.get(nxt, 0), phase_map[node] + 1)
            remaining_in[nxt] = remaining_in.get(nxt, 1) - 1
            if remaining_in.get(nxt, 0) <= 0:
                queue.append(nxt)

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
    paths. If ANY driving transition reaches the state, it is driving.

    Primary entity states are all driving (spec rule).
    Virtual entities inherit original entity's classification.
    """
    state_type_map: dict[str, dict[str, dict[str, str]]] = defaultdict(lambda: defaultdict(dict))
    side_effect_keywords = {'退', '撤销', '退款', '驳回'}

    # Two-pass: first collect which states have at least one driving inbound
    driving_states: dict[tuple, bool] = {}  # (entity, dim, target) → has_driving

    for to in tos:
        entity = to.get('entity', '')
        dim = to.get('dimension', '')
        target = to.get('to', '')
        if not target:
            continue

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
            driving_states[key] = True

    for to in tos:
        entity = to.get('entity', '')
        dim = to.get('dimension', '')
        target = to.get('to', '')
        if not target or entity == primary:
            continue

        key = (entity, dim, target)
        if driving_states.get(key):
            state_type_map[entity][dim][target] = 'driving'
        else:
            state_type_map[entity][dim][target] = 'side_effect'

    return dict(state_type_map)


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
    transition_relations: list[dict] = None,
) -> int:
    """Compute entry phase for a dependent entity's dimension.

    Strategies (in priority order):
    0. Precondition-based: TO preconditions reference primary-entity states
       (e.g. "项目状态为已结束" → phase 4).  This is the most direct signal.
    1. Upstream anchoring: from=null transitions with upstream from anchor
       OR any entity in the dependency chain (recursive).
    2. CO constraint: fallback when no upstream chain found
    3. Structural composition: anchor creates child entity
    4. 从维度: transition_relations where to=entity
    5. Anchor min phase fallback
    """
    # Strategy 0: Precondition-based phase derivation
    # Scan this entity's TO preconditions for primary-entity state references.
    # This is the most direct signal: if a TO says "项目状态为已结束", the
    # entity's entry phase IS the phase of "已结束" (phase 4).
    primary_entity = phase_table.get('primary_entity', '')
    primary_dim = phase_table.get('primary_dimension', '')
    primary_states = phase_table.get('state_to_phase', {}).get(primary_dim, {})
    entity_tos = [t for t in tos if t.get('entity') == entity and t.get('dimension') == dim]
    for to in entity_tos:
        for prec in to.get('preconditions', []) or []:
            for state_name, phase_val in primary_states.items():
                if state_name and len(state_name) >= 2 and state_name in prec:
                    return phase_val

    # Strategy 1: Upstream anchoring for initial transitions (PRIORITY)
    # Check upstreams from anchor OR any entity in the dependency chain.
    # When an upstream comes from a non-anchor entity (e.g. E-EVAL's T-090
    # upstream T-015 from E-REG), look up that entity's dep_state_phase_map
    # which is already aligned to the primary entity's global phase scale.
    entity_dim_tos = [t for t in tos if t.get('entity') == entity and t.get('dimension') == dim and t.get('from') is None]
    for to in entity_dim_tos:
        tid = to.get('transition_id', '')
        upstreams = transition_upstream_map.get(tid, [])
        for utid in upstreams:
            ut = next((x for x in tos if x.get('transition_id') == utid), None)
            if not ut:
                continue
            ut_entity = ut.get('entity', '')
            ut_dim = ut.get('dimension', '')
            ut_to = ut.get('to')
            # Try anchor first
            if ut_entity == anchor:
                a_pm = _get_anchor_phase(anchor, ut_dim, phase_table, dep_map)
                if a_pm and ut_to in a_pm:
                    return a_pm[ut_to]
            # Try upstream entity's dep_state_phase_map (recursive chain)
            if ut_entity in dep_map and ut_dim in dep_map.get(ut_entity, {}):
                ut_phase = dep_map[ut_entity][ut_dim].get(ut_to)
                if ut_phase is not None:
                    return ut_phase
            # Also try if upstream entity is the primary entity
            if ut_entity == phase_table.get('primary_entity', ''):
                pm = phase_table.get('state_to_phase', {}).get(ut_dim, {})
                if ut_to in pm:
                    return pm[ut_to]

    # Strategy 2: CO constraint anchoring (fallback)
    if cos:
        for co in cos:
            if co.get('dependent_entity') == entity and co.get('enabler_entity') == anchor:
                enabler_dim = co.get('enabler_dimension', '')
                enabler_state = co.get('enabler_state', '')
                if anchor == phase_table.get('primary_entity', '') or anchor in phase_table.get('state_to_phase', {}):
                    anchor_map = phase_table['state_to_phase'].get(enabler_dim, {})
                    if enabler_state in anchor_map:
                        return anchor_map[enabler_state]
                if anchor in dep_map and enabler_dim in dep_map.get(anchor, {}):
                    if enabler_state in dep_map[anchor][enabler_dim]:
                        return dep_map[anchor][enabler_dim][enabler_state]

    # Strategy 3: Structural composition
    if anchor == phase_table.get('primary_entity', '') or anchor in phase_table.get('state_to_phase', {}):
        primary_dim = phase_table.get('primary_dimension', '')
        anchor_map = phase_table.get('state_to_phase', {}).get(primary_dim, {})
        if anchor_map:
            non_zero_phases = [p for p in anchor_map.values() if p > 0]
            if non_zero_phases:
                return min(non_zero_phases)
            return min(anchor_map.values())

    # Strategy 4: 从维度 — transition_relations to=entity → from-side primary-dim phase
    if transition_relations:
        for tr in transition_relations:
            if tr.get('to') == entity or tr.get('to') == anchor:
                from_entity = tr.get('from', '')
                if from_entity == phase_table.get('primary_entity', ''):
                    primary_dim = phase_table.get('primary_dimension', '')
                    from_map = phase_table.get('state_to_phase', {}).get(primary_dim, {})
                    # Get from_entity's trigger state phase
                    trigger = tr.get('trigger', '')
                    from_transitions = [t for t in tos if t.get('entity') == from_entity
                                       and (t.get('action', '') == trigger or t.get('to', '') == trigger)]
                    for ft in from_transitions:
                        ft_to = ft.get('to', '')
                        if ft_to in from_map:
                            return from_map[ft_to]
                    # Fallback: min non-zero phase of from_entity
                    if from_map:
                        non_zero = [p for p in from_map.values() if p > 0]
                        return min(non_zero) if non_zero else min(from_map.values())

    # Strategy 5: Anchor in dep_map
    if anchor in dep_map:
        all_phases = [p for dm in dep_map[anchor].values() for p in dm.values()]
        if all_phases:
            non_zero = [p for p in all_phases if p > 0]
            return min(non_zero) if non_zero else min(all_phases)

    return 0


def _get_anchor_phase(anchor: str, dim: str, phase_table: dict, dep_map: dict) -> dict[str, int]:
    """Get phase mapping for anchor entity on a given dimension."""
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
    transition_relations: list[dict] = None,
    structural: list[dict] = None,
) -> tuple[dict, dict]:
    """S0.3 step 3: Dependent entity phase mapping via anchor-entity method.

    Includes: from-state补全 (1.2), 从维度 mapping (1.3)

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

        if is_ve:
            actual_entity = ve_info.get('original_entity', entity)
            entity_tos = [t for t in tos if t.get('entity') == actual_entity]
            dim_map: dict[str, dict[str, int]] = defaultdict(dict)
            for to in entity_tos:
                dim = to.get('dimension', '')
                target = to.get('to', '')
                if dim and target:
                    dim_map[dim][target] = 0  # placeholder
            dep_map[entity] = dict(dim_map)
            continue

        # Non-VE: longest-path DAG per dimension
        # BDD: include empty-dimension TOs (e.g. E-ARC, E-CERT have dim="")
        # Previously `if dim:` skipped them, leaving dep_map[entity] empty
        # and forcing phase=0 fallback.  Now use "" as a valid dimension key.
        entity_tos = [t for t in tos if t.get('entity') == entity]
        dim_map: dict[str, dict[str, int]] = defaultdict(dict)
        dim_tos: dict[str, list[dict]] = defaultdict(list)
        for to in entity_tos:
            dim = to.get('dimension', '')
            dim_tos[dim].append(to)

        for dim, dim_transitions in dim_tos.items():
            state_graph: dict[str, list[str]] = defaultdict(list)
            edge_is_se: dict[tuple[str, str], bool] = {}
            initial_states = set()
            all_states = set()

            se_keywords = {'退', '撤销', '退款', '驳回'}

            for to in dim_transitions:
                f = to.get('from')
                t = to.get('to')
                # Guard: skip None/empty so they don't become dict keys
                f = f.strip() if isinstance(f, str) else (f if f else '')
                t = t.strip() if isinstance(t, str) else (t if t else '')
                if t:
                    all_states.add(t)
                if f:
                    all_states.add(f)
                    if t:
                        state_graph[f].append(t)
                        desc = to.get('desc', '') or to.get('description', '') or ''
                        action = to.get('action', '') or ''
                        traits = to.get('risk_traits', []) or to.get('traits', []) or []
                        is_se = (
                            any(kw in desc for kw in se_keywords)
                            or any(kw in action for kw in se_keywords)
                            or 'rollback' in traits
                        )
                        edge_is_se[(f, t)] = is_se
                elif t:
                    initial_states.add(t)

            entry_phase = _compute_entry_phase(
                entity, anchor, dim, tos, phase_table, dep_map,
                transition_upstream_map, structural=structural, cos=cos,
                transition_relations=transition_relations,
            )

            # Bellman-Ford iterative propagation
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
                        continue
                    for nxt in successors:
                        is_se = edge_is_se.get((f_state, nxt), False)
                        if is_se:
                            if state_phase[nxt] == UNASSIGNED:
                                state_phase[nxt] = state_phase[f_state]
                                changed = True
                        else:
                            new_phase = state_phase[f_state] + 1
                            if new_phase > state_phase[nxt]:
                                state_phase[nxt] = new_phase
                                changed = True

            # 1.2: from-state补全 — backfill unmapped from-states
            for f_state in all_states:
                if state_phase[f_state] == UNASSIGNED:
                    # If this state appears as a 'from' in some transition,
                    # infer phase from anchor entry phase
                    is_source = any(f_state == f for f in state_graph)
                    if is_source:
                        # Heuristic: if appears as from in driving edges,
                        # phase ≈ entry_phase + max depth from initial
                        state_phase[f_state] = entry_phase
                    else:
                        state_phase[f_state] = entry_phase

            # Fill remaining unreachable
            for s in all_states:
                if state_phase[s] == UNASSIGNED:
                    state_phase[s] = entry_phase

            dim_map[dim] = dict(state_phase)

        dep_map[entity] = dict(dim_map)

    # 1.3: 从维度 — transition_relations to=entity → use from-side phase
    # (handled inside _compute_entry_phase via the transition_relations param)

    # Detect contextual phase rules
    ctx_rules = _detect_contextual_phase_rules(
        primary, tos, dep_map, entity_parent, phase_table, transition_upstream_map
    )

    return dep_map, ctx_rules


def _detect_contextual_phase_rules(
    primary: str,
    tos: list[dict],
    dep_map: dict,
    entity_parent: dict,
    phase_table: dict,
    transition_upstream_map: dict,
) -> dict[str, dict]:
    """S0.3b: Detect dimensions where same state maps to different phases per context."""
    ctx_rules: dict[str, dict] = {}

    for entity, dims in dep_map.items():
        for dim, state_phases in dims.items():
            dim_tos = [t for t in tos if t.get('entity') == entity and t.get('dimension') == dim]
            if not dim_tos:
                continue

            # Check from=null transitions with multiple upstream sources at different phases
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
                source_phases = {}
                for src_entity, entries in trigger_sources.items():
                    src_phase = _get_anchor_phase_for_entity(src_entity, phase_table, dep_map)
                    source_phases[src_entity] = src_phase

                unique_phases = set(source_phases.values())
                if len(unique_phases) >= 2:
                    rules = []
                    for src_entity, entries in sorted(trigger_sources.items()):
                        src_phase = source_phases[src_entity]
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
# S0.4: Dependent entity detection (V4 — cardinality-based signal classification)
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

    V4: Implements 4-level signal classification:
      - strong: composition high + 1:N cardinality
      - medium: composition high + 1:1, or composition medium + 1:N
      - transition: transition_relations to=primary from-side, evidence_points to parent
      - weak: non-high structural

    F/V/D判定 per-candidate, with transitivity.
    """
    entity_parent: dict[str, str] = {}

    # Build entity → transitions map
    entity_tos: dict[str, list] = defaultdict(list)
    for to in tos:
        entity_tos[to.get('entity', '')].append(to)

    # Step 1: Collect candidates with signal strength
    signal_strength: dict[str, str] = {}  # entity → strong|medium|transition|weak
    signal_parent: dict[str, str] = {}  # entity → suggested parent

    for rel in structural:
        f = rel.get('from', '')
        t = rel.get('to', '')
        rtype = rel.get('relation_type', '')
        conf = rel.get('confidence', '')
        card = rel.get('cardinality', '') or '1:1'

        if t == primary or f == t or not f or not t:
            continue

        is_one_to_n = ':N' in card or ':n' in card or card.endswith(':N') or card.endswith(':n')

        if rtype == 'composition':
            if conf == 'high' and is_one_to_n:
                sig = 'strong'
            elif conf == 'high' or (conf == 'medium' and is_one_to_n):
                sig = 'medium'
            else:
                sig = 'weak'
        elif rtype == 'reference' and conf == 'high':
            sig = 'medium'
        else:
            sig = 'weak'

        # Keep strongest signal
        if t not in signal_strength or _signal_rank(sig) > _signal_rank(signal_strength[t]):
            signal_strength[t] = sig
            signal_parent[t] = f

    # Step 2: Transition_relations signals
    for tr in transition:
        f = tr.get('from', '')
        t = tr.get('to', '')
        if t == primary and f not in signal_strength:
            signal_strength[f] = 'transition'
            signal_parent[f] = primary

    # Step 3: F/V/D判定
    dependent: list[str] = []

    for entity in list(signal_strength.keys()):
        if entity == primary:
            continue

        sig = signal_strength[entity]
        parent = signal_parent.get(entity, '')
        has_state_machine = bool(entity_tos.get(entity))

        # V (从属) criteria:
        is_dependent = False

        # strong signal → dependent
        if sig == 'strong':
            is_dependent = True
        # medium signal → dependent
        elif sig == 'medium':
            is_dependent = True
        # transition signal → dependent
        elif sig == 'transition':
            is_dependent = True
        # weak signal + has state machine + parent is primary/dependent
        elif sig == 'weak' and has_state_machine:
            if parent == primary or parent in dependent:
                is_dependent = True
        # desc contains dependency hints
        elif has_state_machine:
            for rel in structural:
                if rel.get('to') == entity:
                    desc = rel.get('desc', '') or rel.get('description', '')
                    if any(kw in desc for kw in ['归属', '属于', '依赖', '从属', '包含', '关联']):
                        is_dependent = True
                        signal_parent.setdefault(entity, rel.get('from', primary))
                        break

        # F (非从属) criteria:
        if is_dependent:
            # Check exclusions
            entity_details = []  # We don't have direct access to _context here
            # configurable + no transitions → F
            crud_count = sum(1 for eo in eos if eo.get('entity') == entity and eo.get('type') == 'crud_operation')
            if crud_count >= 4 and sig != 'strong':
                # CRUD≥4 without high-confidence signal → F (skip)
                continue
            dependent.append(entity)

    # Step 4: entity_parent assignment
    for entity in dependent:
        parent = signal_parent.get(entity)
        # BUGFIX #16: explicit parens to disambiguate operator precedence.
        # Original was parsed as `(parent and parent in dependent) or (parent == primary)`
        # which is the intended logic — but make it explicit for readability.
        if (parent and parent in dependent) or (parent == primary):
            entity_parent[entity] = parent
        elif parent:
            # Parent not yet known as dependent — try structural composition from primary
            entity_parent[entity] = primary
        else:
            # Default to primary
            entity_parent[entity] = primary

    # Step 5: Transitivity (循环至收敛)
    changed = True
    while changed:
        changed = False
        for rel in structural:
            f = rel.get('from', '')
            t = rel.get('to', '')
            if f in dependent and t not in dependent and t != primary:
                if entity_tos.get(t):  # has state machine
                    dependent.append(t)
                    entity_parent[t] = f
                    changed = True

    # Step 6: dependency_depth (BFS from primary)
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


def _signal_rank(sig: str) -> int:
    """Rank signal strength: strong=3, medium=2, transition=2, weak=1."""
    return {'strong': 3, 'medium': 2, 'transition': 2, 'weak': 1}.get(sig, 0)


# ---------------------------------------------------------------------------
# S0.5: Topology levels (V4 — BFS backtracking)
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
    """S0.5: Compute topology_levels with BFS backtracking (1.7).

    Level assignment:
    - L0: managed/configurable entities, no structural parent to primary/deps
    - L1: entities that reference primary
    - L2: Primary entity
    - L3: Direct dependents (depth=1)
    - L4: Indirect dependents (depth≥2)
    - L5: Other entities

    Backtracking: L3+ unassigned structural upstream → L0
                  transition_relations to=primary from→L1
                  Conflict: take smaller level
    """
    levels: dict[str, int] = {}

    # Primary is L1 — main state machine comes before reference entities
    levels[primary] = 1

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

    # Assign entities that reference primary → L2 (after primary, before dependents)
    for rel in structural:
        f = rel.get('from', '')
        t = rel.get('to', '')
        if t == primary and f not in levels:
            if rel.get('relation_type') == 'composition':
                levels[f] = 2
            else:
                levels[f] = 0  # reference/other → L0, foundational config data

    # BFS backtracking (1.7)
    # L3+ entities with unassigned structural upstream → L0
    for rel in structural:
        f = rel.get('from', '')
        t = rel.get('to', '')
        if f not in levels and t in levels and levels[t] >= 3:
            if rel.get('relation_type') in ('composition', 'reference'):
                levels[f] = 0  # L0

    # transition_relations to=primary from端 → L2
    for tr in transition:
        f = tr.get('from', '')
        t = tr.get('to', '')
        if t == primary and f not in levels:
            levels[f] = 2

    # Remaining unassigned
    for e in all_entities:
        if e in levels:
            continue
        is_child = any(
            r.get('to') == e and r.get('from') in levels and r.get('relation_type') in ('composition', 'reference')
            for r in structural
        )
        if is_child:
            for r in structural:
                if r.get('to') == e and r.get('from') in levels:
                    parent_level = levels[r['from']]
                    if r.get('relation_type') == 'composition' and parent_level >= 1:
                        levels[e] = parent_level + 1
                    else:
                        levels[e] = 0
                    break
        else:
            levels[e] = 0

    # Conflict resolution: take smaller level if already assigned non-L0
    for e in list(levels.keys()):
        current = levels[e]
        # Re-check structural relations for better (smaller) assignment
        if current >= 3:
            for rel in structural:
                if rel.get('to') == e and rel.get('from') in levels:
                    alt = levels[rel['from']] + 1
                    if alt < current and alt > 0:
                        levels[e] = alt

    # Managed entities → L0 override
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

    for to in tos:
        tid = to.get('transition_id', '')
        if tid and tid not in upstream_map:
            upstream_map[tid] = []

    return dict(upstream_map)


# ---------------------------------------------------------------------------
# S0.7: Virtual entity decomposition (V4 — CO-causal + Structural multi-parent)
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
    """S0.7: Virtual entity decomposition.

    Two sources:
    1. CO-causal multi-parent: entity is enabler for ≥2 unique dependent entities
    2. Structural multi-parent: entity has ≥2 active composition parents

    Merging: same parent_entity from both sources → merge co_ids.
    E3 guards enforced.
    """
    virtual_entities: dict[str, dict] = {}

    # Build CO index
    co_by_enabler: dict[str, list[dict]] = defaultdict(list)
    for co in cos:
        ee = co.get('enabler_entity', '')
        if ee and ee != primary:
            co_by_enabler[ee].append(co)

    # ── Source 2: CO-causal multi-parent ──
    for entity, co_list in co_by_enabler.items():
        if entity in dependent_entities:
            co_dep_entities = set(co.get('dependent_entity', '') for co in co_list)
            if len(co_dep_entities) < 2:
                continue
            if co_dep_entities == {entity}:
                continue

        if len(co_list) < 2:
            continue

        # Group by dependent_entity
        dep_entity_groups: dict[str, list[dict]] = defaultdict(list)
        for co in co_list:
            de = co.get('dependent_entity', '')
            dep_entity_groups[de].append(co)

        unique_dep_entities = set(dep_entity_groups.keys())
        if len(unique_dep_entities) < 2:
            continue

        # Check cross-cutting: same enabler state constrains ≥2 entities
        shared_state_deps: dict[tuple, set[str]] = defaultdict(set)
        for co in co_list:
            key = (co.get('enabler_dimension', ''), co.get('enabler_state', ''))
            shared_state_deps[key].add(co.get('dependent_entity', ''))
        has_cross_cutting = any(len(deps) >= 2 for deps in shared_state_deps.values())
        if not has_cross_cutting:
            continue

        # E3 guards
        entity_tids = [t.get('transition_id') for t in tos
                       if t.get('entity') == entity and t.get('transition_id')]
        if len(entity_tids) < 2:
            continue  # E3 ①: transitions<2不拆

        # Create VEs per unique (dep_entity, dep_phase) context
        ve_index = 0
        co_phase_groups: dict[tuple, list[dict]] = defaultdict(list)
        for dep_entity, co_group in dep_entity_groups.items():
            for co in co_group:
                # Group by dependent condition (same phase → merge)
                dep_cond = co.get('dependent_condition', '')
                co_phase_groups.setdefault((dep_entity, dep_cond), []).append(co)

        if len(co_phase_groups) < 2:
            continue  # E3 ②: 单场景不拆

        for (dep_entity, dep_cond), co_group in sorted(co_phase_groups.items()):
            ve_name = f"{entity}{chr(65 + ve_index)}"
            ve_index += 1

            trigger = co_group[0].get('trigger', '') or co_group[0].get('desc', '') or ''
            context_desc = trigger.split('(')[0].split('→')[0].strip() if trigger else f"归属{dep_entity}"

            virtual_entities[ve_name] = {
                'original_entity': entity,
                'parent_entity': dep_entity,
                'transitions': entity_tids,
                'trigger_source': dep_entity,
                'context': context_desc,
                'co_ids': [co.get('id') for co in co_group],
                'resolved_phase': 0,
            }

    # ── Source 1: Structural multi-parent ──
    for entity in set(to.get('entity', '') for to in tos):
        if entity == primary:
            continue
        if entity in dependent_entities:
            continue

        # Entity not yet decomposed by CO-causal
        entity_has_co_ve = any(ve['original_entity'] == entity for ve in virtual_entities.values())

        # Get composition parents that are L2/L3/L4
        comp_parents = [
            r.get('from') for r in structural
            if r.get('to') == entity
            and r.get('relation_type') == 'composition'  # I16: only composition
            and r.get('from') in topology_levels
            and topology_levels[r.get('from')] >= 1
        ]
        unique_comp_parents = list(dict.fromkeys(comp_parents))  # ordered unique

        if len(unique_comp_parents) < 2:
            continue

        # E3 ①: transitions<2不拆
        entity_tids = [t.get('transition_id') for t in tos
                       if t.get('entity') == entity and t.get('transition_id')]
        if len(entity_tids) < 2:
            continue

        # Create structural VEs
        existing_ve_names = set(virtual_entities.keys())
        ve_index = len(virtual_entities)

        for parent in unique_comp_parents:
            # Check if VE with same parent already exists from CO-causal
            existing = [vn for vn, ve in virtual_entities.items()
                       if ve['original_entity'] == entity and ve['parent_entity'] == parent]
            if existing:
                # Merge: CO-causal VE already covers this parent
                continue

            ve_name = f"{entity}{chr(65 + ve_index)}"
            ve_index += 1

            # Get context from structural relation
            rel = next((r for r in structural
                       if r.get('from') == parent and r.get('to') == entity
                       and r.get('relation_type') == 'composition'), {})
            context = rel.get('desc', '') or f"归属{parent}"

            virtual_entities[ve_name] = {
                'original_entity': entity,
                'parent_entity': parent,
                'transitions': entity_tids,
                'trigger_source': parent,
                'context': context,
                'co_ids': [],
                'resolved_phase': 0,
            }

    # ── E3 guards and cleanup ──
    # ④: Self-reference removal
    to_remove = [vn for vn, ve in virtual_entities.items() if ve['parent_entity'] == ve['original_entity']]
    for vn in to_remove:
        del virtual_entities[vn]

    # G0.7: Parent uniqueness verification
    parent_map: dict[str, list[str]] = defaultdict(list)
    for ve_name, ve in virtual_entities.items():
        key = (ve['original_entity'], ve['parent_entity'])
        parent_map[key].append(ve_name)

    for key, ve_names in parent_map.items():
        if len(ve_names) > 1:
            # Same original_entity+parent → merge the first, remove others
            keeper = ve_names[0]
            for vn in ve_names[1:]:
                virtual_entities[keeper]['co_ids'].extend(virtual_entities[vn]['co_ids'])
                virtual_entities[keeper]['context'] += '; ' + virtual_entities[vn]['context']
                del virtual_entities[vn]

    return virtual_entities


def _resolve_ve_phases(
    virtual_entities: dict,
    dep_state_phase_map: dict,
    phase_table: dict,
    tos: list[dict],
    cos: list[dict],
) -> tuple[dict, dict]:
    """Resolve VE resolved_phase after dep_state_phase_map is computed."""
    co_by_id = {co.get('id'): co for co in cos}

    for ve_name, ve in virtual_entities.items():
        parent = ve.get('parent_entity', '')
        co_ids = ve.get('co_ids', [])

        resolved = False
        for co_id in co_ids:
            co = co_by_id.get(co_id)
            if not co:
                continue
            dep_entity = co.get('dependent_entity', '')
            dep_dim = co.get('dependent_dimension', '')
            dep_cond = co.get('dependent_condition', '')

            if dep_entity in dep_state_phase_map:
                entity_map = dep_state_phase_map[dep_entity]
                if dep_dim in entity_map and dep_cond in entity_map[dep_dim]:
                    ve['resolved_phase'] = entity_map[dep_dim][dep_cond]
                    resolved = True
                    break
                for dim, state_map in entity_map.items():
                    if dep_cond in state_map:
                        ve['resolved_phase'] = state_map[dep_cond]
                        resolved = True
                        break
                if resolved:
                    break

            if dep_entity == phase_table.get('primary_entity', ''):
                for dim, state_map in phase_table.get('state_to_phase', {}).items():
                    if dep_cond in state_map:
                        ve['resolved_phase'] = state_map[dep_cond]
                        resolved = True
                        break
                if resolved:
                    break

        if resolved:
            if ve_name in dep_state_phase_map:
                for dim, state_map in dep_state_phase_map[ve_name].items():
                    for state in state_map:
                        state_map[state] = ve['resolved_phase']
            continue

        # Fallback: parent entity's min phase
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
# E1: Structural contradiction detection
# ---------------------------------------------------------------------------

def _detect_structural_contradictions(
    structural: list[dict],
    warnings: list[str],
) -> None:
    """E1: Detect contradictions in structural relations.

    Checks for semantic contradictions between from/to and relation_type.
    Records warning but does NOT flip the relation — spec rule.
    """
    # Composition should have from as parent/container and to as child/part
    # Contradiction: if desc suggests the opposite
    for rel in structural:
        rtype = rel.get('relation_type', '')
        desc = rel.get('desc', '') or rel.get('description', '') or ''
        f = rel.get('from', '')
        t = rel.get('to', '')

        if rtype == 'composition':
            # If desc suggests 'to' contains 'from', that's contradictory
            containment_keywords = ['属于', '依赖', '关联到']
            for kw in containment_keywords:
                if kw in desc and f in desc and t in desc:
                    # Check if the relationship direction is inverted in the description
                    if desc.index(t) < desc.index(kw) < desc.index(f):
                        warnings.append(
                            f"E1: structural contradiction — {f}→{t} (composition) "
                            f"but desc suggests {t} depends on {f}: {desc[:80]}"
                        )
                        break

        if rtype == 'reference':
            # Reference should be lightweight, not containment
            ownership_keywords = ['包含', '拥有', '管理', '控制', '所属']
            for kw in ownership_keywords:
                if kw in desc and f in desc:
                    warnings.append(
                        f"E1: structural contradiction — {f}→{t} (reference) "
                        f"but desc suggests ownership: {desc[:80]}"
                    )
                    break


# ---------------------------------------------------------------------------
# S0 invariant enforcement helpers
# ---------------------------------------------------------------------------

def _enforce_s0_invariants(
    primary: str,
    phase_table: dict,
    dep_state_phase_map: dict,
    contextual_phase_rules: dict,
    dependent_entities: list[str],
    entity_parent: dict,
    dependency_depth: dict,
    virtual_entities: dict,
    warnings: list[str],
) -> list[str]:
    """Enforce S0 invariants: G0.3, G0.4, I7, I8, I14.

    Returns updated warnings list.
    """
    # G0.3: primary_dimension non-null + primary entity spans all phases
    primary_dim = phase_table.get('primary_dimension', '')
    if not primary_dim:
        warnings.append("G0.3: primary_dimension is null — no phases mapped for primary entity")
    else:
        state_to_phase = phase_table.get('state_to_phase', {}).get(primary_dim, {})
        if not state_to_phase:
            warnings.append(f"G0.3: primary entity '{primary}' has no states mapped in primary_dimension '{primary_dim}'")

    # G0.3: dep_state_phase_map covers dependent entities' main dimensions
    for e in dependent_entities:
        if e not in dep_state_phase_map or not dep_state_phase_map[e]:
            warnings.append(f"G0.3: dependent entity '{e}' has no dep_state_phase_map entry")

    # I14: contextual_phase_rules dimensions must NOT appear in dep_state_phase_map
    for ctx_key in contextual_phase_rules:
        parts = ctx_key.split('.', 1)
        if len(parts) == 2:
            entity, dim = parts[0], parts[1]
            if entity in dep_state_phase_map and dim in dep_state_phase_map[entity]:
                del dep_state_phase_map[entity][dim]
                warnings.append(f"I14: removed '{dim}' from dep_state_phase_map['{entity}'] — context-dependent dimension")

    # I7: parent < child (dependency_depth)
    for child, parent in entity_parent.items():
        if parent and parent in dependency_depth and child in dependency_depth:
            parent_depth = dependency_depth[parent]
            child_depth = dependency_depth[child]
            if parent_depth >= child_depth and parent_depth > 0:
                warnings.append(
                    f"I7: parent '{parent}' (depth={parent_depth}) not shallower than "
                    f"child '{child}' (depth={child_depth})"
                )

    # I8: VE parents unique and ≠ self
    ve_parents_seen = set()
    for ve_name, ve in virtual_entities.items():
        parent = ve.get('parent_entity', '')
        original = ve.get('original_entity', '')
        if parent == original:
            warnings.append(f"I8: VE '{ve_name}' parent == original '{original}' — self-reference")
        if parent in ve_parents_seen:
            # Check if different original → OK (different entities can share parent context)
            pass  # Parent reuse is allowed for different original entities
        ve_parents_seen.add(parent)

    return warnings


# ---------------------------------------------------------------------------
# Main S0 node
# ---------------------------------------------------------------------------

def s0_topology_node(state: AgentState) -> dict:
    """S0 Topology Discovery node — deterministic implementation."""
    warnings = list(state.get("warnings", []))
    errors = list(state.get("errors", []))

    cm_path = state["coverage_model_path"]
    with open(cm_path, 'r', encoding='utf-8') as f:
        cm_data = json.load(f)
    raw = cm_data.get('coverage_model')
    coverage_model = raw if raw is not None else cm_data

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
            return {"errors": errors, "warnings": warnings, "current_stage": "s0_failed"}

    try:
        from models.schema import validate_engine_state
        validated = validate_engine_state(result)
        warnings.append(f"S0 validated: primary_entity={validated.primary_entity}, phases={validated.phase_table.phase_count}")
    except Exception as e:
        # BUGFIX #10: validation failure means S0 output violates invariants
        # (e.g. primary_entity null, parent>=child depth).  Previously this
        # only appended a warning and returned current_stage="s0", causing
        # downstream S1 to crash on missing fields.  Promote to a fatal
        # error and return s0_failed so should_continue_after_s0 stops the
        # pipeline cleanly.
        errors.append(f"S0 invariant validation FAILED: {e}")
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
            "errors": errors,
            "warnings": warnings,
            "current_stage": "s0_failed",
        }

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

    # E1: Detect structural contradictions
    _detect_structural_contradictions(structural, warnings)

    # S0.2: Primary entity (E2 enhanced)
    primary = _identify_primary_entity(structural, transition, tos, eos)
    if not primary:
        raise ValueError("S0.2: Could not identify primary_entity")
    warnings.append(f"S0.2: primary_entity={primary}")

    # S0.3: Phase table (longest path)
    phase_table = _derive_phase_table(primary, tos, cos)
    warnings.append(f"S0.3: primary_dimension={phase_table['primary_dimension']}, phase_count={phase_table['phase_count']}")

    # S0.4: Dependent entities (cardinality-based)
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

    for e in all_entities:
        if e not in dependency_depth:
            dependency_depth[e] = 0

    # S0.7: Virtual entity decomposition (CO-causal + Structural)
    virtual_entities = _decompose_virtual_entities(
        primary, structural, cos, tos, dependent_entities, {}, entity_parent
    )

    for ve_name, ve in virtual_entities.items():
        parent = ve.get('parent_entity', '')
        if parent in dependency_depth:
            dependency_depth[ve_name] = dependency_depth[parent] + 1
        else:
            dependency_depth[ve_name] = 1

    managed_entities = _build_managed_entities(cm)

    # S0.5: Topology levels (with BFS backtracking)
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

    # Dep state phase map (with from-state补全 + 从维度)
    dep_state_phase_map, contextual_phase_rules = _derive_dep_state_phase_map(
        primary, phase_table, tos, dependent_entities, entity_parent,
        state_type_map, transition_upstream_map, virtual_entities,
        cos=cos, transition_relations=transition, structural=structural,
    )

    # Resolve VE phases AFTER dep_state_phase_map
    virtual_entities, dep_state_phase_map = _resolve_ve_phases(
        virtual_entities, dep_state_phase_map, phase_table, tos, cos
    )

    if virtual_entities:
        topology_levels = _compute_topology_levels(
            primary, dependent_entities, entity_parent, dependency_depth,
            structural, transition, all_entities, virtual_entities,
            managed_entities=managed_entities
        )
        warnings.append(f"S0.7: {len(virtual_entities)} virtual entities: {list(virtual_entities.keys())}")

    # Enforce S0 invariants
    warnings = _enforce_s0_invariants(
        primary, phase_table, dep_state_phase_map, contextual_phase_rules,
        dependent_entities, entity_parent, dependency_depth,
        virtual_entities, warnings,
    )

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
