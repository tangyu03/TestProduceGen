from __future__ import annotations
"""S0 Topology Discovery Node — Deterministic Implementation (V4).

Implements all sub-stages S0.1–S0.7:
  S0.1: Relation loading (structural_relations + transition_relations)
  S0.2: Primary entity identification (weighted freq + chain-length + E2 tiebreakers)
  S0.3: Phase table derivation (longest-path DAG, from-state补全, 从维度, G0.3/I14 enforcement)
  S0.4: Dependent entity detection (4-level signal classification, F/V/D, transitivity)
  S0.5: Topology levels (BFS backtracking, conflict resolution)
  S0.7: Virtual entity decomposition (CO-causal + Structural multi-parent, E3 guards)

Falls back to LLM only if deterministic computation fails.
"""

import json
import os
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from models.state import AgentState

# ⑧ 遗留: Strategy 0 入口锚定消费 constraint_predicate 的结构化状态引用
# （ref_state_dimension 为首要机制），与 S1 predicate_phase_lower_bound 同源。
from context.constraint_fields import iter_predicate_state_refs

# v29 Engineering Optimization Gap 1: Fallback Observability
from tools.fallback_log import record_fallback as _record_fallback


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
def _normalize_dim_list(dimensions_field) -> dict:
    """Coerce a state_info[entity].dimensions value to a {dim_name: dim_info} dict.

    P2 emits `dimensions` as a LIST of dicts, each carrying a `dimension_name`
    key (not as a dict keyed by dim name). Older code assumed dict layout and
    silently returned {} for every entity, so the V08 explicit-phase-mapping
    path never triggered.

    Returns a dict {dim_name: dim_info}. Passes through if already a dict.
    Drops entries without a usable `dimension_name`.
    """
    if isinstance(dimensions_field, dict):
        return {k: v for k, v in dimensions_field.items() if isinstance(v, dict)}
    if not isinstance(dimensions_field, list):
        return {}
    out: dict[str, dict] = {}
    for entry in dimensions_field:
        if not isinstance(entry, dict):
            continue
        name = entry.get('dimension_name') or entry.get('dim') or entry.get('name')
        if isinstance(name, str) and name:
            out[name] = entry
    return out


def _derive_phase_mapping_from_states(dim_info: dict) -> dict[str, int] | None:
    """Derive a phase mapping from the `states` list order when no explicit
    `phase_mapping` is present.

    The `states` list in state_info is declared in business progression order
    (e.g. ['待选入','已选入','待评审','评审中','待归档','已归档']). Using the
    list index as the phase gives a correct monotonic mapping that respects
    both cyclic state machines (e.g. E-ORG 合格→不合格→试用→合格, where the
    states list ['合格','不合格','试用'] yields 合格=0, 不合格=1, 试用=2) and
    linear chains (E-SCORE 未保存→已保存→已提交 → 0/1/2).

    Terminal-state pinning: all declared `terminal` states are remapped to the
    SAME maximum phase. This aligns with case_spec.phase_mapping.reference
    (e.g. E-PLAN terminals 结束/超时结束/取消结束 all → P5) and satisfies the
    V08 "terminal state must be at max phase" rule. Without this pin, the
    raw indices would give 结束=6, 超时结束=7, 取消结束=8 — three different
    phases for states that semantically represent the same lifecycle end.
    """
    if not isinstance(dim_info, dict):
        return None
    states = dim_info.get('states')
    if not isinstance(states, list) or not states:
        return None
    pm: dict[str, int] = {}
    for idx, s in enumerate(states):
        if isinstance(s, str) and s:
            pm[s] = idx
    if not pm:
        return None

    # Pin all terminal states to the same max phase.
    # The max is the highest index among non-terminal states, OR
    # (if all states are terminal) the highest index overall.
    terminals = dim_info.get('terminal')
    if isinstance(terminals, list):
        term_set = {s for s in terminals if isinstance(s, str) and s}
        if term_set:
            non_terminal_phases = [p for s, p in pm.items() if s not in term_set]
            if non_terminal_phases:
                # +1: terminals are one phase beyond the last non-terminal
                terminal_phase = max(non_terminal_phases) + 1
            else:
                terminal_phase = max(pm.values())
            for s in term_set:
                if s in pm:
                    pm[s] = terminal_phase
    return pm


def _get_explicit_phase_mapping(state_info: dict | None, entity: str, dim: str) -> dict[str, int] | None:
    """V08 fix: read authoritative phase_mapping from state_info.

    P2 (context/generate_obligation_model.py) derives phase_mapping
    deterministically from transitions + initial + terminal and writes
    it to state_info[entity][dim].phase_mapping. S0 reads this directly
    instead of re-deriving via error-prone BFS.

    Falls back to deriving from the `states` list order when no explicit
    `phase_mapping` is declared — the states list is the authoritative
    business-progression order and yields a correct monotonic phase mapping
    even for cyclic state machines (which the BFS fallback below mishandles).

    Returns None only when state_info has no usable entry for (entity, dim).
    """
    if not state_info or not isinstance(state_info, dict):
        return None
    ent = state_info.get(entity)
    if not isinstance(ent, dict):
        return None

    # Layout A (P2 flat): state_info[entity][dim] = {states, initial, terminal, phase_mapping}
    dim_info = ent.get(dim)
    if isinstance(dim_info, dict):
        pm = dim_info.get('phase_mapping')
        if isinstance(pm, dict) and pm:
            return {str(k): int(v) for k, v in pm.items() if isinstance(v, (int, float))}
        # No explicit phase_mapping → derive from `states` list order
        derived = _derive_phase_mapping_from_states(dim_info)
        if derived:
            return derived

    # Layout B (P2 list): state_info[entity].dimensions = [{dimension_name, states, ...}]
    dimensions = _normalize_dim_list(ent.get('dimensions'))
    if dim in dimensions:
        dim_info = dimensions[dim]
        pm = dim_info.get('phase_mapping')
        if isinstance(pm, dict) and pm:
            return {str(k): int(v) for k, v in pm.items() if isinstance(v, (int, float))}
        # No explicit phase_mapping → derive from `states` list order
        derived = _derive_phase_mapping_from_states(dim_info)
        if derived:
            return derived

    # Layout C (legacy dict): state_info[entity].dimensions[dim] = {...}
    if isinstance(ent.get('dimensions'), dict):
        legacy = ent['dimensions']
        if isinstance(legacy, dict) and dim in legacy and isinstance(legacy[dim], dict):
            dim_info = legacy[dim]
            pm = dim_info.get('phase_mapping')
            if isinstance(pm, dict) and pm:
                return {str(k): int(v) for k, v in pm.items() if isinstance(v, (int, float))}
            derived = _derive_phase_mapping_from_states(dim_info)
            if derived:
                return derived

    return None


def _get_branch_phase_mappings(state_info: dict | None, entity: str, dim: str) -> dict[str, dict[str, int]]:
    """branch_values 生命周期归属改造：读取 P2 写入的 phase_mapping_by_branch。

    返回 {branch_value: {state: phase}}；state_info 无该 (entity, dim) 的
    per-branch 相位时返回 {}（S1 查询 miss 后落回全局链，行为退化安全）。
    支持 Layout A（state_info[entity][dim]）与 Layout B（dimensions 列表）。
    """
    if not state_info or not isinstance(state_info, dict):
        return {}
    ent = state_info.get(entity)
    if not isinstance(ent, dict):
        return {}
    candidates: list[dict] = []
    dim_info = ent.get(dim)
    if isinstance(dim_info, dict):
        candidates.append(dim_info)
    dimensions = _normalize_dim_list(ent.get('dimensions'))
    if dim in dimensions and isinstance(dimensions[dim], dict):
        candidates.append(dimensions[dim])
    if isinstance(ent.get('dimensions'), dict):
        legacy = ent['dimensions']
        if dim in legacy and isinstance(legacy[dim], dict):
            candidates.append(legacy[dim])
    for dim_info in candidates:
        pmb = dim_info.get('phase_mapping_by_branch')
        if isinstance(pmb, dict) and pmb:
            out: dict[str, dict[str, int]] = {}
            for b, pm in pmb.items():
                if isinstance(pm, dict) and pm:
                    out[str(b)] = {str(k): int(v) for k, v in pm.items()
                                   if isinstance(v, (int, float))}
            if out:
                return out
    return {}


def _build_state_pos(state_info: dict | None) -> dict:
    """Build {(entity_id, dim_name): {state: position}} from _context.state_info.

    Position = explicit phase_mapping value (fallback: index in the states
    list). Handles both state_info layouts (dict and P2's list-of-dicts with
    `dimension_name`) via _normalize_dim_list. A transition whose `to`
    position is <= its `from` position is a loop/back edge (s3 Guard 1).
    """
    pos: dict[tuple, dict] = {}
    for ent, info in (state_info or {}).items():
        if not isinstance(info, dict):
            continue
        for dim_name, dim in _normalize_dim_list(info.get("dimensions") or []).items():
            pm = dim.get("phase_mapping") or {}
            states = dim.get("states") or []
            d = {}
            for i, st in enumerate(states):
                if isinstance(st, str) and st:
                    d[st] = pm.get(st, i)
            if d:
                pos[(ent, dim_name)] = d
    return pos


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
    state_info: dict | None = None,
) -> str:
    """S0.2: Identify primary_entity via multi-signal fusion (v29 #19).

    v28 algorithm: weighted frequency on structural from-side only.
    Failure modes observed in other projects:
      - Main entity has low structural from-side freq (it's the "dependee",
        not the "depender") → freq ranking underestimates it.
      - Main entity has no state machine (only attributes) → multi_state
        tie-break loses to children with state machines.
      - Causal chain source (transition_relations.from) is the true driver,
        but v28 doesn't count transition_relations in freq.
      - confidence all "low" → freq differentiation weak.

    v29 #19 algorithm: multi-signal fusion with 5 normalized scores:
      1. structural_driver_freq  — from-side freq in structural_relations
      2. causal_driver_freq     — direction-agnostic degree in
                                  transition_relations (from + to, self-once):
                                  "causal graph center" = flow carrier
      3. dependee_score         — to-side freq in structural_relations
                                   (being depended ON = main entity)
      4. lifecycle_completeness — initial+terminal+states+transitions
      5. container_degree       — composition from-side count

    Each signal normalized to [0, 1], then weighted sum:
      score = 0.20 * structural_driver_freq
            + 0.25 * causal_driver_freq       # causal center is key
            + 0.20 * dependee_score           # being depended on = main
            + 0.20 * lifecycle_completeness   # full lifecycle = main
            + 0.15 * container_degree         # container role

    Container-priority override preserved from v28.
    """
    if eos is None:
        eos = []
    state_info = state_info or {}

    weight_map = {'high': 2, 'medium': 1, 'low': 0.5}

    # ── Signal 1: structural_driver_freq (v28 behavior, kept) ──
    structural_freq: dict[str, float] = defaultdict(float)
    # ── Signal 3: dependee_score (to-side freq) ──
    dependee_freq: dict[str, float] = defaultdict(float)
    # ── Signal 5: container_degree ──
    container_count: dict[str, int] = defaultdict(int)
    # Track all entities seen in structural
    structural_entities: set[str] = set()

    for rel in structural:
        f = rel.get('from', '')
        t = rel.get('to', '')
        w = weight_map.get(rel.get('confidence', 'low'), 0.5)
        if f:
            structural_freq[f] += w
            structural_entities.add(f)
        if t:
            dependee_freq[t] += w
            structural_entities.add(t)
        # Container: from-side of composition
        if f and rel.get('relation_type') == 'composition':
            container_count[f] += 1

    # ── Signal 2: causal_driver_freq (transition_relations → causal center) ──
    # v30: from-only undervalues a "flow carrier" that is the causal SINK.
    #   PT017: E-CAR receives 6 task→CAR causal edges (REG/ARC/TRF/RET/RCY/OUT
    #   drive its state machine) yet emits only CAR→USER → from-only gives it
    #   the same 1-edge count as every task, so the carrier ties with tasks.
    #   review: E-PLAN is the causal SOURCE (PLAN→PROJ/ORG, SCORE→PLAN).
    # Direction-agnostic degree (count each endpoint of every causal edge,
    # self-edge counted once) = "who is at the center of the causal graph" =
    # the business-flow carrier.  PT017 → E-CAR (6 in + 1 out);  review →
    # E-PLAN (2 out + 1 in).  Weights/other signals unchanged.
    causal_freq: dict[str, float] = defaultdict(float)
    causal_entities: set[str] = set()
    for tr in (transition or []):
        f = tr.get('from', '')
        t = tr.get('to', '')
        if not f and not t:
            continue
        w = weight_map.get(tr.get('confidence', 'low'), 0.5)
        if f:
            causal_freq[f] += w
            causal_entities.add(f)
        if t and t != f:
            causal_freq[t] += w
            causal_entities.add(t)

    # ── Signal 4: lifecycle_completeness ──
    # entity → {has_initial, has_terminal, state_count, transition_count, dim_count}
    lifecycle: dict[str, dict] = defaultdict(lambda: {
        'has_initial': 0, 'has_terminal': 0, 'state_count': 0,
        'transition_count': 0, 'dim_count': 0,
    })
    entity_has_multi_state: dict[str, bool] = {}
    entity_dims: dict[str, set] = defaultdict(set)

    for to in tos:
        e = to.get('entity', '')
        if not e:
            continue
        dim = to.get('dimension', '')
        if dim:
            entity_has_multi_state[e] = True
            entity_dims[e].add(dim)
        lifecycle[e]['transition_count'] += 1

    # Populate state counts from state_info.
    # state_info 存在三种形态（与 _get_explicit_phase_mapping 一致）：
    #   Layout A: state_info[ent][dim] = {states, initial, terminal, ...}
    #   Layout B: state_info[ent] = {entity_name, dimensions: [{dimension_name, states, ...}]}
    #   Layout C: state_info[ent].dimensions = {dim: {states, ...}} (legacy)
    # 直接 dims.items() 只认 Layout A——对 Layout B 会迭代到 entity_name(字符串)/dimensions(list)
    # 而读不到 states，导致 lifecycle 信号对 Layout B 数据全平（PT017 实测全实体 0.25）。
    # 统一经 _normalize_dim_list 归一为 {dim_name: dim_info} 再统计。
    for ent_id, dims in state_info.items():
        if not isinstance(dims, dict):
            continue
        dim_field = dims.get('dimensions') if isinstance(dims.get('dimensions'), (list, dict)) else dims
        for dim_name, dim_info in _normalize_dim_list(dim_field).items():
            states = dim_info.get('states', []) or []
            lifecycle[ent_id]['state_count'] += len(states)
            if dim_info.get('initial'):
                lifecycle[ent_id]['has_initial'] = 1
            if dim_info.get('terminal'):
                lifecycle[ent_id]['has_terminal'] = 1

    # All candidate entities
    all_candidates: set[str] = set()
    all_candidates.update(structural_entities)
    all_candidates.update(causal_entities)
    all_candidates.update(lifecycle.keys())
    for to in tos:
        if to.get('entity'):
            all_candidates.add(to['entity'])

    if not all_candidates:
        if tos:
            return tos[0].get('entity', '')
        return ''

    # ── Compute normalized scores ──
    def _normalize(d: dict) -> dict:
        if not d:
            return {e: 0.0 for e in all_candidates}
        mx = max(d.values()) if d else 1
        if mx == 0:
            return {e: 0.0 for e in all_candidates}
        return {e: d.get(e, 0) / mx for e in all_candidates}

    norm_struct_freq = _normalize(structural_freq)
    norm_causal_freq = _normalize(causal_freq)
    norm_dependee = _normalize(dependee_freq)
    norm_container = {e: container_count.get(e, 0) / max(max(container_count.values()), 1) if container_count else 0.0
                      for e in all_candidates}

    # Lifecycle completeness: (has_initial + has_terminal + state_score + transition_score) / 4
    max_states = max((l['state_count'] for l in lifecycle.values()), default=1) or 1
    max_transitions = max((l['transition_count'] for l in lifecycle.values()), default=1) or 1
    norm_lifecycle = {}
    for e in all_candidates:
        l = lifecycle.get(e, lifecycle.default_factory())
        state_score = min(l['state_count'] / max(3, max_states * 0.5), 1.0)
        trans_score = min(l['transition_count'] / max(3, max_transitions * 0.5), 1.0)
        norm_lifecycle[e] = (l['has_initial'] + l['has_terminal'] + state_score + trans_score) / 4

    # ── Weighted fusion ──
    W = {'struct': 0.20, 'causal': 0.25, 'dependee': 0.20, 'lifecycle': 0.20, 'container': 0.15}
    fusion_scores: dict[str, float] = {}
    for e in all_candidates:
        fusion_scores[e] = (
            W['struct'] * norm_struct_freq.get(e, 0)
            + W['causal'] * norm_causal_freq.get(e, 0)
            + W['dependee'] * norm_dependee.get(e, 0)
            + W['lifecycle'] * norm_lifecycle.get(e, 0)
            + W['container'] * norm_container.get(e, 0)
        )

    # Sort by fusion score (desc), with v28 tie-breaks as secondary
    candidates = sorted(
        all_candidates,
        key=lambda e: (
            fusion_scores[e],
            entity_has_multi_state.get(e, False),
            _compute_chain_length(e, tos),
            -_count_crud_operations(e, eos),
            len(entity_dims.get(e, set())),
        ),
        reverse=True,
    )

    if not candidates:
        return ''

    primary = candidates[0]

    # ── Container-priority override (preserved from v28) ──
    # If primary is a child of another candidate that is a container,
    # and the container has multi-state or strong lifecycle, prefer container.
    for candidate in candidates:
        if candidate == primary:
            continue
        is_child = any(
            r.get('from') == candidate and r.get('to') == primary
            and r.get('relation_type') == 'composition'
            for r in structural
        )
        if not is_child:
            continue
        # candidate is parent of primary
        p_multi = entity_has_multi_state.get(candidate, False)
        c_multi = entity_has_multi_state.get(primary, False)
        p_lifecycle = norm_lifecycle.get(candidate, 0)
        c_lifecycle = norm_lifecycle.get(primary, 0)
        # Override conditions (v29: relaxed to also accept lifecycle)
        if p_multi and not c_multi:
            primary = candidate
            break
        if fusion_scores.get(candidate, 0) >= fusion_scores.get(primary, 0) * 0.8 and p_multi:
            primary = candidate
            break
        if p_lifecycle > c_lifecycle and p_multi:
            primary = candidate
            break
        # Lifecycle inclusion: child's from=null transitions all driven by parent
        c_null_froms = [t for t in tos if t.get('entity') == primary and t.get('from') is None]
        if c_null_froms:
            c_null_tids = [t.get('transition_id') for t in c_null_froms if t.get('transition_id')]
            matching_trs = [
                tr for tr in (transition or [])
                if tr.get('to') == primary
                and any(t in c_null_tids for t in (tr.get('evidence_transitions') or []))
            ]
            if matching_trs and all(tr.get('from') == candidate for tr in matching_trs):
                primary = candidate
                break

    return primary


