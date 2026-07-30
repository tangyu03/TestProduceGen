"""V02 守卫极性（重构版）：given 命中禁止/确认规则时，then 的断言方向必须符合极性。

极性档位（case_spec guard_policies[*].expected）：
- rejected：操作被禁止（不可/不能/禁止/只能）→
    then 必须命中 assertion_pattern（拒绝/提示/状态不变类），
    且 state 类断言不得声称成功迁移（"状态转换为X"）。
    两者缺一即 fail。
- confirm：操作允许但需二次确认（"需进行确认"）→
    then 必须命中 assertion_pattern（确认提示类），
    但允许同时含成功迁移（确认后操作可继续）。
    缺确认断言即 fail。
- 其他值（allowed 等）：跳过。

匹配语义：
- 条件匹配：pol.when_given_matches 归一化后作为子串在 givens 文本
  （state + description 拼接）中查找。
- 动作匹配：pol.action / pol.when_action_matches 与用例 when.action 双向子串，
  兜底 bigram 相似度（覆盖"提交打分" vs "打分提交"类语序变体）。
- 断言匹配：assertion_pattern 按 | 切分，任一关键词子串命中即通过。

卫生检查（记 note 不阻断）：
- cond 含 !=/>=/<= 等表达式符号 → 提示 spec 应改写为自然语言关键词
  （用例 givens 不会出现表达式文本，此类 cond 永远匹配不上 = 静默漏报）。
"""
import re

from .base import CheckResult, get_procedures, normalize_text

CHECK_ID = "V02"
SUCCESS_HINT = ("状态转换为", "状态变更为")
EXPR_SYMBOLS = ("!=", ">=", "<=", "==", "∈", "∉")


def _givens_text(p) -> str:
    return normalize_text(" ".join(
        str(g.get("state", "")) + str(g.get("description", ""))
        for g in p.get("givens", []) or []))


def _match_assertion_pattern(pattern: str, text: str) -> bool:
    """assertion_pattern 是 |-分隔的关键词列表，任一子串命中即通过。"""
    if not pattern:
        return False
    for alt in pattern.split("|"):
        kw = alt.strip()
        if kw and kw in text:
            return True
    return False


def _bigrams(s: str) -> set:
    s = normalize_text(s)
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else {s}


def _action_matches(pol_act: str, action: str) -> bool:
    """双向子串优先；bigram Jaccard >= 0.5 兜底（语序变体）。"""
    if not pol_act:
        return True
    if not action:
        return False
    pa, ac = normalize_text(pol_act), normalize_text(action)
    if pa in ac or ac in pa:
        return True
    b1, b2 = _bigrams(pa), _bigrams(ac)
    if not b1 or not b2:
        return False
    return len(b1 & b2) / len(b1 | b2) >= 0.5


def _claims_success(p) -> bool:
    """成功迁移检测：仅限 kind=="state" 的 thens（behavior 类不算）。

    "状态转换为已选入"= 成功迁移；"提示不可选入"（behavior）不算。
    """
    for t in p.get("thens", []) or []:
        if t.get("kind") == "state" and any(h in t.get("expectation", "")
                                            for h in SUCCESS_HINT):
            return True
    return False


def _joined_then_text(p) -> str:
    return " ".join(t.get("expectation", "") for t in p.get("thens", []) or [])


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="blocker", suspected_stage="S3",
                      suspected_files=["nodes/s3_dependency.py", "prompts/s1_prompt.py"])
    policies = (spec or {}).get("guard_policies") or []
    if not policies:
        res.skip("case_spec.guard_policies missing")
        return res

    hygiene, triggered = [], {"rejected": 0, "confirm": 0}
    for pol in policies:
        cond_raw = pol.get("when_given_matches", "") or ""
        if any(sym in cond_raw for sym in EXPR_SYMBOLS):
            hygiene.append(f"{pol.get('guard_id')}: cond 含表达式符号，"
                           f"用例 givens 无法文本命中，存在静默漏报风险")

    for p in get_procedures(output):
        g_text = _givens_text(p)
        action = (p.get("when") or {}).get("action", "") or ""
        joined = _joined_then_text(p)
        success = _claims_success(p)

        for pol in policies:
            expected = pol.get("expected", "rejected")
            if expected not in ("rejected", "confirm"):
                continue
            cond = normalize_text(cond_raw_of(pol))
            if not cond or cond not in g_text:
                continue
            pol_act = pol.get("when_action_matches", "") or pol.get("action", "") or ""
            if pol_act and not _action_matches(pol_act, action):
                continue

            pattern = pol.get("assertion_pattern", "")
            matched_guarded = _match_assertion_pattern(pattern, joined)
            triggered[expected] += 1

            if expected == "rejected":
                # 完整违规 = 无拒绝断言，或声称了成功迁移
                if not matched_guarded or success:
                    res.fail({"temp_id": p.get("temp_id"),
                              "guard_id": pol.get("guard_id"),
                              "clause": pol.get("clause", ""),
                              "violation": ("missing_reject_assertion"
                                            if not matched_guarded
                                            else "claims_success_despite_forbidden"),
                              "found": joined[:120],
                              "expected_pattern": pattern})
            else:  # confirm
                # 只缺确认断言算违规；含成功迁移是合法的
                if not matched_guarded:
                    res.fail({"temp_id": p.get("temp_id"),
                              "guard_id": pol.get("guard_id"),
                              "clause": pol.get("clause", ""),
                              "violation": "missing_confirm_assertion",
                              "found": joined[:120],
                              "expected_pattern": pattern})

    # Build a human-readable note explaining what was checked and the outcome.
    # "triggered" counts how many times a guard policy matched a procedure:
    #   - rejected: proc's givens matched a "rejected" guard → checked that
    #     thens assert rejection (not success migration)
    #   - confirm: proc's givens matched a "confirm" guard → checked that
    #     thens contain a confirmation prompt
    # fail_count=0 means all triggered guards had correct polarity.
    total_triggered = triggered['rejected'] + triggered['confirm']
    if res.fail_count == 0:
        if total_triggered == 0:
            res.note = (
                "守卫极性检查通过：无 guard_policies 被触发（所有 proc 的 givens "
                "均未命中任何 guard 的 when_given_matches 条件），无违规项"
            )
        else:
            res.note = (
                f"守卫极性检查通过：共触发 {total_triggered} 次 guard 匹配"
                f"（rejected={triggered['rejected']}，confirm={triggered['confirm']}），"
                f"全部通过极性校验（rejected 类断言了拒绝，confirm 类含确认提示）"
            )
    else:
        res.note = (
            f"守卫极性检查失败：共触发 {total_triggered} 次 guard 匹配"
            f"（rejected={triggered['rejected']}，confirm={triggered['confirm']}），"
            f"其中 {res.fail_count} 项违规（见 evidence）"
        )
    if hygiene:
        res.note += f" | spec hygiene: {'; '.join(hygiene[:5])}"
    return res


def cond_raw_of(pol: dict) -> str:
    return pol.get("when_given_matches", "") or ""
