#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_p1_direction.py — P1 输出的 direction 字段脚本校验。

校验项（对应 P1_Prompt Step 6 校验清单第 13 项）：
1. 每个 transition 必填 direction 字段
2. direction 值合法（forward/backward/lateral/resume）
3. from=null 的创建转换必须为 forward
4. direction=resume 时 from 必须为侧挂状态（lateral 入口目标）
5. direction=lateral 时 to 必须为侧挂状态（被 lateral 进入的状态）
6. direction=backward 时 to 的 states 索引应 < from（除非环状机，note.comment 含"环状机"）
7. direction=forward 时 to 的 states 索引应 > from（除非超时跳级，note.comment 含"超时"）

用法：
    python scripts/validate_p1_direction.py <p1_output.json>
    python scripts/validate_p1_direction.py   # 默认 context/P1_out.json

退出码：0=全部通过，1=有错误
"""
import json
import os
import sys
from pathlib import Path

VALID_DIRECTIONS = {"forward", "backward", "lateral", "resume"}


def load_p1(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_state_index(p1: dict) -> dict:
    """构建 {entity_id: {dimension: {states_list, initial, terminal_set, lateral_states}}}"""
    idx = {}
    for e in p1.get("domain_model", {}).get("entities", []):
        ent_id = e["id"]
        idx[ent_id] = {}
        for d in e.get("state_dimensions", []):
            dim_name = d["dimension_name"]
            states = d.get("states", [])
            idx[ent_id][dim_name] = {
                "states": states,
                "state_index": {s: i for i, s in enumerate(states)},
                "initial": d.get("initial"),
                "terminal": set(d.get("terminal", [])),
                "lateral_states": set(),  # 后面填充
            }
    # 第二遍：找出 lateral 状态（被 lateral 边进入的状态）
    for t in p1.get("state_and_flow", {}).get("transitions", []):
        if t.get("direction") == "lateral":
            ent = t.get("entity")
            dim = t.get("dimension")
            to = t.get("to")
            if ent in idx and dim in idx[ent] and to:
                idx[ent][dim]["lateral_states"].add(to)
    return idx


def validate_transition(t: dict, state_idx: dict, errors: list, warnings: list):
    """校验单个 transition 的 direction 字段。"""
    tid = t.get("id", "?")
    direction = t.get("direction")
    f = t.get("from")
    to = t.get("to")
    entity = t.get("entity")
    dim = t.get("dimension")
    note_comment = (t.get("note") or {}).get("comment", "") if isinstance(t.get("note"), dict) else ""

    # 1. 必填
    if direction is None:
        errors.append(f"{tid}: 缺少 direction 字段（必填）")
        return
    if direction not in VALID_DIRECTIONS:
        errors.append(f"{tid}: direction={direction!r} 不合法，应为 {VALID_DIRECTIONS}")
        return

    # 3. 创建转换必须 forward
    if f is None or f == "(初始)":
        if direction != "forward":
            errors.append(f"{tid}: 创建转换（from=null）direction 必须为 forward，实际为 {direction}")
        return

    # 获取状态索引
    ent_idx = state_idx.get(entity, {})
    dim_info = ent_idx.get(dim)
    if not dim_info:
        return  # 实体/维度不在索引里，其他校验会管

    si = dim_info["state_index"]
    lateral_states = dim_info["lateral_states"]

    # 4. resume 时 from 必须为侧挂状态
    if direction == "resume":
        if f not in lateral_states:
            warnings.append(f"{tid}: direction=resume 但 from={f!r} 不是侧挂状态（lateral 入口目标）")

    # 5. lateral 时 to 必须为侧挂状态
    if direction == "lateral":
        if to not in lateral_states:
            warnings.append(f"{tid}: direction=lateral 但 to={to!r} 未被任何 lateral 边指向")

    # 6. backward 时 to 索引应 < from（除非环状机）
    if direction == "backward" and f in si and to in si:
        if si[to] >= si[f] and "环状机" not in note_comment:
            warnings.append(
                f"{tid}: direction=backward 但 to={to!r}(idx={si[to]}) 索引 >= from={f!r}(idx={si[f]})，"
                f"且 note.comment 未注明'环状机'"
            )

    # 7. forward 时 to 索引应 > from（除非超时跳级）
    if direction == "forward" and f in si and to in si:
        if si[to] <= si[f] and "超时" not in note_comment and "环状机" not in note_comment:
            warnings.append(
                f"{tid}: direction=forward 但 to={to!r}(idx={si[to]}) 索引 <= from={f!r}(idx={si[f]})，"
                f"且 note.comment 未注明'超时'或'环状机'"
            )


def validate(p1: dict) -> tuple[list[str], list[str]]:
    """返回 (errors, warnings)。"""
    errors, warnings = [], []
    transitions = p1.get("state_and_flow", {}).get("transitions", [])
    if not transitions:
        errors.append("state_and_flow.transitions 为空或缺失")
        return errors, warnings

    state_idx = build_state_index(p1)

    # 统计 direction 覆盖
    total = len(transitions)
    with_direction = sum(1 for t in transitions if t.get("direction"))

    for t in transitions:
        validate_transition(t, state_idx, errors, warnings)

    # 汇总信息
    from collections import Counter
    dir_dist = Counter(t.get("direction", "MISSING") for t in transitions)
    print(f"Transition direction 覆盖: {with_direction}/{total}")
    print(f"Direction 分布: {dict(dir_dist)}")
    print(f"Errors: {len(errors)}, Warnings: {len(warnings)}")

    return errors, warnings


def main():
    if len(sys.argv) >= 2:
        p1_path = sys.argv[1]
    else:
        # 默认路径
        script_dir = Path(__file__).resolve().parent
        p1_path = str(script_dir.parent / "context" / "P1_out.json")

    if not os.path.exists(p1_path):
        print(f"ERROR: P1 output not found: {p1_path}")
        sys.exit(1)

    print(f"Validating P1 direction: {p1_path}")
    print("=" * 60)

    p1 = load_p1(p1_path)
    errors, warnings = validate(p1)

    if errors:
        print("\n=== ERRORS (必须修复) ===")
        for e in errors:
            print(f"  ✗ {e}")
    else:
        print("\n✓ 无错误")

    if warnings:
        print("\n=== WARNINGS (建议检查) ===")
        for w in warnings[:20]:
            print(f"  ⚠ {w}")
        if len(warnings) > 20:
            print(f"  ... 还有 {len(warnings) - 20} 条 warning")
    else:
        print("\n✓ 无警告")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
