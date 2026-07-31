"""V03 动作归属：迁移型用例（obligation_type=1）的 when.action 必须属于
该实体的 action_catalog；跨实体级联效果不得直接挂在从动实体上。

豁免规则：
1. actor="系统" 或 actor 为空：系统驱动 transition，不是用户手动操作
2. indirect_via：proc 的 source_ids 对应的 spec transition 有 indirect_via
   字段时，说明这是跨实体联动（如 评审计划.建立 → 项目.已选入→待评审），
   action 描述的是联动效果而非用户直接操作，豁免

匹配策略（两级）：
1. 子串匹配：catalog 任一 action 是 proc action 的子串
2. bigram 相似：bigram Jaccard >= 0.4
"""
from .base import CheckResult, entity_alias, get_procedures, normalize_text

CHECK_ID = "V03"

_SYSTEM_ACTORS = {"系统", "system"}


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


def _build_indirect_via_set(spec: dict) -> set:
    """从 spec.state_machines 提取所有有 indirect_via 的 transition id。

    indirect_via 标记的 transition 是跨实体联动（如 评审计划.建立 → 项目状态变化），
    其 action 描述的是联动效果而非用户直接操作，不需要匹配 action_catalog。
    """
    result = set()
    for m in (spec.get("state_machines") or {}).values():
        for t in m.get("transitions", []) or []:
            iv = t.get("indirect_via")
            if iv:
                result.add(t.get("id", ""))
    return result


def _build_tid_triggers(spec: dict) -> dict:
    """从 spec.state_machines 提取 tid → trigger 文本。

    P1 的 action 可能描述的是触发者+动作（如'评审专家打分保存'），
    而 case_spec 的 trigger 字段记录了同样的语义（'专家对项目打分保存'）。
    如果 proc action 和 spec trigger 匹配，说明 action 是正确的，只是
    措辞和 action_catalog 不同。
    """
    result = {}
    for m in (spec.get("state_machines") or {}).values():
        for t in m.get("transitions", []) or []:
            tid = t.get("id", "")
            trigger = t.get("trigger", "") or t.get("action", "") or ""
            if tid and trigger:
                result[tid] = trigger
    return result


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="blocker", suspected_stage="S0",
                      suspected_files=["nodes/s0_topology.py", "prompts/s0_prompt.py"])
    catalog = {k: set(v) for k, v in ((spec or {}).get("action_catalog") or {}).items()
               if isinstance(v, list)}
    if not catalog:
        res.skip("case_spec.action_catalog missing")
        return res

    indirect_via_tids = _build_indirect_via_set(spec or {})
    tid_triggers = _build_tid_triggers(spec or {})

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

        # 豁免2: indirect_via → 跨实体联动 transition
        source_ids = p.get("source_ids", []) or []
        if any(sid in indirect_via_tids for sid in source_ids):
            continue

        # 匹配1: action_catalog 子串/bigram 匹配
        if _action_matches(action, catalog[ent]):
            continue

        # 匹配2: spec transition trigger 匹配
        # P1 action 可能和 case_spec trigger 措辞不同但语义相同
        # (如 '评审专家打分保存' vs '专家对项目打分保存')
        for sid in source_ids:
            trigger = tid_triggers.get(sid, "")
            if trigger and _action_matches(action, {trigger}):
                break  # 匹配成功
        else:
            # 都不匹配 → fail
            res.fail({"temp_id": p.get("temp_id"), "entity": p.get("entity"),
                      "action": action, "allowed": sorted(catalog[ent])})
    return res
