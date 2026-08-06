"""双通道对账：确定性下界（signals/derive）× LLM 全量（数据文件）→ 差异即评审队列。
产出按 prompt 中断协议格式化为 ambiguity 候选（severity=minor，不暂停）。"""
from __future__ import annotations
import difflib
import re
import unicodedata

def _cover_keys(items, key_fn):
    return {key_fn(i) for i in items} - {None}

# 原文里的枚举分隔符：`由已完成变为结束或超时结束`、`由A变为B/C` 都按此拆开
_ENUM_SPLIT = re.compile(r"[或/、，,；;]")

def _split_enum(v: str) -> list:
    return [x for x in _ENUM_SPLIT.split(v) if x]

def _change_covered(frm: str, to: str, llm_pairs) -> bool:
    """状态变化候选对账：`由A变为B或C` 拆成 (A,B)/(A,C) 等子值，
    任一子值与模型边配对即视为已建模（精度优先，拆开比漏报更稳）。"""
    return any((a, b) in llm_pairs
               for a in _split_enum(frm) for b in _split_enum(to))

# ---- Gate B：BR 候选覆盖判定 ----
# 候选正文与模型任一面文本的最长公共子串 ≥ 此字数即视为已建模（minor 级，精度优先）
_MIN_OVERLAP = 10

def _normalize(s: str) -> str:
    """匹配用字符归一化：解除 markdown 转义、NFKC 全角转半角、顿号统一为逗号。
    候选来自原文（带 `1\\-5`、全角 `７`、顿号），字段来自数据（干净），
    归一化只用于 LCS 判定，不污染入队的展示文本。"""
    s = re.sub(r"\\(.)", r"\1", s)                 # `1\-5`、`a\)` → `1-5`、`a)`
    s = unicodedata.normalize("NFKC", s)           # `７天`/`Ａ`/`（` → 半角
    return s.replace("、", ",")                     # 顿号统一，避免 LCS 在标点处断裂

def _candidate_core(text: str) -> str:
    """候选正文：去空白 + 归一化 + 去掉 `> `/`（1）`/`a)`/`编辑：` 等前置标记。"""
    c = _normalize(re.sub(r"\s+", "", text))
    c = re.sub(r"^[>#①②③④⑤⑥⑦⑧⑨⑩]+", "", c)
    c = re.sub(r"^[（(]\d+[）)]", "", c)
    c = re.sub(r"^[a-zA-Z][)）]", "", c)
    c = re.sub(r"^[^：:]{1,8}[：:]", "", c)
    return c

def _model_texts(model) -> list:
    """模型所有文本面（BR/转换/操作/XC）归一化后的覆盖索引。"""
    out = []

    def add(t: str):
        t = _normalize(re.sub(r"\s+", "", t))
        if t:
            out.append(t)

    for b in model.business_rules:
        add(b["desc"])
    for t in model.transitions:
        add(t["action"])
        for r in t["expected_results"]:
            add(r)
        add(t["note"].get("comment", ""))
    for e in model.entities:
        for o in e["operations"]:
            add(o["name"])
            for r in o["expected_results"]:
                add(r)
            add(o["note"].get("comment", ""))
    for x in model.cross_entity:
        add(x["desc"])
    return out

def _overlap_len(a: str, b: str) -> int:
    """最长公共子串长度。autojunk=False：长序列不把高频字符当 junk 而截断 LCS。"""
    return difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(
        0, len(a), 0, len(b)).size

def _br_covered(cand_text: str, texts: list) -> bool:
    """Gate B：候选正文与任一模型文本面的 LCS ≥ 阈值即视为已建模。命中即短路。"""
    c = _candidate_core(cand_text)
    if not c:
        return False
    for m in texts:
        if _overlap_len(c, m) >= _MIN_OVERLAP:
            return True
    return False

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
        if not _change_covered(c["from"], c["to"], llm_pairs):
            queue.append({"kind": "change_gap", "severity": "minor",
                          "concept": f"状态变化候选未建模: {c['from']}→{c['to']}",
                          "description": f"原文[{c['source_ref']}]含"
                                         f"'由{c['from']}变为{c['to']}'，transitions 无此边",
                          "suggestion": "人工确认是否遗漏转换或属非状态语义"})

    texts = _model_texts(model)
    for c in signals.br_candidates:                        # BR 候选漏收录检查（Gate B）
        if not _br_covered(c["text"], texts):              # 已在任一模型面 → 跳过
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
