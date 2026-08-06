#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Constraint-referenced semantic field registry (Step 3).

P2 的 79 条 constraint 前提引用了 9 个领域字段，而实体表单属性模型并未携带它们
（E-PROJ 属性只有 技术领域/项目类型；被引用的概念是评价产物、计数、状态快照，
不是表单字段）。本模块是这些字段的单一事实源。

消费方：
  - P2 constraint 谓词解析器（context/generate_obligation_model.py）把谓词里的
    `field` 引用 {entity, name} 对照本表解析，归一化别名（优→优秀、评价结果→评级）。
  - phase 下界从不硬编码进字段记录。由 field_phase_lower_bound() 在运行时对照
    **当前** dep_state_phase_map（Step 1 shift 之后）推导——见 completion / E-SCORE.
    已提交：P2 局部相位是 2，Step 1 锚定后 shift 到 4；硬编码 2 是错的，所以字段
    存"被填充的状态锚点"，不存相位数字。

三个裁定/补充（schema 审查结论）在此落地：
  - D1 统一：评级 与 评价结果 合并为一个逻辑字段（scope=per_phase 保留阶段语义）。
  - 暂停前计划状态 显式标注值域闭集 {待评审, 评审中, 已完成}（业务可暂停来源，
    不是 E-PLAN.计划状态 全量态名）。
  - occurrence_limit 的 on 引用改为语义特征 {entity, dimension, from, to}，
    不硬编码 transition ID（解析器侧约定，见模块尾 PREDICATE_RULES）。
  - disjunction_ref 未展开引用的下界 = P0 保守值，resolved=False（见 PREDICATE_RULES）。
