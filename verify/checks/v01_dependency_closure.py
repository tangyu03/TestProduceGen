"""V01 依赖图健康：悬空引用（BLOCKER，含 PROC-T* 中间命名空间泄漏）、
依赖环（DAG）、依赖相位单调性（融合 regression_baseline 检查 4 与 10）。"""
import re
from collections import deque

from .base import CheckResult, get_procedures

CHECK_ID = "V01"
INTERMEDIATE_NS = re.compile(r"^PROC-T\d+-")


def _is_dag(nodes, edges):
    indeg = {n: 0 for n in nodes}
    adj = {n: [] for n in nodes}
    for a, b in edges:
        adj[a].append(b)
        indeg[b] += 1
    q = deque([n for n, d in indeg.items() if d == 0])
    seen = 0
    while q:
        n = q.popleft()
        seen += 1
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    return seen == len(nodes)


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="blocker", suspected_stage="S3",
                      suspected_files=["nodes/s3_dependency.py", "tools/graph_algo.py"])
    procs = get_procedures(output)
    ids = {p.get("temp_id") for p in procs}
    by_id = {p.get("temp_id"): p for p in procs}
    edges, ns_leak = [], set()

    for p in procs:
        pid = p.get("temp_id")
        s3 = p.get("_S3_fields", {}) or {}
        refs = set(s3.get("dependencies", []) or [])
        refs |= set((s3.get("dep_origins") or {}).keys())
        refs |= set((s3.get("weak_origins") or {}).keys())
        refs |= set(s3.get("weak_dependencies", []) or [])
        for r in refs:
            if not r:
                continue
            if r not in ids:
                res.fail({"kind": "dangling", "temp_id": pid, "dangling_ref": r})
                if INTERMEDIATE_NS.match(r):
                    ns_leak.add(r)
            elif r != pid:
                edges.append((r, pid))
        # 相位单调：依赖的 phase 不得高于自身（regression_baseline #4）
        my_phase = (p.get("_S2_fields", {}) or {}).get("phase", 0)
        for dep in s3.get("dependencies", []) or []:
            d = by_id.get(dep)
            if d and (d.get("_S2_fields", {}) or {}).get("phase", 0) > my_phase:
                res.fail({"kind": "phase_inversion", "temp_id": pid,
                          "my_phase": my_phase, "dep": dep,
                          "dep_phase": (d.get("_S2_fields", {}) or {}).get("phase")})

    if not _is_dag(list(ids), edges):
        res.fail({"kind": "cycle", "detail": "dependency graph contains cycle(s)"})
    if ns_leak:
        res.note = f"intermediate namespace leaked ({len(ns_leak)}): {sorted(ns_leak)[:10]}"
    return res
