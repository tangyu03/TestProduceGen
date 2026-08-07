#!/usr/bin/env python3
"""⑤ probe — dump 当前被 phase-inversion 降级为 weak 的边, 及其被依赖 TO 的 direction."""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

from graph import compile_p3_graph
import scripts.s3_probe as probe


def main(cm_path: str):
    app = compile_p3_graph()
    result = dict(probe.initial_state(cm_path))
    for event in app.stream(result):
        for n, out in event.items():
            result.update(out)
    procs = result.get("procedures") or []
    cm = result.get("coverage_model") or {}
    to_by_id = {t["id"]: t for t in cm.get("transition_obligations", [])}
    to_by_tid = {t["transition_id"]: t for t in cm.get("transition_obligations", [])
                 if t.get("transition_id")}

    def resolve(sid):
        t = to_by_id.get(sid) or to_by_tid.get(sid)
        if t:
            return t
        base = sid[:-1] if sid and sid[-1].isalpha() else sid
        return to_by_id.get(base) or to_by_tid.get(base)

    rows = []
    for p in sorted(procs, key=lambda x: x["temp_id"]):
        s3 = p.get("_S3_fields", {})
        my_phase = (p.get("_S2_fields") or {}).get("phase", 0)
        for wd, origin in (s3.get("weak_origins") or {}).items():
            if origin != "transition_upstream_phase_inversion":
                continue
            dep = next((q for q in procs if q["temp_id"] == wd), None)
            dep_srcs = dep.get("source_ids") or [] if dep else []
            dep_phase = (dep.get("_S2_fields") or {}).get("phase", 0) if dep else "?"
            # resolve the dep's TOs and their directions
            dirs = sorted({(resolve(s) or {}).get("direction") for s in dep_srcs} - {None})
            rows.append({
                "proc": p["temp_id"], "proc_src": sorted(p.get("source_ids") or []),
                "my_phase": my_phase,
                "weak_dep": wd, "dep_src": sorted(dep_srcs),
                "dep_phase": dep_phase,
                "dep_dir": dirs,
            })
    print(f"=== weak phase_inversion edges: {len(rows)} ===")
    for r in rows:
        print(f"  {r['proc']}(P{r['my_phase']}) src={r['proc_src']} "
              f"-> WEAK {r['weak_dep']}(P{r['dep_phase']}) src={r['dep_src']} dir={r['dep_dir']}")
    # summary by direction
    from collections import Counter
    c = Counter(tuple(r["dep_dir"]) for r in rows)
    print("\n=== by dep direction ===")
    for k, v in sorted(c.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "coverage_obligations.json")
