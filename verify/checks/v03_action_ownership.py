"""V03 动作归属：迁移型用例（obligation_type=1）的 when.action 必须属于
该实体的 action_catalog；跨实体级联效果不得直接挂在从动实体上。

匹配策略（两级）：
1. 子串匹配：catalog 任一 action 是 proc action 的子串（原逻辑）
2. bigram 相似：bigram Jaccard >= 0.4（捕获"提为试用" vs "试用机构升为合格"类变体）

系统驱动豁免：actor="系统" 的 transition 是系统自动触发（非用户手动操作），
不需要匹配 action_catalog。这用 P1 的 role 字段判断，不用硬编码关键词。
"""
from .base import CheckResult, entity_alias, get_procedures, normalize_text

CHECK_ID = "V03"

# 系统角色名——P1 role=system 在 S1 转换后的中文名
_SYSTEM_ACTORS = {"系统", "system"}


def _bigrams(s: str) -> set:
    s = normalize_text(s)
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else ({s} if s else set())


def _action_matches(action: str, catalog_actions: set) -> bool:
    """两级匹配：子串 → bigram → False。"""
    if not action:
        return True
    # Pass 1: substring (original logic)
    for a in catalog_actions:
        if a and a in action:
            return True
    # Pass 2: bigram similarity (captures paraphrased action names)
    ab = _bigrams(action)
    if ab:
        for a in catalog_actions:
            if not a:
                continue
            cb = _bigrams(a)
            if cb and len(ab & cb) / len(ab) >= 0.4:
                return True
    return False


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

        # 系统驱动豁免：actor="系统" 的 transition 是系统自动触发，
        # 不是用户手动操作，不需要匹配 action_catalog。
        # 用 P1 的 role 字段（经 S1 转换为中文"系统"）判断，不用关键词。
        actor = (p.get("when") or {}).get("actor", "") or ""
        if actor in _SYSTEM_ACTORS:
            continue

        if not _action_matches(action, catalog[ent]):
            res.fail({"temp_id": p.get("temp_id"), "entity": p.get("entity"),
                      "action": action, "allowed": sorted(catalog[ent])})
    return res
