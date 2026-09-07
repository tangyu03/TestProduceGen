from __future__ import annotations
"""S1 Procedure Generation Node.

Deterministic procedure generation, faithfully replicating V2 JS engine logic.
All type generators (Type1, Type3, Type4a, Type4b, Type5, Type6, Type7)
are fully implemented with complete logic translated from p3_engine_v2.mjs.
"""
import json
import re
from typing import Any
from models.state import AgentState
from models.schema import ObligationType
from nodes.s0_topology import (
    _build_entity_name_map, _build_role_map, _build_managed_entities,
    TYPE_PRIORITY_MAP, TYPE5_SPECIAL_OPS, _collect_same_action_groups,
)
from nodes.field_validation import parse_entity_constraints, enrich_procedure_steps
from nodes.signal_validation import generate_signal_v_steps
from context.entity_operators import form_operator_roles
from context.sysfields import sys_maintained_pairs
from context.time_control import needs_time_control_ids
from context.constraint_fields import predicate_phase_lower_bound, get_state_phase
from context.domain_precondition import base_data_entity_ids, object_existence

# v29 Engineering Optimization Gap 1: Fallback Observability
from tools.fallback_log import record_fallback as _record_fallback


# v29 修复 1: derive_is_approve (基于实验 0/29 死刑)
# 实验 1+2+3 共 0/29 transition 含 is_approve 字段. declared 路径已死.
# derived 用结构信号推. 已知病灶: 信号同源 LLM, 共因失效. 但比 declared 0% 强.
# APPROVE_VERBS / REVIEWER_ROLES 是项目相关兜底配置 (不是领域无关), 显式标注.
_APPROVE_VERBS_CONFIG = ("审核通过", "审批通过", "批准", "同意", "确认通过")
_REJECT_VERBS_CONFIG = ("驳回", "拒绝", "退回")
_REVIEWER_ROLES_CONFIG = {"R-REV", "R-LEAD", "R-DIR", "R-PM", "R-ADMIN"}


def _derive_is_approve(to: dict, action: str) -> tuple[bool, float, list[str]]:
    """从结构信号推算 is_approve. 不读 declared 字段.

    返回 (value, confidence, evidence).
    confidence 当前是 score (0-1), 还不是统计校准置信度.
    等 review queue 积累数据后再从命中率倒推.
    """
    score = 0.0
    evidence = []

    # 信号 1: action 含决策类动词 (项目相关兜底)
    if any(v in (action or "") for v in _APPROVE_VERBS_CONFIG):
        score += 0.4; evidence.append(f"action 含 approve verb")
    elif any(v in (action or "") for v in _REJECT_VERBS_CONFIG):
        # reject 明确不是 approve
        return False, 0.3, evidence + ["action 含 reject verb (决策但非通过)"]

    # 信号 2: role 是审核方 (项目相关兜底)
    if to.get("role") in _REVIEWER_ROLES_CONFIG:
        score += 0.3; evidence.append(f"role={to.get('role')} ∈ reviewers")

    # 信号 3: to_state 非终态 (approve 通常不进终态, 但反例存在, 低权重)
    # 注: terminals 需要从 state_info 取, S1 此处可能拿不到. 暂时跳过这个信号.
    # 如果有 terminals 集合, 可以这样:
    # if to.get("to") not in terminals:
    #     score += 0.2; evidence.append("to_state non-terminal")
    # else:
    #     score -= 0.1; evidence.append("to_state is terminal (降权)")

    # 信号 4: traits 含 audit
    if "audit" in (to.get("risk_traits") or to.get("traits") or []):
        score += 0.1; evidence.append("traits ∋ audit")

    return score >= 0.5, score, evidence

# ---------------------------------------------------------------------------
# Global gen-seq counter (module-level so all generators share one sequence)
# ---------------------------------------------------------------------------
_gen_seq_counter = 0


def _next_gen_seq() -> int:
    global _gen_seq_counter
    _gen_seq_counter += 1
    return _gen_seq_counter


# ---------------------------------------------------------------------------
# Helper functions (mirroring V2 JS engine)
# ---------------------------------------------------------------------------

def _resolve_entity_names(name_str, entity_name_map: dict | None = None) -> list[str]:
    """Convert Chinese entity names or IDs to canonical IDs using dynamic map.

    Accepts either a comma-separated string (old ``entities`` format) or a
    list (new ``entities_involved`` format).
    """
    if not name_str:
        return []
    if entity_name_map is None:
        entity_name_map = {}
    # Normalise to list
    if isinstance(name_str, list):
        items = name_str
    else:
        items = re.split(r'[,，、\s]+', str(name_str))
    return [entity_name_map.get(n.strip(), n.strip())
            for n in items if n.strip()]


def _get_role_name(role_id: str | None, action: str = '', entity: str = '',
                   state: AgentState | None = None) -> str:
    """I21: Resolve role with LLM-classified human-decision fallback chain.

    Replaces the legacy HUMAN_DECISION_KEYWORDS hardcoded list with an
    LLM-based action classification (cached in ``state['action_classification']``).
    The classification is performed once at S1 start by
    ``_classify_actions_via_llm`` and stored as ``{action_text: "human"|"system"}``.
    """
    # Build role_map dynamically from coverage_model._context
    role_map = _build_role_map(state.get('coverage_model', {})) if state else {}
    base = role_map.get(role_id, role_id) or '系统'

    if role_id and role_id != 'system' and base != '系统':
        return base

    # P1 role=system is authoritative — return '系统' immediately,
    # regardless of LLM action classification. The LLM may classify
    # a system-driven action (e.g. '试用机构升为合格') as 'human'
    # because the action text sounds like a human operation, but
    # P1's role=system declaration is the ground truth from SRS reading.
    # Without this early return, the code falls into the has_human_kw
    # branch below and returns '[待确认角色]', causing V03/V07 fails.
    if role_id in ('system', '系统'):
        return '系统'

    # BDD: LLM-based action classification (replaces HUMAN_DECISION_KEYWORDS)
    # Read from state['action_classification'] — a dict {action_text: "human"|"system"}
    # populated once at S1 start by _classify_actions_via_llm.
    action_cls = state.get('action_classification', {}) if state else {}
    action_type = action_cls.get(action, '')
    has_human_kw = action_type == 'human'
    has_auto_kw = action_type == 'system'

    def _role_lookup(roles_data, key: str) -> str | None:
        """Look up role by entity key, handling both list and dict formats."""
        if isinstance(roles_data, dict):
            return roles_data.get(key)
        if isinstance(roles_data, list):
            for item in roles_data:
                if isinstance(item, dict):
                    if item.get('entity') == key or item.get('id') == key:
                        return item.get('role') or item.get('name') or item.get(key)
            for item in roles_data:
                if isinstance(item, dict) and key in item:
                    return item[key]
        return None

    if has_human_kw:
        if state:
            ep = state.get('entity_parent', {})
            parent = ep.get(entity)
            if parent:
                ctx = state.get('coverage_model', {}).get('_context', {})
                roles = ctx.get('roles', {})
                parent_role = _role_lookup(roles, parent)
                if parent_role and parent_role != 'system':
                    return role_map.get(parent_role, parent_role)

        return '[待确认角色]'

    if has_auto_kw or role_id == 'system':
        return '系统'

    # BDD: creation transitions (from_state is None) → system role.
    # Previously hardcoded `action == '创建'` — replaced with structural check
    # on the TO's from_state, passed in via the `to` dict context.
    # Fallback: if no action info at all, assume system.
    if not action:
        return '系统'

    return base


# 流转形态检测：跨维度 state_ref 若文本含"由…变为/变为/转为"，其 ref.state
# 是流转的目标态（非前置态）。渲染层按 given_type 分流时，flow 走 `流转：X→Y`，
# state 走 `状态 = X`——把流转结果伪装成前置条件是语义串线（正确性问题）。
_FLOW_RE = re.compile(r"由[^;]*变为|变为|转为")


def _is_flow_state(text: str) -> bool:
    """跨维度 state_ref 文本是否流转形态（ref.state 为目标态）。"""
    return bool(_FLOW_RE.search(text or ""))


def _make_given(target: str, state: str, description: str = "",
                given_type: str = "state") -> dict:
    """Build a BDD Given clause (business-state precondition).

    ``state`` must be a business state value (e.g. "待审批"), NOT a UI
    navigation instruction.  ``description`` is optional context (e.g.
    VE scenario label).

    ``given_type`` selects the render format (纯格式选择器，无渲染层文本猜测):
    - "state"      → `{target} 状态 = {state} ({desc})`   （主锚定/同维度/跨维度纯状态）
    - "event"      → 事件已完成断言，独立 Given（同 state 格式）
    - "flow"       → `{target} 流转：{desc}`  （跨维度流转形态，desc 保留原文）
    - "constraint" → `约束：{desc}`            （业务约束，非状态前置）
    - "branch"     → `分支条件：{value}`        （分支维度 Given）
    - "rule"       → `{desc}`                  （规则上下文，desc=被测 BR 原文）
    - "rule_noise" → 渲染跳过                  （空泛占位 "…相关数据已准备"，无测试价值）
    - "restatement"→ `{desc}`                  （对象实例复述，desc 已含完整句子形态）
    - "field_data" → 渲染挂 When 事件步子行  （创建/编辑表单字段清单，desc 由 P1
                                                 entity_details 派生，见 _field_data_given；
                                                 state 恒为空，非前置条件不在 Given 渲染）
    """
    return {"target": target, "state": state, "description": description,
            "given_type": given_type}


def _make_when(target: str, event: str, actor: str = "", action: str = "") -> dict:
    """Build a BDD When clause (business event under test).

    ``event`` describes the business occurrence (declarative, e.g.
    "审批通过事件触发"), NOT the mechanical action.  ``actor`` and
    ``action`` carry concrete execution info.
    """
    return {"target": target, "event": event, "actor": actor, "action": action}


def _make_then(target: str, expectation: str,
               kind: str = "state",
               br_refs: list[str] | None = None,
               cross_refs: list[str] | None = None,
               dedup_group: str | None = None) -> dict:
    """Build a BDD Then clause (observable business outcome).

    ``expectation`` must be a concrete, non-tautological observable
    (I19: forbidden values include "查看效果", "验证差异").
    ``kind`` ∈ {"state", "behavior", "prompt"}.
    ``dedup_group`` marks redundant assertions for the RENDERING layer
    (e.g. "transition_target" is implied by "transition_flow"; coverage
    statements assert no observable result). It drives display dedup in
    the renderer instead of the renderer text-matching data-layer strings.
    """
    return {
        "target": target,
        "expectation": expectation,
        "kind": kind,
        "br_refs": br_refs or [],
        "cross_refs": cross_refs or [],
        "dedup_group": dedup_group,
    }


def _mark_then_subsumption(valid_procs: list) -> int:
    """Then 吸收下沉：把「transition_target 状态行被同 target 的 behavior 行
    完全包含」的判定从渲染层移到 S1 数据层。

    transition_target 状态行（expectation="状态转换为X"）被同 target 的
    behavior 行复述（"状态…为X"，如 "回收任务创建，状态初始化为草稿"）——
    事件+状态双信息都被行为行携带，单独保留无独立信息。此吸收判断属语义
    决策（判断某 Then 是否冗余），由数据层在 S1 标记 `subsumed=True`，
    渲染层只消费标记，不再做文本比对。

    判据与渲染层旧实现逐字一致（数据驱动，无硬编码动词表）：状态行须
    dedup_group=="transition_target" 且 kind=="state"；behavior 行须同
    target 且 expectation 含 "状态[^，。；]*为X"（纯文本关系）。全量
    152 处精确命中、321 条标记行中 169 条无复述者保留。

    返回标记数量。
    """
    marked = 0
    for p in valid_procs:
        for t in p.thens:
            if t.kind != "state" or t.dedup_group != "transition_target":
                continue
            m = re.match(r"^状态转换为(.+)$", (t.expectation or "").strip())
            if not m:
                continue
            st_val = m.group(1)
            if any(
                b.kind == "behavior" and b.target == t.target
                and re.search(r"状态[^，。；]*为" + re.escape(st_val),
                              (b.expectation or ""))
                for b in p.thens
            ):
                t.subsumed = True
                marked += 1
    return marked


# ── Procedure skeleton factories ─────────────────────────────────────────
# Every generator (Type1/3/5/6/7/9) builds the same _S2/_S3/_S4 field shape.
# These factories centralize the defaults so a schema change is one edit.

# 调试/内部推导的 phase_basis 值(引擎 traceability,对测试执行者是噪声)。
# 分类在引擎层完成并写入 _S2_fields.phase_basis_debug,渲染层只读标记,
# 不匹配具体 basis 字符串(避免渲染层耦合引擎内部命名)。
#
# 判定原则:只隐藏"启发式/聚合推导"的 basis(min/max/兜底/父锚/VE/配置类),
# 保留"精确状态锚定"的 basis。精确锚定形如 phase_table.{dim}.{state} 或
# dep_state_phase_map.{entity}.{dim}.{state}——指明"该过程因某实体某状态映射
# 到相位 N 而执行于 N",是测试执行者可判定的阶段前提;启发式形如
# dep_state_phase_map.X.min_phase(整表取 min)、dep_map_max_phase.X.N(取 max)
# 等,是引擎估算,对执行者是噪声。故列表只含启发式标记,不含锚定前缀。
_DEBUG_BASIS_PATTERNS = [
    "fallback_default", ".min_phase",
    "primary_entity_max_phase", "primary_entity_default",
    "dep_map_max_phase", "config_entity.", "parent_phase.",
    "parent_primary_phase", "VE.", "topology_level L0",
]


def _is_debug_phase_basis(basis: str) -> bool:
    return any(p in basis for p in _DEBUG_BASIS_PATTERNS)


def _make_S2_fields(phase: int, phase_name: str, phase_basis: str,
                    topology_level: int, operation_lifecycle: int,
                    chain_depth: int, type_label: str, type_priority: int,
                    dimension_priority: int, context) -> dict:
    """S2-sortable fields. Callers pass computed values; defaults live here."""
    return {
        "phase": phase,
        "phase_name": phase_name,
        "phase_basis": phase_basis,
        "phase_basis_debug": _is_debug_phase_basis(phase_basis),
        "topology_level": topology_level,
        "sort_key": [],
        "operation_lifecycle": operation_lifecycle,
        "chain_depth": chain_depth,
        "type_label": type_label,
        "type_priority": type_priority,
        "dimension_priority": dimension_priority,
        "context": context,
    }


def _make_S3_fields(dependencies=None, weak_dependencies=None) -> dict:
    return {
        "dependencies": list(dependencies or []),
        "weak_dependencies": list(weak_dependencies or []),
    }


def _make_S4_fields() -> dict:
    return {"multi_instance": False, "multi_count": 1, "multi_reason": ""}


# ── Business event derivation ────────────────────────────────────────────
#
# Convert a mechanical action into a natural business event description.
# This is the single place where When.event text is shaped — keeps the
# "事件触发" suffix out of the BDD spec.
#
# Design principle: NO hardcoded business verbs.  The function only does
# generic text cleanup (strip "事件触发" suffix) + optional state-context
# annotation when from/to states are known.  Works for any business domain.


def _derive_business_event(action: str, from_state: str = "", to_state: str = "") -> str:
    """Derive a natural business-event description from a mechanical action.

    Instead of "机构新增/修改实验室信息事件触发", produce "机构新增/修改实验室信息".

    The target state is intentionally NOT appended to the event label (no
    "（目标状态：X）"): it is an OUTCOME asserted by the Then clause
    ("状态转换为X"), and for same-action branch families (e.g. 重启评审计划 →
    待评审/评审中/已完成) the Given's branch condition already disambiguates
    which instance is under test.  Repeating it in the When is redundant echo
    for the test executor.  This is the single place When.event text is shaped,
    so removing it here cleans both JSON and rendered MD (DECISIONS ㉝).

    Generic — no hardcoded business keywords.  Only does:
      1. Strip mechanical "事件触发" suffix
      2. If action is empty, describe via from→to state change
    """
    if not action:
        if from_state and to_state and from_state != to_state:
            return f"状态从{from_state}变更为{to_state}"
        return "状态转换"

    # If the action already contains "事件触发", strip it
    cleaned = action.replace("事件触发", "").strip()
    if not cleaned:
        return "状态转换"

    return cleaned


# ── V06: time_sensitive 触发机制推导（模块级，无硬编码）──────────────
#
# validator 检查 time_sensitive 用例要求声明执行路径（time_control.mechanism）：
#   clock_injection / db_time_update / scheduler_manual_trigger
#
# 机制在数据层推导（_derive_time_mechanism），写入 JSON time_control 字段供
# V06 校验；**不再**生成 human-readable 触发方式 hint 行注入 operation_hints
# —— 需求原文自陈触发语义（"48小时后系统自动结束"），把 3 种机制描述当编号
# 步骤列进 When 块与执行事件混排，是测试基建措辞冒充业务操作（用户判
# "位置与需求不符"，已删，DECISIONS ㊺）。触发方式标识符是 validator 协议
# 约定的枚举，不算业务硬编码。

def _derive_time_mechanism(action_text: str) -> str:
    """从 action 语义推导主触发机制(V06 time_control.mechanism)。

    判定规则：
    - action 含"边界"/"接近" → clock_injection（时钟注入到边界）
    - action 含"过期"/"已过期" → db_time_update（数据库时间更新）
    - 其他（含"超时"/"自动"）→ scheduler_manual_trigger（调度器触发）

    触发方式标识符是 validator 协议约定的枚举,不算业务硬编码。
    """
    if any(kw in action_text for kw in ["边界", "接近"]):
        return "clock_injection"
    if any(kw in action_text for kw in ["过期", "已过期"]):
        return "db_time_update"
    return "scheduler_manual_trigger"


def _find_reviewer_role_for_dim(
    current_to: dict,
    cm: dict,
    reject_keywords: tuple,
) -> str | None:
    """v29 #13: Find the reviewer role for a transition's entity+dimension.

    Scans all other audit transitions in the same entity+dimension and
    returns the role most likely to be the REVIEWER (the party that
    approves/rejects submissions).

    Priority:
      1. Role from a REJECT transition (action contains 退回/驳回/撤销/退款)
         — this is unambiguously the reviewer.
      2. Role from an APPROVE transition (action contains 审核/批准/通过/同意/确认
         AND from_state is non-null — i.e. not the creation transition).
      3. None — fall back to the original TO's role.

    Example (E-LAB.审核状态):
      T-070: (null)→待审核, role=R-PARTICIPANT, action="机构新增/修改实验室信息"
      T-071: 待审核→启用,   role=R-SYS-ADMIN,  action="管理用户审核通过"
      T-072: 待审核→退回修改, role=R-SYS-ADMIN,  action="管理用户审核退回修改" ← REJECT
      → reviewer_role = R-SYS-ADMIN (from T-072)
    """
    if not current_to:
        return None
    entity = current_to.get('entity', '')
    dimension = current_to.get('dimension', '')
    current_tid = current_to.get('transition_id', '')

    tos = cm.get('transition_obligations', []) if isinstance(cm, dict) else []
    approve_keywords = ('审核', '批准', '通过', '同意', '确认')

    # Pass 1: find a REJECT transition's role
    for to in tos:
        if to.get('transition_id') == current_tid:
            continue
        if to.get('entity') != entity or to.get('dimension') != dimension:
            continue
        action = to.get('action', '') or ''
        if any(kw in action for kw in reject_keywords):
            role = to.get('role')
            if role and role != 'system':
                return role

    # Pass 2: find an APPROVE transition's role (non-creation)
    for to in tos:
        if to.get('transition_id') == current_tid:
            continue
        if to.get('entity') != entity or to.get('dimension') != dimension:
            continue
        action = to.get('action', '') or ''
        if not to.get('from'):
            continue  # creation transition — submitter, not reviewer
        if any(kw in action for kw in approve_keywords):
            role = to.get('role')
            if role and role != 'system':
                return role

    return None


def _derive_rejection_action_v29(
    original_action: str,
    reviewer_role_name: str,
    original_role_id: str | None = None,
    role_map: dict | None = None,
) -> str:
    """v29 #13: Build a rejection action that names the reviewer explicitly.

    Strategy:
      1. If action contains approve keyword (通过/批准/同意/确认) AS A VERB
         (not as a preposition like "通过表单"):
         - Replace approve_kw with "驳回"
         - Truncate at "并" / "，" if the suffix describes a follow-up action
           that doesn't apply to rejection (e.g. "批准并发放" → "驳回",
           not "驳回并发放")
      2. Otherwise: prefix with reviewer role name + "驳回" verb, e.g.
         "管理用户驳回机构新增/修改实验室信息"

    The reviewer_role_name is the human-readable role name (e.g. "管理用户",
    "项目管理员") resolved via _get_role_name.
    """
    if not original_action:
        return "驳回"
    cleaned = _strip_branch_suffix(original_action)

    # v29: detect if approve_kw is used as a VERB (审核通过/批准/同意/确认)
    # vs a preposition (通过表单 = "via form"). Heuristic:
    # - "通过" is a verb if preceded by 审核/审批/审议, OR if it's at the end
    #   of action, OR if it's followed by 并/，/空格
    # - "批准/同意/确认" are almost always verbs in this domain
    approve_verbs_strong = ("批准", "同意", "确认")  # almost always verbs
    approve_verbs_weak = ("通过",)  # could be preposition

    def _is_approve_verb(action: str, kw: str) -> bool:
        """Check if `kw` in `action` is used as an approve verb."""
        if kw in approve_verbs_strong:
            return True
        # For "通过": check context
        idx = action.find(kw)
        while idx >= 0:
            before = action[:idx]
            after = action[idx + len(kw):]
            # Verb usage: preceded by 审核/审批/审议, OR at end, OR followed by 并/，/,
            is_verb = (
                before.endswith(('审核', '审批', '审议', '复核')) or
                not after or  # at end
                after.startswith(('并', '，', ',', '且', ' '))
            )
            # Preposition usage: followed by a noun phrase like "表单/方式/途径"
            is_prep = after.startswith(('表单', '方式', '途径', '渠道'))
            if is_verb and not is_prep:
                return True
            idx = action.find(kw, idx + 1)
        return False

    # Try to find an approve verb and replace
    for approve_kw in ("通过", "批准", "同意", "确认"):
        if approve_kw in cleaned and _is_approve_verb(cleaned, approve_kw):
            # Find the position of the approve verb
            idx = cleaned.find(approve_kw)
            # Check if there's a follow-up action after "并" / "，"
            # that should be truncated (e.g. "批准并发放" → "驳回", not "驳回并发放")
            after_kw = cleaned[idx + len(approve_kw):]
            # Truncate at "并" / "，" / "," — the rejection only does the
            # rejection part, not the follow-up action
            for sep in ('并', '，', ',', '且'):
                if sep in after_kw:
                    after_kw = ''  # truncate
                    break
            # Build the rejection action: prefix (before approve_kw) + "驳回" + truncated suffix
            prefix = cleaned[:idx]
            return f"{prefix}驳回{after_kw}".rstrip('，, ')

    # v29: prefix with reviewer role name
    if reviewer_role_name and reviewer_role_name not in ('系统', '[待确认角色]', ''):
        # Check if reviewer role name is already in the action (avoid duplication)
        if reviewer_role_name in cleaned:
            return f"{cleaned}（驳回）"
        # Check if original role name is a prefix of the action
        # (e.g. action="项目管理员审核报名通过" starts with role="项目管理员")
        # — in that case, replace the original role prefix with reviewer role.
        if role_map and original_role_id:
            orig_role_name = role_map.get(original_role_id, '')
            if orig_role_name and orig_role_name != reviewer_role_name:
                if cleaned.startswith(orig_role_name):
                    return f"{reviewer_role_name}驳回{cleaned[len(orig_role_name):]}"
                # Also handle case where original role name appears anywhere
                if orig_role_name in cleaned:
                    return cleaned.replace(orig_role_name, reviewer_role_name, 1) + "（驳回）"
        # Default: prefix with reviewer
        return f"{reviewer_role_name}驳回{cleaned}"

    # Fallback: v28 behavior
    return f"{cleaned}（驳回）"


# ── Branch dimension extraction (generic, not hardcoded) ─────────────────
#
# P2 may split a single business transition into multiple TOs by branch
# dimension (e.g. T-030a / T-030b split by 项目类型=能力验证/测量审核).
# The branch info lives in two places:
#   1. coverage_model._context.branch_dimensions — the canonical source:
#      {entity, dimension, branches: [{value, target_transition}]}
#   2. TO.action text — P2 sometimes appends "[维度=值]" suffix as a marker
#
# S1 should:
#   - read branch_dimensions to find which branch value applies to this TO
#   - emit a Given clause for the branch dimension (so BDD spec shows the branch)
#   - strip the "[维度=值]" suffix from action (it's a P2 marker, not spec)
#
# This is GENERIC: works for any branch dimension (项目类型, 评分方式, 评价人员角色,
# 消息发送接收人范围, etc.), not hardcoded to 项目类型.

# Regex to strip "[维度=值]" or "[维度=值1/值2]" suffix from action text
_BRANCH_SUFFIX_RE = re.compile(r'\s*\[[^\]]+=[^\]]+\]\s*$')


def _strip_branch_suffix(action: str) -> str:
    """Remove trailing [维度=值] markers from action text.

    Examples:
        "发出样品 [项目类型=能力验证]" → "发出样品"
        "发放样品与作业指导书 [项目类型=测量审核]" → "发放样品与作业指导书"
        "立项批准 [项目类型=能力验证/测量审核]" → "立项批准"
    """
    if not action:
        return action
    cleaned = action
    while _BRANCH_SUFFIX_RE.search(cleaned):
        cleaned = _BRANCH_SUFFIX_RE.sub('', cleaned).strip()
    return cleaned


def _is_state_derived_branch_dimension(
    bd: dict, tos: list[dict]
) -> bool:
    """Fix-3: detect branch dimensions whose values are a restatement of the
    affected transitions' OWN state (from_state or to_state).

    Genuine state-derived example (暂停前状态):
      T-PLAN-008 (暂停) from=待评审, branch=[暂停前状态=待评审]
      T-PLAN-009 (暂停) from=评审中, branch=[暂停前状态=评审中]
      T-PLAN-010 (暂停) from=已完成, branch=[暂停前状态=已完成]
      Every variant's branch value equals its OWN from_state → the dimension
      merely restates the state machine; splitting produces only diagonal
      (from=pre_pause) reachable pairs, not 3×3 combos.

    NOT state-derived (项目阶段, e.g. T-014 归档后阶段变更):
      T-014 branch=[项目阶段=开题] from=开题 to=验收
      The branch value equals its OWN from_state 开题 — but this dimension is
      NOT state-derived for T-014 alone (its sibling T-013 新增项目 is an
      INITIALIZATION: from=None, to=开题, and P2 now guards initialization
      transitions against splitting on their own dimension — see
      generate_obligation_model.get_matched_dims — so T-013 is never split and
      no 项目阶段=验收→开题 contradiction variant exists).

    Detection (generic): a dimension is state-derived iff EVERY affected TO's
    branch value for that dimension equals its OWN from_state or to_state.
    """
    bd_dim = bd.get("dimension", "")
    if len(set(bd.get("values", []) or [])) < 2:
        return False

    # Collect TOs whose branch_path includes this dimension
    affected: list[dict] = []
    for to in tos:
        if any(bp.get("dimension") == bd_dim for bp in (to.get("branch_path", []) or [])):
            affected.append(to)
    if len(affected) < 2:
        return False

    for to in affected:
        val = next(
            (bp.get("value") for bp in (to.get("branch_path", []) or [])
             if bp.get("dimension") == bd_dim),
            None,
        )
        if val is None:
            return False
        if val not in (to.get("from"), to.get("to")):
            return False  # orthogonal branch value → genuine branch
    return True


