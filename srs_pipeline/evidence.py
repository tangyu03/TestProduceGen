"""证据库：从原文机器抽取的逐字证据，作为一切白名单校验的事实源。
原则：建库即保真——只有能与原文精确对齐的片段才入库，LLM 不参与本层。"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

_HEADING = re.compile(r"^(\d+(?:\.\d+){0,3})[、.．]?\s*(\S.{0,40}?)\s*$", re.M)
_ENUM_LINE = re.compile(r"(状态|阶段)(?:包括|分为)[：:]?\s*([^。\n]{2,100})")
_SPLIT = re.compile(r"[、,，/；;]|和")
_RESTRICTIVE = ("必须", "不得", "禁止", "只能", "不可", "不超过")

@dataclass
class Span:
    id: str
    kind: str                      # heading | state_enum | constraint
    text: str                      # 原文逐字片段
    values: list = field(default_factory=list)  # state_enum 的枚举值（保持原文顺序）
    source_ref: str = ""

def build_evidence(doc_text: str) -> list:
    """机器抽取。任何入库存量都通过 `in doc_text` 精确验证，幻觉无从进入。"""
    spans, seq = [], 0

    def add(kind, text, values=None, ref=""):
        nonlocal seq
        if text and text in doc_text:
            seq += 1
            spans.append(Span(f"SP-{seq:03d}", kind, text, values or [], ref))

    for m in _HEADING.finditer(doc_text):
        add("heading", m.group(2).strip(), ref=f"{m.group(1)} {m.group(2).strip()}")

    for m in _ENUM_LINE.finditer(doc_text):
        raw = m.group(2).strip()
        values = [v.strip() for v in _SPLIT.split(raw) if v.strip()]
        values = [v for v in values if 1 <= len(v) <= 12 and v in doc_text]
        if 2 <= len(values) <= 12:
            add("state_enum", m.group(0).strip(), values)

    for ln in doc_text.splitlines():
        s = ln.strip().rstrip("。")
        if s and any(k in s for k in _RESTRICTIVE):
            add("constraint", s)
    return spans

def enum_spans(spans) -> list:
    return [s for s in spans if s.kind == "state_enum"]

def best_enum_match(states, spans):
    """为某个状态维度找覆盖度最高的原文枚举。返回 (span, covered_set)。"""
    best, best_cov = None, set()
    for sp in enum_spans(spans):
        cov = set(states) & set(sp.values)
        if len(cov) > len(best_cov):
            best, best_cov = sp, cov
    return best, best_cov
