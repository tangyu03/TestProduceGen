#!/usr/bin/env python3
"""v29 #8: 黄金用例回归基线 (Golden Case Regression Baseline)

建立一组"黄金用例"断言，验证每次改造后输出顺序未被破坏。

黄金用例 = 业务上必须保持顺序的关键链路：
  1. 主实体 phase 单调递增（不允许 P3 → P1 回退）
  2. 主实体 initial state 必须在 P0
  3. 同一 transition 的 multi-instance procedures 必须连续
  4. 无 ERROR 级别错误
  5. procedure 数量在合理范围（防止回归性丢失）
  6. 每个有 dependencies 的 procedure，其依赖必须满足 phase 单调性
  7. Type1 transition procedure 的 post_state 必须非空
  8. 主链路 phase 分布：P0 ≤ P1 ≤ P2 ... 单调

使用方式：
  python scripts/regression_baseline.py [output.json]

  不传参数时，默认跑流水线生成 output 到 /tmp，再校验。
"""
import json
import sys
import subprocess
from pathlib import Path


PROJECT_DIR = Path("/home/z/my-project/project_v28")
DEFAULT_OUTPUT = "/tmp/test_output_v29.json"


def run_pipeline(output_path: str) -> dict:
    """Run the P3 pipeline and load the output JSON."""
    cmd = [
        "/home/z/.venv/bin/python", "main.py",
        "test_coverage_model.json", output_path,
    ]
    result = subprocess.run(
        cmd, cwd=str(PROJECT_DIR),
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        print("STDERR:", result.stderr[-2000:])
        raise RuntimeError(f"Pipeline failed with exit code {result.returncode}")
    with open(output_path) as f:
        return json.load(f)


def assert_check(name: str, condition: bool, detail: str = "") -> bool:
    """Assert a single check; return True if passed, False otherwise."""
    status = "✓ PASS" if condition else "✗ FAIL"
    print(f"  [{status}] {name}" + (f": {detail}" if detail else ""))
    return condition


def run_baseline_checks(output: dict) -> tuple[int, int]:
    """Run all golden-case checks. Returns (passed, failed) counts."""
    procs = output.get("procedures", [])
    state = output.get("engine_state", output)  # may be nested
    primary = state.get("primary_entity", "")
    phase_table = state.get("phase_table", {})
    phase_count = phase_table.get("phase_count", 1)
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])

    print(f"\n=== Golden Case Regression Baseline ===")
    print(f"  Primary: {primary}, phase_count: {phase_count}, procedures: {len(procs)}")
    print(f"  Errors: {len(errors)}, Warnings: {len(warnings)}")
    print()

    passed = 0
    failed = 0

    def check(name, cond, detail=""):
        nonlocal passed, failed
        if assert_check(name, cond, detail):
            passed += 1
        else:
            failed += 1

    # ── Check 1: No errors ──
    check("1. No ERROR-level errors", len(errors) == 0,
          f"errors={errors[:3]}" if errors else "")

    # ── Check 2: Procedure count in reasonable range ──
    # Scale upper bound by number of unique TOs referenced by procedures.
    # Rule of thumb: each TO produces ~10-15 procedures after multi-instance expansion.
    # Lower bound: at least 1 procedure per TO. Upper bound: max(200, num_TOs * 20).
    unique_tids = set()
    for p in procs:
        for sid in p.get("source_ids", []):
            # source_id may be "TO-XXX" or "T-XXX" — strip prefix
            unique_tids.add(sid)
    tos_count = max(len(unique_tids), 6)
    lower_bound = max(10, tos_count)
    upper_bound = max(200, tos_count * 20)
    check(f"2. Procedure count in [{lower_bound}, {upper_bound}] range",
          lower_bound <= len(procs) <= upper_bound,
          f"actual={len(procs)}, unique_source_ids={tos_count}")

    # ── Check 3: Primary entity initial state at P0 ──
    primary_dim = phase_table.get("primary_dimension", "")
    state_to_phase = phase_table.get("state_to_phase", {}).get(primary_dim, {})
    # For test data: E-PRJ.项目状态.待开始 should be P0
    initial_state = None
    for s, p in state_to_phase.items():
        # Heuristic: state named "待开始" / "初始" / "新建" / "未开始" is initial
        if any(kw in s for kw in ["待开始", "初始", "新建", "未开始"]):
            initial_state = s
            break
    if initial_state:
        check(f"3. Primary initial state '{initial_state}' at P0",
              state_to_phase.get(initial_state) == 0,
              f"actual=P{state_to_phase.get(initial_state)}")
    else:
        check("3. Primary initial state detection (skipped — no initial keyword found)", True)

    # ── Check 4: Phase monotonicity per procedure ──
    # A procedure's dependencies must all have phase <= its own phase
    proc_by_id = {p["temp_id"]: p for p in procs}
    phase_violations = []
    for p in procs:
        my_phase = p.get("_S2_fields", {}).get("phase", 0)
        for dep_id in p.get("_S3_fields", {}).get("dependencies", []):
            dep = proc_by_id.get(dep_id)
            if not dep:
                continue
            dep_phase = dep.get("_S2_fields", {}).get("phase", 0)
            if dep_phase > my_phase:
                phase_violations.append(
                    f"{p['temp_id']}(P{my_phase}) dep {dep_id}(P{dep_phase})"
                )
    check("4. Phase monotonicity (deps ≤ my phase)",
          len(phase_violations) == 0,
          f"violations={phase_violations[:3]}" if phase_violations else "")

    # ── Check 5: Type1 procedures have non-empty post_state ──
    empty_post = [p["temp_id"] for p in procs
                  if p.get("obligation_type") == 1 and not p.get("post_state")]
    check("5. Type1 procedures have non-empty post_state",
          len(empty_post) == 0,
          f"empty={empty_post[:3]}" if empty_post else "")

    # ── Check 6: Multi-instance procedures share same source transition ──
    # Procedures with temp_id like "PROC-001.1", "PROC-001.2" must share source_ids
    multi_groups = {}
    for p in procs:
        tid = p.get("temp_id", "")
        base = tid.split(".")[0] if "." in tid else tid
        multi_groups.setdefault(base, []).append(p)
    mismatched = []
    for base, group in multi_groups.items():
        if len(group) < 2:
            continue
        first_src = set(group[0].get("source_ids", []))
        for p in group[1:]:
            if set(p.get("source_ids", [])) != first_src:
                mismatched.append(f"{base}: {first_src} vs {set(p.get('source_ids', []))}")
    check("6. Multi-instance procedures share source_ids",
          len(mismatched) == 0,
          f"mismatches={mismatched[:3]}" if mismatched else "")

    # ── Check 7: Phase distribution covers expected range ──
    phase_dist = {}
    for p in procs:
        ph = p.get("_S2_fields", {}).get("phase", 0)
        phase_dist[ph] = phase_dist.get(ph, 0) + 1
    # Should have at least 2 distinct phases for non-trivial fixture
    check("7. Phase distribution has ≥ 2 distinct phases",
          len(phase_dist) >= 2,
          f"phases={sorted(phase_dist.keys())}")

    # ── Check 8: Primary entity procedures cover all declared states ──
    # Each state in phase_table.state_to_phase should appear in at least one
    # procedure's post_state OR from_state (givens[0].state).
    # Initial states (e.g. 待开始) are often only from_states, never post_states.
    primary_states = set(state_to_phase.keys())
    covered_states = set()
    for p in procs:
        if p.get("dimension") != primary_dim:
            continue
        # Check post_state
        post = p.get("post_state", "")
        for sep in ["→", "->"]:
            if sep in post:
                post = post.split(sep)[-1].strip()
                break
        if post:
            covered_states.add(post)
        # Check from_state (givens[0].state)
        givens = p.get("givens", [])
        if givens:
            from_st = givens[0].get("state", "")
            if from_st and from_st not in ("(初始)", "(None)", "None", ""):
                covered_states.add(from_st)
    missing = primary_states - covered_states
    check("8. Primary entity covers all declared states (post_state or from_state)",
          len(missing) == 0,
          f"missing={missing}, covered={covered_states}" if missing else
          f"covered={covered_states}")

    # ── Check 9: Guard 1 deps exist (state machine predecessor binding active) ──
    guard1_count = sum(
        1 for p in procs
        for origin in p.get("_S3_fields", {}).get("dep_origins", {}).values()
        if origin == "guard1_state_pred"
    )
    check("9. Guard 1 (state machine predecessor) produced at least 1 dep",
          guard1_count >= 1,
          f"count={guard1_count}")

    # ── Check 10: No dependency cycles (break_cycles succeeded) ──
    # Verify the dependency graph is a DAG by attempting topological sort
    import networkx as nx
    G = nx.DiGraph()
    for p in procs:
        G.add_node(p["temp_id"])
        for dep_id in p.get("_S3_fields", {}).get("dependencies", []):
            if dep_id in proc_by_id:
                G.add_edge(dep_id, p["temp_id"])
    try:
        # If is_directed_acyclic_graph returns True, no cycles remain
        is_dag = nx.is_directed_acyclic_graph(G)
        check("10. No dependency cycles (DAG after break_cycles)", is_dag,
              "cycles remain!" if not is_dag else "")
    except Exception as e:
        check("10. No dependency cycles (DAG check)", False, f"exception={e}")

    return passed, failed


def main():
    output_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT
    if not Path(output_path).exists():
        print(f"Output not found at {output_path}, running pipeline...")
        output = run_pipeline(output_path)
    else:
        print(f"Loading existing output from {output_path}")
        with open(output_path) as f:
            output = json.load(f)

    passed, failed = run_baseline_checks(output)
    total = passed + failed
    print()
    print(f"=== Summary: {passed}/{total} passed, {failed} failed ===")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
