"""V10 覆盖矩阵（重构版）：coverage_matrix 条目探测 + 状态机状态覆盖核查。

骨架层只做机械匹配，但旧版"整词子串匹配"对长描述型 probe
（如 "开题合格及以上→已选入且阶段变验收"）永不命中。本版分级匹配：
- 短 probe（≤6 字符）：精确子串匹配
- 长 probe：bigram 包含率 ≥ 0.6 视为命中（容忍措辞变体，不引入语义模型）
- 可选 spec 扩展 entry.probe_aliases = {probe: [alias...]}：probe 或其任一变体命中即算

required_types 检查为 warning 级：条目声明需要的用例类型（如 transition），
若全部命中 probe 的用例中没有该类型，记入 evidence(level=warning) 提示
"有文本提及但无对应类型用例"，不阻断 skeleton_pass——类型级判定留给 Gate-E。

状态覆盖核查：按 machine.dimension / 实体别名分组，状态必须在该组用例的
post_state（解析箭头后精确等值）或 givens.state（精确等值）中出现。
不用子串匹配（"合格"子串会到处误命中）；组内无用例时回退全局检查并记 hygiene。

boundary 无 boundary_probe_template 时不探测（记 hygiene，数值边界归 Gate-E）。
"""
import re

from .base import CheckResult, entity_alias, get_procedures, normalize_text

CHECK_ID = "V10"

BIGRAM_HIT_RATIO = 0.6
# Probes with length <= SHORT_PROBE_LEN use exact-substring matching (too
# short for stable bigram statistics). The threshold is inclusive: a 6-char
# probe like "归档转为结束" has only 5 bigrams, and one missing bigram (e.g.
# "档转" missing because text says "状态转换为") drops the ratio to 0.6,
# which IS the threshold — but substring match fails because the literal
# 6-char sequence isn't contiguous in text. So 6-char probes should go
# through the bigram path, not the substring path. Use < (strict).
SHORT_PROBE_LEN = 5

# required_types 文本 → obligation_type 集合（display 无专属类型，按 rule/config 宽匹配）
_TYPE_MAP = {
    "transition": {1},
    "rule": {8, 6},
    "display": {8, 3},
    "field_validation": {9},
}


def _proc_text(p) -> str:
    parts = [p.get("title", ""), p.get("entity", ""),
             (p.get("when") or {}).get("event", ""),
             (p.get("when") or {}).get("action", "")]
    parts += [t.get("expectation", "") for t in p.get("thens", []) or []]
    parts += [str(g.get("state", "")) + str(g.get("description", ""))
              for g in p.get("givens", []) or []]
    parts += [str(x) for x in (p.get("source_ids", []) or [])]
    return normalize_text(" ".join(str(x) for x in parts))


def _bigrams(s: str) -> set:
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else ({s} if s else set())


# Character-set Jaccard threshold for the order-independent fallback.
# Catches cases where the probe and text share most characters but in
# different word order (e.g. probe "已提交不可修改" vs text
# "已提交的项目不能进行分数修改" — bigram overlap is only 0.5 because
# "交不" doesn't appear in text, but character overlap is high).
CHAR_JACCARD_THRESHOLD = 0.7


def _char_jaccard(probe: str, text: str) -> float:
    """Character-set Jaccard similarity (order-independent).

    Only meaningful for non-trivial probes (>= 4 chars); below that the
    bigram path already handles short probes via exact substring match.
    """
    if not probe or not text:
        return 0.0
    ps, ts = set(probe), set(text)
    if not ps or not ts:
        return 0.0
    return len(ps & ts) / len(ps | ts)


def _probe_hit(probe: str, texts: list) -> bool:
    """texts: 已归一化的用例文本列表。

    五级匹配：
    1. 短 probe (≤5 字符)：精确子串匹配。
    2. 短 probe 兜底：probe 的所有字符均在文本中出现（字符子集），
       捕获"5人组" vs "评审组由5、7或9个专家组成"这类同义表述。
    3. 长 probe：bigram 包含率 ≥ 0.6 视为命中。
    4. 长 probe 兜底 A：字符集 Jaccard ≥ 0.7（捕获短文本场景）。
    5. 长 probe 兜底 B：probe 是 text 字符子集 AND 至少 1 个 bigram 命中。
    """
    p = normalize_text(probe)
    if not p:
        return True
    if len(p) <= SHORT_PROBE_LEN:
        # Pass 1: exact substring
        if any(p in t for t in texts):
            return True
        # Pass 2: character-subset (all probe chars present in text)
        ps = set(p)
        for t in texts:
            if ps and ps.issubset(set(t)):
                return True
        return False
    pb = _bigrams(p)
    if not pb:
        return False
    # Pass 3: bigram containment (strict)
    for t in texts:
        tb = _bigrams(t)
        if tb and len(pb & tb) / len(pb) >= BIGRAM_HIT_RATIO:
            return True
    # Pass 4: character-set Jaccard (order-independent, works for short texts)
    for t in texts:
        if _char_jaccard(p, t) >= CHAR_JACCARD_THRESHOLD:
            return True
    # Pass 5: probe is a character-subset of text AND at least one bigram
    # matches. Catches "全零不可提交" vs "项目各项打分全部为零的不能提交"
    # — all 6 probe chars present in text, but only 1 bigram matches
    # (提交); the strict bigram ratio (0.2) is too low for Pass 3, but
    # the character-subset property confirms semantic overlap.
    ps = set(p)
    for t in texts:
        if ps and ps.issubset(set(t)):
            tb = _bigrams(t)
            if tb and (pb & tb):
                return True
    return False


