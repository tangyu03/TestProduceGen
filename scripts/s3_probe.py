#!/usr/bin/env python3
"""S0→S3 probe harness (no LLM, no output translation).

Runs the graph up to S3 on a coverage model and reports dependency facts
for the three diagnostic procedures. Baseline probe — does NOT modify code.
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

from graph import compile_p3_graph
from models.state import AgentState


def initial_state(cm_path: str) -> AgentState:
    return {
        "messages": [],
        "coverage_model_path": cm_path,
        "primary_entity": None, "phase_table": None,
        "dep_state_phase_map": None, "contextual_phase_rules": None,
        "state_type_map": None, "dependent_entities": None,
        "entity_parent": None, "dependency_depth": None,
        "topology_levels": None, "virtual_entities": None,
        "transition_upstream_map": None,
        "coverage_model": None,
        "procedures": None, "br_classifications": None,
        "type5_filtered": None, "gen_seq_counter": 0,
        "sorted_procedures": None, "dependency_graph": None,
        "entity_instance_counts": None,
        "warnings": [], "current_stage": "init", "errors": [],
    }


def run(cm_path: str, focus: list[str] | None = None):
    app = compile_p3_graph()
    result = dict(initial_state(cm_path))
    for event in app.stream(result):
        for node_name, node_output in event.items():
            result.update(node_output)
    procs = result.get("procedures") or []
    # Focus probes by SOURCE_ID (PROC numbering is order-dependent and the
    # on-disk p3_agent_output may be stale vs current code).
    focus_sids = focus or ["T-ORG-004", "T-013[b]", "EO-CRU-007", "T-ORG-002"]
    print("=" * 70)
    for sid in focus_sids:
        hits = [p for p in procs if sid in (p.get("source_ids") or [])]
        if not hits:
            print(f"{sid}: NOT FOUND in S3 procedures")
            continue
        for p in hits[:1]:
            s2 = p.get("_S2_fields", {})
            s3 = p.get("_S3_fields", {})
            print(f"{sid} | {p.get('temp_id')} | {p.get('entity')} | {p.get('dimension')} | ot={p.get('obligation_type')}")
            print(f"  post={p.get('post_state')}")
            print(f"  phase={s2.get('phase')} sort_key={s2.get('sort_key')}")
            print(f"  deps={s3.get('dependencies')}")
            print(f"  weak={s3.get('weak_dependencies')}")
            print(f"  dep_origins={s3.get('dep_origins')}")
            print()
    # Aggregate: how many procs with empty deps, phase 0
    n = len(procs)
    empty = sum(1 for p in procs if not (p.get("_S3_fields") or {}).get("dependencies"))
    ph0 = sum(1 for p in procs if (p.get("_S2_fields") or {}).get("phase") == 0)
    print(f"TOTAL procs (S3): {n} | empty-deps: {empty} | phase0: {ph0}")
    # Phase histogram (by entity)
    from collections import Counter
    ph_by_ent: dict[str, Counter] = {}
    for p in procs:
        ent = p.get("entity", "?")
        ph = (p.get("_S2_fields") or {}).get("phase", 0)
        ph_by_ent.setdefault(ent, Counter())[ph] += 1
    print("phase histogram by entity:")
    for ent in sorted(ph_by_ent, key=lambda e: sum(ph_by_ent[e].values()), reverse=True):
        hist = dict(sorted(ph_by_ent[ent].items()))
        print(f"  {ent}: {hist}")
    return result


if __name__ == "__main__":
    cm_path = sys.argv[1] if len(sys.argv) > 1 else "P2_output.json"
    focus = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    run(cm_path, focus=focus)