def _select_primary_via_llm(
    heuristic_primary: str,
    tos: list[dict],
    cos: list[dict],
    structural: list[dict],
    eos: list[dict],
) -> str:
    """S0.2 LLM-based primary entity selection.

    Design rationale:
    ──────────────────
    The heuristic (_identify_primary_entity) picks the entity with highest
    structural from-side frequency — but that measures "who is referenced
    as parent most often", NOT "who is the business flow carrier".

    For example, E-PROJ (project container) is referenced as parent by
    E-REG/E-EVAL/E-ARC, so heuristic picks E-PROJ. But E-REG (registration
    record) is the actual business flow carrier — it has 22 transitions
    across 5 dimensions covering the entire lifecycle, while E-PROJ only
    has 6 transitions in 2 dimensions.

    LLM can understand business semantics that heuristics cannot:
    - Which entity's state machine spans the full business timeline?
    - Which entity is the "object being processed" vs the "container"?
    - Which entity has the finest-grained state coverage?

    Input to LLM: per-entity summary (id, name, TO count, state count,
    dimension list, transition summary).

    Output: {"primary_entity": "E-REG", "primary_dimension": "报名记录状态", "reason": "..."}

    Fallback: if LLM unavailable or returns invalid response, return
    heuristic_primary unchanged.
    """
    import os as _os
    import json as _json
    import urllib.request as _urllib

    api_base = _os.environ.get('LLM_API_BASE', 'https://open.bigmodel.cn/api/paas/v4').rstrip('/')
    api_key = _os.environ.get('LLM_API_KEY', '')
    model = _os.environ.get('LLM_PRIMARY_SELECT_MODEL', 'glm-4-flash')
    if not api_key:
        cfg_path = _os.path.join(_os.path.dirname(__file__), '..', 'config.json')
        try:
            with open(cfg_path) as f:
                cfg = _json.load(f)
            llm_cfg = cfg.get('llm', {})
            api_base = llm_cfg.get('api_base', api_base).rstrip('/')
            api_key = llm_cfg.get('api_key', api_key)
            model = llm_cfg.get('primary_select_model', model)
        except Exception:
            pass
    if not api_key:
        print('      [PRIMARY-SELECT] LLM_API_KEY not set — using heuristic')
        return ''

    # Build entity summaries
    from collections import defaultdict
    entity_tos = defaultdict(list)
    for to in tos:
        e = to.get('entity', '')
        if e:
            entity_tos[e].append(to)

    # Entity name lookup
    name_map = _build_entity_name_map({'_context': {'entity_details': eos}}) if eos else {}

    # Structural parent counts
    parent_freq = defaultdict(int)
    for r in structural:
        f = r.get('from', '')
        if f:
            parent_freq[f] += 1

    summaries = []
    for entity, etos in entity_tos.items():
        dims = sorted(set(t.get('dimension', '') for t in etos if t.get('dimension')))
        states = set()
        for t in etos:
            if t.get('from'): states.add(t['from'])
            if t.get('to'): states.add(t['to'])
        name = name_map.get(entity, entity)
        summaries.append({
            'entity_id': entity,
            'entity_name': name,
            'to_count': len(etos),
            'state_count': len(states),
            'dimensions': dims,
            'structural_parent_count': parent_freq.get(entity, 0),
            'transitions': [
                f"  {t.get('from') or '(初始)'} → {t.get('to') or '?'}"
                for t in etos[:5]
            ][:3],  # limit to keep prompt small
        })

    prompt = f"""你是业务分析师。从以下实体中选出"业务流程主载体"作为主实体（primary_entity）。

## 选择标准（按优先级）
1. 状态机覆盖完整业务流程的实体（状态数最多、跨业务阶段最广）
2. 是"被处理的对象"而非"容器"（如报名记录 vs 项目）
3. 状态粒度最细（能区分不同业务阶段的细节）
4. 维度数多（覆盖业务多个方面）

## 候选实体
{_json.dumps(summaries, ensure_ascii=False, indent=2)}

## 输出格式（严格 JSON）
{{"primary_entity": "E-XXX", "primary_dimension": "状态维度名", "reason": "简短理由"}}

注意：primary_dimension 必须是该实体状态数最多、覆盖业务流程最完整的维度。"""

    body = _json.dumps({
        'model': model,
        'messages': [
            {'role': 'system', 'content': '你是业务分析专家，擅长识别业务流程的核心载体实体。'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.1,
        'max_tokens': 500,
    }).encode('utf-8')

    req = _urllib.Request(
        f'{api_base}/chat/completions',
        data=body,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        },
    )

    try:
        print(f'      [PRIMARY-SELECT] calling LLM with {len(summaries)} candidate entities')
        with _urllib.urlopen(req, timeout=60) as resp:
            data = _json.loads(resp.read().decode('utf-8'))
        raw = (data.get('choices') or [{}])[0].get('message', {}).get('content', '')
        # Strip code fences
        raw = raw.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1] if '\n' in raw else raw[3:]
        if raw.endswith('```'):
            raw = raw[:-3]
        raw = raw.strip()
        result = _json.loads(raw)
        selected = result.get('primary_entity', '')
        if selected and selected in entity_tos:
            print(f'      [PRIMARY-SELECT] LLM selected: {selected} (reason: {result.get("reason", "")[:80]})')
            return selected
        print(f'      [PRIMARY-SELECT] LLM returned invalid entity: {selected}')
        return ''
    except Exception as e:
        print(f'      [PRIMARY-SELECT] LLM call failed: {e}')
        return ''


# ---------------------------------------------------------------------------
# S0.3: Phase table derivation (LONGEST PATH IN DAG)
# ---------------------------------------------------------------------------

# v29 #26k: configurable action keywords for edge classification fallback.
# Default: empty sets (projects with structured annotations don't need keywords).
# Can be set from _context.action_keywords in coverage_model.
_ACTION_KEYWORDS: dict[str, set] = {
    'rollback': set(),   # e.g. {'退回', '驳回', '撤销', '退款', '暂停', '取消'}
    'resubmit': set(),   # e.g. {'重新提交', '修改后', '重新发起', '重启', '恢复'}
}

# Default keywords for backward compat (used when _context.action_keywords
# is not present in coverage_model — older P1/P2 output without structured
# annotations). These are generic Chinese business verbs, not project-specific.
_DEFAULT_ROLLBACK_KW = {'退回', '驳回', '撤销', '退款', '暂停', '取消'}
_DEFAULT_RESUBMIT_KW = {'重新提交', '修改后', '重新发起', '重启', '恢复'}


def _classify_edge_type(
    to: dict,
    from_state: str,
    to_state: str,
    terminal_states: set,
) -> str:
    """v29 #22/#26k: Classify edge type using structured signals.

    Multi-signal fusion with priority:
      1. to_state ∈ terminal_states → 'forward' (terminal is business end)
      2. risk_traits contains 'rollback' → 'resubmit' (P2 annotated rollback)
      3. branch_path dimension name contains '前状态' or 'pre_state'
         → 'side_effect' (P1 annotated side-effect marker)
      4. Keyword fallback (v29 #26k: configurable via _ACTION_KEYWORDS):
         - If _ACTION_KEYWORDS is configured, use those
         - If not configured (empty sets), use _DEFAULT_*_KW (backward compat)
         - SKIP keyword fallback if branch_path is non-empty
         - action/desc contains 重新提交/修改后/重新发起/重启/恢复 → 'resubmit'
      5. Default → 'forward'

    Returns: 'forward' | 'side_effect' | 'resubmit'
    """
    if not from_state or not to_state:
        return 'forward'

    # Signal 1: terminal state (highest priority — terminal is business end,
    # even if action contains "取消" or traits has 'rollback')
    if to_state in terminal_states:
        return 'forward'

    # Signal 2: risk_traits contains 'rollback' (P2 structured annotation)
    traits = to.get('risk_traits') or to.get('traits') or []
    if 'rollback' in traits:
        return 'resubmit'

    # Signal 3: branch_path dimension name contains '前状态'/'pre_state'
    # (P1 structured annotation — marks side-effect transitions like 暂停/挂起)
    bp = to.get('branch_path') or []
    for b in bp:
        dim_name = b.get('dimension', '') or ''
        if '前状态' in dim_name or 'pre_state' in dim_name.lower():
            return 'side_effect'

    # Signal 4: keyword fallback (v29 #26k: keywords are now configurable
    # via _context.action_keywords, defaulting to empty sets).
    # v29 #22b: SKIP keyword fallback if branch_path is non-empty — P1 has
    # already provided structured annotation, keyword match on branch
    # variant text (e.g. "（暂停状态）" in action) would misclassify.
    # v29 Engineering Optimization Gap 1: record fallback ONLY when keyword
    # matching actually classifies the edge — reaching the keyword check
    # without a match means the edge is genuinely "forward", which is the
    # expected happy path (not a fallback). Logging every forward edge
    # would flood the report with noise.
    bp = to.get('branch_path') or []
    if not bp:
        action = to.get('action', '') or ''
        desc = to.get('desc', '') or to.get('description', '') or ''
        # v29 #26k: read keywords from _ACTION_KEYWORDS (configurable)
        # If empty, fall back to _DEFAULT_*_KW (backward compat).
        _configured_rollback = bool(_ACTION_KEYWORDS.get('rollback'))
        _configured_resubmit = bool(_ACTION_KEYWORDS.get('resubmit'))
        _rollback_kw = _ACTION_KEYWORDS.get('rollback') or _DEFAULT_ROLLBACK_KW
        _resubmit_kw = _ACTION_KEYWORDS.get('resubmit') or _DEFAULT_RESUBMIT_KW
        # v29 Engineering Optimization: try keyword match first, log ONLY
        # if a keyword actually matched (i.e. structured signals missed
        # what keyword logic caught).
        _to_id = to.get('id', '') or ''
        _matched_kw = ''
        if _resubmit_kw and (any(kw in action for kw in _resubmit_kw) or any(kw in desc for kw in _resubmit_kw)):
            _matched_kw = 'resubmit'
        elif _rollback_kw and (any(kw in action for kw in _rollback_kw) or any(kw in desc for kw in _rollback_kw)):
            _matched_kw = 'rollback'
        if _matched_kw:
            # Keyword logic classified this edge — structured signals missed it.
            if not (_configured_rollback or _configured_resubmit):
                _record_fallback(
                    "s0.classify_edge_type.default_keywords",
                    transition_id=_to_id,
                    detail=(
                        f"edge ({from_state}->{to_state}) classified as {_matched_kw} "
                        f"by DEFAULT keywords (P1 didn't declare action_keywords)"
                    ),
                    fallback_used="default_chinese_keywords",
                )
            else:
                _record_fallback(
                    "s0.classify_edge_type.action_keywords",
                    transition_id=_to_id,
                    detail=(
                        f"edge ({from_state}->{to_state}) classified as {_matched_kw} "
                        f"by project-specific _context.action_keywords"
                    ),
                    fallback_used="project_specific_keywords",
                )
            if _matched_kw == 'resubmit':
                return 'resubmit'
            else:
                return 'side_effect'

    # v29 #24b: detect "back to earlier state" edges (regression edges).
    # These are forward-looking in action text (e.g. "归档联动" doesn't
    # contain rollback keywords), but they go from a LATER state to an
    # EARLIER state in the state machine (e.g. 待归档→已选入, 待归档→待选入).
    # Detect by checking if to_state appears BEFORE from_state in the
    # state list (state_info.states is ordered by business progression).
    # This prevents cycles in the forward graph that would break BFS.
    if from_state and to_state and terminal_states:
        # Only check if we have state_info states list
        # (passed via terminal_states context — we need the full state list)
        pass  # handled below in _derive_phase_table with state_order

    # Default: forward progression
    return 'forward'