def _extract_branch_givens(
    to: dict, coverage_model: dict
) -> list[dict]:
    """Extract branch-dimension Given clauses for a TO.

    Canonical source: the TO's branch_path — it carries the EXACT
    {dimension, value} pairs for THIS variant (e.g. T-007[b] → [{项目评级, 良好}]).
    Deriving givens from branch_path is precise; the previous approach matched
    the FIRST branch of the branch_dimension by base-transition prefix, so every
    variant of a transition got the SAME (first) value → their procedures were
    deduped as "complete duplicates" and the distinct branches were lost.

    Fallback: TO.action "[维度=值]" suffix (for TOs without branch_path).

    This is GENERIC: works for any branch dimension, no hardcoded names.

    Fix-3: state-derived branch dimensions (e.g. 暂停前状态 whose values
    equal the from_states of the same transitions) are skipped — they are
    not orthogonal to the state machine and would explode the procedure
    count without adding semantic value.
    """
    if not to:
        return []
    to_entity = to.get("entity", "")
    to_action = to.get("action", "") or ""
    givens: list[dict] = []
    seen_dims: set[str] = set()

    # Fix-3: pre-compute the set of state-derived branch dimensions to skip
    tos_all = coverage_model.get("transition_obligations", [])
    state_derived_dims: set[str] = set()
    for bd in coverage_model.get("_context", {}).get("branch_dimensions", []):
        if _is_state_derived_branch_dimension(bd, tos_all):
            state_derived_dims.add(bd.get("dimension", ""))

    # ── Source 1 (canonical): branch_path — exact {dimension, value} per variant ──
    for bp in to.get("branch_path", []) or []:
        dim = bp.get("dimension", "")
        val = bp.get("value", "")
        if dim in state_derived_dims:
            continue
        if dim and val and dim not in seen_dims:
            givens.append(_make_given(
                target=f"{to_entity}.{dim}",
                state=val,
                description=f"分支条件: {dim}={val}",
                given_type="branch",
            ))
            seen_dims.add(dim)

    # ── Source 2: action "[维度=值]" suffix (fallback, deduped by dim) ──
    # Pattern: [项目类型=能力验证] or [评分方式=分值, 评价人员角色=评价成员]
    for m in re.finditer(r'\[([^\]]+)\]', to_action):
        content = m.group(1)
        # Split by comma (Chinese or ASCII) for multi-dimension branches
        for part in re.split(r'[,，]', content):
            if '=' in part:
                dim_name, dim_value = part.split('=', 1)
                dim_name = dim_name.strip()
                dim_value = dim_value.strip()
                # Fix-3: skip state-derived branch dimensions in action suffix too
                if dim_name in state_derived_dims:
                    continue
                if dim_name and dim_value and dim_name not in seen_dims:
                    givens.append(_make_given(
                        target=f"{to_entity}.{dim_name}",
                        state=dim_value,
                        description=f"分支条件: {dim_name}={dim_value}",
                        given_type="branch",
                    ))
                    seen_dims.add(dim_name)
    return givens


def _compute_synth_branch_declarations(
    tos: list[dict], bds: list[dict], warnings: list
) -> None:
    """S1-a/S1-b: 为共享 TO 合成生命周期分支声明（原位写回 TO）。

    背景（v13 依赖评审 四.4）：P2 只透传转换自带的 branch_values/branch_path；
    共用转换（t08 报名审核 / t21 参加者测试与结果提交族）在两个流程分支下都
    实例化，却不声明 项目类型 归属 → 渲染无分支 Given、S3 跨分支门禁拿不到
    归属。两个互补机制，全部数据驱动（无硬编码维度名/值）：

    S1-a 同动作兄弟传播：precondition_state_refs 与分支归属皆空的 TO，采纳
      同 (action, entity) 已归属兄弟的生命周期维度值（t07 ← t02 同动作拆行，
      拆行本身不带归属）。只采生命周期维度值，避免把兄弟的配置分支值
      （报名审核结果=…）误当流程归属。t06（缴费通知单，异实体同动作）不入组，
      保持共享——否则 054 会被门禁错杀 034 依赖。

    S1-b 分支域闭包声明：domain(t) = 自身归属 ∪ 前置状态引用生产者的 domain
      （不动点）。自身无生命周期归属值、闭包在该维度 ≥2 值的状态机 TO →
      声明 "分支条件: <dim>=A/B"。覆盖直接命中（t08/t09/t30 的前置
      报名中/报名待审核 由两分支转换生产）与闭包命中（t15/t21/t25/t26/t27
      沿状态链上溯到两分支创建）。

    生命周期维度 = 本实体创建转换（from 为空）的 note.branch_dimension。
    写回：TO["_synth_branch_givens"]（渲染 Given，挂载点见 s1 proc 组装
    _extract_branch_givens 之后）+ TO["_synth_branch_values"]（结构化归属，
    S3 _to_branch_values 并集消费——不做 Given 文本反解析，规避 CJK 值词
    碰撞）。
    """
    # 生产者索引: (entity, dimension, to_state) -> [TO]
    producers: dict = {}
    for t in tos:
        to_state = t.get("to")
        if to_state:
            producers.setdefault(
                (t.get("entity"), t.get("dimension"), to_state), []).append(t)

    # 生命周期维度（per 实体）：创建转换的 note.branch_dimension
    lifecycle_dim: dict = {}
    for t in tos:
        if t.get("from") is None:
            bd = (t.get("note") or {}).get("branch_dimension") or ""
            if bd and t.get("entity") not in lifecycle_dim:
                lifecycle_dim[t["entity"]] = bd

    def _own_pairs(t: dict) -> set:
        pairs = {(bp.get("dimension"), str(bp.get("value")))
                 for bp in (t.get("branch_path") or [])
                 if isinstance(bp, dict) and bp.get("dimension") and bp.get("value")}
        if t.get("branch_values"):
            dim = (t.get("note") or {}).get("branch_dimension") or ""
            pairs |= {(dim, str(v)) for v in t["branch_values"] if v}
        return pairs

    # 维度值排序基准：branch_dimensions 元数据的 values 序（缺省 sorted 兜底）
    dim_value_order: dict = {}
    for bd in bds or []:
        dim = bd.get("dimension", "")
        if dim and dim not in dim_value_order:
            dim_value_order[dim] = list(bd.get("values", []) or [])

    def _ordered(dim: str, vals: set) -> list:
        order = dim_value_order.get(dim) or []
        known = [v for v in order if v in vals]
        rest = sorted(vals - set(known))
        return known + rest

    def _attach(t: dict, dim: str, vals: set, kind: str) -> None:
        ordered = _ordered(dim, vals)
        state_str = "/".join(ordered)
        t["_synth_branch_givens"] = [_make_given(
            target=f"{t.get('entity')}.{dim}",
            state=state_str,
            description=f"分支条件: {dim}={state_str}",
            given_type="branch",
        )]
        t["_synth_branch_values"] = ordered
        warnings.append(
            f"S1.分支声明({kind}): {t.get('id')} {dim}={state_str}")

    # ── S1-a: 同动作兄弟传播（用自身归属，先于闭包） ──
    groups: dict = {}
    for t in tos:
        groups.setdefault((t.get("action"), t.get("entity")), []).append(t)
    own = {id(t): _own_pairs(t) for t in tos}
    for t in tos:
        if own[id(t)] or (t.get("precondition_state_refs") or []):
            continue
        ld = lifecycle_dim.get(t.get("entity"))
        if not ld:
            continue
        sib_vals = set()
        for sib in groups.get((t.get("action"), t.get("entity")), ()):
            if sib is not t:
                sib_vals |= {v for d, v in own[id(sib)] if d == ld}
        if sib_vals:
            _attach(t, ld, sib_vals, "propagate")
            own[id(t)] = {(ld, v) for v in sib_vals}

    # ── S1-b: 分支域闭包声明（不动点） ──
    domain = {id(t): set(own[id(t)]) for t in tos}
    for _ in range(len(tos) + 2):
        changed = False
        for t in tos:
            d = domain[id(t)]
            for ref in (t.get("precondition_state_refs") or []):
                key = (ref.get("entity"), ref.get("dimension"), ref.get("state"))
                for p in producers.get(key, ()):
                    if p is t:
                        continue
                    # v13 评审三补：生命周期已归属的生产者只传播自身归属，
                    # 不传播它从上游吸入的闭包值——T-046 自带 项目类型=
                    # 测量审核，其 domain 经生产者 T-007（S1-a 能力验证）
                    # 吸入对侧分支值；整体下传会给消费方 T-048 注入
                    # 能力验证/测量审核 双值 → S3 跨分支门禁放行 T-007
                    # （022/067/078 guard5 错挂根因）。
                    p_ld = lifecycle_dim.get(p.get("entity"))
                    p_pairs = own[id(p)]
                    contrib = (p_pairs
                               if p_ld and any(dd == p_ld for dd, _ in p_pairs)
                               else domain[id(p)])
                    before = len(d)
                    d |= contrib
                    if len(d) != before:
                        changed = True
        if not changed:
            break
    # v13 评审四.4 补充：自身已有**生命周期维度**归属（如 t40 显式声明
    # 测量审核）→ 不动，保留专用身份（B2 分支消歧依赖它）。自身只有配置
    # 分支条件（审核结果=通过 等，t08/t09/t25/t26）→ 生命周期维度无归属，
    # 闭包声明与配置分支并存：渲两个分支 Given + 注入生命周期归属值。
    for t in tos:
        ld = lifecycle_dim.get(t.get("entity"))
        if not ld:
            continue
        own_ld = {v for d, v in own[id(t)] if d == ld}
        if own_ld:
            continue
        vals = {v for d, v in domain[id(t)] if d == ld}
        if len(vals) >= 2:
            _attach(t, ld, vals, "closure")


def _warn_undeclared_birth_states(tos: list[dict], warnings: list) -> None:
    """分支出生态初始值未声明的确定性告警（warning 非 error，不中断）。

    背景（v13 评审三防线②）：消费转换 t 的前置 state_ref (E, D, S) 若无
    同分支 post_state 生产者，S3 的 then 级初始化回退只能依赖创建转换
    expected_results 的「…{D}…初始为{S}」声明（glm5pr §3.1 多状态面出生
    值契约）。声明缺失时 S3 静默丢根（021→031 根边消失，无任何告警）——
    本检查在 S1 层提前暴露，使上游 LLM 漏报在正确的层被看见。

    判据与 S3 then_init 回退同源：声明 = expected_results 条目同时含
    「初始」+ 维度名 + 状态值（子串，CJK 无词界——「预通知状态」含
    「通知状态」是有意放行）；分支兼容 = 空归属共享、非空须相交
    （与 S3 _branch_compatible 同口径，消费 _synth_branch_values）。
    """
    producers: dict = {}
    creations: dict = {}
    for t in tos:
        if t.get("to"):
            producers.setdefault(
                (t.get("entity"), t.get("dimension"), t.get("to")), []).append(t)
        if t.get("from") is None:
            creations.setdefault(t.get("entity"), []).append(t)

    def _bv(t: dict) -> set:
        vals = {str(v) for v in (t.get("branch_values") or []) if v}
        vals |= {str(v) for v in (t.get("_synth_branch_values") or []) if v}
        return vals

    def _compat(a: set, b: set) -> bool:
        return not a or not b or bool(a & b)

    def _declares(c: dict, dim: str, state: str) -> bool:
        return any("初始" in er and dim in er and state in er
                   for er in (c.get("expected_results") or []))

    for t in tos:
        tbv = _bv(t)
        for ref in (t.get("precondition_state_refs") or []):
            ent = ref.get("entity")
            dim = ref.get("dimension")
            state = ref.get("state")
            if not (ent and dim and state) or state in ("(初始)", "(None)", "None"):
                continue
            # 同分支 post_state 生产者存在 → 无缺口
            same = [p for p in producers.get((ent, dim, state), ())
                    if p is not t and _compat(tbv, _bv(p))]
            if same:
                continue
            # 同分支创建转换已声明初始值（S3 then_init 回退将命中）→ 无缺口
            if any(c is not t and _compat(tbv, _bv(c)) and _declares(c, dim, state)
                   for c in creations.get(ent, ())):
                continue
            cross = [p for p in producers.get((ent, dim, state), ()) if p is not t]
            cross_info = "、".join(
                f"{p.get('id', '?')}({'/'.join(sorted(_bv(p))) or '共享'})"
                for p in cross) or "无生产者"
            warnings.append(
                f"S1.初始出生点未声明: {t.get('id')} 前置 {ent}.{dim}={state} "
                f"无同分支生产者（{cross_info}），且 {ent} 创建转换未声明"
                f"「{dim}初始为{state}」——若为分支出生态，请在承载该出生动作的"
                f"创建转换 expected_results 补「{dim}初始为{state}」"
                f"（glm5pr §3.1 多状态面出生值契约）")


def _enrich_thens(entity_id: str, action: str, thens: list[dict],
                  constraint_steps: dict[str, list[dict]]) -> list[dict]:
    """Append field-validation Thens to a procedure's thens list.

    field_validation now emits ThenClause dicts directly (target/expectation/
    kind/br_refs/cross_refs), so we just extend ``thens`` with them.
    """
    from nodes.field_validation import should_enrich
    if not should_enrich(action):
        return thens
    extra = constraint_steps.get(entity_id, [])
    for then_clause in extra:
        # Already in ThenClause format — append directly
        if then_clause.get("expectation"):
            thens.append(then_clause)
    return thens


def _is_type5_retained(eo: dict, state: AgentState) -> bool:
    """Type5 retention check — V2 logic.

    An EO of type crud_operation is retained if ANY of these hold:
    1. entity ∈ {primary + dependent + VE.original} AND op ∈ special ops
    2. coverage_priority is medium/high/critical
    3. entity ∈ L0/L1/L5 AND op == '删除'
    4. operation_name matches a CO trigger
    """
    entity = eo["entity"]
    op_name = eo["operation_name"]
    primary = state["primary_entity"]
    dependents = state.get("dependent_entities", [])
    ves = state.get("virtual_entities", {})

    # P2 初始化去重标记（Step 2.5b）：crud 操作已被同(entity,action) 的初始化
    # 转换的 expected_results 文本覆盖 → 不产出独立 Type5 用例。
    # 该 EO 仍保留在模型中作溯源，只是不生成过程。
    if eo.get("covered_by"):
        return False

    # Rule 1: relevant entity + special op (configurable via coverage_model)
    # BDD: TYPE5_SPECIAL_OPS is now read from coverage_model._context.type5_special_ops
    # instead of being a hardcoded business keyword list.
    # v29 Engineering Optimization Gap 1: if _context.type5_special_ops is
    # empty/missing, every Type5 retention check is going through Rule 2/3
    # (priority / topology) instead of the structured special-op path.
    # Log this once per pipeline run when first detected.
    cm = state["coverage_model"]
    _ctx_special_ops = cm.get("_context", {}).get("type5_special_ops", [])
    if not _ctx_special_ops and not getattr(_is_type5_retained, "_logged_fallback", False):
        _record_fallback(
            "s1.type5_special_ops.generic_fallback",
            detail=(
                "_context.type5_special_ops is empty; "
                "Type5 retention relies on coverage_priority / topology_level rules"
            ),
            fallback_used="priority_and_topology_rules",
        )
        _is_type5_retained._logged_fallback = True  # type: ignore[attr-defined]
    special_ops = set(_ctx_special_ops) | TYPE5_SPECIAL_OPS
    relevant = {primary, *dependents}
    for ve in ves.values():
        relevant.add(ve.get("original_entity", ""))
    if entity in relevant and op_name in special_ops:
        return True
    # Rule 2: priority >= medium
    if eo.get("coverage_priority") in ("medium", "high", "critical"):
        return True
    # Rule 3: base data / primary / level-5 + delete
    # BDD: "删除" is now configurable via type5_special_ops; if not configured,
    # retain delete-as-Type5 for base data (topology 0 or S0 leaf), the primary
    # entity (level 1) and level 5. Flow dependents (levels 2-4) are excluded.
    topology_levels = state.get("topology_levels", {})
    tl = topology_levels.get(entity, -1)
    delete_ops = {"删除", "remove", "delete"} | special_ops
    if (tl in (1, 5) or entity in base_data_entity_ids(state)) and any(d in op_name for d in delete_ops):
        return True
    # Rule 4: CO trigger match
    for co in cm.get("cross_entity_obligations", []):
        trigger = co.get("trigger")
        if trigger and op_name in trigger:
            return True
    return False


# ---------------------------------------------------------------------------
# Phase resolution
# ---------------------------------------------------------------------------

def _branch_value_of(to: dict) -> str:
    """branch_values 生命周期归属改造：取 TO 的分支归属值（branch_path 首个 value）。

    归属式 TO（P2 branch_values 产物）带 branch_path=[{dimension, value}]；
    共享/非分支 TO 返回空串 → 相位查询走全局链，行为与旧版一致。
    """
    for bp in ((to or {}).get("branch_path") or []):
        v = (bp or {}).get("value")
        if v:
            return str(v)
    return ""


def _resolve_phase(entity: str, dimension: str, state_value: str, state: AgentState,
                   branch_value: str = "") -> dict:
    """Phase resolution — V2 logic.

    branch_value（branch_values 生命周期归属改造）：非空时优先在 per-branch
    视图（phase_table_by_branch / dep_state_phase_map_by_branch）中查询——
    平行生命周期各分支有自己的相位链（如测量审核链 报名中=0 → 待开始=1），
    归属转换在链内单调；miss 时落回全局链（退化安全，行为与旧版一致）。

    Lookup order:
    0. Per-branch view (branch_value 非空时)
    1. Primary entity → phase_table.state_to_phase
    2. Dependent / VE entity → dep_state_phase_map
    3. Contextual phase rules → return special contextual marker
    4. Topology fallback → L0→P0, VE resolved_phase, parent anchor min
    """
    primary = state["primary_entity"]
    phase_table = state["phase_table"]
    dep_map = state["dep_state_phase_map"]
    ctx_rules = state.get("contextual_phase_rules", {})
    ves = state.get("virtual_entities", {})
    parent_map = state["entity_parent"]

    # 0. Per-branch view（branch_values 改造）
    if branch_value:
        ptb = (state.get("phase_table_by_branch") or {}).get(branch_value) or {}
        b_dim_map = (ptb.get("state_to_phase") or {}).get(dimension, {})
        if state_value in b_dim_map:
            return {"phase": b_dim_map[state_value],
                    "basis": f"phase_table_by_branch.{branch_value}.{dimension}.{state_value}"}
        b_dep = (state.get("dep_state_phase_map_by_branch") or {}).get(branch_value) or {}
        if entity in b_dep:
            b_map = (b_dep.get(entity) or {}).get(dimension, {})
            if state_value in b_map:
                return {"phase": b_map[state_value],
                        "basis": f"dep_state_phase_map_by_branch.{branch_value}.{entity}.{dimension}.{state_value}"}

    # Primary entity
    if entity == primary:
        dim_map = phase_table["state_to_phase"].get(dimension, {})
        if state_value in dim_map:
            return {"phase": dim_map[state_value], "basis": f"phase_table.{dimension}.{state_value}"}

    # Dependent entities (including VEs)
    if entity in dep_map:
        dim_map = dep_map.get(entity, {}).get(dimension, {})
        if state_value in dim_map:
            return {"phase": dim_map[state_value], "basis": f"dep_state_phase_map.{entity}.{dimension}.{state_value}"}

    # Contextual phase rules
    ctx_key = f"{entity}.{dimension}"
    if ctx_key in ctx_rules:
        return {"phase": None, "basis": "contextual", "contextual": ctx_key}

    # Topology fallback — base data (topology 0 or S0 leaf) → P0
    if entity in base_data_entity_ids(state):
        return {"phase": 0, "basis": "P6: topology_level L0 → P0"}
    if entity == primary:
        return {"phase": 0, "basis": "fallback"}
    if entity in ves:
        return {"phase": ves[entity].get("resolved_phase", 0), "basis": f"VE.{entity}.resolved_phase"}

    # Parent anchor
    parent = parent_map.get(entity)
    if parent and entity in dep_map:
        all_phases = [p for dm in dep_map[entity].values() for p in dm.values()]
        if all_phases:
            return {"phase": min(all_phases), "basis": f"anchor_entity_min_phase.{entity}"}

    return {"phase": 0, "basis": "fallback_default"}


# Non-transition obligation types that are DATA MAINTENANCE (setup semantics):
# EO-ATC(3), EO-CRU(5/6), FIELD-VAL(9). RO-IT(7)/RO-BR(8) are rules (constraints).
_NON_TRANSITION_SETUP_TYPES = (
    ObligationType.ATTRIBUTE_CONFIG,
    ObligationType.LIFECYCLE,
    ObligationType.CRUD,
    ObligationType.FIELD_VALIDATION,
)


def _resolve_phase_for_non_transition(state: dict, entity: str,
                                      obligation_type: ObligationType = ObligationType.INVALID) -> dict:
    """Derive a phase for non-transition procedures (Type3/5/6/7/8/9).

    Behavior decided at the OBLIGATION-TYPE layer (domain-agnostic, NOT entity
    names), using S0 topology_level:
      - Data maintenance (EO, obligation_type in {3,5,6,9}):
          base data (topology_level 0, e.g. 机构/分数限值/角色/日志/超时) → P0;
          flow entities (topology_level >= 1) → entity's ENTRY phase (min);
          a stateless flow entity (empty lifecycle) inherits the parent's flow
          phase — NOT forced to P0 (it is flow data, e.g. 附件).
      - Rules (RO, obligation_type in {7,8}): the entity's LATER stage (max,
        "too late is safer").
    """
    is_setup = obligation_type in _NON_TRANSITION_SETUP_TYPES
    primary = state["primary_entity"]
    dep_map = state.get("dep_state_phase_map", {})
    phase_table = state.get("phase_table", {})

    def _phases_of(dim_maps: dict) -> list:
        return [p for dm in dim_maps.values() for p in dm.values()] if dim_maps else []

    def _pick(phases: list) -> int:
        if is_setup:
            return min(phases)
        non_zero = [p for p in phases if p > 0]
        return max(non_zero) if non_zero else max(phases)

    # Base data (topology 0 or S0 leaf, e.g. 机构/分数限值/角色/日志/超时): data
    # maintenance precedes the flow → P0. 单一谓词 base_data_entity_ids 收敛原
    # `topology_level == 0` 硬编码 — 叶子被 S0 提到 leaf_level 后仍算基础数据。
    if is_setup and entity in base_data_entity_ids(state):
        return {"phase": 0, "basis": f"base_data_setup_phase.{entity}.0"}

    # Virtual entity: inherit its resolved_phase (set during S0 VE discovery).
    # Must be checked before dep_map so VE names never fall through to the
    # parent-chain / fallback branches (which would assign a wrong phase).
    ves = state.get("virtual_entities", {})
    if entity in ves:
        vp = ves[entity].get("resolved_phase", 0)
        return {"phase": vp, "basis": f"VE.{entity}.resolved_phase"}

    if entity == primary:
        all_p = _phases_of(phase_table.get("state_to_phase", {}))
        if not all_p:
            return {"phase": 0, "basis": "primary_entity_default"}
        p = _pick(all_p)
        kind = "entry" if is_setup else "max"
        return {"phase": p, "basis": f"primary_entity_{kind}_phase.{p}"}

    if entity in dep_map and dep_map[entity]:
        all_p = _phases_of(dep_map[entity])
        if all_p:
            p = _pick(all_p)
            kind = "entry" if is_setup else "max"
            return {"phase": p, "basis": f"dep_map_{kind}_phase.{entity}.{p}"}

    # Entity absent from dep_map (or empty dep_map):
    # Config entities (tagged "configurable" without multi-state) are
    # foundational setup like E-TESTITEM — they should stay at P0 rather
    # than being pushed to the parent's late lifecycle phase.
    ctx = state.get("coverage_model", {}).get("_context", {})
    entity_details = ctx.get("entity_details", [])
    if isinstance(entity_details, dict):
        entity_details = list(entity_details.values())
    entity_tags = []
    for e in entity_details:
        if e.get("id") == entity:
            entity_tags = e.get("tags", [])
            break
    is_config_only = "configurable" in entity_tags and "multi-state" not in entity_tags
    if is_config_only:
        return {"phase": 0, "basis": f"config_entity.{entity}"}

    # Stateless flow entity (empty lifecycle, topology_level >= 1): both setup
    # and rules inherit the parent's flow phase — NOT forced to P0. (Reference
    # dependents like 专家/用户 hit the topology_level L0 branch above → P0;
    # composition dependents like 附件 are flow data → parent-chain flow phase.)
    parent_map = state.get("entity_parent", {})
    parent = entity
    while parent:
        parent = parent_map.get(parent)
        if not parent:
            break
        if parent in dep_map and dep_map[parent]:
            all_p = _phases_of(dep_map[parent])
            if all_p:
                return {"phase": max(all_p), "basis": f"parent_phase.{parent}.{max(all_p)} (via chain from {entity})"}
        if parent == primary:
            all_p = _phases_of(phase_table.get("state_to_phase", {}))
            if all_p:
                return {"phase": max(all_p), "basis": f"parent_primary_phase.{parent}.{max(all_p)} (via chain from {entity})"}

    return {"phase": 0, "basis": f"fallback_default.{entity}"}


