#!/usr/bin/env python3
"""T-002 分支拆分 — 第一性原理: 从 constraint_predicate 数据派生变体 (非硬编码).

算法 (全数据驱动, 零 LLM):
  1. 扫描 transition_obligations, 找出所有 branch_path=[] 且 constraint_predicate
     为 compound (conjunction 含多 part) 的 TO (当前仅 T-002)。
  2. 从 constraint_predicate 提取:
      - branch 字段: 多个 part 引用的公共 field (评级)
      - 约束值: 各 part 中 field_equals 的 value (差, 不合格)
      - part→value 映射: 哪个 predicate part 约束哪个值
  3. 从 _context.branch_dimensions 查该字段的全量合法值。
  4. 按值分组:
      - 每个约束值 → 独立变体 (constraint_predicate = 仅该值的 part)
      - 剩余值 (约束值之外的全量值) → catch-all 变体 (constraint_predicate=null)
  5. 约束文本路由: precondition type=constraint 的文本按关键词匹配到变体。
  6. 约束值按 constraint_predicate parts 出现顺序定序 (源顺序, 确定性);
     ID 按 [a][b][c] 后缀; action 追加 [分支维=值] 后缀。
  7. 更新 _context.transition_splits, branch_dimensions; RO-IT 吸收指针
     按 reason 关键词路由到变体。
  8. 字节精确写回 (CRLF)。

确定性: 纯 JSON 变换, 不调 LLM; 双跑结果一致 (idempotent: 二次跑安全中止).

运行: python scripts/t2_branch_split.py
"""
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CM_PATH = ROOT / "coverage_obligations.json"

# ── constraint_predicate 提取工具 ──────────────────────────────────────────


def _field_key(part: dict) -> str | None:
    """提取 part 引用的字段键: 'entity.field' (如 'E-PROJ.评级')。"""
    f = _field_from_part(part)
    if f:
        return f"{f.get('entity', '')}.{f.get('name', '')}"
    return None


def _field_from_part(part: dict) -> dict | None:
    """从 predicate part 提取引用的 field dict。"""
    t = part.get("type")
    if t == "field_equals":
        return part.get("field")
    if t == "negation":
        return _field_from_part(part.get("operand", {}))
    if t == "occurrence_limit":
        w = part.get("when")
        return _field_from_part(w) if isinstance(w, dict) else None
    if t == "field_in":
        return part.get("field")
    if t == "field_range":
        return part.get("field")
    return None


def _part_values(part: dict) -> set[str]:
    """提取 predicate part 约束的离散值集合。"""
    t = part.get("type")
    if t == "field_equals":
        return {part.get("value", "")}
    if t == "negation":
        return _part_values(part.get("operand", {}))
    if t == "occurrence_limit":
        w = part.get("when")
        return _part_values(w) if isinstance(w, dict) else set()
    if t == "field_in":
        return set(part.get("values", []))
    # field_range / unparsed / aggregate_count: no discrete values to split on
    return set()


def _part_constrains_value(part: dict, value: str) -> bool:
    """该 predicate part 是否约束 value 这个离散值?"""
    return value in _part_values(part)


def _find_compound_tos(tos: list[dict]) -> list[dict]:
    """找出所有未拆分支 + compound constraint_predicate 的 TO。"""
    candidates = []
    for to in tos:
        if to.get("branch_path") or not to.get("constraint_predicate"):
            continue
        cp = to["constraint_predicate"]
        if cp.get("type") != "conjunction":
            continue
        parts = cp.get("parts", [])
        if len(parts) < 2:
            continue
        # 检查是否有多个 part 引用同一字段的不同值
        value_map: dict[str, set[str]] = {}
        for p in parts:
            fk = _field_key(p)
            if fk:
                value_map.setdefault(fk, set()).update(_part_values(p))
        # 只有至少一个字段被多个 part 以不同值引用才视为可拆分
        for fk, vals in value_map.items():
            if len(vals) >= 2:
                candidates.append(to)
                break
    return candidates


def _match_constraint_texts(texts: list[dict], values: set[str]) -> dict[str, list]:
    """将 precondition type=constraint 文本按关键词匹配到值。

    返回 {value: [precond dict, ...]}.
    匹配规则: 约束文本包含该值名称 → 归入该值变体。
    """
    result: dict[str, list] = defaultdict(list)
    for prec in texts:
        if prec.get("type") != "constraint":
            continue
        txt = prec.get("text", "")
        matched = False
        for v in values:
            if v in txt:
                result[v].append(prec)
                matched = True
                break
        if not matched:
            # 无法匹配 → 归入第一个值 (安全网, 当前数据不会触发)
            first = next(iter(values)) if values else ""
            if first:
                result[first].append(prec)
    return dict(result)