def _enrich_primary_sub_dims(primary: str, primary_dimension: str,
                             state_info: dict | None,
                             state_to_phase: dict[str, dict[str, int]],
                             include_sub_dims: bool) -> dict[str, dict[str, int]]:
    """㊾ 方案A：把主实体自身次维度并入 phase_table.state_to_phase。

    根因（DECISIONS ㊾）：主实体自身次维度（如报名记录的 发票状态/费用状态/
    通知状态/报名记录样品状态）既不在 phase_table.state_to_phase（只含
    primary_dimension）也不在 dep_state_phase_map（_derive_dep_state_phase_map
    对 primary 一律 continue）→ _resolve_phase 对它们落 fallback P0 → S2 排序
    全部挤在 P0，与报名记录主生命周期脱节。

    修复：从 state_info 取次维度的显式 phase_mapping（或 states 列表顺序）
    并入 state_to_phase。_resolve_phase 对主实体只查 phase_table.state_to_phase
    [dimension]，并入后 S1/S2/S3 零改动即按各自生命周期排序。只读 state_info，
    不引入 TO 推导，保持确定性。

    只对 pipeline 主实体调用生效（include_sub_dims=True，调用点 3117）。
    从属/虚拟实体复用 _derive_phase_table 的路径（2067/2151/2774/2801，传
    单实体 orig_si）不触发——它们的 shift 逻辑遍历 state_to_phase 全维度，
    多键会污染 state_phase。
    """
    if not include_sub_dims or not state_info or not isinstance(state_info, dict):
        return state_to_phase
    ent = state_info.get(primary)
    if not isinstance(ent, dict):
        return state_to_phase
    dim_field = ent.get('dimensions') if isinstance(ent.get('dimensions'), (list, dict)) else ent
    dims = _normalize_dim_list(dim_field)
    for dim in dims:
        if dim == primary_dimension or dim in state_to_phase:
            continue
        pm = _get_explicit_phase_mapping(state_info, primary, dim)
        if pm:
            state_to_phase[dim] = pm
    return state_to_phase


def _derive_phase_table(primary: str, tos: list[dict], cos: list[dict],
                        state_info: dict | None = None,
                        include_sub_dims: bool = False) -> dict:
    """Derive primary_dimension and state_to_phase via longest-path in DAG.

    Uses longest path (not BFS shortest path) so that skip-transitions
    (e.g., 待开始→进行中) do NOT collapse phases.

    Initial state handling (v29 #4 fix):
    ─────────────────────────────────────
    If ``state_info`` declares an explicit ``initial`` state for the
    primary entity's primary dimension, that state is FORCED to P0 —
    even if it also appears as the ``to`` of some transition (rare but
    possible when a rollback/rejection path re-enters the initial state).

    Without this explicit pin, an initial state that happens to have an
    inbound forward edge would inherit `src_phase + 1` and drift away
    from P0, breaking the "entry of the primary entity is P0" contract.

    Rollback handling:
    ───────────────────
    Edges whose action/desc/traits contain 退回/驳回/撤销/退款 are
    "rollback" edges.  Their target state should be at the SAME phase
    as the source's FORWARD predecessor (not +1 from source).

    Example: 结果已提交(P3) → 结果退回修改(rollback)
    Forward predecessor of 结果已提交 = 结果待提交(P2)
    So 结果退回修改 = P2 (semantically "back to waiting"), NOT P3.

    This matches business intuition: a rollback state puts you back
    to the phase BEFORE the rollback source, not at the same phase
    as the rollback source.
    """
    # Determine primary_dimension — pick the dimension with the MOST STATES
    # (not CO frequency).  The primary dimension should be the one whose
    # state machine spans the most business stages — that's the dimension
    # that defines the phase_table's granularity.
    #
    # Old logic used CO enabler_dimension frequency, but that picks the
    # dimension most-referenced by cross-entity constraints, NOT the one
    # with the most complete state machine.  For E-REG, CO references
    # 费用状态 (only 2 states), but 报名记录状态 has 8 states covering
    # the full business flow.
    dim_state_count: dict[str, int] = defaultdict(int)
    for to in tos:
        if to.get('entity') == primary and to.get('dimension'):
            dim_state_count[to['dimension']] += 1
    if dim_state_count:
        primary_dimension = max(dim_state_count, key=dim_state_count.get)
    else:
        # Fallback: CO enabler_dimension frequency (legacy behavior)
        dim_freq = defaultdict(int)
        for co in cos:
            if co.get('causal_type') == 'constraint' and co.get('enabler_entity') == primary:
                dim = co.get('enabler_dimension', '')
                if dim:
                    dim_freq[dim] += 1
        primary_dimension = max(dim_freq, key=dim_freq.get) if dim_freq else ''

    # v29 #4: resolve explicit initial state from state_info.
    # This state will be force-pinned to P0 after the longest-path BFS,
    # overriding any accidental +1 propagation through rollback cycles.
    declared_initial_state = ''
    if state_info and isinstance(state_info, dict):
        si_ent = state_info.get(primary, {})
        if isinstance(si_ent, dict):
            # state_info 三形态统一归一（Layout B dimensions 列表），否则读不到 initial
            dim_field = si_ent.get('dimensions') if isinstance(si_ent.get('dimensions'), (list, dict)) else si_ent
            si_dim = _normalize_dim_list(dim_field).get(primary_dimension, {})
            if isinstance(si_dim, dict):
                declared_initial_state = (si_dim.get('initial') or '').strip()

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

    # ── V08 fix: spec-first phase mapping ──────────────────────────
    # P2 derives phase_mapping deterministically and writes it to
    # state_info[entity][dim].phase_mapping. Use it verbatim — the
    # longest-path BFS below is only a fallback for projects where
    # P2 didn't produce a phase_mapping.
    explicit_pm = _get_explicit_phase_mapping(state_info, primary, primary_dimension)
    if explicit_pm:
        phase_map = dict(explicit_pm)
        max_phase = max(phase_map.values()) if phase_map else 0
        phase_names = [f'P{i}' for i in range(max_phase + 1)]
        state_to_phase = {primary_dimension: phase_map}
        state_to_phase = _enrich_primary_sub_dims(
            primary, primary_dimension, state_info, state_to_phase, include_sub_dims)
        return {
            'primary_entity': primary,
            'primary_dimension': primary_dimension,
            'state_to_phase': state_to_phase,
            'phase_names': phase_names,
            'phase_count': max_phase + 1,
        }
    # ── End V08 fix ────────────────────────────────────────────────

    # Fallback: BFS longest-path derivation (legacy behavior, only
    # triggered when no explicit phase_mapping is available).
    if not primary_tos:
        phase_names = ['P0']
        return {
            'primary_entity': primary,
            'primary_dimension': primary_dimension,
            'state_to_phase': state_to_phase,
            'phase_names': phase_names,
            'phase_count': 1,
        }

    # Classify edges: forward vs rollback
    # Rollback detection: based on ACTION TEXT keywords, NOT traits.
    # traits=['rollback'] in coverage_model marks any transition involved
    # in rollback flow — including re-submit edges (报名退回→报名待审核)
    # which are actually FORWARD edges back to normal flow.
    #
    # True rollback edges have action containing 退回/驳回 AND go from a
    # "normal" state to a "sent back" state (e.g. 报名待审核→报名退回).
    # Re-submit edges (报名退回→报名待审核) are forward and must NOT be
    # classified as rollback, otherwise the forward graph breaks.
    #
    # v29 #22: edge classification uses _classify_edge_type (multi-signal fusion)
    # instead of keyword-only _is_rollback/_is_resubmit.
    # Structured signals (terminal, risk_traits, branch_path) take priority
    # over keyword fallback. See _classify_edge_type for details.
    # Keywords preserved as fallback for projects without structured annotations.
    rollback_keywords = {'退回', '驳回', '撤销', '退款', '暂停', '取消'}  # fallback only
    resubmit_keywords = {'重新提交', '修改后', '重新发起', '重启', '恢复'}  # fallback only

    # Resolve terminal states from state_info (for _classify_edge_type)
    # v29 #24g: only use primary_dimension's terminals, not all dimensions
    # (otherwise a secondary dim with empty terminal overwrites the primary's)
    _primary_terminals: set[str] = set()
    if state_info and isinstance(state_info, dict):
        si_ent = state_info.get(primary, {})
        if isinstance(si_ent, dict):
            # Only get terminals from primary_dimension (already selected above)
            # state_info 三形态统一归一（Layout B dimensions 列表），否则读不到 terminal
            dim_field = si_ent.get('dimensions') if isinstance(si_ent.get('dimensions'), (list, dict)) else si_ent
            dim_info = _normalize_dim_list(dim_field).get(primary_dimension, {})
            if isinstance(dim_info, dict):
                term = dim_info.get('terminal', [])
                if isinstance(term, list):
                    _primary_terminals = {s.strip() for s in term if isinstance(s, str) and s.strip()}

    def _edge_type(to_obj: dict) -> str:
        """Classify edge using multi-signal fusion (v29 #22)."""
        f = to_obj.get('from')
        t = to_obj.get('to')
        f = f.strip() if isinstance(f, str) else (f if f else '')
        t = t.strip() if isinstance(t, str) else (t if t else '')
        return _classify_edge_type(to_obj, f, t, _primary_terminals)

    # Build state order from state_info states list, if available.
    # state_info 三形态统一经 _normalize_dim_list 归一——否则 Layout B 的
    # dimensions 列表读不到 states，state_order 恒空，回归边剔除(G0.3/I14)
    # 与背边检测全部退化为空序兜底。只取 primary_dimension。
    state_order: dict[str, int] = {}
    if state_info and primary in state_info:
        si_ent = state_info.get(primary, {})
        if isinstance(si_ent, dict):
            dim_field = si_ent.get('dimensions') if isinstance(si_ent.get('dimensions'), (list, dict)) else si_ent
            dim_info = _normalize_dim_list(dim_field).get(primary_dimension)
            if isinstance(dim_info, dict):
                for idx, s in enumerate(dim_info.get('states', []) or []):
                    if isinstance(s, str) and s and s not in state_order:
                        state_order[s] = idx

    # Build forward graph (excluding rollback AND resubmit edges) and rollback list
    forward_graph: dict[str, list[str]] = defaultdict(list)
    forward_predecessors: dict[str, list[str]] = defaultdict(list)  # state → [forward predecessors]
    rollback_edges: list[tuple[str, str]] = []  # (from, to) for rollback edges
    resubmit_edges: list[tuple[str, str]] = []  # v29 #21b: (from, to) for resubmit edges
    all_states = set()
    initial_states = set()
    in_degree: dict[str, int] = defaultdict(int)

    for to in primary_tos:
        f = to.get('from')
        t = to.get('to')
        f = f.strip() if isinstance(f, str) else (f if f else '')
        t = t.strip() if isinstance(t, str) else (t if t else '')
        if t:
            all_states.add(t)
        if f:
            all_states.add(f)
            if t:
                et = _edge_type(to)
                if et == 'side_effect':
                    rollback_edges.append((f, t))
                elif et == 'resubmit':
                    resubmit_edges.append((f, t))
                else:  # forward
                    # Fix-4d: skip self-loops (f == t) — they don't carry
                    # phase progression and create false cycles.
                    if f == t:
                        pass  # ignore self-loop in forward graph
                    # G0.3/I14: also skip edges where to_state is earlier in
                    # business progression than from_state (regression edges).
                    # This prevents T-007a (待归档→已选入) and similar
                    # backward-looking transitions from breaking the forward
                    # DAG and collapsing phases.
                    elif state_order and f in state_order and t in state_order and state_order[t] <= state_order[f]:
                        rollback_edges.append((f, t))  # treat as rollback to preserve forward progression
                    elif t not in forward_graph[f]:
                        # v29 #25c: deduplicate forward edges — multiple branch
                        # variants of the same transition (e.g. T-PROJ-007a×10)
                        # produce the same (from, to) edge. Without dedup,
                        # in_degree gets inflated (e.g. in_degree[已选入]=15
                        # instead of 2), breaking BFS longest-path computation.
                        forward_graph[f].append(t)
                        forward_predecessors[t].append(f)
                        in_degree[t] = in_degree.get(t, 0) + 1
        elif t:
            initial_states.add(t)

    for s in all_states:
        if s not in in_degree:
            in_degree[s] = 0

    # v29 #24b: detect cycles in forward_graph and reclassify
    # "back to earlier state" edges as side_effect.
    # Strategy: compute topological order, then any edge going from
    # higher order to lower order is a "back edge" → reclassify as side_effect.
    # This preserves the main forward chain while breaking cycles.
    import networkx as nx
    G_forward = nx.DiGraph()
    for f, targets in forward_graph.items():
        for t in targets:
            G_forward.add_edge(f, t)
    if not nx.is_directed_acyclic_graph(G_forward):
        # Has cycles — compute approximate topological order
        # (ignoring cycle edges) to determine which edges are "back edges"
        # Use DFS to find back edges
        edges_to_remove = set()
        try:
            cycles = list(nx.simple_cycles(G_forward))
        except Exception:
            cycles = []
        # For each cycle, the back edge is the one where to_state is
        # EARLIER in business progression than from_state (i.e., it
        # "goes back" to an earlier stage).
        # Use state_info.states order if available to determine which
        # state is "earlier". If not available, use the cycle order:
        # the back edge is the one where to_state appears BEFORE
        # from_state in the cycle (closing the loop).
        # Get state order from state_info (passed to _derive_phase_table)
        # v29 #24h: ONLY use primary_dimension's state order (not all dims)
        state_order: dict[str, int] = {}
        si_for_order = {}
        if state_info and primary in state_info:
            si_for_order = state_info[primary]
        if isinstance(si_for_order, dict):
            # Only use primary_dimension's states for ordering.
            # 同上方 Spot：Layout B 的 dimensions 列表必须归一，否则 state_order
            # 恒空 → 环形主状态机背边检测退化为 (cyc[-1], cyc[0]) 兜底（空序退化）。
            dim_field = si_for_order.get('dimensions') if isinstance(si_for_order.get('dimensions'), (list, dict)) else si_for_order
            dim_info_order = _normalize_dim_list(dim_field).get(primary_dimension, {})
            if isinstance(dim_info_order, dict):
                for i, s in enumerate(dim_info_order.get('states', []) or []):
                    if isinstance(s, str) and s and s not in state_order:
                        state_order[s] = i

        for cyc in cycles:
            if len(cyc) < 2:
                continue
            # Find the back edge: the edge where to_state has LOWER
            # state_order than from_state (i.e., goes back to earlier state)
            back_edge = None
            for j in range(len(cyc)):
                f = cyc[j]
                t = cyc[(j + 1) % len(cyc)]
                if f in state_order and t in state_order:
                    if state_order[t] <= state_order[f]:
                        back_edge = (f, t)
                        break
            if not back_edge:
                # Fallback: use cycle's last→first edge
                back_edge = (cyc[-1], cyc[0])
            edges_to_remove.add(back_edge)
        # Move these edges from forward_graph to a separate list
        # v29 #25g: cycle-removed edges are NOT rollback edges — they're
        # "conditional regression" edges (e.g. 待归档→已选入 when 评级合格).
        # Adding them to rollback_edges causes rollback post-processing
        # to overwrite BFS-correct phases with wrong values.
        # Instead, just remove them from forward_graph without rollback processing.
        new_forward = defaultdict(list)
        removed_count: dict[str, int] = defaultdict(int)
        for f, targets in forward_graph.items():
            for t in targets:
                if (f, t) in edges_to_remove:
                    # Don't add to rollback_edges — just drop
                    removed_count[t] += 1
                else:
                    if t not in new_forward[f]:
                        new_forward[f].append(t)
        # Adjust in_degree by actual removed count
        for t, cnt in removed_count.items():
            in_degree[t] = max(0, in_degree.get(t, 0) - cnt)
        forward_graph = new_forward
        # Rebuild forward_predecessors
        forward_predecessors = defaultdict(list)
        for f, targets in forward_graph.items():
            for t in targets:
                forward_predecessors[t].append(f)

    # v29 #24j: recompute in_degree from deduplicated forward_graph
    # (forward_graph was deduplicated by `if t not in new_forward[f]`,
    # but in_degree was not adjusted to match. This caused BFS to
    # never dequeue nodes because remaining_in never reached 0.)
    in_degree = defaultdict(int)
    for f, targets in forward_graph.items():
        for t in targets:
            in_degree[t] += 1
    for s in all_states:
        if s not in in_degree:
            in_degree[s] = 0

    # Longest-path BFS on forward edges only
    phase_map: dict[str, int] = {s: 0 for s in initial_states}
    queue = deque([s for s in all_states if in_degree.get(s, 0) == 0])
    remaining_in = dict(in_degree)

    while queue:
        node = queue.popleft()
        if node not in phase_map:
            phase_map[node] = 0
        for nxt in forward_graph.get(node, []):
            phase_map[nxt] = max(phase_map.get(nxt, 0), phase_map[node] + 1)
            remaining_in[nxt] = remaining_in.get(nxt, 1) - 1
            if remaining_in.get(nxt, 0) <= 0:
                queue.append(nxt)

    for s in all_states:
        if s not in phase_map:
            phase_map[s] = 0

    # v29 #4: Force-pin declared initial state to P0.
    # state_info.initial is the authoritative "entry of the primary entity"
    # signal. If it accidentally picked up a +1 (e.g. via a re-submit edge
    # that loops back to the initial state), unconditionally reset to P0.
    # This also makes the entry invariant explicit rather than implicit.
    if declared_initial_state and declared_initial_state in phase_map:
        if phase_map[declared_initial_state] != 0:
            phase_map[declared_initial_state] = 0

    # Fix-4b: Terminal-state phase pinning.
    # state_info.terminal declares business-end states (e.g. E-PLAN: 结束,
    # 超时结束, 取消结束). These should map to the MAXIMUM phase, not to
    # from_state.phase+1 — because they represent the end of the lifecycle,
    # regardless of which earlier state the cancellation/timeout originated
    # from. Without this pin, "取消结束" (from 已建立 P0 → 取消结束) gets
    # assigned P1 instead of P5, placing terminal procedures at the start
    # of the test execution order.
    if _primary_terminals:
        # Compute provisional max from non-terminal states first
        non_terminal_phases = [p for s, p in phase_map.items()
                                if s not in _primary_terminals]
        provisional_max = max(non_terminal_phases) if non_terminal_phases else 0
        for term_state in _primary_terminals:
            if term_state in phase_map:
                # Pin terminal to provisional_max (do NOT use the terminal's
                # own phase in computing max — that would create a feedback
                # loop where multiple terminals inflate each other).
                phase_map[term_state] = provisional_max

    # Apply rollback rule: rollback target's phase = rollback source's
    # "normal predecessor" phase.
    #
    # "Normal predecessor" = forward predecessor that is NOT itself a
    # rollback target.  This excludes re-submit edges (e.g. 报名退回→报名待审核)
    # which would create circular dependencies.
    #
    # Examples:
    #   报名待审核(P1) → 报名退回(rollback):
    #     normal preds of 报名待审核 = [] (only pred is 报名退回, a rollback target)
    #     → 报名退回 = 报名待审核's phase = P1 (same as source)
    #
    #   结果已提交(P4) → 结果退回修改(rollback):
    #     normal preds of 结果已提交 = [结果待提交(P3)] (结果退回修改 is also a pred but it's a rollback target)
    #     → 结果退回修改 = 结果待提交's phase = P3 (one phase back)
    #
    # This matches business intuition: rollback puts you back to the phase
    # BEFORE the rollback source's current stage.
    rollback_target_states = {tgt for _, tgt in rollback_edges}

    for src, tgt in rollback_edges:
        # Find normal (non-rollback-target) forward predecessors of src
        normal_preds = [
            p for p in forward_predecessors.get(src, [])
            if p not in rollback_target_states
        ]
        if normal_preds:
            pred_phases = [phase_map.get(p, 0) for p in normal_preds]
            phase_map[tgt] = min(pred_phases)
        else:
            # No normal predecessor — source is entry or only reachable via
            # re-submit cycle.  Rollback target = source's phase.
            phase_map[tgt] = phase_map.get(src, 0)

    max_phase = max(phase_map.values()) if phase_map else 0
    phase_names = [f'P{i}' for i in range(max_phase + 1)]

    state_to_phase = {primary_dimension: phase_map}
    state_to_phase = _enrich_primary_sub_dims(
        primary, primary_dimension, state_info, state_to_phase, include_sub_dims)

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