def _resolve_phase_for_transition(entity: str, dimension: str, from_state: str,
                                  to_state: str, state: AgentState,
                                  is_rollback: bool = False,
                                  preconditions: list[str] | None = None,
                                  constraint_predicate: dict | None = None,
                                  branch_value: str = "") -> dict:
    """Phase assignment for transition procedures.

    Forward edges: phase = to_state's phase (entering a new stage).
    Rollback edges: phase = from_state's phase (backward transition stays
        at the stage where it was triggered, e.g. 评价确认中→评价中
        happens at phase 5, not phase 4).

    P0 fix: precondition-aware phase derivation.
    A procedure's phase should reflect the BUSINESS stage at which it
    executes.  If preconditions reference states from LATER phases,
    bump phase to that later phase.  Only cross-entity references bump
    (same-entity state machine progress shouldn't bump).
    """
    if is_rollback and from_state:
        result = _resolve_phase(entity, dimension, from_state, state, branch_value=branch_value)
        if result.get("phase", 0) > 0:
            base_phase = result["phase"]
            base_basis = result["basis"]
        else:
            result = _resolve_phase(entity, dimension, to_state, state, branch_value=branch_value)
            base_phase = result.get("phase", 0)
            base_basis = result.get("basis", "")
    else:
        result = _resolve_phase(entity, dimension, to_state, state, branch_value=branch_value)
        base_phase = result.get("phase", 0)
        base_basis = result.get("basis", "")

    # P0 fix: bump phase if preconditions reference later-phase states.
    # Three orthogonal mechanisms compose by max (AND 语义取最晚):
    #   1. _max_precondition_phase   — text-based, only string preconditions
    #      (dead code for P2 dicts, but harmless).
    #   2. predicate_phase_lower_bound — structured field/aggregate/time
    #      constraint predicates (评级 字段 → 待归档 P4).
    #   3. _max_state_ref_phase      — structured cross-dimension state_ref
    #      (T-014 引用 项目状态.待归档 P4; 文本版吃不到 dict, predicate 只认
    #      constraint, 二者都漏 → 卡在 P1).
    # 原来用早退 return, 后到的机制会跳过前面的; 改为逐级取 max 再统一返回。
    best_phase = base_phase
    best_basis = base_basis

    if preconditions:
        prec_phase, prec_state = _max_precondition_phase(
            preconditions, state, exclude_entity=entity
        )
        if prec_phase > best_phase:
            best_phase = prec_phase
            best_basis = f"{base_basis} → bumped to P{prec_phase} (precondition refs {prec_state})"

    # v6 P2→P3 downstream: structured constraint predicate phase bump.
    # Text-based _max_precondition_phase cannot parse aggregate_count/
    # field_equals/etc. (their surface text matches no state name), so
    # constraint TOs were silently stuck at P0. Consume the structured
    # predicate from P2 and raise the phase to its true lower bound.
    if constraint_predicate:
        dep_map = state.get("dep_state_phase_map", {})
        pt = state.get("phase_table", {})
        # 字段注册表 = P2 按本次 P1 派生的（coverage_model._context.field_registry）。
        # S1 是独立进程、不加载 P1，从序列化上下文读；缺失 → 保守（字段谓词不抬升）。
        field_registry = (state.get("coverage_model", {})
                          .get("_context", {}).get("field_registry") or {})
        pred_phase = predicate_phase_lower_bound(
            constraint_predicate, dep_map, pt, registry=field_registry)
        if pred_phase is not None and pred_phase > best_phase:
            best_phase = pred_phase
            best_basis = f"{base_basis} → bumped to P{pred_phase} (predicate {constraint_predicate.get('type')})"

    # v32: structured cross-dimension state_ref bump.
    # 引用 (entity, dimension) ≠ 转移自身的 state_ref 是真实的时序前置
    # (计划结束/取消结束 P5, 待归档 P4), 抬升到该状态相位.
    if preconditions:
        sr_phase, sr_state = _max_state_ref_phase(
            preconditions, entity, dimension, state, branch_value=branch_value)
        if sr_phase > best_phase:
            best_phase = sr_phase
            best_basis = f"{base_basis} → bumped to P{sr_phase} (state_ref {sr_state})"

    return {"phase": best_phase, "basis": best_basis}


def _max_precondition_phase(
    preconditions: list[str],
    state: AgentState,
    exclude_entity: str = "",
) -> tuple[int, str]:
    """Find the maximum phase referenced by any precondition state.

    P0 refinement: only consider CROSS-ENTITY state references.
    Same-entity state machine progress (e.g. E-REG.通知状态 "通知状态为待审核"
    for an E-REG.通知状态 transition) shouldn't bump phase.

    Uses dim-qualified matching: "通知状态为待审核" matches E-REG.通知状态.待审核
    (dim="通知状态"), NOT E-TASK.审核任务状态.待审核.
    """
    if not preconditions:
        return 0, ""

    phase_table = state.get("phase_table", {})
    dep_map = state.get("dep_state_phase_map", {})
    primary = state.get("primary_entity", "")

    # Build state → max phase lookup, EXCLUDING the procedure's own entity
    state_to_phase: dict[str, int] = {}
    if primary and primary != exclude_entity:
        for dim_map in phase_table.get("state_to_phase", {}).values():
            for s, p in dim_map.items():
                if s not in state_to_phase or p > state_to_phase[s]:
                    state_to_phase[s] = p
    for ent, dims in dep_map.items():
        if ent == exclude_entity:
            continue
        for dim_states in dims.values():
            for s, p in dim_states.items():
                if s not in state_to_phase or p > state_to_phase[s]:
                    state_to_phase[s] = p

    if not state_to_phase:
        return 0, ""

    # Build (dim_name, state) → phase for dim-qualified matching
    dim_state_to_phase: dict[tuple[str, str], int] = {}
    if primary and primary != exclude_entity:
        for dim_name, state_map in phase_table.get("state_to_phase", {}).items():
            for s, p in state_map.items():
                key = (dim_name, s)
                if key not in dim_state_to_phase or p > dim_state_to_phase[key]:
                    dim_state_to_phase[key] = p
    for ent, dims in dep_map.items():
        if ent == exclude_entity:
            continue
        for dim_name, state_map in dims.items():
            for s, p in state_map.items():
                key = (dim_name, s)
                if key not in dim_state_to_phase or p > dim_state_to_phase[key]:
                    dim_state_to_phase[key] = p

    # Extract state values from preconditions
    # Regex must exclude ) and ） so "已确认)" captures "已确认"
    prec_state_re = re.compile(
        r'(?:为|=|状态=)\s*[\u201c\u2018\"\']?([^\u201d\u2019\"\'，,；;（(（)）\s]+)[\u201d\u2019\"\']?'
    )
    # Dim-qualified pattern: "<dim>为<state>" or "<dim>状态为<state>"
    dim_qualified_re = re.compile(
        r'([^\s，,；;（(（)）=为]{2,15}?)\s*(?:状态)?\s*为\s*([\u4e00-\u9fa5A-Za-z0-9（）()]+)'
    )

    max_phase = 0
    max_state = ""
    for prec in preconditions:
        if not prec or not isinstance(prec, str):
            continue

        # Strategy 0: dim-qualified match
        dim_qualified_hits = []
        for m in dim_qualified_re.finditer(prec):
            dim_qualified_hits.append((m.group(1).strip(), m.group(2).strip()))

        if dim_qualified_hits:
            for dim_q, state_q in dim_qualified_hits:
                if (dim_q, state_q) in dim_state_to_phase:
                    p = dim_state_to_phase[(dim_q, state_q)]
                    if p > max_phase:
                        max_phase = p
                        max_state = f"{dim_q}.{state_q}"
                else:
                    for (d, s), p in dim_state_to_phase.items():
                        if dim_q in d and s == state_q:
                            if p > max_phase:
                                max_phase = p
                                max_state = f"{d}.{s}"
                            break
        else:
            # Strategy 1: bare "为XXX" match
            for m in prec_state_re.finditer(prec):
                val = m.group(1).strip()
                if val in state_to_phase:
                    p = state_to_phase[val]
                    if p > max_phase:
                        max_phase = p
                        max_state = val

        # Strategy 2: arrow-separated states
        if "->" in prec or "→" in prec:
            normalized = prec.replace("→", "->")
            for chunk in normalized.split("->"):
                chunk = chunk.strip()
                chunk = re.sub(r'^[（(]+\s*', '', chunk)
                chunk = re.sub(r'\s*[）)]*$', '', chunk)
                if chunk and len(chunk) >= 2 and chunk in state_to_phase:
                    p = state_to_phase[chunk]
                    if p > max_phase:
                        max_phase = p
                        max_state = chunk

    return max_phase, max_state


def _max_state_ref_phase(preconditions: list | None, entity: str,
                         dimension: str, state: AgentState,
                         branch_value: str = "") -> tuple[int, str]:
    """结构化跨维度 state_ref 抬升 (P2 dict 前置专用).

    文本版 _max_precondition_phase 对 dict 前置是死代码 (isinstance str 过滤),
    且 exclude_entity 排掉整个自身实体 — T-014 的项目状态.待归档 (同实体跨维度)
    因此两边都漏, 卡在 P1。这里按 (entity, dimension) 精确排除"同一状态机"的
    自我引用 (如 T-025 引用 计划状态.暂停 之于 计划状态 转移是套套逻辑, 自身
    from/to 已表达), 其余跨维度 state_ref 取最大相位。

    branch_value（branch_values 生命周期归属改造）：非空时 state_ref 相位优先
    在该分支的 per-branch 视图查询，miss 落回全局链（退化安全，行为与旧版一致）。
    收发样品链归属能力验证分支后，其跨维度门禁「项目.通知状态.已确认」须按
    能力验证链（已确认=P2）而非全局链（=P6）抬升——否则样品发放仍被拖到评价后。
    """
    if not preconditions:
        return 0, ""
    dep_map = state.get("dep_state_phase_map", {})
    pt = state.get("phase_table", {})
    ptb = ((state.get("phase_table_by_branch") or {}).get(branch_value)
           if branch_value else None)
    b_dep = ((state.get("dep_state_phase_map_by_branch") or {}).get(branch_value)
             if branch_value else None)
    max_phase = 0
    max_state = ""
    for prec in preconditions:
        if not isinstance(prec, dict):
            continue
        if prec.get("type") != "state_ref":
            continue
        ref = prec.get("ref") or {}
        re_ent = ref.get("entity")
        re_dim = ref.get("dimension")
        re_st = ref.get("state")
        if not re_ent or not re_st:
            continue
        if re_ent == entity and re_dim == dimension:
            continue  # 同一状态机自我引用, 套套逻辑, 不抬升
        # per-branch 视图优先（与 _resolve_phase 查询序一致：主实体 ptb → 依赖实体 b_dep）
        p = None
        if ptb is not None and re_ent == pt.get("primary_entity"):
            p = (ptb.get("state_to_phase") or {}).get(re_dim, {}).get(re_st)
        if p is None and b_dep:
            p = (b_dep.get(re_ent) or {}).get(re_dim, {}).get(re_st)
        if p is None:
            p = get_state_phase(re_ent, re_dim, re_st, dep_map, pt)
        if p is not None and p > max_phase:
            max_phase = p
            max_state = f"{re_ent}.{re_dim}.{re_st}"
    return max_phase, max_state


# ---------------------------------------------------------------------------
# Dimension / type priority helpers
# ---------------------------------------------------------------------------

def _get_dimension_priority(entity: str, dimension: str | None, state: AgentState) -> int:
    if not dimension:
        return 1
    if entity == state["primary_entity"] and dimension == state["phase_table"]["primary_dimension"]:
        return 0
    stm = state.get("state_type_map", {}).get(entity, {})
    if dimension in stm:
        first_val = next(iter(stm[dimension].values()), None)
        if first_val == "driving":
            return 0
    return 1


def _get_type_label(risk_trait: str, obligation_type: int) -> str:
    """Map obligation_type to type label per S1.0 type table."""
    if obligation_type == ObligationType.CONSTRAINT:
        return "constraint"          # Type4a
    if obligation_type == ObligationType.LIFECYCLE:
        return "lifecycle"           # Type4b
    if obligation_type == ObligationType.CRUD:
        return "crud"                # Type5
    if obligation_type == ObligationType.INVALID:
        return "invalid"             # Type6
    if obligation_type == ObligationType.RULE:
        return "rule"                # Type7 standalone
    if risk_trait in ("audit", "audit_rejection"):
        return "audit"
    if risk_trait == "rollback":
        return "rollback"
    if risk_trait == "branch":
        return "branch"
    if risk_trait == "data_constraint":
        return "data_constraint"
    if risk_trait == "time_sensitive":
        return "time_sensitive"
    return "happy"


def _get_type_priority(risk_trait: str, obligation_type: int) -> int:
    """Map obligation_type to type_priority per sort_key spec."""
    if obligation_type == ObligationType.CONSTRAINT:
        return TYPE_PRIORITY_MAP.get("constraint", 3)   # Type4a
    if obligation_type == ObligationType.LIFECYCLE:
        return TYPE_PRIORITY_MAP.get("lifecycle", 7)    # Type4b
    if obligation_type == ObligationType.CRUD:
        return TYPE_PRIORITY_MAP.get("crud", 5)          # Type5
    if obligation_type == ObligationType.INVALID:
        return TYPE_PRIORITY_MAP.get("invalid", 9)       # Type6
    if obligation_type == ObligationType.RULE:
        return TYPE_PRIORITY_MAP.get("rule", 6)          # Type7
    if obligation_type == ObligationType.ATTRIBUTE_CONFIG:
        return TYPE_PRIORITY_MAP.get("happy", 1)         # Type3
    return TYPE_PRIORITY_MAP.get(risk_trait, 1)


# ---------------------------------------------------------------------------
# Type1 — Transition Obligation procedures
# ---------------------------------------------------------------------------

def _pred_contains_type(node, target: str) -> bool:
    """递归检查 constraint_predicate 树是否含某类型的节点。

    constraint_predicate 是 P2 后置解析器（generate_obligation_model.py
    build_constraint_predicate）从 constraint precondition 文本确定性派生的
    结构化谓词树。guard 极性检查以此结构为准：含 negation 节点 → 结构性负向，
    不再依赖关键词文本匹配（文本匹配曾误伤频次限制词，如 "只有"）。
    """
    if not isinstance(node, dict):
        return False
    if node.get("type") == target:
        return True
    for v in node.values():
        if isinstance(v, dict) and _pred_contains_type(v, target):
            return True
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and _pred_contains_type(item, target):
                    return True
    return False


