#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""渲染层中文标签注册表（展示词汇，跨项目不变）。

`type_label`（happy/crud/rule/…）是生成器在 S1 依据 obligation_type + risk_trait
产出的固定枚举，其中文展示名与 nodes/s0_topology.TYPE_PRIORITY_MAP 同源、跨项目
不变。渲染层（main.py `_generate_markdown`）只消费本注册表，不内联硬编码，新增
形态（如新的 type_label）只需在本表加行。

业务模块（阶段）标签只做"大致划分模块"，不在此注册任何 P0→中文 硬编码表。每条
用例 `_S2_fields.phase_basis`（S1/S2 产出的相位解析依据字符串）决定其模块归属，
只分两类：

1. **实体形态**（状态锚定 `dep_state_phase_map.<实体>.<维度>.<状态>` /
   `phase_table.<维度>.<状态>`，或相位号 `min_phase`/`max_phase`/`parent_phase`/
   `*_entry_phase`）→ 返回该实体的中文模块名（如 "项目"、"评审计划"）。bumped/
   时间/父级继承尾注不影响模块归属，正则后直接取实体名，无需相位号→状态反查。
2. **机制形态**（`base_data_setup_phase`/`domain_precond_creation`/
   `fallback_default`）→ 返回跨实体模块的中文直译（基础数据维护/前置条件创建/
   默认阶段）。

模块中文名（实体名）来自 `coverage_model._context.state_info.entity_name`，
机制直译集中在 `PHASE_MECHANISM_CN`，全部数据驱动、不内联硬编码。新增形态
只加正则/机制行。
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

# phase_basis 机制前缀 → 中文直译（S2 用这些机制名标注相位解析依据，直译即语义）
PHASE_MECHANISM_CN: dict[str, str] = {
    "base_data_setup_phase": "基础数据",
    "domain_precond_creation": "前置条件创建",
    "fallback_default": "默认阶段",
    "primary_entity_entry_phase": "业务入口",
    "dep_map_entry_phase": "业务入口",
    # parent_phase 的阶段语义来自父实体继承链（如附件继承项目的相位），
    # 后缀标注来源，避免与用例自身的 Given 状态混淆
    "parent_phase": "父级继承",
}

# phase_basis 中附在状态后的尾注：不加理会，直取状态名
_TIME_SUFFIX_RE = re.compile(r"\s+\(time_(?:boundary|expired)\)$")
# parent_phase 的继承说明尾注
_VIA_CHAIN_RE = re.compile(r"\s+\(via chain from[^)]*\)")

# 状态锚定形态：
#   dep_state_phase_map.<实体>.<维度>.<状态>   （实体+维度+状态三段）
#   phase_table.<维度>.<状态>                  （主实体维度+状态两段）
_ANCHORED_RE = re.compile(r"^dep_state_phase_map\.([^.]+)\.([^.]+)\.(.+)$")
_PHASE_TABLE_RE = re.compile(r"^phase_table\.([^.]+)\.(.+)$")
# 实体+相位号 形态
_MIN_PHASE_RE = re.compile(r"^dep_state_phase_map\.([^.]+)\.min_phase$")
_MAX_PHASE_RE = re.compile(r"^(dep_map_max_phase|parent_phase)\.([^.]+)\.(\d+)$")
_PRIMARY_MAX_RE = re.compile(r"^primary_entity_max_phase\.(\d+)$")
_BASE_SETUP_RE = re.compile(r"^base_data_setup_phase\.([^.]+)\.\d+$")
_ENTRY_RE = re.compile(r"^dep_map_entry_phase\.([^.]+)\.(\d+)$")
_PRIMARY_ENTRY_RE = re.compile(r"^primary_entity_entry_phase\.(\d+)$")
_PRECOND_RE = re.compile(r"^domain_precond_creation\.")
_FALLBACK_RE = re.compile(r"^fallback_default\.")


def _phase_fallback(phase):
    """无任何可锚定数据时回退：只保留相位号（中文格式）。"""
    if phase is None:
        return "—"
    return f"第{phase}阶段"


