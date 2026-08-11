#!/usr/bin/env python3
"""v33 Strategy 0 ref_state_dimension 入口锚定回归探针（⑧ 遗留机制锁定）。

当前 coverage_obligations.json 无依赖实体 TO 携带 ref_state_dimension 谓词，
Strategy 0 的谓词消费路径在真实数据上是零行为变化——本探针用合成 TO 证明该
路径是**活代码**（非死分支），并锁定语义：
  1. iter_predicate_state_refs 遍历谓词树产出结构化状态引用（ref_state_dimension
     值解析 / completion.target / selection_range.source_state / occurrence_limit.on
     递归 negation/conjunction/disjunction/when）；
  2. _compute_entry_phase Strategy 0 消费谓词引用：命中主实体主维度状态 → entry
     = 该状态相位 + 1；
  3. 非主维度引用不得误采信（E-SCORE.已提交 非主维度 → 不抬升）；
  4. 谓词引用与 preconditions[].ref 取 max（每个引用都是入口门禁）。

退出码：全部断言通过 → 0，否则 1。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from context.constraint_fields import iter_predicate_state_refs
import nodes.s0_topology as s0


def _entry(tos, phase_table, dep_map=None):
    return s0._compute_entry_phase(
        "E-X", "E-PLAN", "X状态", tos, phase_table,
        dep_map if dep_map is not None else {}, {}, restrict_05=True,
    )


PRIMARY_PT = {
    "primary_entity": "E-PLAN",
    "primary_dimension": "计划状态",
    "state_to_phase": {
        "计划状态": {"已建立": 0, "待启动": 1, "待评审": 2, "评审中": 3,
                     "已完成": 4, "暂停": 4, "结束": 5},
    },
}


def main() -> int:
    # ── 1. iter_predicate_state_refs ─────────────────────────────────
    pred = {"type": "field_equals", "field": {"entity": "E-PLAN", "name": "暂停前计划状态"},
            "value": "评审中", "ref_state_dimension": "E-PLAN.计划状态"}
    assert list(iter_predicate_state_refs(pred)) == [("E-PLAN", "计划状态", "评审中")]

    pred = {"type": "field_in", "field": {"entity": "E-PLAN", "name": "暂停前计划状态"},
            "values": ["待评审", "已完成"], "ref_state_dimension": "E-PLAN.计划状态"}
    assert list(iter_predicate_state_refs(pred)) == [("E-PLAN", "计划状态", "待评审"),
                                                     ("E-PLAN", "计划状态", "已完成")]

    pred = {"type": "completion",
            "target": {"entity": "E-SCORE", "dimension": "打分状态", "state": "已提交"}}
    assert list(iter_predicate_state_refs(pred)) == [("E-SCORE", "打分状态", "已提交")]

    pred = {"type": "occurrence_limit",
            "on": {"entity": "E-PROJ", "dimension": "项目状态", "from": "待选入", "to": "已选入"},
            "limit": 1}
    assert list(iter_predicate_state_refs(pred)) == [("E-PROJ", "项目状态", "已选入")]

    pred = {"type": "negation", "operand": {"type": "conjunction", "parts": [
        {"type": "field_equals", "field": {"entity": "E-PLAN", "name": "暂停前计划状态"},
         "value": "待评审", "ref_state_dimension": "E-PLAN.计划状态"},
        {"type": "completion",
         "target": {"entity": "E-SCORE", "dimension": "打分状态", "state": "已提交"}}]}}
    got = list(iter_predicate_state_refs(pred))
    assert ("E-PLAN", "计划状态", "待评审") in got and ("E-SCORE", "打分状态", "已提交") in got

    # 无 ref_state_dimension 的字段谓词（评级=差）→ 无状态引用
    pred = {"type": "field_equals", "field": {"entity": "E-PROJ", "name": "评级"}, "value": "差"}
    assert list(iter_predicate_state_refs(pred)) == []
    assert list(iter_predicate_state_refs(None)) == []
    assert list(iter_predicate_state_refs([])) == []
    pred = {"type": "field_equals", "field": {"entity": "E-SCORE", "name": "各项打分"}, "value": 0}
    assert list(iter_predicate_state_refs(pred)) == []

    # ── 2. Strategy 0 消费 ref_state_dimension 谓词引用 ──────────────
    tos = [{"id": "T-X1", "entity": "E-X", "dimension": "X状态", "from": "A", "to": "B",
            "preconditions": [{"text": "暂停前计划状态=评审中", "type": "constraint", "ref": None}],
            "constraint_predicate": {
                "type": "field_equals", "field": {"entity": "E-PLAN", "name": "暂停前计划状态"},
                "value": "评审中", "ref_state_dimension": "E-PLAN.计划状态"}}]
    assert _entry(tos, PRIMARY_PT) == 4, "评审中=P3 → entry=3+1=4"

    # 非主维度引用不得抬升
    tos2 = [{"id": "T-X2", "entity": "E-X", "dimension": "X状态", "from": "A", "to": "B",
             "preconditions": [],
             "constraint_predicate": {"type": "completion",
                                      "target": {"entity": "E-SCORE", "dimension": "打分状态",
                                                 "state": "已提交"}}}]
    assert _entry(tos2, PRIMARY_PT) == 0, "非主维度引用不抬升"

    # 谓词引用与前置 ref 取 max
    tos3 = [{"id": "T-X3", "entity": "E-X", "dimension": "X状态", "from": "A", "to": "B",
             "preconditions": [{"text": "评审计划处于待评审状态", "type": "state_ref",
                                "ref": {"entity": "E-PLAN", "dimension": "计划状态",
                                        "state": "待评审"}}],
             "constraint_predicate": {
                 "type": "field_equals", "field": {"entity": "E-PLAN", "name": "暂停前计划状态"},
                 "value": "评审中", "ref_state_dimension": "E-PLAN.计划状态"}}]
    assert _entry(tos3, PRIMARY_PT) == 4, "max(待评审P2, 评审中P3)+1=4"

    print("v33_ref_state_dimension_entry: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
