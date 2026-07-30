#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re
import sys

if len(sys.argv) < 2:
    print("Usage: python validate.py <path_to_p1_json>")
    sys.exit(1)

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)

entities = {e['id']: e for e in data['domain_model']['entities']}
roles = {r['id']: r for r in data['domain_model']['roles']}

errors = []
warnings = []

# Check 1: 引用完整性
for t in data['state_and_flow']['transitions']:
    if t['entity'] not in entities:
        errors.append(f"T-{t['id']}: entity {t['entity']} not found")
    if t['role'] != 'system' and t['role'] not in roles:
        errors.append(f"T-{t['id']}: role {t['role']} not found")
    for p in t['preconditions']:
        if p['type'] == 'state_ref' and p['ref']:
            ref = p['ref']
            if ref['entity'] not in entities:
                errors.append(f"T-{t['id']}: precondition ref entity {ref['entity']} not found")
            else:
                e = entities[ref['entity']]
                dims = [d['dimension_name'] for d in e['state_dimensions']]
                if ref['dimension'] not in dims:
                    errors.append(f"T-{t['id']}: precondition ref dimension {ref['dimension']} not in entity {ref['entity']}")
                else:
                    dim = next(d for d in e['state_dimensions'] if d['dimension_name'] == ref['dimension'])
                    if ref['state'] not in dim['states']:
                        errors.append(f"T-{t['id']}: precondition ref state {ref['state']} not in {ref['entity']}.{ref['dimension']} states")

# Check 2: 状态结构 - non-terminal has out-edges
for e in data['domain_model']['entities']:
    for dim in e['state_dimensions']:
        for state in dim['states']:
            if state in dim['terminal']:
                continue
            has_out = False
            for t in data['state_and_flow']['transitions']:
                if t['entity'] == e['id'] and t['dimension'] == dim['dimension_name'] and t['from'] == state:
                    has_out = True
                    break
            if not has_out:
                errors.append(f"{e['id']}.{dim['dimension_name']}: non-terminal state '{state}' has no outgoing transition")

# Check 3: preconditions结构
for t in data['state_and_flow']['transitions']:
    for p in t['preconditions']:
        if not isinstance(p, dict):
            errors.append(f"T-{t['id']}: precondition is not object")
        elif not p.get('text'):
            errors.append(f"T-{t['id']}: precondition text empty")
        elif p['type'] not in ['state_ref', 'event_ref', 'constraint']:
            errors.append(f"T-{t['id']}: precondition type invalid: {p['type']}")
        elif p['type'] == 'state_ref':
            if not isinstance(p.get('ref'), dict):
                errors.append(f"T-{t['id']}: state_ref ref is not object")
        else:
            if p.get('ref') is not None:
                errors.append(f"T-{t['id']}: {p['type']} ref should be null")

# Check 10: 字符安全
def check_str_safe(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            check_str_safe(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check_str_safe(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        # Check for raw arrows
        for arrow in ['\u2192', '\u2190', '\u2191', '\u2193']:
            if arrow in obj:
                errors.append(f"{path}: contains arrow: {obj[:80]}")
        # Check for curly quotes
        for q in ['\u201c', '\u201d', '\u2018', '\u2019']:
            if q in obj:
                errors.append(f"{path}: contains curly quote: {obj[:80]}")
        # Check for raw & not part of entity
        for m in re.finditer(r'&(?!lt;|gt;|amp;|quot;|#\d+;)', obj):
            errors.append(f"{path}: contains unescaped &: {obj[:80]}")
            break

check_str_safe(data)

# Check 12: operations完整性
valid_categories = ['session', 'ui', 'file', 'query', 'crud', 'config']
for e in data['domain_model']['entities']:
    op_names = set()
    for op in e.get('operations', []):
        if op['category'] not in valid_categories:
            errors.append(f"{e['id']}.op {op['name']}: invalid category {op['category']}")
        if not op.get('source_ref'):
            errors.append(f"{e['id']}.op {op['name']}: empty source_ref")
        if len(op.get('expected_results', [])) < 1:
            errors.append(f"{e['id']}.op {op['name']}: empty expected_results")
        if op['name'] in op_names:
            errors.append(f"{e['id']}: duplicate operation {op['name']}")
        op_names.add(op['name'])

# Check 11: 空值规范 - check required fields exist
for e in data['domain_model']['entities']:
    for field in ['id', 'name', 'desc', 'type', 'tags', 'attributes', 'state_dimensions', 'operations']:
        if field not in e:
            errors.append(f"{e['id']}: missing field {field}")

print(f"Errors: {len(errors)}")
for e in errors[:30]:
    print(f"  ERROR: {e}")
print(f"\nWarnings: {len(warnings)}")
for w in warnings[:10]:
    print(f"  WARN: {w}")

# Branch coverage check
print("\n=== Branch Coverage ===")
for bd in data['_meta']['branch_dimensions']:
    has_t = len(bd['coverage']['transitions']) > 0
    has_xc = len(bd['coverage']['cross_entity']) > 0
    has_br = len(bd['coverage']['business_rules']) > 0
    print(f"  {bd['dimension']}: T={has_t} XC={has_xc} BR={has_br}")
    if not (has_t and has_br):
        warnings.append(f"Branch {bd['dimension']}: missing T or BR coverage")

# Check transition_relations
print("\n=== Transition Relations ===")
for tr in data['domain_model']['transition_relations']:
    if not tr.get('trigger'):
        errors.append(f"TR {tr['from']}->{tr['to']}: empty trigger")
    if not tr.get('trigger_source'):
        errors.append(f"TR {tr['from']}->{tr['to']}: empty trigger_source")

print(f"\nFinal: {len(errors)} errors, {len(warnings)} warnings")