def _derive_primary_eid(state_info: dict, procedures: list | None) -> str | None:
    """数据驱动地确定主实体 E-XXX id。

    主实体 = `phase_table.<维度>` 引用的维度在 state_info 中从属于哪个实体
    （phase_table 只引用主实体的维度）。无 phase_table 引用时，兜底取状态机
    规模最大的实体。不依赖任何硬编码的实体 id。
    """
    if procedures:
        for p in procedures:
            b = (p.get("_S2_fields") or {}).get("phase_basis", "") or ""
            m = re.search(r"phase_table\.([^.]+)\.", b)
            if m:
                dim = m.group(1)
                for eid, ent in (state_info or {}).items():
                    for d in ent.get("dimensions") or []:
                        if d.get("dimension_name") == dim:
                            return eid
    best, best_n = None, -1
    for eid, ent in (state_info or {}).items():
        n = sum(len(d.get("states") or []) for d in ent.get("dimensions") or [])
        if n > best_n:
            best, best_n = eid, n
    return best


def build_phase_labeler(state_info: dict, procedures: list | None = None):
    """从 coverage_model._context.state_info 构建数据驱动的业务模块解析器。

    返回 `phase_label(proc: dict) -> str`：输入一条 procedure，输出该用例所属的
    粗粒度业务模块中文名，如 "项目"、"评审计划"、"基础数据维护"。只做"大致划分
    模块"，不再精确到具体业务状态（如 项目·已选入）——具体状态由 Given 表达。

    state_info 缺省（无 coverage_model）时退化为只显示相位号的格式化器。
    """
    # --- 索引 state_info（全部派生自数据，无硬编码） ---
    eid_to_name: dict[str, str] = {}       # E-XXX id → 中文实体名
    for eid, ent in (state_info or {}).items():
        eid_to_name[eid] = ent.get("entity_name") or eid

    primary_eid = _derive_primary_eid(state_info, procedures)

    def _cn(entity: str) -> str:
        """实体标识（E-XXX id 或中文名）→ 中文实体名；未知原样返回。"""
        if entity in eid_to_name:
            return eid_to_name[entity]
        return entity

    def phase_label(proc: dict) -> str:
        s2 = proc.get("_S2_fields") or {}
        basis = (s2.get("phase_basis") or "").strip()
        phase = s2.get("phase")

        # 机制形态：跨实体的粗粒度模块（数据维护/前置条件/默认阶段），直译即语义。
        # base_data_setup_phase 后缀实体（`base_data_setup_phase.<实体>.<相位>`），
        # 展示为 "基础数据-<实体>"（如 基础数据-专家），实体从 phase_basis 捕获，
        # 不另立实体清单。其余机制形态（前置条件创建/默认阶段）无实体后缀，直译。
        m = _BASE_SETUP_RE.match(basis or "")
        if m:
            return f"{PHASE_MECHANISM_CN['base_data_setup_phase']}-{_cn(m.group(1))}"
        for pat, cn in (
            (_PRECOND_RE, PHASE_MECHANISM_CN["domain_precond_creation"]),
            (_FALLBACK_RE, PHASE_MECHANISM_CN["fallback_default"]),
        ):
            if basis and pat.match(basis):
                return cn

        if not basis:
            return _phase_fallback(phase)

        # 归一化：去时间尾注与继承说明尾注
        basis = _TIME_SUFFIX_RE.sub("", basis)
        basis = _VIA_CHAIN_RE.sub("", basis)

        # 实体形态 → 返回实体中文模块名（bumped/继承/时间尾注均不影响模块归属）
        m = _ANCHORED_RE.match(basis)
        if m:
            return _cn(m.group(1))
        m = _PHASE_TABLE_RE.match(basis)
        if m:
            return _cn(primary_eid) if primary_eid else _phase_fallback(phase)
        m = _MIN_PHASE_RE.match(basis)
        if m:
            return _cn(m.group(1))
        m = _MAX_PHASE_RE.match(basis)
        if m:
            return _cn(m.group(2))
        if primary_eid:
            if _PRIMARY_MAX_RE.match(basis) or _PRIMARY_ENTRY_RE.match(basis):
                return _cn(primary_eid)
        m = _ENTRY_RE.match(basis)
        if m:
            return _cn(m.group(1))

        # 未知 basis 形态：保留相位号（不臆造）
        return _phase_fallback(phase)

    return phase_label
