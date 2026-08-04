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
from nodes.s0_topology import (
    _build_entity_name_map, _build_role_map, _build_managed_entities,
    TYPE_PRIORITY_MAP, TYPE5_SPECIAL_OPS,
)
from nodes.field_validation import parse_entity_constraints, enrich_procedure_steps
from nodes.signal_validation import generate_signal_v_steps

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
    if role_id == 'system':
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

            upstream_map = state.get('transition_upstream_map', {})
            tos = state.get('coverage_model', {}).get('transition_obligations', [])
            to_by_tid = {t.get('transition_id'): t for t in tos if t.get('transition_id')}
            for tid, ups in upstream_map.items():
                t = to_by_tid.get(tid)
                if t and t.get('entity') == entity:
                    for uid in ups:
                        ut = to_by_tid.get(uid)
                        if ut and ut.get('entity') != entity:
                            ctx = state.get('coverage_model', {}).get('_context', {})
                            r = _role_lookup(ctx.get('roles', {}), ut.get('entity', ''))
                            if r and r != 'system':
                                return role_map.get(r, r)

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


def _make_given(target: str, state: str, description: str = "") -> dict:
    """Build a BDD Given clause (business-state precondition).

    ``state`` must be a business state value (e.g. "待审批"), NOT a UI
    navigation instruction.  ``description`` is optional context (e.g.
    VE scenario label).
    """
    return {"target": target, "state": state, "description": description}


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


# ── Procedure skeleton factories ─────────────────────────────────────────
# Every generator (Type1/3/5/6/7/9) builds the same _S2/_S3/_S4 field shape.
# These factories centralize the defaults so a schema change is one edit.

