"""双通道对账：确定性下界（signals/derive）× LLM 全量（数据文件）→ 差异即评审队列。
产出按 prompt 中断协议格式化为 ambiguity 候选（severity=minor，不暂停）。"""
from __future__ import annotations

def _cover_keys(items, key_fn):
    return {key_fn(i) for i in items} - {None}

def reconcile_signals(signals, model) -> list:
    """文档扫描候选 vs LLM 产物。返回评审队列条目列表。"""
    queue = []

    llm_states = {s for e in model.entities for d in e["state_dimensions"]
                  for s in d["states"]}
    for c in signals.state_enums:                          # 枚举候选漏建模检查
        missing = [v for v in c["values"] if v not in llm_states]
        if missing and len(missing) < len(c["values"]):    # 部分命中才算疑似遗漏
            queue.append({"kind": "state_enum_gap", "severity": "minor",
                          "concept": f"状态枚举候选未覆盖: {missing}",
                          "description": f"原文[{c['source_ref']}]枚举 {c['values']}，"
                                         f"其中 {missing} 未出现在任何状态维度",
                          "suggestion": "人工确认是属性取值还是遗漏的状态维度"})

    llm_pairs = {(t["from"], t["to"]) for t in model.transitions}
    for c in signals.changes:                              # 转换候选漏提取检查
        if (c["from"], c["to"]) not in llm_pairs:
            queue.append({"kind": "change_gap", "severity": "minor",
                          "concept": f"状态变化候选未建模: {c['from']}→{c['to']}",
                          "description": f"原文[{c['source_ref']}]含"
                                         f"'由{c['from']}变为{c['to']}'，transitions 无此边",
                          "suggestion": "人工确认是否遗漏转换或属非状态语义"})

    br_texts = "；".join(b["desc"] for b in model.business_rules)
    for c in signals.br_candidates:                        # BR 候选漏收录检查
        if c["keyword"] not in br_texts or c["text"][:15] not in br_texts:
            queue.append({"kind": "br_gap", "severity": "minor",
                          "concept": f"限制性语句未收录: {c['text'][:24]}…",
                          "description": f"原文[{c['source_ref']}]含限制词"
                                         f"[{c['keyword']}]，BR 中未见对应规则",
                          "suggestion": f"建议 category={c['category_hint']}"})
    return queue

def reconcile_causal(model) -> list:
    """derive 推出的因果候选 vs LLM 写的 transition_relations（4.5/4.6 对账）。"""
    from .derive import derive_causal_from_results
    have = {(r["from"], r["to"]) for r in model.transition_relations}
    queue = []
    for c in derive_causal_from_results(model):
        if (c["from"], c["to"]) not in have:
            queue.append({"kind": "causal_gap", "severity": "minor",
                          "concept": f"疑似遗漏因果: {c['from']}→{c['to']}",
                          "description": f"{c['evidence_transitions'][0]} 的 "
                                         f"expected_results 含'{c['trigger'][:30]}…'，"
                                         f"但 transition_relations 无此关系",
                          "suggestion": "过 4.6 鉴别：判因果则补录，判约束则入 XC"})
    return queue
