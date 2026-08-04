"""V10 覆盖校验(模型推导版)：每个模型化义务必须有用例覆盖 + 状态机状态全覆盖。

第一性原理：覆盖是可追溯性(结构化引用)问题,不是文本关键词匹配问题。
procedure 的 source_ids 引用义务 id(T-*/EO-*/RO-*),embedded_brs 引用嵌入的
BR。V10 据此验证——不再用 case_spec.coverage_matrix 的需求关键词做子串匹配
(那是 AI 生成的二手代理,且措辞差异产生大量伪影)。

覆盖检查(每个义务 ≥1 用例引用)：
  - transition_obligations → Type1 用例的 source_ids
  - entity_obligations     → Type3/5/9 用例的 source_ids
  - business_rule ROs      → Type7 source_ids 或 embedded_brs(映射 BR→RO-BR)
                             或 XC-* 因果约束(设计上无独立用例,豁免)
  - invalid_transition ROs → Type6 用例的 source_ids
  - cross_entity           → 结构义务(无独立用例),豁免

状态覆盖：model._context.state_info 的每个状态,须出现在某用例的
post_state 或 givens.state(精确等值,不用子串)。

真实覆盖缺口(需求未建模为义务,如"计划编号自动生成唯一")不属于 V10——
那是 P1 模型对 SRS 的忠实度问题,由 P1 校验层(C1-C16/原文对账)负责。

缺 --model 时跳过(无法推导期望,不退回 case_spec 关键词代理)。
"""
from collections import defaultdict

from .base import CheckResult, get_procedures

CHECK_ID = "V10"


def _post_state(p) -> str:
    raw = (p.get("post_state") or "").strip()
    if not raw:
        return ""
    for sep in ("→", "->"):
        if sep in raw:
            return raw.split(sep)[-1].strip().strip("()")
    return raw.strip().strip("()")


def _reached_states_by_dim(procs: list, name_to_id: dict) -> dict:
    """(entity_id, dimension) → set(reached states from post_state + givens.state)。

    output.json 的 procedure.entity 是中文名(经 _translate_procedures 翻译),
    model._context.state_info 用实体 ID(E-PROJ)。这里把中文名归一为 ID。
    """
    reached: dict[tuple, set] = defaultdict(set)
    for p in procs:
        ent = name_to_id.get(p.get("entity", ""), p.get("entity", ""))
        dim = p.get("dimension", "")
        key = (ent, dim)
        ps = _post_state(p)
        if ps:
            reached[key].add(ps)
        for g in p.get("givens", []) or []:
            s = str(g.get("state", "")).strip()
            if s:
                reached[key].add(s)
    return reached


def _obligation_coverage(model: dict, procs: list) -> tuple[list, list]:
    """返回 (未覆盖义务列表, note 片段列表)。"""
    missing = []
    notes = []

    to_ids = {t["id"] for t in model.get("transition_obligations", []) or []}
    eo_ids = {e["id"] for e in model.get("entity_obligations", []) or []}
    ros = model.get("constraint_obligations", []) or []
    br_ids = {r["id"] for r in ros if r.get("type") == "business_rule"}
    it_ids = {r["id"] for r in ros if r.get("type") == "invalid_transition"}
    # BR-xxx → RO-BR-xxx 映射(embedded_brs 用 constraint_id)
    br_by_cid = {r.get("constraint_id"): r["id"] for r in ros if r.get("constraint_id")}
    # XC-* 因果约束 BR: 设计上无独立用例,豁免
    xc_causal_ids = {r["id"] for r in ros
                     if str(r.get("constraint_id") or "").startswith("XC-")
                     or r.get("source_xc")}

    src_covered: set = set()
    embedded_covered: set = set()
    for p in procs:
        src_covered.update(set(p.get("source_ids", []) or []))
        for cid in p.get("embedded_brs", []) or []:
            if cid in br_by_cid:
                embedded_covered.add(br_by_cid[cid])

    # TO 覆盖
    miss_to = sorted(to_ids - src_covered)
    if miss_to:
        missing.append({"kind": "transition", "missing": miss_to})
    notes.append(f"TO {len(to_ids) - len(miss_to)}/{len(to_ids)}")

    # EO 覆盖
    miss_eo = sorted(eo_ids - src_covered)
    if miss_eo:
        missing.append({"kind": "entity", "missing": miss_eo})
    notes.append(f"EO {len(eo_ids) - len(miss_eo)}/{len(eo_ids)}")

    # BR 覆盖(source_ids + embedded_brs; XC 豁免)
    covered_br = (src_covered & br_ids) | embedded_covered | xc_causal_ids
    miss_br = sorted(br_ids - covered_br)
    if miss_br:
        missing.append({"kind": "business_rule", "missing": miss_br})
    notes.append(f"BR {len(br_ids) - len(miss_br)}/{len(br_ids)}"
                 f"(embedded {len(embedded_covered & br_ids)}, "
                 f"xc_causal {len(xc_causal_ids)})")

    # IT 覆盖
    miss_it = sorted(it_ids - src_covered)
    if miss_it:
        missing.append({"kind": "invalid_transition", "missing": miss_it})
    notes.append(f"IT {len(it_ids) - len(miss_it)}/{len(it_ids)}")

    return missing, notes


def _state_coverage(model: dict, procs: list) -> list:
    """从 state_info 校验每个状态被覆盖。"""
    state_info = (model.get("_context") or {}).get("state_info", {}) or {}
    name_to_id = {info.get("entity_name"): ent for ent, info in state_info.items()}
    reached = _reached_states_by_dim(procs, name_to_id)
    missing = []
    for ent, info in state_info.items():
        for dim in info.get("dimensions", []) or []:
            dim_name = dim.get("dimension_name", "")
            rs = reached.get((ent, dim_name), set())
            for st in dim.get("states", []) or []:
                if st and st not in rs:
                    missing.append({"machine": f"{ent}.{dim_name}",
                                    "missing_state": st})
    return missing


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="blocker", suspected_stage="P2",
                      suspected_files=["build_obligations.py", "nodes/s1_generation.py"])
    model = output.get("_model")
    if not model:
        res.skip("no coverage model passed (--model); skipping model-derived V10")
        return res

    procs = get_procedures(output)
    ob_missing, notes = _obligation_coverage(model, procs)
    for m in ob_missing:
        res.fail({"obligation_kind": m["kind"],
                  "missing_obligation_ids": m["missing"][:10],
                  "count": len(m["missing"])})

    st_missing = _state_coverage(model, procs)
    for m in st_missing:
        res.fail({"machine": m["machine"], "missing_state": m["missing_state"]})

    res.note = " | ".join(notes + [f"state_misses={len(st_missing)}"])
    return res
