# -*- coding: utf-8 -*-
import json, re
d = json.load(open('pt_outputv13.json', encoding='utf-8'))
procs = d['procedures']
by_base = {}
for p in procs:
    base = re.sub(r'\.\d+$', '', p['temp_id'])
    by_base.setdefault(base, []).append(p)

def show(pid):
    ps = by_base.get(pid)
    if not ps:
        print(pid, 'NOT FOUND'); return
    p = ps[0]
    print(pid, 'x%d' % len(ps), '| src:', p.get('source_ids'), '| ent:', p.get('entity'), '| dim:', p.get('dimension'))
    print('   post:', p.get('post_state'), '| when:', (p.get('when') or {}).get('action'))
    for x in p.get('givens', []):
        print('   given:', x.get('given_type'), '|', (x.get('description') or '')[:40], '| state_ref:', x.get('state_ref'))
    s3 = p.get('_S3_fields', {})
    print('   deps:', s3.get('dependencies'))
    print('   origins:', s3.get('dep_origins'))
    print('   weak:', s3.get('weak_dependencies'), '| worigins:', s3.get('weak_origins'))
    for t in p.get('thens', [])[:8]:
        print('   then:', t.get('target'), '|', (t.get('expectation') or '')[:40], '| kind:', t.get('kind'))
    print()

for pid in ['PROC-008', 'PROC-031', 'PROC-021', 'PROC-022', 'PROC-067', 'PROC-078', 'PROC-079',
            'PROC-030', 'PROC-029', 'PROC-034', 'PROC-052', 'PROC-049', 'PROC-066', 'PROC-059',
            'PROC-070', 'PROC-068', 'PROC-069', 'PROC-081', 'PROC-080', 'PROC-012', 'PROC-013',
            'PROC-017', 'PROC-055', 'PROC-054', 'PROC-056', 'PROC-005', 'PROC-019', 'PROC-089',
            'PROC-084', 'PROC-085', 'PROC-121', 'PROC-011']:
    show(pid)
