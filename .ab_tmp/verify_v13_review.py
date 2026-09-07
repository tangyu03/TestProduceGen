# -*- coding: utf-8 -*-
"""MD ↔ JSON 依赖一致性校验（评审修补后）。"""
import json
import re

d = json.load(open('pt_outputv13.json', encoding='utf-8'))
procs = d['procedures']
json_deps = {}   # base -> set(base ids of deps)
json_weak = {}
json_branch = {}  # base -> has 项目类型 branch given
for p in procs:
    base = re.sub(r'\.\d+$', '', p['temp_id'])
    s3 = p.get('_S3_fields', {})
    ds = {re.sub(r'\.\d+$', '', x) for x in s3.get('dependencies', [])}
    ws = {re.sub(r'\.\d+$', '', x) for x in s3.get('weak_dependencies', [])}
    json_deps.setdefault(base, set()).update(ds)
    json_weak.setdefault(base, set()).update(ws)
    for g in p.get('givens', []):
        if g.get('given_type') == 'branch' and '项目类型' in (g.get('description') or ''):
            json_branch[base] = True

text = open('pt_outputv13.md', encoding='utf-8').read()
blocks = re.split(r'\n(?=### )', text)
md_cases = {}
for b in blocks:
    b = b.strip()
    m = re.match(r'### (PROC-\d+)', b)
    if not m:
        continue
    pid = m.group(1)
    dep = re.search(r'\*\*依赖\*\*：(.+)', b)
    weak = re.search(r'\*\*弱依赖\*\*：(.+)', b)
    md_cases[pid] = {
        'deps': {x.strip() for x in dep.group(1).split(',')} if dep else set(),
        'weak': {x.strip() for x in weak.group(1).split(',')} if weak else set(),
        'branch_type': '分支条件：项目类型=' in b,
    }

bad = 0
for pid, mc in sorted(md_cases.items()):
    jd = json_deps.get(pid, set())
    jw = json_weak.get(pid, set())
    jb = json_branch.get(pid, False)
    if mc['deps'] != jd:
        print(f'DEP MISMATCH {pid}: md={sorted(mc["deps"])} json={sorted(jd)}'); bad += 1
    if mc['weak'] != jw:
        print(f'WEAK MISMATCH {pid}: md={sorted(mc["weak"])} json={sorted(jw)}'); bad += 1
    if mc['branch_type'] != jb:
        print(f'BRANCH MISMATCH {pid}: md={mc["branch_type"]} json={jb}'); bad += 1

# 评审点逐项复核
checks = [
    ('PROC-012 依赖含017', 'PROC-017' in md_cases['PROC-012']['deps']),
    ('PROC-013 依赖含017', 'PROC-017' in md_cases['PROC-013']['deps']),
    ('PROC-052 依赖含049', 'PROC-049' in md_cases['PROC-052']['deps']),
    ('PROC-066 依赖含059', 'PROC-059' in md_cases['PROC-066']['deps']),
    ('PROC-070 依赖含068/069', {'PROC-068','PROC-069'} <= md_cases['PROC-070']['deps']),
    ('PROC-071 依赖含068/069', {'PROC-068','PROC-069'} <= md_cases['PROC-071']['deps']),
    ('PROC-081 依赖含080', 'PROC-080' in md_cases['PROC-081']['deps']),
    ('PROC-021 根=031', md_cases['PROC-021']['deps'] == {'PROC-031'}),
    ('PROC-022 根=031', md_cases['PROC-022']['deps'] == {'PROC-031','PROC-021'}),
    ('PROC-067 根=031', md_cases['PROC-067']['deps'] == {'PROC-031','PROC-022'}),
    ('PROC-078 根=031', md_cases['PROC-078']['deps'] == {'PROC-031','PROC-021','PROC-067'}),
    ('PROC-079 根=031', md_cases['PROC-079']['deps'] == {'PROC-031','PROC-078'}),
    ('PROC-056 仅005', md_cases['PROC-056']['deps'] == {'PROC-005'}),
    ('PROC-089 挂084', md_cases['PROC-089']['deps'] == {'PROC-073','PROC-082','PROC-084'}),
    ('PROC-030 无029', 'PROC-029' not in md_cases['PROC-030']['deps']),
    ('PROC-031 无029', 'PROC-029' not in md_cases['PROC-031']['deps']),
    ('PROC-034 无029', 'PROC-029' not in md_cases['PROC-034']['deps']),
    ('PROC-055 仅054', md_cases['PROC-055']['deps'] == {'PROC-054'}),
    ('PROC-121 弱依赖清空', md_cases['PROC-121']['weak'] == set()),
    ('PROC-031 Then 补断言', '预通知状态初始为未发送' in text.split('### PROC-032')[0].split('### PROC-031')[1]),
]
for pid in ('PROC-035','PROC-036','PROC-049','PROC-074','PROC-075','PROC-076','PROC-077'):
    checks.append((f'{pid} 分支声明', md_cases[pid]['branch_type']))

for name, ok in checks:
    if not ok:
        print('CHECK FAIL:', name); bad += 1

# 全库一致性: JSON 里 021/022/067/078/079 任何实例不得再有 008 根
for p in procs:
    base = re.sub(r'\.\d+$', '', p['temp_id'])
    if base in ('PROC-021','PROC-022','PROC-067','PROC-078','PROC-079'):
        for x in p['_S3_fields']['dependencies']:
            if x.startswith('PROC-008.'):
                print('RESIDUAL 008:', p['temp_id'], x); bad += 1

print('TOTAL MISMATCHES:', bad)
print('MD cases:', len(md_cases))