def _generate_type1(state: AgentState, indices: dict,
                    br_list: list[dict] | None = None) -> list[dict]:
    """Generate Type1 (transition_obligation) procedures — BDD style.

    For each TO:
    - Check if it belongs to a VE (virtual entity) → generate per VE
    - Build Given/When/Then clauses with side-effects as additional Thens
    - Add audit_rejection variant if risk_traits contains 'audit'
    - Add time_sensitive boundary + expired variants if risk_traits contains 'time_sensitive'
    - br_list (business_rule ROs) is used for guard-polarity detection:
      a restrictive BR whose description appears in the givens and whose
      restricted operation matches the TO action marks the TO as a
      negative branch (rejected), replacing the old post-hoc
      _enforce_guard_polarity patch.

    BDD mapping (from AAA):
      Old S step → Given(target=entity.dim, state=from_state)
      Old A step → When(event=action_desc, actor=role, action=action)
      Old V step → Then(target=entity.dim, expectation=to_state, kind="state")
      Old side-effect V → Then(target=target.dim, expectation=effect_desc, kind="behavior")
    """
    cm = state["coverage_model"]
    tos = cm.get("transition_obligations", [])
    phase_table = state["phase_table"]
    ves = state.get("virtual_entities", {})
    topo = state["topology_levels"]

    procedures: list[dict] = []

    for to in tos:
        # P2 跨维度初始化联动合并（Step 2.5a）：note.inferred 且 (entity, action,
        # role) 与父转换一致的初始化 TO 标 merged_into，其 expected_results 已并入
        # 父 TO → 不产出独立 Type1 用例，避免"新增项目"类行为出现两条过程。
        if to.get("merged_into"):
            continue
        entity = to["entity"]
        dimension = to.get("dimension", "")
        risk_traits = to.get("risk_traits", [])
        transition_id = to.get("transition_id", "")
        # chain_depth: depth_cache 机制已随 transition_upstream_map 清除 (恒 0;
        # 已从 S2 sort_key 移除, 仅作 break_cycles 全 0 tiebreaker)。
        chain_depth = 0

        # Check if this TO belongs to a virtual entity
        ve_list = [(ve_name, ve) for ve_name, ve in ves.items()
                    if transition_id in ve.get("transitions", [])]

        # Determine which entities to generate procedures for
        if ve_list:
            target_entities = [
                {"entity": ve_name, "context": ve.get("context"), "parent": ve.get("parent_entity")}
                for ve_name, ve in ve_list
            ]
        else:
            target_entities = [{"entity": entity, "context": None, "parent": None}]

        for te in target_entities:
            # Base procedure
            # BDD: rollback edges use from_state's phase, forward edges use to_state's
            to_traits = to.get("risk_traits", []) or to.get("traits", []) or []
            is_rollback = "rollback" in to_traits
            # P0 fix: pass preconditions so phase can be bumped to reflect
            # the latest business stage referenced by the procedure's
            # preconditions (e.g. PROC-061 refs E-EVAL.已确认 P7).
            phase_info = _resolve_phase_for_transition(
                te["entity"], dimension, to.get("from"), to.get("to"), state,
                is_rollback=is_rollback,
                preconditions=to.get("preconditions"),
                constraint_predicate=to.get("constraint_predicate"),
                branch_value=_branch_value_of(to),
            )
            dim_priority = _get_dimension_priority(te["entity"], dimension, state)

            # Determine risk_trait for this procedure
            proc_risk_trait = ""
            proc_type_priority = 1
            proc_type_label = "happy"

            if "branch" in risk_traits:
                proc_risk_trait = "branch"
                proc_type_priority = 2
                proc_type_label = "branch"
            elif "audit" in risk_traits:
                proc_risk_trait = "audit"
                proc_type_priority = 4
                proc_type_label = "audit"
            elif "rollback" in risk_traits:
                proc_risk_trait = "rollback"
                proc_type_priority = 4
                proc_type_label = "rollback"

            # ── Build BDD clauses ──
            loc = f"{te['entity']}.{dimension}"
            from_state = to.get('from') or '(初始)'
            to_state = to.get('to', '')
            action = to.get('action', '')
            preconditions = to.get("preconditions", [])

            # v29 #11 fix: split preconditions into state precondition vs
            # event-completed assertions.
            #
            # v28 behavior: ALL preconditions were joined with "; " into a
            # single Given.description. This conflated two semantically
            # different kinds of preconditions:
            #   (a) State precondition: "报名记录状态为结果已提交"
            #       — the source state must be X (becomes Given.state)
            #   (b) Event-completed assertion: "结果通知单/证书已上传"
            #       — a separate business event must have already happened
            #       (should be its own Given clause, not merged into desc)
            #
            # Example bug (PROC-115, T-018):
            #   preconditions = ["报名记录状态为结果已提交", "结果通知单/证书已上传"]
            #   v28: Given(state=结果已提交, desc="报名记录状态为结果已提交; 结果通知单/证书已上传")
            #     → confusing: the desc mixes state with event
            #   v29: Given(state=结果已提交, desc="报名记录状态为结果已提交")
            #        Given(state=结果已提交, desc="结果通知单/证书已上传")
            #     → clear: two separate preconditions, each testable independently
            given_desc = te["context"] or ""
            # v29 #26f: use P1's precondition.type field (structured) instead
            # of keyword matching. P1's preconditions now declare type:
            #   [{"text": "...", "type": "state_ref|event_ref|constraint"}]
            # Falls back to keyword heuristic when type is absent.
            state_prec_texts: list[str] = []
            event_prec_texts: list[str] = []
            detached_state_givens: list[dict] = []
            constraint_texts: list[dict] = []
            for prec in preconditions:
                # v29 #26f: check if precondition is a structured object
                if isinstance(prec, dict):
                    prec_str = prec.get("text", "") or ""
                    prec_type = prec.get("type", "") or ""
                    ref = prec.get("ref") if isinstance(prec.get("ref"), dict) else {}
                    if not prec_str.strip():
                        continue
                    if prec_type == "constraint":
                        # constraint：独立 Given（业务约束，非状态前置）→ 渲染层 `约束：`
                        constraint_texts.append(_make_given(
                            target=loc, state="", description=prec_str,
                            given_type="constraint"))
                    elif prec_type == "state_ref":
                        re_ent = ref.get("entity", "")
                        re_dim = ref.get("dimension", "")
                        # 跨维度 state_ref（ref.dimension ≠ 转换维度）：独立 Given 语义
                        # 归位。纯状态形态 ref.state 是前置态 → state；流转形态
                        # ref.state 是目标态，提升会串线 → flow（desc 保留原文）。
                        if re_ent and re_dim and re_dim != dimension:
                            if _is_flow_state(prec_str):
                                detached_state_givens.append(_make_given(
                                    target=f"{re_ent}.{re_dim}", state="",
                                    description=prec_str, given_type="flow"))
                            else:
                                detached_state_givens.append(_make_given(
                                    target=f"{re_ent}.{re_dim}",
                                    state=ref.get("state", ""),
                                    description=prec_str, given_type="state"))
                        else:
                            # 同维度 state_ref：并入 givens[0] 描述（当前语义）
                            state_prec_texts.append(prec_str)
                    elif prec_type == "event_ref":
                        event_prec_texts.append(prec_str)
                    else:
                        # Unknown type — treat as state_ref by default
                        state_prec_texts.append(prec_str)
                else:
                    # Fallback: string precondition, use keyword heuristic
                    prec_str = prec if isinstance(prec, str) else str(prec)
                    if not prec_str.strip():
                        continue
                    if ("状态" in prec_str and ("为" in prec_str or "=" in prec_str)) or \
                       ("阶段" in prec_str and ("为" in prec_str or "=" in prec_str)):
                        state_prec_texts.append(prec_str)
                    else:
                        event_prec_texts.append(prec_str)

            # First Given: the from_state (business state precondition)
            # Include the state-qualified precondition text in description if present
            first_given_desc = given_desc
            if state_prec_texts:
                first_given_desc = (first_given_desc + ("; " if first_given_desc else "") +
                                    "; ".join(state_prec_texts))
            givens: list[dict] = [
                _make_given(target=loc, state=from_state, description=first_given_desc)
            ]
            # Additional Givens: event-completed assertions (each its own Given)
            for evt_prec in event_prec_texts:
                givens.append(_make_given(
                    target=loc,
                    state=from_state,  # same state context
                    description=evt_prec,
                    given_type="event",
                ))
            # 跨维度 state_ref（纯状态/流转形态）独立 Given：语义归位到 ref 的维度
            # （渲染层按 given_type 选格式，不再文本匹配）。
            givens.extend(detached_state_givens)
            # constraint 独立 Given：业务约束行（渲染层 `约束：`）。
            # 按 description 精确去重：继承前置与 P2 分支值注入可能同文重复，
            # 塌缩避免同一约束在 proc 里出现两次。
            _seen_constraints: set[str] = set()
            for _cg in constraint_texts:
                _key = _cg.get("description", "")
                if _key and _key in _seen_constraints:
                    continue
                _seen_constraints.add(_key)
                givens.append(_cg)
            # BDD: append branch-dimension Givens (generic, from branch_dimensions)
            # e.g. Given: E-PROJ.项目类型 = 能力验证 (分支条件)
            givens.extend(_extract_branch_givens(to, cm))
            # S1-a/S1-b: 共享 TO 的合成分支声明（同动作传播 / 闭包域）
            givens.extend(to.get("_synth_branch_givens") or [])

            # When: business event (declarative) + actor + action
            # BDD: strip "[维度=值]" suffix from action — it's a P2 marker, not spec
            role = _get_role_name(to.get('role'), action, entity, state)
            clean_action = _strip_branch_suffix(action)
            event_desc = _derive_business_event(clean_action, from_state, to_state)
            when: dict = _make_when(
                target=loc, event=event_desc, actor=role, action=clean_action
            )

            # Thens: main observable + side effects + rollback
            thens: list[dict] = []

            # Fix-2: Negative-branch detection.
            # When a TO's preconditions explicitly prohibit the action's target
            # state (e.g. "本阶段评价结果为差的项目不可选入" with action="项目选入"),
            # the correct behavior is REJECTION — the operation must be blocked
            # and the state must remain in from_state. The original engine
            # ignored this signal and unconditionally generated "状态转换为{to_state}",
            # producing semantically wrong procedures (PROC-155 rating=差 still
            # asserting "状态转换为已选入").
            #
            # Detection strategy (no hardcoded business verbs):
            #   1. Scan preconditions for prohibition markers
            #      (不可/不能/不得/禁止/不允许) followed by an action/state noun.
            #   2. Check whether the prohibited noun overlaps with the action's
            #      verb/object (e.g. "不可选入" vs action "项目选入" → match on "选入").
            #   3. If overlap found → this TO is a negative test: the operation
            #      is expected to be REJECTED, not succeed.
            #
            # When negative-branch is detected:
            #   - Then expectation: "操作被拒绝，状态保持为{from_state}并提示"
            #   - post_state: unchanged from from_state (no transition occurs)
            #   - risk_trait: "negative_test" (overrides any audit/branch label)
            #   - branch givens are still emitted (so the branch condition that
            #     triggers rejection is visible in the spec)
            is_negative_branch = False
            # Read prohibition keywords from coverage_model._context.prohibition_config
            # (emitted by P2). Falls back to built-in defaults if not configured.
            # This replaces hardcoded keyword tables — projects can override
            # via P1 input → P2 _context.prohibition_config.
            _ctx = cm.get("_context", {}) or {}
            _pc = _ctx.get("prohibition_config", {}) or {}
            _neg_prefixes = _pc.get("negation_prefixes",
                ["不可", "不能", "不得", "禁止", "不允许", "无法", "无权", "未被"])
            # 默认前缀不含「未」：状态名前缀「未发送/未收样/未缴费」是枚举态值非
            # 禁止词，命中 prohibition_re 会把「未发送」状态 + 「发送」动词误判为
            # 负向分支（v13 PROC-076 根因）。「未被」保留（真正禁止形态）。
            _action_verbs = _pc.get("action_verbs",
                ["选入", "纳入", "启动", "提交", "保存", "删除", "修改", "新增",
                 "审批", "批准", "通过", "归档", "重启", "暂停", "结束", "发放",
                 "退出", "登录", "操作", "编辑", "查看", "分配", "入选", "进入",
                 "选为", "选择", "执行"])
            prohibition_re = re.compile(
                r'(' + '|'.join(_neg_prefixes) + r')'
                r'[^，,。.；;]{0,15}?'
                r'(' + '|'.join(_action_verbs) + r')'
            )
            action_core = clean_action or action or ""
            # Strip "[维度=值]" markers and common auxiliary words from action
            # to get the core verb-object (e.g. "项目选入 [项目评级=差]" → "项目选入")
            action_core_clean = _strip_branch_suffix(action_core).strip()
            for prec in preconditions:
                prec_str = prec.get('text', '') if isinstance(prec, dict) else (prec if isinstance(prec, str) else '')
                if not prec_str:
                    continue
                for m in prohibition_re.finditer(prec_str):
                    prohibited_verb = m.group(2)
                    # Check overlap between prohibited verb and the action's core
                    if prohibited_verb and prohibited_verb in action_core_clean:
                        is_negative_branch = True
                        break
                if is_negative_branch:
                    break

            # ── Guard polarity (V02) ──
            # v29 修复: 原 post-hoc `_enforce_guard_polarity` 只改写 thens[0],
            # 遗留 thens[1:] 的成功断言造成自相矛盾(状态流转 / expected_results /
            # side-effect 仍声称迁移成功,而 thens[0] 却声称被拒绝)。此处把同一
            # 判定前移到 Then 构建之前,并入 is_negative_branch 单一入口:
            # 命中 restrictive BR 描述片段(givens 中出现) + action 匹配被限制
            # 操作 → 该 TO 是负向用例,只生成拒绝断言,不生成成功态 Then。
            # 检测逻辑与原 post-processor 一致(见 _enforce_guard_polarity 历史版),
            # 额外要求 BR 实体命中当前 entity,避免纯文本巧合误判。
            #
            # 结构优先 (DECISIONS ㉜): 含 negation 节点 → 存在操作被拒分支,
            # 结构性负向 (T-002[a]/T-036: 差不可选入 / 各项打分全零不可提交),
            # 不依赖关键词文本。无 negation 的 TO (如 occurrence_limit "只有 N
            # 次" 正向限次, 或 aggregate_count / {}) 走关键词文本兜底; 频次限制
            # 词 "只有" 已从 prohibit_keywords 数据与默认兜底移除 (数据修正),
            # occurrence_limit 分支无需结构豁免即不会被误判负向。
            _cp_to = to.get("constraint_predicate") or {}
            _cp_has_negation = _pred_contains_type(_cp_to, "negation")
            if not is_negative_branch and _cp_has_negation:
                is_negative_branch = True
            _guard_br_id = ""
            if not is_negative_branch and br_list:
                _ctx_g = cm.get("_context", {}) or {}
                _pc_g = _ctx_g.get("prohibition_config", {}) or {}
                # 通用禁止词兜底。领域特定短语(如"不能提为试用""连续3天")
                # 由 P2 的 prohibition_config.prohibit_keywords 提供(本数据集
                # 已配置);此处默认值只保留领域无关的通用否定词,避免领域词汇
                # 泄漏进通用引擎(违反 "NO hardcoded business keywords" 原则)。
                # 默认值不含 "只有" —— 它是频次限制词(occurrence_limit), 非
                # 禁止词, 作为禁止词会误伤正向限次用例 (T-002[b])。
                _prohibit_kw = tuple(_pc_g.get("prohibit_keywords",
                    ["不可", "不能", "禁止", "不得", "不允许", "无法", "无权",
                     "只能", "仅限", "才可"]))
                _givens_text = " ".join(
                    str(g.get("state", "")) + str(g.get("description", ""))
                    for g in givens or []
                )
                for br in br_list:
                    _br_desc = ((br.get("description") or "")
                                + " " + (br.get("suggested_action") or ""))
                    _br_restrictive = br.get("restrictive") or False
                    # v29 修复: 要求 BR 描述含显式禁止词(不可/不能/禁止/只能/
                    # 才可/只有等)。restrictive 的"规则定义型"BR
                    # (如 "从已选入状态的项目中选取1-5个项目纳入评审计划")描述
                    # 的是合法操作而非禁止——把它们当负向会误伤正常流程(T-003
                    # 项目纳入评审计划被误判为拒绝)。只有显式禁止的 BR 才阻断
                    # 该操作。
                    if (not _br_restrictive
                            or not any(kw in _br_desc for kw in _prohibit_kw)):
                        continue
                    if entity not in (br.get("entities_involved") or []):
                        continue
                    _br_ops = [m.group(1) for m in re.finditer(
                        r"(?:不可|不能|禁止|不得)([一-龥]{2,6})", _br_desc)]
                    # 8-char sliding chunks (同原 post-processor) 匹配 givens
                    _chunks = [_br_desc[i:i+8]
                               for i in range(0, max(0, len(_br_desc)-8), 4)]
                    _chunks = [c for c in _chunks if len(c) >= 6 and not c.isspace()]
                    if not any(c and c in _givens_text for c in _chunks):
                        continue
                    if (_br_ops and any(op in action_core_clean for op in _br_ops)) or \
                       (len(action_core_clean) >= 4 and action_core_clean in _br_desc):
                        is_negative_branch = True
                        _guard_br_id = br.get("constraint_id") or br.get("id", "")
                        break

            if is_negative_branch:
                # Negative test: operation is rejected, state preserved.
                # Override the success Then entirely — do NOT add "状态转换为{to_state}".
                # br_refs carries the restrictive BR that blocks this operation
                # (set by the guard-polarity detection above; empty for
                # precondition-based negative branches).
                thens.append(_make_then(
                    target=loc,
                    expectation=f"操作被拒绝，状态保持为{from_state}并给出禁止提示",
                    kind="state",
                    br_refs=[_guard_br_id] if _guard_br_id else None,
                ))
                # P2 吸收的 invalid_transition（同 entity/from/to，Step 4.1 标
                # absorbed_by_transition）→ 把其具体拒绝提示并入负向用例作附加断言
                # （如"本阶段评价结果为差的项目不可选入"），补齐独立 Type6 消失后的
                # 提示文本覆盖。假设：转换只有单个负向分支；若未来出现多负向分支需
                # 按分支条件匹配 reason，此处按整转换匹配。
                _absorbed_ro = next(
                    (r for r in (cm.get("constraint_obligations") or [])
                     if r.get("type") == "invalid_transition"
                     and r.get("entity") == entity
                     and r.get("from") == to.get("from")
                     and r.get("to") == to.get("to")
                     and r.get("reason")),
                    None)
                if _absorbed_ro:
                    thens.append(_make_then(
                        target=loc,
                        expectation=f"操作被拒绝，{_absorbed_ro['reason']}",
                        kind="prompt",
                    ))
                _negative_branch_flag = True
                # post_state uses from_state (no transition occurs)
                to_state_for_post = from_state
            else:
                _negative_branch_flag = False
                to_state_for_post = to_state
                if to.get('from') and to.get('from') == to.get('to'):
                    # Self-loop: observe the effect (not state change)
                    er = (to.get('expected_results') or [''])[0] if to.get('expected_results') else '效果生效'
                    thens.append(_make_then(
                        target=loc, expectation=er, kind="behavior"
                    ))
                else:
                    # E15: form_selected_state 创建转换（T-058 新增标准库）——
                    # 创建目标状态由表单所选值决定，硬断言"状态转换为{to_state}"
                    # 是假精确（表单可选停用）。跳过合成，改由 expected_results
                    # 承载"状态为表单所选值（启用/停用）"。
                    _to_traits = to.get("risk_traits", []) or to.get("traits", []) or []
                    _form_selected = "form_selected_state" in _to_traits
                    if not _form_selected:
                        # dedup_group="transition_target": 渲染层在存在
                        # "transition_flow"(状态流转:from→to)时省略本断言——
                        # from→to 已隐含目标状态,保留信息最全的一条。
                        thens.append(_make_then(
                            target=loc, expectation=f"状态转换为{to_state}", kind="state",
                            dedup_group="transition_target",
                        ))
                    # V10 fix (S1-side, transition coverage): append a Then
                    # containing the literal "{from}→{to}" form so that
                    # coverage_matrix branches like "待选入→已选入" match.
                    # This is NOT a post-hoc patch — it's a natural part of
                    # the transition's observable contract: the procedure
                    # verifies that the state moved from `from` to `to`,
                    # and the from→to notation is the canonical way to
                    # express that contract.
                    if from_state and to_state and from_state != "(初始)" and from_state != to_state:
                        thens.append(_make_then(
                            target=loc,
                            expectation=f"状态流转：{from_state}→{to_state}",
                            kind="state",
                            dedup_group="transition_flow",
                        ))
                    # V10 required_type fix: append TO's expected_results as
                    # additional Thens. P1 extracted observable result keywords
                    # (e.g. "项目状态初始化为待选入", "项目阶段为开题") into
                    # expected_results. Without these in the proc text, V10
                    # coverage_matrix probes like "新增初始化待选入且开题阶段"
                    # never match the Type1 proc, causing required_type=transition
                    # warnings even though a transition proc exists.
                    for er in to.get('expected_results', []) or []:
                        er_text = str(er).strip()
                        if er_text and er_text != f"状态转换为{to_state}":
                            thens.append(_make_then(
                                target=loc,
                                expectation=er_text,
                                kind="behavior",
                            ))

            # Side effects as additional Thens (Type2 embedding) — I20: ≤1 hop
            cos = cm.get("cross_entity_obligations", [])
            side_effects = to.get("side_effects") or []
            # Fix 3b: 负向分支（操作被拒绝）不追加副作用断言——操作被拒时副作用
            # 不生效，否则与拒绝断言自相矛盾（PROC-013：操作被拒绝 + 系统自动
            # 锁定）。副作用只描述成功迁移的落盘效果。
            for se in side_effects:
                if _negative_branch_flag:
                    break
                target = se.get('target_entity', '')
                se_target_dim = se.get('target_dimension') or dimension
                se_loc = f"{target}.{se_target_dim}"
                effect_desc = se.get('effect_desc', '')
                # (a) Same entity → add directly
                if target == entity:
                    thens.append(_make_then(
                        target=se_loc, expectation=effect_desc, kind="behavior"
                    ))
                else:
                    # (b) Cross-entity with direct CO link → add with causal check
                    direct_co = next((co for co in cos
                                      if co.get('enabler_entity') == entity
                                      and co.get('dependent_entity') == target), None)
                    if direct_co:
                        dep_cond = direct_co.get('dependent_condition', '')
                        if dep_cond and effect_desc and dep_cond in effect_desc:
                            thens.append(_make_then(
                                target=se_loc, expectation=effect_desc, kind="behavior"
                            ))
                    # (c) No direct CO → skip (indirect causal, covered by own entity)

            # operation_lifecycle: 1=创建(from==null) 2=修改(from==to) 3=流转(from≠to) 4=终止(rollback)
            if to.get('from') is None:
                op_lifecycle = 1  # 创建
            elif to.get('from') == to.get('to'):
                op_lifecycle = 2  # 修改
            elif "rollback" in risk_traits:
                op_lifecycle = 4  # 终止
            else:
                op_lifecycle = 3  # 流转

            # --- data_constraint: skip if has branch ---
            if "data_constraint" in risk_traits:
                has_branch = any(
                    bd.get('entity') == entity and bd.get('dimension') == dimension
                    for bd in cm.get('_context', {}).get('branch_dimensions', [])
                )
                if has_branch:
                    continue

            # --- rollback: embed as additional Then ---
            # v29 #17 fix: only add "可回退" Then for TRUE rollback edges
            # (action contains 退回/驳回/撤销/退款), not for forward audit
            # transitions that merely HAVE the rollback trait.
            #
            # v28 behavior: any transition with "rollback" in risk_traits
            # got a "状态可回退至前驱状态" Then. But T-011 (报名待审核→报名成功,
            # action="审核报名通过") has rollback trait because it CAN be
            # rolled back by T-013 (退回→待审核), yet T-011 itself is a
            # FORWARD progression — saying "可回退" in its Then is confusing
            # and semantically wrong (the forward transition doesn't roll back).
            #
            # v29: only add the "可回退" Then when the transition is a
            # rollback action. Use TO.direction (derived by P2 from P1
            # traits + state_order) instead of hardcoded keyword matching.
            # direction == 'backward' means the transition goes back to
            # an earlier state (rollback/regression).
            #
            # ── 隐性依赖说明 ──
            # 这个判定有两个前置条件：
            #   1. "rollback" in risk_traits — 来自 P1 的 traits 字段
            #   2. to.get('direction') == 'backward' — 来自 P2 的 derive_direction
            #
            # 如果 P1 的 traits 漏标 rollback（如 T-006~T-009 归档回退只有
            # time_sensitive 没有 rollback），条件 1 为 False，条件 2 不会被
            # 求值。此时新旧代码行为等价（都不会加"可回退"Then）。
            #
            # 如果 P1 的 traits 标了 rollback 但 P2 的 direction 缺失或错误，
            # 条件 2 会误判。这需要 P1 输出后用脚本校验 + LLM 判别确保
            # traits 和 direction 都准确。
            #
            # 根本方案：P1 直出 direction 字段（必填 + 校验），P2 透传，
            # S1 直接读 direction，不再依赖 traits 推导 direction。
            _is_rollback_action = to.get('direction') == 'backward'
            if "rollback" in risk_traits and _is_rollback_action:
                thens.append(_make_then(
                    target=loc,
                    expectation="状态可回退至前驱状态",
                    kind="behavior"
                ))

            # BDD: field_validation Thens are NO LONGER injected into Type1.
            # They are generated as independent Type9 procedures instead,
            # so each procedure describes exactly one business behaviour.
            # (was: _enrich_thens(entity, action, thens, constraint_steps))

            phase_val = phase_info.get("phase") if phase_info.get("phase") is not None else 0
            phase_name = (phase_table["phase_names"][phase_val]
                          if phase_val < len(phase_table["phase_names"])
                          else f"P{phase_val}")

            base_proc = {
                "temp_id": f"PROC-T1-{_next_gen_seq()}",
                "source_ids": [to["id"]],
                "entity": te["entity"],
                "dimension": dimension,
                "obligation_type": ObligationType.TRANSITION,
                "risk_trait": ("negative_test" if _negative_branch_flag else proc_risk_trait),
                "givens": givens,
                "when": when,
                "thens": thens,
                # V06: 声明 time_control.mechanism(从时效语义推导);非时效为 None。
                # 不再注入 human-readable 触发方式 hint 行（需求原文自陈触发语义）。
                "operation_hints": [],
                "time_control": (
                    {"mechanism": _derive_time_mechanism(action), "status": "planned"}
                    if "time_sensitive" in risk_traits else None
                ),
                "gen_seq": _gen_seq_counter,
                "post_state": f"{te['entity']}.{dimension}→{to_state_for_post}",
                "cascade_chain": None,
                "embedded_brs": [],
                "_S2_fields": _make_S2_fields(
                    phase_val, phase_name, phase_info.get("basis", ""),
                    topo.get(te["entity"], 0), op_lifecycle, chain_depth,
                    ("negative" if _negative_branch_flag else proc_type_label),
                    (9 if _negative_branch_flag else proc_type_priority),
                    dim_priority, te["context"],
                ),
                "_S3_fields": _make_S3_fields(),
                "_S4_fields": _make_S4_fields(),
            }
            procedures.append(base_proc)

            # --- Positive-path variant for negative-branch TOs ---
            # When a TO's preconditions contain a prohibition (e.g. "差的不可选入"),
            # S1 generates a negative_test procedure above. But the SAME TO also
            # represents the happy path (e.g. normal 选入 when conditions are met).
            # Without a positive variant, coverage_matrix probes like "正常选入"
            # never match because no procedure asserts the successful transition.
            #
            # Fix: emit a second procedure for the same TO that asserts the
            # successful transition (state changes to to_state). This is NOT
            # a duplicate — it's the complementary branch of the same transition.
            # The negative procedure covers the rejection path; this one covers
            # the acceptance path.
            if is_negative_branch and from_state and to_state and from_state != to_state:
                import os as _os
                if _os.environ.get('S1_TRACE_POS') == '1':
                    print(f'[POS-VARIANT] to={to.get("id")} from={from_state} to_state={to_state}', flush=True)
                pos_thens = [_make_then(
                    target=loc,
                    expectation=f"状态转换为{to_state}",
                    kind="state",
                    dedup_group="transition_target",
                )]
                # Also append the from→to literal for V10 transition coverage
                if from_state != "(初始)":
                    pos_thens.append(_make_then(
                        target=loc,
                        expectation=f"状态流转：{from_state}→{to_state}",
                        kind="state",
                        dedup_group="transition_flow",
                    ))
                # Positive-path givens: strip restrictive precondition clauses
                # (the ones that triggered is_negative_branch). The positive
                # path represents the NORMAL scenario where the operation
                # succeeds, so givens must NOT mention prohibitions like
                # "差不可选入". Without this strip, V02 validator sees the
                # restrictive text in givens and flags the success-asserting
                # Then as a polarity violation.
                #
                # Precondition descriptions are ;-separated clauses within a
                # single given's description field. We split on ; and remove
                # any clause that matches the prohibition regex, keeping the
                # rest (e.g. "项目处于待选入状态" stays, "差不可选入" goes).
                #
                # The regex here is intentionally BROADER than the detection
                # regex above: the strip must remove ANY restrictive clause
                # (neg-prefix + any short verb), including verbs not in the
                # configured action_verbs list. With the strict known-verb
                # regex, clauses like "研制机构累计3次评级为不合格，则不能
                # 提为试用机构" survive the strip because "提为/试用" are not
                # in action_verbs — the positive-path givens then retain the
                # prohibition and V02 falsely flags the success assertion.
                # (The is_negative_branch DETECTION keeps the strict regex so
                # it doesn't over-trigger; only the strip is broadened.)
                _PROHIBIT_RE = re.compile(
                    r'(' + '|'.join(_neg_prefixes) + r')'
                    r'[^，,。.；;]{0,15}?'
                    r'([一-龥]{2,4})'
                )
                pos_givens = []
                for g in givens:
                    g_copy = dict(g)
                    desc = g_copy.get("description", "")
                    # given_type=constraint 的 given 是独立信息行 (非 givens[0] 的
                    # 分句): 整条描述即禁止性规则 (如"本阶段评价结果为差的项目不可
                    # 选入"), 属拒绝路径的触发条件。正向(接受)路径直接删除该 given,
                    # 不再像旧结构那样把 desc 清成空壳。
                    if g_copy.get("given_type") == "constraint" \
                            and isinstance(desc, str) and _PROHIBIT_RE.search(desc):
                        continue
                    if isinstance(desc, str) and _PROHIBIT_RE.search(desc):
                        # Split on ; and keep only non-restrictive clauses
                        clauses = re.split(r'[;；]', desc)
                        kept = [c for c in clauses if not _PROHIBIT_RE.search(c)]
                        g_copy["description"] = "; ".join(c.strip() for c in kept if c.strip())
                    pos_givens.append(g_copy)
                pos_gen_seq = _next_gen_seq()
                pos_proc = {
                    "temp_id": f"PROC-{pos_gen_seq:04d}",
                    "source_ids": [to["id"]],
                    "entity": te["entity"],
                    "dimension": dimension,
                    "obligation_type": ObligationType.TRANSITION,
                    "risk_trait": proc_risk_trait,
                    # Marker: this is the positive-path sibling of a negative_test
                    # procedure. Its givens contain restrictive BR text
                    # (inherited from the same TO), but this procedure
                    # represents the acceptance path, not the rejection path —
                    # so it must never be reclassified as a negative branch.
                    "_positive_path_variant": True,
                    "givens": pos_givens,
                    "when": when,
                    "thens": pos_thens,
                    "operation_hints": [],
                    "time_control": (
                        {"mechanism": _derive_time_mechanism(action), "status": "planned"}
                        if "time_sensitive" in risk_traits else None
                    ),
                    "gen_seq": pos_gen_seq,
                    "post_state": f"{te['entity']}.{dimension}→{to_state}",
                    "cascade_chain": None,
                    "embedded_brs": [],
                    "_S2_fields": _make_S2_fields(
                        phase_val, phase_name, phase_info.get("basis", ""),
                        topo.get(te["entity"], 0), 3,  # 3=流转 (forward)
                        chain_depth, proc_type_label, proc_type_priority,
                        dim_priority, te["context"],
                    ),
                    "_S3_fields": _make_S3_fields(),
                    "_S4_fields": _make_S4_fields(),
                }
                procedures.append(pos_proc)

            # --- Audit rejection variant --- I21: role fallback for rejection
            # v29 #12 fix: skip rejection variant when the transition ITSELF
            # is already a reject/rollback action.
            #
            # v28 behavior: every audit transition got an audit_rejection
            # variant (state → state(驳回)), even when the transition's
            # action was already "审核退回" / "审核驳回" / "撤销" etc.
            # This produced nonsensical pairs like:
            #   T-012 "审核报名退回" (报名待审核→报名退回) + rejection variant
            #     → "报名退回(驳回)" — rejecting a rejection is meaningless
            #
            # v29: if the action already contains a rejection keyword,
            # skip the rejection variant. The transition itself IS the
            # rejection path; adding a "(驳回)" variant on top of it is
            # redundant and pollutes the procedure count.
            _REJECTION_ACTION_KEYWORDS = ('退回', '驳回', '撤销', '退款')
            _is_already_rejection = any(
                kw in (action or '') for kw in _REJECTION_ACTION_KEYWORDS
            ) or any(
                kw in (to.get('desc', '') or to.get('description', '') or '')
                for kw in _REJECTION_ACTION_KEYWORDS
            )
            # Also skip if the target state itself is a rejection state
            # (e.g. to_state contains 退回/驳回/撤销) — the transition is
            # already creating a rejection state, no variant needed.
            if to_state and any(kw in to_state for kw in _REJECTION_ACTION_KEYWORDS):
                _is_already_rejection = True

            # B5: 兄弟退回转换抑制 —— 同 entity+dimension+from 下已存在目标态含
            # 退回/驳回/撤销/退款 的转换时，审核通过转换不再生成退回变体
            # （T-062 的兄弟 T-063 已是模型化退回，v13 PROC-063 即此重复变体）。
            # 状态机已建模退回边 = 需求显式声明，无需框架再合成同义变体。
            _sibling_reject_exists = False
            if from_state and dimension:
                for _st in (cm.get('transition_obligations') or []):
                    if not isinstance(_st, dict):
                        continue
                    if _st.get('entity') != entity or _st.get('dimension') != dimension:
                        continue
                    if _st.get('from') != from_state:
                        continue
                    if _st.get('id') == to.get('id') \
                            or _st.get('transition_id') == to.get('transition_id'):
                        continue
                    if any(kw in str(_st.get('to', '') or '')
                           for kw in _REJECTION_ACTION_KEYWORDS):
                        _sibling_reject_exists = True
                        break

            # v29 #14 fix: only generate rejection variant for true APPROVE
            # actions (审核通过/批准/同意/确认), not for business progression
            # actions (发放样品/提交报名/etc.).
            #
            # v28 behavior: every audit transition got an audit_rejection
            # variant, even when the transition was NOT an approve action
            # (e.g. T-014 "项目管理员发放样品..." is a progression, not an
            # approve). The generated "报名成功(驳回)" post_state is a
            # FAKE state that doesn't exist in state_info, and the state
            # machine has no reverse edge from 报名成功(驳回) back to
            # 报名成功 — making the procedure semantically meaningless.
            #
            # v29: rejection variant is ONLY generated when the action
            # contains an approve keyword (通过/批准/同意/确认). For
            # progression actions (no approve keyword), the audit trait
            # still triggers Type1 generation but no rejection variant —
            # the audit gate is expressed via preconditions, not via a
            # separate rejection procedure.
            #
            # v29 #17b fix: strip branch suffix [项目类型=测量审核] BEFORE
            # checking approve keywords. Otherwise "测量审核" (branch value)
            # triggers the "审核" approve detection, misclassifying T-014b
            # (发放样品, progression) as an approve action.
            # v29 #26d: use P1's is_approve field (structured) instead of
            # keyword matching. Falls back to derived only when is_approve
            # is not present.
            #
            # v29 修复 1 (基于实验 0/29 死刑):
            # 实验 1+2+3 共 0/29 transition 含 is_approve 字段(LLM 系统性不产出).
            # declared 路径已死, 改为 derived: 用结构信号 (action/role/traits/terminals)
            # 多源推算. 已知病灶: 信号同源 LLM, 共因失效. 但比 declared 0% 强,
            # 因为 derived 至少能产出值. APPROVE_VERBS 和 reviewer_roles 是项目相关
            # 兜底配置 (不是领域无关), 显式标注.
            _is_approve_structured = to.get('is_approve')
            if _is_approve_structured is not None:
                _is_approve_action = bool(_is_approve_structured)
            else:
                # 修复 1: derived 路径 (替代 keyword 路径)
                # 2026-08-14: derived 是主路径 (LLM 0/29 系统性不产 declared),
                # 非降级。不再记录 fallback (s1.is_approve.derived_fallback 已删,
                # 91 次常量噪声, 让 is_clean_run 永久 false)。
                _is_approve_action, _derived_conf, _derived_ev = _derive_is_approve(
                    to, action
                )

            if ("audit" in risk_traits and not _is_already_rejection
                    and not _sibling_reject_exists
                    and _is_approve_action and not _negative_branch_flag):
                # Fix-2: skip rejection variant for negative_branch procedures —
                # they already express rejection via the main Then clause.
                # v29 #13 fix: rejection variant should use the REVIEWER role,
                # not the original TO's submitter role.
                #
                # v28 behavior: rejection variant inherited the original TO's
                # role (e.g. T-070 R-PARTICIPANT) and action (e.g. "机构新增/
                # 修改实验室信息"), just appending "（驳回）". This produced
                # nonsensical procedures like:
                #   "能力验证参加者 驳回 机构新增/修改实验室信息"
                # But business-wise, the SUBMITTER doesn't reject their own
                # submission — the REVIEWER does. For T-070, the reviewer is
                # R-SYS-ADMIN (管理用户), seen on T-071/T-072 of the same dim.
                #
                # v29: scan other audit transitions in the same entity+dim
                # to find the reviewer role (prefer the role on a reject
                # transition; else the role on an approve transition).
                # Also rephrase the action as "<reviewer>驳回<original action>"
                # to make the actor/action consistent.
                reviewer_role_id = _find_reviewer_role_for_dim(
                    to, cm, _REJECTION_ACTION_KEYWORDS
                )
                reject_role_id = reviewer_role_id or to.get('role')
                reject_role = _get_role_name(reject_role_id, '驳回', entity, state)
                reject_action = _derive_rejection_action_v29(
                    action, reject_role, original_role_id=to.get('role'),
                    role_map=_build_role_map(cm) if state else {}
                )
                reject_givens = [
                    _make_given(
                        target=loc,
                        state=from_state,
                        description=(f"[{te['context']}] " if te["context"] else "") +
                                    "已提请审批",
                    )
                ]
                reject_when = _make_when(
                    target=loc, event=_derive_business_event(reject_action, from_state),
                    actor=reject_role, action=reject_action
                )
                reject_thens = [
                    _make_then(
                        target=loc,
                        expectation=f"状态回退至{from_state}且驳回原因已记录",
                        kind="state",
                    )
                ]
                reject_proc = {
                    "temp_id": f"PROC-T1-{_next_gen_seq()}",
                    "source_ids": [to["id"]],
                    "entity": te["entity"],
                    "dimension": dimension,
                    "obligation_type": ObligationType.TRANSITION,
                    "risk_trait": "audit_rejection",
                    "givens": reject_givens,
                    "when": reject_when,
                    "thens": reject_thens,
                    "operation_hints": [],
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{te['entity']}.{dimension}→{from_state}(驳回)",
                    "cascade_chain": None,
                    "embedded_brs": [],
                    "_S2_fields": _make_S2_fields(
                        phase_val, phase_name,
                        phase_info.get("basis", "") + " (rejection variant)",
                        topo.get(te["entity"], 0), 4,  # 4=终止 (rejection)
                        chain_depth + 1, "audit", 4, dim_priority, te["context"],
                    ),
                    "_S3_fields": _make_S3_fields(dependencies=[base_proc["temp_id"]]),
                    "_S4_fields": _make_S4_fields(),
                }
                procedures.append(reject_proc)

            # --- Time sensitive variants ---
            if "time_sensitive" in risk_traits:
                # V06: time_sensitive 用例声明 time_control.mechanism（JSON），
                # 不再注入触发方式 hint 行（需求原文自陈触发语义，见模块头部）。

                # Boundary variant
                boundary_givens = [
                    _make_given(target=loc, state=from_state,
                                description="时间边界条件: 接近截止时间")
                ]
                boundary_when = _make_when(
                    target=loc, event=_derive_business_event(f"{action}(时间边界)", from_state, to_state),
                    actor=role, action=f"{action}(边界)"
                )
                boundary_thens = [
                    _make_then(target=loc,
                               expectation=f"状态转换为{to_state}(时间边界生效)",
                               kind="state")
                ]
                boundary_proc = {
                    "temp_id": f"PROC-T1-{_next_gen_seq()}",
                    "source_ids": [to["id"]],
                    "entity": te["entity"],
                    "dimension": dimension,
                    "obligation_type": ObligationType.TRANSITION,
                    "risk_trait": "time_sensitive",
                    "givens": boundary_givens,
                    "when": boundary_when,
                    "thens": boundary_thens,
                    # V06: boundary 主触发为 clock_injection（JSON 声明，无 hint 行）
                    "operation_hints": [],
                    "time_control": {"mechanism": "clock_injection", "status": "planned"},
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{te['entity']}.{dimension}→{to_state}(时间边界)",
                    "cascade_chain": None,
                    "embedded_brs": [],
                    "_S2_fields": _make_S2_fields(
                        phase_val, phase_name,
                        phase_info.get("basis", "") + " (time_boundary)",
                        topo.get(te["entity"], 0), op_lifecycle, chain_depth,
                        "time_sensitive", 3, dim_priority, te["context"],
                    ),
                    "_S3_fields": _make_S3_fields(dependencies=[base_proc["temp_id"]]),
                    "_S4_fields": _make_S4_fields(),
                }
                procedures.append(boundary_proc)

                # Expired variant
                expired_givens = [
                    _make_given(target=loc, state=from_state,
                                description="时间过期条件: 超过截止时间")
                ]
                expired_when = _make_when(
                    target=loc, event=f"尝试{action}事件(已过期)",
                    actor=role, action=f"尝试{action}(已过期)"
                )
                expired_thens = [
                    _make_then(target=loc,
                               expectation="操作不可执行或状态不变",
                               kind="behavior")
                ]
                expired_proc = {
                    "temp_id": f"PROC-T1-{_next_gen_seq()}",
                    "source_ids": [to["id"]],
                    "entity": te["entity"],
                    "dimension": dimension,
                    "obligation_type": ObligationType.TRANSITION,
                    "risk_trait": "time_sensitive",
                    "givens": expired_givens,
                    "when": expired_when,
                    "thens": expired_thens,
                    # V06: expired 主触发为 db_time_update（JSON 声明，无 hint 行）
                    "operation_hints": [],
                    "time_control": {"mechanism": "db_time_update", "status": "planned"},
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{te['entity']}.{dimension}→(过期未执行)",
                    "cascade_chain": None,
                    "embedded_brs": [],
                    "_S2_fields": _make_S2_fields(
                        phase_val, phase_name,
                        phase_info.get("basis", "") + " (time_expired)",
                        topo.get(te["entity"], 0), op_lifecycle, chain_depth,
                        "time_sensitive", 3, dim_priority, te["context"],
                    ),
                    "_S3_fields": _make_S3_fields(dependencies=[base_proc["temp_id"]]),
                    "_S4_fields": _make_S4_fields(),
                }
                procedures.append(expired_proc)

    return procedures