"""

from __future__ import annotations

# ── 字段记录 ────────────────────────────────────────────────────────────
# 结构：
#   entity / name            引用键（谓词 field 引用按 "entity.name" 解析）
#   aliases                  同义拼写/别名，全部归一化到本条
#   kind                     attribute | state_snapshot | counter | config
#   values                   取值域；None = 无约束（数值/计数）
#   value_normalization      拼写归一映射（优→优秀 等）
#   scope                    per_phase（每阶段评价）| once | accumulating
#   populated_anchors        字段被写入的状态锚点列表；下界 = min(各锚点 phase)
#   ref_state_dimension      仅 state_snapshot：取值域来源的状态维度
#   value_closed_set         仅 state_snapshot：显式闭集（业务可取值，非全量态名）
#   desc                     语义说明
#   maps_to                  对应的既有表单属性/配置项（若有）

FIELD_REGISTRY: dict[str, dict] = {
    # D1 统一：评级 == 评价结果（同一评审产物，5 级量表，拼写不一致）
    "E-PROJ.评级": {
        "entity": "E-PROJ",
        "name": "评级",
        "aliases": ["评价结果"],
        "kind": "attribute",
        "values": ["优秀", "良好", "合格", "不合格", "差"],
        "value_normalization": {"优": "优秀", "良": "良好"},
        "scope": "per_phase",
        "populated_anchors": [
            {"entity": "E-PROJ", "dimension": "项目状态", "state": "待归档",
             "reason": "评审定级——每个项目阶段的评价产物（评价结果/评级同一字段）"},
        ],
        "ref_state_dimension": None,
        "value_closed_set": None,
        "maps_to": None,
        "desc": "项目每阶段评审定级；T-044 计数锚点（评价结果为优累计10次）与 T-007 门控（评级=优秀）指向同一字段。",
    },
    # 别名键：评价结果 → 评级（不重复存记录，只做解析路径）
    "E-PROJ.评价结果": {
        "entity": "E-PROJ",
        "name": "评价结果",
        "aliases": [],
        "kind": "alias",
        "canonical": "E-PROJ.评级",
        "values": None,
        "value_normalization": {},
        "scope": "per_phase",
        "populated_anchors": [],
        "ref_state_dimension": None,
        "value_closed_set": None,
        "maps_to": "E-PROJ.评级",
        "desc": "评价结果 的别名注册键，解析时归一到 E-PROJ.评级。",
    },
    "E-PROJ.选入次数": {
        "entity": "E-PROJ",
        "name": "选入次数",
        "aliases": [],
        "kind": "counter",
        "values": None,
        "value_normalization": {},
        "scope": "once",
        "populated_anchors": [
            {"entity": "E-PROJ", "dimension": "项目状态", "state": "待选入",
             "reason": "每次 待选入→已选入 递增（occurrence_limit：不合格评价结果仅1次选入机会）"},
        ],
        "ref_state_dimension": None,
        "value_closed_set": None,
        "maps_to": None,
        "desc": "项目被选入评审计划的累计次数，occurrence_limit 计数对象。",
    },
    "E-PLAN.评审组人数": {
        "entity": "E-PLAN",
        "name": "评审组人数",
        "aliases": ["专家人数"],
        "kind": "config",
        "values": [5, 7, 9],
        "value_normalization": {},
        "scope": "once",
        "populated_anchors": [
            {"entity": "E-PLAN", "dimension": "计划状态", "state": "已建立",
             "reason": "评审计划建立时配置评审组规模"},
        ],
        "ref_state_dimension": None,
        "value_closed_set": None,
        "maps_to": "E-PLAN.专家人数",  # 既有 attribute_config 配置项
        "desc": "评审组专家规模，5/7/9；对应既有 E-PLAN.专家人数 配置属性。",
    },
    "E-PLAN.组长专家数": {
        "entity": "E-PLAN",
        "name": "组长专家数",
        "aliases": [],
        "kind": "config",
        "values": [1],
        "value_normalization": {},
        "scope": "once",
        "populated_anchors": [
            {"entity": "E-PLAN", "dimension": "计划状态", "state": "已建立",
             "reason": "计划建立时指定唯一组长"},
        ],
        "ref_state_dimension": None,
        "value_closed_set": None,
        "maps_to": None,
        "desc": "组长专家数量，恒为 1（有且只能有一个组长）。",
    },
    "E-PLAN.暂停前计划状态": {
        "entity": "E-PLAN",
        "name": "暂停前计划状态",
        "aliases": [],
        "kind": "state_snapshot",
        "values": None,
        "value_normalization": {},
        "scope": "once",
        "populated_anchors": [
            {"entity": "E-PLAN", "dimension": "计划状态", "state": "待评审",
             "reason": "暂停发生时快照；可暂停来源态的最早者（待评审）"},
            {"entity": "E-PLAN", "dimension": "计划状态", "state": "评审中",
             "reason": "暂停来源态之二"},
            {"entity": "E-PLAN", "dimension": "计划状态", "state": "已完成",
             "reason": "暂停来源态之三"},
        ],
        "ref_state_dimension": "E-PLAN.计划状态",
        # 显式闭集：业务上只有这三个状态可暂停，不是 E-PLAN.计划状态 全量态名
        "value_closed_set": ["待评审", "评审中", "已完成"],
        "maps_to": None,
        "desc": "暂停时刻记录的前一状态，恢复时据此回跳；值域闭集 = 可暂停来源态。",
    },
    "E-PLAN.评审计划超时类型": {
        "entity": "E-PLAN",
        "name": "评审计划超时类型",
        "aliases": [],
        "kind": "attribute",
        "values": ["下发", "启动", "评审", "归档"],
        "value_normalization": {},
        "scope": "once",
        "populated_anchors": [
            {"entity": "E-PLAN", "dimension": "计划状态", "state": "已建立",
             "reason": "下发超时触发点（T-018 已建立→待启动）——超时类型最早写入点"},
            {"entity": "E-PLAN", "dimension": "计划状态", "state": "待启动",
             "reason": "启动超时触发点（T-020）"},
            {"entity": "E-PLAN", "dimension": "计划状态", "state": "待评审",
             "reason": "评审超时触发点（T-029）"},
            {"entity": "E-PLAN", "dimension": "计划状态", "state": "已完成",
             "reason": "归档超时触发点（T-033）"},
        ],
        "ref_state_dimension": None,
        "value_closed_set": None,
        "maps_to": None,
        "desc": "超时发生时记录的时段类型；字段级下界 = min 触发点 = 已建立(0)（值级细化可后置）。",
    },
    "E-SCORE.各项打分": {
        "entity": "E-SCORE",
        "name": "各项打分",
        "aliases": [],
        "kind": "attribute",
        "values": None,  # 数值
        "value_normalization": {},
        "scope": "once",
        "populated_anchors": [
            {"entity": "E-SCORE", "dimension": "打分状态", "state": "已保存",
             "reason": "专家打分落库（未打分→已保存）"},
        ],
        "ref_state_dimension": None,
        "value_closed_set": None,
        "maps_to": None,
        "desc": "专家对项目的各项打分；completion/聚合判定（各项全为零不可提交、全部专家提交）的数值来源。",
    },
    "E-USER.连续密码错误次数": {
        "entity": "E-USER",
        "name": "连续密码错误次数",
        "aliases": [],
        "kind": "counter",
        "values": None,
        "value_normalization": {},
        "scope": "accumulating",
        "populated_anchors": [
            {"entity": "E-USER", "dimension": "锁定状态", "state": "未锁定",
             "reason": "登录失败在未锁定侧累积；达到 3 次 → 锁定"},
        ],
        "ref_state_dimension": None,
        "value_closed_set": None,
        "maps_to": None,
        "desc": "普通用户连续密码错误计数（连续 3 次 → 锁定）；aggregate_count 的 consecutive 变体。",
    },
}


def resolve_field(field_ref: dict) -> dict | None:
    """按 {entity, name} 解析字段记录；别名（评价结果→评级、专家人数→评审组人数）
    归一化到 canonical 记录。返回 None 表示未注册。"""
    entity = (field_ref or {}).get("entity")
    name = (field_ref or {}).get("name")
    if not entity or not name:
        return None
    rec = FIELD_REGISTRY.get(f"{entity}.{name}")
    if rec is None:
        return None
    if rec.get("kind") == "alias":
        rec = FIELD_REGISTRY.get(rec.get("canonical"))
    return rec


def field_phase_lower_bound(field_ref: dict, dep_state_phase_map: dict | None,
                            phase_table: dict | None = None) -> int | None:
    """字段 phase 下界 = min(各 populated_anchor 的 phase)，对照**当前**
    （Step 1 shift 之后）的相位表解析。

    相位表分层：主实体的态相位在 phase_table.state_to_phase（按维度键控），
    依赖实体的态相位在 dep_state_phase_map（按实体键控）。两表都要查——
    E-PLAN 是主实体（计划状态），只查 dep_state_phase_map 会全部落空。

    语义规则（schema 第 4 节映射表）：谓词下界从字段生命周期推导，不存进字段。
    任一锚点不可解析 → 返回 None（消费方回退保守 P0，见 PREDICATE_RULES）。
    """
    rec = resolve_field(field_ref)
    if rec is None:
        return None
    anchors = rec.get("populated_anchors") or []
    if not anchors:
        return None
    dmap = dep_state_phase_map or {}
    pt = phase_table or {}
    primary_entity = pt.get("primary_entity")
    stp = pt.get("state_to_phase") or {}
    phases: list[int] = []
    for a in anchors:
        ph = None
        ent_dims = dmap.get(a["entity"], {})
        if ent_dims:
            ph = ent_dims.get(a["dimension"], {}).get(a["state"])
        if ph is None and a["entity"] == primary_entity:
            # 主实体：相位在 phase_table.state_to_phase（按维度键控）
            ph = stp.get(a["dimension"], {}).get(a["state"])
        if ph is None:
            return None
        phases.append(int(ph))
    return min(phases)


# ── 谓词级规则（解析器侧约定，Schema 审查补充） ────────────────────────────
PREDICATE_RULES = {
    # disjunction_ref：引用未展开的规则列表（满足降级规则任一条）。
    # v1 确定性行为：phase 下界 = P0 保守值（不抬升），resolved=False，
    # 下游（Guard 6 / Step 4）不得把这条谓词当硬约束。
    "disjunction_ref": {
        "default_phase": 0,
        "resolved": False,
        "resolved_marker": "resolved",
    },
    # completion：下界 = 完成态 phase，按 dep_state_phase_map 当前值取
    #（E-SCORE.已提交 Step 1 后 = 4，非 P2 局部值 2）。
    "completion_phase_rule": "target_state_phase",
    # occurrence_limit：on 引用用语义特征，不硬编码 transition ID。
    "occurrence_limit_on_ref": {"entity": None, "dimension": None, "from": None, "to": None},
}
