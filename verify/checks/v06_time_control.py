"""V06 超时机制声明（重构版）：双向核对，事件命中与 spec 标记的迁移都必须声明 time_control。

两个检查方向：
1. 事件文本命中（原有）：when.event 含 spec.time_control.events_requiring 关键词
   （如"超时""时限到达""30分钟无操作""密码有效期7天"）→ 用例必须声明 time_control。
2. spec 迁移表核对（新增）：transitions 中 time_control_required=true 的迁移，
   其 source_ids 引用的用例必须声明 time_control——即使事件文本没写"超时"二字
   （比如用例标题只写"系统自动转换"）。

判定：
- time_control.mechanism ∈ allowed_mechanisms → 合法
- time_control.status == "planned" → 骨架阶段豁免（详细化阶段应被 Gate-E 拒绝）
- 两者都不满足 → fail（warning 级，不阻断 skeleton_pass）

统计：note 报告 (事件命中数, spec迁移标记命中数, 未声明数) 便于校准误报。
"""
from .base import CheckResult, get_procedures

CHECK_ID = "V06"


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="warning", suspected_stage="S1",
                      suspected_files=["prompts/s1_prompt.py", "nodes/s1_generation.py"])
    tc = (spec or {}).get("time_control") or {}
    kws = tc.get("events_requiring") or []
    allowed = set(tc.get("allowed_mechanisms") or [])
    if not kws or not allowed:
        res.skip("case_spec.time_control missing")
        return res

    # spec 迁移表：time_control_required=true 的迁移 id 集合
    tc_tids = set()
    for m in ((spec or {}).get("state_machines") or {}).values():
        for t in m.get("transitions", []) or []:
            if t.get("time_control_required") and t.get("id"):
                tc_tids.add(t["id"])

    event_hits = spec_tid_hits = missing = 0
    for p in get_procedures(output):
        event = (p.get("when") or {}).get("event", "") or ""
        srcs = set(p.get("source_ids", []) or [])
        event_hit = any(k in event for k in kws)
        tid_hit = bool(srcs & tc_tids)
        if not (event_hit or tid_hit):
            continue
        if event_hit:
            event_hits += 1
        if tid_hit:
            spec_tid_hits += 1
        decl = p.get("time_control") or {}
        ok = decl.get("mechanism") in allowed or decl.get("status") == "planned"
        if not ok:
            missing += 1
            res.fail({"temp_id": p.get("temp_id"),
                      "event": event[:80],
                      "hit_by": (["event_keyword"] if event_hit else [])
                                + (["spec_transition"] if tid_hit else []),
                      "declared": decl or None,
                      "allowed": sorted(allowed)})

    res.note = (f"event_keyword hits={event_hits}, spec_transition hits={spec_tid_hits}, "
                f"missing time_control={missing}")
    return res
