#!/usr/bin/env python3
"""Tier 2 确定性双跑 (手off §5) — 输出 S0→S3 业务数据规范化的 JSON 到 stdout.

用法 (须以不同 PYTHONHASHSEED 各跑一次, 外部 diff):
  PYTHONIOENCODING=utf-8 PYTHONHASHSEED=0 python -X utf8 -m scripts.tier2_determinism
  PYTHONIOENCODING=utf-8 PYTHONHASHSEED=999 python -X utf8 -m scripts.tier2_determinism
  两份输出应 byte-identical。
"""
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

    # 只取业务相关字段, 按确定性顺序输出 (不依赖 hash 序的 set/dict 遍历)
    rows = []
    for p in sorted(procs, key=lambda x: x["temp_id"]):
        s2 = p.get("_S2_fields") or {}
        s3 = p.get("_S3_fields") or {}
        rows.append({
            "temp_id": p["temp_id"],
            "entity": p.get("entity"),
            "obligation_type": p.get("obligation_type"),
            "source_ids": sorted(p.get("source_ids") or []),
            "givens": [{"target": g.get("target"), "state": g.get("state"),
                        "description": g.get("description")} for g in (p.get("givens") or [])],
            "phase": s2.get("phase"),
            "phase_basis": s2.get("phase_basis"),
            "dependencies": sorted(s3.get("dependencies") or []),
        })
    print(json.dumps({"rows": rows}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "coverage_obligations.json")
