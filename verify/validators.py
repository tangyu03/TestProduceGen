#!/usr/bin/env python3
"""Gate-S 骨架校验调度器。

用法：
  python verify/validators.py --spec verify/case_spec.json --output test_output.json
  python verify/validators.py -s case_spec.json -o out.json --model coverage_obligations.json --json verdict.json
退出码：skeleton_pass=True → 0，否则 1。

--model 传入 coverage_obligations.json(结构化模型)：
  第一性原理——校验器的期望(动作目录/角色权限/超时判据/相位映射/覆盖义务)
  应从模型推导,而非 case_spec.json 这个 AI 生成的二手代理。需要模型的
  校验器(V03/V06/V07/V08/V10)通过 output["_model"] 读取;不需要的忽略。
  case_spec.json 只承载模型无法表达的 4 类测试设计事实(guard_policies /
  built_in_entities.readonly+no_form_page / dimension_constraints /
  time_control.allowed_mechanisms),其余期望一律以模型为准。
"""
import argparse
import importlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from verify.checks.base import CheckResult  # noqa: E402

CHECK_MODULES = [
    "v01_dependency_closure", "v02_guard_polarity", "v03_action_ownership",
    "v04_builtin_entity_protect", "v05_dimension_combo", "v06_time_control",
    "v07_role_permission", "v08_phase_consistency", "v09_dedup_instances",
    "v10_coverage_matrix",
]


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def run_all(output: dict, spec: dict, model: dict | None = None) -> list:
    # 模型注入 output["_model"]：需要模型推导期望的校验器读取,其余忽略。
    if model is not None:
        output = {**output, "_model": model}
    results = []
    for name in CHECK_MODULES:
        mod = importlib.import_module(f"verify.checks.{name}")
        t0 = time.time()
        try:
            r = mod.check(output, spec)
        except Exception as e:                       # 检查器自身崩溃不得静默
            r = CheckResult(check_id=name[:3].upper(), result="fail",
                            severity="blocker", note=f"check crashed: {e!r}")
        r.elapsed_ms = int((time.time() - t0) * 1000)
        results.append(r)
    return results


def compute_metrics(output: dict, results: list) -> dict:
    procs = output.get("procedures", []) or []
    uniq = len({json.dumps([p.get("givens"), p.get("when"), p.get("thens")],
                           ensure_ascii=False, sort_keys=True, default=str)
                for p in procs})
    fc = {r.check_id: r.fail_count for r in results}
    return {
        "case_total": len(procs),
        "dedup_ratio": round(uniq / max(len(procs), 1), 4),
        "guard_violations": fc.get("V02", 0),
        "dangling_deps": fc.get("V01", 0),
        "invalid_combos": fc.get("V05", 0),
        "builtin_misuse": fc.get("V04", 0),
        "coverage_misses": fc.get("V10", 0),
    }


def aggregate(output: dict, results: list) -> dict:
    import hashlib
    blockers = [r for r in results if r.result == "fail" and r.severity == "blocker"]
    warnings = [r for r in results if r.result == "fail" and r.severity != "blocker"]
    verdict = {
        "verdict": "fail" if blockers else "pass",
        "skeleton_pass": not blockers,
        "blocker_failures": len(blockers),
        "warning_failures": len(warnings),
        "checks": [r.to_dict() for r in results],
        "metrics": compute_metrics(output, results),
        "signature": None,
    }
    if blockers:
        raw = "|".join(f"{r.check_id}:{r.fail_count}" for r in blockers)
        verdict["signature"] = hashlib.sha1(raw.encode()).hexdigest()[:12]
    return verdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", "-s", required=True)
    ap.add_argument("--output", "-o", required=True)
    ap.add_argument("--model", "-m", default=None,
                    help="coverage_obligations.json 结构化模型(校验器从模型推导期望)")
    ap.add_argument("--json", "-j", default=None)
    args = ap.parse_args()
    spec, output = load_json(args.spec), load_json(args.output)
    model = load_json(args.model) if args.model else None
    verdict = aggregate(output, run_all(output, spec, model))
    text = json.dumps(verdict, ensure_ascii=False, indent=2)
    if args.json:
        Path(args.json).write_text(text, encoding="utf-8")
    print(text)
    sys.exit(0 if verdict["skeleton_pass"] else 1)


if __name__ == "__main__":
    main()