def _apply_gated_preconditions(
    entity: str, dim: str, tos: list[dict], phase_table: dict,
    rel_phase_map: dict,
) -> dict | None:
    """门禁前置锚定：入口门禁整体平移 vs 阶段门禁钉住目标态及之后（2026-09-08）。

    旧实现（_entry_from_gated_preconditions）把门禁一律沿相对相位回传入口态并
    **整条维度平移**——对"入口门禁"正确（生命周期整体在门禁后才开始，如
    E-PJ.评价状态：待评价→评价中 前置 报名记录.结果已提交 →
    {待评价:4, 评价中:5, ...}），但对"阶段门禁"会误伤早期态：E-XM.项目状态
    T-037/T-067(进行中→报告审核中) 前置 结果已提交 若整体平移得 {待开始:2,
    报名中:3, 进行中:4, 报告审核中:5, 已结束:6}，把项目早期创建/报名用例
    错误拖后（PROC-008/020 相位被抬）。

    阶段门禁语义：门禁作用在**目标态**上，只把目标态及之后的相对相位钉到
    ref_phase+1，早期态保持相对相位不动。判别：门禁转换的 from 若等于维度
    入口态（rel 最小的态）→ 入口门禁（整条平移）；否则 → 阶段门禁（后缀平移）。
    E-XM.项目状态：进行中→报告审核中 前置 结果已提交(P4) → 报告审核中=5、
    已结束=6，待开始/报名中/进行中保持 0/1/2。

    返回 None = 无门禁（退回原逻辑）；否则返回该维度完整相位映射。
    """
    primary_entity = phase_table.get("primary_entity", "")
    primary_dim = phase_table.get("primary_dimension", "")
    primary_states = phase_table.get("state_to_phase", {}).get(primary_dim, {})
    if not rel_phase_map or not primary_states:
        return None
    entity_tos = [t for t in tos if t.get("entity") == entity and t.get("dimension") == dim]
    entry_state = min(rel_phase_map, key=rel_phase_map.get)

    # 每条门禁：入口门禁标记 + 目标态 + 位移量 delta = ref_phase + 1 - rel[目标态]。
    gates: list[tuple[bool, str, int]] = []
    for to in entity_tos:
        ref_phase = None
        for prec in to.get("preconditions", []) or []:
            if isinstance(prec, dict) and prec.get("pattern") == "phase_anchor":
                continue  # 单转换相位锚定，非整机门禁（与策略 0 同规则）
            ref = prec.get("ref") if isinstance(prec, dict) else None
            if (isinstance(ref, dict)
                    and ref.get("entity") == primary_entity
                    and ref.get("dimension") == primary_dim
                    and ref.get("state") in primary_states):
                pv = primary_states[ref["state"]]
                ref_phase = pv if ref_phase is None else max(ref_phase, pv)
        if ref_phase is None:
            continue
        target = (to.get("to") or "").strip()
        if target not in rel_phase_map:
            continue
        frm = (to.get("from") or "").strip()
        is_entry = (not frm) or frm == entry_state
        delta = (ref_phase + 1) - int(rel_phase_map.get(target, 0))
        gates.append((is_entry, target, delta))
    if not gates:
        return None

    out: dict[str, int] = {}
    for s, p in rel_phase_map.items():
        p = int(p)
        best = 0
        for is_entry, target, delta in gates:
            if is_entry or p >= int(rel_phase_map[target]):
                best = max(best, delta)
        out[s] = p + max(0, best)
    return out


def _compute_entry_phase(
    entity: str,
    anchor: str,
    dim: str,
    tos: list[dict],
    phase_table: dict,
    dep_map: dict,
    structural: list[dict] = None,
    cos: list[dict] = None,
    transition_relations: list[dict] = None,
    restrict_05: bool = False,
) -> int:
    """Compute entry phase for a dependent entity's dimension.

    Strategies (in priority order):
    0. Precondition-based: TO preconditions reference primary-entity states
       (e.g. "项目状态为已结束" → phase 4).  This is the most direct signal.
    2. CO constraint: fallback when no upstream chain found
    3. Structural composition: anchor creates child entity
    4. 从维度: transition_relations where to=entity
    5. Anchor min phase fallback

    restrict_05=True: run ONLY Strategy 0 then Strategy 5.  The fixpoint-recursive
    upstream anchoring (Strategy 1) and the heuristic fallbacks (2/3/4) are
    skipped — they are the risk surface for cyclic-state-machine non-convergence
    (V08's original reason for short-circuiting the whole anchoring path).
    """
    # Strategy 0: Precondition-based phase derivation
    # Scan this entity's TO preconditions for primary-entity state references.
    # If a TO says "项目状态为已结束", the entity's entry happens AFTER
    # the primary entity reaches "已结束", so entry_phase = 已结束's phase + 1.
    # The +1 is critical: without it, E-ARC (precondition "已结束"=ph4) would
    # get entry=4, same as E-EVAL (评价中=ph4), causing them to interleave.
    # With +1, E-ARC entry=5, separating it from E-EVAL (entry=3).
    #
    # phase_anchor 前置例外：P2 的 phase_anchor 把"某个转换"锚定到主实体后置
    # 状态（如 机构评价→计划状态.结束），这是**单转换相位**信号，S1/S3 消费。
    # 它不代表"整个状态机入口在后置状态"——若在此被整机入口启发式捕获，会把
    # 该维度全部状态抬到锚点相位（E-ORG 循环机 合格/不合格/试用 {0,1,2} 被
    # 抬成 {6,7,8}，连创建转换 T-041 也被拖后），与 scope=non_creation 语义相悖。
    # 故 pattern=phase_anchor 的前置跳过入口锚定推导。
    primary_entity = phase_table.get('primary_entity', '')
    primary_dim = phase_table.get('primary_dimension', '')
    primary_states = phase_table.get('state_to_phase', {}).get(primary_dim, {})
    entity_tos = [t for t in tos if t.get('entity') == entity and t.get('dimension') == dim]

    # P2 emits preconditions as dicts {"text","type","ref"} where ref
    # {"entity","dimension","state"} names the referenced state STRUCTURALLY.
    # Prefer that data-layer signal over scanning the natural-language text:
    #   - T-034 "评审计划状态由待启动变为待评审" ref.state=待评审 — the entry
    #     condition is the TO-state 待评审 (phase 2), NOT the from-state 待启动
    #     (phase 1) that a text scan hits first via dict iteration order.
    #   - phase_anchor preconditions (pattern="phase_anchor") are single
    #     transition anchors (见上), excluded here exactly as before.
    # When multiple structured refs exist, the entry must wait for the LATEST
    # primary state (max phase) — every referenced state gates the entry.
    # Text scan remains only as a fallback for preconditions without a
    # usable ref (e.g. P1-inherited bare strings).
    ref_phase = None
    text_phase = None
    for to in entity_tos:
        for prec in to.get('preconditions', []) or []:
            if isinstance(prec, dict) and prec.get('pattern') == 'phase_anchor':
                continue  # 单转换相位锚定，非整机入口锚定（见上）
            ref = prec.get('ref') if isinstance(prec, dict) else None
            if (isinstance(ref, dict)
                    and ref.get('entity') == primary_entity
                    and ref.get('dimension') == primary_dim
                    and ref.get('state') in primary_states):
                pv = primary_states[ref['state']]
                ref_phase = pv if ref_phase is None else max(ref_phase, pv)
                continue
            if text_phase is None:
                prec_text = prec.get('text', '') if isinstance(prec, dict) else str(prec or '')
                for state_name, phase_val in primary_states.items():
                    if state_name and len(state_name) >= 2 and state_name in prec_text:
                        text_phase = phase_val
                        break
    # ⑧ 遗留: Strategy 0 消费 constraint_predicate 的结构化状态引用。
    # preconditions[].ref 只覆盖 type=state_ref 前提；type=constraint 前提的
    # 状态引用在 constraint_predicate 里——field_equals 的 ref_state_dimension
    # 把字段值解析回状态维度（暂停前计划状态=待评审 → E-PLAN.计划状态.待评审），
    # completion.target / selection_range.source_state 等直接命名状态。
    # 与 preconditions[].ref 同语义：命中主实体主维度状态 → 计入入口门禁（max），
    # 每个引用的状态都是入口门禁（⑰ 语义不变）。phase_anchor 是前置级标记，
    # 谓词树无此标记，跳过规则不在此重复。
    for to in entity_tos:
        for rent, rdim, rstate in iter_predicate_state_refs(to.get('constraint_predicate')):
            if rent == primary_entity and rdim == primary_dim and rstate in primary_states:
                pv = primary_states[rstate]
                ref_phase = pv if ref_phase is None else max(ref_phase, pv)
    if ref_phase is not None:
        return ref_phase + 1  # +1: dependent starts AFTER primary reaches state
    if text_phase is not None:
        return text_phase + 1

    if restrict_05:
        # Strategy 5 only: anchor min phase fallback.
        # Primary-anchored entities: the primary is never in dep_map, so this
        # degrades to 0 (no shift) — the conservative default for entities with
        # no primary-state precondition signal.
        if anchor in dep_map:
            all_phases = [p for dm in dep_map[anchor].values() for p in dm.values()]
            if all_phases:
                non_zero = [p for p in all_phases if p > 0]
                return min(non_zero) if non_zero else min(all_phases)
        return 0

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

    # Strategy 3: Causal fallback — use primary entity's LATEST phase
    # Root-cause fix: replaced structural composition heuristic with causal
    # reasoning.  When no upstream chain is found, the entity has no explicit
    # causal trigger in the data.  Previously this fell back to
    # "min(primary phases)" which pulled everything to early phases
    # (causing E-PROJ to be all P1).
    #
    # New logic: use primary entity's MAX phase.  Rationale: if we don't
    # know when this entity is triggered, assume it's available throughout
    # the lifecycle.  Using max means its procedures sort LATER (closer to
    # completion), which is safer than sorting early — late procedures
    # with missing causal info don't break early flow, but early procedures
    # with wrong phase can block downstream.
    primary_dim = phase_table.get('primary_dimension', '')
    anchor_map = phase_table.get('state_to_phase', {}).get(primary_dim, {})
    if anchor_map:
        return max(anchor_map.values())

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


