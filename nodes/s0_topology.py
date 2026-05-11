"""S0 Topology Discovery Node — Deterministic Implementation.

Implements all sub-stages S0.1–S0.7 per v3 specification:
  S0.1: Relation loading (structural_relations + transition_relations)
  S0.2: Primary entity identification
  S0.3: Phase table derivation (phase_table, dep_state_phase_map,
         contextual_phase_rules, state_type_map)
  S0.4: Dependent entity detection (dependent_entities, entity_parent,
         dependency_depth)
  S0.5: Topology levels
  S0.6: Upstream map rebuilding
  S0.7: Virtual entity decomposition

Falls back to LLM or existing file only if deterministic computation fails.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from models.state import AgentState

ENTITY_NAME_MAP = {
    '验证项目': 'E-PRJ', '报名记录': 'E-REG', '实验室': 'E-LAB',
    '物品核验单': 'E-VRF', '付款记录': 'E-PAY', '评价': 'E-EVAL',
    '审批流程': 'E-APPR', '归档': 'E-ARCHIVE', '标准库': 'E-STD',
    '测试项': 'E-TEST', '子领域': 'E-CATE', '产品类型': 'E-PTYPE',
    '测试物品': 'E-ITEM', '通知公告': 'E-ANNOUNCE', '常见问题': 'E-FAQ',
    '信息发送记录': 'E-MSG'
}

ROLE_MAP = {
    'R-01': '技术主管', 'R-02': '实验室负责人', 'R-03': '授权签字人',
    'R-04': '策划人员', 'R-05': '项目管理员', 'R-06': '样品制备人员',
    'R-07': '样品管理员', 'R-08': '评价人员', 'R-09': '统计人员',
    'R-10': '质量专员', 'R-11': '财务管理人员', 'R-12': '系统管理人员',
    'R-13': '能力验证参加者', 'R-14': '印章管理员', 'R-15': '监督员',
    'system': '系统'
}

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
L0_L1_L5_ENTITIES = {'E-LAB', 'E-STD', 'E-TEST', 'E-CATE', 'E-PTYPE', 'E-ITEM', 'E-ANNOUNCE', 'E-FAQ', 'E-MSG'}


def _load_existing_s0(s0_path: str) -> dict | None:
    if not s0_path or not os.path.exists(s0_path):
        return None
    try:
        with open(s0_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'engine_state' in data:
            return data['engine_state']
        if 'primary_entity' in data:
            return data
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# S0.1: Relation loading
# ---------------------------------------------------------------------------

def _load_relations(cm: dict) -> tuple[list[dict], list[dict]]:
    """S0.1: Load structural_relations and transition_relations from _context.

    G0.1: Deduplicate structural_relations by {from,to} pair, keep highest confidence.
    """
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
        primary = primary
        break

    return primary


# ---------------------------------------------------------------------------
# S0.3: Phase table derivation
# ---------------------------------------------------------------------------

def _derive_phase_table(primary: str, tos: list[dict], cos: list[dict]) -> dict:
    """Derive primary_dimension and state_to_phase via BFS."""
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

    graph: dict[str, list[str]] = defaultdict(list)
    initial_states = set()
    all_states = set()
    for to in primary_tos:
        f = to.get('from')
        t = to.get('to')
        if t:
            all_states.add(t)
        if f:
            all_states.add(f)
            graph[f].append(t)
        else:
            initial_states.add(t)
            all_states.add(t)

    phase_map: dict[str, int] = {}
    visited: dict[str, int] = {}

    def bfs_assign(start: str, start_phase: int):
        queue = deque([(start, start_phase)])
        while queue:
            node, ph = queue.popleft()
            if node in visited:
                visited[node] = max(visited[node], ph)
                continue
            visited[node] = ph
            for nxt in graph.get(node, []):
                queue.append((nxt, ph + 1))

    for init in initial_states:
        bfs_assign(init, 0)

    for s in all_states:
        if s not in visited:
            visited[s] = 0

    phase_map = visited
    max_phase = max(phase_map.values()) if phase_map else 0
    phase_names = [f'P{i}' for i in range(max_phase + 1)]

    state_to_phase = {primary_dimension: phase_map}

    return {
        'primary_dimension': primary_dimension,
        'state_to_phase': state_to_phase,
        'phase_names': phase_names,
        'phase_count': max_phase + 1,
    }


def _classify_state_types(tos: list[dict], primary: str) -> dict[str, dict[str, dict[str, str]]]:
    """S0.3 step 5: Classify states as driving/side_effect."""
    state_type_map: dict[str, dict[str, dict[str, str]]] = defaultdict(lambda: defaultdict(dict))
    side_effect_keywords = {'退', '撤销', '退款', '驳回'}
    for to in tos:
        entity = to.get('entity', '')
        dim = to.get('dimension', '')
        target = to.get('to', '')
        if not target:
            continue
        desc = to.get('desc', '') or to.get('description', '')
        risk_traits = to.get('risk_traits', []) or []
        is_se = (any(kw in desc for kw in side_effect_keywords) or 'rollback' in risk_traits)
        if entity == primary:
            state_type_map[entity][dim][target] = 'driving'
        else:
            state_type_map[entity][dim][target] = 'side_effect' if is_se else 'driving'
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

        entity_tos = [t for t in tos
                      if t.get('entity') == (ve_info.get('original_entity', entity) if is_ve else entity)]

        dim_map: dict[str, dict[str, int]] = defaultdict(dict)

        for to in entity_tos:
            dim = to.get('dimension', '')
            if not dim:
                continue
            f = to.get('from')
            t = to.get('to')
            if not t:
                continue

            if f is None:
                tid = to.get('transition_id', '')
                upstreams = transition_upstream_map.get(tid, [])
                entry_phase = None
                for utid in upstreams:
                    ut = next((x for x in tos if x.get('transition_id') == utid), None)
                    if ut and ut.get('entity') == anchor:
                        anchor_dim_map = _get_anchor_phase(anchor, ut.get('dimension', ''), phase_table, dep_map)
                        if anchor_dim_map:
                            ut_to_phase = anchor_dim_map.get(ut.get('to'))
                            if ut_to_phase is not None:
                                entry_phase = ut_to_phase
                                break
                            ut_from_phase = anchor_dim_map.get(ut.get('from'))
                            if ut_from_phase is not None:
                                entry_phase = ut_from_phase
                                break

                if entry_phase is None:
                    anchor_dim_map = _get_anchor_phase(anchor, phase_table.get('primary_dimension', ''), phase_table, dep_map)
                    if anchor_dim_map:
                        entry_phase = min(anchor_dim_map.values()) if anchor_dim_map else 0
                    else:
                        entry_phase = 0

                dim_map[dim][t] = entry_phase
            else:
                if f in dim_map[dim]:
                    is_se = False
                    if entity in state_type_map and dim in state_type_map.get(entity, {}):
                        is_se = state_type_map[entity][dim].get(t) == 'side_effect'
                    if is_se:
                        dim_map[dim][t] = dim_map[dim][f]
                    else:
                        upstream_phase = dim_map[dim][f]
                        if anchor:
                            anchor_phase = _get_anchor_phase_for_entity(anchor, phase_table, dep_map)
                            upstream_phase = max(upstream_phase, anchor_phase)
                        dim_map[dim][t] = dim_map[dim][f] + (0 if is_se else 1)

        for dim, smap in list(dim_map.items()):
            for s, ph in list(smap.items()):
                if ph is None:
                    smap[s] = 0

        dep_map[entity] = dict(dim_map)

    return dep_map, ctx_rules


def _get_anchor_phase(anchor: str, dim: str, phase_table: dict, dep_map: dict) -> dict[str, int]:
    """Get phase mapping for anchor entity on a given dimension."""
    if anchor in phase_table.get('state_to_phase', {}):
        return phase_table['state_to_phase'].get(dim, {})
    if anchor in dep_map and dim in dep_map[anchor]:
        return dep_map[anchor][dim]
    return {}


def _get_anchor_phase_for_entity(anchor: str, phase_table: dict, dep_map: dict) -> int:
    """Get minimum phase for anchor entity."""
    if anchor in phase_table.get('state_to_phase', {}):
        all_phases = [p for dm in phase_table['state_to_phase'].values() for p in dm.values()]
        return min(all_phases) if all_phases else 0
    if anchor in dep_map:
        all_phases = [p for dm in dep_map[anchor].values() for p in dm.values()]
        return min(all_phases) if all_phases else 0
    return 0


# ---------------------------------------------------------------------------
# S0.4: Dependent entity detection
# ---------------------------------------------------------------------------

def _detect_dependent_entities(
    primary: str,
    structural: list[dict],
    transition: list[dict],
    tos: list[dict],
    eos: list[dict],
) -> tuple[list[str], dict, dict]:
    """S0.4: Detect dependent_entities, entity_parent, dependency_depth.

    Returns (dependent_entities, entity_parent, dependency_depth).
    """
    entity_parent: dict[str, str] = {}
    candidates: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for rel in structural:
        f = rel.get('from', '')
        t = rel.get('to', '')
        card = rel.get('cardinality', '')
        conf = rel.get('confidence', '')
        rtype = rel.get('relation_type', '')

        if conf == 'high' and card in ('1:N', '1:n'):
            candidates[t].append(('strong', f))
        elif conf == 'high' and card in ('1:1',) and rtype == 'composition':
            candidates[t].append(('medium', f))
        elif conf == 'medium' and card in ('1:N', '1:n'):
            candidates[t].append(('medium', f))

    for tr in transition:
        f = tr.get('from', '')
        t = tr.get('to', '')
        if t == primary and f != primary:
            candidates[f].append(('transition', t))

    entity_tos: dict[str, list] = defaultdict(list)
    for to in tos:
        entity_tos[to.get('entity', '')].append(to)

    entity_crud_count: dict[str, int] = defaultdict(int)
    for eo in eos:
        if eo.get('type') == 'crud_operation':
            entity_crud_count[eo.get('entity', '')] += 1

    dependent: list[str] = []
    for entity, signals in candidates.items():
        if entity == primary:
            continue

        has_tos = bool(entity_tos.get(entity))
        is_configurable_no_trans = not has_tos
        high_crud_no_signal = entity_crud_count.get(entity, 0) >= 4 and not any(s[0] == 'strong' for s in signals)

        if is_configurable_no_trans or high_crud_no_signal:
            continue

        strong_parent = None
        for sig_type, sig_source in signals:
            if sig_type == 'strong':
                strong_parent = sig_source
                break
            elif sig_type == 'transition':
                strong_parent = sig_source
                break

        if strong_parent:
            dependent.append(entity)
            entity_parent[entity] = strong_parent
        else:
            for sig_type, sig_source in signals:
                if sig_type in ('medium', 'transition'):
                    dependent.append(entity)
                    entity_parent[entity] = sig_source
                    break

    for entity in list(dependent):
        for rel in structural:
            f = rel.get('from', '')
            t = rel.get('to', '')
            if t == entity and f not in dependent and f != primary:
                if f in entity_tos and rel.get('relation_type') == 'composition':
                    dependent.append(f)
                    entity_parent[f] = entity

    for to in tos:
        e = to.get('entity', '')
        if e in dependent:
            for se in (to.get('side_effects') or []):
                te = se.get('target_entity', '')
                if te == primary and e not in entity_parent:
                    entity_parent[e] = primary

    for e in dependent:
        if e not in entity_parent:
            entity_parent[e] = primary

    dependency_depth: dict[str, int] = {primary: 0}
    queue = deque([primary])
    while queue:
        cur = queue.popleft()
        for rel in structural:
            f = rel.get('from', '')
            t = rel.get('to', '')
            if f == cur and t in dependent and t not in dependency_depth:
                dependency_depth[t] = dependency_depth[cur] + 1
                queue.append(t)

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
) -> dict[str, int]:
    """S0.5: Compute topology_levels."""
    levels: dict[str, int] = {}
    levels[primary] = 2

    for e in dependent_entities:
        d = dependency_depth.get(e, 1)
        if d == 1:
            levels[e] = 3
        else:
            levels[e] = 4

    for ve_name, ve in virtual_entities.items():
        parent = ve.get('parent_entity', '')
        if parent in levels:
            levels[ve_name] = levels[parent] + 1
        else:
            levels[ve_name] = 3

    for rel in structural:
        f = rel.get('from', '')
        t = rel.get('to', '')
        if t == primary and f not in levels:
            levels[f] = 1
        if f == primary and t not in levels and t not in dependent_entities:
            pass

    for rel in structural:
        f = rel.get('from', '')
        t = rel.get('to', '')
        if f not in levels and t in levels and levels[t] <= 2:
            if levels[t] == 2:
                levels[f] = 1
            elif levels[t] == 1:
                levels[f] = 0

    for tr in transition:
        f = tr.get('from', '')
        t = tr.get('to', '')
        if t == primary and f not in levels:
            levels[f] = 1

    for e in all_entities:
        if e not in levels:
            if e in dependency_depth:
                d = dependency_depth[e]
                levels[e] = min(d + 2, 4)
            else:
                levels[e] = 5

    for e in list(levels.keys()):
        if e in dependency_depth and e in dependent_entities:
            d = dependency_depth[e]
            override = {0: 0, 1: 3, 2: 4}.get(d, min(d + 2, 4))
            if levels[e] > 2:
                levels[e] = override

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

    for tr in transition:
        ev = tr.get('evidence_transitions', []) or []
        from_tids = [t for t in ev if t in to_by_tid and to_by_tid[t].get('entity') == tr.get('from')]
        to_tids = [t for t in ev if t in to_by_tid and to_by_tid[t].get('entity') == tr.get('to')]
        for to_tid in to_tids:
            upstream_map[to_tid].extend(from_tids)

    for co in cos:
        et = co.get('enabler_transition_id')
        dt = co.get('dependent_transition_id')
        if et and dt:
            upstream_map[dt].append(et)

    for tid in upstream_map:
        upstream_map[tid] = list(set(upstream_map[tid]))

    return dict(upstream_map)


# ---------------------------------------------------------------------------
# S0.7: Virtual entity decomposition
# ---------------------------------------------------------------------------

def _decompose_virtual_entities(
    primary: str,
    structural: list[dict],
    cos: list[dict],
    tos: list[dict],
    dep_state_phase_map: dict,
    dependent_entities: list[str],
    topology_levels: dict,
) -> dict:
    """S0.7: Virtual entity decomposition (structural multi-parent + CO causal multi-parent)."""
    virtual_entities: dict[str, dict] = {}
    entity_active_parents: dict[str, list[tuple[str, dict]]] = defaultdict(list)

    active_set = {primary} | set(dependent_entities)

    for rel in structural:
        f = rel.get('from', '')
        t = rel.get('to', '')
        rtype = rel.get('relation_type', '')
        if rtype != 'composition':
            continue
        f_level = topology_levels.get(f, 5)
        if f_level not in (2, 3, 4):
            continue
        if f not in active_set:
            continue
        entity_active_parents[t].append((f, rel))

    for entity, parents in entity_active_parents.items():
        if len(parents) < 2:
            continue
        # V2约束：parent实体必须互不相同(去重)
        unique_parent_entities = set(p[0] for p in parents)
        if len(unique_parent_entities) < 2:
            continue
        # V2约束：entity自身必须有≥2个transition
        entity_tids = [t.get('transition_id') for t in tos 
            if t.get('entity') == entity and t.get('transition_id')]
        if len(entity_tids) < 2:
            continue
        for i, (parent, rel) in enumerate(parents):
            ve_name = f"{entity}{chr(65 + i)}"
            virtual_entities[ve_name] = {
                'original_entity': entity,
                'parent_entity': parent,
                'transitions': entity_tids,
                'trigger_source': parent,
                'context': f"归属{parent}",
                'co_ids': [],
                'resolved_phase': _get_entity_min_phase(parent, dep_state_phase_map),
            }

    co_enabler_map: dict[str, list[tuple]] = defaultdict(list)
    for co in cos:
        e = co.get('enabler_entity', '')
        if e:
            co_enabler_map[e].append(co)

    for entity, co_list in co_enabler_map.items():
        if len(co_list) < 2:
            continue

        unique_contexts: dict[tuple, list] = defaultdict(list)
        for co in co_list:
            dep_entity = co.get('dependent_entity', '')
            dep_phase = _lookup_phase(dep_entity, co.get('dependent_condition', ''), dep_state_phase_map)
            key = (dep_entity, dep_phase)
            unique_contexts[key].append(co)

        if len(unique_contexts) < 2:
            continue

        entity_tids = [t.get('transition_id') for t in tos if t.get('entity') == entity and t.get('transition_id')]
        if len(entity_tids) < 2:
            continue

        existing = {ve['parent_entity']: ve_name for ve_name, ve in virtual_entities.items() if ve['original_entity'] == entity}

        for i, ((dep_entity, dep_phase), cos_group) in enumerate(sorted(unique_contexts.items())):
            if dep_entity in existing:
                ve_name = existing[dep_entity]
                virtual_entities[ve_name]['co_ids'].extend([co.get('id') for co in cos_group])
                continue

            ve_name = f"{entity}{chr(65 + len(virtual_entities))}"
            virtual_entities[ve_name] = {
                'original_entity': entity,
                'parent_entity': dep_entity,
                'transitions': entity_tids,
                'trigger_source': dep_entity,
                'context': '/'.join([co.get('trigger') or (co.get('desc', '') or '')[:20] for co in cos_group]),
                'co_ids': [co.get('id') for co in cos_group],
                'resolved_phase': dep_phase,
            }

    to_remove = []
    for ve_name, ve in virtual_entities.items():
        if ve['parent_entity'] == ve['original_entity']:
            to_remove.append(ve_name)
    for v in to_remove:
        del virtual_entities[v]

    return virtual_entities


def _get_entity_min_phase(entity: str, dep_state_phase_map: dict) -> int:
    if entity in dep_state_phase_map:
        phases = [p for dm in dep_state_phase_map[entity].values() for p in dm.values()]
        return min(phases) if phases else 0
    return 0


def _lookup_phase(entity: str, condition: str, dep_state_phase_map: dict) -> int:
    if entity in dep_state_phase_map:
        for dim, smap in dep_state_phase_map[entity].items():
            if condition in smap:
                return smap[condition]
        phases = [p for dm in dep_state_phase_map[entity].values() for p in dm.values()]
        return min(phases) if phases else 0
    return 0


# ---------------------------------------------------------------------------
# Main S0 node
# ---------------------------------------------------------------------------

def s0_topology_node(state: AgentState) -> dict:
    """S0 Topology Discovery node — deterministic implementation.

    Strategy:
    1. Deterministic computation of all S0.1–S0.7 fields
    2. Fallback: try loading existing S0 file or LLM
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
        warnings.append(f"S0 deterministic computation failed: {e}, trying fallback")
        s0_path = str(Path(cm_path).parent / "p3_s2_s3_s4_result.json")
        engine_state = _load_existing_s0(s0_path)

        if engine_state is None:
            try:
                from tools.llm_client import LLMClient
                from prompts.s0_prompt import S0_SYSTEM_PROMPT, S0_USER_PROMPT_TEMPLATE
                import asyncio
                client = LLMClient()
                user_msg = S0_USER_PROMPT_TEMPLATE.format(
                    coverage_model_json=json.dumps(coverage_model, ensure_ascii=False, indent=2)
                )
                engine_state = asyncio.run(client.chat_json(S0_SYSTEM_PROMPT, user_msg))
            except Exception as e2:
                errors.append(f"S0 fallback also failed: {e2}")
                return {"errors": errors, "current_stage": "s0_failed"}

            result = engine_state

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
    """Full deterministic S0 computation."""
    tos = cm.get('transition_obligations', [])
    eos = cm.get('entity_obligations', [])
    cos = cm.get('cross_entity_obligations', [])
    ros = cm.get('constraint_obligations', [])

    structural, transition = _load_relations(cm)

    primary = _identify_primary_entity(structural, transition, tos)
    if not primary:
        raise ValueError("S0.2: Could not identify primary_entity")
    warnings.append(f"S0.2: primary_entity={primary}")

    phase_table = _derive_phase_table(primary, tos, cos)
    warnings.append(f"S0.3: primary_dimension={phase_table['primary_dimension']}, phase_count={phase_table['phase_count']}")

    dependent_entities, entity_parent, dependency_depth = _detect_dependent_entities(
        primary, structural, transition, tos, eos
    )
    warnings.append(f"S0.4: {len(dependent_entities)} dependent entities: {dependent_entities}")

    all_entities = set()
    for to in tos:
        all_entities.add(to.get('entity', ''))
    for eo in eos:
        all_entities.add(eo.get('entity', ''))
    for rel in structural:
        all_entities.add(rel.get('from', ''))
        all_entities.add(rel.get('to', ''))

    topology_levels = _compute_topology_levels(
        primary, dependent_entities, entity_parent, dependency_depth,
        structural, transition, all_entities, {}
    )
    warnings.append(f"S0.5: topology_levels computed for {len(topology_levels)} entities")

    transition_upstream_map = _rebuild_upstream_map(tos, transition, cos)
    warnings.append(f"S0.6: upstream_map with {len(transition_upstream_map)} entries")

    state_type_map = _classify_state_types(tos, primary)

    virtual_entities = _decompose_virtual_entities(
        primary, structural, cos, tos, {}, dependent_entities, topology_levels
    )

    dep_state_phase_map, contextual_phase_rules = _derive_dep_state_phase_map(
        primary, phase_table, tos, dependent_entities, entity_parent,
        state_type_map, transition_upstream_map, virtual_entities
    )

    if virtual_entities:
        topology_levels = _compute_topology_levels(
            primary, dependent_entities, entity_parent, dependency_depth,
            structural, transition, all_entities, virtual_entities
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
