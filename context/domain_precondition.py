"""领域前置派生 — CRUD/查看义务的"对象实例须已存在"先决 (Tier 2).

单一事实源: 从 S0 派生的 topology_levels 判别业务生命周期对象, 从 P2 数据层
的创建转换 (from=None) 派生对象存在性锚定。被 S1 (Given 生成 + 相位底) 与
S3 (Guard 7 依赖绑定) 消费, 不硬编码任何领域名词。

不变量: 管理类实体 (topology_level 0, 专家/角色/机构/用户/日志/配置) 保持
"=存在" 弱 Given 是合理的, 不做领域前置。

语义 (与 DECISIONS ⑭/⑱ 一致):
  - 对实体 E 的非创建操作 (查看/修改/删除), 仅在 E 的实例已存在时语义有效。
  - "已存在" = E 的创建转换已触发 = E 处于创建转换的 to_state。
  - E-ATT (附件) 无自身创建转换 → 用 composition 父实体 (E-PROJ) 的创建转换。
"""
from __future__ import annotations

from context.constraint_fields import get_state_phase


def lifecycle_entity_ids(state: dict) -> set[str]:
    """业务生命周期对象 = topology_level > 0 的实体 (数据驱动, 非名字硬编码).

    S0 已把 {E-PLAN:1, E-PROJ:1, E-ATT:2, E-SCORE:1} 标为 >0, 管理类全为 0。
    """
    topo = state.get("topology_levels") or {}
    return {e for e, lvl in topo.items() if isinstance(lvl, int) and lvl > 0}


def creation_transitions(cm: dict, entity: str) -> list[dict]:
    """实体的创建转换 = from is None 的转换 (实例诞生的唯一入口)。"""
    tos = cm.get("transition_obligations", []) or []
    return [t for t in tos if t.get("entity") == entity and t.get("from") is None]


def _to_state_phase(t: dict, state: dict) -> int:
    return (
        get_state_phase(
            t.get("entity"), t.get("dimension"), t.get("to"),
            state.get("dep_state_phase_map"), state.get("phase_table"),
        )
        or 0
    )


def _anchor_creation(cm: dict, state: dict, entity: str) -> dict | None:
    """存在性锚定创建转换: 最早 to_state 相位, 平局按 id 升序 (确定性)。

    E-PROJ 有两个创建转换 (T-001 项目状态→待选入, T-013 项目阶段→开题),
    锚定在相位最早的那个 (待选入), 保证 "项目已存在" 挂在主生命周期上。
    """
    cands = creation_transitions(cm, entity)
    if not cands:
        return None
    return sorted(cands, key=lambda t: (_to_state_phase(t, state), t.get("id", "")))[0]


def _composition_parent(cm: dict, entity: str) -> str | None:
    """composition 父实体: structural_relations 中 to==entity 的 from (子→父)。"""
    for sr in cm.get("_context", {}).get("structural_relations", []) or []:
        if sr.get("relation_type") == "composition" and sr.get("to") == entity:
            return sr.get("from")
    return None


def object_existence(cm: dict, state: dict, entity: str) -> dict | None:
    """为实体派生"对象实例须已存在"的领域前置。

    Returns None (管理类实体 / 无创建转换 / S0 未跑) 或:
      object_entity   — 须存在的对象实体 (E-ATT → 父 E-PROJ)
      object_dim      — 存在锚定维度 (锚定创建转换的维度)
      object_state    — 存在锚定状态 (锚定创建转换的 to_state)
      creation_to_id  — 锚定创建转换 id (S1 相位底查表用)
      creation_to_ids — 锚定维度上全部创建转换 id (S3 依赖绑定用,
                        T-015[a/b/c] 同维分支全绑, T-013 异维不绑)
    """
    if entity not in lifecycle_entity_ids(state):
        return None
    obj_entity = entity
    anchor = _anchor_creation(cm, state, entity)
    if anchor is None:
        parent = _composition_parent(cm, entity)
        if parent:
            obj_entity = parent
            anchor = _anchor_creation(cm, state, parent)
    if anchor is None:
        return None
    same_dim = sorted(
        (t for t in creation_transitions(cm, obj_entity)
         if t.get("dimension") == anchor.get("dimension")),
        key=lambda t: t.get("id", ""),
    )
    return {
        "object_entity": obj_entity,
        "object_dim": anchor.get("dimension"),
        "object_state": anchor.get("to"),
        "creation_to_id": anchor.get("id"),
        "creation_to_ids": [t.get("id") for t in same_dim],
    }
