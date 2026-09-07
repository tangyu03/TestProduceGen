# -*- coding: utf-8 -*-
"""v13 评审 11 项 + 衍生修正断言（内容键控：按 source_ids 解析 proc，不依赖编号）
+ 全库 deps/weak diff（再生版 vs 手工补丁基线，内容键对齐）。"""
import json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

NEW = json.load(open('pt_outputv13.json', encoding='utf-8'))
OLD = json.load(open('.ab_tmp/patched_baseline/pt_outputv13.json', encoding='utf-8'))

def by_base(doc):
    out = {}
    for p in doc['procedures']:
        out.setdefault(re.sub(r'\.\d+$', '', p['temp_id']), []).append(p)
    return out

NB, OB = by_base(NEW), by_base(OLD)
fails, passes = [], []

def check(name, cond, detail=""):
    (passes if cond else fails).append(f"{'PASS' if cond else 'FAIL'} {name} {detail}")

# ── 内容键解析：首 source_id → base temp_id（每文档独立解析）──
def make_resolver(buckets):
    res = {}
    dup = []
    for b, ps in buckets.items():
        sid = (ps[0].get('source_ids') or ['?'])[0]
        if sid in res:
            dup.append(sid)
        res[sid] = b
    return res, dup

NRES, NDUP = make_resolver(NB)
ORES, ODUP = make_resolver(OB)
if NDUP or ODUP:
    print("WARN duplicated first-source ids:", set(NDUP) | set(ODUP))

def B(sid, res=NRES):
    """sid → base id（如 'T-005' → 'PROC-012'）；带基名直接查。"""
    if res.get(sid):
        return res[sid]
    raise KeyError(f"no proc with first source {sid}")

def deps_of(sid, res=NRES):
    b = B(sid, res)
    return [set(p.get('_S3_fields', {}).get('dependencies', [])) for p in NB[b]]

def weak_of(sid):
    b = B(sid)
    return [set(p.get('_S3_fields', {}).get('weak_dependencies', [])) for p in NB[b]]

def D(sid):
    """deps 集合化到 base 级：{PROC-017.1,...} → {'T-002'} 内容键集合"""
    out = []
    for s in deps_of(sid):
        keys = set()
        for d in s:
            base = re.sub(r'\.\d+$', '', d)
            ps = NB.get(base) or []
            keys.add((ps[0].get('source_ids') or ['?'])[0] if ps else base)
        out.append(keys)
    return out

def has_all(sid, wanted_sids):
    want = set(wanted_sids)          # D() 返回内容键（source_id），直接比对
    return all(want <= s for s in D(sid))

def has_none(sid, banned_sids):
    ban = set(banned_sids)
    return all(not (ban & s) for s in D(sid))

def exact(sid, wanted_sids):
    want = set(wanted_sids)
    return bool(D(sid)) and all(s == want for s in D(sid))

def all_instances(sid, pred):
    ps = NB[B(sid)]
    return bool(ps) and all(pred(p) for p in ps)

def branch_given(p):
    return any(g.get('given_type') == 'branch' and '项目类型' in str(g.get('description', ''))
               for g in (p.get('givens') or []))

# ══ 二 依赖链断裂 ═══════════════════════════════════════════
check("二① T-005/T-004 ⊇ T-002", has_all('T-005', ['T-002']) and has_all('T-004', ['T-002']),
      f"{D('T-005')} {D('T-004')}")
check("二② T-008(EO缴费) ⊇ T-008? -> 052⊇049", has_all('EO-CRU-017', ['T-008']), f"{D('EO-CRU-017')}")
check("二③ EO提交结果 ⊇ T-015", has_all('EO-CRU-016', ['T-015']), f"{D('EO-CRU-016')}")
check("二④ EO上传结果通知单/证书 ⊇ T-037,T-067",
      has_all('EO-CRU-009', ['T-037', 'T-067']) and has_all('EO-CRU-010', ['T-037', 'T-067']),
      f"{D('EO-CRU-009')} {D('EO-CRU-010')}")
check("二⑤ EO文件整理 ⊇ T-039", has_all('EO-CRU-004', ['T-039']), f"{D('EO-CRU-004')}")

# ══ 三 测量审核通知链 ═══════════════════════════════════════
EXPECT3 = {'T-046': ['T-040'], 'T-048': ['T-040', 'T-046'], 'T-049': ['T-040', 'T-048'],
           'T-047': ['T-040', 'T-046', 'T-049'], 'T-050': ['T-040', 'T-047']}
for sid, want in EXPECT3.items():
    check(f"三 {sid}=={want}", exact(sid, want), f"{D(sid)}")
check("三 通知链无 T-007 边", has_none('T-046', ['T-007']) and has_none('T-048', ['T-007'])
      and has_none('T-049', ['T-007']) and has_none('T-047', ['T-007']) and has_none('T-050', ['T-007']))
p31 = (NB[B('T-040')] or [{}])[0]
check("三 T-040 Then 含预通知状态初始为未发送",
      any('预通知状态初始为未发送' in str(t.get('expectation', '')) for t in p31.get('thens', [])))
check("三 不新增初始化用例(proc数一致)", len(NEW['procedures']) == len(OLD['procedures']),
      f"{len(NEW['procedures'])} vs {len(OLD['procedures'])}")
p54 = (NB[B('T-006')] or [{}])[0]
check("三 T-006(缴费通知单) 不挂通知链",
      not ({B('T-040'), B('T-046'), B('T-007')} & set(p54.get('_S3_fields', {}).get('dependencies', []))),
      str(p54.get('_S3_fields', {}).get('dependencies')))