def _probe_hit_types(probe: str, procs: list, texts: list) -> set:
    """返回命中该 probe 的用例 obligation_type 集合。"""
    p = normalize_text(probe)
    if not p:
        return set()
    hit = set()
    if len(p) <= SHORT_PROBE_LEN:
        ps = set(p)
        for proc, t in zip(procs, texts):
            if p in t:
                hit.add(proc.get("obligation_type"))
                continue
            # Character-subset fallback for short probes
            if ps and ps.issubset(set(t)):
                hit.add(proc.get("obligation_type"))
        return hit
    pb = _bigrams(p)
    ps = set(p)
    for proc, t in zip(procs, texts):
        tb = _bigrams(t)
        if tb and len(pb & tb) / len(pb) >= BIGRAM_HIT_RATIO:
            hit.add(proc.get("obligation_type"))
            continue
        # Character-set Jaccard fallback
        if _char_jaccard(p, t) >= CHAR_JACCARD_THRESHOLD:
            hit.add(proc.get("obligation_type"))
            continue
        # Subset + at-least-one-bigram fallback
        if ps and ps.issubset(set(t)) and tb and (pb & tb):
            hit.add(proc.get("obligation_type"))
    return hit


def _post_states(p) -> set:
    out = set()
    raw = (p.get("post_state") or "").strip()
    if raw:
        for sep in ("→", "->"):
            if sep in raw:
                raw = raw.split(sep)[-1]
                break
        out.add(raw.strip().strip("()"))
    return out


def _given_states(p) -> set:
    return {str(g.get("state", "")).strip() for g in p.get("givens", []) or []
            if str(g.get("state", "")).strip()}


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="blocker", suspected_stage="P2",
                      suspected_files=["build_obligations.py", "prompts/s0_prompt.py"])
    procs = get_procedures(output)
    texts = [_proc_text(p) for p in procs]
    hygiene, type_warns = [], 0

    # ── 覆盖矩阵探测 ──
    matrix = (spec or {}).get("coverage_matrix") or []
    if not matrix:
        res.skip("case_spec.coverage_matrix missing")
        return res
    total_probes = 0
    for entry in matrix:
        clause, topic = entry.get("clause", "?"), entry.get("topic", "")
        aliases = entry.get("probe_aliases") or {}
        probes = list(entry.get("must_include") or []) + list(entry.get("branches") or [])
        hit_types = set()
        for kw in probes:
            total_probes += 1
            variants = [kw] + list(aliases.get(kw, []) or [])
            if any(_probe_hit(v, texts) for v in variants):
                for v in variants:
                    hit_types |= _probe_hit_types(v, procs, texts)
                continue
            res.fail({"clause": clause, "topic": topic, "missing_keyword": kw})
        # required_types 覆盖（warning 级）
        for rt in entry.get("required_types", []) or []:
            want = _TYPE_MAP.get(rt, set())
            if want and hit_types and not (hit_types & want):
                type_warns += 1
                res.evidence.append({
                    "level": "warning", "clause": clause, "topic": topic,
                    "required_type": rt, "hit_types": sorted(t for t in hit_types if t),
                    "reason": "text mentions found but no case of required obligation_type"})
        # boundary
        tpl = entry.get("boundary_probe_template")
        for b in entry.get("boundary") or []:
            if tpl:
                probe = normalize_text(tpl.format(n=b))
                if not _probe_hit(probe, texts):
                    total_probes += 1
                    res.fail({"clause": clause, "topic": topic, "missing_boundary": b})
            else:
                hygiene.append(f"{clause}({topic}): boundary {b} has no probe template, skipped")

    # ── 状态机状态覆盖（精确字段等值，不用子串） ──
    machines = (spec or {}).get("state_machines") or {}
    known_entities = set(machines.keys())
    for name, m in machines.items():
        dim = m.get("dimension")
        group = [p for p in procs
                 if (dim and p.get("dimension") == dim)
                 or entity_alias(p.get("entity", ""), known_entities) == name]
        if group:
            reached = set()
            for p in group:
                reached |= _post_states(p)
                reached |= _given_states(p)
            scope = "dimension/entity group"
        else:
            reached = set()
            for p in procs:
                reached |= _post_states(p)
                reached |= _given_states(p)
            scope = "global fallback (no grouped cases)"
            hygiene.append(f"{name}: no cases matched dimension/entity, state check fell back to global")
        for st in m.get("states", []) or []:
            if st and st not in reached:
                res.fail({"machine": name, "missing_state_coverage": st, "scope": scope})

    # ── 汇总 ──
    misses = res.fail_count
    hit_ratio = round((total_probes - misses) / total_probes, 4) if total_probes else 1.0
    notes = [f"probe hit ratio={hit_ratio} ({total_probes - misses}/{total_probes})"]
    if type_warns:
        notes.append(f"required_type warnings={type_warns} (not blocking)")
    if hygiene:
        notes.append("spec hygiene: " + "; ".join(hygiene[:5]))
    res.note = " | ".join(notes)
    return res