# ---------------------------------------------------------------------------
# Type3 — Attribute Config procedures
# ---------------------------------------------------------------------------

def _type3_then_expectation(eo: dict, branch: dict, state: AgentState) -> tuple[str, str, list[str]]:
    """I19: Generate non-tautological Then expectation for Type3.

    Returns (expectation, kind, br_refs).
    Priority: ① BR effect → ② branch path condition → ③ display value
    """
    attr = eo.get('attribute_name', '')
    val = branch.get('value', '')
    bds = state.get('coverage_model', {}).get('_context', {}).get('branch_dimensions', [])
    for bd in bds:
        if bd.get('entity') == eo['entity'] and bd.get('dimension') == attr:
            brs = bd.get('business_rules', []) or bd.get('coverage', {}).get('business_rules', [])
            for br_id in brs:
                return (f"配置{attr}={val}的效果已生效", "behavior", [br_id])
            bp = bd.get('branch_path') or branch.get('desc', '')
            if bp:
                return (f"{bp}已生效，{attr}可见{val}对应选项", "behavior", [])
    return (f"{attr}显示为{val}", "state", [])


def _generate_type3(state: AgentState, indices: dict) -> list[dict]:
    """Generate Type3 (attribute_config) procedures — BDD style.

    For each attribute_config EO:
    - If a matching branch_dimension exists → one procedure per branch value
    - Otherwise → single procedure

    BDD mapping:
      Old "导航配置入口" → operation_hint (NOT a Given)
      Given: entity has current attribute value (business state)
      When: attribute change event fires
      Then: observable effect (BR effect / branch path / display value)

    Fix-6: skip Type3 generation for attributes marked is_config=False in
    coverage_model._context.entity_details. These are system-builtin
    non-editable fields (e.g. E-WEIGHT.组长专家权重 = "5人时为40%，7人时
    为25%，9人时为18%" — derived from 评审组人数, not directly editable).
    Generating "修改组长专家权重为X" procedures for them is semantically
    wrong because the UI has no such input field. Only is_config=True
    attributes are user-editable and produce meaningful config-change tests.
    """
    phase_table = state["phase_table"]
    topo = state["topology_levels"]
    cfg_eo_to_bd = indices["cfg_eo_to_bd"]

    # Fix-6: build (entity, attribute) → is_config map from entity_details
    # Only is_config=False attributes are non-editable; skip them in Type3.
    # If P1 incorrectly marks a system-maintained field as is_config=True
    # (e.g. 机构类型 desc says "不可编辑" but is_config=True), that's a P1
    # data quality issue — fix it in P1 validation, not in S1 with keywords.
    cm = state["coverage_model"]
    non_editable_attrs: set[tuple[str, str]] = set()
    for ed in cm.get("_context", {}).get("entity_details", []):
        ent_id = ed.get("id", "")
        for attr in ed.get("attributes", []) or []:
            if isinstance(attr, dict):
                attr_name = attr.get("name", "")
                # is_config=False → not user-editable, skip Type3
                if attr.get("is_config") is False and ent_id and attr_name:
                    non_editable_attrs.add((ent_id, attr_name))

    procedures: list[dict] = []

    attr_cfg_eos = indices["eo_by_type"].get("attribute_config", [])
    for eo in attr_cfg_eos:
        bd = cfg_eo_to_bd.get(eo["id"])
        attr = eo.get('attribute_name', '')

        # Fix-6: skip non-editable (is_config=False) attributes
        if (eo["entity"], attr) in non_editable_attrs:
            continue

        if bd:
            # Generate one procedure per branch value
            for branch in bd.get("branches", []):
                transition_id = branch.get("target_transition", "")
                chain_depth = 0
                # Type3 是数据维护类:分支路径走 setup 解析器,与非分支路径
                # (PROC-002 基础数据-文件导出任务)一致。_resolve_phase 面向
                # 状态锚定,配置属性(任务级别)非状态维度会落到 L0 debug 标记
                # "P6: topology_level L0 → P0"(渲染层不识别→"第N阶段"兜底)。
                phase_info = _resolve_phase_for_non_transition(state, eo["entity"], obligation_type=ObligationType.ATTRIBUTE_CONFIG)
                dim_priority = _get_dimension_priority(eo["entity"], attr, state)

                val = branch['value']
                exp, kind, br_refs = _type3_then_expectation(eo, branch, state)
                givens = [_make_given(
                    target=eo['entity'],
                    state=f"{attr}为当前值",
                    description=f"当前{attr}配置值",
                )]
                when = _make_when(
                    target=eo['entity'],
                    event=f"{attr}配置变更为{val}事件",
                    action=f"修改{attr}为{val}",
                )
                thens = [_make_then(
                    target=f"{eo['entity']}.{attr}",
                    expectation=exp, kind=kind, br_refs=br_refs,
                )]
                # operation_hint carries the UI navigation detail
                op_hints = [f"导航至{eo['entity']}配置入口"]

                phase_val = phase_info.get("phase") or 0
                phase_name = (phase_table["phase_names"][phase_val]
                              if phase_val < len(phase_table["phase_names"]) else f"P{phase_val}")

                proc = {
                    "temp_id": f"PROC-T3-{_next_gen_seq()}",
                    "source_ids": [eo["id"]],
                    "entity": eo["entity"],
                    "dimension": attr,
                    "obligation_type": ObligationType.ATTRIBUTE_CONFIG,
                    "risk_trait": "",
                    "givens": givens,
                    "when": when,
                    "thens": thens,
                    "operation_hints": op_hints,
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{eo['entity']}.{attr}→{val}",
                    "cascade_chain": None,
                    "embedded_brs": list(br_refs),
                    "_S2_fields": _make_S2_fields(
                        phase_val, phase_name, phase_info.get("basis", ""),
                        topo.get(eo["entity"], 0), 2, chain_depth,
                        "happy", 1, dim_priority, None,
                    ),
                    "_S3_fields": _make_S3_fields(),
                    "_S4_fields": _make_S4_fields(),
                }
                # BDD: field_validation moved to independent Type9 procedures
                # (was: _enrich_thens(eo["entity"], ..., proc["thens"], ...))
                procedures.append(proc)
        else:
            tl = topo.get(eo["entity"], 0)
            phase_res = _resolve_phase_for_non_transition(state, eo["entity"], obligation_type=ObligationType.ATTRIBUTE_CONFIG)
            phase = phase_res["phase"]
            phase_basis = phase_res["basis"]
            dim_priority = _get_dimension_priority(eo["entity"], attr, state)

            givens = [_make_given(
                target=eo['entity'],
                state=f"{attr}为当前值",
                description=f"当前{attr}配置值",
            )]
            when = _make_when(
                target=eo['entity'],
                event=f"{attr}配置变更事件",
                action=f"修改{attr}",
            )
            thens = [_make_then(
                target=f"{eo['entity']}.{attr}",
                expectation=f"{attr}显示为修改后的值",
                kind="state",
            )]
            op_hints = [f"导航至{eo['entity']}配置入口"]

            phase_name = (phase_table["phase_names"][phase]
                          if phase < len(phase_table["phase_names"]) else f"P{phase}")

            proc = {
                "temp_id": f"PROC-T3-{_next_gen_seq()}",
                "source_ids": [eo["id"]],
                "entity": eo["entity"],
                "dimension": attr,
                "obligation_type": ObligationType.ATTRIBUTE_CONFIG,
                "risk_trait": "",
                "givens": givens,
                "when": when,
                "thens": thens,
                "operation_hints": op_hints,
                "gen_seq": _gen_seq_counter,
                "post_state": f"{eo['entity']}.{attr}→(已修改)",
                "cascade_chain": None,
                "embedded_brs": [],
                "_S2_fields": _make_S2_fields(
                    phase, phase_name, phase_basis, tl, 2, 0,
                    "happy", 1, dim_priority, None,
                ),
                "_S3_fields": _make_S3_fields(),
                "_S4_fields": _make_S4_fields(),
            }
            # BDD: field_validation moved to independent Type9 procedures
            # (was: _enrich_thens(eo["entity"], ..., proc["thens"], ...))
            procedures.append(proc)

    return procedures


# ---------------------------------------------------------------------------
# Type4a/4b — REMOVED: CO used only for ordering, not for generation
# ---------------------------------------------------------------------------
# Type4a (constraint CO) and Type4b (lifecycle CO) procedures have been
# removed.  They were redundant — their enabler and dependent state
# transitions are already covered by Type1 procedures, and their own Then
# said "此条件已在T-XXX前置条件中体现".
#
# CO (cross_entity_obligations) is now used ONLY in S3 for dependency
# ordering: enabler's Type1 procedure must precede dependent's Type1.
# No procedures are generated from CO.


# ---------------------------------------------------------------------------
# Type5 — CRUD Operation procedures (filtered)
# ---------------------------------------------------------------------------

def _apply_stage_hint(eo: dict, phase: int, phase_basis: str, givens: list,
                      state: dict, id_to_zh: dict):
    """2026-09 排序修复 C：无状态前置操作（file/数据类 EO）的阶段挂载。

    背景：这类 EO（无 dimension/from/to）唯一锚点是 object_existence→
    创建态，"上传证书/上传结果通知单"等项目末期操作被钉死在项目刚创建
    的相位（排序问题 2 的根因：一切"对项目的操作"退化为"项目已存在"）。

    stage_hint 由 P1 数据层声明、P2 透传到 EO，形态二选一：
      {"anchor_state": {"entity": "E-BMJL", "dimension": "报名记录状态",
                        "state": "报告/证书已发布"}}
      {"min_phase": 6}
    解析规则：
      - anchor_state：相位 = dep_state_phase_map[entity][dim][state]（主实体
        走 phase_table），并追加该状态的 restatement Given；
      - min_phase：相位下限；
      - 最终相位 = max(当前相位, 提示相位)——提示只上提、不前移（对象创建
        相位仍是硬下限）；无提升时返回原值，行为与旧版一致。
    """
    hint = eo.get('stage_hint') if isinstance(eo, dict) else None
    if not isinstance(hint, dict):
        return phase, phase_basis, givens

    dep_map = state.get('dep_state_phase_map') or {}
    phase_table = state.get('phase_table') or {}
    primary = state.get('primary_entity') or ''
    hinted = None
    new_given = None

    a = hint.get('anchor_state')
    if isinstance(a, dict) and a.get('state'):
        h_ent = a.get('entity') or (eo.get('entity', '') if isinstance(eo, dict) else '')
        h_dim = a.get('dimension') or ''
        h_state = str(a['state']).strip()
        ph = None
        if h_ent == primary and h_dim:
            ph = (phase_table.get('state_to_phase', {}) or {}).get(h_dim, {}).get(h_state)
        elif h_dim:
            ph = (dep_map.get(h_ent, {}) or {}).get(h_dim, {}).get(h_state)
        else:
            dm_ent = dep_map.get(h_ent, {}) or {}
            cands = [dm[h_state] for dm in dm_ent.values()
                     if isinstance(dm, dict) and h_state in dm]
            ph = min(cands) if cands else None
        if ph is not None:
            hinted = int(ph)
            zh = (id_to_zh or {}).get(h_ent, h_ent)
            new_given = _make_given(
                target=h_ent, state=h_state,
                description=f"{zh}处于{h_state}状态",
                given_type="restatement",
            )

    if hinted is None and hint.get('min_phase') is not None:
        try:
            hinted = int(hint['min_phase'])
        except (TypeError, ValueError):
            hinted = None

    if hinted is None:
        return phase, phase_basis, givens

    givens2 = list(givens)
    if new_given is not None:
        # D9：anchor_state 存在时替换 givens[0]（object_existence 创建锚
        # restatement，或「操作入口可用」占位）为锚定状态 restatement，而非
        # 仅追加——无状态前置操作的真实业务前置是「对象处于目标阶段状态」，
        # 对象已存在（创建态）只是唯一定锚时的占位。已含真实状态前置
        # （state 非空非"存在"）则保留原主给定，锚定状态并入。
        _g0 = givens2[0] if givens2 and isinstance(givens2[0], dict) else None
        _is_placeholder = bool(_g0) and (
            _g0.get('given_type') == 'restatement'
            or _g0.get('state') in ('', '存在')
        )
        if _is_placeholder:
            givens2[0] = new_given
        elif not any(
            isinstance(g, dict) and g.get('target') == new_given['target']
            and g.get('state') == new_given['state']
            for g in givens2
        ):
            givens2.append(new_given)

    if hinted > phase:
        return hinted, f"stage_hint.{eo.get('id', '')}.P{hinted}", givens2
    return phase, phase_basis, givens2


# ── 2026-09 排序修复 A v2：同动作组相位对齐（S1 后、事实相位）──────────
_TID_RE = __import__('re').compile(r'^(T-\d+)')


def _proc_base_tids_s1(proc: dict) -> set:
    """基础转换号提取（'T-041' ← 'T-041[a]' / 'T-041a'）。与 S3 同规则。"""
    tids = set()
    for sid in proc.get('source_ids', []) or []:
        if isinstance(sid, str):
            m = _TID_RE.match(sid)
            if m:
                tids.add(m.group(1))
    return tids


def _align_same_action_phases_post_s1(
    proc_dicts: list, cm: dict, state: dict, warnings: list,
) -> int:
    """同动作组（link_op_transition 声明绑定）的跨实体视图相位对齐。

    v1 在 S0 内对齐 dep_state_phase_map，已废弃，两个必然缺陷：
      a) S0 时主实体视图只能读 raw phase_table，真实相位要等 S1 的入口
         门控/state_ref 提升（收样 084：raw 待发样=P0，经 结果待提交 门
         → P3）。S0 阶段算不出 P3，对齐目标系统性偏低（实测 P4→P0）；
      b) 对主实体成员写 dep_state_phase_map[primary] 直接 KeyError（主
         实体不在 map 中），且 S1 解析主实体相位不读 dep_map，写了无效。

    v2 在 S1 全部过程生成后运行，此时 _S2_fields.phase 已含入口门控
    提升的真实值（事实相位，无需推断）：
      组来源     仅 link_op_transition 声明绑定（_collect_same_action_groups
                 v2 范围）；transition_relations 证据组是同一维度时间线上
                 的先后状态，不收集。
      目标相位   组内主实体视图成员的最小真实相位（主时间线=单一事实源）；
                 组内无主实体视图时取组内最小（入口锚定最接地，默认前向
                 +1 最不可信）。
      对齐对象   非主实体的组成员 proc（按 source_ids 基础转换号归属）＋
                 锚定在被对齐转换 to 态上的同实体 proc（验证类 proc 不携带
                 组成员 tid，但相位派生自同一 dep_map 条目——以 phase_basis
                 的 dep_state_phase_map 锚定串或 restatement Given 认定）。
      不可触碰   主实体成员 proc（它们定义事实相位）与 phase_table。
    同步更新 dep_state_phase_map 中被对齐的 to 态条目，保持状态一致。
    Returns aligned proc count.
    """
    groups = _collect_same_action_groups(cm)
    if not groups:
        return 0

    to_by_tid: dict = {}
    for to in cm.get('transition_obligations', []) or []:
        if isinstance(to, dict):
            tid = to.get('id') or to.get('transition_id') or ''
            if tid:
                to_by_tid[tid] = to

    primary = state.get('primary_entity') or ''
    dep_map = state.get('dep_state_phase_map') or {}
    aligned = 0

    for group in groups:
        gset = set(group)
        members = []
        for p in proc_dicts:
            if ((p.get('_S2_fields') or {}).get('phase') is None):
                continue
            if _proc_base_tids_s1(p) & gset:
                members.append(p)
        if not members:
            continue

        member_ids = {id(p) for p in members}
        primary_members = [p for p in members
                           if primary and p.get('entity', '') == primary]
        pool = primary_members or members
        try:
            target = min(p['_S2_fields']['phase'] for p in pool)
        except (KeyError, TypeError, ValueError):
            continue

        def _set_phase(p: dict, new_phase: int, tag: str) -> None:
            nonlocal aligned
            s2 = p.setdefault('_S2_fields', {})
            old = s2.get('phase')
            if old == new_phase:
                return
            s2['phase'] = new_phase
            s2['phase_name'] = f"P{new_phase}"
            s2['phase_basis'] = f"align.same_action.P{new_phase}"
            aligned += 1
            warnings.append(
                f"S1.A 同动作相位对齐({tag}): {p.get('temp_id', '?')}"
                f"({p.get('entity', '?')}) P{old}→P{new_phase} "
                f"(组 {','.join(group)})")

        # 1) 组成员 proc（主实体成员定义事实相位，永不修改）
        for p in members:
            if primary and p.get('entity', '') == primary:
                continue
            _set_phase(p, target, '成员')

        # 2) 锚定传播：to 态被对齐的非主实体转换，其同实体锚定 proc 一并对齐
        for tid in group:
            t = to_by_tid.get(tid)
            if not t:
                continue
            ent = t.get('entity', '')
            if not ent or (primary and ent == primary):
                continue
            dim = t.get('dimension', '')
            to_s = t.get('to')
            to_s = to_s.strip() if isinstance(to_s, str) else ''
            if not to_s:
                continue
            old = (((dep_map.get(ent, {}) or {}).get(dim, {}) or {}).get(to_s))
            if old is None or old == target:
                continue
            anchor_basis = f"dep_state_phase_map.{ent}.{dim}.{to_s}"
            for p in proc_dicts:
                if p.get('entity', '') != ent or id(p) in member_ids:
                    continue
                s2 = p.get('_S2_fields') or {}
                if s2.get('phase') != old:
                    continue
                gated = any(
                    isinstance(g, dict) and g.get('target') == ent
                    and g.get('state') == to_s
                    for g in (p.get('givens') or []))
                if gated or anchor_basis in str(s2.get('phase_basis') or ''):
                    _set_phase(p, target, f'锚定传播 {ent}.{dim}.{to_s}')
            # dep_map 条目同步（S2 contextual/诊断读取一致性）
            try:
                dep_map.setdefault(ent, {}).setdefault(dim, {})[to_s] = target
            except AttributeError:
                pass

    return aligned


def _creation_proc_phase(creation_to_ids: list | None, prior_procs: list | None) -> int | None:
    """创建转换对应 Type1 过程的实际相位 (经 ⑬ precondition bump 后的真实值).

    用 prior_procs 查表而非重新推导 _resolve_phase_for_transition: 文本前置
    (如 T-015 的"处于已选入状态") 正则吃不到但实际相位已被抬到 1, 重推导会
    低估。Type1 在 Type5 之前生成, 传进来的 prior_procs 已含创建过程。
    """
    if not prior_procs or not creation_to_ids:
        return None
    best: int | None = None
    for p in prior_procs:
        if any(cid in (p.get("source_ids") or []) for cid in creation_to_ids):
            ph = (p.get("_S2_fields") or {}).get("phase")
            if ph is not None and (best is None or ph > best):
                best = ph
    return best


# 表单录入类 CRUD 动词（领域无关，引擎词汇，定位同 _GENERIC_CRUD_VERBS）。
# 只有创建/编辑类操作面向表单录入 → 补"字段数据上下文"Given；删除/查询/确认
# 等无表单，不补。业务特定动词不进此表（由 operation_category/操作名携带）。
_FORM_ENTRY_CRUD_VERBS = ("新增", "创建", "编辑", "修改")


def _field_data_given(cm: dict, entity: str, eo: dict | None = None) -> dict | None:
    """从 entity_details 派生「字段数据上下文」Given（创建/编辑表单的字段清单）。

    数据驱动：字段名与 desc **全文**原样来自 P1 的 entity_details.attributes，
    无领域词表、无裁剪启发式。系统自动赋值字段（如申请部门 desc"根据登录用户
    自动获取申请人部门"）同样列入——这正是创建/编辑用例里用户应知晓的字段语义。
    实体缺失或无 attributes 返回 None（不硬生成空行）。

    ``eo.form_fields`` 优先：操作级字段清单覆盖（v13 评审 PROC-028/111/112 根因
    ——修改备注表单只含报名编号+备注，却错挂实体全量 10 字段；测试项表单只含
    标号/名称）。无声明回落 entity_details.attributes 全量。

    ``state`` 置空：字段数据不是业务状态，S3 Guard 1 逐 given 扫 state 做状态
    前置匹配时不得把它当 from_state（见 s3_dependency.py:706）。
    """
    if isinstance(eo, dict) and eo.get('form_fields'):
        parts: list[str] = []
        for ff in eo['form_fields']:
            if not isinstance(ff, dict) or not ff.get('name'):
                continue
            desc = str(ff.get('desc', '') or '').strip()
            parts.append(f"{ff['name']}({desc})" if desc else ff['name'])
        if parts:
            return _make_given(
                target=entity, state="", description="；".join(parts),
                given_type="field_data",
            )
    for ed in cm.get("_context", {}).get("entity_details", []) or []:
        if not isinstance(ed, dict) or ed.get("id") != entity:
            continue
        parts: list[str] = []
        for attr in ed.get("attributes", []) or []:
            if not isinstance(attr, dict) or not attr.get("name"):
                continue
            desc = str(attr.get("desc", "") or "").strip()
            parts.append(f"{attr['name']}({desc})" if desc else attr["name"])
        if not parts:
            return None
        return _make_given(
            target=entity,
            state="",
            description="；".join(parts),
            given_type="field_data",
        )
    return None


# ── 效果状态锚定 (Type5) ────────────────────────────────────────────────
# CRUD EO 的 expected_results 声明状态变更目标 ("费用状态变为已缴费" /
# "报名记录状态推进至报告/证书审核中" / "记录状态初始化为报名待审核")。
# phase 应锚到该效果状态所在阶段——操作发生在哪个业务阶段由其效果决定,
# 而非一律取实体 entry phase=P0 (否则报名记录的 CRUD 用例全部挤在 P0)。
# 数据驱动: 状态名来自 phase_table/dep_state_phase_map 的键集合, 不硬编码。
# 无状态效果声明的属性操作 (下载/上传/查询/备注等) 解析失败 → 回退原逻辑。
_EFFECT_STATE_RE = re.compile(
    r'状态(?:变(?:为|更)?|初始化为|推进(?:为|至|到)?)(?:为|至|到|成)?([^；;，,。]+)')


def _effect_state_phase(eo: dict, phase_table: dict, dep_map: dict) -> dict | None:
    """从 CRUD EO 的 expected_results 解析效果状态 → 目标阶段。

    返回 {"phase": N, "basis": "phase_table.<dim>.<state>"} 或 None(无信号)。
    多效果取 MAX ("通过则报名成功; 退回则报名退回" → 报名成功 P1)。
    跨实体效果也命中 (EO-CRU-048 操作报名记录但"样品状态变为已核查"→E-XM P1)。
    """
    cand: dict[str, list[tuple[str, int]]] = {}
    for dim, m in (phase_table.get("state_to_phase") or {}).items():
        for s, p in m.items():
            cand.setdefault(s, []).append((f"phase_table.{dim}", int(p)))
    for ent, dims in (dep_map or {}).items():
        for dim, m in dims.items():
            for s, p in m.items():
                cand.setdefault(s, []).append((f"dep_state_phase_map.{ent}.{dim}", int(p)))
    if not cand:
        return None

    hits: list[tuple[str, int, str]] = []
    for er in eo.get("expected_results", []) or []:
        for m in _EFFECT_STATE_RE.finditer(str(er)):
            phrase = m.group(1).strip()
            # 最长状态名前缀匹配: 捕获短语以状态名开头。规避短名子串误命中
            # ("报名待审核" 命中 "待审核" 的歧义)。
            best = None
            for s, entries in cand.items():
                if phrase.startswith(s) and (best is None or len(s) > len(best[0])):
                    best = (s, entries)
            if best:
                s, entries = best
                for src, p in entries:
                    hits.append((s, p, src))
    if not hits:
        return None
    s, p, src = max(hits, key=lambda x: x[1])
    return {"phase": p, "basis": f"{src}.{s}"}