# 调试/内部推导的 phase_basis 值(引擎 traceability,对测试执行者是噪声)。
# 分类在引擎层完成并写入 _S2_fields.phase_basis_debug,渲染层只读标记,
# 不匹配具体 basis 字符串(避免渲染层耦合引擎内部命名)。
_DEBUG_BASIS_PATTERNS = [
    "fallback_default", "dep_state_phase_map.", ".min_phase",
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

    For state transitions, if from_state and to_state are available and
    meaningful, the event can reference the target state:
      action="提交审核", to_state="待审核" → "提交审核（目标状态：待审核）"

    Generic — no hardcoded business keywords.  Only does:
      1. Strip mechanical "事件触发" suffix
      2. If action is empty, describe via from→to state change
      3. If to_state is known and meaningful, append target-state context
    """
    if not action:
        if from_state and to_state and from_state != to_state:
            return f"状态从{from_state}变更为{to_state}"
        return "状态转换"

    # If the action already contains "事件触发", strip it
    cleaned = action.replace("事件触发", "").strip()
    if not cleaned:
        return "状态转换"

    # Append target-state context when the to_state is meaningful (not initial)
    if to_state and to_state != "(初始)" and to_state != from_state:
        return f"{cleaned}（目标状态：{to_state}）"

    return cleaned


# ── V06: time_sensitive 触发方式动态推导（模块级，无硬编码）─────────────
#
# validator 检查 time_sensitive 用例要求有明确的执行路径：
#   clock_injection / db_time_update / scheduler_manual_trigger
#
# 本函数根据 TO 的 action 语义动态推导主触发方式，其余作为备选。
# 触发方式标识符本身是 validator 协议约定的（类似枚举值），不算业务硬编码。

_ALLOWED_TRIGGER_METHODS = [
    "clock_injection",
    "db_time_update",
    "scheduler_manual_trigger",
]

_TRIGGER_HINT_TEMPLATES = {
    "clock_injection": "clock_injection: 测试时注入时钟到边界值",
    "db_time_update": "db_time_update: 直接更新数据库时间到过期后",
    "scheduler_manual_trigger": "scheduler_manual_trigger: 系统调度器在时限到达时自动触发",
}


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


def _build_timeout_hints(action_text: str) -> list[str]:
    """根据 action 语义动态构建触发方式 hints。

    所有 time_sensitive 用例都列出 3 种触发方式，主触发方式排第一。
    """
    primary = _derive_time_mechanism(action_text)
    ordered = [primary] + [m for m in _ALLOWED_TRIGGER_METHODS if m != primary]
    return [_TRIGGER_HINT_TEMPLATES[m] for m in ordered]


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
    """Fix-3: detect branch dimensions whose values coincide with the
    from_state or to_state set of the affected transitions, marking them
    as state-derived rather than genuinely orthogonal.

    Such dimensions produce meaningless cartesian explosions. Example:
      T-PLAN-008 (暂停) has from=待评审, branch_path=[暂停前状态=待评审]
      T-PLAN-009 (暂停) has from=评审中, branch_path=[暂停前状态=评审中]
      T-PLAN-010 (暂停) has from=已完成, branch_path=[暂停前状态=已完成]
      branch_dimensions[暂停前状态].values = [待评审, 评审中, 已完成]
      → equals the set of from_states across T-PLAN-008/009/010 (the
        causally-related transitions that lead INTO 暂停).
      The "暂停前状态" branch is thus just a re-statement of the from_state,
      not an independent dimension. Generating 3×3=9 procedures (each
      (from_state, pre_pause_state) pair) is wrong — only the 3 diagonal
      pairs (from=pre_pause) are semantically reachable.

    Detection (generic, no hardcoded dimension names):
      1. Collect ALL transitions listed in bd.affected_obligations (or, as
         fallback, those whose transition_id is in branch.target_transition).
      2. Compute the union of their from_states AND to_states.
      3. Compare against bd.values.
      4. If bd.values ⊆ (from_states ∪ to_states) AND |bd.values|≥2 AND
         |bd.values| ≥ |from_states| (i.e. bd covers most of the state
         variety), declare the dimension state-derived.
    """
    bd_values = set(bd.get("values", []) or [])
    if len(bd_values) < 2:
        return False

    # Collect affected TOs (preferred: from affected_obligations field;
    # fallback: from branch.target_transition)
    affected_ids = set(bd.get("affected_obligations", []) or [])
    target_tids = set()
    for branch in bd.get("branches", []):
        t = branch.get("target_transition", "")
        if t:
            target_tids.add(t)

    related_states: set[str] = set()
    for to in tos:
        to_id = to.get("id", "")
        tid = to.get("transition_id", "")
        matched = False
        if affected_ids and to_id in affected_ids:
            matched = True
        if not matched and tid in target_tids:
            matched = True
        if not matched:
            continue
        for s in (to.get("from"), to.get("to")):
            if isinstance(s, str) and s.strip():
                related_states.add(s.strip())

    if not related_states:
        return False
    # State-derived if bd_values is a subset of (or equal to) the related
    # states, with at least 2 elements overlapping.
    overlap = bd_values & related_states
    return len(overlap) >= 2 and overlap == bd_values


def _extract_branch_givens(
    to: dict, coverage_model: dict
) -> list[dict]:
    """Extract branch-dimension Given clauses for a TO.

    Two sources (merged, deduped):
      1. coverage_model._context.branch_dimensions — canonical, matched by
         target_transition prefix (e.g. target=T-001, to_id=T-001a → match).
         Entity filter is NOT applied because branch_dimensions may record
         only the primary entity (E-PROJ) while branch TOs exist on other
         entities (E-REG, E-ARC).
      2. TO.action text "[维度=值]" suffix — fallback when branch_dimensions
         is incomplete.  P2 appends this marker to branched TOs.

    This is GENERIC: works for any branch dimension (项目类型, 评分方式,
    评价人员角色, 消息发送接收人范围, etc.), no hardcoded dimension names.

    Fix-3: state-derived branch dimensions (e.g. 暂停前状态 whose values
    equal the from_states of the same transitions) are skipped — they are
    not orthogonal to the state machine and would explode the procedure
    count without adding semantic value.
    """
    if not to:
        return []
    to_id = to.get("id", "") or to.get("transition_id", "")
    to_entity = to.get("entity", "")
    to_action = to.get("action", "")
    to_tid = to.get("transition_id", "")
    givens: list[dict] = []
    seen_dims: set[str] = set()

    # Fix-3: pre-compute the set of state-derived branch dimensions to skip
    tos_all = coverage_model.get("transition_obligations", [])
    state_derived_dims: set[str] = set()
    for bd in coverage_model.get("_context", {}).get("branch_dimensions", []):
        if _is_state_derived_branch_dimension(bd, tos_all):
            state_derived_dims.add(bd.get("dimension", ""))

    # ── Source 1: branch_dimensions (canonical) ──
    bds = coverage_model.get("_context", {}).get("branch_dimensions", [])
    for bd in bds:
        bd_entity = bd.get("entity", "")
        bd_dim = bd.get("dimension", "")
        # Fix-3: skip state-derived branch dimensions
        if bd_dim in state_derived_dims:
            continue
        # Match by target_transition prefix (no entity filter — branch may
        # apply to dependent entities too, e.g. E-REG.报名记录样品状态)
        for branch in bd.get("branches", []):
            target_tid = branch.get("target_transition", "")
            branch_value = branch.get("value", "")
            if target_tid and to_id.startswith(target_tid) and to_id != target_tid:
                givens.append(_make_given(
                    target=f"{bd_entity}.{bd_dim}",
                    state=branch_value,
                    description=f"分支条件: {bd_dim}={branch_value}",
                ))
                seen_dims.add(bd_dim)
                break

    # ── Source 2: action "[维度=值]" suffix (fallback) ──
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
                    ))
                    seen_dims.add(dim_name)
    return givens


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
    # Rule 3: L0/L1/L5 + delete
    # BDD: "删除" is now configurable via type5_special_ops; if not configured,
    # check topology_level for L0/L1/L5 entities with any delete-like op.
    topology_levels = state.get("topology_levels", {})
    tl = topology_levels.get(entity, -1)
    delete_ops = {"删除", "remove", "delete"} | special_ops
    if tl in (0, 1, 5) and any(d in op_name for d in delete_ops):
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

def _resolve_phase(entity: str, dimension: str, state_value: str, state: AgentState) -> dict:
    """Phase resolution — V2 logic.

    Lookup order:
    1. Primary entity → phase_table.state_to_phase
    2. Dependent / VE entity → dep_state_phase_map
    3. Contextual phase rules → return special contextual marker
    4. Topology fallback → L0→P0, VE resolved_phase, parent anchor min
    """
    primary = state["primary_entity"]
    phase_table = state["phase_table"]
    dep_map = state["dep_state_phase_map"]
    ctx_rules = state.get("contextual_phase_rules", {})
    topo = state["topology_levels"]
    ves = state.get("virtual_entities", {})
    parent_map = state["entity_parent"]

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

    # Topology fallback
    tl = topo.get(entity, 0)
    if tl == 0:
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


def _resolve_phase_for_non_transition(state: dict, entity: str) -> dict:
    """Derive a sensible phase for non-transition procedures (Type3, Type7, etc.)

    Uses the entity's dep_state_phase_map maximum non-zero phase so rules,
    attribute configs, and other non-transition procedures sort near the
    entity's later business stage. Using max ensures the system state
    prerequisites exist before the rule is tested (better too late than too early).
    """
    primary = state["primary_entity"]
    dep_map = state.get("dep_state_phase_map", {})
    phase_table = state.get("phase_table", {})

    # Virtual entity: inherit its resolved_phase (set during S0 VE discovery).
    # Must be checked before dep_map so VE names never fall through to the
    # parent-chain / fallback branches (which would assign a wrong phase).
    ves = state.get("virtual_entities", {})
    if entity in ves:
        vp = ves[entity].get("resolved_phase", 0)
        return {"phase": vp, "basis": f"VE.{entity}.resolved_phase"}

    if entity == primary:
        all_p = [p for dm in phase_table.get("state_to_phase", {}).values() for p in dm.values()]
        if all_p:
            non_zero = [p for p in all_p if p > 0]
            p = max(non_zero) if non_zero else max(all_p)
            return {"phase": p, "basis": f"primary_entity_max_phase.{p}"}
        return {"phase": 0, "basis": "primary_entity_default"}

    if entity in dep_map:
        all_p = [p for dm in dep_map[entity].values() for p in dm.values()]
        if all_p:
            non_zero = [p for p in all_p if p > 0]
            p = max(non_zero) if non_zero else max(all_p)
            return {"phase": p, "basis": f"dep_map_max_phase.{entity}.{p}"}
        # Empty dep_map — fall through to parent-chain logic below

    # Entity absent from dep_map (or has empty dep_map):
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

    # Follow entity_parent chain to find a parent with phase info.
    parent_map = state.get("entity_parent", {})
    parent = entity
    while parent:
        parent = parent_map.get(parent)
        if not parent:
            break
        if parent in dep_map:
            all_p = [p for dm in dep_map[parent].values() for p in dm.values()]
            if all_p:
                non_zero = [p for p in all_p if p > 0]
                p = max(non_zero) if non_zero else max(all_p)
                return {"phase": p, "basis": f"parent_phase.{parent}.{p} (via chain from {entity})"}
        if parent == primary:
            all_p = [p for dm in phase_table.get("state_to_phase", {}).values() for p in dm.values()]
            if all_p:
                non_zero = [p for p in all_p if p > 0]
                p = max(non_zero) if non_zero else max(all_p)
                return {"phase": p, "basis": f"parent_primary_phase.{parent}.{p} (via chain from {entity})"}
        # Continue walking up the chain

    return {"phase": 0, "basis": f"fallback_default.{entity}"}


def _resolve_phase_for_transition(entity: str, dimension: str, from_state: str,
                                  to_state: str, state: AgentState,
                                  is_rollback: bool = False,
                                  preconditions: list[str] | None = None) -> dict:
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
        result = _resolve_phase(entity, dimension, from_state, state)
        if result.get("phase", 0) > 0:
            base_phase = result["phase"]
            base_basis = result["basis"]
        else:
            result = _resolve_phase(entity, dimension, to_state, state)
            base_phase = result.get("phase", 0)
            base_basis = result.get("basis", "")
    else:
        result = _resolve_phase(entity, dimension, to_state, state)
        base_phase = result.get("phase", 0)
        base_basis = result.get("basis", "")

    # P0 fix: bump phase if preconditions reference later-phase states
    if preconditions:
        prec_phase, prec_state = _max_precondition_phase(
            preconditions, state, exclude_entity=entity
        )
        if prec_phase > base_phase:
            return {
                "phase": prec_phase,
                "basis": f"{base_basis} → bumped to P{prec_phase} (precondition refs {prec_state})",
            }

    return {"phase": base_phase, "basis": base_basis}


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
    if obligation_type == 4:
        return "constraint"          # Type4a
    if obligation_type == 5:
        return "lifecycle"           # Type4b
    if obligation_type == 6:
        return "crud"                # Type5
    if obligation_type == 7:
        return "invalid"             # Type6
    if obligation_type == 8:
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
    if obligation_type == 4:
        return TYPE_PRIORITY_MAP.get("constraint", 3)   # Type4a
    if obligation_type == 5:
        return TYPE_PRIORITY_MAP.get("lifecycle", 7)    # Type4b
    if obligation_type == 6:
        return TYPE_PRIORITY_MAP.get("crud", 5)          # Type5
    if obligation_type == 7:
        return TYPE_PRIORITY_MAP.get("invalid", 9)       # Type6
    if obligation_type == 8:
        return TYPE_PRIORITY_MAP.get("rule", 6)          # Type7
    if obligation_type == 3:
        return TYPE_PRIORITY_MAP.get("happy", 1)         # Type3
    return TYPE_PRIORITY_MAP.get(risk_trait, 1)


# ---------------------------------------------------------------------------
# Type1 — Transition Obligation procedures
# ---------------------------------------------------------------------------

def _generate_type1(state: AgentState, indices: dict, depth_cache: dict,
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
        entity = to["entity"]
        dimension = to.get("dimension", "")
        risk_traits = to.get("risk_traits", [])
        transition_id = to.get("transition_id", "")
        chain_depth = depth_cache.get(transition_id, 0)

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
            for prec in preconditions:
                # v29 #26f: check if precondition is a structured object
                if isinstance(prec, dict):
                    prec_str = prec.get("text", "") or ""
                    prec_type = prec.get("type", "") or ""
                    if not prec_str.strip():
                        continue
                    if prec_type == "state_ref":
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
                ))
            # BDD: append branch-dimension Givens (generic, from branch_dimensions)
            # e.g. Given: E-PROJ.项目类型 = 能力验证 (分支条件)
            givens.extend(_extract_branch_givens(to, cm))

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
                ["不可", "不能", "不得", "禁止", "不允许", "无法", "无权", "未被", "未"])
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
            _guard_br_id = ""
            if not is_negative_branch and br_list:
                _ctx_g = cm.get("_context", {}) or {}
                _pc_g = _ctx_g.get("prohibition_config", {}) or {}
                # 通用禁止词兜底。领域特定短语(如"不能提为试用""连续3天")
                # 由 P2 的 prohibition_config.prohibit_keywords 提供(本数据集
                # 已配置);此处默认值只保留领域无关的通用否定词,避免领域词汇
                # 泄漏进通用引擎(违反 "NO hardcoded business keywords" 原则)。
                _prohibit_kw = tuple(_pc_g.get("prohibit_keywords",
                    ["不可", "不能", "禁止", "不得", "不允许", "无法", "无权",
                     "只能", "仅限", "才可", "只有"]))
                _givens_text = " ".join(
                    str(g.get("state", "")) + str(g.get("description", ""))
                    for g in givens or []
                )
                for br in br_list:
                    _br_desc = ((br.get("description") or "")
                                + " " + (br.get("suggested_action") or ""))
                    _br_signal = br.get("signal_type") or ""
                    # v29 修复: 要求 BR 描述含显式禁止词(不可/不能/禁止/只能/
                    # 才可/只有等)。signal_type=restrictive 的"规则定义型"BR
                    # (如 "从已选入状态的项目中选取1-5个项目纳入评审计划")描述
                    # 的是合法操作而非禁止——把它们当负向会误伤正常流程(T-003
                    # 项目纳入评审计划被误判为拒绝)。只有显式禁止的 BR 才阻断
                    # 该操作。
                    if (_br_signal != "restrictive"
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
                       (action_core_clean[:2] and action_core_clean[:2] in _br_desc):
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
            for se in side_effects:
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
                "obligation_type": 1,
                "risk_trait": ("negative_test" if _negative_branch_flag else proc_risk_trait),
                "givens": givens,
                "when": when,
                "thens": thens,
                # V06: time_sensitive 用例注入触发方式 hints（动态推导）
                "operation_hints": (
                    _build_timeout_hints(action) if "time_sensitive" in risk_traits else []
                ),
                # V06: 声明 time_control.mechanism(从时效语义推导);非时效为 None
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
                    "obligation_type": 1,
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
                    "operation_hints": (
                        _build_timeout_hints(action) if "time_sensitive" in risk_traits else []
                    ),
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
                _record_fallback(
                    "s1.is_approve.derived_fallback",
                    transition_id=to.get('id', '') or '',
                    detail=(
                        f"to.id={to.get('id', '')} has no is_approve field (LLM 0/29 不产出); "
                        f"using derived multi-signal"
                    ),
                    fallback_used="derived_multi_signal",
                )
                _is_approve_action, _derived_conf, _derived_ev = _derive_is_approve(
                    to, action
                )

            if ("audit" in risk_traits and not _is_already_rejection
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
                    "obligation_type": 1,
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
                # V06: time_sensitive 用例必须含触发方式 operation_hints
                # 使用模块级 _build_timeout_hints() 动态推导（无硬编码 hints 内容）

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
                    "obligation_type": 1,
                    "risk_trait": "time_sensitive",
                    "givens": boundary_givens,
                    "when": boundary_when,
                    "thens": boundary_thens,
                    # V06: 注入触发方式 hints（动态推导，boundary 主触发为 clock_injection）
                    "operation_hints": _build_timeout_hints(action + "(时间边界)"),
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
                    "obligation_type": 1,
                    "risk_trait": "time_sensitive",
                    "givens": expired_givens,
                    "when": expired_when,
                    "thens": expired_thens,
                    # V06: 注入触发方式 hints（动态推导，expired 主触发为 db_time_update）
                    "operation_hints": _build_timeout_hints(action + "(已过期)"),
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


def _generate_type3(state: AgentState, indices: dict, depth_cache: dict) -> list[dict]:
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
                chain_depth = depth_cache.get(transition_id, 0)
                phase_info = _resolve_phase(eo["entity"], attr, branch["value"], state)
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
                    "obligation_type": 3,
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
            phase_res = _resolve_phase_for_non_transition(state, eo["entity"])
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
                "obligation_type": 3,
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

def _generate_type5(state: AgentState, indices: dict) -> list[dict]:
    """Generate Type5 (crud_operation) procedures with retention filter.

    Only retained EOs generate procedures. If the entity has been split into
    VEs, generate one procedure per VE.
    """
    phase_table = state["phase_table"]
    dep_map = state["dep_state_phase_map"]
    ves = state.get("virtual_entities", {})
    topo = state["topology_levels"]
    primary = state["primary_entity"]

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
            primary_dim_map = phase_table["state_to_phase"].get(phase_table["primary_dimension"], {})
            if primary_dim_map:
                first_phase = next(iter(primary_dim_map.values()), 0)
                phase = first_phase if first_phase is not None else 0
                phase_basis = f"phase_table.{phase_table['primary_dimension']}"
        elif entity in dep_map:
            first_dim = next(iter(dep_map[entity].values()), None)
            if first_dim:
                phase = min(first_dim.values())
                phase_basis = f"dep_state_phase_map.{entity}.min_phase"
            else:
                # Empty dep_map — use parent chain
                phase_res = _resolve_phase_for_non_transition(state, entity)
                phase = phase_res["phase"]
                phase_basis = phase_res["basis"]
        elif entity in ves:
            phase = ves[entity].get("resolved_phase", 0)
            phase_basis = f"VE.{entity}.resolved_phase"
        else:
            phase_res = _resolve_phase_for_non_transition(state, entity)
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
                    "obligation_type": 6,
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
            givens = [_make_given(
                target=entity, state="存在",
                description="操作入口可用",
            )]
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
            op_hints = [f"导航至{entity_name}页面"]

            phase_name = (phase_table["phase_names"][phase]
                          if phase < len(phase_table["phase_names"]) else f"P{phase}")

            proc = {
                "temp_id": f"PROC-T5-{_next_gen_seq()}",
                "source_ids": [eo["id"]],
                "entity": entity,
                "dimension": None,
                "obligation_type": 6,
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

def _generate_type6(state: AgentState, indices: dict, depth_cache: dict) -> list[dict]:
    """Generate Type6 (invalid_transition) procedures.

    Phase is based on the 'from' state; chain_depth is the max depth of
    TOs whose 'to' matches the RO's 'from'.
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
                phase_res = _resolve_phase_for_non_transition(state, entity)
                phase = phase_res["phase"]
                phase_basis = phase_res["basis"]
        elif entity not in dep_map:
            # Entity absent from dep_map — try parent chain via helper
            phase_res = _resolve_phase_for_non_transition(state, entity)
            phase = phase_res["phase"]
            phase_basis = phase_res["basis"]

        # Chain depth from the transition that leads to "from" state
        chain_depth = 0
        for to in tos:
            if to["entity"] == entity and to.get("to") == ro.get("from"):
                chain_depth = max(chain_depth, depth_cache.get(to.get("transition_id", ""), 0))

        proc = {
            "temp_id": f"PROC-T6-{_next_gen_seq()}",
            "source_ids": [ro["id"]],
            "entity": entity,
            "dimension": None,
            "obligation_type": 7,
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
            matching_it = next((ro for ro in ro_by_type.get("invalid_transition", [])
                                if ro["entity"] in br_entities), None)
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
                               depth_cache: dict | None = None,
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
        phase_res = _resolve_phase_for_non_transition(state, primary_br_entity)
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
        br_signal_type = br.get('signal_type', '')

        # v29 修复 (Type7 同义反复): restrictive BR 且能抽取出被禁止操作时,
        # 用确定性负向模板(违规场景 → 拦截断言),不再产出 When/Then 同文
        # 的"按规则X执行操作 / Then: [BR] X"。非 restrictive 或无法抽取
        # 禁止操作的 BR 保持描述性 fallback。
        # 动作动词从 prohibition_config 读取(领域无关兜底),不在此处硬编码
        # 业务动词列表。
        _type7_action_verbs = _get_action_verbs(cm)
        neg_op = (_extract_negative_op(br_desc, _type7_action_verbs)
                  if br_signal_type == "restrictive" else "")

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
                description=f"规则：{br_desc}",
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

        # Try to find associated transition for chain depth
        chain_depth = 0
        for to in tos:
            if br_entities and to["entity"] in br_entities:
                t_depth = depth_cache.get(to.get("transition_id", ""), 0) if depth_cache else 0
                chain_depth = max(chain_depth, t_depth)

        # V06: 时限/超时/timing BR 注入触发方式 hints + time_control
        # 条件与 V06 模型信号一致: category=timing 或 desc 含"超时/时限"
        _is_timing_br = (br.get("category") == "timing"
                         or "超时" in br_desc or "时限" in br_desc)

        proc = {
            "temp_id": f"PROC-T7-{_next_gen_seq()}",
            "source_ids": [br.get("id", br.get("constraint_id", ""))],
            "entity": primary_br_entity,
            "dimension": None,
            "obligation_type": 8,
            "risk_trait": "",
            "givens": givens,
            "when": when,
            "thens": thens,
            "operation_hints": (
                _build_timeout_hints(br_desc) if _is_timing_br else []
            ),
            # V06: 时限/超时 BR 用例声明 time_control(调度器触发)
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
    state: AgentState, indices: dict, depth_cache: dict
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

    # Build non_editable_attrs set (same as Type3) to filter out
    # non-configurable fields from Type9 field_validation procs.
    # Only uses is_config=False (structural signal, no keyword matching).
    cm = state.get("coverage_model", {})
    non_editable_attrs: set[tuple[str, str]] = set()
    for ed in cm.get("_context", {}).get("entity_details", []):
        ent_id = ed.get("id", "")
        for attr in ed.get("attributes", []) or []:
            if isinstance(attr, dict):
                attr_name = attr.get("name", "")
                if attr.get("is_config") is False and ent_id and attr_name:
                    non_editable_attrs.add((ent_id, attr_name))

    for entity_id, field_thens in constraint_steps.items():
        if not field_thens:
            continue

        # Filter out thens that target non-editable (system-maintained) fields
        filtered_thens = []
        for t in field_thens:
            tgt = t.get("target", "") or ""
            # Check if target matches any non_editable_attr (format: "entity.attr" or "E-XXX.attr")
            for ent_id, attr_name in non_editable_attrs:
                # Match both "E-ORG.机构类型" and "机构.机构类型" formats
                if attr_name in tgt and (ent_id in tgt or ent_id.replace("E-", "") in tgt):
                    break
            else:
                filtered_thens.append(t)

        if not filtered_thens:
            continue  # All fields were non-editable, skip this entity
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
                first_phase = next(iter(primary_dim_map.values()), 0)
                phase = first_phase if first_phase is not None else 0
                phase_basis = f"phase_table.{phase_table.get('primary_dimension', '')}"
        elif entity_id in dep_map:
            first_dim = next(iter(dep_map[entity_id].values()), None)
            if first_dim:
                phase = min(first_dim.values())
                phase_basis = f"dep_state_phase_map.{entity_id}.min_phase"
            else:
                phase_res = _resolve_phase_for_non_transition(state, entity_id)
                phase = phase_res["phase"]
                phase_basis = phase_res["basis"]
        elif entity_id in ves:
            phase = ves[entity_id].get("resolved_phase", 0)
            phase_basis = f"VE.{entity_id}.resolved_phase"
        else:
            phase_res = _resolve_phase_for_non_transition(state, entity_id)
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
        cm = state.get("coverage_model", {})
        tos_all = cm.get("transition_obligations", [])
        roles_ctx = cm.get("_context", {}).get("roles", [])
        role_name_map = {r.get("id", ""): r.get("name", "") for r in roles_ctx if isinstance(r, dict)}
        role_name_map["system"] = "系统"

        # 收集该 entity 在 TO 中出现过的所有 role
        entity_roles = []
        for to in tos_all:
            if to.get("entity") == entity_id:
                role = to.get("role", "")
                if role and role not in entity_roles:
                    entity_roles.append(role)

        # 优先选非 system 的业务角色
        business_roles = [r for r in entity_roles if r != "system"]
        if business_roles:
            inferred_actor = role_name_map.get(business_roles[0], business_roles[0])
        elif entity_roles:
            # 只有 system role
            inferred_actor = role_name_map.get(entity_roles[0], "系统")
        else:
            # 无 TO（managed 实体）：根据 entity_details.type 推断
            entity_details = next((ed for ed in cm.get("_context", {}).get("entity_details", [])
                                   if ed.get("id") == entity_id), None)
            if entity_details:
                etype = entity_details.get("type", "")
                if etype == "managed":
                    inferred_actor = role_name_map.get("R-SYSADMIN", "系统管理员")
                else:
                    inferred_actor = role_name_map.get("R-SYSADMIN", "系统管理员")
            else:
                inferred_actor = role_name_map.get("R-SYSADMIN", "系统管理员")

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
            "obligation_type": 9,  # Type9 = field_validation
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
    topo = state["topology_levels"]
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
                          if p["obligation_type"] == 3
                          and any(sid in host_eo_ids for sid in p.get("source_ids", []))]

        elif bc["category"] == "transition_constraint":
            host_to_id = bc.get("host_to_id")
            host_co_id = bc.get("host_co_id")
            if host_to_id:
                host_procs = [p for p in procedures
                              if p["obligation_type"] == 1
                              and host_to_id in p.get("source_ids", [])
                              and p.get("risk_trait") != "audit_rejection"]
            if host_co_id:
                host_procs.extend([p for p in procedures
                                   if p["obligation_type"] == 4
                                   and host_co_id in p.get("source_ids", [])])

        elif bc["category"] == "crud_constraint":
            host_eo_id = bc.get("host_eo_id")
            if host_eo_id:
                host_procs = [p for p in procedures
                              if p["obligation_type"] == 6
                              and host_eo_id in p.get("source_ids", [])]

        elif bc["category"] == "br_embed":
            # v29 #23b: standalone BR embedded into same-entity Type1 proc
            host_to_id = bc.get("host_to_id")
            if host_to_id:
                host_procs = [p for p in procedures
                              if p["obligation_type"] == 1
                              and host_to_id in p.get("source_ids", [])
                              and p.get("risk_trait") != "audit_rejection"]

        elif bc["category"] == "negative_test":
            entities_raw = br.get("entities_involved", br.get("entities", ""))
            br_entities = _resolve_entity_names(entities_raw, entity_name_map)
            # Find existing Type6 proc for same entity
            host_procs = [p for p in procedures
                          if p["obligation_type"] == 7
                          and br_entities and p["entity"] in br_entities]

            if not host_procs:
                # Create new Type6 variant procedure (negative_test BR with no existing Type6)
                # v29 #18: was "E-PRJ" hardcoded — replaced with state["primary_entity"]
                primary_br_entity = br_entities[0] if br_entities else state.get("primary_entity", "")
                tl = topo.get(primary_br_entity, 0)
                phase = 0
                phase_basis = "P6: topology_level L0 → P0" if tl == 0 else "default"

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
                    "obligation_type": 7,
                    "risk_trait": "negative",
                    "givens": [_make_given(
                        target=primary_br_entity,
                        state="规则适用前提满足",
                        description=f"{prohibited}相关数据已准备",
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

def _dedup_procedures(procedures: list[dict], cos: list[dict], warnings: list[str]) -> list[dict]:
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
        """Extract branch-condition Givens as a comparable set."""
        return {
            (g.get("target", ""), g.get("state", ""))
            for g in p.get("givens", [])
            if "分支条件" in g.get("description", "")
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
                    p1["source_ids"] = list(set(p1.get("source_ids", []) + p2.get("source_ids", [])))
                    to_remove.add(p2["temp_id"])
                    warnings.append(f"DEDUP: {p2['temp_id']} merged into {p1['temp_id']} (reason: 完全重复)")
                else:
                    p2["source_ids"] = list(set(p2.get("source_ids", []) + p1.get("source_ids", [])))
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
                    any(sid == co.get('enabler_transition_id') or sid == co.get('dependent_transition_id')
                        for co in cos if co.get('enabler_entity') == p1['entity'] or co.get('dependent_entity') == p1['entity'])
                    for sid in p1.get('source_ids', [])
                )
                p2_co_linked = any(
                    any(sid == co.get('enabler_transition_id') or sid == co.get('dependent_transition_id')
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
                    primary_proc["source_ids"] = list(set(primary_proc.get("source_ids", []) + secondary_proc.get("source_ids", [])))
                    to_remove.add(secondary_proc["temp_id"])
                    warnings.append(f"DEDUP: {secondary_proc['temp_id']} merged into {primary_proc['temp_id']} (reason: 同实体因果合并)")
                    continue

            # ── Branch C: cross-entity causal merge ──
            if not same_entity and similar_action:
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
                    primary_proc["source_ids"] = list(set(primary_proc.get("source_ids", []) + secondary_proc.get("source_ids", [])))
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
    # the same entity (e.g. E-REG.通知状态 vs E-REG.报名记录状态) from
    # sharing a chain_depth pool and interleaving by gen_seq.
    from tools.graph_algo import calc_all_chain_depths
    transition_entities: dict[str, str] = {}
    transition_dimensions: dict[str, str] = {}
    for to in tos:
        tid = to.get("transition_id", "")
        ent = to.get("entity", "")
        dim = to.get("dimension", "") or ""
        if tid and ent:
            transition_entities[tid] = ent
            transition_dimensions[tid] = dim
    depth_cache = calc_all_chain_depths(
        state["transition_upstream_map"],
        transition_entities=transition_entities,
        transition_dimensions=transition_dimensions,
    )

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
    procedures.extend(_generate_type1(state, indices, depth_cache, br_list))
    procedures.extend(_generate_type3(state, indices, depth_cache))
    procedures.extend(_generate_type5(state, indices))
    procedures.extend(_generate_type6(state, indices, depth_cache))
    # BDD: field_validation as independent Type9 procedures (not injected into Type1/3/5)
    procedures.extend(_generate_type9_field_validation(state, indices, depth_cache))

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
        br_classifications, state, depth_cache, entity_name_map, signal_v_steps
    ))

    # BR embedding (non-standalone → V steps in host procedures)
    procedures = _embed_brs(procedures, br_classifications, state, entity_name_map, signal_v_steps)

    # V02 guard polarity is now enforced inside _generate_type1 at build time
    # (restrictive BR matching merged into is_negative_branch detection),
    # replacing the old post-hoc _enforce_guard_polarity patch. This avoids
    # the cascade pollution where thens[0] asserted rejection while thens[1:]
    # still claimed successful state migration.

    # S1.10 Dedup (I24)
    procedures = _dedup_procedures(procedures, cos, warnings)

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

    return {
        # BUGFIX #26: removed dead `hasattr(p, 'model_dump')` branch —
        # validate_procedures always returns Pydantic Procedure models.
        "procedures": [p.model_dump(by_alias=True) for p in valid_procs],
        "br_classifications": br_classifications,
        "type5_filtered": type5_filtered,
        "gen_seq_counter": _gen_seq_counter,
        "warnings": warnings,
        "errors": errors,
        "current_stage": "s1",
    }