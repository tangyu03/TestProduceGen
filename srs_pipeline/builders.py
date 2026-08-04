"""通用构造函数。在数据写入期就 fail-fast 拦截枚举/契约错误，比留到 Step6 再报更早。"""
from __future__ import annotations

from .constants import OP_CATEGORIES, PRECOND_TYPES
from .escape import esc

def N(inferred=False, comment="", conflict="", branch_dimension="") -> dict:
    n = {"inferred": bool(inferred)}                       # note 键规范：inferred 必填
    if comment:
        n["comment"] = esc(str(comment))
    if conflict:
        n["conflict"] = esc(str(conflict))
    if branch_dimension:
        n["branch_dimension"] = esc(str(branch_dimension))
    return n

def attr(name, desc, is_config=False) -> dict:
    return {"name": str(name), "desc": esc(desc), "is_config": bool(is_config)}

def op(name, category, expected_results, source_ref, note=None) -> dict:
    if category not in OP_CATEGORIES:
        raise ValueError(f"操作[{name}] category 非法: {category!r}，六枚举 {OP_CATEGORIES}")
    if not expected_results:
        raise ValueError(f"操作[{name}] expected_results 至少 1 条（Step1 契约）")
    if not source_ref:
        raise ValueError(f"操作[{name}] source_ref 必须非空（输入契约，豁免铁律9）")
    return {"name": str(name), "category": category,
            "expected_results": [esc(e) for e in expected_results],
            "source_ref": esc(source_ref), "note": note or N()}

def precond(text, ptype, ref=None) -> dict:
    """铁律12：结构化前置条件。ref 合法性由校验器 C03 兜底（补全或降级）。"""
    if ptype not in PRECOND_TYPES:
        raise ValueError(f"precondition type 非法: {ptype!r}，枚举 {PRECOND_TYPES}")
    if ptype != "state_ref":
        ref = None                                          # event_ref/constraint 的 ref 必为 null
    return {"text": esc(text), "type": ptype, "ref": ref}

def state_ref(entity, dimension, state) -> dict:
    return {"entity": entity, "dimension": dimension, "state": state}
