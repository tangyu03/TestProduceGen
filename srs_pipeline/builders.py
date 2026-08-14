"""通用构造函数。在数据写入期就 fail-fast 拦截枚举/契约错误，比留到 Step6 再报更早。"""
from __future__ import annotations

import warnings

from .constants import OP_CATEGORIES, PRECOND_TYPES
from .escape import esc

def N(inferred=False, comment="", conflict="", branch_dimension="", role=None) -> dict:
    n = {"inferred": bool(inferred)}                       # note 键规范：inferred 必填
    if comment:
        n["comment"] = esc(str(comment))
    if conflict:
        n["conflict"] = esc(str(conflict))
    if branch_dimension:
        n["branch_dimension"] = esc(str(branch_dimension))
    if role:
        n["role"] = role                                   # C18 输入契约：op note 须含 role
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
    note = note or N()
    if not isinstance(note, dict) or not note.get("role"):
        # C18 输入契约：op note 须含 role。build 期尽早提示（不阻断），
        # assemble 后校验器仍以 error 级兜底（validate.py c18_inv_operations_role）。
        warnings.warn(f"op[{name}] note 缺 role 字段，assemble 的 C18 校验将报 error",
                      stacklevel=2)
    return {"name": str(name), "category": category,
            "expected_results": [esc(e) for e in expected_results],
            "source_ref": esc(source_ref), "note": note}

def precond(text, ptype, ref=None, note=None) -> dict:
    """铁律12：结构化前置条件。ref 合法性由校验器 C03 兜底（补全或降级）。"""
    if ptype not in PRECOND_TYPES:
        raise ValueError(f"precondition type 非法: {ptype!r}，枚举 {PRECOND_TYPES}")
    if ptype != "state_ref":
        ref = None                                          # event_ref/constraint 的 ref 必为 null
    p = {"text": esc(text), "type": ptype, "ref": ref}
    if note:
        if isinstance(note, str):                           # 可选注解，校验器 C03 以 .get 访问
            p["note"] = {"comment": esc(note)}
        else:
            p["note"] = dict(note)
            if p["note"].get("comment"):
                p["note"]["comment"] = esc(str(p["note"]["comment"]))
    return p

def state_ref(entity, dimension, state) -> dict:
    return {"entity": entity, "dimension": dimension, "state": state}