# ══ 四 冗余/错挂 ═══════════════════════════════════════════
check("四① T-062=={T-061}", exact('T-062', ['T-061']), f"{D('T-062')}")
check("四② T-034 含T-033 不含T-035", has_all('T-034', ['T-033']) and has_none('T-034', ['T-035']),
      f"{D('T-034')}")
check("四③ T-003/T-040/T-041 ∌ T-057",
      has_none('T-003', ['T-057']) and has_none('T-040', ['T-057']) and has_none('T-041', ['T-057']),
      f"{D('T-003')} {D('T-040')} {D('T-041')}")
for sid in ('T-009', 'T-030', 'T-008', 'T-021', 'T-025', 'T-026', 'T-027'):
    check(f"四④ {sid} 分支Given", all_instances(sid, branch_given),
          f"{B(sid)} givens={[g.get('given_type') for g in NB[B(sid)][0].get('givens', [])]}")
check("四⑤ RO-BR-002 weak==∅", all(s == set() for s in weak_of('RO-BR-002')), f"{weak_of('RO-BR-002')}")
check("四⑥ EO编制缴费通知=={T-006}", exact('EO-CRU-038', ['T-006']), f"{D('EO-CRU-038')}")

# ══ 衍生修正（统一口径）════════════════════════════════════
check("衍生 T-005/T-004 =={T-001,T-002,T-054}",
      exact('T-005', ['T-001', 'T-002', 'T-054']) and exact('T-004', ['T-001', 'T-002', 'T-054']),
      f"{D('T-005')} {D('T-004')}")
check("衍生 T-007 =={T-001}", exact('T-007', ['T-001']), f"{D('T-007')}")
check("衍生 T-042/T-043 =={T-054,T-040}",
      exact('T-042', ['T-054', 'T-040']) and exact('T-043', ['T-054', 'T-040']),
      f"{D('T-042')} {D('T-043')}")
check("衍生 T-032[a] ∌ T-025/T-027", has_none('T-032[a]', ['T-025', 'T-027']), f"{D('T-032[a]')}")
check("衍生 T-054 ∌ T-053", has_none('T-054', ['T-053']), f"{D('T-054')}")
for sid in ('T-030', 'T-015', 'T-021', 'T-025', 'T-026', 'T-027', 'T-036'):
    check(f"衍生 {sid} 组合根T-001", has_all(sid, ['T-001']) and has_none(sid, ['T-007']), f"{D(sid)}")
check("衍生 EO缴费/提交结果 ∌ T-007", has_none('EO-CRU-017', ['T-007']) and has_none('EO-CRU-016', ['T-007']))

# ══ 全库 diff（内容键对齐）════════════════════════════════
print('=' * 72)
print('FULL DIFF (content-keyed, regenerated vs patched baseline):')
KEY2NEW = {}
for b, ps in NB.items():
    KEY2NEW[(ps[0].get('source_ids') or ['?'])[0]] = b

def content_deps(doc_buckets, sid):
    b = None
    for bb, ps in doc_buckets.items():
        if (ps[0].get('source_ids') or ['?'])[0] == sid:
            b = bb
            break
    if b is None:
        return None, None
    ds = [set(p.get('_S3_fields', {}).get('dependencies', [])) for p in doc_buckets[b]]
    ws = [set(p.get('_S3_fields', {}).get('weak_dependencies', [])) for p in doc_buckets[b]]
    keys = []
    for s in ds:
        kk = set()
        for d in s:
            base = re.sub(r'\.\d+$', '', d)
            ps = doc_buckets.get(base) or []
            kk.add((ps[0].get('source_ids') or ['?'])[0] if ps else base)
        keys.append(kk)
    return keys, (set().union(*ws) if ws else set())

all_sids = sorted(set(NRES) | set(ORES))
for sid in all_sids:
    nk, nw = content_deps(NB, sid)
    ok, ow = content_deps(OB, sid)
    if nk is None or ok is None:
        print(f"  {sid}: MISSING in {'NEW' if nk is None else 'OLD'}")
        continue
    nu, ou = set().union(*nk), set().union(*ok)
    if nu != ou:
        origins = {}
        b = KEY2NEW.get(sid)
        for p in NB.get(b, []):
            origins.update(p.get('_S3_fields', {}).get('dep_origins', {}))
        base2sid = {}
        for bb, ps in NB.items():
            base2sid[bb] = (ps[0].get('source_ids') or ['?'])[0]
        add = {base2sid.get(re.sub(r'\.\d+$', '', d), d) for d in (nu - ou)}
        rem = {base2sid.get(re.sub(r'\.\d+$', '', d), d) for d in (ou - nu)}
        oinfo = ' '.join(f"{base2sid.get(re.sub(r'[.].*$', '', d), d)}:{origins.get(d, '?')[:16]}"
                         for d in sorted(nu - ou))
        print(f"  {sid}: NEW={sorted(add | (nu & ou))}")
        print(f"           OLD={sorted(rem | (nu & ou))}")
        if add:
            print(f"           + {sorted(add)}   origins: {oinfo}")
        if rem:
            print(f"           - {sorted(rem)}")
    if nw != ow:
        print(f"  {sid} WEAK: NEW={sorted(nw)} OLD={sorted(ow)}")

print('=' * 72)
print(f"PASS {len(passes)}  FAIL {len(fails)}")
for f in fails:
    print(' ', f)
sys.exit(1 if fails else 0)
