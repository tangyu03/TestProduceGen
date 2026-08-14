#!/usr/bin/env python3
"""AST-based field diff between two srs_data builder files.

Reports, per construct type:
  - kwargs present in PT017.py but absent in V1   (后者有、前者没有)
  - kwargs present in V1 but absent in PT017.py   (前者有、后者没有)
Also digs into nested dict fields: state_dimensions dimension keys,
op/trans/precond note dict keys, prohibition_config keys.
"""
import ast, sys
from collections import Counter, defaultdict

V1, B = sys.argv[1], sys.argv[2]


def analyze(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    kw = defaultdict(Counter)          # target -> kwarg -> count
    npos = defaultdict(Counter)        # target -> nargs -> count
    dim_keys = defaultdict(Counter)    # 'state_dimensions' dimension-level keys
    state_keys = Counter()             # keys of per-state dicts inside dimensions
    note_keys = Counter()              # keys of note/__note dicts
    br_keys = Counter()                # keys of branch dicts inside add_branch_dimension
    note_depth = 0

    def walk(node, dim=False):
        nonlocal note_depth
        if isinstance(node, ast.Call):
            f = node.func
            target = None
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "m":
                target = "m." + f.attr
            elif isinstance(f, ast.Name) and f.id in ("attr", "op", "precond", "state_ref", "N"):
                target = f.id
            if target:
                for k in node.keywords:
                    if k.arg is None:
                        continue
                    kw[target][k.arg] += 1
                    if k.arg == "note" and isinstance(k.value, ast.Dict):
                        note_keys.update(_dict_keys(k.value))
                    if k.arg == "state_dimensions" and isinstance(k.value, ast.List):
                        for el in k.value.elts:
                            if isinstance(el, ast.Dict):
                                dim_keys[target].update(_dict_keys(el))
                                for key, val in zip(el.keys, el.values):
                                    if isinstance(key, ast.Constant) and key.value == "states" and isinstance(val, ast.List):
                                        for st in val.elts:
                                            if isinstance(st, ast.Dict):
                                                state_keys.update(_dict_keys(st))
                    if k.arg == "branches" and isinstance(k.value, ast.List):
                        for el in k.value.elts:
                            if isinstance(el, ast.Dict):
                                br_keys.update(_dict_keys(el))
                    if k.arg == "dict" and isinstance(k.value, ast.Dict):  # set_prohibition_config
                        pass
                npos[target][len(node.args)] += 1
        for child in ast.iter_child_nodes(node):
            walk(child)
    walk(tree)
    return kw, npos, dim_keys, state_keys, note_keys, br_keys


def _dict_keys(d):
    out = []
    for k, v in zip(d.keys, d.values):
        if isinstance(k, ast.Constant):
            out.append(k.value)
    return out


ka, pa, da, sa, na, ba = analyze(V1)
kb, pb, db, sb, nb, bb = analyze(B)

print("=" * 70)
print(f"前者 V1        = {V1}")
print(f"后者 PT017     = {B}")
print("=" * 70)

# 1. prohibition_config / DomainModel-level
print("\n== 1. DomainModel / set_prohibition_config ==")
for t in sorted(set(ka) | set(kb)):
    if t in ("m.add_entity", "m.add_trans", "m.add_structural", "m.add_causal",
             "m.add_xc", "m.add_br", "m.add_branch_dimension", "m.add_role",
             "m.add_permission", "m.set_prohibition_config", "attr", "op",
             "precond", "state_ref", "N"):
        continue
    print(f"  {t}: V1={dict(ka[t])} PT017={dict(kb[t])}")

# 2. roles positional args
print("\n== 2. m.add_role positional args ==")
print(f"  V1: nargs={dict(pa.get('m.add_role', Counter()))}")
print(f"  PT017: nargs={dict(pb.get('m.add_role', Counter()))}")

# 3. main constructs
print("\n== 3. 构造字段（仅列出有差异的） ==")
for t in ["m.add_entity", "m.add_trans", "m.add_structural", "m.add_causal",
          "m.add_xc", "m.add_br", "m.add_branch_dimension", "m.add_permission",
          "attr", "op", "precond", "state_ref"]:
    a, b = ka.get(t, Counter()), kb.get(t, Counter())
    only_b = {k: v for k, v in b.items() if k not in a}
    only_a = {k: v for k, v in a.items() if k not in b}
    both_diff = {k: (a[k], b[k]) for k in a if k in b and a[k] != b[k]}
    print(f"\n### {t}  (V1={sum(a.values())} 调用, PT017={sum(b.values())} 调用)")
    if only_b:
        print(f"  [后者有、前者没有] {only_b}")
    if only_a:
        print(f"  [前者有、后者没有] {only_a}")
    if both_diff:
        print(f"  [两者都有、次数不同] {both_diff}")
    if not (only_b or only_a or both_diff):
        print("  (字段集完全一致)")

# 4. state_dimensions dimension-level keys
print("\n== 4. state_dimensions 维度级字段 ==")
a, b = da.get("m.add_entity", Counter()), db.get("m.add_entity", Counter())
only_b = {k: v for k, v in b.items() if k not in a}
only_a = {k: v for k, v in a.items() if k not in b}
print(f"  [后者有、前者没有] {only_b}")
print(f"  [前者有、后者没有] {only_a}")

print("\n== 4b. state 字典级字段（V1 的 per-state dict / PT017 的字符串 states） ==")
print(f"  V1 per-state dict keys: {dict(sa)}")
print(f"  PT017: (states 为字符串, 无 per-state dict) {dict(sb)}")

# 5. note dict fields
print("\n== 5. note dict 字段（op/trans/precond 全部合并） ==")
print(f"  V1 note keys: {dict(na)}")
print(f"  PT017 note keys: {dict(nb)}")

# 6. branch dict fields
print("\n== 6. add_branch_dimension branches dict 字段 ==")
print(f"  V1 branch keys: {dict(ba)}")
print(f"  PT017 branch keys: {dict(bb)}")

# 7. set_prohibition_config keys
print("\n== 7. set_prohibition_config dict keys ==")
for path, tag in ((V1, "V1"), (B, "PT017")):
    tree = ast.parse(open(path, encoding="utf-8").read())
    keys = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
           and node.func.attr == "set_prohibition_config":
            for k in node.keywords:
                if k.arg == "config" and isinstance(k.value, ast.Dict):
                    keys = [x.value for x in k.value.keys if isinstance(x, ast.Constant)]
                if k.arg is None and isinstance(k.value, ast.Dict):
                    keys = [x.value for x in k.value.keys if isinstance(x, ast.Constant)]
    print(f"  {tag}: {keys}")