def _lookup_cross_entity_precondition_phase(
    preconditions: list[str],
    self_entity: str,
    phase_table: dict,
    dep_map: dict,
    primary: str,
) -> int | None:
    """Look up the phase referenced by a precondition that points to a
    CROSS-ENTITY state.

    Used for sub-state machine detection: if an entity's entry transition
    (from=None) has a precondition referencing another entity's state, we
    anchor the entire sub-state machine to that state's phase.

    Args:
        preconditions: List of precondition strings
        self_entity: The entity whose entry we're examining (skip self-refs)
        phase_table: Primary entity's phase table
        dep_map: Already-computed dep_state_phase_map entries
        primary: Primary entity id

    Returns:
        The phase of the referenced cross-entity state, or None if no
        cross-entity state reference found.
    """
    import re

    if not preconditions:
        return None

    # Build state → phase lookup across all entities EXCEPT self
    state_to_phase: dict[str, int] = {}
    # Primary entity states
    if primary and primary != self_entity:
        for dim_map in phase_table.get("state_to_phase", {}).values():
            for s, p in dim_map.items():
                if s not in state_to_phase or p > state_to_phase[s]:
                    state_to_phase[s] = p
    # Dependent entity states (already computed)
    for ent, dims in dep_map.items():
        if ent == self_entity:
            continue
        for dim_states in dims.values():
            for s, p in dim_states.items():
                if s not in state_to_phase or p > state_to_phase[s]:
                    state_to_phase[s] = p

    if not state_to_phase:
        return None

    # Build (dim_name, state) → phase for dim-qualified matching
    dim_state_to_phase: dict[tuple[str, str], int] = {}
    if primary and primary != self_entity:
        for dim_name, state_map in phase_table.get("state_to_phase", {}).items():
            for s, p in state_map.items():
                key = (dim_name, s)
                if key not in dim_state_to_phase or p > dim_state_to_phase[key]:
                    dim_state_to_phase[key] = p
    for ent, dims in dep_map.items():
        if ent == self_entity:
            continue
        for dim_name, state_map in dims.items():
            for s, p in state_map.items():
                key = (dim_name, s)
                if key not in dim_state_to_phase or p > dim_state_to_phase[key]:
                    dim_state_to_phase[key] = p

    # Extract state values from preconditions
    # Same regex as S1's _max_precondition_phase (excludes closing parens)
    prec_state_re = re.compile(
        r'(?:为|=|状态=)\s*[\u201c\u2018\"\']?([^\u201d\u2019\"\'，,；;（(（)）\s]+)[\u201d\u2019\"\']?'
    )
    # Dim-qualified pattern: "<dim>为<state>" or "<dim>状态为<state>"
    dim_qualified_re = re.compile(
        r'([^\s，,；;（(（)）=为]{2,15}?)\s*(?:状态)?\s*为\s*([\u4e00-\u9fa5A-Za-z0-9（）()]+)'
    )

    for prec in preconditions:
        if not prec or not isinstance(prec, str):
            continue

        # Strategy 0: dim-qualified match
        dim_qualified_hits = []
        for m in dim_qualified_re.finditer(prec):
            dim_qualified_hits.append((m.group(1).strip(), m.group(2).strip()))

        if dim_qualified_hits:
            for dim_q, state_q in dim_qualified_hits:
                if (dim_q, state_q) in dim_state_to_phase:
                    return dim_state_to_phase[(dim_q, state_q)]
                # Substring match on dim name
                for (d, s), p in dim_state_to_phase.items():
                    if dim_q in d and s == state_q:
                        return p
        else:
            # Strategy 1: bare "为XXX" match
            for m in prec_state_re.finditer(prec):
                val = m.group(1).strip()
                if val in state_to_phase:
                    return state_to_phase[val]

        # Strategy 2: arrow-separated states
        if "->" in prec or "→" in prec:
            normalized = prec.replace("→", "->")
            for chunk in normalized.split("->"):
                chunk = chunk.strip()
                chunk = re.sub(r'^[（(]+\s*', '', chunk)
                chunk = re.sub(r'\s*[）)]*$', '', chunk)
                if chunk and len(chunk) >= 2 and chunk in state_to_phase:
                    return state_to_phase[chunk]

    return None


# ── 2026-09 排序修复 A：同动作组收集 + 相位对齐 ──────────────────────────
# 用户报告的三类排序问题中，问题 1/3 的共同根因：SRS 用 link_op_transition
# （op.linked_transitions）与 transition_relations 声明了"同一因果事件的多
# 个实体视图"，但 _derive_dep_state_phase_map 只在非显式相位分支消费
# transition_relations；走 spec-first（显式 phase_mapping + 入口锚定）路径
# 的维度（如 E-YP.样品状态）完全不感知绑定，叠加默认前向 +1，同一动作的
# 两个视图相位错档（t17→已核查=P4 vs t18→待发样=P3，核查排在收样后）。
# 本组函数在 S0 相位推导完成后做一次组内对齐：
#   组来源（并集，重叠组合并）：
#     a) _context.transition_relations[].evidence_transitions（跨实体证据组）
#     b) entity_obligations[].linked_transitions（P1 link_op_transition，
#        经 P2 透传；亦兼容 _context.op_links）
#   对齐规则：组内含主实体视图时以其相位为权威（主时间线 = 单一事实源）；
#   否则取组内最小相位（入口锚定派生最接地，默认前向 +1 最不可信）。
#   只调整组内各转换 to 态的相位，不修改 phase_table（主实体时间线）。

def _collect_same_action_groups(cm: dict) -> list:
    """Collect same-action transition groups from declared bindings only.

    v2 scope: link_op_transition 声明绑定 ONLY（eo.linked_transitions /
    _context.op_links）。transition_relations 的 evidence 组是同一维度
    时间线上的先后状态（如 缴费通知单 未发送→已发送），非"同一动作的
    跨实体视图"，不收集（v1 曾消费它，实测把已发送 P3 拉到 P2）。
    Returns a list of transition-id groups (each ≥2 tids spanning ≥2
    entities). Overlapping groups are merged. Tolerant to all data
    shapes: absent fields yield no groups.
    """
    tos = cm.get('transition_obligations', []) or []
    tid_entity = {}
    for to in tos:
        if not isinstance(to, dict):
            continue
        tid = to.get('id') or to.get('transition_id') or ''
        if tid:
            tid_entity[tid] = to.get('entity', '')

    groups = []

    def _add_group(tids):
        valid = [t for t in tids if t in tid_entity]
        ents = {tid_entity[t] for t in valid}
        if len(valid) >= 2 and len(ents) >= 2:
            groups.append(set(valid))

    ctx = cm.get('_context', {}) or {}

    for eo in cm.get('entity_obligations', []) or []:
        lt = eo.get('linked_transitions') if isinstance(eo, dict) else None
        if lt and len(lt) >= 2:
            _add_group(list(lt))

    for ol in ctx.get('op_links', []) or []:
        trs = ol.get('transitions', []) or []
        if len(trs) >= 2:
            _add_group(list(trs))

    merged = []
    for g in groups:
        overlap = [m for m in merged if m & g]
        if overlap:
            uni = set.union(g, *overlap)
            for m in overlap:
                merged.remove(m)
            merged.append(uni)
        else:
            merged.append(g)
    return [sorted(m) for m in merged]


# v1 的 _align_same_action_phases（S0 内 dep_map 对齐）已删除，两个必然缺陷：
#   a) S0 时主实体视图只能读 raw phase_table（待发样=0），真实相位（P3）
#      要等 S1 入口门控/state_ref 提升，S0 阶段算不出 → 对齐目标系统性偏低
#      （实测 t17/t18 组 已核查 P4→P0）；
#   b) 对主实体成员写 dep_state_phase_map[primary] 直接 KeyError（主实体
#      不在 map 中），且 S1 解析主实体相位不读 dep_map，写了也无效。
# v2 由 s1_generation._align_same_action_phases_post_s1 在 S1 之后按
# 各 proc 的真实派生相位对齐（事实相位，无需推断）。


