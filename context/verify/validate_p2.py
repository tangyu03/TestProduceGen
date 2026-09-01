#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate P2 output against schema requirements."""
import json
import re
import sys

if len(sys.argv) < 2:
    print("Usage: python validate_p2.py <path_to_p2_json> [path_to_p1_json]")
    sys.exit(1)

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    d = json.load(f)

p1_path = sys.argv[2] if len(sys.argv) >= 3 else None
p1 = None
if p1_path:
    with open(p1_path, 'r', encoding='utf-8') as f:
        p1 = json.load(f)

errors = []
warnings = []
infos = []

# Check top-level keys
expected_top = ['entity_obligations', 'transition_obligations', 'cross_entity_obligations', 'constraint_obligations', '_context']
for k in expected_top:
    if k not in d:
        errors.append(f"Missing top-level key: {k}")

# Check EO-ATC schema
for eo in d['entity_obligations']:
    if eo['type'] == 'attribute_config':
        required = ['id', 'type', 'entity', 'entity_name', 'attribute_name', 'attribute_desc',
                    'description', 'suggested_action', 'coverage_priority', 'dimension', 'from', 'to', 'source_ref']
        for r in required:
            if r not in eo:
                errors.append(f"{eo['id']}: missing field {r}")
        if eo['dimension'] is not None or eo['from'] is not None or eo['to'] is not None:
            errors.append(f"{eo['id']}: dimension/from/to should be null")
        # EO-ATC source_ref：P1 属性无 source_ref 字段，生成器透传实体首条操作的 source_ref
        # 作章节定位（generate_obligation_model._entity_config_section_ref）。合法值 = null
        # （实体无带 source_ref 的操作）或非空字符串（透传值）；一致性由下方 p1 派生复核闸门兜底。
        if eo['source_ref'] is not None and (
                not isinstance(eo['source_ref'], str) or not eo['source_ref'].strip()):
            errors.append(f"{eo['id']}: source_ref 应为 null 或非空字符串（实体首条操作章节定位）")
    elif eo['type'] == 'crud_operation':
        required = ['id', 'type', 'entity', 'entity_name', 'operation_name', 'operation_category',
                    'description', 'expected_results', 'suggested_action', 'coverage_priority', 'source_ref']
        for r in required:
            if r not in eo:
                errors.append(f"{eo['id']}: missing field {r}")
        if not eo.get('expected_results'):
            errors.append(f"{eo['id']}: expected_results empty")
        valid_cats = ['session', 'ui', 'file', 'query', 'crud', 'config']
        if eo['operation_category'] not in valid_cats:
            errors.append(f"{eo['id']}: invalid operation_category {eo['operation_category']}")

# Check TO schema
for to in d['transition_obligations']:
    required = ['id', 'entity', 'dimension', 'from', 'to', 'action', 'role',
                'preconditions', 'expected_results', 'risk_traits', 'priority', 'source_ref',
                'note', 'coverage_priority', 'is_repeatable', 'repeat_condition',
                'side_effects', 'branch_path', 'precondition_state_refs']
    for r in required:
        if r not in to:
            errors.append(f"TO {to['id']}: missing field {r}")
    # preconditions must be object array
    for p in to.get('preconditions', []):
        if not isinstance(p, dict) or 'text' not in p or 'type' not in p or 'ref' not in p:
            errors.append(f"TO {to['id']}: precondition not structured: {p}")
        elif p['type'] not in ['state_ref', 'event_ref', 'constraint']:
            errors.append(f"TO {to['id']}: invalid precondition type {p['type']}")
        elif p['type'] == 'state_ref' and p['ref'] is not None:
            ref = p['ref']
            if not isinstance(ref, dict):
                errors.append(f"TO {to['id']}: state_ref ref not object")
            elif 'entity' not in ref or 'dimension' not in ref or 'state' not in ref:
                errors.append(f"TO {to['id']}: state_ref ref missing keys")
    # coverage_priority valid
    if to['coverage_priority'] not in ['critical', 'high', 'medium', 'low']:
        errors.append(f"TO {to['id']}: invalid coverage_priority {to['coverage_priority']}")

