#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v29 数据访问层统一 accessor.

修复"位置假设 bug":
  validator 和消费端假设 valid_combinations 长在 BD 上,
  但 LLM 实际把它放在 transition 对象上(实验 3 发现).

所有读 valid_combinations 的地方都走 get_valid_combinations().
"""
from __future__ import annotations

from typing import Any


def _flatten_combinations(vc_list: list) -> list[dict]:
    """兼容包装层 {transition, combinations} 和扁平层 [{...}]."""
    result = []
    for item in vc_list or []:
        if isinstance(item, dict) and "combinations" in item:
            for combo in item.get("combinations", []) or []:
                if isinstance(combo, dict):
                    result.append(combo)
        elif isinstance(item, dict):
            result.append(item)
    return result


def _normalize_combo(c: Any) -> dict:
    return c if isinstance(c, dict) else {}


def get_valid_combinations(bd: dict, transitions: list[dict]) -> list[dict]:
    """统一 accessor.

    LLM 可能把 valid_combinations 放在两处之一:
    - branch_dimensions[i].valid_combinations (旧假设)
    - transition[j].valid_combinations (实验 3 实际位置)

    两处都查,合并,按 dim 过滤.

    Args:
        bd: branch_dimension dict, 含 dimension/values/coverage
        transitions: list of transition dicts

    Returns:
        list of normalized combination dicts, e.g. [{"项目类型": "重点项目"}]
        只含属于当前 BD 的组合.
    """
    dim = bd.get("dimension", "")
    if not dim:
        return []
    combos: list[dict] = []

    # 位置1: 长在 BD 上 (旧假设)
    for c in bd.get("valid_combinations", []) or []:
        for norm in _flatten_combinations([c]):
            if dim in norm:
                combos.append(norm)

    # 位置2: 长在 transition 上 (实验 3 实际位置)
    for t in transitions:
        vc = t.get("valid_combinations")
        if not vc:
            continue
        for norm in _flatten_combinations(vc if isinstance(vc, list) else [vc]):
            if dim in norm:
                combos.append(norm)

    return combos


def get_valid_combinations_for_tid(
    bd: dict, transitions: list[dict], tid: str
) -> list[dict]:
    """获取某个 transition 在某 BD 上的合法组合.

    Returns:
        list of combos for this tid under this BD
    """
    dim = bd.get("dimension", "")
    if not dim:
        return []
    combos: list[dict] = []

    # 位置1: BD.valid_combinations 里 transition == tid
    for vc in bd.get("valid_combinations", []) or []:
        if isinstance(vc, dict) and vc.get("transition") == tid:
            for combo in vc.get("combinations", []) or []:
                if isinstance(combo, dict) and dim in combo:
                    combos.append(combo)

    # 位置2: transition[tid].valid_combinations
    for t in transitions:
        if t.get("id") != tid:
            continue
        vc = t.get("valid_combinations")
        if not vc:
            continue
        for norm in _flatten_combinations(vc if isinstance(vc, list) else [vc]):
            if dim in norm:
                combos.append(norm)
        break  # 找到 tid 就停

    return combos


def has_valid_combinations(bd: dict, transitions: list[dict], tid: str) -> bool:
    """快速检查某个 tid 在某 BD 下是否有声明."""
    return len(get_valid_combinations_for_tid(bd, transitions, tid)) > 0


if __name__ == "__main__":
    # 用实验 3 数据自测
    import json
    p1 = json.load(open("/home/z/my-project/scripts/llm_p1_output/p1_exp3_review_assembled.json"))
    bds = p1["_meta"].get("branch_dimensions", [])
    trans = p1["state_and_flow"]["transitions"]

    for bd in bds:
        dim = bd["dimension"]
        all_combos = get_valid_combinations(bd, trans)
        print(f"BD {dim}: 收集到 {len(all_combos)} 个组合")
        for c in all_combos:
            print(f"  {c}")
        for tid in (bd.get("coverage") or {}).get("transitions", []):
            tid_combos = get_valid_combinations_for_tid(bd, trans, tid)
            print(f"  tid={tid}: {len(tid_combos)} 个组合 → {tid_combos}")