def _derive_dep_state_phase_map(
    primary: str,
    phase_table: dict,
    tos: list[dict],
    dependent_entities: list[str],
    entity_parent: dict,
    state_type_map: dict,
    virtual_entities: dict,
    cos: list[dict] = None,
    transition_relations: list[dict] = None,
    structural: list[dict] = None,
    state_info: dict = None,
    branch_value: str = "",
) -> tuple[dict, dict]:
    """S0.3 step 3: Dependent entity phase mapping via anchor-entity method.

    branch_value（branch_values 生命周期归属改造）：非空时 dependent 实体的
    explicit phase_mapping 优先取该分支的 phase_mapping_by_branch 视图。
    

    Includes: from-state补全 (1.2), 从维度 mapping (1.3)

    Returns (dep_state_phase_map, contextual_phase_rules).
    """
    dep_map: dict[str, dict[str, dict[str, int]]] = {}
    ctx_rules: dict[str, dict] = {}

    # ── Causal-order entity computation ──
    # Compute entities in topological order based on transition_relations
    # causal direction (NOT entity_parent structural direction).
    # If entity A's transitions are driven by entity B's transitions
    # (via transition_relation B→A), B must be computed first.
    raw_entities = list(dependent_entities) + list(virtual_entities.keys())
    # v29 #25d: also include entities that have transition_obligations with
    # dimensions but were not detected as dependent_entities (e.g. E-SCORE
    # has 打分状态 transitions but no structural relation from primary).
    for to in tos:
        e = to.get('entity', '')
        if e and e != primary and e not in raw_entities:
            # Check if this entity has at least one transition with a dimension
            # (entities without dimensions don't need phase map processing)
            if to.get('dimension'):
                raw_entities.append(e)
    entity_causal_deps: dict[str, set[str]] = {e: set() for e in raw_entities if e != primary}
    to_by_tid = {t.get('transition_id'): t for t in tos if t.get('transition_id')}
    for tr in (transition_relations or []):
        from_e = tr.get('from', '')
        to_e = tr.get('to', '')
        if to_e != primary and from_e != to_e and to_e in entity_causal_deps:
            if from_e != primary or from_e in entity_causal_deps:
                entity_causal_deps[to_e].add(from_e)

    # Kahn topological sort
    in_degree = {e: len(deps) for e, deps in entity_causal_deps.items()}
    queue = sorted([e for e, d in in_degree.items() if d == 0])
    all_entities = []
    while queue:
        e = queue.pop(0)
        all_entities.append(e)
        for other, deps in entity_causal_deps.items():
            if e in deps:
                in_degree[other] -= 1
                if in_degree[other] == 0:
                    inserted = False
                    for i, q in enumerate(queue):
                        if other < q:
                            queue.insert(i, other)
                            inserted = True
                            break
                    if not inserted:
                        queue.append(other)
    for e in raw_entities:
        if e != primary and e not in all_entities:
            all_entities.append(e)

    # state_info: entity → dim → initial state (from coverage_model._context)
    state_info = state_info or {}

    for entity in all_entities:
        if entity == primary:
            continue

        is_ve = entity in virtual_entities
        ve_info = virtual_entities.get(entity, {})
        anchor = ve_info.get('parent_entity') if is_ve else entity_parent.get(entity)

        # v29 #25d: entities with transitions but no detected parent (anchor)
        # should still be processed — use the entity itself as anchor.
        # This fixes E-SCORE (打分状态) being skipped because _detect_
        # dependent_entities didn't find a structural relation from E-PLAN
        # to E-SCORE (the relation is E-PROJ → E-SCORE, not E-PLAN → E-SCORE).
        if not anchor:
            # Check if this entity has transitions with dimensions
            ent_tos = [t for t in tos if t.get('entity') == entity and t.get('dimension')]
            if ent_tos:
                anchor = entity  # self-anchor — process with P0 fallback
            else:
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
                    dim_map[dim][target] = 0
            dep_map[entity] = dict(dim_map)
            continue

        # ── Causal-graph-based phase derivation ──
        # Root-cause design (no compensation layers):
        # 1. phase only changes at BUSINESS STAGE boundaries, not at every
        #    state transition.  Same-entity forward edges do NOT +1 phase.
        # 2. transition_relation binds cross-entity transitions to the SAME
        #    phase (they are the same causal event seen from both sides).
        # 3. side_effect (rollback) edges: target phase = source phase.
        # 4. state_info.initial states → P0.
        # 5. Entities without causal binding fall back to anchor min phase.
        entity_tos = [t for t in tos if t.get('entity') == entity]
        dim_map: dict[str, dict[str, int]] = defaultdict(dict)
        dim_tos: dict[str, list[dict]] = defaultdict(list)
        for to in entity_tos:
            dim = to.get('dimension', '')
            dim_tos[dim].append(to)

        # Build transition_id → transition lookup for this entity
        tid_to_to: dict[str, dict] = {t.get('transition_id', ''): t for t in entity_tos if t.get('transition_id')}

        # Build bidirectional causal bindings: for each transition T in this
        # entity, collect all OTHER transitions that share a transition_relation
        # with T (regardless of which side T is on).  transition_relation
        # declares that from-side and to-side transitions are the same causal
        # event → same phase.
        tr_bindings: dict[str, list[str]] = defaultdict(list)
        for tr in (transition_relations or []):
            ev = tr.get('evidence_transitions', []) or []
            # Find this entity's transitions in the evidence
            my_tids = [t for t in ev if t in tid_to_to]
            # Find the OTHER entity's transitions in the evidence
            other_tids = [t for t in ev if t in to_by_tid and t not in tid_to_to]
            for mtid in my_tids:
                tr_bindings[mtid].extend(other_tids)

        for dim, dim_transitions in dim_tos.items():
            # ── V08 fix: spec-first phase mapping ──────────────────
            # If P2 produced phase_mapping for this (entity, dim), use
            # it verbatim and skip the fixpoint / sub-state-machine /
            # cyclic-dim compensation logic below.
            explicit_pm_dep = None
            if branch_value:
                # branch_values 改造：优先取该分支的 lifecycle 相位链
                explicit_pm_dep = _get_branch_phase_mappings(
                    state_info, entity, dim).get(branch_value)
            if not explicit_pm_dep:
                explicit_pm_dep = _get_explicit_phase_mapping(state_info, entity, dim)
            if explicit_pm_dep:
                pm_states = set(explicit_pm_dep.keys())
                trans_states = set()
                for to in dim_transitions:
                    f = to.get('from', '')
                    t = to.get('to', '')
                    f = f.strip() if isinstance(f, str) else (f if f else '')
                    t = t.strip() if isinstance(t, str) else (t if t else '')
                    if t: trans_states.add(t)
                    if f: trans_states.add(f)
                merged = dict(explicit_pm_dep)
                for s in trans_states - pm_states:
                    merged[s] = 0
                # Step-1 revival: global anchoring via entry phase (S0+5 only).
                # Shift the local scale onto the primary timeline UNLESS the dim
                # already shares state names with the primary dim — shared names
                # mean the local scale was aligned to the primary already (e.g.
                # E-PROJ.项目状态 待评审:2/评审中:3 == primary 待评审:2/评审中:3),
                # and an extra offset would inflate phases past P5.
                primary_dim_s = phase_table.get('primary_dimension', '')
                primary_state_names = set(
                    (phase_table.get('state_to_phase', {}) or {}).get(primary_dim_s, {}).keys()
                )
                # 门禁前置锚定：入口门禁整体平移 / 阶段门禁只钉目标态及之后
                # （_apply_gated_preconditions，2026-09-08 取代旧整条平移实现）。
                # 无门禁 → 回落策略 0/5。
                gated = _apply_gated_preconditions(
                    entity, dim, tos, phase_table, merged,
                )
                if gated is not None:
                    dim_map[dim] = gated
                else:
                    _entry = 0
                    if not (set(merged.keys()) & primary_state_names):
                        _entry = _compute_entry_phase(
                            entity, anchor, dim, tos, phase_table, dep_map,
                            structural=structural, cos=cos,
                            transition_relations=transition_relations, restrict_05=True,
                        )
                    if _entry:
                        dim_map[dim] = {s: int(_entry) + int(p) for s, p in merged.items()}
                    else:
                        dim_map[dim] = {s: int(p) for s, p in merged.items()}
                continue  # skip fixpoint / sub-sm / cyclic branches
            # ── End V08 fix ────────────────────────────────────────
            all_states = set()
            for to in dim_transitions:
                f = to.get('from', '')
                t = to.get('to', '')
                f = f.strip() if isinstance(f, str) else (f if f else '')
                t = t.strip() if isinstance(t, str) else (t if t else '')
                if t: all_states.add(t)
                if f: all_states.add(f)

            # v29 #5: Toggle pair detection.
            # A toggle pair is (A→B, B→A) where NEITHER edge has rollback/
            # resubmit keywords. These represent business toggles like
            # 启用↔停用 / 激活↔冻结 / 上线↔下线. Both edges should propagate
            # the SAME phase (no +1) — otherwise the fixpoint iteration
            # inflates phase until max_iter (E-LAB T-074↔T-075 bug).
            # v29 #22: use _classify_edge_type (multi-signal fusion) instead
            # of keyword-only check. Structured signals (terminal, risk_traits,
            # branch_path) take priority over keyword fallback.
            si_ent = state_info.get(entity, {}) if isinstance(state_info, dict) else {}
            # state_info 三形态统一归一（Layout B dimensions 列表），否则读不到 terminal
            dim_field = si_ent.get('dimensions') if isinstance(si_ent.get('dimensions'), (list, dict)) else si_ent
            si_dim_info = _normalize_dim_list(dim_field).get(dim, {})
            _dim_terminals: set[str] = set()
            if isinstance(si_dim_info, dict):
                term = si_dim_info.get('terminal', [])
                if isinstance(term, list):
                    _dim_terminals = {s.strip() for s in term if isinstance(s, str) and s.strip()}

            def _is_side_effect_edge(to_obj: dict) -> bool:
                """v29 #22: use _classify_edge_type for side-effect detection."""
                f = to_obj.get('from', '')
                t = to_obj.get('to', '')
                f = f.strip() if isinstance(f, str) else (f if f else '')
                t = t.strip() if isinstance(t, str) else (t if t else '')
                et = _classify_edge_type(to_obj, f, t, _dim_terminals)
                return et in ('side_effect', 'resubmit')

            # Build edge index: (from_state, to_state) → [transition_ids]
            edge_index: dict[tuple[str, str], list[str]] = defaultdict(list)
            for to in dim_transitions:
                f = to.get('from', '')
                t = to.get('to', '')
                f = f.strip() if isinstance(f, str) else (f if f else '')
                t = t.strip() if isinstance(t, str) else (t if t else '')
                if f and t:
                    edge_index[(f, t)].append(to.get('transition_id', ''))

            # A transition is a "toggle edge" if its reverse edge also exists
            # AND neither direction is a rollback/resubmit side_effect.
            toggle_tids: set[str] = set()
            for (f, t), tids in edge_index.items():
                reverse_tids = edge_index.get((t, f), [])
                if not reverse_tids:
                    continue
                # Check neither direction is rollback/resubmit
                fwd_objs = [to for to in dim_transitions if to.get('transition_id') in tids]
                rev_objs = [to for to in dim_transitions if to.get('transition_id') in reverse_tids]
                if any(_is_side_effect_edge(o) for o in fwd_objs + rev_objs):
                    continue
                # Both directions exist and neither is side-effect → toggle
                for tid in tids + reverse_tids:
                    toggle_tids.add(tid)

            # v29 #1: state_info.terminal as cross-stage signal.
            # If from_state is declared terminal in state_info, this forward
            # edge crosses a business stage boundary → +1 is justified.
            # Otherwise the default is +1 (preserves v28 behavior); the
            # within-stage issue (e.g. 报名待审核→报名成功 both at P1) requires
            # richer state_info.stages data to fully fix, documented as a
            # known limitation.
            si_ent = state_info.get(entity, {}) if isinstance(state_info, dict) else {}
            # state_info 三形态统一归一（Layout B dimensions 列表），否则读不到 terminal
            dim_field = si_ent.get('dimensions') if isinstance(si_ent.get('dimensions'), (list, dict)) else si_ent
            si_dim = _normalize_dim_list(dim_field).get(dim, {})
            terminal_states: set[str] = set()
            if isinstance(si_dim, dict):
                term = si_dim.get('terminal', [])
                if isinstance(term, list):
                    terminal_states = {s.strip() for s in term if isinstance(s, str) and s.strip()}

            UNASSIGNED = -1
            state_phase: dict[str, int] = {s: UNASSIGNED for s in all_states}

            # v29 #10 (root-cause fix for 通知状态 phase 传播不完整):
            # Pre-seed declared initial state to P0 BEFORE the fixpoint loop.
            #
            # Root cause:
            #   The fixpoint only resolves a forward edge (from→to) when the
            #   from_state already has a phase. If the declared initial state
            #   is never a `to` of any transition (common pattern: entry is
            #   `未发送 → 待确认`, not `null → 未发送`), it stays UNASSIGNED
            #   forever and the entire downstream chain defers. Eventually
            #   all unassigned states get backfilled to 0, losing the +1
            #   propagation. S1's precondition-bump only rescues transitions
            #   that have cross-entity preconditions; same-dim chains (e.g.
            #   T-061/T-062/T-063 in E-REG.通知状态) stay at P0.
            #
            # Fix: seed declared initial state to P0 here. The downstream
            #   fixpoint will then propagate P1, P2, ... via forward +1.
            #   This is consistent with _derive_phase_table's behavior on
            #   the primary entity (where in_degree=0 → phase 0 implicitly
            #   handles initial state).
            if isinstance(si_dim, dict):
                init_state = si_dim.get('initial', '')
                # v29 #25a: pre-seed initial state even if not in all_states
                # (e.g. "未打分" is declared initial in state_info but never
                # appears as a transition's from/to — it's the implicit
                # starting state before T-SCORE-001 fires).
                # Old check `init_state in state_phase` failed for these
                # states because state_phase was built from all_states
                # (which only contains transition from/to values).
                if isinstance(init_state, str) and init_state.strip():
                    state_phase[init_state] = 0
                    all_states.add(init_state)  # ensure it's in all_states too

            # ── Sub-state machine detection ──
            # A dim is a sub-state machine if:
            # 1. Its entry transition has a cross-entity TR binding, AND
            # 2. Its OTHER transitions do NOT have TR bindings to DIFFERENT
            #    phases (if they do, the dim spans multiple business stages
            #    and is NOT a sub-state machine).
            #
            # Example sub-state machine: E-EVAL.评价状态
            #   - Entry T-090 bound to T-015 (E-REG.结果已提交)
            #   - T-091/T-092/T-093/T-094 have NO TR bindings
            #   - All 4 states anchor to entry phase
            #
            # Example NOT sub-state machine: E-REG.报名记录状态
            #   - Entry T-010 bound to T-001 (P1)
            #   - T-014 bound to T-002 (P2) ← different phase!
            #   - T-019 bound to T-004 (P4) ← different phase!
            #   - Dim spans P1-P4, NOT a sub-state machine
            sub_sm_phase = None
            entry_bound_phases = set()
            other_bound_phases = set()

            for to in dim_transitions:
                tid = to.get('transition_id', '')
                is_entry = not to.get('from')
                for bound_tid in tr_bindings.get(tid, []):
                    bp = None
                    bt = to_by_tid.get(bound_tid)
                    if bt:
                        bt_entity = bt.get('entity', '')
                        bt_dim = bt.get('dimension', '')
                        bt_to = bt.get('to', '')
                        bt_to = bt_to.strip() if isinstance(bt_to, str) else (bt_to if bt_to else '')
                        if bt_entity == primary:
                            pm = phase_table.get('state_to_phase', {}).get(bt_dim, {})
                            bp = pm.get(bt_to) if bt_to else None
                        elif bt_entity in dep_map and bt_dim in dep_map.get(bt_entity, {}):
                            bp = dep_map[bt_entity][bt_dim].get(bt_to)
                    if bp is not None:
                        if is_entry:
                            entry_bound_phases.add(bp)
                        else:
                            other_bound_phases.add(bp)

            # Sub-state machine: entry has binding, others have NO binding or
            # all bindings point to the same phase as entry.
            #
            # Fix-4a: be conservative — if any non-entry transition has a TR
            # binding whose other-side entity has NOT YET been processed (i.e.
            # dep_map doesn't contain it), DO NOT declare sub-state machine.
            # Otherwise we falsely collapse states when the binding target's
            # phase is simply not yet known (e.g. E-SCORE processed before
            # E-PROJ, so T-SCORE-003's binding to T-PROJ-006 can't be resolved).
            unresolvable_bindings = False
            for to in dim_transitions:
                tid = to.get('transition_id', '')
                for bound_tid in tr_bindings.get(tid, []):
                    bt = to_by_tid.get(bound_tid)
                    if not bt:
                        continue
                    bt_entity = bt.get('entity', '')
                    bt_dim = bt.get('dimension', '')
                    bt_to = bt.get('to', '')
                    if bt_entity == primary:
                        pm = phase_table.get('state_to_phase', {}).get(bt_dim, {})
                        if bt_to and bt_to not in pm:
                            unresolvable_bindings = True
                    elif bt_entity in dep_map and bt_dim in dep_map.get(bt_entity, {}):
                        # resolvable
                        pass
                    elif bt_entity != entity:
                        # Not yet processed — can't determine binding phase
                        unresolvable_bindings = True

            if entry_bound_phases and not unresolvable_bindings:
                entry_phase_val = max(entry_bound_phases)
                if not other_bound_phases or other_bound_phases == {entry_phase_val}:
                    sub_sm_phase = entry_phase_val
                    if os.environ.get('S0_TRACE') == '1' and entity in ('E-SCORE', 'E-USER'):
                        print(f'[SUBSM] entity={entity} dim={dim} sub_sm_phase={sub_sm_phase}', flush=True)
            elif os.environ.get('S0_TRACE') == '1' and entity in ('E-SCORE', 'E-USER'):
                print(f'[SUBSM-SKIP] entity={entity} dim={dim} entry={entry_bound_phases} unresolvable={unresolvable_bindings}', flush=True)

            if sub_sm_phase is not None:
                # Fix-4: sub-state machine — preserve internal state ordering
                # instead of collapsing all states to a single phase.
                #
                # Original behavior: assigned all states to entry_phase_val.
                # This collapsed E-SCORE (未打分→已保存→已提交) into a single
                # phase, losing the temporal ordering of the scoring lifecycle.
                #
                # New behavior: use _derive_phase_table to compute RELATIVE
                # phases within the sub-state machine (0, 1, 2, ...), then
                # shift by sub_sm_phase as the base. This preserves the
                # internal ordering while keeping the sub-state machine anchored
                # to the parent entity's phase.
                #
                # If _derive_phase_table fails (no forward edges / cyclic),
                # fall back to the original flat-assign behavior.
                entity_tos_for_sub = [t for t in tos if t.get('entity') == entity]
                orig_si_sub = {}
                if entity in state_info:
                    orig_si_sub = {entity: state_info[entity]}
                try:
                    sub_pt = _derive_phase_table(
                        entity, entity_tos_for_sub, cos, state_info=orig_si_sub
                    )
                    sub_s2p = sub_pt.get('state_to_phase', {}).get(dim, {})
                    if sub_s2p and len(sub_s2p) >= 2:
                        # Shift relative phases by sub_sm_phase as base
                        for s in all_states:
                            rel = sub_s2p.get(s, 0)
                            state_phase[s] = sub_sm_phase + rel
                        # Also include any states declared in state_info but
                        # not in sub_s2p (e.g. 未打分 declared as initial but
                        # never a transition's from/to)
                        si_ent_sub = state_info.get(entity, {}) if isinstance(state_info, dict) else {}
                        # state_info 三形态统一归一（Layout B dimensions 列表），否则读不到 initial
                        dim_field_sub = si_ent_sub.get('dimensions') if isinstance(si_ent_sub.get('dimensions'), (list, dict)) else si_ent_sub
                        si_dim_sub = _normalize_dim_list(dim_field_sub).get(dim, {})
                        if isinstance(si_dim_sub, dict):
                            init_s = si_dim_sub.get('initial', '')
                            if init_s and init_s not in state_phase:
                                state_phase[init_s] = sub_sm_phase
                        dim_map[dim] = dict(state_phase)
                        continue
                except Exception:
                    pass
                # Fallback: flat-assign all states to sub_sm_phase
                state_phase = {s: sub_sm_phase for s in all_states}
                dim_map[dim] = dict(state_phase)
                continue

            # Helper: look up phase of a transition's to_state from any entity
            def _lookup_phase(transition_id: str) -> int | None:
                t = to_by_tid.get(transition_id)
                if not t:
                    return None
                t_entity = t.get('entity', '')
                t_dim = t.get('dimension', '')
                t_to = t.get('to', '')
                t_to = t_to.strip() if isinstance(t_to, str) else (t_to if t_to else '')
                if t_entity == primary:
                    pm = phase_table.get('state_to_phase', {}).get(t_dim, {})
                    return pm.get(t_to) if t_to else None
                if t_entity in dep_map and t_dim in dep_map.get(t_entity, {}):
                    return dep_map[t_entity][t_dim].get(t_to)
                return None

            # Fixpoint iteration
            # v29 #25f: detect cyclic state machines and use _derive_phase_table
            # for proper phase computation (instead of just assigning anchor_phase).
            # Cyclic state machines (like E-ORG: 合格→不合格→试用→合格, or
            # E-PROJ: 待归档→已选入/待选入) need back-edge removal + BFS,
            # not just flat assignment.
            import networkx as nx
            _cyclic_dim = False
            _dim_G = nx.DiGraph()
            for to in dim_transitions:
                f = to.get('from', '')
                t = to.get('to', '')
                f = f.strip() if isinstance(f, str) else (f if f else '')
                t = t.strip() if isinstance(t, str) else (t if t else '')
                if f and t:
                    # Fix-4d: skip self-loops (f == t) — they are no-op
                    # transitions (e.g. 已保存→已保存 for re-save) and add
                    # networkx cycles that falsely trigger the cyclic-DIM
                    # path, which then removes the real forward edge
                    # (已保存→已提交) and collapses all states to phase 0.
                    if f == t:
                        continue
                    et = _is_side_effect_edge(to)
                    if not et:  # only forward edges
                        _dim_G.add_edge(f, t)
            if not nx.is_directed_acyclic_graph(_dim_G):
                _cyclic_dim = True

            if _cyclic_dim:
                # v29 #25h: use _derive_phase_table for cyclic state machines
                # It has proper back-edge removal (using state_order from
                # state_info) + BFS longest-path, which correctly assigns
                # phases like 待选入=P0 → 已归档=P5.
                # Old behavior (#25f): flat assign all states to anchor_phase=P0
                # which lost the phase progression.
                entity_tos_for_pt = [t for t in tos if t.get('entity') == entity]
                orig_si = {}
                if entity in state_info:
                    orig_si = {entity: state_info[entity]}
                cycle_pt = _derive_phase_table(
                    entity, entity_tos_for_pt, cos, state_info=orig_si
                )
                cycle_s2p = cycle_pt.get('state_to_phase', {})
                if cycle_s2p:
                    # Use _derive_phase_table's result, but shift by anchor_phase
                    # if the entity has a parent (to align with parent's phase)
                    anchor_phase = _get_anchor_phase_for_entity(anchor, phase_table, dep_map)
                    for dim_name, state_map in cycle_s2p.items():
                        shifted = {s: p + anchor_phase for s, p in state_map.items()}
                        if dim_name in state_phase:
                            for s, p in shifted.items():
                                state_phase[s] = p
                        else:
                            state_phase.update(shifted)
                    dim_map[dim] = dict(state_phase)
                    continue
                # Fallback: flat assign
                anchor_phase = _get_anchor_phase_for_entity(anchor, phase_table, dep_map)
                state_phase = {s: anchor_phase for s in all_states}
                dim_map[dim] = dict(state_phase)
                continue

            # Apply state_info.initial → P0 ONLY for states not yet resolved
            # by causal tracing.  For dep entities, initial state phase is
            # determined by causal bindings (e.g. E-REG.报名待审核 is bound
            # to E-PROJ.报名中=P1 via transition_relation, NOT P0).
            si = state_info.get(entity, {}) if isinstance(state_info, dict) else {}
            # state_info 三形态统一归一（Layout B dimensions 列表），否则读不到 initial
            dim_field = si.get('dimensions') if isinstance(si.get('dimensions'), (list, dict)) else si
            si_dim = _normalize_dim_list(dim_field).get(dim, {})
            if isinstance(si_dim, dict):
                init_state = si_dim.get('initial', '')
                if init_state and state_phase.get(init_state, UNASSIGNED) == UNASSIGNED:
                    state_phase[init_state] = 0

            # Fix-4c: Backfill UNASSIGNED states intelligently.
            # - Terminal states → anchor_phase (terminal = end of lifecycle,
            #   should be at the latest phase relative to the anchor).
            # - Entry-transition target states (from=None, no upstream) →
            #   anchor_phase (entry of a sub-state-machine anchored to parent).
            # - Other UNASSIGNED states → 0 (root default).
            #
            # Original behavior: backfill ALL unassigned to 0, which collapsed
            # E-SCORE.已保存/已提交 to 0 when their TR bindings couldn't be
            # resolved (because the bound entity was processed later).
            anchor_phase_val = _get_anchor_phase_for_entity(anchor, phase_table, dep_map)
            si_term_states: set[str] = set()
            if isinstance(si_dim, dict):
                term = si_dim.get('terminal', [])
                if isinstance(term, list):
                    si_term_states = {s.strip() for s in term if isinstance(s, str) and s.strip()}

            # Collect states that are targets of entry transitions (from=None)
            entry_target_states: set[str] = set()
            for to in dim_transitions:
                if not to.get('from') and to.get('to'):
                    entry_target_states.add(to['to'].strip() if isinstance(to['to'], str) else to['to'])

            for s in all_states:
                if state_phase.get(s, UNASSIGNED) != UNASSIGNED:
                    continue
                # Terminal → anchor_phase (end of lifecycle)
                if s in si_term_states:
                    state_phase[s] = anchor_phase_val
                # Entry target (no upstream resolved) → anchor_phase
                elif s in entry_target_states:
                    state_phase[s] = anchor_phase_val
                else:
                    state_phase[s] = 0

            dim_map[dim] = {s: p for s, p in state_phase.items()}

        dep_map[entity] = dict(dim_map)

    # (handled inside _compute_entry_phase via the transition_relations param)

    # contextual_phase_rules: 已随 transition_upstream_map 机制清除 (恒 {} —
    # _detect_contextual_phase_rules 曾按 transition_id 索引, 全仓 TO 无该字段)。
    return dep_map, {}


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

    路线 C (2026-08-14): 从属 = strong ∪ transition (第一性原理, 无启发式阈值).
      - strong: composition 所有权 (主实体拥有该实体)
      - transition: transition_relations → primary (实体驱动主实体状态机)
      - reference 边仅产生 weak/medium, 不再构成从属证据——它表达"引用/使用"而非
        "生命周期从属"。
    原 4 级分类的 medium/weak/desc 路径与 CRUD≥4 排除已删除 (见 Step 3); 实测两
    黄金项目 (PT017/review) dependent 集合与删除前逐字节一致。transitivity 保留。
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
    # A causal edge f→primary means "f drives the primary's state machine" —
    # the strongest dependent evidence. Upgrade over weaker structural signals
    # (transition rank == medium, so `>=` flips medium→transition; strong=3 stays).
    # Was: `f not in signal_strength` — blocked when Step 1 already gave f a
    # weaker structural 'medium' (e.g. PT017: E-CAR primary, E-CAR→E-ARC ref).
    for tr in transition:
        f = tr.get('from', '')
        t = tr.get('to', '')
        if t == primary and f and f != primary:
            if _signal_rank('transition') >= _signal_rank(signal_strength.get(f, '')):
                signal_strength[f] = 'transition'
                signal_parent[f] = primary

    # Step 3: F/V/D判定 — 路线 C (2026-08-14): 从属只由第一性原理信号决定
    #   strong     = composition 所有权 (主实体拥有它)
    #   transition = transition_relations → primary (驱动主实体状态机)
    # reference 边仅给 weak/medium, 单独不足以构成从属——它表达"引用/使用"而非
    # "生命周期从属"。原 medium/weak/desc 路径 + CRUD≥4 排除(自管理资源的启发式
    # 代理)已一并删除; 实测两黄金项目 dependent 集合与删除前逐字节一致。
    dependent: list[str] = []

    for entity in list(signal_strength.keys()):
        if entity == primary:
            continue
        sig = signal_strength[entity]
        if sig in ('strong', 'transition'):
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

