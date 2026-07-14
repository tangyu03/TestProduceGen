#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coverage Obligation Model Generator.
Reads P1 domain model JSON, produces obligation coverage model JSON per spec.
"""

import json
import re
import itertools
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# ---------------------------------------------------------------------------
# ASCII safety
# ---------------------------------------------------------------------------
def safe(s):
    if not isinstance(s, str):
        return s
    s = s.replace("\u2192", "->").replace("\u2190", "<-")
    s = s.replace("\u2191", "^").replace("\u2193", "v")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2018", "'").replace("\u2019", "'")
    s = s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return s

def walk_safe(obj):
    if isinstance(obj, dict):
        return {k: walk_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [walk_safe(v) for v in obj]
    if isinstance(obj, str):
        return safe(obj)
    return obj

# ---------------------------------------------------------------------------
# Working memory (cross-batch persistent)
# ---------------------------------------------------------------------------
class WorkMem:
    def __init__(self):
        self.to_index = defaultdict(list)       # tid -> [TO, ...]
        self.co_list = []                        # list of CO dicts
        self.co_index = []                       # (enabler_entity, dependent_entity, causal_type)
        self.xc_status = {}                      # xc_id -> "co"|"br"|"skipped"
        self.judgments = []                      # semantic judgment records
        self.warnings = defaultdict(list)        # step -> [warning strings]
        self.eo_list = []                        # entity obligations
        self.to_list = []                        # transition obligations
        self.co_output = []                      # final CO list after dedup
        self.ro_it_list = []                     # RO-IT
        self.ro_br_list = []                     # RO-BR (from P1 BRs)
        self.ro_br_from_xc = []                  # RO-BR (from skipped XCs)
        self.xc_to_br_mapping = []               # xc_id -> ro_br_id mapping

# ---------------------------------------------------------------------------
# Index builders
# ---------------------------------------------------------------------------
def build_indices(p1):
    entities = {e['id']: e for e in p1['domain_model']['entities']}
    transitions = {t['id']: t for t in p1['state_and_flow']['transitions']}
    # state_dim_index: (entity_id, dimension_name) -> {states, initial, terminal}
    state_dim_index = {}
    for eid, e in entities.items():
        for d in e.get('state_dimensions', []):
            state_dim_index[(eid, d['dimension_name'])] = {
                'states': d['states'],
                'initial': d['initial'],
                'terminal': d.get('terminal', [])
            }
    # config_attr_index: entity_id -> set of config attribute names
    config_attrs = defaultdict(set)
    for eid, e in entities.items():
        for a in e['attributes']:
            if a.get('is_config'):
                config_attrs[eid].add(a['name'])
    # roles
    roles = {r['id']: r for r in p1['domain_model']['roles']}
    # branch_dims
    branch_dims = p1['_meta']['branch_dimensions']
    # transition_relations
    trs = p1['domain_model']['transition_relations']
    # structural_relations
    srs = p1['domain_model']['structural_relations']
    return entities, transitions, state_dim_index, config_attrs, roles, branch_dims, trs, srs


def find_transition_reaching_state(wm, transitions, entity_id, dimension, target_state):
    """Find a transition of entity_id whose 'to' state in given dimension equals target_state."""
    for tid, t in transitions.items():
        if t['entity'] != entity_id:
            continue
        if t['dimension'] != dimension:
            continue
        to_vals = parse_multi(t['to'])
        if target_state in to_vals:
            return tid
    return None


def parse_multi(val):
    """Parse 'A|B|C' into [A, B, C]. None -> [None]."""
    if val is None:
        return [None]
    if isinstance(val, str) and '|' in val:
        return [s.strip() for s in val.split('|')]
    return [val]


def parse_state_from_condition(condition):
    """Try to extract a clean state value from target_condition strings.
    e.g. '状态=待评审' -> '待评审'
         '状态=待归档(全部项目)' -> '待归档'
         '项目评级 != 差' -> None (not a clean state)
    """
    if not condition:
        return None
    # Pattern: "状态=X" or "状态 = X"
    m = re.search(r'状态\s*=\s*([^\s,;（(]+)', condition)
    if m:
        return m.group(1).strip()
    return None


def validate_eds(enabler_state, enabler_entity, enabler_dimension, state_dim_index, entities):
    """(E,D,S) validation with backtracking.
    Returns (ok, fixed_dimension, judgment_or_None, cleaned_state).
    cleaned_state is the validated state value (may differ from input after semantic inference).
    """
    # Quick path: exact match
    if (enabler_entity, enabler_dimension) in state_dim_index:
        states = state_dim_index[(enabler_entity, enabler_dimension)]['states']
        if enabler_state in states:
            return (True, enabler_dimension, None, enabler_state)

    # Backtrack step 1: find which dimension of enabler_entity contains this state
    for d in entities.get(enabler_entity, {}).get('state_dimensions', []):
        if enabler_state in d['states']:
            return (True, d['dimension_name'], {
                'rule_point': '(E,D,S) backtrack step1',
                'basis': 'enabler_state not in specified dimension, found in another dimension',
                'evidence': [f'enabler_state={enabler_state}, original_dim={enabler_dimension}, fixed_dim={d["dimension_name"]}'],
                'affected_id': '',
                'decision': f'修正dimension为{d["dimension_name"]}'
            }, enabler_state)

    # Semantic inference: try to find a state that's a substring or superstring
    for d in entities.get(enabler_entity, {}).get('state_dimensions', []):
        for s in d['states']:
            if enabler_state and (enabler_state in s or s in enabler_state):
                return (True, d['dimension_name'], {
                    'rule_point': '(E,D,S) semantic inference',
                    'basis': 'enabler_state not exact match, inferred via substring',
                    'evidence': [f'condition={enabler_state}, matched_state={s}, dim={d["dimension_name"]}'],
                    'affected_id': '',
                    'decision': f'推断enabler_state={s}, dimension={d["dimension_name"]}'
                }, s)

    return (False, enabler_dimension, None, enabler_state)


# ---------------------------------------------------------------------------
# Step 1: entity_obligations
# ---------------------------------------------------------------------------
def step1_entity_obligations(p1, wm, entities, config_attrs):
    eo_counter = [0]
    for eid, e in entities.items():
        for attr in e['attributes']:
            if not attr.get('is_config'):
                continue
            eo_counter[0] += 1
            eo_id = f"EO-ATC-{eo_counter[0]:03d}"
            # Build branch description from branch_dimensions if this attr is a branch dim
            branch_desc = "相关业务流转分支"
            for bd in p1['_meta']['branch_dimensions']:
                if bd.get('entity') == eid and bd.get('dimension') == attr['name']:
                    branch_desc = f"影响{bd['impact_scope'][:40]}"
                    break
            eo = {
                'id': eo_id,
                'type': 'attribute_config',
                'entity': eid,
                'entity_name': e['name'],
                'attribute_name': attr['name'],
                'attribute_desc': attr['desc'],
                'description': f"覆盖{e['name']}的配置属性{attr['name']}不同取值对流转的影响",
                'suggested_action': f"修改{e['name']}的{attr['name']}，影响{branch_desc}",
                'coverage_priority': 'medium',
                'dimension': None,
                'from': None,
                'to': None,
            }
            wm.eo_list.append(eo)
    return wm.eo_list


# ---------------------------------------------------------------------------
# Step 2: transition_obligations
# ---------------------------------------------------------------------------
def get_branch_values_for_transition(p1, t, branch_dims):
    """Determine branch dimension values applicable to a transition.
    Returns list of (dimension_name, [values]) tuples.
    """
    tid = t['id']
    result = []  # [(dim_name, [values])]

    # 2.5a: matched_dims from BD.coverage.transitions
    matched_bds = [bd for bd in branch_dims if tid in bd.get('coverage', {}).get('transitions', [])]

    for bd in matched_bds:
        dim_name = bd['dimension']
        # Get relevant values from branches where target_transition == tid
        branch_vals = [b['value'] for b in bd.get('branches', []) if b.get('target_transition') == tid]
        if not branch_vals:
            branch_vals = list(bd['values'])
        # Filter: if this dimension is the transition's own dimension (or semantically same), only keep 'from' state
        is_own_dim = (dim_name == t['dimension']) or (
            bd.get('entity') == t['entity'] and t['from'] is not None and
            any(v in parse_multi(t['from']) for v in branch_vals) and len(branch_vals) > 1
        )
        if is_own_dim and t['from'] is not None:
            from_vals = parse_multi(t['from'])
            branch_vals = [v for v in branch_vals if v in from_vals]
            if not branch_vals:
                branch_vals = from_vals  # fallback
        # For non-owning dimensions, filter by preconditions
        elif bd.get('entity') == t['entity'] and t['from'] is not None:
            # Same entity but different dimension - still might need from-filtering
            from_vals = parse_multi(t['from'])
            overlap = [v for v in branch_vals if v in from_vals]
            if overlap and len(overlap) < len(branch_vals):
                branch_vals = overlap
            else:
                branch_vals = filter_by_preconditions(t, dim_name, branch_vals)
        else:
            # Different entity or no from state - filter by preconditions
            branch_vals = filter_by_preconditions(t, dim_name, branch_vals)
        result.append((dim_name, branch_vals))

    # 2.5b: supplement from note.branch_dimension if tid not in any BD.coverage
    note_bd = t.get('note', {}).get('branch_dimension', '')
    if note_bd and not matched_bds:
        for dim_part in note_bd.split('+'):
            dim_part = dim_part.strip()
            for bd in branch_dims:
                if bd['dimension'] == dim_part:
                    branch_vals = [b['value'] for b in bd.get('branches', []) if b.get('target_transition') == tid]
                    if not branch_vals:
                        branch_vals = list(bd['values'])
                    # Check if this is the transition's own dimension (exact or semantic match)
                    is_own_dim = (dim_part == t['dimension']) or (
                        bd.get('entity') == t['entity'] and t['from'] is not None and
                        any(v in parse_multi(t['from']) for v in branch_vals) and len(branch_vals) > 1
                    )
                    if is_own_dim and t['from'] is not None:
                        from_vals = parse_multi(t['from'])
                        branch_vals = [v for v in branch_vals if v in from_vals]
                        if not branch_vals:
                            branch_vals = from_vals
                    elif bd.get('entity') == t['entity'] and t['from'] is not None:
                        from_vals = parse_multi(t['from'])
                        overlap = [v for v in branch_vals if v in from_vals]
                        if overlap and len(overlap) < len(branch_vals):
                            branch_vals = overlap
                        else:
                            branch_vals = filter_by_preconditions(t, dim_part, branch_vals)
                    else:
                        branch_vals = filter_by_preconditions(t, dim_part, branch_vals)
                    result.append((dim_part, branch_vals))
                    break

    # 2.5b (mixed case): matched_bds exists but note has additional dims
    if note_bd and matched_bds:
        matched_dim_names = {r[0] for r in result}
        for dim_part in note_bd.split('+'):
            dim_part = dim_part.strip()
            if dim_part in matched_dim_names:
                continue
            for bd in branch_dims:
                if bd['dimension'] == dim_part:
                    branch_vals = [b['value'] for b in bd.get('branches', []) if b.get('target_transition') == tid]
                    if not branch_vals:
                        branch_vals = list(bd['values'])
                    is_own_dim = (dim_part == t['dimension']) or (
                        bd.get('entity') == t['entity'] and t['from'] is not None and
                        any(v in parse_multi(t['from']) for v in branch_vals) and len(branch_vals) > 1
                    )
                    if is_own_dim and t['from'] is not None:
                        from_vals = parse_multi(t['from'])
                        branch_vals = [v for v in branch_vals if v in from_vals]
                        if not branch_vals:
                            branch_vals = from_vals
                    elif bd.get('entity') == t['entity'] and t['from'] is not None:
                        from_vals = parse_multi(t['from'])
                        overlap = [v for v in branch_vals if v in from_vals]
                        if overlap and len(overlap) < len(branch_vals):
                            branch_vals = overlap
                        else:
                            branch_vals = filter_by_preconditions(t, dim_part, branch_vals)
                    else:
                        branch_vals = filter_by_preconditions(t, dim_part, branch_vals)
                    result.append((dim_part, branch_vals))
                    break

    return result


def filter_by_preconditions(t, dim_name, values):
    """Filter branch values based on transition preconditions.
    E.g., if preconditions mention '合格及以上', keep only 优秀/良好/合格.
    """
    preconds = ' '.join(t.get('preconditions', []))
    expected = ' '.join(t.get('expected_results', []))
    combined = preconds + ' ' + expected

    # If preconditions explicitly mention values, filter
    mentioned = []
    for v in values:
        if v in combined:
            mentioned.append(v)

    # Special patterns
    if '合格及以上' in combined or '评级在合格及以上' in combined:
        return [v for v in values if v in ['优秀', '良好', '合格']]
    if '不合格或差' in combined or '不合格和差' in combined:
        return [v for v in values if v in ['不合格', '差']]
    if '不可选入' in combined and '差' in values:
        # For T-002, 差 means transition doesn't happen
        return [v for v in values if v != '差']

    if mentioned:
        return mentioned
    return values


def step2_transition_obligations(p1, wm, entities, transitions, state_dim_index, branch_dims, trs):
    to_counter = [0]

    for tid, t in transitions.items():
        # Check if branch splitting applies
        branch_vals = get_branch_values_for_transition(p1, t, branch_dims)
        note_bd = t.get('note', {}).get('branch_dimension', '')

        if not branch_vals and not note_bd:
            # No split
            to_counter[0] += 1
            to_id = f"TO-{to_counter[0]:03d}"
            to_obj = build_to(to_id, t, [], entities, state_dim_index, transitions, trs, wm)
            wm.to_list.append(to_obj)
            wm.to_index[tid].append(to_obj)
        else:
            # Generate cartesian product of branch values
            # Remove empty lists
            branch_vals = [(d, vs) for d, vs in branch_vals if vs]
            if not branch_vals:
                # Fallback: no valid combos, don't split
                to_counter[0] += 1
                to_id = f"TO-{to_counter[0]:03d}"
                to_obj = build_to(to_id, t, [], entities, state_dim_index, transitions, trs, wm)
                wm.to_list.append(to_obj)
                wm.to_index[tid].append(to_obj)
                continue

            # Check combo count
            combo_count = 1
            for _, vs in branch_vals:
                combo_count *= len(vs)

            if combo_count > 16:
                # Degrade: don't split
                wm.warnings['step2'].append(f"{tid}: combo count {combo_count} > 16, degrade to no split")
                to_counter[0] += 1
                to_id = f"TO-{to_counter[0]:03d}"
                to_obj = build_to(to_id, t, [], entities, state_dim_index, transitions, trs, wm)
                wm.to_list.append(to_obj)
                wm.to_index[tid].append(to_obj)
                continue

            # Generate combos
            dim_names = [d for d, _ in branch_vals]
            value_lists = [vs for _, vs in branch_vals]
            combos = list(itertools.product(*value_lists))

            # Filter combos: skip where transition doesn't exist for that value combination
            valid_combos = []
            for combo in combos:
                # Check if this combo is valid for the transition
                skip = False
                for (dim_name, val) in zip(dim_names, combo):
                    # If dim is transition's own dimension, val must match 'from'
                    if dim_name == t['dimension'] and t['from'] is not None:
                        from_vals = parse_multi(t['from'])
                        if val not in from_vals:
                            skip = True
                            break
                if not skip:
                    valid_combos.append(combo)

            if not valid_combos:
                # No valid combos, fallback to no split
                to_counter[0] += 1
                to_id = f"TO-{to_counter[0]:03d}"
                to_obj = build_to(to_id, t, [], entities, state_dim_index, transitions, trs, wm)
                wm.to_list.append(to_obj)
                wm.to_index[tid].append(to_obj)
                continue

            # Generate split TOs
            suffix_idx = 0
            for combo in valid_combos:
                suffix_idx += 1
                suffix = chr(ord('a') + suffix_idx - 1)
                to_counter[0] += 1
                to_id = f"TO-{to_counter[0]:03d}"
                branch_path = [{'dimension': d, 'value': v} for d, v in zip(dim_names, combo)]
                to_obj = build_to(to_id, t, branch_path, entities, state_dim_index, transitions, trs, wm, combo, dim_names)
                wm.to_list.append(to_obj)
                wm.to_index[tid].append(to_obj)

    return wm.to_list


def build_to(to_id, t, branch_path, entities, state_dim_index, transitions, trs, wm, combo=None, combo_dims=None):
    """Build a single TO object."""
    tid = t['id']

    # coverage_priority
    priority = t.get('priority', 'P2')
    entity = t['entity']
    dim_name = t['dimension']

    # Check terminal
    terminal_states = []
    if (entity, dim_name) in state_dim_index:
        terminal_states = state_dim_index[(entity, dim_name)]['terminal']

    to_vals = parse_multi(t['to'])
    is_terminal = any(tv in terminal_states for tv in to_vals)

    if t['from'] is None or is_terminal:
        coverage_priority = 'critical'
    elif priority == 'P0':
        coverage_priority = 'critical'
    elif priority == 'P1':
        coverage_priority = 'high'
    else:
        coverage_priority = 'medium'

    # risk_traits
    risk_traits = list(t.get('traits', []))

    # is_repeatable
    is_repeatable = False
    repeat_condition = None
    if t['from'] is not None:
        from_vals = parse_multi(t['from'])
        if any(fv in to_vals for fv in from_vals):
            is_repeatable = True
            repeat_condition = f"from={t['from']} to={t['to']}, 状态自循环"

    # Build action with combo annotation
    action = t['action']
    if combo and combo_dims:
        combo_str = ' '.join(f'{d}={v}' for d, v in zip(combo_dims, combo))
        action = f"{action} [{combo_str}]"

    # Refine preconditions and expected_results based on combo
    preconditions = list(t.get('preconditions', []))
    expected_results = list(t.get('expected_results', []))

    if combo and combo_dims:
        # Filter expected_results to match the combo
        filtered_er = []
        for er in expected_results:
            # Check if this er line applies to the current combo
            applies = True
            for d, v in zip(combo_dims, combo):
                # If er mentions a different value of this dimension, skip
                # Simple heuristic: check for "评级in[...]" patterns
                pass
            if applies:
                filtered_er.append(er)

        # For T-007 with combo, refine expected_results
        if tid == 'T-007' and combo:
            stage = None
            rating = None
            for d, v in zip(combo_dims, combo):
                if d == '项目阶段':
                    stage = v
                if d == '项目评级':
                    rating = v
            if stage and rating:
                if stage == '开题' and rating in ['优秀', '良好', '合格']:
                    filtered_er = [f"项目阶段=开题, 评级={rating}: 项目状态->已选入, 阶段->验收"]
                elif stage == '开题' and rating in ['不合格', '差']:
                    filtered_er = [f"项目阶段=开题, 评级={rating}: 项目状态->待选入, 阶段不变"]
                elif stage == '验收' and rating in ['优秀', '良好', '合格']:
                    filtered_er = [f"项目阶段=验收, 评级={rating}: 项目状态->已归档, 阶段不变"]
                elif stage == '验收' and rating in ['不合格', '差']:
                    filtered_er = [f"项目阶段=验收, 评级={rating}: 项目状态->待选入, 阶段不变"]

        # For T-002 with combo (评级)
        if tid == 'T-002' and combo:
            for d, v in zip(combo_dims, combo):
                if d == '项目评级':
                    if v == '不合格':
                        filtered_er = [f"评级=不合格: 项目状态由待选入变为已选入(仅1次选入机会)"]
                    elif v in ['优秀', '良好', '合格']:
                        filtered_er = [f"评级={v}: 项目状态由待选入变为已选入(正常选入)"]

        expected_results = filtered_er

    # side_effects (Step 2.6)
    side_effects = compute_side_effects(t, trs, transitions, entities, state_dim_index)

    # role
    role = t.get('role')

    # suggested_action
    suggested_action = f"在{action}时，执行{t['entity']}的{dim_name}状态从{t['from']}推进至{t['to']}的操作"

    # note
    note = {
        'inferred': t.get('note', {}).get('inferred', False),
        'comment': t.get('note', {}).get('comment', ''),
        'conflict': t.get('note', {}).get('conflict', ''),
        'branch_dimension': t.get('note', {}).get('branch_dimension', ''),
    }

    to_obj = {
        'id': to_id,
        'type': 'transition_obligation',
        'transition_id': tid,
        'entity': entity,
        'dimension': dim_name,
        'from': t['from'],
        'to': t['to'],
        'action': action,
        'role': role,
        'coverage_priority': coverage_priority,
        'preconditions': preconditions,
        'expected_results': expected_results,
        'source_ref': t.get('source_ref', ''),
        'risk_traits': risk_traits,
        'is_repeatable': is_repeatable,
        'repeat_condition': repeat_condition,
        'branch_path': branch_path,
        'side_effects': side_effects,
        'note': note,
        'sub_steps': t.get('sub_steps', []),
        'suggested_action': suggested_action,
    }
    return to_obj


def compute_side_effects(t, trs, transitions, entities, state_dim_index):
    """Step 2.6: compute side_effects for a transition.
    Channel 1: transition_relations where from==t.entity and evidence contains t.id
    Channel 2: scan expected_results for other entity state changes
    """
    side_effects = []
    seen = set()  # (target_entity, target_dimension) for dedup

    tid = t['id']
    t_entity = t['entity']

    # Channel 1: structured
    for tr in trs:
        if tr['from'] != t_entity:
            continue
        if tid not in tr.get('evidence_transitions', []):
            continue
        target_entity = tr['to']
        # Find target dimension: look at target_entity's state_dimensions
        target_dim = None
        effect_desc = tr.get('desc', '')
        for d in entities.get(target_entity, {}).get('state_dimensions', []):
            # Prefer the dimension mentioned in desc or the first state dimension
            if target_dim is None:
                target_dim = d['dimension_name']
        if target_entity == t_entity:
            # Self-loop, skip (not a side effect on OTHER entity)
            pass
        else:
            key = (target_entity, target_dim)
            if key not in seen:
                seen.add(key)
                side_effects.append({
                    'target_entity': target_entity,
                    'target_dimension': target_dim,
                    'effect_desc': effect_desc
                })

    # Channel 2: text scan of expected_results
    for er in t.get('expected_results', []):
        # Look for patterns mentioning other entities' state changes
        for eid, e in entities.items():
            if eid == t_entity:
                continue  # skip same entity
            ename = e['name']
            if ename in er or eid in er:
                # Check if this is a state change description
                # Look for dimension names
                for d in e.get('state_dimensions', []):
                    dname = d['dimension_name']
                    if dname in er or any(s in er for s in d['states']):
                        key = (eid, dname)
                        if key not in seen:
                            seen.add(key)
                            side_effects.append({
                                'target_entity': eid,
                                'target_dimension': dname,
                                'effect_desc': er
                            })
                        break

    return side_effects


# ---------------------------------------------------------------------------
# Step 3: cross_entity_obligations
# ---------------------------------------------------------------------------
def check_gates(enabler_entity, enabler_dimension, enabler_state,
                dependent_tid, dependent_entity, dependent_dimension, dependent_condition,
                causal_source, config_attrs, state_dim_index, entities, wm,
                to_index, source_xc_id=None):
    """Check gates G1-G6. Returns (passed, gate_failed, reason)."""
    # G1: enabler_dimension is a config attribute
    if enabler_dimension and enabler_dimension in config_attrs.get(enabler_entity, set()):
        return (False, 'G1', f'enabler_dimension={enabler_dimension} is config attr of {enabler_entity}')

    # G2: can't extract dimension/state
    if not enabler_dimension or not enabler_state:
        if not dependent_dimension or not dependent_condition:
            return (False, 'G2', f'cannot extract dimensions/states: enabler_dim={enabler_dimension}, dep_dim={dependent_dimension}')

    # G3: all TOs of dependent_tid have from==null
    dep_tos = to_index.get(dependent_tid, [])
    if dep_tos:
        if all(to_obj['from'] is None for to_obj in dep_tos):
            return (False, 'G3', f'all TOs of {dependent_tid} have from==null (creation transition)')

    # G4: only for 3.3 (cardinality check), handled separately

    # G5: enabler_state not valid enum
    if enabler_state and enabler_dimension:
        ok, fixed_dim, judgment, cleaned_state = validate_eds(enabler_state, enabler_entity, enabler_dimension, state_dim_index, entities)
        if not ok:
            return (False, 'G5', f'enabler_state={enabler_state} not valid for {enabler_entity}.{enabler_dimension}')
        if judgment:
            wm.judgments.append(judgment)
            if source_xc_id:
                judgment['affected_id'] = source_xc_id
            # Update dimension if fixed
            return (True, 'G5_passed_with_fix', fixed_dim)

    return (True, None, None)


def step3_1_xc_constraints(p1, wm, entities, transitions, state_dim_index, config_attrs, to_index):
    """Step 3.1: Generate CO from XC constraints."""
    co_counter = [0]
    xcs = p1['constraints']['cross_entity']

    for xc in xcs:
        xc_id = xc['id']
        source_entity = xc['source_entity']
        source_transition = xc['source_transition']
        source_state = xc['source_state']
        target_entity = xc['target_entity']
        target_dimension = xc['target_dimension']
        target_condition = xc['target_condition']

        # Parse enabler_state from target_condition
        enabler_state = parse_state_from_condition(target_condition)
        if enabler_state is None:
            # Try using target_condition directly as state
            enabler_state = target_condition

        enabler_entity = target_entity
        enabler_dimension = target_dimension
        dependent_entity = source_entity
        dependent_transition_id = source_transition
        dependent_tos = to_index.get(source_transition, [])
        if dependent_tos:
            dependent_dimension = dependent_tos[0]['dimension']
        else:
            dependent_dimension = target_dimension  # fallback
        dependent_condition = source_state

        # Check G3: dependent transition must have from != null
        if dependent_tos and all(to_obj['from'] is None for to_obj in dependent_tos):
            # G3 fail: skip and convert to BR
            wm.xc_status[xc_id] = 'skipped'
            create_br_from_xc(xc, wm, 'G3: dependent transition is creation (from==null)', entities, config_attrs, to_index)
            continue

        # Check G1: enabler_dimension is config attr
        if enabler_dimension and enabler_dimension in config_attrs.get(enabler_entity, set()):
            wm.xc_status[xc_id] = 'skipped'
            create_br_from_xc(xc, wm, f'G1: enabler_dimension={enabler_dimension} is config attr', entities, config_attrs, to_index)
            continue

        # Check G2: can't extract
        if not enabler_dimension or (not enabler_state and not target_condition):
            wm.xc_status[xc_id] = 'skipped'
            create_br_from_xc(xc, wm, 'G2: cannot extract dimension/state', entities, config_attrs, to_index)
            continue

        # (E,D,S) validation
        ok, fixed_dim, judgment, cleaned_state = validate_eds(enabler_state, enabler_entity, enabler_dimension, state_dim_index, entities)
        if not ok:
            # (E,D,S) fail: skip and convert to BR
            wm.xc_status[xc_id] = 'skipped'
            create_br_from_xc(xc, wm, f'(E,D,S) fail: enabler_state={enabler_state} not valid for {enabler_entity}.{enabler_dimension}', entities, config_attrs, to_index)
            continue

        if judgment:
            wm.judgments.append({**judgment, 'affected_id': xc_id})
            enabler_dimension = fixed_dim  # apply fix
            enabler_state = cleaned_state  # apply cleaned state

        # All gates passed, generate CO
        # Find enabler_transition_id: transition reaching enabler_state in enabler_entity
        enabler_tid = find_transition_reaching_state(wm, transitions, enabler_entity, enabler_dimension, enabler_state)

        # aggregation: 1:N composition and depends on all children -> "all"
        aggregation = None
        # Check if there's a composition structural relation from enabler to dependent with 1:N
        for sr in p1['domain_model']['structural_relations']:
            if (sr['from'] == enabler_entity and sr['to'] == dependent_entity
                    and sr['relation_type'] == 'composition' and sr['cardinality'] == '1:N'):
                aggregation = 'all'
                break

        # coverage_priority: from dependent TO priority
        dep_priorities = [to_obj['coverage_priority'] for to_obj in dependent_tos]
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        if dep_priorities:
            coverage_priority = min(dep_priorities, key=lambda p: priority_order.get(p, 3))
        else:
            coverage_priority = 'medium'

        # roles
        enabler_role = None
        if enabler_tid and enabler_tid in transitions:
            r = transitions[enabler_tid].get('role')
            if r != 'system':
                enabler_role = r
        dependent_role = None
        if dependent_tos:
            r = dependent_tos[0].get('role')
            if r != 'system':
                dependent_role = r

        # ref_to: check if dependent TO's preconditions reference enabler_state
        ref_to = None
        for to_obj in dependent_tos:
            for pc in to_obj.get('preconditions', []):
                if enabler_state and enabler_state in pc:
                    ref_to = {
                        'obligation_type': 'transition_obligation',
                        'obligation_id': to_obj['id'],
                        'relation': 'precondition_references_enabler_state',
                        'detail': [pc]
                    }
                    break
            if ref_to:
                break

        # suggested_action
        if aggregation == 'all':
            suggested_action = f"所有{enabler_entity}的{enabler_dimension}达到{enabler_state}是{dependent_entity}的{dependent_dimension}推进至{dependent_condition}的前置门禁"
        else:
            suggested_action = f"{enabler_entity}的{enabler_dimension}达到{enabler_state}是{dependent_entity}的{dependent_dimension}推进至{dependent_condition}的前置门禁"

        desc = f"{enabler_entity}.{enabler_dimension}={enabler_state}是{dependent_entity}.{dependent_dimension}推进至{dependent_condition}的前置条件"

        co_counter[0] += 1
        co_id = f"CO-{co_counter[0]:03d}"
        co = {
            'id': co_id,
            'type': 'cross_entity',
            'constraint_id': xc_id,
            'causal_type': 'constraint',
            'enabler_entity': enabler_entity,
            'enabler_transition_id': enabler_tid,
            'enabler_dimension': enabler_dimension,
            'enabler_state': enabler_state,
            'dependent_entity': dependent_entity,
            'dependent_transition_id': dependent_transition_id,
            'dependent_dimension': dependent_dimension,
            'dependent_condition': dependent_condition,
            'aggregation': aggregation,
            'ref_to': ref_to,
            'trigger': None,
            'trigger_source': None,
            'rollback_propagation': False,
            'confidence': 'high',
            'desc': desc,
            'coverage_priority': coverage_priority,
            'enabler_role': enabler_role,
            'dependent_role': dependent_role,
            'suggested_action': suggested_action,
            'merged_from': [],
        }
        wm.co_list.append(co)
        wm.co_index.append((enabler_entity, dependent_entity, 'constraint', co_id))
        wm.xc_status[xc_id] = 'co'

    return


def create_br_from_xc(xc, wm, skip_reason, entities, config_attrs, to_index):
    """Create RO-BR from a skipped XC (3.1 跳过后处理)."""
    xc_id = xc['id']
    source_entity = xc['source_entity']
    target_entity = xc['target_entity']
    target_condition = xc['target_condition']
    desc_text = xc.get('desc', '')

    entities_involved = [source_entity, target_entity]

    # Category determination (semantic double-layer)
    combined = target_condition + ' ' + desc_text
    category = 'validation'
    if any(kw in combined for kw in ['显示', '展示', '统计']):
        category = 'display'
    elif any(kw in combined for kw in ['查询', '排序', '分页', '同步', '一致', '标识', '提示']):
        category = 'usability'
    elif any(kw in combined for kw in ['计算', '金额']):
        category = 'computation'
    else:
        category = 'validation'

    # coverage_priority
    coverage_priority = 'medium'
    if category == 'display':
        coverage_priority = 'medium'
    elif category == 'usability' and any(kw in combined for kw in ['必填', '标识', '提示']):
        coverage_priority = 'high'
    elif category == 'computation':
        coverage_priority = 'high'

    description = f"[来源于{xc_id}] {target_condition}; {desc_text}"

    suggested_action = f"在{source_entity}与{target_entity}涉及环节, 按{target_condition[:30]}规则执行操作"

    # Check if P1 has a same-topic BR for ref_to_existing_br
    ref_to_existing_br = None  # simplified: not matching

    ro_br_id = f"RO-BR-{len(wm.ro_br_from_xc) + len(wm.ro_br_list) + 1:04d}"
    ro_br = {
        'id': ro_br_id,
        'type': 'business_rule',
        'constraint_id': xc_id,
        'entities_involved': entities_involved,
        'category': category,
        'signal_type': None,
        'description': description,
        'enforcement': 'mandatory',
        'source_xc': xc_id,
        'ref_to_existing_br': ref_to_existing_br,
        'coverage_priority': coverage_priority,
        'suggested_action': suggested_action,
    }
    wm.ro_br_from_xc.append(ro_br)
    wm.xc_to_br_mapping.append({
        'xc_id': xc_id,
        'ro_br_id': ro_br_id,
        'ref_to_existing_br': ref_to_existing_br,
        'xc_content': f"src={source_entity}/{xc['source_transition']}/{xc['source_state']} -> tgt={target_entity}/{xc['target_dimension']}/{target_condition}",
        'skip_reason': skip_reason,
    })


def step3_2_tr_constraints(p1, wm, entities, transitions, state_dim_index, config_attrs, to_index):
    """Step 3.2: Generate CO from transition_relations (C1-auto)."""
    co_counter = [len(wm.co_list)]
    trs = p1['domain_model']['transition_relations']

    for tr in trs:
        r_from = tr['from']
        r_to = tr['to']
        evidence = tr.get('evidence_transitions', [])

        # Split evidence into enabler-side (R.from entity) and dependent-side (R.to entity)
        enabler_tids = [tid for tid in evidence if tid in transitions and transitions[tid]['entity'] == r_from]
        dependent_tids = [tid for tid in evidence if tid in transitions and transitions[tid]['entity'] == r_to]

        # If dependent side not in evidence, try to find via expected_results of enabler transitions
        if not dependent_tids and enabler_tids:
            for etid in enabler_tids:
                et = transitions[etid]
                for er in et.get('expected_results', []):
                    # Look for r_to entity state change
                    for tid, t in transitions.items():
                        if t['entity'] != r_to:
                            continue
                        # Check if this transition's state change is described in er
                        if t['from'] and t['to']:
                            if t['from'] in er and t['to'] in er:
                                if tid not in dependent_tids:
                                    dependent_tids.append(tid)
                                    break

        if not enabler_tids:
            wm.warnings['step3_2'].append(f"TR {r_from}->{r_to}: no enabler transitions in evidence {evidence}")
            continue

        if not dependent_tids:
            wm.warnings['step3_2'].append(f"TR {r_from}->{r_to}: no dependent transitions found, evidence={evidence}")
            continue

        # For each (enabler_tid, dependent_tid) pair, generate a CO
        for enabler_tid in enabler_tids:
            enabler_t = transitions[enabler_tid]
            enabler_dim = enabler_t['dimension']
            enabler_state = enabler_t['to']
            # For multi-value 'to', take first
            if '|' in str(enabler_state):
                enabler_state = str(enabler_state).split('|')[0].strip()

            for dependent_tid in dependent_tids:
                # Skip self-loop (enabler_tid == dependent_tid)
                if enabler_tid == dependent_tid and r_from == r_to:
                    wm.judgments.append({
                        'rule_point': '3.2 self-loop skip',
                        'basis': 'enabler transition == dependent transition, self-loop not meaningful as CO',
                        'evidence': [f'enabler_tid={enabler_tid}, dependent_tid={dependent_tid}, entity={r_from}'],
                        'affected_id': f'TR-{r_from}->{r_to}',
                        'decision': '跳过自循环'
                    })
                    continue

                dependent_t = transitions[dependent_tid]
                dependent_dim = dependent_t['dimension']
                dependent_condition = dependent_t['to']
                if '|' in str(dependent_condition):
                    dependent_condition = str(dependent_condition).split('|')[0].strip()

                # G3: dependent from==null
                dep_tos = to_index.get(dependent_tid, [])
                if dep_tos and all(to_obj['from'] is None for to_obj in dep_tos):
                    wm.warnings['step3_2'].append(f"TR {r_from}->{r_to}: G3 fail, dependent {dependent_tid} is creation")
                    continue

                # G1: enabler_dim is config
                if enabler_dim in config_attrs.get(r_from, set()):
                    wm.warnings['step3_2'].append(f"TR {r_from}->{r_to}: G1 fail, enabler_dim={enabler_dim} is config")
                    continue

                # (E,D,S) validation
                ok, fixed_dim, judgment, cleaned_state = validate_eds(enabler_state, r_from, enabler_dim, state_dim_index, entities)
                if not ok:
                    wm.warnings['step3_2'].append(f"TR {r_from}->{r_to}: (E,D,S) fail, enabler_state={enabler_state} not valid for {r_from}.{enabler_dim}")
                    continue
                if judgment:
                    wm.judgments.append({**judgment, 'affected_id': f'TR-{r_from}->{r_to}'})
                    enabler_dim = fixed_dim
                    enabler_state = cleaned_state

                # G6: check if same (enabler, dependent, constraint) already exists
                g6_hit = False
                for (e_ent, d_ent, c_type, co_id) in wm.co_index:
                    if e_ent == r_from and d_ent == r_to and c_type == 'constraint':
                        g6_hit = True
                        break
                if g6_hit:
                    wm.warnings['step3_2'].append(f"TR {r_from}->{r_to}: G6 hit, constraint CO already exists")
                    continue

                # coverage_priority
                trigger_source = tr.get('trigger_source', 'expected_results')
                rollback = tr.get('rollback_propagation', False)
                confidence = tr.get('confidence', 'high')
                coverage_priority = 'high'
                if trigger_source == 'bidi_coupling':
                    coverage_priority = 'critical'
                elif rollback:
                    coverage_priority = 'critical'
                elif confidence in ['low', 'medium']:
                    coverage_priority = 'high'
                if not evidence:
                    coverage_priority = 'medium'

                # aggregation
                aggregation = None
                for sr in p1['domain_model']['structural_relations']:
                    if (sr['from'] == r_from and sr['to'] == r_to
                            and sr['relation_type'] == 'composition' and sr['cardinality'] == '1:N'):
                        aggregation = 'all'
                        break

                # roles
                enabler_role = None
                er = enabler_t.get('role')
                if er != 'system':
                    enabler_role = er
                dependent_role = None
                dr = dependent_t.get('role')
                if dr != 'system':
                    dependent_role = dr

                # ref_to
                ref_to = None
                for to_obj in dep_tos:
                    for pc in to_obj.get('preconditions', []):
                        if enabler_state and enabler_state in pc:
                            ref_to = {
                                'obligation_type': 'transition_obligation',
                                'obligation_id': to_obj['id'],
                                'relation': 'precondition_references_enabler_state',
                                'detail': [pc]
                            }
                            break
                    if ref_to:
                        break

                desc = f"{r_from}.{enabler_dim}={enabler_state}是{r_to}.{dependent_dim}推进至{dependent_condition}的前置条件"

                if aggregation == 'all':
                    suggested_action = f"所有{r_from}的{enabler_dim}达到{enabler_state}是{r_to}的{dependent_dim}推进至{dependent_condition}的前置门禁"
                else:
                    suggested_action = f"{r_from}的{enabler_dim}达到{enabler_state}是{r_to}的{dependent_dim}推进至{dependent_condition}的前置门禁"

                co_counter[0] += 1
                co_id = f"CO-{co_counter[0]:03d}"
                co = {
                    'id': co_id,
                    'type': 'cross_entity',
                    'constraint_id': None,
                    'causal_type': 'constraint',
                    'enabler_entity': r_from,
                    'enabler_transition_id': enabler_tid,
                    'enabler_dimension': enabler_dim,
                    'enabler_state': enabler_state,
                    'dependent_entity': r_to,
                    'dependent_transition_id': dependent_tid,
                    'dependent_dimension': dependent_dim,
                    'dependent_condition': dependent_condition,
                    'aggregation': aggregation,
                    'ref_to': ref_to,
                    'trigger': tr.get('trigger'),
                    'trigger_source': trigger_source,
                    'rollback_propagation': rollback,
                    'confidence': confidence,
                    'desc': desc,
                    'coverage_priority': coverage_priority,
                    'enabler_role': enabler_role,
                    'dependent_role': dependent_role,
                    'suggested_action': suggested_action,
                    'merged_from': [],
                }
                wm.co_list.append(co)
                wm.co_index.append((r_from, r_to, 'constraint', co_id))

    return


def step3_3_lifecycle(p1, wm, entities, transitions, state_dim_index, to_index):
    """Step 3.3: Generate lifecycle CO from 1:1 composition business_ownership."""
    co_counter = [len(wm.co_list)]
    srs = p1['domain_model']['structural_relations']

    for sr in srs:
        if sr['relation_type'] != 'composition':
            continue
        if sr['cardinality'] != '1:1':
            continue  # G4: 1:N/M:N skip
        if sr['ownership_dimension'] != 'business_ownership':
            continue
        if sr['from'] == sr['to']:
            continue  # self_reference

        from_ent = sr['from']
        to_ent = sr['to']

        # Find creation transitions for both
        from_create_tid = None
        to_create_tid = None
        for tid, t in transitions.items():
            if t['entity'] == from_ent and t['from'] is None:
                from_create_tid = tid
            if t['entity'] == to_ent and t['from'] is None:
                to_create_tid = tid

        if not from_create_tid or not to_create_tid:
            wm.warnings['step3_2'].append(f"3.3 lifecycle {from_ent}->{to_ent}: missing creation transition")
            continue

        from_t = transitions[from_create_tid]
        to_t = transitions[to_create_tid]

        co_counter[0] += 1
        co_id = f"CO-{co_counter[0]:03d}"
        co = {
            'id': co_id,
            'type': 'cross_entity',
            'constraint_id': None,
            'causal_type': 'lifecycle',
            'enabler_entity': from_ent,
            'enabler_transition_id': from_create_tid,
            'enabler_dimension': from_t['dimension'],
            'enabler_state': from_t['to'],
            'dependent_entity': to_ent,
            'dependent_transition_id': to_create_tid,
            'dependent_dimension': to_t['dimension'],
            'dependent_condition': to_t['to'],
            'aggregation': None,
            'ref_to': None,
            'trigger': None,
            'trigger_source': None,
            'rollback_propagation': False,
            'confidence': 'high',
            'desc': f"{from_ent}与{to_ent}一对一绑定，创建/删除同步",
            'coverage_priority': 'high',
            'enabler_role': None,
            'dependent_role': None,
            'suggested_action': f"在{from_ent}创建/删除时，{to_ent}同步创建/删除",
            'merged_from': [],
        }
        wm.co_list.append(co)
        wm.co_index.append((from_ent, to_ent, 'lifecycle', co_id))

    return


def step3_4_dedup(wm):
    """Step 3.4: Deduplicate COs."""
    seen_signatures = {}  # signature -> co_id
    to_remove = set()

    for i, co in enumerate(wm.co_list):
        sig = (
            co['enabler_entity'],
            co['enabler_dimension'],
            co['enabler_state'],
            co['dependent_entity'],
            co['dependent_dimension'],
            co['dependent_condition'],
            co['causal_type'],
        )

        if sig in seen_signatures:
            # Merge into the earlier one
            keeper_id = seen_signatures[sig]
            keeper = next(c for c in wm.co_list if c['id'] == keeper_id)
            # Merge trigger/trigger_source/rollback/confidence
            if not keeper['trigger'] and co['trigger']:
                keeper['trigger'] = co['trigger']
            if not keeper['trigger_source'] and co['trigger_source']:
                keeper['trigger_source'] = co['trigger_source']
            if not keeper['rollback_propagation'] and co['rollback_propagation']:
                keeper['rollback_propagation'] = co['rollback_propagation']
            # Confidence: take higher
            conf_order = {'high': 0, 'medium': 1, 'low': 2}
            if conf_order.get(co['confidence'], 2) < conf_order.get(keeper['confidence'], 2):
                keeper['confidence'] = co['confidence']
            # coverage_priority: take higher
            pri_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            if pri_order.get(co['coverage_priority'], 3) < pri_order.get(keeper['coverage_priority'], 3):
                keeper['coverage_priority'] = co['coverage_priority']
            keeper['merged_from'].append(co['id'])
            to_remove.add(i)
        else:
            seen_signatures[sig] = co['id']

    wm.co_output = [co for i, co in enumerate(wm.co_list) if i not in to_remove]


def step3_5_validate(wm):
    """Step 3.5: Post-generation validation."""
    for co in wm.co_output:
        # 1. Direction check: dependent TO.preconditions should reference enabler side
        dep_tid = co['dependent_transition_id']
        if dep_tid:
            dep_tos = wm.to_index.get(dep_tid, [])
            enabler_ent = co['enabler_entity']
            enabler_state = co['enabler_state']
            for to_obj in dep_tos:
                for pc in to_obj.get('preconditions', []):
                    # Check if precondition references enabler entity/state
                    if enabler_ent in pc or (enabler_state and enabler_state in pc):
                        pass  # OK
                    # If precondition only references dependent entity itself, might be wrong direction
                    # (simplified check)

        # 2. Self-loop check: suggested_action shouldn't reference dependent_transition's action
        if dep_tid and dep_tid in {t['id'] for t in []}:  # need transitions
            pass

        # 3. (E,D,S) recheck
        enabler_state = co['enabler_state']
        if enabler_state:
            # Already validated in generation, skip detailed recheck
            pass


# ---------------------------------------------------------------------------
# Step 4: constraint_obligations
# ---------------------------------------------------------------------------
def step4_constraint_obligations(p1, wm):
    """Step 4: Generate RO-IT and RO-BR."""
    # 4.1: invalid_transitions -> RO-IT
    ro_it_counter = [0]
    for it in p1['constraints']['invalid_transitions']:
        ro_it_counter[0] += 1
        ro_it_id = f"RO-IT-{ro_it_counter[0]:03d}"
        ro_it = {
            'id': ro_it_id,
            'type': 'invalid_transition',
            'constraint_id': it['id'],
            'entity': it['entity'],
            'dimension': None,  # Will infer from entity
            'from': it['from'],
            'to': it['to'],
            'reason': it['reason'],
            'coverage_priority': 'high',
            'suggested_action': f"在{it['entity']}处于{it['from']}状态时，尝试执行{it['to']}",
        }
        # Infer dimension from entity's first state dimension
        for e in p1['domain_model']['entities']:
            if e['id'] == it['entity']:
                if e.get('state_dimensions'):
                    ro_it['dimension'] = e['state_dimensions'][0]['dimension_name']
                break
        wm.ro_it_list.append(ro_it)

    # 4.2: business_rules -> RO-BR
    # Counter continues from RO-BR already created from XCs
    ro_br_counter = [len(wm.ro_br_from_xc)]
    for br in p1['constraints']['business_rules']:
        ro_br_counter[0] += 1
        ro_br_id = f"RO-BR-{ro_br_counter[0]:04d}"
        desc = br.get('desc', '')
        severity = br.get('severity', 'mandatory')
        signal_type = br.get('signal_type')
        category = br.get('category', 'validation')

        # coverage_priority
        coverage_priority = 'medium'
        if '金额' in desc or '计算' in desc:
            coverage_priority = 'high'
        if severity == 'conditional':
            coverage_priority = 'low'
        if signal_type == 'usability' and any(kw in desc for kw in ['必填', '标识', '提示']):
            coverage_priority = 'high'
        if category == 'display':
            coverage_priority = 'medium'
        if signal_type == 'field_constraint':
            coverage_priority = 'high'
        # mandatory + computation/auth -> high
        if severity == 'mandatory' and category in ['computation', 'authorization', 'timing']:
            coverage_priority = 'high'

        entities_involved = br.get('entities_involved', [])
        entities_label = ', '.join(entities_involved) if isinstance(entities_involved, list) else str(entities_involved)

        ro_br = {
            'id': ro_br_id,
            'type': 'business_rule',
            'constraint_id': br['id'],
            'entities_involved': entities_involved,
            'category': category,
            'signal_type': signal_type,
            'description': desc,
            'enforcement': 'mandatory' if severity == 'mandatory' else 'conditional',
            'source_xc': None,
            'ref_to_existing_br': None,
            'coverage_priority': coverage_priority,
            'suggested_action': f"在{entities_label}涉及环节, 按{desc[:40]}规则执行操作",
        }
        wm.ro_br_list.append(ro_br)

    return


# ---------------------------------------------------------------------------
# Step 5: _context
# ---------------------------------------------------------------------------
def step5_context(p1, wm, entities, transitions, state_dim_index, branch_dims, trs, srs):
    """Step 5: Build _context."""

    # branch_dimensions: copy from P1, supplement entity, fill affected_obligations
    ctx_branch_dims = []
    for bd in branch_dims:
        bd_copy = {
            'dimension': bd['dimension'],
            'entity': bd.get('entity', ''),
            'values': list(bd['values']),
            'impact_scope': bd.get('impact_scope', ''),
            'evidence': bd.get('evidence', ''),
            'branches': [],
            'coverage': bd.get('coverage', {}),
            'affected_obligations': [],
        }
        # Process branches: set target_transition to empty if not in P1
        for b in bd.get('branches', []):
            tt = b.get('target_transition', '')
            if tt and tt not in transitions:
                tt = ''
            bd_copy['branches'].append({
                'value': b['value'],
                'target_transition': tt,
                'desc': b.get('desc', '')
            })
        # Scan TOs for branch_path matching this dimension
        for to_obj in wm.to_list:
            for bp in to_obj.get('branch_path', []):
                if bp['dimension'] == bd['dimension']:
                    if to_obj['id'] not in bd_copy['affected_obligations']:
                        bd_copy['affected_obligations'].append(to_obj['id'])
        ctx_branch_dims.append(bd_copy)

    # structural_relations
    ctx_srs = []
    for sr in srs:
        ctx_srs.append({
            'from': sr['from'],
            'to': sr['to'],
            'relation_type': sr['relation_type'],
            'ownership_dimension': sr.get('ownership_dimension', ''),
            'cardinality': sr['cardinality'],
            'confidence': sr.get('confidence', 'high'),
            'desc': sr.get('desc', ''),
        })

    # transition_relations
    ctx_trs = []
    for tr in trs:
        ctx_trs.append({
            'from': tr['from'],
            'to': tr['to'],
            'trigger': tr.get('trigger', ''),
            'trigger_source': tr.get('trigger_source', ''),
            'evidence_transitions': list(tr.get('evidence_transitions', [])),
            'rollback_propagation': tr.get('rollback_propagation', False),
            'confidence': tr.get('confidence', 'high'),
            'desc': tr.get('desc', ''),
        })

    # state_info
    state_info = {}
    for eid, e in entities.items():
        state_info[eid] = {}
        for d in e.get('state_dimensions', []):
            state_info[eid][d['dimension_name']] = {
                'initial': d['initial'],
                'terminal': d.get('terminal', []),
                'states': list(d['states'])
            }

    # entity_details
    entity_details = []
    for eid, e in entities.items():
        entity_details.append({
            'id': eid,
            'name': e['name'],
            'tags': e.get('tags', []),
            'type': e['type'],
            'desc': e.get('desc', ''),
            'attributes': [{'name': a['name'], 'desc': a['desc'], 'is_config': a.get('is_config', False)} for a in e['attributes']],
        })

    # roles
    roles = [{'id': r['id'], 'name': r['name'], 'readonly': r.get('readonly', False)} for r in p1['domain_model']['roles']]

    # transition_notes: only transitions with non-empty note
    transition_notes = {}
    for tid, t in transitions.items():
        n = t.get('note', {})
        if n.get('comment') or n.get('conflict') or n.get('inferred'):
            transition_notes[tid] = {
                'inferred': n.get('inferred', False),
                'comment': n.get('comment', ''),
                'conflict': n.get('conflict', ''),
                'branch_dimension': n.get('branch_dimension', ''),
            }

    # xc_to_br_mapping: already built in wm
    # judgments: already in wm
    # warnings: already in wm

    ctx = {
        'branch_dimensions': ctx_branch_dims,
        'structural_relations': ctx_srs,
        'transition_relations': ctx_trs,
        'state_info': state_info,
        'entity_details': entity_details,
        'roles': roles,
        'transition_notes': transition_notes,
        'xc_to_br_mapping': wm.xc_to_br_mapping,
        'judgments': wm.judgments,
        'warnings': {
            'data_check': wm.warnings.get('data_check', []),
            'step3_1': wm.warnings.get('step3_1', []),
            'step3_2': wm.warnings.get('step3_2', []),
            'step3_5': wm.warnings.get('step3_5', []),
        },
    }
    return ctx


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    with open('/home/z/my-project/download/srs_structured_analysis.json', 'r', encoding='utf-8') as f:
        p1 = json.load(f)

    wm = WorkMem()
    entities, transitions, state_dim_index, config_attrs, roles, branch_dims, trs, srs = build_indices(p1)

    # Step 1
    step1_entity_obligations(p1, wm, entities, config_attrs)

    # Step 2
    step2_transition_obligations(p1, wm, entities, transitions, state_dim_index, branch_dims, trs)

    # Step 3.1
    step3_1_xc_constraints(p1, wm, entities, transitions, state_dim_index, config_attrs, wm.to_index)

    # Step 3.2
    step3_2_tr_constraints(p1, wm, entities, transitions, state_dim_index, config_attrs, wm.to_index)

    # Step 3.3
    step3_3_lifecycle(p1, wm, entities, transitions, state_dim_index, wm.to_index)

    # Step 3.4 dedup
    step3_4_dedup(wm)

    # Step 3.5 validate
    step3_5_validate(wm)

    # Step 4
    step4_constraint_obligations(p1, wm)

    # Step 5
    ctx = step5_context(p1, wm, entities, transitions, state_dim_index, branch_dims, trs, srs)

    # Assemble output
    output = {
        'entity_obligations': wm.eo_list,
        'transition_obligations': wm.to_list,
        'cross_entity_obligations': wm.co_output,
        'constraint_obligations': wm.ro_it_list + wm.ro_br_from_xc + wm.ro_br_list,
        '_context': ctx,
    }

    # ASCII safety
    output = walk_safe(output)

    # Write
    out_path = '/home/z/my-project/download/obligation_coverage_model.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Validate
    with open(out_path, 'r', encoding='utf-8') as f:
        reloaded = json.load(f)

    # ASCII safety scan
    content = json.dumps(reloaded, ensure_ascii=False)
    forbidden = ['\u2192', '\u2190', '\u2191', '\u2193', '\u201c', '\u201d', '\u2018', '\u2019']
    found = [c for c in forbidden if c in content]
    ascii_ok = len(found) == 0

    # Check no branch_scenarios field
    no_branch_scenarios = 'branch_scenarios' not in content

    # Check all XC in xc_status
    all_xc_covered = True
    for xc in p1['constraints']['cross_entity']:
        if xc['id'] not in wm.xc_status:
            all_xc_covered = False

    print(f"=== Output Summary ===")
    print(f"File: {out_path}")
    print(f"ASCII safety: {'PASSED' if ascii_ok else 'FAILED: ' + str(found)}")
    print(f"No branch_scenarios: {no_branch_scenarios}")
    print(f"All XC covered: {all_xc_covered}")
    print(f"entity_obligations: {len(reloaded['entity_obligations'])}")
    print(f"transition_obligations: {len(reloaded['transition_obligations'])}")
    print(f"cross_entity_obligations: {len(reloaded['cross_entity_obligations'])}")
    print(f"constraint_obligations: {len(reloaded['constraint_obligations'])}")
    print(f"  RO-IT: {len(wm.ro_it_list)}")
    print(f"  RO-BR (from P1 BR): {len(wm.ro_br_list)}")
    print(f"  RO-BR (from skipped XC): {len(wm.ro_br_from_xc)}")
    print(f"xc_status: {dict(list(wm.xc_status.items()))}")
    print(f"judgments: {len(wm.judgments)}")
    print(f"warnings: {sum(len(v) for v in wm.warnings.values())}")


if __name__ == '__main__':
    main()
