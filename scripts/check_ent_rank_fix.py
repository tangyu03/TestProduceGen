"""Verify the _entity_order_rank fix (config-tail = relation-graph leaf only).

Re-sort the committed PT017 baseline procedures with recomputed sort_keys:
  - old logic: incoming={to} (the bug) — must reproduce the CURRENT order
    (新建用户 PROC-046 < 新增部门 PROC-122).
  - new logic: related={from}∪{to} (the fix) — must place 部门/角色 before 用户.

Uses the actual committed procedures (_S3 deps + _S2 sort_key) so S1 output is
identical; only ent_rank changes. Deterministic, no LLM.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nodes.s2_sorting import _entity_order_rank
from tools.graph_algo import topological_sort_procedures

ROOT = Path(__file__).resolve().parents[1]
CM_PATH = ROOT / "PT_017_coverage_obligations.json"
OUT_PATH = ROOT / "PT017_output.json"


def run(rank_fn, label):
    with open(CM_PATH, encoding="utf-8") as f:
        cm = json.load(f)
    with open(OUT_PATH, encoding="utf-8") as f:
        out = json.load(f)
    es = out["engine_state"]
    topo = es["topology_levels"]
    depth = es["dependency_depth"]
    rank = rank_fn(cm, topo, depth)

    procs = out["procedures"]
    # Rebuild sort_key[1] (ent_rank) with the given rank map; keep the rest.
    for p in procs:
        sk = list(p["_S2_fields"]["sort_key"])
        ent = p.get("entity", "")
        sk[1] = rank.get(ent, 900)
        p["_S2_fields"]["sort_key"] = sk

    ordered = topological_sort_procedures(procs)
    pos = {}
    for i, p in enumerate(ordered):
        pos[p["temp_id"]] = i
    return rank, pos, ordered


def locate(ordered, key):
    for p in ordered:
        t = p.get("title", "") or ""
        e = p.get("entity", "")
        if key in t:
            return p["temp_id"], e, t
    return None


def ent_rank_old(cm, topo, depth):
    """Replicate the PRE-fix logic (incoming = {to}) for comparison."""
    ctx = cm.get("_context", {})
    details = ctx.get("entity_details", []) or []
    relations = ctx.get("structural_relations", []) or []
    state_info = ctx.get("state_info", {}) or {}
    to_entities = {t.get("entity") for t in cm.get("transition_obligations", []) or []}

    incoming = {r.get("to") for r in relations if r.get("to")}
    config = set()
    for ed in details:
        eid = ed.get("id", "")
        ndim = len(state_info.get(eid, {}).get("dimensions", []) or [])
        if ndim == 0 and eid not in to_entities and eid not in incoming:
            config.add(eid)

    rank = {}
    non_config = [ed.get("id") for ed in details if ed.get("id") and ed.get("id") not in config]
    scored = []
    for eid in non_config:
        tl = topo.get(eid, 9)
        ndim = len(state_info.get(eid, {}).get("dimensions", []) or [])
        dims_lead = 0 if ndim >= 2 else 100
        dd = depth.get(eid, 9)
        scored.append((tl, dims_lead, dd, eid))
    scored.sort()
    for i, (_, _, _, eid) in enumerate(scored):
        rank[eid] = i
    off = len(scored)
    for i, eid in enumerate([ed.get("id") for ed in details if ed.get("id") in config]):
        rank[eid] = off + 10 + i
    for ed in details:
        if ed.get("name"):
            rank[ed["name"]] = rank.get(ed.get("id"), 900)
    return rank


if __name__ == "__main__":
    # ---- OLD logic ----
    rank_old, pos_old, ordered_old = run(ent_rank_old, "old")
    # ---- NEW logic (the fixed module function) ----
    rank_new, pos_new, ordered_new = run(_entity_order_rank, "new")

    print("=== entity rank map ===")
    for e in ["E-DEPT", "E-ROLE", "E-USER", "E-LOG", "E-CAR", "E-ARC"]:
        print(f"  {e}: old={rank_old.get(e, 'NA')}  new={rank_new.get(e, 'NA')}")

    print("\n=== order of key procedures ===")
    for label, pos, ordered in (("OLD", pos_old, ordered_old), ("NEW", pos_new, ordered_new)):
        user = locate(ordered, "新建用户")
        dept = locate(ordered, "新增部门")
        role = locate(ordered, "查询角色")
        log = locate(ordered, "查询登录日志")
        print(f"  [{label}]")
        print(f"    新建用户 (用户)   -> {user[0]} @ pos {pos[user[0]]}")
        print(f"    新增部门 (部门)   -> {dept[0]} @ pos {pos[dept[0]]}")
        print(f"    查询角色 (角色)   -> {role[0]} @ pos {pos[role[0]]}")
        print(f"    查询登录日志(日志)-> {log[0]} @ pos {pos[log[0]]}")
        print(f"    部门在用户之前? {pos[dept[0]] < pos[user[0]]}")