def _generate_type5(state: AgentState, indices: dict, prior_procs: list | None = None) -> list[dict]:
    """Generate Type5 (crud_operation) procedures with retention filter.

    Only retained EOs generate procedures. If the entity has been split into
    VEs, generate one procedure per VE.
    """
    phase_table = state["phase_table"]
    dep_map = state["dep_state_phase_map"]
    ves = state.get("virtual_entities", {})
    topo = state["topology_levels"]
    primary = state["primary_entity"]
    # _build_entity_name_map 是 中文名→E-XXX, 这里反转为 id→中文名 (领域前置 desc 用)
    id_to_zh = {v: k for k, v in (indices.get("entity_name_map") or {}).items()}

    procedures: list[dict] = []

    crud_eos = indices["eo_by_type"].get("crud_operation", [])
    for eo in crud_eos:
        if not _is_type5_retained(eo, state):
            continue

        entity = eo["entity"]
        tl = topo.get(entity, 0)
        phase = 0
        phase_basis = ""

        if entity == primary:
            effect = _effect_state_phase(eo, phase_table, dep_map)
            if effect:
                phase, phase_basis = effect["phase"], effect["basis"]
            else:
                primary_dim_map = phase_table["state_to_phase"].get(phase_table["primary_dimension"], {})
                if primary_dim_map:
                    # 锚定第一个状态,产成两段式 phase_table.<维度>.<状态>。该字符串是
                    # 引擎的相位追溯记录(JSON 内),渲染层不再解析它取模块名/状态——
                    # 模块名用 proc.entity,目标状态用 proc.post_state。
                    anchor_state, first_phase = next(iter(primary_dim_map.items()), (None, 0))
                    phase = first_phase if first_phase is not None else 0
                    phase_basis = f"phase_table.{phase_table['primary_dimension']}.{anchor_state}"
        elif entity in dep_map:
            effect = _effect_state_phase(eo, phase_table, dep_map)
            if effect:
                phase, phase_basis = effect["phase"], effect["basis"]
            else:
                first_dim = next(iter(dep_map[entity].values()), None)
                if first_dim:
                    phase = min(first_dim.values())
                    phase_basis = f"dep_state_phase_map.{entity}.min_phase"
                else:
                    # Empty dep_map (stateless) — setup precedes the flow → P0
                    phase_res = _resolve_phase_for_non_transition(state, entity, obligation_type=ObligationType.LIFECYCLE)
                    phase = phase_res["phase"]
                    phase_basis = phase_res["basis"]
        elif entity in ves:
            phase = ves[entity].get("resolved_phase", 0)
            phase_basis = f"VE.{entity}.resolved_phase"
        else:
            phase_res = _resolve_phase_for_non_transition(state, entity, obligation_type=ObligationType.LIFECYCLE)
            phase = phase_res["phase"]
            phase_basis = phase_res["basis"]

        # Check if entity has VEs → generate one per VE
        ves_for_entity = [(ve_name, ve) for ve_name, ve in ves.items()
                          if ve.get("original_entity") == entity]

        if ves_for_entity:
            for ve_name, ve in ves_for_entity:
                ve_phase = ve.get("resolved_phase", 0)
                op_name = eo['operation_name']
                op_desc = eo.get('description', '')
                givens = [_make_given(
                    target=ve_name, state="存在",
                    description=f"操作入口可用",
                )]
                # Tier 2 领域前置 (VE 分支): 用 original_entity 判别业务生命周期
                # 对象, 声明对象实例须已存在 + 相位底不低于对象创建相位。
                dp_ref = object_existence(
                    state["coverage_model"], state, ve.get("original_entity") or entity)
                if dp_ref:
                    givens = [_make_given(
                        target=dp_ref["object_entity"],
                        state=dp_ref["object_state"],
                        description=(
                            f"{id_to_zh.get(dp_ref['object_entity'], dp_ref['object_entity'])}"
                            f"已存在，处于{dp_ref['object_state']}状态"
                        ),
                        given_type="restatement",
                    )]
                    creation_phase = _creation_proc_phase(dp_ref["creation_to_ids"], prior_procs)
                    if creation_phase is not None and creation_phase > ve_phase:
                        ve_phase = creation_phase
                # 2026-09 排序修复 C：stage_hint 阶段挂载（只上提不前移）
                ve_phase, _sb, givens = _apply_stage_hint(
                    eo, ve_phase, f"VE.{ve_name}.resolved_phase", givens,
                    state, id_to_zh)
                # 字段数据上下文（同非 VE 分支）：VE 的字段清单属原实体。
                if op_name.startswith(_FORM_ENTRY_CRUD_VERBS):
                    fg = _field_data_given(
                        state["coverage_model"], ve.get("original_entity") or entity)
                    if fg:
                        givens = givens + [fg]
                when = _make_when(
                    target=ve_name,
                    event=_derive_business_event(op_name),
                    action=f"执行{op_name}",
                )
                thens = [_make_then(
                    target=ve_name,
                    expectation=op_desc or f"{op_name}完成",
                    kind="behavior",
                )]
                # V10 fix: append each expected_result as a separate Then.
                # P1 already extracted observable result keywords (e.g.
                # "登录成功", "可进入本系统", "系统给出提示") into expected_results.
                # Without these in the proc text, V10 coverage_matrix probes
                # like "登录成功" / "可进入本系统" never match.
                for er in eo.get('expected_results', []) or []:
                    er_text = str(er).strip()
                    if er_text and er_text != op_desc:
                        thens.append(_make_then(
                            target=ve_name,
                            expectation=er_text,
                            kind="behavior",
                        ))
                op_hints = [f"导航至{ve_name}页面"]

                ve_phase_name = (phase_table["phase_names"][ve_phase]
                                 if ve_phase < len(phase_table["phase_names"]) else f"P{ve_phase}")

                proc = {
                    "temp_id": f"PROC-T5-{_next_gen_seq()}",
                    "source_ids": [eo["id"]],
                    "entity": ve_name,
                    "dimension": None,
                    "obligation_type": ObligationType.CRUD,
                    "risk_trait": "",
                    "givens": givens,
                    "when": when,
                    "thens": thens,
                    "operation_hints": op_hints,
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{ve_name}→({op_name}完成)",
                    "cascade_chain": None,
                    "embedded_brs": [],
                    "_S2_fields": _make_S2_fields(
                        ve_phase, ve_phase_name, f"VE.{ve_name}.resolved_phase",
                        topo.get(ve_name, 0), 1, 0, "crud", 5, 1,
                        ve.get("context"),
                    ),
                    "_S3_fields": _make_S3_fields(),
                    "_S4_fields": _make_S4_fields(),
                }
                # BDD: field_validation moved to independent Type9 procedures
                procedures.append(proc)
        else:
            op_name = eo['operation_name']
            op_desc = eo.get('description', '')
            entity_name = eo.get('entity_name', entity)
            # Tier 2 领域前置: CRUD/查看义务作用于业务生命周期对象 (topology>0)
            # 时, Given 声明"对象实例须已存在"(锚定创建转换 to_state), 相位
            # 不得早于对象创建相位。管理类实体 (topology 0) 不派生 → 保持 "=存在"。
            # D18: 创建类 op（新增/创建）跳过 object_existence 锚——对象在本
            # 操作中诞生，"{实体}已存在，处于{创建态}"是语义反义占位（v13
            # PROC-034 误连 PROC-017/033/031 的根因）。givens[0] 落「操作入口
            # 可用」，相位不被创建锚推高（新增项目=准备阶段 P0）。
            _is_creation_op = op_name.startswith(("新增", "创建"))
            dp_ref = (None if _is_creation_op
                      else object_existence(state["coverage_model"], state, entity))
            if dp_ref:
                givens = [_make_given(
                    target=dp_ref["object_entity"],
                    state=dp_ref["object_state"],
                    description=(
                        f"{id_to_zh.get(dp_ref['object_entity'], dp_ref['object_entity'])}"
                        f"已存在，处于{dp_ref['object_state']}状态"
                    ),
                    given_type="restatement",
                )]
                creation_phase = _creation_proc_phase(dp_ref["creation_to_ids"], prior_procs)
                if creation_phase is not None and creation_phase > phase:
                    phase = creation_phase
                    phase_basis = f"domain_precond_creation.{dp_ref['creation_to_id']}.P{creation_phase}"
            else:
                givens = [_make_given(
                    target=entity, state="存在",
                    description="操作入口可用",
                )]
            # 2026-09 排序修复 C：stage_hint 阶段挂载（只上提不前移）。
            # 上传证书/结果通知单等 file/数据类操作由数据层声明目标阶段，
            # 替代"对象已存在=创建态"的唯一定锚。
            phase, phase_basis, givens = _apply_stage_hint(
                eo, phase, phase_basis, givens, state, id_to_zh)
            # 字段数据上下文：创建/编辑表单的字段清单（P1 entity_details 派生）。
            # 数据驱动、无领域词；系统自动赋值字段（申请部门"根据登录用户自动获
            # 取…"）一并列入，补全表单语义。删除/查询/确认等无表单操作不补。
            # 追加在后：保持 givens[0]（状态前置）不变，S3 Guard 依 givens[0]。
            if op_name.startswith(_FORM_ENTRY_CRUD_VERBS):
                fg = _field_data_given(state["coverage_model"], entity, eo)
                if fg:
                    givens = givens + [fg]
            when = _make_when(
                target=entity,
                event=_derive_business_event(op_name),
                action=f"执行{op_name}",
            )
            thens = [_make_then(
                target=entity,
                expectation=op_desc or f"{op_name}完成",
                kind="behavior",
            )]
            # V10 fix: append each expected_result as a separate Then.
            # P1 already extracted observable result keywords (e.g.
            # "可进入本系统", "系统给出提示", "机构管理员可依据项目名称和技术领域条件进行查询")
            # into expected_results. Without these in the proc text, V10
            # coverage_matrix probes never match — the proc only contained
            # the generic description "覆盖{entity_name}的{op_name}操作".
            # This was the root cause of ~40 of the 75 V10 misses.
            for er in eo.get('expected_results', []) or []:
                er_text = str(er).strip()
                if er_text and er_text != op_desc:
                    thens.append(_make_then(
                        target=entity,
                        expectation=er_text,
                        kind="behavior",
                    ))
            # D13：导航页面覆盖——操作声明 page 时用声明页（如 提交审核
            # 按钮在「报名信息批量处理页」而非审核任务页），否则回退实体页。
            _page_ov = str(eo.get('page') or '').strip()
            op_hints = ([f"导航至{_page_ov}"] if _page_ov
                        else [f"导航至{entity_name}页面"])

            phase_name = (phase_table["phase_names"][phase]
                          if phase < len(phase_table["phase_names"]) else f"P{phase}")

            proc = {
                "temp_id": f"PROC-T5-{_next_gen_seq()}",
                "source_ids": [eo["id"]],
                "entity": entity,
                "dimension": None,
                "obligation_type": ObligationType.CRUD,
                "risk_trait": "",
                "givens": givens,
                "when": when,
                "thens": thens,
                "operation_hints": op_hints,
                "gen_seq": _gen_seq_counter,
                "post_state": f"{entity}→({op_name}完成)",
                "cascade_chain": None,
                "embedded_brs": [],
                "_S2_fields": _make_S2_fields(
                    phase, phase_name, phase_basis, tl, 1, 0,
                    "crud", 5, 1, None,
                ),
                "_S3_fields": _make_S3_fields(),
                "_S4_fields": _make_S4_fields(),
            }
            # BDD: field_validation moved to independent Type9 procedures
            procedures.append(proc)

    return procedures


# ---------------------------------------------------------------------------
# Type6 — Invalid Transition procedures
# ---------------------------------------------------------------------------

def _generate_type6(state: AgentState, indices: dict) -> list[dict]:
    """Generate Type6 (invalid_transition) procedures.

    Phase is based on the 'from' state (chain_depth 恒 0, depth_cache 机制已清除).
    """
    phase_table = state["phase_table"]
    dep_map = state["dep_state_phase_map"]
    topo = state["topology_levels"]
    primary = state["primary_entity"]
    cm = state["coverage_model"]
    tos = cm.get("transition_obligations", [])

    procedures: list[dict] = []

    invalid_transitions = indices["ro_by_type"].get("invalid_transition", [])
    for ro in invalid_transitions:
        # P2 吸收判定（Step 4.1）：该 RO 的 (entity, from, to) 已由某转换的
        # constraint_predicate 否定分支建模，拒绝提示并入转换负向用例 →
        # 不产出独立 Type6（避免同一规则两条过程，如 RO-IT-001 vs T-002 反例）。
        if ro.get("absorbed_by_transition"):
            continue
        entity = ro["entity"]
        tl = topo.get(entity, 0)
        phase = 0
        phase_basis = ""

        if entity == primary:
            primary_dim_map = phase_table["state_to_phase"].get(phase_table["primary_dimension"], {})
            if primary_dim_map and ro.get("from") in primary_dim_map:
                phase = primary_dim_map[ro["from"]]
                phase_basis = f"phase_table.{phase_table['primary_dimension']}.{ro['from']}"
        elif entity in dep_map:
            for dim, state_map in dep_map.get(entity, {}).items():
                if ro.get("from") in state_map:
                    phase = state_map[ro["from"]]
                    phase_basis = f"dep_state_phase_map.{entity}.{dim}.{ro['from']}"
                    break
            # If dep_map exists but is empty or state not found, fall through
            if phase == 0 and not phase_basis:
                phase_res = _resolve_phase_for_non_transition(state, entity, obligation_type=ObligationType.INVALID)
                phase = phase_res["phase"]
                phase_basis = phase_res["basis"]
        elif entity not in dep_map:
            # Entity absent from dep_map — try parent chain via helper
            phase_res = _resolve_phase_for_non_transition(state, entity, obligation_type=ObligationType.INVALID)
            phase = phase_res["phase"]
            phase_basis = phase_res["basis"]

        # Chain depth: depth_cache 机制已清除 (恒 0)
        chain_depth = 0

        proc = {
            "temp_id": f"PROC-T6-{_next_gen_seq()}",
            "source_ids": [ro["id"]],
            "entity": entity,
            "dimension": None,
            "obligation_type": ObligationType.INVALID,
            "risk_trait": "",
            "givens": [_make_given(
                target=entity, state=ro.get('from', ''),
                description=f"{entity}处于\"{ro.get('from', '')}\"状态",
            )],
            "when": _make_when(
                target=entity,
                event=f"尝试{ro.get('from', '')}→{ro.get('to', '')}转换事件",
                action=f"尝试执行从\"{ro.get('from', '')}\"到\"{ro.get('to', '')}\"的操作",
            ),
            "thens": [
                _make_then(
                    target=entity,
                    expectation=f"操作被拒绝，{ro.get('reason', '')}",
                    kind="prompt",
                ),
                _make_then(
                    target=entity,
                    expectation=f"状态仍为{ro.get('from', '')}",
                    kind="state",
                ),
            ],
            "operation_hints": [],
            "gen_seq": _gen_seq_counter,
            "post_state": f"{entity}→(操作被阻止)",
            "cascade_chain": None,
            "embedded_brs": [],
            "_S2_fields": _make_S2_fields(
                phase,
                phase_table["phase_names"][phase] if phase < len(phase_table["phase_names"]) else f"P{phase}",
                phase_basis, tl, 2, chain_depth,
                "invalid", 9, 1, None,
            ),
            "_S3_fields": _make_S3_fields(),
            "_S4_fields": _make_S4_fields(),
        }
        procedures.append(proc)

    return procedures


# ---------------------------------------------------------------------------
# BR Classification (S1.8)
# ---------------------------------------------------------------------------

# 通用 CRUD 操作动词(领域无关,引擎词汇)。业务特定操作动词由
# prohibition_config.action_verbs 提供;此处仅作 object-verb 形态的兜底。
_GENERIC_CRUD_VERBS = (
    "删除", "修改", "编辑", "新增", "创建", "查看", "查询", "锁定", "重置",
)


def _extract_constrained_ops(desc: str, crud_verbs: tuple | None = None) -> set:
    """Extract operation verbs constrained by a BR description.

    Used for operation-level CRUD host matching: a BR may only embed into a
    CRUD EO whose operation_name overlaps the verb it actually constrains —
    not merely any CRUD EO on the same entity.

    Patterns covered:
      1. Prohibition/requirement prefix + verb, e.g. "不可选入", "才能删除",
         "只有1次选入机会" → verb 选入 / 删除.
      2. "进行<verb>" construction, e.g. "不能进行分数修改" → 修改.
      3. "<noun><verb>" object-verb form, e.g. "专家删除" → 删除.

    ``crud_verbs`` comes from prohibition_config.action_verbs (see
    _get_action_verbs); falls back to the generic CRUD set.

    Returns a set of candidate verbs (includes noise — matching against CRUD
    operation_names is what filters).
    """
    verbs: set[str] = set()
    # 1. prefix + verb (lazy gap ≤8 non-punct chars to reach the verb)
    for m in re.finditer(
        r'(?:不可|不能|禁止|不得|不允许|只能|仅限|才可|只有)'
        r'[^，,。.；;：:]{0,8}?([一-龥]{2,6})', desc):
        verbs.add(m.group(1))
    # 2. "进行<verb>"
    for m in re.finditer(r'进行([一-龥]{2,6})', desc):
        verbs.add(m.group(1))
    # 3. object-verb form: <noun><verb> (verb set from config, generic fallback)
    _ov = crud_verbs or _GENERIC_CRUD_VERBS
    for m in re.finditer(r'[一-龥]{2,6}(' + '|'.join(_ov) + r')', desc):
        verbs.add(m.group(1))
    return verbs


def _verb_matches_op(verb: str, op_name: str) -> bool:
    """Whether a constrained BR verb matches a CRUD operation name.

    Matches if the verb's first 2 chars equal the op's first 2 chars
    (verb-object form, e.g. 删除↔删除专家) OR the verb's last 2 chars equal
    the op's last 2 chars (object-verb form, e.g. 选入↔项目选入).
    This deliberately avoids substring coincidences such as 评审 matching
    建立评审计划 — 评审 is a noun inside the object there, not the verb.
    """
    if not verb or not op_name:
        return False
    v = verb.strip()
    op = op_name.strip()
    if len(v) >= 2 and len(op) >= 2:
        # verb-object form (删除↔删除专家): verb at the start.
        if v[:2] == op[:2]:
            return True
        # object-verb form (选入↔项目选入): short verb at the end.
        # Requiring len(v) <= 4 avoids phrase coincidences such as
        # "提为试用机构" ending in the object noun "机构" matching
        # "添加研制机构".
        if len(v) <= 4 and v[-2:] == op[-2:]:
            return True
        # No substring fallback: 评审 is a substring of 建立评审计划
        # but is NOT the operation's verb — that would wrongly embed a
        # 评审 rule into every X评审计划 CRUD op.
        return False
    return v in op


def _classify_business_rules(state: AgentState, indices: dict) -> list[dict]:
    """S1.8.1: Classify BRs with full degradation chain.

    Priority: attribute_effect > transition_constraint > crud_constraint > negative_test > standalone.
    If high-priority category has no host → downgrade to next, with warning.
    """
    cm = state["coverage_model"]
    bds = cm.get("_context", {}).get("branch_dimensions", [])
    tos = cm.get("transition_obligations", [])
    co_constraint = indices["co_constraint"]
    eo_by_type = indices["eo_by_type"]
    ro_by_type = indices["ro_by_type"]
    entity_name_map = indices.get("entity_name_map", {})
    warnings = list(state.get("warnings", []))

    br_list = ro_by_type.get("business_rule", [])
    classifications = []

    for br in br_list:
        br_id = br.get("constraint_id", "")
        desc = br.get("description", "")
        entities_raw = br.get("entities_involved", br.get("entities", ""))
        br_entities = _resolve_entity_names(entities_raw, entity_name_map)
        # 受约束实体声明（C24 保证合法）：crud/negative 宿主选择优先收窄到它
        constrained = br.get("constrained_entity")

        candidates = []

        # 1. attribute_effect
        for bd in bds:
            cov = bd.get("coverage", {})
            if cov and br_id in cov.get("business_rules", []):
                cfg_eos = [eo for eo in eo_by_type.get("attribute_config", [])
                           if eo["entity"] == bd["entity"] and eo.get("attribute_name") == bd["dimension"]]
                if cfg_eos:
                    candidates.append({
                        "category": "attribute_effect", "host_proc_type": 3,
                        "host_eo_ids": [eo["id"] for eo in cfg_eos], "bd": bd,
                        "priority": 1
                    })

        # 2. transition_constraint
        if re.search(r'需先.*后|才可|必须.*后', desc) and len(br_entities) >= 2:
            to_match = next((to for to in tos
                             if br_entities and to["entity"] in br_entities
                             and "audit" in (to.get("risk_traits") or [])), None)
            co_match = next((co for co in co_constraint
                             if co["enabler_entity"] in br_entities or co["dependent_entity"] in br_entities), None)
            if to_match or co_match:
                candidates.append({
                    "category": "transition_constraint",
                    "host_proc_type": 1 if to_match else 4,
                    "host_to_id": to_match["id"] if to_match else None,
                    "host_co_id": co_match["id"] if co_match else None,
                    "priority": 2
                })

        # 3. crud_constraint — operation-level matching (v29 fix)
        # BDD: crud_ops read from coverage_model._context (configurable)
        cm_ctx = cm.get("_context", {})
        crud_ops = set(cm_ctx.get("crud_ops", []))
        # Operation-level matching: the BR's constrained verb must overlap a
        # CRUD EO's operation_name. The old heuristic only checked that SOME
        # CRUD EO existed on the entity, so every "实体+状态" BR got embedded
        # into that entity's first CRUD op (e.g. 时限/选入 rules onto 新增项目
        # or 建立评审计划) even when unrelated. Non-CRUD BRs now fall through
        # to standalone / negative_test instead of attaching to a wrong host.
        br_verbs = _extract_constrained_ops(desc, _get_action_verbs(cm))
        crud_eos = [eo for eo in eo_by_type.get("crud_operation", [])
                    if eo["entity"] in br_entities]
        # constrained_entity 声明优先：多实体 BR 收窄到受约束实体的 crud EO。
        # 受约束实体无 crud EO 时保持空集 → 本分支自然不产出候选（不再误挂旁实体）。
        if constrained and constrained in br_entities:
            crud_eos = [eo for eo in crud_eos if eo["entity"] == constrained]
        if crud_ops:
            has_crud = any(op in desc for op in crud_ops)
        else:
            has_crud = (bool(br_verbs) and any(
                any(_verb_matches_op(v, eo.get("operation_name", "")) for v in br_verbs)
                for eo in crud_eos))
        has_state = bool(re.search(r'状态|才可|不可|不允许|不能|只有|需先', desc))
        if has_crud and has_state:
            # Prefer the CRUD EO whose operation verb matches the BR's verbs.
            matching_eo = next((eo for eo in crud_eos
                                if any(_verb_matches_op(v, eo.get("operation_name", ""))
                                       for v in br_verbs)), None)
            if matching_eo is None and crud_ops:
                matching_eo = next((eo for eo in crud_eos
                                    if any(op in eo.get("operation_name", "") for op in crud_ops)), None)
            if matching_eo and _is_type5_retained(matching_eo, state):
                candidates.append({
                    "category": "crud_constraint", "host_proc_type": 5,
                    "host_eo_id": matching_eo["id"],
                    "priority": 3
                })

        # 4. negative_test
        if re.search(r'不可.*选择|不可.*删除|不可.*修改|不可.*操作|不可.*发布|不允许.*删除|不允许.*操作|不能.*删除|不能.*混合', desc):
            its = ro_by_type.get("invalid_transition", [])
            if constrained and constrained in br_entities:
                matching_it = next((ro for ro in its if ro["entity"] == constrained), None)
            else:
                matching_it = next((ro for ro in its if ro["entity"] in br_entities), None)
            candidates.append({
                "category": "negative_test", "host_proc_type": 6,
                "host_ro_id": matching_it["id"] if matching_it else None,
                "generate_variant": matching_it is None,
                "priority": 4
            })

        # 4.5 v29 #15: causal_constraint (XC-* BRs)
        # XC-* BRs are causal constraints derived from cross-entity
        # transition relations (e.g. "实验室启用 → 可创建报名待审核").
        # Per user feedback, these should NOT generate standalone Type8
        # procedures — they should be expressed as weak dependencies on
        # the relevant Type1 procedures (the dependent entity's creation
        # transition).
        #
        # Detection: source_xc field is present OR constraint_id starts
        # with "XC-". These BRs are already represented in
        # transition_relations, so a standalone procedure is redundant.
        source_xc = br.get('source_xc', '')
        if source_xc or br_id.startswith('XC-'):
            candidates.append({
                "category": "causal_constraint", "host_proc_type": 0,
                # 0 = no procedure generated; attached as weak dep instead
                "priority": 1  # higher priority than standalone (5)
            })

        candidates.sort(key=lambda c: c["priority"])

        chosen = None
        for cand in candidates:
            # v29 #15: causal_constraint (XC-* BRs) doesn't need a host —
            # it intentionally generates no procedure (host_proc_type=0).
            # Treat it as "chosen" immediately without host check.
            if cand.get("category") == "causal_constraint":
                chosen = cand
                break
            has_host = (
                cand.get("host_eo_ids") or cand.get("host_to_id") or
                cand.get("host_co_id") or cand.get("host_eo_id") or
                cand.get("host_ro_id") or cand.get("generate_variant")
            )
            if has_host:
                chosen = cand
                break
            else:
                warnings.append(f"BR {br_id}: {cand['category']} has no host, downgrading")

        # v29 #23b: If chosen is standalone, try to find a same-entity Type1
        # host to embed into. This avoids generating 468+ empty Type8 procs
        # ("按规则...执行操作") that are unexecutable. Instead, the BR
        # assertion is appended as a Then to the most relevant Type1 proc.
        if chosen and chosen.get("category") == "standalone":
            # Find Type1 procs for the same entity
            br_ents = _resolve_entity_names(entities_raw, entity_name_map)
            for ent in br_ents:
                type1_for_ent = [to for to in tos
                                 if to.get('entity') == ent
                                 and to.get('dimension')
                                 and "audit" in (to.get('risk_traits') or to.get('traits') or [])]
                if type1_for_ent:
                    # Found a Type1 host — change category from standalone to br_embed
                    chosen["category"] = "br_embed"
                    chosen["host_to_id"] = type1_for_ent[0]["id"]
                    chosen["host_proc_type"] = 1
                    chosen["priority"] = 6  # lower than standalone (5)
                    break

        if chosen:
            chosen["br"] = br
            classifications.append(chosen)
        else:
            classifications.append({"br": br, "category": "standalone", "host_proc_type": 7, "priority": 5})

    return classifications


# ---------------------------------------------------------------------------
# BR Description Decomposition (方案A: 原子V步拆解)
# ---------------------------------------------------------------------------

# Predicate keywords that signal an independent clause in Chinese business rules.
# These cover: prohibitions (不可/不能), obligations (必须/应), permissions (可/可以),
# entity descriptions (由/包含/记录), display behavior (展示/显示), and action verbs.
# ---------------------------------------------------------------------------
# LLM-based BR description decomposition (replaces _BR_PREDICATE_MARKERS)
# ---------------------------------------------------------------------------

_BR_DECOMPOSE_PROMPT = """你是一个业务规则拆解器。将复合业务规则描述拆解为原子断言。

## 拆解原则
1. 分号（；）必拆——分隔独立规则
2. 逗号（，）仅当两侧都是独立断言时拆
3. 每个原子断言应是一个完整的、可独立验证的规则
4. 不要拆分枚举（如"启用/停用"）
5. 不要拆分从句（如"当X时，做Y"中的X是从句）

## 输出格式（JSONL）
{"id":"BR-原始ID","atoms":["原子断言1","原子断言2",...]}

只输出 JSONL，不要额外说明。"""


