#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""渲染层中文标签注册表（展示词汇，跨项目不变）。

`type_label`（happy/crud/rule/…）是生成器在 S1 依据 obligation_type + risk_trait
产出的固定枚举，其中文展示名与 nodes/s0_topology.TYPE_PRIORITY_MAP 同源、跨项目
不变。渲染层（main.py `_generate_markdown`）只消费本注册表，不内联硬编码，新增
形态（如新的 type_label）只需在本表加行。

业务定位的模块段 = `phase_label(proc)`，单一事实源是 proc 本身：

- **模块名** = `proc.entity`（中文实体名），仅少量 `phase_basis` 机制覆盖：
  `base_data_setup_phase` 加"基础数据-"前缀 / `parent_phase` 取父实体 /
  `domain_precond_creation` 显示"前置条件创建"。不再用正则解析状态锚定形态。
- **目标状态**（括号内）= `proc.post_state` 的后置状态，且必须是该实体状态机
  （`state_info.dimensions[].states`）里的真实状态；规则/校验/非法等行为结果
  （`→(…)`）或配置值（如"任务级别=A级"）不显示，避免引擎词与配置噪声。

引擎词（P{phase} / 相位 / 锚定 / phase_basis）不进渲染，全部保留在 JSON 供追溯。
"""

import re

# type_label → 中文展示名
TYPE_LABEL_CN: dict[str, str] = {
    "happy": "正向流程",
    "branch": "分支路径",
    "audit": "审批流程",
    "audit_rejection": "审批驳回",
    "time_sensitive": "时效约束",
    "data_constraint": "数据约束",
    "rollback": "回退验证",
    "constraint": "前置门禁",
    "lifecycle": "生命周期",
    "crud": "数据操作",
    "invalid": "非法验证",
    "rule": "业务规则",
    "negative": "反向流程",
    "field_validation": "字段校验",
}

# post_state 后置状态的时序尾注（时间边界/过期）：剥掉后才是真实状态名
_TIME_SUFFIX_RE = re.compile(r"\s*[（(](?:时间边界|时间过期|time_boundary|time_expired)[）)]$")


def _phase_fallback(phase):
    """无实体可锚定时回退：只保留相位号（中文格式）。"""
    if phase is None:
        return "—"
    return f"第{phase}阶段"


def build_phase_labeler(state_info: dict, procedures: list | None = None):
    """构建业务模块解析器。

    返回 `phase_label(proc: dict) -> str`：`{模块}` 或 `{模块}（{目标状态}）`。

    - 模块名：默认 `proc.entity`，机制覆盖见 `_module_of`
    - 目标状态：`_state_of` 从 `post_state` 取后置状态，并校验在实体状态机内
    - `state_info` 缺省（无 coverage_model）时退化为"模块=实体名、不显示状态"
    """
    eid_to_name: dict[str, str] = {}        # E-XXX id → 中文实体名
    entity_states: dict[str, set] = {}      # 实体名/id → 状态机状态集
    for eid, ent in (state_info or {}).items():
        name = ent.get("entity_name") or eid
        eid_to_name[eid] = name
        states = set()
        for d in ent.get("dimensions") or []:
            states.update(d.get("states") or [])
        entity_states[name] = states
        entity_states[eid] = states

    def _cn(entity: str) -> str:
        """实体标识（E-XXX id 或中文名）→ 中文实体名；未知原样返回。"""
        return eid_to_name.get(entity, entity)

    def _module_of(proc: dict) -> str:
        s2 = proc.get("_S2_fields") or {}
        basis = (s2.get("phase_basis") or "").strip()
        entity = proc.get("entity") or ""
        if basis.startswith("base_data_setup_phase."):
            return f"基础数据-{_cn(entity)}"
        if basis.startswith("parent_phase."):
            parts = basis.split(".")
            return _cn(parts[1]) if len(parts) >= 2 else _cn(entity)
        if basis.startswith("domain_precond_creation."):
            return "前置条件创建"
        if entity:
            return _cn(entity)
        return _phase_fallback(s2.get("phase"))

    def _state_of(proc: dict) -> str:
        """目标状态（post_state 后置状态）；非状态机真实状态时返回 ''。"""
        ps = proc.get("post_state") or ""
        if "→" not in ps:
            return ""
        to = ps.split("→", 1)[1].strip()
        if to.startswith("("):          # 行为结果：角色→(操作被阻止)
            return ""
        to = _TIME_SUFFIX_RE.sub("", to)
        states = entity_states.get(proc.get("entity") or "")
        return to if states and to in states else ""

    def phase_label(proc: dict) -> str:
        module = _module_of(proc)
        state = _state_of(proc)
        return f"{module}（{state}）" if state else module

    return phase_label
