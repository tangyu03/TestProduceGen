#!/usr/bin/env python3
"""Edge-level diff old (on-disk p3 output) vs new (real S0→S3 rerun).

Normalizes edges by source-TO tuple to survive temp_id renumbering.
Lists added / removed edges (unique (src_TO_tuple, dep_TO_tuple)).
"""
import json
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

import scripts.v32_check as check


def edges_of(procs: list) -> set:
    tid_src = {p["temp_id"]: tuple(p.get("source_ids") or []) for p in procs}
    edges = set()
    for p in procs:
        src = tuple(p.get("source_ids") or [])
        for dep in (p.get("_S3_fields") or {}).get("dependencies") or []:
            dep_src = tid_src.get(dep, ())
            edges.add((src, dep_src))
    return edges


def main(cm_path: str, old_path: str):
    new_procs = check.run_graph(cm_path)
    old_procs = json.load(open(old_path, encoding="utf-8"))
    old_procs = old_procs.get("procedures", old_procs) if isinstance(old_procs, dict) else old_procs

    old_e = edges_of(old_procs)
    new_e = edges_of(new_procs)
    added = new_e - old_e
    removed = old_e - new_e

    print(f"old edges: {len(old_e)} | new edges: {len(new_e)} | added: {len(added)} | removed: {len(removed)}")

    # map TO id -> action for readability
    cmd = json.load(open(cm_path, encoding="utf-8"))
    act = {t["id"]: (t.get("action") or "") for t in cmd.get("transition_obligations", [])}

    print("\n=== ADDED edges ===")
    for (src, dep) in sorted(added, key=lambda e: str(e)):
        s = "+".join(f"{s}({act.get(s,'?')[:18]})" for s in src)
        d = "+".join(f"{s}({act.get(s,'?')[:18]})" for s in dep)
        print(f"  {s}  ->  {d}")

    print("\n=== REMOVED edges ===")
    for (src, dep) in sorted(removed, key=lambda e: str(e)):
        s = "+".join(src)
        d = "+".join(dep)
        print(f"  {s}  ->  {d}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "coverage_obligations.json",
         sys.argv[2] if len(sys.argv) > 2 else "p3_agent_output.json")