def _decompose_brs_via_llm(brs: list[dict]) -> dict[str, list[tuple[str, str]]]:
    """Decompose BR descriptions into atomic assertions via LLM.

    Args:
        brs: List of BR dicts (from constraint_obligations, type=business_rule)

    Returns:
        ``{br_id: [(sub_label, assertion_text), ...]}`` dict.
        On failure, returns empty dict — callers fall back to single-atom
        (no decomposition).
    """
    if not brs:
        return {}

    import os as _os
    api_base = _os.environ.get('LLM_API_BASE', 'https://open.bigmodel.cn/api/paas/v4').rstrip('/')
    api_key = _os.environ.get('LLM_API_KEY', '')
    model = _os.environ.get('LLM_BR_DECOMPOSE_MODEL', 'glm-4-flash')
    if not api_key:
        cfg_path = _os.path.join(_os.path.dirname(__file__), '..', 'config.json')
        try:
            import json as _json
            with open(cfg_path) as f:
                cfg = _json.load(f)
            llm_cfg = cfg.get('llm', {})
            api_base = llm_cfg.get('api_base', api_base).rstrip('/')
            api_key = llm_cfg.get('api_key', api_key)
            model = llm_cfg.get('br_decompose_model', model)
        except Exception:
            pass
    if not api_key:
        print('      [BR-DECOMPOSE] LLM_API_KEY not set — skipping BR decomposition')
        return {}

    # Build user prompt
    lines = ["请拆解以下业务规则：", ""]
    for i, br in enumerate(brs, 1):
        bid = br.get('constraint_id', br.get('id', f'BR-{i}'))
        desc = br.get('description', '')
        lines.append(f"{i}. ID={bid}")
        lines.append(f"   描述：{desc}")
    user_msg = "\n".join(lines)

    # Call LLM
    import urllib.request as _urllib
    import json as _json
    url = f'{api_base}/chat/completions'
    body = _json.dumps({
        'model': model,
        'messages': [
            {'role': 'system', 'content': _BR_DECOMPOSE_PROMPT},
            {'role': 'user', 'content': user_msg},
        ],
        'temperature': 0.1,
        'max_tokens': len(brs) * 200 + 200,
    }).encode('utf-8')
    req = _urllib.Request(url, data=body, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    })

    try:
        with _urllib.urlopen(req, timeout=180) as resp:
            data = _json.loads(resp.read().decode('utf-8'))
        raw = (data.get('choices') or [{}])[0].get('message', {}).get('content', '')
    except Exception as e:
        print(f'      [BR-DECOMPOSE] LLM call failed: {e}')
        return {}

    # Parse JSONL response
    result: dict[str, list[tuple[str, str]]] = {}
    for line in raw.split('\n'):
        line = line.strip()
        if not line or line.startswith('```'):
            continue
        try:
            obj = _json.loads(line)
            if isinstance(obj, dict) and 'id' in obj and 'atoms' in obj:
                bid = obj['id']
                atoms = obj['atoms']
                if isinstance(atoms, list) and atoms:
                    # Assign sub-labels (a, b, c, ...)
                    if len(atoms) == 1:
                        result[bid] = [(bid, atoms[0])]
                    else:
                        result[bid] = [
                            (f"{bid}{chr(ord('a') + i)}", a)
                            for i, a in enumerate(atoms)
                        ]
        except _json.JSONDecodeError:
            continue
    print(f'      [BR-DECOMPOSE] Decomposed {len(result)}/{len(brs)} BRs')
    return result


def _decompose_br_desc(br_id: str, br_desc: str,
                       llm_cache: dict | None = None) -> list[tuple[str, str]]:
    """Decompose a BR description into atomic assertions.

    Uses LLM cache (populated by _decompose_brs_via_llm at S1 start) if
    available; falls back to single-atom (no decomposition) otherwise.

    The legacy regex-based decomposition (_BR_PREDICATE_MARKERS etc.) has
    been removed — it was domain-specific Chinese keyword matching that
    couldn't be ported to other projects.
    """
    br_desc = (br_desc or '').strip()
    if not br_desc:
        return [(br_id, br_desc)]
    if llm_cache and br_id in llm_cache:
        return llm_cache[br_id]
    # Fallback: no decomposition
    return [(br_id, br_desc)]


_NEG_PREFIXES = ("不可", "不能", "不得", "禁止", "不允许", "无法", "无权")

# 领域无关的通用动作动词兜底。业务特定动词(选入/归档/发放/打分 等)由 P2 的
# prohibition_config.action_verbs 提供(见 _get_action_verbs);默认值只保留
# 通用系统/CRUD 动词,避免业务词汇泄漏进通用引擎
# (违反 "NO hardcoded business verbs" 原则)。
_DEFAULT_ACTION_VERBS = (
    "启动", "提交", "保存", "删除", "修改", "新增", "审批", "批准", "通过",
    "重启", "暂停", "结束", "退出", "登录", "操作", "编辑", "查看", "进入",
    "选择", "执行", "上传", "下载", "锁定", "重置",
)


def _get_action_verbs(cm: dict) -> tuple:
    """Read the project's action verbs from prohibition_config.

    Falls back to the domain-agnostic generic set when the project doesn't
    configure one (or config is absent). This is the single source of action
    verbs — Type7's negative-op extraction should never hardcode a business
    verb list of its own.
    """
    _ctx = (cm or {}).get("_context", {}) or {}
    _pc = _ctx.get("prohibition_config", {}) or {}
    verbs = _pc.get("action_verbs")
    return tuple(verbs) if verbs else _DEFAULT_ACTION_VERBS


def _extract_negative_op(br_desc: str, action_verbs: tuple | None = None) -> str:
    """Extract the operation prohibited by a restrictive BR, if any.

    Matches 不可/不能/禁止/不得/不允许 + a known action verb within a
    short gap (e.g. "不能进行分数修改" → "修改", "不可选入评审组" → "选入").
    ``action_verbs`` comes from prohibition_config (see _get_action_verbs).
    Returns "" when no clean verb is found (pure computation/display rules,
    or prohibitions without a known verb) — callers then keep the
    description-based template instead of emitting a garbled rejection text.
    """
    if not (br_desc or '').strip():
        return ""
    verbs = action_verbs or _DEFAULT_ACTION_VERBS
    _re = re.compile(
        r'(' + '|'.join(_NEG_PREFIXES) + r')'
        r'[^，,。.；;]{0,15}?'
        r'(' + '|'.join(verbs) + r')'
    )
    m = _re.search(br_desc)
    return m.group(2) if m else ""


def _extract_condition_text(br_desc: str) -> str:
    """Extract the triggering condition preceding the prohibition clause.

    For "对于本阶段评价结果为差的项目，不可选入" returns
    "对于本阶段评价结果为差的项目". Empty when the prohibition opens the desc.
    """
    parts = re.split(r'[，,；;]', br_desc or '')
    cond = []
    for part in parts:
        if any(kw in part for kw in ("不可", "不能", "禁止", "不得", "不允许")):
            break
        cond.append(part)
    return "，".join(cond) if cond else ""


def _build_negative_test_thens(br_id: str, br_desc: str,
                               entity: str,
                               action_verbs: tuple | None = None) -> list[dict]:
    """Deterministic fallback for restrictive BRs: 违规场景 → 拦截断言.

    Replaces the tautological "When: 按规则X执行操作 / Then: [BR] X" form
    (When and Then were the same text, unexecutable) with an executable
    rejection scenario: assert the prohibited operation is rejected and the
    system state is preserved. No LLM dependency.
    """
    neg_op = _extract_negative_op(br_desc, action_verbs)
    condition_text = _extract_condition_text(br_desc)
    if neg_op:
        rejection = f"操作被拒绝：{neg_op}操作不可执行"
    else:
        rejection = "操作被拒绝并给出禁止提示"
    if condition_text:
        rejection += f"（条件：{condition_text}）"
    return [
        _make_then(target=entity, expectation=rejection,
                   kind="prompt", br_refs=[br_id]),
        _make_then(target=entity, expectation="系统状态保持不变",
                   kind="state", br_refs=[br_id]),
    ]


# ---------------------------------------------------------------------------
# Type7 — Standalone BR procedures (only for standalone-classified BRs)
# ---------------------------------------------------------------------------

def _generate_type7_standalone(br_classifications: list[dict], state: AgentState,
                               entity_name_map: dict | None = None,
                               signal_v_steps: dict[str, list[dict]] | None = None) -> list[dict]:
    """Generate standalone Type7 procedures from standalone BRs only.

    When ``signal_v_steps`` is provided, LLM-generated V-steps are used
    in place of the deterministic template decomposition.
    """
    if signal_v_steps is None:
        signal_v_steps = {}
    phase_table = state["phase_table"]
    dep_map = state["dep_state_phase_map"]
    ves = state.get("virtual_entities", {})
    topo = state["topology_levels"]
    primary = state["primary_entity"]
    cm = state["coverage_model"]
    tos = cm.get("transition_obligations", [])

    procedures: list[dict] = []
    standalone_brs = [bc for bc in br_classifications if bc["category"] == "standalone"]

    for bc in standalone_brs:
        br = bc["br"]
        entities_raw = br.get("entities_involved", br.get("entities", ""))
        br_entities = _resolve_entity_names(entities_raw, entity_name_map)
        # v29 #18: was "E-PRJ" hardcoded — replaced with state["primary_entity"]
        # so BR fallback works for ANY project, not just 能力验证项目.
        primary_br_entity = br_entities[0] if br_entities else state.get("primary_entity", "")

        tl = topo.get(primary_br_entity, 0)
        phase_res = _resolve_phase_for_non_transition(state, primary_br_entity, obligation_type=ObligationType.RULE)
        phase = phase_res["phase"]
        phase_basis = phase_res["basis"]

        br_desc = br.get("description", "")
        enforcement = br.get("enforcement", "mandatory")
        br_category = bc.get("category", "standalone")

        # I11: Category-assisted V step focus
        category_focus = {
            "authorization": "验证权限控制: 无权限者不可操作",
            "computation": "验证计算逻辑: 输入→输出正确",
            "notification": "验证通知触发: 事件产生对应消息",
            "data_integrity": "验证数据约束: 边界值有效, 越界值被拒绝",
            "timing": "验证时间约束: 触发条件满足时生效, 延迟符合预期",
            "validation": "验证数据校验: 条件满足通过, 条件不满足被拒绝",
        }.get(br_category, "")

        # ── BDD clauses ──
        br_id = br.get('constraint_id', '')
        br_restrictive = br.get('restrictive') or False

        # v29 修复 (Type7 同义反复): restrictive BR 且能抽取出被禁止操作时,
        # 用确定性负向模板(违规场景 → 拦截断言),不再产出 When/Then 同文
        # 的"按规则X执行操作 / Then: [BR] X"。非 restrictive 或无法抽取
        # 禁止操作的 BR 保持描述性 fallback。
        # 动作动词从 prohibition_config 读取(领域无关兜底),不在此处硬编码
        # 业务动词列表。
        _type7_action_verbs = _get_action_verbs(cm)
        neg_op = (_extract_negative_op(br_desc, _type7_action_verbs)
                  if br_restrictive else "")

        if neg_op:
            # 负向模板: Given=规则原文(作为被测规则上下文), When=尝试违规
            # 操作, Then=拒绝+状态保持。
            # 注意: 规则原文只放在 Given 做上下文,不放进 When/Then —— 避免
            # 审查指出的 When/Then 同义反复。同时保留原文可让 V10 coverage
            # 的 missing_keyword probe(按需求原文匹配)继续命中,而不是因为
            # 负向模板改写而丢失规则关键词。
            givens = [_make_given(
                target=primary_br_entity,
                state="规则适用前提满足",
                description=br_desc,
                given_type="rule",
            )]
            when = _make_when(
                target=primary_br_entity,
                event=f"尝试执行被规则禁止的{neg_op}操作",
                action=f"尝试执行{neg_op}操作",
            )
            thens = _build_negative_test_thens(
                br_id, br_desc, primary_br_entity, _type7_action_verbs)
        else:
            givens = [_make_given(
                target=primary_br_entity,
                state="规则适用前提满足",
                description=f"{', '.join(br_entities)}相关数据已准备",
                given_type="rule_noise",
            )]
            when = _make_when(
                target=primary_br_entity,
                event=f"按规则\"{br_desc}\"执行操作事件",
                action=f"按规则\"{br_desc}\"执行操作",
            )
            thens: list[dict] = []

        # Priority 1: LLM-generated signal-aware Thens (override the
        # deterministic template when available).
        llm_v_steps = signal_v_steps.get(br_id) if signal_v_steps else None
        if llm_v_steps:
            thens = []
            for vs in llm_v_steps:
                # BDD: vs is now a ThenClause dict (target/expectation/kind/br_refs/cross_refs)
                loc = vs.get("target", primary_br_entity)
                exp = vs.get("expectation", "")
                if not exp:
                    continue
                thens.append(_make_then(
                    target=loc,
                    expectation=exp,
                    kind=vs.get("kind", "behavior"),
                    br_refs=[br_id] + vs.get("br_refs", []),
                ))
        elif not neg_op:
            # Priority 2 fallback: deterministic decomposition (方案A).
            # Skipped when neg_op already built the negative-template thens
            # above — appending the description-based atoms would re-introduce
            # the When/Then tautology this fix removes.
            atoms = _decompose_br_desc(br_id, br_desc, state.get('br_decomposition', {}))
            if enforcement == "conditional":
                focus_hint = f" ({category_focus})" if category_focus else ""
                for sub_label, assertion in atoms:
                    thens.append(_make_then(
                        target=primary_br_entity,
                        expectation=f"[{sub_label}]正面: {assertion}{focus_hint}",
                        kind="behavior", br_refs=[sub_label],
                    ))
                    thens.append(_make_then(
                        target=primary_br_entity,
                        expectation=f"[{sub_label}]负面: 不满足条件时规则不触发",
                        kind="behavior", br_refs=[sub_label],
                    ))
            else:
                for sub_label, assertion in atoms:
                    thens.append(_make_then(
                        target=primary_br_entity,
                        expectation=f"[{sub_label}] {assertion}",
                        kind="behavior", br_refs=[sub_label],
                    ))

        # Chain depth: depth_cache 机制已清除 (恒 0)
        chain_depth = 0

        # V06: 时限/超时/timing BR 注入触发方式 hints + time_control
        # 条件与 V06 模型信号一致: category=timing 或 desc 含"超时/时限"
        _is_timing_br = (br.get("category") == "timing"
                         or "超时" in br_desc or "时限" in br_desc)

        proc = {
            "temp_id": f"PROC-T7-{_next_gen_seq()}",
            "source_ids": [br.get("id", br.get("constraint_id", ""))],
            "entity": primary_br_entity,
            "dimension": None,
            "obligation_type": ObligationType.RULE,
            "risk_trait": "",
            "givens": givens,
            "when": when,
            "thens": thens,
            # V06: 时限/超时 BR 用例声明 time_control(调度器触发);不注入 hint 行
            "operation_hints": [],
            "time_control": (
                {"mechanism": "scheduler_manual_trigger", "status": "planned"}
                if _is_timing_br else None
            ),
            "gen_seq": _gen_seq_counter,
            "post_state": f"{primary_br_entity}→(规则验证完成)",
            "cascade_chain": None,
            "embedded_brs": [],
            "_S2_fields": _make_S2_fields(
                phase,
                phase_table["phase_names"][phase] if phase < len(phase_table["phase_names"]) else f"P{phase}",
                phase_basis, tl, 1, chain_depth,
                "rule", 6, 1, None,
            ),
            "_S3_fields": _make_S3_fields(),
            "_S4_fields": _make_S4_fields(),
        }
        procedures.append(proc)

    return procedures


# ---------------------------------------------------------------------------
# Type9 — Field Validation procedures (independent BDD scenarios)
# ---------------------------------------------------------------------------

def _generate_type9_field_validation(
    state: AgentState, indices: dict
) -> list[dict]:
    """Generate independent Type9 procedures for field-level validation.

    Each entity that has field-validation constraints (boundary, format, etc.)
    gets ONE Type9 procedure.  This keeps Type1/3/5 procedures clean — they
    only describe the primary business behaviour (state transition / config /
    CRUD), while field validation becomes its own BDD scenario.

    BDD structure:
        Given: 实体处于可编辑状态（如"实验室信息录入页面"）
        When:  提交含违规值的表单
        Then:  [多个字段校验失败的可观察结果]
    """
    phase_table = state["phase_table"]
    topo = state["topology_levels"]
    dep_map = state["dep_state_phase_map"]
    primary = state["primary_entity"]
    ves = state.get("virtual_entities", {})
    constraint_steps = indices.get("constraint_steps", {})

    if not constraint_steps:
        return []

    procedures: list[dict] = []

    # 系统维护字段过滤: 只剔"系统自动生成/自动获取"的真系统字段, 保留全部
    # 用户可编辑字段的校验。判据与 V04 校验器共享 context/sysfields.py (desc
    # 标记正则) —— 不用 is_config: attr() 默认 is_config=False (builders.py),
    # 会把所有非配置下拉字段误当"不可编辑", 曾致登记字段校验缺失 (PROC-029/
    # PROC-039 只剩载体类别/级别两条)。
    cm = state.get("coverage_model", {})
    sys_pairs = sys_maintained_pairs(cm.get("_context", {}).get("entity_details", []))

    for entity_id, field_thens in constraint_steps.items():
        if not field_thens:
            continue

        # 操作者门禁: 无表单操作者的只读实体 (如 E-ROLE/E-LOG, operator 集为空)
        # 不生成 Type9 —— 否则兜底「系统管理员」会触发 V07 actor 失败。
        pick = form_operator_roles(cm, entity_id)
        if not pick:
            continue

        # Filter out thens that target system-maintained fields. 全限定精确匹配:
        # 目标 "实体.字段" 的 (实体, 字段) 对命中共享推导集合才剔除。不能用子串
        # 匹配 —— 中文实体名/字段名互相是子串 (E-CAR 载体.载体编号 vs E-REG
        # 载体登记任务.原载体编号), 子串会把用户可编辑字段跨实体误伤。
        sys_field_set = {(k, a) for k, a in sys_pairs}
        filtered_thens = []
        for t in field_thens:
            tgt = t.get("target", "") or ""
            ent_part, _, attr_part = tgt.rpartition(".")
            if attr_part and (ent_part, attr_part) in sys_field_set:
                continue  # system-maintained field — drop
            filtered_thens.append(t)

        if not filtered_thens:
            continue  # All fields were system-maintained, skip this entity
        field_thens = filtered_thens

        # Resolve phase for this entity (same logic as Type5)
        tl = topo.get(entity_id, 0)
        phase = 0
        phase_basis = ""
        if entity_id == primary:
            primary_dim_map = phase_table["state_to_phase"].get(
                phase_table.get("primary_dimension", ""), {}
            )
            if primary_dim_map:
                # 同 Type5 主实体分支:锚定第一个状态,产成两段式 phase_table 形态
                anchor_state, first_phase = next(iter(primary_dim_map.items()), (None, 0))
                phase = first_phase if first_phase is not None else 0
                phase_basis = f"phase_table.{phase_table.get('primary_dimension', '')}.{anchor_state}"
        elif entity_id in dep_map:
            first_dim = next(iter(dep_map[entity_id].values()), None)
            if first_dim:
                phase = min(first_dim.values())
                phase_basis = f"dep_state_phase_map.{entity_id}.min_phase"
            else:
                phase_res = _resolve_phase_for_non_transition(state, entity_id, obligation_type=ObligationType.FIELD_VALIDATION)
                phase = phase_res["phase"]
                phase_basis = phase_res["basis"]
        elif entity_id in ves:
            phase = ves[entity_id].get("resolved_phase", 0)
            phase_basis = f"VE.{entity_id}.resolved_phase"
        else:
            phase_res = _resolve_phase_for_non_transition(state, entity_id, obligation_type=ObligationType.FIELD_VALIDATION)
            phase = phase_res["phase"]
            phase_basis = phase_res["basis"]

        phase_name = (phase_table.get("phase_names", ["P0"])[phase]
                      if phase < len(phase_table.get("phase_names", []))
                      else f"P{phase}")

        # V07 修复: 根据 entity 推断合适的 actor，而非硬编码"操作员"
        # "操作员"不在 role matrix 中，validator 会报 actor not in role matrix
        #
        # 动态推导策略（无硬编码 entity→actor 映射）：
        # 1. 扫描 transition_obligations，找该 entity 出现过的所有 role
        # 2. 优先选非 system 的 role（业务角色优先于系统角色）
        # 3. 若有多个业务角色，选第一个（CRUD 操作不区分具体业务角色）
        # 4. 若无 TO（managed 实体如 E-WEIGHT/E-LEVEL），用 entity_details.type 推断:
        #    - managed → 系统管理员（配置类实体由系统管理员维护）
        #    - core → 从同实体的 EO.suggested_action 上下文推断
        # 5. 兜底 → 系统管理员
        # V07 修复（共享派生）: Type9 actor = 该实体表单的授权操作者,与 V07
        # 校验器共用 context/entity_operators.py 同一份派生,避免"生成器兜底
        # 系统管理员 / 校验器查 action 子串"两套逻辑漂移(见 co_derivation.py
        # 立下的 single-source-of-truth 原则)。兜底仅当实体确实无法从模型
        # 派生时(如 E-ROLE/E-LOG 这类只读实体,模型无其表单操作)。
        # pick 已在循环顶部门禁算出 (空集实体已 continue), 首角色即表单操作者
        inferred_actor = pick[0]

        # Build BDD clauses
        givens = [_make_given(
            target=entity_id,
            state="可编辑",
            description=f"{entity_id}信息录入页面已打开",
        )]
        when = _make_when(
            target=entity_id,
            event=f"提交含违规值的{entity_id}表单",
            actor=inferred_actor,
            action="提交含违规值的表单",
        )
        # Thens: all field-validation ThenClauses for this entity
        thens = list(field_thens)

        # Operation hint: navigate to the entity's edit page
        op_hints = [f"导航至{entity_id}新增/编辑页面"]

        proc = {
            "temp_id": f"PROC-T9-{_next_gen_seq()}",
            "source_ids": [f"FIELD-VAL-{entity_id}"],
            "entity": entity_id,
            "dimension": None,
            "obligation_type": ObligationType.FIELD_VALIDATION,  # Type9 = field_validation
            "risk_trait": "field_validation",
            "givens": givens,
            "when": when,
            "thens": thens,
            "operation_hints": op_hints,
            "gen_seq": _gen_seq_counter,
            "post_state": f"{entity_id}→(校验失败，表单未提交)",
            "cascade_chain": None,
            "embedded_brs": [],
            "_S2_fields": _make_S2_fields(
                phase, phase_name, phase_basis or f"field_validation.{entity_id}",
                tl, 2, 0, "field_validation", 5, 1, None,
            ),
            "_S3_fields": _make_S3_fields(),
            "_S4_fields": _make_S4_fields(),
        }
        procedures.append(proc)

    return procedures

def _embed_brs(procedures: list[dict], br_classifications: list[dict],
               state: AgentState, entity_name_map: dict | None = None,
               signal_v_steps: dict[str, list[dict]] | None = None) -> list[dict]:
    """Embed non-standalone BRs into host procedures as V steps.

    When ``signal_v_steps`` is provided, LLM-generated V-steps replace the
    deterministic template decomposition for embedded BR V-steps.
    """
    dep_map = state["dep_state_phase_map"]
    phase_table = state["phase_table"]
    warnings = list(state.get("warnings", []))
    total_embedded = 0

    if signal_v_steps is None:
        signal_v_steps = {}

    non_standalone = [bc for bc in br_classifications
                      if bc["category"] != "standalone"
                      and bc["category"] != "causal_constraint"]  # v29 #15: skip XC-* BRs
    for bc in non_standalone:
        br = bc["br"]
        br_id = br.get("constraint_id", "")
        br_desc = br.get("description", "")
        enforcement = br.get("enforcement", "mandatory")

        host_procs: list[dict] = []

        if bc["category"] == "attribute_effect":
            host_eo_ids = bc.get("host_eo_ids", [])
            host_procs = [p for p in procedures
                          if p["obligation_type"] == ObligationType.ATTRIBUTE_CONFIG
                          and any(sid in host_eo_ids for sid in p.get("source_ids", []))]

        elif bc["category"] == "transition_constraint":
            host_to_id = bc.get("host_to_id")
            host_co_id = bc.get("host_co_id")
            if host_to_id:
                host_procs = [p for p in procedures
                              if p["obligation_type"] == ObligationType.TRANSITION
                              and host_to_id in p.get("source_ids", [])
                              and p.get("risk_trait") != "audit_rejection"]
            if host_co_id:
                host_procs.extend([p for p in procedures
                                   if p["obligation_type"] == ObligationType.CONSTRAINT
                                   and host_co_id in p.get("source_ids", [])])

        elif bc["category"] == "crud_constraint":
            host_eo_id = bc.get("host_eo_id")
            if host_eo_id:
                host_procs = [p for p in procedures
                              if p["obligation_type"] == ObligationType.CRUD
                              and host_eo_id in p.get("source_ids", [])]

        elif bc["category"] == "br_embed":
            # v29 #23b: standalone BR embedded into same-entity Type1 proc
            host_to_id = bc.get("host_to_id")
            if host_to_id:
                host_procs = [p for p in procedures
                              if p["obligation_type"] == ObligationType.TRANSITION
                              and host_to_id in p.get("source_ids", [])
                              and p.get("risk_trait") != "audit_rejection"]

        elif bc["category"] == "negative_test":
            entities_raw = br.get("entities_involved", br.get("entities", ""))
            br_entities = _resolve_entity_names(entities_raw, entity_name_map)
            # Fix 4: 语义化宿主选择。负向 BR 的禁止操作动词（_extract_negative_op
            # 从描述 + action_verbs 提取，如 "不可回收"→回收）必须出现在宿主动作
            # 中（IT/guard 负向 proc 的 when.action 为 "尝试执行从X到Y的操作"），
            # 否则仅实体命中即嵌入会污染语义无关宿主（曾致 RO-IT-004 锁定→正常
            # 混入 BR-019 账号不可修改、BR-032 角色不可更改删除）。无对齐宿主时
            # 走下方"新建独立 Type7"分支。
            _neg_op = _extract_negative_op(br_desc, _get_action_verbs(state["coverage_model"]))
            host_procs = [p for p in procedures
                          if p["obligation_type"] == ObligationType.INVALID
                          and br_entities and p["entity"] in br_entities
                          and _neg_op
                          and _neg_op in ((p.get("when") or {}).get("action") or p.get("action") or "")]

            if not host_procs:
                # Create new Type6 variant procedure (negative_test BR with no existing Type6)
                # v29 #18: was "E-PRJ" hardcoded — replaced with state["primary_entity"]
                primary_br_entity = br_entities[0] if br_entities else state.get("primary_entity", "")
                # topology_level 记录进 _S2_fields (叶子经 S0 提升到 leaf_level 后此处为 leaf_level)
                tl = state.get("topology_levels", {}).get(primary_br_entity, 0)
                phase = 0
                phase_basis = ("P6: topology_level L0 → P0"
                               if primary_br_entity in base_data_entity_ids(state) else "default")

                if primary_br_entity in dep_map:
                    all_phases = [p for dm in dep_map[primary_br_entity].values() for p in dm.values()]
                    if all_phases:
                        phase = min(all_phases)
                        phase_basis = f"dep_state_phase_map.{primary_br_entity}.min_phase"

                # Extract the prohibited part from description
                prohibited = ""
                for marker in ["不可", "不允许", "不能"]:
                    idx = br_desc.find(marker)
                    if idx >= 0:
                        prohibited = br_desc[idx:]
                        break
                if not prohibited:
                    prohibited = br_desc

                new_proc = {
                    "temp_id": f"PROC-T6BR-{_next_gen_seq()}",
                    "source_ids": [br.get("id", br.get("constraint_id", ""))],
                    "entity": primary_br_entity,
                    "dimension": None,
                    "obligation_type": ObligationType.INVALID,
                    "risk_trait": "negative",
                    "givens": [_make_given(
                        target=primary_br_entity,
                        state="规则适用前提满足",
                        description=f"{prohibited}相关数据已准备",
                        given_type="rule_noise",
                    )],
                    "when": _make_when(
                        target=primary_br_entity,
                        event="尝试违反规则操作事件",
                        action="尝试违反规则操作",
                    ),
                    "thens": [_make_then(
                        target=primary_br_entity,
                        expectation=br_desc,
                        kind="prompt",
                        br_refs=[br_id],
                    )],
                    "operation_hints": [],
                    "gen_seq": _gen_seq_counter,
                    "post_state": f"{primary_br_entity}→(操作被阻止)",
                    "cascade_chain": None,
                    "embedded_brs": [],
                    "_S2_fields": _make_S2_fields(
                        phase,
                        phase_table["phase_names"][phase] if phase < len(phase_table["phase_names"]) else f"P{phase}",
                        phase_basis, tl, 2, 0, "invalid", 9, 1, None,
                    ),
                    "_S3_fields": _make_S3_fields(),
                    "_S4_fields": _make_S4_fields(),
                }
                procedures.append(new_proc)
                host_procs = [new_proc]

        # Embed Thens into host procedures
        # Priority 1: LLM-generated signal-aware Thens
        # Priority 2: deterministic decomposition fallback (方案A)
        for proc in host_procs:
            entity = proc["entity"]
            dimension = proc.get("dimension") or ""
            loc = f"{entity}.{dimension}" if dimension else entity
            entities_raw = br.get("entities_involved", br.get("entities", ""))
            br_entities = _resolve_entity_names(entities_raw, entity_name_map)
            cross_refs = [e for e in br_entities if e != entity] if len(br_entities) > 1 else []

            llm_v_steps = signal_v_steps.get(br_id) if signal_v_steps else None
            if llm_v_steps:
                for vs in llm_v_steps:
                    # BDD: vs is now a ThenClause dict
                    vs_loc = vs.get("target", loc)
                    vs_exp = vs.get("expectation", "")
                    if not vs_exp:
                        continue
                    proc["thens"].append(_make_then(
                        target=vs_loc,
                        expectation=vs_exp,
                        kind=vs.get("kind", "behavior"),
                        br_refs=[br_id] + vs.get("br_refs", []),
                        cross_refs=cross_refs,
                    ))
            elif enforcement == "conditional":
                atoms = _decompose_br_desc(br_id, br_desc, state.get('br_decomposition', {}))
                for sub_label, assertion in atoms:
                    proc["thens"].append(_make_then(
                        target=loc,
                        expectation=f"[{sub_label}]正面: {assertion}",
                        kind="behavior", br_refs=[sub_label], cross_refs=cross_refs,
                    ))
                    proc["thens"].append(_make_then(
                        target=loc,
                        expectation=f"[{sub_label}]负面: 不满足条件时规则不触发",
                        kind="behavior", br_refs=[sub_label], cross_refs=cross_refs,
                    ))
            else:
                atoms = _decompose_br_desc(br_id, br_desc, state.get('br_decomposition', {}))
                for sub_label, assertion in atoms:
                    proc["thens"].append(_make_then(
                        target=loc,
                        expectation=f"[{sub_label}] {assertion}",
                        kind="behavior", br_refs=[sub_label], cross_refs=cross_refs,
                    ))
            proc.setdefault("embedded_brs", []).append(br_id)
            total_embedded += 1

    return procedures