# Check CO schema
for co in d['cross_entity_obligations']:
    required = ['id', 'type', 'constraint_id', 'causal_type', 'enabler_entity', 'enabler_dimension',
                'enabler_state', 'enabler_transition_id', 'enabler_role', 'dependent_entity',
                'dependent_transition_id', 'dependent_dimension', 'dependent_condition', 'dependent_role',
                'aggregation', 'ref_to', 'trigger', 'trigger_source', 'rollback_propagation',
                'confidence', 'desc', 'coverage_priority', 'suggested_action', 'merged_from', 'source_ref']
    for r in required:
        if r not in co:
            errors.append(f"CO {co['id']}: missing field {r}")
    if co['causal_type'] not in ['constraint', 'auto', 'lifecycle']:
        errors.append(f"CO {co['id']}: invalid causal_type {co['causal_type']}")

# Check RO schema
for ro in d['constraint_obligations']:
    if ro['type'] == 'invalid_transition':
        required = ['id', 'type', 'constraint_id', 'entity', 'from', 'to', 'reason', 'coverage_priority', 'source_ref']
        for r in required:
            if r not in ro:
                errors.append(f"RO-IT {ro['id']}: missing field {r}")
    elif ro['type'] == 'business_rule':
        required = ['id', 'type', 'constraint_id', 'entities_involved', 'category', 'restrictive',
                    'description', 'enforcement', 'ref_to_existing_br', 'coverage_priority', 'suggested_action', 'source_ref']
        for r in required:
            if r not in ro:
                errors.append(f"RO-BR {ro['id']}: missing field {r}")

# Check _context
ctx = d['_context']
required_ctx = ['source', 'generated_at', 'p1_meta', 'branch_dimensions', 'structural_relations',
                'transition_relations', 'state_info', 'xc_to_br_mapping', 'judgments', 'warnings',
                'snapshot', 'self_check']
for r in required_ctx:
    if r not in ctx:
        errors.append(f"_context: missing field {r}")

