"""V05 维度组合合法性（重构版）：givens 中不得出现 spec 声明的不可达组合。

combo schema（case_spec v1.1+，三种形态）：
1. 显式键值型（blocker）：
   {"current": "待评审", "pre_pause": "已完成"}
   → 每个键映射到 givens 中的探测文本；键→探测模板由 _probe_for_key 决定。
   全部探测命中且 match_mode=all（默认）才判违规。
2. 表达式型（blocker）：
   {"current": "专家人数=6"}
   → current 值本身是"维度=值"表达式，直接作为子串探测。
3. note 型（warning）：
   {"current": "待选入", "note": "首次新增待选入项目 + 任意评价结果（未评价过）"}
   → 语义约束（"未评价过的项目不得带评价结果"），无法用纯文本精确判定。
     current 命中时按 warning 级记录，提示需语义复核，不阻断 skeleton_pass。

match_mode（combo 级，默认 all）：
- all：所有键探测命中才违规
- any：任一键探测命中即违规（用于"任一禁词出现即非法"类）
"""
import re

from .base import CheckResult, get_procedures, normalize_text

CHECK_ID = "V05"

# 键名 → givens 探测模板。{} 占位 combo 值。
# givens 文本由 state + description 拼接归一化而来，
# 分支条件的描述形态是 "分支条件: 维度=值"（S4 实例化的产物）。
_KEY_PROBE_TEMPLATES = {
    "current": "{}",
    "pre_pause": "暂停前状态={}",
    "other_dim": "{}",
}

_EXPR_RE = re.compile(r"^.+[=＝].+$")


def _givens_text(p) -> str:
    return normalize_text(" ".join(
        str(g.get("state", "")) + str(g.get("description", ""))
        for g in p.get("givens", []) or []))


def _probe_for_key(key: str, value: str) -> str:
    tpl = _KEY_PROBE_TEMPLATES.get(key, "{}")
    return normalize_text(tpl.format(value))


def _is_note_combo(combo: dict) -> bool:
    return "note" in combo


def _combo_probes(combo: dict) -> list:
    """把 combo 展开为 (key, probe) 列表，跳过 note/meta 键。"""
    probes = []
    for key, value in combo.items():
        if key in ("note", "match_mode") or not value:
            continue
        if key == "current" and _EXPR_RE.match(str(value)):
            # 表达式型："专家人数=6" 整体作为探测串
            probes.append((key, normalize_text(str(value))))
        else:
            probes.append((key, _probe_for_key(key, str(value))))
    return probes


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="blocker", suspected_stage="S4",
                      suspected_files=["nodes/s4_multi_instance.py", "nodes/s0_topology.py"])
    constraints = (spec or {}).get("dimension_constraints") or []
    if not constraints:
        res.skip("case_spec.dimension_constraints missing")
        return res

    hygiene, advisory_hits = [], 0
    for p in get_procedures(output):
        g_text = _givens_text(p)
        if not g_text:
            continue
        for c in constraints:
            cname = c.get("name", "?")
            combos = c.get("invalid_combos", []) or []
            if not combos:
                hygiene.append(f"constraint '{cname}' has empty invalid_combos")
                continue
            for combo in combos:
                if _is_note_combo(combo):
                    # note 型：current 命中 → warning 级记录
                    cur = normalize_text(str(combo.get("current", "")))
                    if cur and cur in g_text:
                        advisory_hits += 1
                        res.evidence.append({
                            "level": "warning",
                            "temp_id": p.get("temp_id"),
                            "constraint": cname,
                            "combo": combo,
                            "reason": "note-type constraint hit; needs semantic review"})
                    continue
                probes = _combo_probes(combo)
                if not probes:
                    hygiene.append(f"constraint '{cname}' combo has no matchable keys: {combo}")
                    continue
                mode = str(combo.get("match_mode", "all")).lower()
                hits = sum(1 for _, probe in probes if probe and probe in g_text)
                violated = (hits == len(probes)) if mode == "all" else (hits > 0)
                if violated:
                    res.fail({"temp_id": p.get("temp_id"),
                              "constraint": cname,
                              "combo": combo,
                              "matched": [k for k, pr in probes if pr and pr in g_text]})

    notes = []
    if advisory_hits:
        notes.append(f"note-type advisory hits: {advisory_hits} (warning, not blocking)")
    if hygiene:
        notes.append("spec hygiene: " + "; ".join(hygiene[:5]))
    if notes:
        res.note = " | ".join(notes)
    return res