def _derive_catchall_value(all_values: list[str], constrained: set[str]) -> str:
    """从已约束值 vs 全量值派生 catch-all 值标签。

    例: all_values=[优秀,良好,合格,不合格,差], constrained={差,不合格}
         → unconstrained={优秀,良好,合格} → "优秀/良好/合格"
    """
    unconstrained = [v for v in all_values if v not in constrained]
    return "/".join(unconstrained) if unconstrained else "其他"


# ── 主逻辑 ─────────────────────────────────────────────────────────────────


def main() -> int:
    raw = Path(CM_PATH).read_bytes()
    data = json.loads(raw.decode("utf-8"))

    # 1) 往返字节一致校验
    probe = json.dumps(data, ensure_ascii=False, indent=2).replace("\n", "\r\n")
    if probe.encode("utf-8") != raw:
        print("[ABORT] round-trip mismatch: 源文件格式与 dump 参数不符, 中止")
        return 1

    tos = data.get("transition_obligations")
    if not isinstance(tos, list):
        print("[ABORT] transition_obligations 不是列表, 中止")
        return 1

    candidates = _find_compound_tos(tos)
    if not candidates:
        print("[OK] 没有需要拆分的 compound constraint_predicate TO, 中止")
        return 0
    print(f"[SCAN] 发现 {len(candidates)} 个待拆分 TO: "
          f"{[t['id'] for t in candidates]}")

    # 2) 获取 branch_dimensions 的值域
    ctx = data.get("_context", {})
    branch_dims = {bd["dimension"]: bd for bd in ctx.get("branch_dimensions", [])}

    total_added = 0
    for to in candidates:
        cp = to["constraint_predicate"]
        parts = cp["parts"]

        # 2a) 确定分支字段: 取被多个 part 引用的公共字段
        field_value_map: dict[str, set[str]] = {}
        for p in parts:
            fk = _field_key(p)
            if fk:
                field_value_map.setdefault(fk, set()).update(_part_values(p))

        # 选出现值最多的字段作为分支维
        branch_field_key = max(field_value_map, key=lambda k: len(field_value_map[k]))
        constrained_values = field_value_map[branch_field_key]
        # 从 field_key 提取维度名 (E-PROJ.评级 → 项目评级)
        # 查 branch_dimensions 找到匹配的维度
        branch_dim_name = None
        all_values: list[str] = []
        for dim_name, bd in branch_dims.items():
            for b in bd.get("branches", []):
                if b.get("target_transition") == to["id"]:
                    branch_dim_name = dim_name
                    all_values = bd.get("values", [])
                    break
            if branch_dim_name:
                break
        # fallback: 用 field_key 的 name 部分猜维度名
        if not branch_dim_name:
            field_name = branch_field_key.rsplit(".", 1)[-1]  # 评级
            for dim_name, bd in branch_dims.items():
                if field_name in dim_name:
                    branch_dim_name = dim_name
                    all_values = list(bd.get("values", []))
                    break

        print(f"\n[SPLIT] {to['id']}: 分支维={branch_dim_name}, "
              f"约束值={sorted(constrained_values)}, 全量值={all_values}")

        # 2b) 约束值按 parts 出现顺序定序 (数据驱动, 确定性, 保持源顺序)
        ordered_values: list[str] = []
        _seen = set()
        for p in parts:
            for v in sorted(_part_values(p)):
                if v in constrained_values and v not in _seen:
                    _seen.add(v)
                    ordered_values.append(v)
        for v in sorted(constrained_values):  # 安全网: 补漏 (不应触发)
            if v not in _seen:
                ordered_values.append(v)
        constrained_ordered = ordered_values

        # 2c) 分组: 每个约束值一个 part 组
        value_parts: dict[str, list] = defaultdict(list)
        for p in parts:
            for v in constrained_ordered:
                if _part_constrains_value(p, v):
                    value_parts[v].append(p)
                    break
            else:
                # part 不约束任何离散值 → 归入 "其他" (当前数据无此情况)
                pass

        # 2d) 约束文本路由
        constraint_preconds = [
            p for p in to.get("preconditions", [])
            if p.get("type") == "constraint"
        ]
        text_assign = _match_constraint_texts(constraint_preconds, constrained_ordered)

        # 2e) 生成变体
        variant_defs = []
        suffixes = "abcdefghijklmnopqrstuvwxyz"
        for idx, v in enumerate(constrained_ordered):
            variant_defs.append({
                "id": f"{to['id']}[{suffixes[idx]}]",
                "value": v,
                "parts": value_parts.get(v, []),
                "constraint_texts": text_assign.get(v, []),
            })

        # catch-all
        catchall_value = _derive_catchall_value(all_values, set(constrained_ordered))
        variant_defs.append({
            "id": f"{to['id']}[{suffixes[len(constrained_ordered)]}]",
            "value": catchall_value,
            "parts": [],  # null predicate
            "constraint_texts": [],  # no constraint text for catch-all
        })

        # 2e) 构建 TO dicts
        new_tos = []
        for vd in variant_defs:
            new_to = {k: v for k, v in to.items()
                      if k not in ("id", "action", "risk_traits", "branch_path",
                                   "note", "preconditions", "constraint_predicate",
                                   "expected_results")}
            new_to["id"] = vd["id"]
            # action 追加 [维度=值] 后缀 (已存在的 [维度=值] 先 strip)
            action = to.get("action", "")
            action = re.sub(r"\s*\[[^\]]+\]\s*$", "", action).strip()
            new_to["action"] = f"{action} [{branch_dim_name}={vd['value']}]" if branch_dim_name else action

            new_to["risk_traits"] = (to.get("risk_traits") or []) + ["branch"]
            # 去重 risk_traits
            seen_rt = set()
            new_to["risk_traits"] = [rt for rt in new_to["risk_traits"]
                                     if not (rt in seen_rt or seen_rt.add(rt))]

            new_to["branch_path"] = [{"dimension": branch_dim_name, "value": vd["value"]}]

            note = dict(to.get("note") or {})
            note["branch_dimension"] = branch_dim_name
            new_to["note"] = note

            # preconditions: state_ref + event_ref (passthrough) + routed constraint texts
            passthrough = [p for p in to.get("preconditions", [])
                           if p.get("type") != "constraint"]
            new_to["preconditions"] = passthrough + [
                dict(ct) for ct in vd["constraint_texts"]
            ]

            # constraint_predicate
            if vd["parts"]:
                if len(vd["parts"]) == 1:
                    new_to["constraint_predicate"] = vd["parts"][0]
                else:
                    new_to["constraint_predicate"] = {"type": "conjunction", "parts": vd["parts"]}
            else:
                new_to["constraint_predicate"] = None

            # expected_results
            new_to["expected_results"] = list(to.get("expected_results") or [])

            new_tos.append(new_to)

        # 2f) 替换原 TO
        idx = tos.index(to)
        tos[idx:idx + 1] = new_tos
        count = len(new_tos)
        total_added += count - 1

        # 2g) 更新 _context
        splits = ctx.setdefault("transition_splits", {})
        splits[to["id"]] = [vt["id"] for vt in new_tos]

        if branch_dim_name and branch_dim_name in branch_dims:
            bd = branch_dims[branch_dim_name]
            for vt in new_tos:
                bd.setdefault("branches", []).append({
                    "value": vt["branch_path"][0]["value"],
                    "target_transition": vt["id"],
                    "desc": f"{vt['branch_path'][0]['value']}：{vt['action']}",
                })

        # 2h) RO-IT 吸收指针: 按 RO reason 关键词匹配到变体值 (与约束文本路由同机制)
        for ro in data.get("constraint_obligations", []):
            if ro.get("absorbed_by_transition") == to["id"]:
                reason = ro.get("reason", "")
                target = None
                for vd in variant_defs:
                    if vd["value"] and vd["value"] in reason:
                        target = next(t for t in new_tos if t["id"] == vd["id"])
                        break
                if target is None:  # 安全网: 无关键词命中 → 默认第一个变体
                    target = new_tos[0]
                ro["absorbed_by_transition"] = target["id"]
                print(f"  {ro['id']}: absorbed_by_transition → {target['id']}")

        tot = len(tos)
        ids = [vt["id"] for vt in new_tos]
        print(f"  → {ids} (total TOs: {tot})")

    # 3) 安全网
    for to in candidates:
        remaining = {t["id"] for t in tos if isinstance(t, dict)}
        assert to["id"] not in remaining, f"{to['id']} still present after split!"

    # 4) 写回
    out = json.dumps(data, ensure_ascii=False, indent=2).replace("\n", "\r\n")
    Path(CM_PATH).write_bytes(out.encode("utf-8"))
    print(f"\n[OK] 写回 {CM_PATH} ({len(out)} bytes, net +{total_added} TOs, "
          f"total {len(tos)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
