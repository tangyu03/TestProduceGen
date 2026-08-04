"""V06 超时机制声明(模型推导版)：时间触发型义务的用例必须声明 time_control。

第一性原理："哪些用例需要 time_control"从模型推导(单一真相源),而非
case_spec.time_control.events_requiring 关键词(那会误伤"设置超时"配置操作、
"待办任务说明"等仅提及"超时"字样的非时间触发用例)：
  - transition_obligations 中 risk_traits 含 time_sensitive 的 TO
  - constraint_obligations 中 category==timing(或 desc 含超时/时限)的 BR

这些义务被引用(source_ids)的用例必须声明 time_control.mechanism ∈
allowed_mechanisms(测试策略,来自 case_spec.time_control)或 status=="planned"。

S1 生成器已从时效语义填充 time_control(见 _derive_time_mechanism)。
"""
from .base import CheckResult, get_procedures

CHECK_ID = "V06"


def _needs_time_control(model: dict) -> set:
    """返回需要 time_control 的义务 id 集合。"""
    needs: set = set()
    for to in model.get("transition_obligations", []) or []:
        if "time_sensitive" in (to.get("risk_traits") or []):
            if to.get("id"):
                needs.add(to["id"])
    for r in model.get("constraint_obligations", []) or []:
        desc = r.get("description") or ""
        if (r.get("type") == "business_rule"
                and (r.get("category") == "timing"
                     or "超时" in desc or "时限" in desc)):
            if r.get("id"):
                needs.add(r["id"])
    return needs


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="warning", suspected_stage="S1",
                      suspected_files=["nodes/s1_generation.py"])
    model = output.get("_model")
    if not model:
        res.skip("no coverage model passed (--model); skipping model-derived V06")
        return res

    allowed = set((spec or {}).get("time_control", {}).get("allowed_mechanisms", []))
    needs = _needs_time_control(model)
    if not needs:
        res.skip("model has no time-sensitive obligations")
        return res

    missing = 0
    for p in get_procedures(output):
        srcs = set(p.get("source_ids", []) or [])
        if not (srcs & needs):
            continue
        decl = p.get("time_control") or {}
        ok = decl.get("mechanism") in allowed or decl.get("status") == "planned"
        if not ok:
            missing += 1
            res.fail({"temp_id": p.get("temp_id"),
                      "source_ids": sorted(srcs & needs)[:5],
                      "declared": decl or None,
                      "allowed": sorted(allowed)})

    res.note = f"time obligations={len(needs)}, missing time_control={missing}"
    return res
