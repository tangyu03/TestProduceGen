#!/usr/bin/env python3
"""v32 state_ref phase-bump real rerun check.

Runs S0→S3 on the coverage model with the CURRENT (modified) S1 code,
then:
  1. V01 gate: every dep's phase ≤ my phase (monotonicity), real graph.
  2. Dependency-graph diff vs on-disk p3_agent_output.json (old output),
     keyed by source_ids (temp_ids shift when phase ordering changes).
  3. Phase diff for the affected TOs.
"""
import json
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

from graph import compile_p3_graph
from models.state import AgentState
import scripts.s3_probe as probe  # reuse initial_state


def run_graph(cm_path: str) -> list:
    app = compile_p3_graph()
    result = dict(probe.initial_state(cm_path))
    for event in app.stream(result):
        for node_name, node_output in event.items():
            result.update(node_output)
    return result.get("procedures") or []


def old_map(path: str) -> dict:
    d = json.load(open(path, encoding="utf-8"))
    procs = d.get("procedures", d) if isinstance(d, dict) else d
    out: dict[str, dict] = defaultdict(lambda: {"phases": set(), "deps": set()})
    for p in procs:
        key = tuple(sorted(p.get("source_ids") or []))
        out[key]["phases"].add((p.get("_S2_fields") or {}).get("phase"))
        out[key]["deps"].update((p.get("_S3_fields") or {}).get("dependencies") or [])
    return out


def main(cm_path: str, old_path: str):
    new_procs = run_graph(cm_path)
    old = old_map(old_path)

    by_src: dict = defaultdict(list)
    for p in new_procs:
        by_src[tuple(sorted(p.get("source_ids") or []))].append(p)

    v01_viol = []
    # map temp_id -> phase (new)
    phase_of = {p["temp_id"]: (p.get("_S2_fields") or {}).get("phase", 0) for p in new_procs}
    for p in new_procs:
        my_ph = phase_of[p["temp_id"]]
        for dep in (p.get("_S3_fields") or {}).get("dependencies") or []:
            dp_ph = phase_of.get(dep)
            if dp_ph is not None and dp_ph > my_ph:
                v01_viol.append((p["temp_id"], p.get("source_ids"), my_ph, dep, dp_ph))
    print(f"V01 violations in REAL rerun: {len(v01_viol)}")
    for v in v01_viol[:15]:
        print("   ", v)

    # phase + dep diff per TO
    print("\n=== per-TO diff (old on-disk vs new real rerun) ===")
    focus = ["T-007[a]", "T-007[b]", "T-007[c]", "T-008[a]", "T-008[b]",
             "T-010[a]", "T-010[b]", "T-010[c]", "T-010[d]", "T-010[e]",
             "T-011", "T-012", "T-014"]
    for key, procs in sorted(by_src.items(), key=lambda kv: str(kv[0])):
        sid0 = key[0] if key else "?"
        if sid0 not in focus:
            continue
        new_phases = {(p.get("_S2_fields") or {}).get("phase") for p in procs}
        new_deps = set()
        for p in procs:
            new_deps.update((p.get("_S3_fields") or {}).get("dependencies") or [])
        new_dep_src = set()
        for p in new_procs:
            if p["temp_id"] in new_deps:
                new_dep_src.update(p.get("source_ids") or [])
        old_phases = old.get(key, {}).get("phases", set())
        old_dep_tids = old.get(key, {}).get("deps", set())
        old_dep_src = set()
        for p in new_procs:  # resolve old dep temp_ids via new graph numbering fallback
            pass
        # resolve old dep temp_ids using the OLD output's own mapping is not
        # possible here (temp ids differ); instead compare counts + phase
        ph_change = "SAME" if old_phases == new_phases else f"{sorted(old_phases)}->{sorted(new_phases)}"
        print(f"{sid0}: phase {ph_change} | new dep srcs={sorted(new_dep_src)}")

    # global dep-edge count diff (both sides per-procedure)
    old_procs = json.load(open(old_path, encoding="utf-8"))
    old_procs = old_procs.get("procedures", old_procs) if isinstance(old_procs, dict) else old_procs
    old_edge_total = sum(len((p.get("_S3_fields") or {}).get("dependencies") or []) for p in old_procs)
    new_edge_total = sum(len((p.get("_S3_fields") or {}).get("dependencies") or []) for p in new_procs)
    print(f"\ndep edges: old={old_edge_total} new={new_edge_total} (delta {new_edge_total-old_edge_total:+d})")

    # phase histogram delta (both sides per-procedure)
    old_hist = Counter((p.get("_S2_fields") or {}).get("phase", 0) for p in old_procs)
    new_hist = Counter((p.get("_S2_fields") or {}).get("phase", 0) for p in new_procs)
    print("phase histogram old :", dict(sorted(old_hist.items())))
    print("phase histogram new :", dict(sorted(new_hist.items())))

    # origin-type distribution (new) — how many edges per guard origin
    origin_counter = Counter()
    for p in new_procs:
        for o in ((p.get("_S3_fields") or {}).get("dep_origins") or {}).values():
            origin_counter[o] += 1
    print("new dep origins:", dict(sorted(origin_counter.items())))

    # resolve new deps of focus TOs to (source_id, action) for semantic eyeball
    tid_to_proc = {p["temp_id"]: p for p in new_procs}
    print("\n=== focus TO dep targets (new) ===")
    for key, procs in sorted(by_src.items(), key=lambda kv: str(kv[0])):
        sid0 = key[0] if key else "?"
        if sid0 not in focus:
            continue
        p0 = procs[0]
        deps = (p0.get("_S3_fields") or {}).get("dependencies") or []
        print(f"\n{sid0} (phase {(p0.get('_S2_fields') or {}).get('phase')}) deps:")
        for dep in deps:
            dp = tid_to_proc.get(dep, {})
            src = (dp.get("source_ids") or ["?"])[0]
            act = dp.get("when") or {}
            act = act.get("action", "") if isinstance(act, dict) else ""
            print(f"   {dep} <- src={src} action={act}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "coverage_obligations.json",
         sys.argv[2] if len(sys.argv) > 2 else "p3_agent_output.json")
