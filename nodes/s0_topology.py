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
      2. causal_driver_freq     — from-side freq in transition_relations
      3. dependee_score         — to-side freq in structural_relations
                                   (being depended ON = main entity)
      4. lifecycle_completeness — initial+terminal+states+transitions
      5. container_degree       — composition from-side count

    Each signal normalized to [0, 1], then weighted sum:
      score = 0.20 * structural_driver_freq
            + 0.25 * causal_driver_freq       # causal chain source is key
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

    # ── Signal 2: causal_driver_freq (transition_relations from-side) ──
    causal_freq: dict[str, float] = defaultdict(float)
    causal_entities: set[str] = set()
    for tr in (transition or []):
        f = tr.get('from', '')
        if not f:
            continue
        w = weight_map.get(tr.get('confidence', 'low'), 0.5)
        causal_freq[f] += w
        causal_entities.add(f)
        # Also count to-side (the dependent in causal relation)
        t = tr.get('to', '')
        if t:
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

    # Populate state counts from state_info
    for ent_id, dims in state_info.items():
        if not isinstance(dims, dict):
            continue
        for dim_name, dim_info in dims.items():
            if not isinstance(dim_info, dict):
                continue
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


def _derive_phase_table(primary: str, tos: list[dict], cos: list[dict],
                        state_info: dict | None = None) -> dict:
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
            si_dim = si_ent.get(primary_dimension, {})
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
            dim_info = si_ent.get(primary_dimension, {})
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

    # Build state order from state_info states list, if available
    state_order: dict[str, int] = {}
    if state_info and primary in state_info:
        for dim_name, dim_data in state_info[primary].items():
            if dim_name == primary_dimension:
                for idx, s in enumerate(dim_data.get('states', []) or []):
                    if s not in state_order:
                        state_order[s] = idx
                break

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
            # Only use primary_dimension's states for ordering
            dim_info_order = si_for_order.get(primary_dimension, {})
            if isinstance(dim_info_order, dict):
                for i, s in enumerate(dim_info_order.get('states', []) or []):
                    if s not in state_order:
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
    restrict_05: bool = False,
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
    for to in entity_tos:
        for prec in to.get('preconditions', []) or []:
            # P2 emits preconditions as dicts {"text","type","ref"} (not bare
            # strings), so membership must test the text, not dict keys.
            if isinstance(prec, dict) and prec.get('pattern') == 'phase_anchor':
                continue  # 单转换相位锚定，非整机入口锚定（见上）
            prec_text = prec.get('text', '') if isinstance(prec, dict) else str(prec or '')
            for state_name, phase_val in primary_states.items():
                if state_name and len(state_name) >= 2 and state_name in prec_text:
                    return phase_val + 1  # +1: dependent starts AFTER primary reaches state

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
    state_info: dict = None,
) -> tuple[dict, dict]:
    """S0.3 step 3: Dependent entity phase mapping via anchor-entity method.

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
                _entry = 0
                if not (set(merged.keys()) & primary_state_names):
                    _entry = _compute_entry_phase(
                        entity, anchor, dim, tos, phase_table, dep_map,
                        transition_upstream_map, structural=structural, cos=cos,
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
            si_dim_info = si_ent.get(dim, {}) if isinstance(si_ent, dict) else {}
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
            si_dim = si_ent.get(dim, {}) if isinstance(si_ent, dict) else {}
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
                        si_dim_sub = (state_info.get(entity, {}).get(dim, {})
                                      if isinstance(state_info, dict) else {})
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

            tid_phase: dict[str, int] = {}
            changed = True
            max_iter = len(dim_transitions) * 3 + 10
            iters = 0
            while changed and iters < max_iter:
                changed = False
                iters += 1
                for to in dim_transitions:
                    tid = to.get('transition_id', '')
                    if not tid or tid in tid_phase:
                        continue
                    f = to.get('from', '')
                    t = to.get('to', '')
                    f = f.strip() if isinstance(f, str) else (f if f else '')
                    t = t.strip() if isinstance(t, str) else (t if t else '')

                    # Check transition_relation binding (strongest signal)
                    bound_phases = []
                    for bound_tid in tr_bindings.get(tid, []):
                        bp = _lookup_phase(bound_tid)
                        if bp is not None:
                            bound_phases.append(bp)

                    if bound_phases:
                        # transition_relation binding → same phase as bound transition.
                        # Do NOT also apply forward +1 — TR binding is the
                        # authoritative phase signal, forward +1 would inflate it.
                        final_phase = max(bound_phases)
                    elif not f:
                        # Entry transition (from=None): try upstream from transition_upstream_map
                        upstreams = transition_upstream_map.get(tid, [])
                        up_phases = []
                        for utid in upstreams:
                            up = _lookup_phase(utid)
                            if up is not None:
                                up_phases.append(up)
                        if up_phases:
                            final_phase = max(up_phases)
                        else:
                            # No causal binding — use anchor min phase
                            final_phase = _get_anchor_phase_for_entity(anchor, phase_table, dep_map)
                    else:
                        # Non-entry, no TR binding: forward edge.
                        # v29 #5: toggle edges (启用↔停用) do NOT +1.
                        # v28 behavior: rollback/re-submit edges do NOT +1.
                        # v29 #1: if from_state is in state_info.terminal,
                        #         this is a cross-stage boundary → +1.
                        #         Otherwise default +1 (within-stage issue
                        #         documented as known limitation; needs
                        #         state_info.stages to fully fix).
                        src_phase = state_phase.get(f, UNASSIGNED)
                        if src_phase != UNASSIGNED:
                            tid_local = to.get('transition_id', '')
                            is_toggle = tid_local in toggle_tids
                            is_side_effect = _is_side_effect_edge(to)
                            if is_toggle or is_side_effect:
                                final_phase = src_phase  # no increment
                                # Fix-4e: side-effect / toggle / resubmit edges
                                # represent state re-entry (e.g. 锁定→未锁定
                                # unlock) and should ONLY set the target phase
                                # if it was previously UNASSIGNED. They must
                                # NOT overwrite a phase already assigned by
                                # an entry transition or a forward edge —
                                # otherwise they pull the entry state up to
                                # the source's phase (e.g. 未锁定 P0 → P1
                                # because 锁定 P1 → 未锁定 resubmit).
                                if t and state_phase.get(t, UNASSIGNED) == UNASSIGNED:
                                    state_phase[t] = final_phase
                                    changed = True
                                tid_phase[tid] = final_phase
                                continue  # skip the normal t-update below
                            elif f in terminal_states:
                                # v29 #1: cross-stage boundary signal
                                final_phase = src_phase + 1
                            else:
                                final_phase = src_phase + 1
                        else:
                            # Source not yet resolved — defer
                            continue

                    tid_phase[tid] = final_phase
                    if os.environ.get('S0_TRACE') == '1' and entity in ('E-SCORE', 'E-USER'):
                        print(f'[FIXPOINT] tid={tid} f={f} t={t} final={final_phase}', flush=True)
                    if t:
                        old = state_phase.get(t, UNASSIGNED)
                        if old == UNASSIGNED or final_phase > old:
                            state_phase[t] = final_phase
                            changed = True
                    # Also set from_state if unset (it may not have an entry)
                    if f and state_phase.get(f, UNASSIGNED) == UNASSIGNED:
                        # If this state is only a from_state and never a to_state,
                        # it's a root state — try initial state info, else P0
                        state_phase[f] = 0
                        changed = True

            # Apply state_info.initial → P0 ONLY for states not yet resolved
            # by causal tracing.  For dep entities, initial state phase is
            # determined by causal bindings (e.g. E-REG.报名待审核 is bound
            # to E-PROJ.报名中=P1 via transition_relation, NOT P0).
            si = state_info.get(entity, {}) if isinstance(state_info, dict) else {}
            if isinstance(si, dict) and dim in si:
                init_state = si[dim].get('initial', '') if isinstance(si[dim], dict) else ''
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
            if isinstance(si, dict) and dim in si and isinstance(si[dim], dict):
                term = si[dim].get('terminal', [])
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

def _tid_to_concrete_ids(tid: str, to_by_tid: dict) -> list[str]:
    """Resolve an abstract transition id to its concrete TO ids.

    Option C: a branch-split transition no longer emits a base TO, so its
    abstract id (referenced by CO enabler/dependent_transition_id) resolves to
    the [a][b]... variant TO ids. Unsplit transitions resolve to themselves.
    Fallback: if the id is not found AND no variants exist (e.g. to_by_tid is
    empty because the model's TOs carry `id` rather than `transition_id`),
    keep the abstract id as-is to preserve pre-Option-C behavior.
    """
    if tid in to_by_tid:
        return [tid]
    variants = sorted(k for k in to_by_tid if k.startswith(tid + "["))
    if variants:
        return variants
    return [tid]


def _build_state_pos(state_info: dict) -> dict:
    """Build {(entity_id, dim_name): {state: position}} from _context.state_info.

    Position = phase_mapping value (fallback: index in the states list). A
    transition whose `to` position is <= its `from` position is a loop/back edge.
    """
    pos: dict[tuple, dict] = {}
    for ent, info in (state_info or {}).items():
        for dim in info.get("dimensions", []) or []:
            dim_name = dim.get("dimension_name", "")
            pm = dim.get("phase_mapping") or {}
            states = dim.get("states") or []
            d = {}
            for i, st in enumerate(states):
                d[st] = pm.get(st, i)
            pos[(ent, dim_name)] = d
    return pos


def _is_back_edge(t: dict, state_pos: dict) -> bool:
    """True if transition t (from->to) goes to an EARLIER state (loop back).

    Back edges (e.g. 归档评级 待归档->已选入 in a cyclic state machine) must
    not become hard prerequisites — they would reverse lifecycle order in the
    final topological sort. Creation (from=None) / terminal (to=None) are not
    back edges; states without lifecycle info are treated as forward.
    """
    frm, to = t.get("from"), t.get("to")
    if frm is None or to is None:
        return False
    d = state_pos.get((t.get("entity"), t.get("dimension")), {})
    pf, pt = d.get(frm), d.get(to)
    if pf is None or pt is None:
        return False
    return pt <= pf


def _rebuild_upstream_map(
    tos: list[dict],
    transition: list[dict],
    cos: list[dict],
    state_pos: dict | None = None,
) -> dict[str, list[str]]:
    """S0.6: Rebuild transition_upstream_map from three sources."""
    upstream_map: dict[str, list[str]] = defaultdict(list)

    to_by_tid = {t.get('transition_id'): t for t in tos if t.get('transition_id')}

    entity_dim_tos: dict[tuple, list[dict]] = defaultdict(list)
    for to in tos:
        key = (to.get('entity'), to.get('dimension'))
        entity_dim_tos[key].append(to)

    # Source 1: Same-entity same-dimension chain ordering
    # Back-edge fix: a loop-back transition (to-state earlier than from-state,
    # e.g. 归档评级 待归档->已选入 in a cyclic machine) must NOT become a hard
    # prerequisite — it would put the archive/rating step before selection in
    # the final topological sort. Only forward chain edges build prerequisites.
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
                    if state_pos is not None and (
                        _is_back_edge(t1, state_pos) or _is_back_edge(t2, state_pos)
                    ):
                        continue
                    upstream_map[t1_tid].append(t2['transition_id'])

    # Source 2: transition_relations evidence
    # v29 #26h: use P1's causal_pairs field (structured) when available.
    # P1's transition_relations now declares:
    #   "causal_pairs": [{"from_tid": "T-XXX", "to_tid": "T-YYY"}]
    # Falls back to #25e index-based pairing when causal_pairs is absent.
    for tr in transition:
        # v29 #26h: prefer structured causal_pairs
        causal_pairs = tr.get('causal_pairs', []) or []
        if causal_pairs:
            for pair in causal_pairs:
                ft = pair.get('from_tid', '')
                tt = pair.get('to_tid', '')
                if ft and tt:
                    upstream_map[tt].append(ft)
            continue  # skip old evidence-based logic for this tr

        # 修复 2: Fallback 可观测 — causal_pairs 缺失时按索引配对, 但要可见.
        # 实验 3: 复杂 case 0/8 输出 causal_pairs. 简单 case 2/2. 不稳定.
        _record_fallback(
            "s0.causal_pairs.index_pairing_fallback",
            detail=(
                f"R({tr.get('from','')}->{tr.get('to','')}) has no causal_pairs; "
                f"falling back to evidence_transitions index-based pairing"
            ),
            fallback_used="index_pairing",
        )
        # Fallback: #25e index-based pairing from evidence_transitions
        ev = tr.get('evidence_transitions', []) or []
        from_tids = [t for t in ev if t in to_by_tid and to_by_tid[t].get('entity') == tr.get('from')]
        to_tids = [t for t in ev if t in to_by_tid and to_by_tid[t].get('entity') == tr.get('to')]
        for i in range(min(len(from_tids), len(to_tids))):
            upstream_map[to_tids[i]].append(from_tids[i])

    # Source 3: CO enabler → dependent transition
    # Option C: CO refs use the abstract (base) transition id, which for a
    # branch-split transition resolves to its [a][b]... variants. Fan the edge
    # out so every concrete variant is wired (branch-agnostic causal link).
    for co in cos:
        et = co.get('enabler_transition_id')
        dt = co.get('dependent_transition_id')
        if et and dt:
            for dv in _tid_to_concrete_ids(dt, to_by_tid):
                for ev in _tid_to_concrete_ids(et, to_by_tid):
                    upstream_map[dv].append(ev)

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
    phase_table = _derive_phase_table(primary, tos, cos, state_info=state_info)
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

    # S0.6: Upstream map (state_pos enables back-edge exclusion so cyclic
    # state machines don't reverse lifecycle order in the dependency DAG)
    state_pos = _build_state_pos(state_info)
    transition_upstream_map = _rebuild_upstream_map(tos, transition, cos, state_pos)
    warnings.append(f"S0.6: upstream_map with {len(transition_upstream_map)} entries")

    # State type map
    state_type_map = _classify_state_types(tos, primary)

    # state_info already loaded above (S0.3 needs it for initial-state pin).
    # Dep state phase map (causal-graph-based phase derivation)
    dep_state_phase_map, contextual_phase_rules = _derive_dep_state_phase_map(
        primary, phase_table, tos, dependent_entities, entity_parent,
        state_type_map, transition_upstream_map, virtual_entities,
        cos=cos, transition_relations=transition, structural=structural,
        state_info=state_info,
    )

    # Resolve VE phases AFTER dep_state_phase_map
    virtual_entities, dep_state_phase_map = _resolve_ve_phases(
        virtual_entities, dep_state_phase_map, phase_table, tos, cos,
        state_info=state_info,
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
