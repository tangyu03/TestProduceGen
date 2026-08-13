#!/usr/bin/env python3
"""A/B compare engine_state between a freshly-run output and a committed baseline.

Usage:
  python scripts/engine_state_ab.py <fresh_output.json> <committed_output.json>

Exits 0 iff all engine_state fields match (leaf_entity_ids compared order-insensitively).
"""
import json
import sys


def norm(v):
    # leaf_entity_ids was a set at runtime; JSON serializes to a list — order-insensitive.
    if isinstance(v, list) and all(isinstance(x, str) for x in v):
        return sorted(v)
    return v


def main() -> int:
    fresh_path, base_path = sys.argv[1], sys.argv[2]
    with open(fresh_path, encoding="utf-8") as f:
        fes = json.load(f).get("engine_state", {})
    with open(base_path, encoding="utf-8") as f:
        bes = json.load(f).get("engine_state", {})
    keys = sorted(set(fes) | set(bes))
    diffs = []
    for k in keys:
        if norm(fes.get(k)) != norm(bes.get(k)):
            diffs.append(k)
            print(f"[DIFF] {k}")
    print(
        f"engine_state fields: {len(keys)} total, "
        f"{len(keys) - len(diffs)} matched, {len(diffs)} diff"
    )
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
