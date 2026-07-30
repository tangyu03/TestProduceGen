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

errors = []
warnings = []

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
        if eo['source_ref'] is not None:
            errors.append(f"{eo['id']}: source_ref should be null (P1 attr has no source_ref)")
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
                'note', 'sub_steps', 'coverage_priority', 'is_repeatable', 'repeat_condition',
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
        required = ['id', 'type', 'constraint_id', 'entities_involved', 'category', 'signal_type',
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

# Check self_check all true (except allowed false)
sc = ctx['self_check']
for k, v in sc.items():
    if v is False and k in ['id_globally_unique', 'p1_root_nodes_complete']:
        errors.append(f"self_check {k} is false (fatal)")
    elif v is False:
        warnings.append(f"self_check {k} is false")

# Check XC status complete (requires P1 JSON for cross-reference)
if p1_path:
    xc_ids_in_status = {m['xc_id'] for m in ctx['xc_to_br_mapping']}
    p1_xc_ids = set()
    with open(p1_path, 'r', encoding='utf-8') as f:
        p1 = json.load(f)
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

print(f"Errors: {len(errors)}")
for e in errors[:20]:
    print(f"  ERROR: {e}")
print(f"\nWarnings: {len(warnings)}")
for w in warnings[:10]:
    print(f"  WARN: {w}")

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
