#!/usr/bin/env python3
"""Ground-truth harness: call the REAL _identify_primary_entity with REAL data,
under candidate data-transformations, for both gold projects.

No reimplementation of the fusion logic — the real function runs on real data.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from nodes.s0_topology import _identify_primary_entity, _load_relations  # noqa: E402


def load_cm(path: Path) -> dict:
    cm = json.load(open(path, encoding="utf-8"))
    raw = cm.get("coverage_model")
    return raw if raw is not None else cm


def fuse(cm: dict, transform: str):
    """Run the real fusion with a data-transform applied."""
    tos = cm.get("transition_obligations", [])
    eos = cm.get("entity_obligations", [])
    state_info = cm.get("_context", {}).get("state_info", {}) if isinstance(cm, dict) else {}

    structural, transition = _load_relations(cm)

    # ── candidate data-transformations ──
    if transform == "baseline":
        pass
    elif transform == "struct-filter":  # exclude configuration_source edges
        structural = [
            r for r in structural
            if r.get("ownership_dimension") != "configuration_source"
        ]
    elif transform == "struct-filter+to-side":  # struct-filter AND causal counts to-side too
        structural = [
            r for r in structural
            if r.get("ownership_dimension") != "configuration_source"
        ]
        transition = [dict(t, **{"_count_to_side": True}) for t in transition]
    elif transform == "causal-degree":  # causal counts to-side too (degree)
        transition = [dict(t, **{"_count_to_side": True}) for t in transition]
    else:
        raise ValueError(transform)

    # causal to-side: count each (from,to) causal edge on BOTH sides
    if any(t.get("_count_to_side") for t in transition):
        # rebuild: for each edge, add a reversed from/to so from-side count picks up sinks
        expanded = []
        for t in transition:
            expanded.append(t)
            rev = dict(t)
            if t.get("from") and t.get("to") and t.get("from") != t.get("to"):
                rev["from"] = t.get("to")
                rev["to"] = t.get("from")
                rev["_rev"] = True
                expanded.append(rev)
        transition = expanded

    primary = _identify_primary_entity(structural, transition, tos, eos, state_info=state_info)
    return primary


def main():
    cases = [
        ("PT017", Path(ROOT) / "PT017_coverage_obligations.json"),
        ("review", Path(ROOT) / "coverage_obligations.json"),
    ]
    transforms = ["baseline", "struct-filter", "causal-degree", "struct-filter+to-side"]
    for name, path in cases:
        cm = load_cm(path)
        for tf in transforms:
            try:
                p = fuse(cm, tf)
            except Exception as e:
                p = f"ERR {e!r}"
            print(f"{name:7s} {tf:22s} primary={p}")


if __name__ == "__main__":
    main()