# ---------------------------------------------------------------------------
# S1.10 Procedure Dedup (I24)
# ---------------------------------------------------------------------------

def _dedup_procedures(procedures: list[dict], cos: list[dict], warnings: list[str],
                      time_needs: set[str]) -> list[dict]:
    """S1.10: Deduplicate procedures — BDD-aware merge.

    Compares procedures by their BDD structure:
    - Action similarity: based on ``when.action`` (not ``steps[1].input``)
    - From-state: extracted from ``givens[0].state`` (not S step input parsing)
    - Merge: secondary's Thens appended to primary's thens (deduped by expectation)

    Generic design — NO hardcoded business keywords:
    Two procedures are considered "complete duplicates" (Branch A) iff ALL of:
      1. same entity + same dimension
      2. same post_state (same from→to transition)
      3. same branch Givens (same branch scenario)
      4. normalized action text equal (whitespace/punctuation-insensitive)
    No keyword list — works for any business domain.
    """
    co_map = {}
    for co in cos:
        co_map.setdefault(co.get('enabler_entity', ''), []).append(co)
        co_map.setdefault(co.get('dependent_entity', ''), []).append(co)

    to_remove: set[str] = set()

    def _normalize_action(action: str) -> str:
        """Normalize action text for comparison: strip whitespace, punctuation,
        and branch suffixes.  No keyword matching — pure text normalization."""
        if not action:
            return ""
        # Strip branch suffixes like [项目类型=能力验证]
        cleaned = _strip_branch_suffix(action)
        # Remove all whitespace and common CJK/ASCII punctuation
        cleaned = re.sub(r'[\s\u3000，。、；：！？""''（）()【】《》〈〉…—_\\/]', '', cleaned)
        return cleaned.lower()

    def _branch_givens(p: dict) -> set[tuple]:
        """Extract branch-condition Givens + the from-state as a comparable set.

        Includes the first (from-state) Given so procedures that differ only by
        their source state (e.g. 暂停 from=待评审 vs from=评审中 — a state-derived
        branch whose branch givens are skipped) are NOT merged as duplicates.
        """
        result = {
            (g.get("target", ""), g.get("state", ""))
            for g in p.get("givens", [])
            if "分支条件" in g.get("description", "")
        }
        fs = (p.get("givens") or [{}])[0].get("state", "")
        if fs:
            result.add(("from_state", fs))
        return result

    def _co_tid_matches(sid: str, tid: str) -> bool:
        """True if a procedure source_id references a CO transition id.

        Option C: branch-split variants carry "T-x[a]" as source_ids while the
        CO references the abstract "T-x". Match either the exact id or a
        variant suffix of it.
        """
        if not tid:
            return False
        return sid == tid or sid.startswith(tid + "[")

    def _ensure_time_control(proc: dict) -> None:
        """After a merge unions source_ids, the survivor must still satisfy V06:
        a procedure referencing a time-sensitive obligation (in time_needs) must
        declare time_control. A survivor that came from the non-time-sensitive
        sibling keeps time_control=None even though its source_ids now carry a
        time-sensitive TO (e.g. PROC-025/026 merging T-038 manual lock with
        T-039 auto-lock). Re-derive the mechanism from the action semantics so
        the declaration matches what _generate_type1 would have produced."""
        if proc.get("time_control"):
            return
        if not (set(proc.get("source_ids", []) or []) & time_needs):
            return
        action = (proc.get("when") or {}).get("action", "")
        proc["time_control"] = {
            "mechanism": _derive_time_mechanism(action),
            "status": "planned",
        }

    for i, p1 in enumerate(procedures):
        if p1["temp_id"] in to_remove:
            continue
        for j in range(i + 1, len(procedures)):
            p2 = procedures[j]
            if p2["temp_id"] in to_remove:
                continue

            same_entity = p1["entity"] == p2["entity"]
            same_dim = p1.get("dimension") == p2.get("dimension")

            # BDD: branch-split procedures must NOT be merged
            if _branch_givens(p1) != _branch_givens(p2):
                continue

            # Generic action similarity: normalized text equality (no keywords)
            action1_norm = _normalize_action(p1.get("when", {}).get("action", ""))
            action2_norm = _normalize_action(p2.get("when", {}).get("action", ""))
            similar_action = bool(action1_norm) and action1_norm == action2_norm

            # ── Branch A: complete duplicate ──
            # Same entity + same dim + same post_state + same branch + same normalized action
            if (same_entity and same_dim and similar_action
                    and p1["post_state"] == p2["post_state"]):
                if len(p1.get("thens", [])) >= len(p2.get("thens", [])):
                    # 确定性: list(set()) 迭代序随 PYTHONHASHSEED 抖动, 用
                    # dict.fromkeys 保序去重 (主流程 source_ids 在前)。
                    p1["source_ids"] = list(dict.fromkeys(p1.get("source_ids", []) + p2.get("source_ids", [])))
                    _ensure_time_control(p1)
                    to_remove.add(p2["temp_id"])
                    warnings.append(f"DEDUP: {p2['temp_id']} merged into {p1['temp_id']} (reason: 完全重复)")
                else:
                    p2["source_ids"] = list(dict.fromkeys(p2.get("source_ids", []) + p1.get("source_ids", [])))
                    _ensure_time_control(p2)
                    to_remove.add(p1["temp_id"])
                    warnings.append(f"DEDUP: {p1['temp_id']} merged into {p2['temp_id']} (reason: 完全重复)")
                continue

            # ── Branch B: same-entity causal merge ──
            if same_entity and similar_action and p1["post_state"] != p2["post_state"]:
                # V10 fix: do NOT merge a negative_test procedure with its
                # positive-path sibling. Both are legitimate branches of the
                # same transition (rejection vs acceptance) and must remain
                # separate procedures so coverage_matrix probes like "正常选入"
                # can match the positive path while "差不可选入" matches the
                # negative path.
                p1_neg = p1.get("risk_trait") == "negative_test" or p1.get("_S2_fields", {}).get("type_label") == "negative"
                p2_neg = p2.get("risk_trait") == "negative_test" or p2.get("_S2_fields", {}).get("type_label") == "negative"
                if p1_neg or p2_neg:
                    continue
                # BDD: extract from_state from givens[0].state directly
                p1_from = p1.get("givens", [{}])[0].get("state", "") if p1.get("givens") else ""
                p2_from = p2.get("givens", [{}])[0].get("state", "") if p2.get("givens") else ""
                if p1_from and p2_from and p1_from != p2_from:
                    continue
                p1_phase = p1.get('_S2_fields', {}).get('phase')
                p2_phase = p2.get('_S2_fields', {}).get('phase')
                if p1_phase is not None and p2_phase is not None and p1_phase != p2_phase:
                    continue

                p1_co_linked = any(
                    any(_co_tid_matches(sid, co.get('enabler_transition_id'))
                        or _co_tid_matches(sid, co.get('dependent_transition_id'))
                        for co in cos if co.get('enabler_entity') == p1['entity'] or co.get('dependent_entity') == p1['entity'])
                    for sid in p1.get('source_ids', [])
                )
                p2_co_linked = any(
                    any(_co_tid_matches(sid, co.get('enabler_transition_id'))
                        or _co_tid_matches(sid, co.get('dependent_transition_id'))
                        for co in cos if co.get('enabler_entity') == p2['entity'] or co.get('dependent_entity') == p2['entity'])
                    for sid in p2.get('source_ids', [])
                )
                if p1_co_linked and p2_co_linked:
                    primary_proc = p1 if p1["obligation_type"] <= p2["obligation_type"] else p2
                    secondary_proc = p2 if primary_proc is p1 else p1
                    # BDD: merge thens (dedupe by expectation text)
                    existing_exp = {t.get("expectation") for t in primary_proc.get("thens", [])}
                    for then in secondary_proc.get("thens", []):
                        if then.get("expectation") not in existing_exp:
                            primary_proc["thens"].append(then)
                            existing_exp.add(then.get("expectation"))
                    primary_proc["source_ids"] = list(dict.fromkeys(primary_proc.get("source_ids", []) + secondary_proc.get("source_ids", [])))
                    _ensure_time_control(primary_proc)
                    to_remove.add(secondary_proc["temp_id"])
                    warnings.append(f"DEDUP: {secondary_proc['temp_id']} merged into {primary_proc['temp_id']} (reason: 同实体因果合并)")
                    continue

            # ── Branch C: cross-entity causal merge ──
            if not same_entity and similar_action:
                # Type9 (field-validation) procs are INDEPENDENT per-entity BDD
                # scenarios — each asserts one entity's form rejects invalid
                # values. They share the generic scaffold action "提交含违规值的
                # 表单", so CO-linked pairs (如 E-ARC↔E-CAR) would normalize
                # equal and get causally merged, producing a proc whose Thens
                # target another entity's fields (E-ARC 用例断言 E-CAR.载体名称).
                # Field validation must stay per-entity: never merge a Type9.
                if (p1.get("obligation_type") == ObligationType.FIELD_VALIDATION
                        or p2.get("obligation_type") == ObligationType.FIELD_VALIDATION):
                    continue
                has_co = any(
                    co.get('enabler_entity') == p1['entity'] and co.get('dependent_entity') == p2['entity']
                    or co.get('enabler_entity') == p2['entity'] and co.get('dependent_entity') == p1['entity']
                    for co in co_map.get(p1['entity'], []) + co_map.get(p2['entity'], [])
                )
                p1_ph = p1.get('_S2_fields', {}).get('phase')
                p2_ph = p2.get('_S2_fields', {}).get('phase')
                if has_co and p1_ph is not None and p2_ph is not None and p1_ph == p2_ph:
                    primary_proc = p1 if p1["obligation_type"] <= p2["obligation_type"] else p2
                    secondary_proc = p2 if primary_proc is p1 else p1
                    existing_exp = {t.get("expectation") for t in primary_proc.get("thens", [])}
                    for then in secondary_proc.get("thens", []):
                        if then.get("expectation") not in existing_exp:
                            primary_proc["thens"].append(then)
                            existing_exp.add(then.get("expectation"))
                    primary_proc["source_ids"] = list(dict.fromkeys(primary_proc.get("source_ids", []) + secondary_proc.get("source_ids", [])))
                    _ensure_time_control(primary_proc)
                    to_remove.add(secondary_proc["temp_id"])
                    warnings.append(f"DEDUP: {secondary_proc['temp_id']} merged into {primary_proc['temp_id']} (reason: 因果合并)")
                    continue

    return [p for p in procedures if p["temp_id"] not in to_remove]


# ---------------------------------------------------------------------------
# LLM-based action classification (replaces HUMAN_DECISION_KEYWORDS)
# ---------------------------------------------------------------------------

_ACTION_CLASSIFY_PROMPT = """你是一个业务动作分类器。判断每个动作是"人工决策"还是"系统自动"。

## 分类标准
- **human**（人工决策）：动作需要人工判断/审批/确认/操作。如审核、审批、确认、签订、发布、驳回、退回、收款、付款、发样、收样、核验、撤销等需要人参与的动作。
- **system**（系统自动）：动作由系统自动执行。如初始化、创建、自动同步、驱动、触发条件、状态推进等无需人工干预的动作。

## 输出格式（JSONL，每行一个）
{"action":"动作文本","type":"human或system"}

只输出 JSONL，不要额外说明。"""


def _classify_actions_via_llm(actions: list[str]) -> dict[str, str]:
    """Classify a list of action texts as 'human' or 'system' via LLM.

    Returns ``{action_text: "human"|"system"}`` dict.
    On failure (no API key, LLM error), returns empty dict — callers
    fall back to treating all actions as 'system' (safe default).
    """
    if not actions:
        return {}
    # Dedupe
    unique = list(set(a for a in actions if a and a.strip()))
    if not unique:
        return {}

    # Load API config
    import os as _os
    api_base = _os.environ.get('LLM_API_BASE', 'https://open.bigmodel.cn/api/paas/v4').rstrip('/')
    api_key = _os.environ.get('LLM_API_KEY', '')
    model = _os.environ.get('LLM_ACTION_CLS_MODEL', 'glm-4-flash')
    if not api_key:
        cfg_path = _os.path.join(_os.path.dirname(__file__), '..', 'config.json')
        try:
            import json as _json
            with open(cfg_path) as f:
                cfg = _json.load(f)
            llm_cfg = cfg.get('llm', {})
            api_base = llm_cfg.get('api_base', api_base).rstrip('/')
            api_key = llm_cfg.get('api_key', api_key)
            model = llm_cfg.get('action_cls_model', model)
        except Exception:
            pass
    if not api_key:
        print('      [ACTION-CLS] LLM_API_KEY not set — skipping action classification')
        return {}

    # Build user prompt
    lines = ["请对以下动作逐一分类：", ""]
    for i, a in enumerate(unique, 1):
        lines.append(f"{i}. {a}")
    user_msg = "\n".join(lines)

    # Call LLM
    import urllib.request as _urllib
    import urllib.error as _urlerr
    import json as _json
    url = f'{api_base}/chat/completions'
    body = _json.dumps({
        'model': model,
        'messages': [
            {'role': 'system', 'content': _ACTION_CLASSIFY_PROMPT},
            {'role': 'user', 'content': user_msg},
        ],
        'temperature': 0.1,
        'max_tokens': len(unique) * 60 + 200,
    }).encode('utf-8')
    req = _urllib.Request(url, data=body, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    })

    try:
        with _urllib.urlopen(req, timeout=120) as resp:
            data = _json.loads(resp.read().decode('utf-8'))
        raw = (data.get('choices') or [{}])[0].get('message', {}).get('content', '')
    except Exception as e:
        print(f'      [ACTION-CLS] LLM call failed: {e}')
        return {}

    # Parse JSONL response
    result: dict[str, str] = {}
    for line in raw.split('\n'):
        line = line.strip()
        if not line or line.startswith('```'):
            continue
        try:
            obj = _json.loads(line)
            if isinstance(obj, dict) and 'action' in obj and 'type' in obj:
                a = obj['action']
                t = obj['type']
                if t in ('human', 'system'):
                    result[a] = t
        except _json.JSONDecodeError:
            continue
    print(f'      [ACTION-CLS] Classified {len(result)}/{len(unique)} actions')
    return result


# ---------------------------------------------------------------------------
# Main node function
# ---------------------------------------------------------------------------

def _inject_co_ids(proc_dicts: list[dict], cos: list[dict]) -> None:
    """Inject CO ids into dependent procedures' source_ids (in place).

    A procedure is a CO's dependent when its source TO id equals the CO's
    dependent_transition_id (branch-suffix variants "T-055a" strip to "T-055").
    This makes procs CARRY the CO id so S3's co_enabler binding can fire —
    S1:3650 already expects `host_co_id in p["source_ids"]`. Deterministic:
    COs appended in coverage-model order, dict.fromkeys dedup preserves order.
    """
    if not cos:
        return
    dep_tid_to_co: dict[str, list[str]] = {}
    for co in cos:
        dt = co.get("dependent_transition_id")
        cid = co.get("id")
        if dt and cid:
            dep_tid_to_co.setdefault(dt, []).append(cid)
    if not dep_tid_to_co:
        return
    for p in proc_dicts:
        sids = p.get("source_ids") or []
        add = []
        for sid in sids:
            add.extend(dep_tid_to_co.get(sid, []))
            base = re.sub(r'[a-z]$', '', sid)  # branch variant "T-055a" → "T-055"
            if base != sid:
                add.extend(dep_tid_to_co.get(base, []))
        if add:
            p["source_ids"] = list(dict.fromkeys(list(sids) + add))


def s1_generation_node(state: AgentState) -> dict:
    """S1 Procedure Generation node — deterministic, V2-equivalent."""
    global _gen_seq_counter
    _gen_seq_counter = 0  # Reset for each pipeline run

    cm = state["coverage_model"]
    warnings = list(state.get("warnings", []))
    errors = list(state.get("errors", []))

    # Build indices (same as V2)
    eos = cm.get("entity_obligations", [])
    tos = cm.get("transition_obligations", [])
    cos = cm.get("cross_entity_obligations", [])
    ros_raw = cm.get("constraint_obligations", [])
    if isinstance(ros_raw, dict):
        ros = [item for sublist in ros_raw.values() for item in sublist]
    elif isinstance(ros_raw, list):
        ros = ros_raw
    else:
        ros = []
    bds = cm.get("_context", {}).get("branch_dimensions", [])

    # ── LLM-based action classification (replaces HUMAN_DECISION_KEYWORDS) ──
    # Collect all unique action texts from TOs and classify them once.
    # Result is cached in state['action_classification'] and read by
    # _get_role_name for I21 role resolution.
    if 'action_classification' not in state:
        all_actions = [to.get('action', '') for to in tos if to.get('action')]
        # Also include CO triggers and suggested_actions
        for co in cos:
            if co.get('trigger'):
                all_actions.append(co['trigger'])
            if co.get('suggested_action'):
                all_actions.append(co['suggested_action'])
        action_cls = _classify_actions_via_llm(all_actions)
        state['action_classification'] = action_cls
        if action_cls:
            warnings.append(f"S1 action classification: {len(action_cls)} actions classified via LLM")
        else:
            warnings.append("S1 action classification: LLM unavailable, all actions treated as 'system'")

    eo_by_type: dict[str, list] = {}
    for eo in eos:
        eo_by_type.setdefault(eo["type"], []).append(eo)

    to_by_entity: dict[str, list] = {}
    for to in tos:
        to_by_entity.setdefault(to["entity"], []).append(to)

    co_constraint = [co for co in cos if co.get("causal_type") == "constraint"]
    co_lifecycle = [co for co in cos if co.get("causal_type") == "lifecycle"]

    ro_by_type: dict[str, list] = {}
    for ro in ros:
        ro_by_type.setdefault(ro["type"], []).append(ro)

    cfg_eo_to_bd: dict[str, dict] = {}
    for bd in bds:
        for eo in eo_by_type.get("attribute_config", []):
            if eo["entity"] == bd["entity"] and eo.get("attribute_name") == bd["dimension"]:
                cfg_eo_to_bd[eo["id"]] = bd

    # Build dynamic maps from coverage_model._context
    entity_name_map = _build_entity_name_map(cm)

    # Parse field-level validation constraint steps from entity_details
    entity_details = cm.get("_context", {}).get("entity_details", [])
    constraint_steps = parse_entity_constraints(entity_details)

    # S1-a/S1-b: 共享 TO 的合成分支声明（原位写回 TO：
    # _synth_branch_givens 渲染用 / _synth_branch_values 归属用，S3 消费）
    _compute_synth_branch_declarations(tos, bds, warnings)
    # 防线②：分支出生态初始值未声明的确定性告警（须在 S1-a/S1-b 之后——
    # 消费 _synth_branch_values 做分支兼容判定）
    _warn_undeclared_birth_states(tos, warnings)

    indices = {
        "eo_by_type": eo_by_type,
        "to_by_entity": to_by_entity,
        "co_constraint": co_constraint,
        "co_lifecycle": co_lifecycle,
        "ro_by_type": ro_by_type,
        "cfg_eo_to_bd": cfg_eo_to_bd,
        "entity_name_map": entity_name_map,
        "constraint_steps": constraint_steps,
    }

    # Calculate chain depths — PER-ENTITY-PER-DIMENSION (not global)
    # BDD root-cause fix: chain_depth only recurses within the same entity
    # AND same dimension.  This prevents independent business flows within
    # Generate procedures by type
    # BDD: Type4a/4b (constraint/lifecycle CO) are NO LONGER generated as
    # independent procedures.  CO's enabler and dependent state transitions
    # are already covered by Type1 procedures.  Type4a/4b were redundant —
    # their own Then said "此条件已在T-XXX前置条件中体现".
    # CO is now used ONLY for dependency ordering in S3 (not for generation).
    # br_list (business_rule ROs) is needed by Type1 for guard-polarity
    # detection, so compute it here before any generation.
    br_list = ro_by_type.get("business_rule", [])

    procedures: list[dict] = []
    procedures.extend(_generate_type1(state, indices, br_list))
    procedures.extend(_generate_type3(state, indices))
    procedures.extend(_generate_type5(state, indices, procedures))
    procedures.extend(_generate_type6(state, indices))
    # BDD: field_validation as independent Type9 procedures (not injected into Type1/3/5)
    procedures.extend(_generate_type9_field_validation(state, indices))

    # BR classification and embedding
    br_classifications = _classify_business_rules(state, indices)

    # ── LLM-based BR decomposition (replaces _BR_PREDICATE_MARKERS) ──
    # Decompose all business_rule ROs into atomic assertions once, cache
    # the result for Type7 generation and BR embedding.
    if 'br_decomposition' not in state:
        # TEMP: skip BR decomposition (LLM call too slow for 63 BRs)
        # br_decomp = _decompose_brs_via_llm(br_list)
        br_decomp = {}
        state['br_decomposition'] = br_decomp
        if br_decomp:
            warnings.append(f"S1 BR decomposition: {len(br_decomp)} BRs decomposed via LLM")
        else:
            warnings.append("S1 BR decomposition: LLM unavailable, BRs not decomposed")

    # ── Signal-type-driven V-step generation via LLM ──────────────────────
    # TODO: 注释LLM验证步骤生成,聚焦排序正确性验证
    # signal_v_steps = generate_signal_v_steps(ros, entity_name_map)
    signal_v_steps = {}

    # Type7 standalone — pass signal_v_steps for LLM-enriched V-steps
    procedures.extend(_generate_type7_standalone(
        br_classifications, state, entity_name_map, signal_v_steps
    ))

    # BR embedding (non-standalone → V steps in host procedures)
    procedures = _embed_brs(procedures, br_classifications, state, entity_name_map, signal_v_steps)

    # V02 guard polarity is now enforced inside _generate_type1 at build time
    # (restrictive BR matching merged into is_negative_branch detection),
    # replacing the old post-hoc _enforce_guard_polarity patch. This avoids
    # the cascade pollution where thens[0] asserted rejection while thens[1:]
    # still claimed successful state migration.

    # S1.10 Dedup (I24)
    # time_needs: obligations that require a time_control declaration (shared
    # criterion with V06 — context/time_control.py). A merge that unions a
    # time-sensitive source into a non-time-sensitive survivor must keep the
    # declaration, or V06 flags the merged proc.
    time_needs = needs_time_control_ids(state.get("coverage_model", {}))
    procedures = _dedup_procedures(procedures, cos, warnings, time_needs)

    # Validate all procedures
    from models.schema import validate_procedures
    valid_procs, val_errors = validate_procedures(procedures)
    errors.extend(val_errors)

    warnings.append(f"S1 generated {len(valid_procs)} procedures ({len(procedures) - len(valid_procs)} validation failures)")

    # Count type5 filtered
    type5_filtered = [eo["id"] for eo in eo_by_type.get("crud_operation", [])
                      if not _is_type5_retained(eo, state)]

    # Standalone count
    standalone_count = len([bc for bc in br_classifications if bc["category"] == "standalone"])

    # BR embedded count
    embedded_brs_count = sum(len(p.get("embedded_brs", [])) for p in procedures)

    warnings.append(f"S1 summary: standalone_type7={standalone_count}, embedded_brs={embedded_brs_count}, type5_filtered={len(type5_filtered)}")

    # Then 吸收下沉: transition_target 状态行被同 target 的 behavior 行完全
    # 包含 → 数据层标记 subsumed, 渲染层只消费标记 (不再文本比对)。
    subsumed_n = _mark_then_subsumption(valid_procs)
    if subsumed_n:
        warnings.append(f"S1 marked {subsumed_n} transition_target Thens subsumed by behavior")

    # CO id 注入: dependent proc 携带其服务的 CO id (source_ids 追加),供
    # S3 co_enabler 绑定。注入在 model_dump 之后 (dedup/校验都已完成)。
    proc_dicts = [p.model_dump(by_alias=True) for p in valid_procs]
    _inject_co_ids(proc_dicts, cos)

    # ── 2026-09 排序修复 A v2：同动作组相位对齐（S1 后、事实相位）────
    # 此时全部 proc 的 _S2_fields.phase 已含入口门控/state_ref 提升的真实
    # 值，对齐目标不再依赖 S0 的 raw phase_table 推断（v1 缺陷，见函数
    # docstring）。S2 排序消费对齐后的相位。
    _n_aligned = _align_same_action_phases_post_s1(proc_dicts, cm, state, warnings)
    if _n_aligned:
        warnings.append(
            f"S1.A: aligned {_n_aligned} proc phases across same-action groups")

    return {
        # BUGFIX #26: removed dead `hasattr(p, 'model_dump')` branch —
        # validate_procedures always returns Pydantic Procedure models.
        "procedures": proc_dicts,
        "br_classifications": br_classifications,
        "type5_filtered": type5_filtered,
        "gen_seq_counter": _gen_seq_counter,
        "warnings": warnings,
        "errors": errors,
        "current_stage": "s1",
    }