# Check character safety (no raw < > &)
def check_str_safe(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            check_str_safe(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check_str_safe(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        for m in re.finditer(r'&(?!lt;|gt;|amp;|quot;|#\d+;)', obj):
            errors.append(f"{path}: unescaped &: {obj[:80]}")
            break

check_str_safe(d)

# Check ID global uniqueness
all_ids = []
for eo in d['entity_obligations']:
    all_ids.append(eo['id'])
for to in d['transition_obligations']:
    all_ids.append(to['id'])
for co in d['cross_entity_obligations']:
    all_ids.append(co['id'])
for ro in d['constraint_obligations']:
    all_ids.append(ro['id'])
if len(all_ids) != len(set(all_ids)):
    from collections import Counter
    dupes = [k for k, v in Counter(all_ids).items() if v > 1]
    errors.append(f"Duplicate IDs: {dupes}")

# no_branch_scenarios recompute (same rule as the P2 generator):
# a branch-affected TO with an empty branch_path is a MISSING scenario ONLY if
# it was not split into branch variants and has no degradation judgment.
# A base TO retained alongside its [a][b]... variants ("main TO" for
# cross-dimension linkage) is a split scenario -> excluded.
def _no_branch_offenders(d):
    ctx = d['_context']
    bds = ctx.get('branch_dimensions', []) or []
    tos = d['transition_obligations']
    judgments = ctx.get('judgments', []) or []
    offenders = []
    for to in tos:
        base = to['id'].split('[')[0]
        matched = [bd for bd in bds if base in (bd.get('coverage') or {}).get('transitions', [])]
        bn = ''
        if isinstance(to.get('note'), dict):
            bn = to['note'].get('branch_dimension', '') or ''
        if not matched and bn:
            matched = [bd for bd in bds if bd.get('dimension') in bn]
        if matched and not to.get('branch_path'):
            has_variants = any(t2['id'].startswith(to['id'] + '[') for t2 in tos)
            has_deg = any(
                ('降级' in j['desc'] or '无实质差异' in j['desc'])
                and j['desc'].split(':', 1)[0].strip() == to['id']
                for j in judgments
            )
            if not has_variants and not has_deg:
                offenders.append(to['id'])
    return offenders

# Check self_check all true (except allowed false)
sc = ctx['self_check']
for k, v in sc.items():
    if v is False and k in ['id_globally_unique', 'p1_root_nodes_complete']:
        errors.append(f"self_check {k} is false (fatal)")
    elif k == 'no_branch_scenarios' and v is False:
        offenders = _no_branch_offenders(d)
        if offenders:
            warnings.append(f"self_check no_branch_scenarios is false; branch-affected TOs not split & no degradation judgment: {offenders}")
        else:
            infos.append("self_check no_branch_scenarios stored false, but recomputed ok: all branch-affected TOs are split (incl. retained main TOs) - excluded")
    elif v is False:
        warnings.append(f"self_check {k} is false")

# Check XC status complete (requires P1 JSON for cross-reference)
if p1_path:
    xc_ids_in_status = {m['xc_id'] for m in ctx['xc_to_br_mapping']}
    p1_xc_ids = set()
    for xc in p1['constraints']['cross_entity']:
        p1_xc_ids.add(xc['id'])
    if xc_ids_in_status != p1_xc_ids:
        errors.append(f"XC status mismatch: missing={p1_xc_ids - xc_ids_in_status}, extra={xc_ids_in_status - p1_xc_ids}")
else:
    warnings.append("P1 JSON not provided — skipping XC status cross-check")

# Check all skipped XC have BR
xc_as_br = {m['xc_id'] for m in ctx['xc_to_br_mapping'] if m['status'] == 'br'}
ro_br_xc_ids = {ro['constraint_id'] for ro in d['constraint_obligations'] if ro['type'] == 'business_rule' and ro['constraint_id'].startswith('XC-')}
if xc_as_br != ro_br_xc_ids:
    errors.append(f"XC->BR mismatch: xc_as_br={xc_as_br}, ro_br_xc_ids={ro_br_xc_ids}")

# Check CO transition refs resolve (Option C): a CO references the abstract (P1)
# transition id; it must be an emitted TO id, a split base in
# _context.transition_splits, or have emitted [a][b]... variants.
to_ids = {t['id'] for t in d['transition_obligations']}
splits = ctx.get('transition_splits', {}) or {}
for co in d['cross_entity_obligations']:
    for fld in ('enabler_transition_id', 'dependent_transition_id'):
        tid = co.get(fld)
        if tid:
            resolves = (tid in to_ids) or (tid in splits) or any(k.startswith(tid + '[') for k in to_ids)
            if not resolves:
                errors.append(f"CO {co['id']}: {fld} {tid} 不指向任何TO/拆分基 (dangling)")

# ============ ③ CO dependent-uniqueness 闸门 ============
# 用共享派生规则(co_derivation, 与 P2 生成器同一份逻辑)从 P1 重推导每个
# auto CO 的 dependent_transition_id, 要求与产出严格一致。兜住历史 first-pick
# 回归(E-PROJ→已选入 4 候选静默取错 T-002, 应为 T-012)。
# 洞4: 同 (enabler_transition, dependent_transition) 边不允许跨 causal_type 共存。
if p1 is not None:
    import os as _os
    import importlib as _importlib
    _ctx_dir = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    if _ctx_dir not in sys.path:
        sys.path.insert(0, _ctx_dir)
    _co_derivation = _importlib.import_module("co_derivation")

    _p1_tr_by_id = {t['id']: t for t in p1['state_and_flow']['transitions']}
    _p1_xc = p1['constraints']['cross_entity']
    _xc_by_id = {x['id']: x for x in _p1_xc}

    for co in d['cross_entity_obligations']:
        if co.get('causal_type') != 'auto':
            continue
        cid = co.get('constraint_id')
        if not cid:
            continue  # R 来源 CO 无 XC, 不在本闸门范围
        xc = _xc_by_id.get(cid)
        if not xc:
            continue
        dep_tid, info = _co_derivation.resolve_dependent_transition(
            _p1_xc, _p1_tr_by_id, xc)
        if co.get('dependent_transition_id') != dep_tid:
            errors.append(
                f"CO {co['id']}: dependent_transition_id={co.get('dependent_transition_id')} "
                f"与共享派生规则不符 (应={dep_tid}, via={info['via']}, "
                f"from={info['from_state']}, to={info['to_state']}, "
                f"candidates={info['candidates']})"
            )

    _seen_edge = {}
    for co in d['cross_entity_obligations']:
        key = (co.get('enabler_transition_id'), co.get('dependent_transition_id'))
        if not all(key):
            continue
        ct = co.get('causal_type')
        if key in _seen_edge and _seen_edge[key] != ct:
            errors.append(
                f"CO {co['id']}: 边 {key} causal_type={ct} 与 {_seen_edge[key]} 冲突 "
                f"(同 (enabler,dependent) 对不允许跨 causal_type 共存)"
            )
        _seen_edge.setdefault(key, ct)

    # EO-ATC source_ref 派生复核（数据驱动）：P1 属性无 source_ref，生成器透传实体首条
    # 带 source_ref 的操作的 source_ref 作章节定位。此处按同规则重推导比对，防生成侧漂移。
    _p1_e_by_id = {e['id']: e for e in p1['domain_model']['entities']}
    for eo in d['entity_obligations']:
        if eo['type'] != 'attribute_config':
            continue
        ent = _p1_e_by_id.get(eo['entity'])
        expect = None
        if ent:
            for op in ent.get('operations', []):
                if isinstance(op, dict) and op.get('source_ref'):
                    expect = op['source_ref']
                    break
        if eo.get('source_ref') != expect:
            errors.append(
                f"EO {eo['id']}: source_ref={eo.get('source_ref')!r} 与派生不符 "
                f"(实体首条操作应={expect!r})")
else:
    infos.append("P1 JSON 未提供 —— 跳过 CO dependent-uniqueness 重推导与 EO-ATC source_ref 复核闸门")

print(f"Errors: {len(errors)}")
for e in errors[:20]:
    print(f"  ERROR: {e}")
print(f"\nWarnings: {len(warnings)}")
for w in warnings[:10]:
    print(f"  WARN: {w}")
if infos:
    print(f"Infos: {len(infos)}")
    for i in infos[:10]:
        print(f"  INFO: {i}")

print(f"\n=== Summary ===")
print(f"EO-ATC: {len([e for e in d['entity_obligations'] if e['type']=='attribute_config'])}")
print(f"EO-CRU: {len([e for e in d['entity_obligations'] if e['type']=='crud_operation'])}")
print(f"TO: {len(d['transition_obligations'])} (split: {len([t for t in d['transition_obligations'] if '[' in t['id']])})")
print(f"CO: {len(d['cross_entity_obligations'])}")
print(f"RO-IT: {len([r for r in d['constraint_obligations'] if r['type']=='invalid_transition'])}")
print(f"RO-BR: {len([r for r in d['constraint_obligations'] if r['type']=='business_rule'])}")
print(f"Judgments: {len(ctx['judgments'])}")
print(f"Warnings in _context: {len(ctx['warnings'])}")
print(f"\nSelf-check: {sc}")
# C-08: 有 error 必须非零退出——CI/脚本靠 $? 判断校验是否通过，
# 旧实现发现 20+ error 也正常退出 0，门禁形同虚设。
sys.exit(1 if errors else 0)
