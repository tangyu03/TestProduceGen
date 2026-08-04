"""V03 动作归属(模型推导版)：迁移型用例(obligation_type=1)的 when.action
必须属于该实体的行为模型(操作 ∪ 转换动作)。

第一性原理：动作目录从模型推导,而非 case_spec.action_catalog 手写清单——
级联转换(项目纳入评审计划/评审计划启动后项目进入评审中)本就是该实体
transition_obligations 的 action,天然入目录,无需 indirect_via 豁免。

豁免(均为结构化标记,非文本匹配)：
1. actor="系统" 或空 → 系统驱动 transition
2. risk_trait ∈ {audit_rejection, time_sensitive} → S1 派生的驳回/超时变体
   (驳回动作、X(边界)/尝试X(已过期) 不在模型中)

缺 --model 时跳过(无法推导目录,不退回 case_spec)。
"""
from .base import CheckResult, entity_alias, get_procedures, normalize_text

CHECK_ID = "V03"

_SYSTEM_ACTORS = {"系统", "system"}
_S1_DERIVED_TRAITS = {"audit_rejection", "time_sensitive"}


def _bigrams(s: str) -> set:
    s = normalize_text(s)
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else ({s} if s else set())


def _action_matches(action: str, catalog_actions: set) -> bool:
    """两级匹配：子串 → bigram → False。"""
    if not action:
        return True
    for a in catalog_actions:
        if a and a in action:
            return True
    ab = _bigrams(action)
    if ab:
        for a in catalog_actions:
            if not a:
                continue
            cb = _bigrams(a)
            if cb and len(ab & cb) / len(ab) >= 0.4:
                return True
    return False


def _build_catalog(model: dict) -> dict:
    """catalog[entity] = 实体操作名 ∪ 转换动作(模型为单一真相源)。"""
    catalog: dict = {}
    for eo in model.get("entity_obligations", []) or []:
        ent = eo.get("entity")
        op = eo.get("operation_name")
        if ent and op:
            catalog.setdefault(ent, set()).add(op)
    for to in model.get("transition_obligations", []) or []:
        ent = to.get("entity")
        act = to.get("action")
        if ent and act:
            catalog.setdefault(ent, set()).add(act)
    return catalog


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="blocker", suspected_stage="S0",
                      suspected_files=["nodes/s0_topology.py", "nodes/s1_generation.py"])
    model = output.get("_model")
    if not model:
        res.skip("no coverage model passed (--model); skipping model-derived V03")
        return res

    catalog = _build_catalog(model)
    if not catalog:
        res.skip("model has no entity operations / transitions")
        return res

    for p in get_procedures(output):
        if p.get("obligation_type") != 1:
            continue
        ent = entity_alias(p.get("entity", ""), set(catalog))
        if ent not in catalog:
            continue
        action = (p.get("when") or {}).get("action", "") or ""
        if not action or action.startswith("按规则"):
            continue
        if action.startswith("执行") and len(action) > 2:
            action = action[2:]

        # 豁免1: actor="系统" 或空 → 系统驱动
        actor = (p.get("when") or {}).get("actor", "") or ""
        if not actor or actor in _SYSTEM_ACTORS:
            continue

        # 豁免2: S1 派生的驳回/超时变体动作(不在模型)
        if p.get("risk_trait") in _S1_DERIVED_TRAITS:
            continue

        if not _action_matches(action, catalog[ent]):
            res.fail({"temp_id": p.get("temp_id"), "entity": p.get("entity"),
                      "action": action, "allowed": sorted(catalog[ent])})
    return res
