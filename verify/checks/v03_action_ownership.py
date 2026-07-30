"""V03 动作归属：迁移型用例（obligation_type=1）的 when.action 必须属于
该实体的 action_catalog；跨实体级联效果不得直接挂在从动实体上。"""
from .base import CheckResult, entity_alias, get_procedures

CHECK_ID = "V03"


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="blocker", suspected_stage="S0",
                      suspected_files=["nodes/s0_topology.py", "prompts/s0_prompt.py"])
    catalog = {k: set(v) for k, v in ((spec or {}).get("action_catalog") or {}).items()
               if isinstance(v, list)}
    if not catalog:
        res.skip("case_spec.action_catalog missing")
        return res
    for p in get_procedures(output):
        if p.get("obligation_type") != 1:          # 仅迁移型用例
            continue
        ent = entity_alias(p.get("entity", ""), set(catalog))
        if ent not in catalog:
            continue
        action = (p.get("when") or {}).get("action", "") or ""
        if not action or action.startswith("按规则"):
            continue
        if action.startswith("执行") and len(action) > 2:
            action = action[2:]
        if not any(a and a in action for a in catalog[ent]):
            res.fail({"temp_id": p.get("temp_id"), "entity": p.get("entity"),
                      "action": action, "allowed": sorted(catalog[ent])})
    return res