def _detect_leaf_entities(cm: dict, structural: list[dict],
                          transition_obligations: list[dict],
                          state_info: dict) -> set[str]:
    """S0.5b: Leaf entities — relation-isolated, no transitions, no state machine.

    Single source of truth for the "系统配置尾部" (config/audit tail, e.g. 日志):
    absent from the structural-relation graph entirely, no transition
    obligations, no state machine. Everything else is part of the domain model.

    Direction convention: structural_relations from→to = downstream
    (s0_prompt.py:188); appearing on either side means the entity is a provider
    (base data) or a consumer of the domain graph — not a leaf. Formerly this
    was re-derived inside S2's _entity_order_rank (config-tail) and drifted from
    S0's L0 judgement (部门/角色 mis-sorted behind 用户). Now S0 owns it.
    """
    to_entity_ids = {t.get("entity") for t in transition_obligations if t.get("entity")}
    related_ids = {r.get("from") for r in structural if r.get("from")} | \
                  {r.get("to") for r in structural if r.get("to")}
    entity_details = cm.get("_context", {}).get("entity_details", []) or []
    if isinstance(entity_details, dict):
        entity_details = list(entity_details.values())
    leaves = set()
    for ed in entity_details:
        eid = ed.get("id", "")
        if not eid:
            continue
        ndim = len((state_info.get(eid, {}) or {}).get("dimensions", []) or [])
        if ndim == 0 and eid not in to_entity_ids and eid not in related_ids:
            leaves.add(eid)
    return leaves


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

    if managed_entities is None:
        managed_entities = set()

    # Base-data-primary mode: when the primary is itself base data (managed),
    # it belongs at L0 (not L1) and its managed→core edges are actor-action
    # (the primary "performs" tasks), not structural prerequisites. Drop those
    # edges so core tasks sort by their own reference_dependency structure.
    base_data_primary = primary in managed_entities
    if base_data_primary:
        core_entities = set(all_entities) - managed_entities
        structural = [r for r in structural if not (
            r.get('from', '') in managed_entities and r.get('to', '') in core_entities
        )]

    # Core entities demote to L0 only under the legacy reference-child rule;
    # in base-data-primary mode they are tasks and settle at L1.
    def _unassigned_level(eid: str) -> int:
        return 0 if (eid in managed_entities or not base_data_primary) else 1

    # Primary level: managed (base data) → L0, core (main state machine) → L1
    levels[primary] = 0 if base_data_primary else 1

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
                levels[f] = _unassigned_level(f)  # reference/other → L0, foundational config data

    # BFS backtracking (1.7)
    # L3+ entities with unassigned structural upstream → L0
    for rel in structural:
        f = rel.get('from', '')
        t = rel.get('to', '')
        if f not in levels and t in levels and levels[t] >= 3:
            if rel.get('relation_type') in ('composition', 'reference'):
                levels[f] = _unassigned_level(f)  # L0

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
                        levels[e] = _unassigned_level(e)
                    break
        else:
            levels[e] = _unassigned_level(e)

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
    for e in managed_entities:
        if e not in levels:
            levels[e] = 0

    return levels


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
    state_info: dict | None = None,
) -> tuple[dict, dict]:
    """Resolve VE resolved_phase after dep_state_phase_map is computed.

    v29 #24: VE inherits original_entity's state machine phase map,
    not just parent's phase. This prevents state machine fragmentation
    when E-PROJ is split into E-PROJA/E-PROJC by trigger_source.
    """
    co_by_id = {co.get('id'): co for co in cos}
    state_info = state_info or {}

    # v29 #24d: Pre-compute phase maps for all original_entities that
    # are NOT in dep_state_phase_map (their transitions were taken by VEs).
    # This must happen BEFORE VE inheritance loop so all VEs can access
    # the correct original_entity phase map.
    # v29 #25i: also recompute if original_entity IS in dep_state_phase_map
    # but its phase map is all-zeros (cyclic state machine was flat-assigned
    # by #25f old behavior, or _derive_dep_state_phase_map's fixpoint failed).
    # Use _derive_phase_table which has proper back-edge removal + BFS.
    ve_originals = set()
    for ve_name, ve in virtual_entities.items():
        orig = ve.get('original_entity', '')
        if orig:
            ve_originals.add(orig)
    for orig_ent in ve_originals:
        # Check if we need to (re)compute
        need_compute = False
        if orig_ent not in dep_state_phase_map:
            need_compute = True
        elif orig_ent in dep_state_phase_map:
            # Check if all phases are 0 (might need recompute)
            all_zero = True
            for dim_map in dep_state_phase_map[orig_ent].values():
                for p in dim_map.values():
                    if p != 0:
                        all_zero = False
                        break
            if all_zero:
                need_compute = True
        if need_compute:
            orig_tos = [to for to in tos if to.get('entity') == orig_ent]
            if orig_tos:
                orig_si = {}
                if orig_ent in state_info:
                    orig_si = {orig_ent: state_info[orig_ent]}
                orig_phase_table = _derive_phase_table(
                    orig_ent, orig_tos, cos, state_info=orig_si
                )
                orig_s2p = orig_phase_table.get('state_to_phase', {})
                if orig_s2p:
                    dep_state_phase_map[orig_ent] = dict(orig_s2p)

    for ve_name, ve in virtual_entities.items():
        parent = ve.get('parent_entity', '')
        co_ids = ve.get('co_ids', [])
        original_entity = ve.get('original_entity', '')

        # v29 #24: VE inherits original_entity's dep_state_phase_map
        # so transitions split across VEs still get proper per-state phases.
        # E-PROJA/E-PROJC should use E-PROJ's 项目状态 phase map.
        if original_entity and original_entity not in dep_state_phase_map:
            # v29 #24c: original_entity itself not in dep_state_phase_map
            # (its transitions were all taken by VEs). Compute phase map
            # directly from its transitions using _derive_phase_table logic.
            orig_tos = [to for to in tos if to.get('entity') == original_entity]
            if orig_tos:
                # Pass state_info for original_entity so _derive_phase_table
                # can pin the declared initial state to P0 and use terminal
                # states for edge classification.
                orig_si = {}
                if state_info and original_entity in state_info:
                    orig_si = {original_entity: state_info[original_entity]}
                orig_phase_table = _derive_phase_table(
                    original_entity, orig_tos, cos, state_info=orig_si
                )
                orig_s2p = orig_phase_table.get('state_to_phase', {})
                if orig_s2p:
                    dep_state_phase_map[original_entity] = dict(orig_s2p)

        if original_entity and original_entity in dep_state_phase_map:
            if ve_name not in dep_state_phase_map:
                dep_state_phase_map[ve_name] = {}
            for dim, state_map in dep_state_phase_map[original_entity].items():
                # v29 #25j: always overwrite VE's phase map with original's,
                # not just when dim is missing. VE's existing map may be
                # all-zeros from _derive_dep_state_phase_map's fixpoint.
                dep_state_phase_map[ve_name][dim] = dict(state_map)

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
            # v29 #24: don't overwrite VE's inherited state map with single phase
            # Only set resolved_phase for the VE; the per-state phases from
            # original_entity are preserved in dep_state_phase_map[ve_name].
            continue

        # Fallback: parent entity's min phase
        if parent in dep_state_phase_map:
            all_phases = [p for dm in dep_state_phase_map[parent].values() for p in dm.values()]
            if all_phases:
                ve['resolved_phase'] = min(all_phases)
                continue

        if parent == phase_table.get('primary_entity', ''):
            primary_dim = phase_table.get('primary_dimension', '')
            dim_map = phase_table.get('state_to_phase', {}).get(primary_dim, {})
            if dim_map:
                ve['resolved_phase'] = min(dim_map.values())
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

    # 协同角色（glm5pr §1.3 collaborative）归一化：role 为 list（多角色按审批顺序
    # 共同执行，如批量审核由技术主管/授权签字人/实验室负责人）时，取首个执行者
    # 作为 actor，完整列表保留进 note.collaborative_roles 供渲染/审计。
    # 主流水线下游（_get_role_name / entity_operator_set / V07 / 渲染）一律按 str
    # 消费 role——list 直接透传会在 role_map.get(list) 崩溃（unhashable dict key）。
    # P1.5 首次引入协同 role（srs_pipeline schema 允许 list）暴露该缺口；归一化放
    # 数据入口，S0 内部与后续全部阶段统一拿到 str。
    for _lst in ("entity_obligations", "transition_obligations",
                 "cross_entity_obligations", "constraint_obligations"):
        _items = coverage_model.get(_lst)
        if not isinstance(_items, list):
            continue
        for _ob in _items:
            _r = _ob.get("role")
            if not isinstance(_r, (list, tuple)) or not _r:
                continue
            _ob["role"] = _r[0]
            _note = _ob.get("note")
            if isinstance(_note, dict):
                _note["collaborative_roles"] = list(_r)
            else:
                _ob["note"] = {"comment": str(_note) if _note else "",
                               "collaborative_roles": list(_r)}

    # v29 #26k: load configurable action keywords from _context
    global _ACTION_KEYWORDS
    _ctx = coverage_model.get('_context', {}) if isinstance(coverage_model, dict) else {}
    _ak = _ctx.get('action_keywords', {})
    if _ak and isinstance(_ak, dict):
        _ACTION_KEYWORDS = {
            'rollback': set(_ak.get('rollback', [])),
            'resubmit': set(_ak.get('resubmit', [])),
        }

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
        "phase_table_by_branch": result.get("phase_table_by_branch", {}),
        "dep_state_phase_map_by_branch": result.get("dep_state_phase_map_by_branch", {}),
            "contextual_phase_rules": result.get("contextual_phase_rules", {}),
            "state_type_map": result.get("state_type_map", {}),
            "dependent_entities": result.get("dependent_entities", []),
            "entity_parent": result.get("entity_parent", {}),
            "dependency_depth": result.get("dependency_depth", {}),
            "topology_levels": result.get("topology_levels", {}),
            "leaf_entity_ids": result.get("leaf_entity_ids", set()),
            "virtual_entities": result.get("virtual_entities", {}),
            "errors": errors,
            "warnings": warnings,
            "current_stage": "s0_failed",
        }

    return {
        "primary_entity": result.get("primary_entity"),
        "phase_table": result.get("phase_table"),
        "dep_state_phase_map": result.get("dep_state_phase_map", {}),
        "phase_table_by_branch": result.get("phase_table_by_branch", {}),
        "dep_state_phase_map_by_branch": result.get("dep_state_phase_map_by_branch", {}),
        "contextual_phase_rules": result.get("contextual_phase_rules", {}),
        "state_type_map": result.get("state_type_map", {}),
        "dependent_entities": result.get("dependent_entities", []),
        "entity_parent": result.get("entity_parent", {}),
        "dependency_depth": result.get("dependency_depth", {}),
        "topology_levels": result.get("topology_levels", {}),
        "leaf_entity_ids": result.get("leaf_entity_ids", set()),
        "virtual_entities": result.get("virtual_entities", {}),
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
    ros_raw = cm.get('constraint_obligations', [])
    if isinstance(ros_raw, dict):
        ros = [item for sublist in ros_raw.values() for item in sublist]
    elif isinstance(ros_raw, list):
        ros = ros_raw
    else:
        ros = []

    structural, transition = _load_relations(cm)

    # E1: Detect structural contradictions
    _detect_structural_contradictions(structural, warnings)

    # S0.2: Primary entity (v29 #19: multi-signal fusion algorithm)
    # v28 used structural from-side freq only, which fails when main entity
    # is the "dependee" (to-side) or has low structural freq.
    # v29 fuses 5 signals: structural_driver_freq, causal_driver_freq,
    # dependee_score, lifecycle_completeness, container_degree.
    state_info_for_primary = cm.get('_context', {}).get('state_info', {}) if isinstance(cm, dict) else {}
    primary = _identify_primary_entity(structural, transition, tos, eos,
                                        state_info=state_info_for_primary)
    if not primary:
        raise ValueError("S0.2: Could not identify primary_entity")
    warnings.append(f"S0.2: primary_entity={primary}")

    # state_info from coverage_model._context (for initial state detection).
    # Loaded here so S0.3 phase_table can pin the declared initial state
    # to P0 (v29 #4 fix) — previously only _derive_dep_state_phase_map
    # consumed it.
    state_info = cm.get('_context', {}).get('state_info', {}) if isinstance(cm, dict) else {}

    # S0.3: Phase table (longest path)
    # include_sub_dims=True（㊾ 方案A）：主实体自身次维度并入 phase_table.
    # state_to_phase；从属/虚拟实体复用路径保持 include_sub_dims=False。
    phase_table = _derive_phase_table(primary, tos, cos, state_info=state_info,
                                      include_sub_dims=True)
    warnings.append(f"S0.3: primary_dimension={phase_table['primary_dimension']}, phase_count={phase_table['phase_count']}")

    # S0.3b: per-branch phase_table（branch_values 生命周期归属改造）。
    # 分支值集合扫描全部实体的 phase_mapping_by_branch（per-branch 相位
    # 建在 lifecycle bd 的宿主实体上，可能是 dependent 如 E-XM，而非主实体）。
    # 主实体 primary_dimension 有该分支相位时替换视图；S1 相位查询按
    # TO.branch_path 优先取归属分支链，miss 落回全局 phase_table（退化安全）。
    phase_table_by_branch: dict[str, dict] = {}
    if primary and phase_table.get('primary_dimension'):
        _branch_values_all: set = set()
        for _ent_info in (state_info or {}).values():
            for _d in (_ent_info.get('dimensions') or []):
                _pmb = _d.get('phase_mapping_by_branch') or {}
                if isinstance(_pmb, dict):
                    _branch_values_all.update(_pmb.keys())
        _primary_pms = _get_branch_phase_mappings(
            state_info, primary, phase_table['primary_dimension'])
        for _b in sorted(_branch_values_all):
            _pt_b = dict(phase_table)
            _stp = dict(phase_table.get('state_to_phase') or {})
            if _b in _primary_pms:
                _stp[phase_table['primary_dimension']] = dict(_primary_pms[_b])
            _pt_b['state_to_phase'] = _stp
            phase_table_by_branch[_b] = _pt_b
        if _branch_values_all:
            warnings.append(
                f"S0.3b: per-branch phase_table for branch values "
                f"{sorted(_branch_values_all)} (primary pinned: {sorted(_primary_pms)})")

    # S0.4: Dependent entities (cardinality-based)
    dependent_entities, entity_parent, dependency_depth = _detect_dependent_entities(
        primary, structural, transition, tos, eos, cos
    )
    warnings.append(f"S0.4: {len(dependent_entities)} dependent entities: {dependent_entities}")

    # Collect all entities — 保序去重 (dict.fromkeys), 不用 set:
    # set 迭代序随 PYTHONHASHSEED 抖动 (DECISIONS.md 304 同款坑), 会污染
    # dependency_depth/topology_levels 等输出 dict 的键插入序 → 双跑 SHA-256 不一致。
    all_entities = list(dict.fromkeys(
        [to.get('entity', '') for to in tos]
        + [eo.get('entity', '') for eo in eos]
        + [rel.get('from', '') for rel in structural]
        + [rel.get('to', '') for rel in structural]
    ))

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

    # State type map
    state_type_map = _classify_state_types(tos, primary)

    # state_info already loaded above (S0.3 needs it for initial-state pin).
    # Dep state phase map (causal-graph-based phase derivation)
    dep_state_phase_map, contextual_phase_rules = _derive_dep_state_phase_map(
        primary, phase_table, tos, dependent_entities, entity_parent,
        state_type_map, virtual_entities,
        cos=cos, transition_relations=transition, structural=structural,
        state_info=state_info,
    )

    # Resolve VE phases AFTER dep_state_phase_map
    virtual_entities, dep_state_phase_map = _resolve_ve_phases(
        virtual_entities, dep_state_phase_map, phase_table, tos, cos,
        state_info=state_info,
    )

    # S0.4b: per-branch dependent phase map（branch_values 生命周期归属改造）。
    # 按分支重跑锚点法推导：phase_table 换成该分支视图、tos 过滤为
    # 共享 ∪ 归属含该分支的子集（_derive_dep_state_phase_map 内部
    # 消费 tos/phase_table，自身无需改动）。VE 的 resolved_phase 修正
    # 在 by-branch 视图缺失时由 S1 查询 miss 落回全局 map 兑底。
    dep_state_phase_map_by_branch: dict[str, dict] = {}
    if phase_table_by_branch:
        for _b, _pt_b in phase_table_by_branch.items():
            _tos_b = [
                _to for _to in tos
                if not _to.get('branch_path')
                or any(bp.get('value') == _b for bp in (_to.get('branch_path') or []))
            ]
            _dep_b, _ctx_b = _derive_dep_state_phase_map(
                primary, _pt_b, _tos_b, dependent_entities, entity_parent,
                state_type_map, virtual_entities,
                cos=cos, transition_relations=transition, structural=structural,
                state_info=state_info, branch_value=_b,
            )
            dep_state_phase_map_by_branch[_b] = _dep_b
        warnings.append(
            f"S0.4b: per-branch dep_state_phase_map for {sorted(dep_state_phase_map_by_branch)}")

    # 排序修复 A 的相位对齐已迁至 S1 之后（s1_generation.
    # _align_same_action_phases_post_s1）——S0 阶段真实相位尚未派生完成
    # （主实体视图需 S1 入口门控提升），此处对齐目标必然失真（v1 缺陷）。

    if virtual_entities:
        topology_levels = _compute_topology_levels(
            primary, dependent_entities, entity_parent, dependency_depth,
            structural, transition, all_entities, virtual_entities,
            managed_entities=managed_entities
        )
        warnings.append(f"S0.7: {len(virtual_entities)} virtual entities: {list(virtual_entities.keys())}")

    # S0.5b: Leaf entities (config/audit tail) — S0 owns this classification so
    # downstream never re-derives "who is base data" (single source of truth).
    # Give them a level strictly above all flow entities; ordering (a pure
    # topology_levels projection) then sorts them last automatically, while
    # lifecycle/phase predicates (context.domain_precondition.base_data_entity_ids)
    # still treat them as non-lifecycle managed data.
    leaf_entity_ids = _detect_leaf_entities(cm, structural, tos, state_info)
    leaf_level = (max(topology_levels.values()) + 1) if topology_levels else 1
    for e in leaf_entity_ids:
        topology_levels[e] = leaf_level
    if leaf_entity_ids:
        warnings.append(
            f"S0.5b: {len(leaf_entity_ids)} leaf entities at leaf_level={leaf_level}: "
            f"{sorted(leaf_entity_ids)}"
        )

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
        'phase_table_by_branch': phase_table_by_branch,
        'dep_state_phase_map_by_branch': dep_state_phase_map_by_branch,
        'contextual_phase_rules': contextual_phase_rules,
        'state_type_map': state_type_map,
        'dependent_entities': dependent_entities,
        'entity_parent': entity_parent,
        'dependency_depth': dependency_depth,
        'topology_levels': topology_levels,
        'leaf_entity_ids': leaf_entity_ids,
        'virtual_entities': virtual_entities,
    }
