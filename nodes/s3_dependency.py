from __future__ import annotations
"""S3 Dependency Binding Node — v3 with I23 business temporal guards.

Implements:
- Strong: transition upstream + same-dim chain ordering + CO enabler + VE.co_ids
- Weak: cross-entity side_effects (filtered by target state)
- I23: Business temporal guards (5 rules)
- Branch-aware binding（branch_values 生命周期归属改造）: 跨分支候选一律不
  连边；回退边判定用归属分支的相位图；B2 容器创建边按归属消歧。
  平行生命周期（如 E-XM 能力验证 vs 测量审核）共用同一状态词汇表但推进
  次序互逆，“实体+状态”全局匹配会把另一分支的 proc 误认成前驱/使能者。
- Cycle detection via graph_algo.break_cycles() — v29 #3: confidence-based
- Final topological sort (deps-first, sort_key tiebreaker) + sequential ID assignment
"""
import re

from models.state import AgentState
from models.schema import ObligationType
from tools.graph_algo import break_cycles, topological_sort_procedures
from context.domain_precondition import object_existence

# v29 Engineering Optimization Gap 1: Fallback Observability
from tools.fallback_log import record_fallback as _record_fallback
from nodes.s0_topology import _build_state_pos, _collect_same_action_groups


def _proc_is_back_edge(p: dict, state_pos: dict) -> bool:
    """True if a procedure's transition is a loop back-edge (post_state earlier
    than from_state in the lifecycle).

    Such procedures (e.g. 归档评级 待归档→已选入 in a cyclic machine) must not be
    treated as state-machine predecessors — Guard 1 would otherwise order the
    archive/rating step BEFORE the earlier lifecycle steps that share the same
    post_state, reversing the business flow.
    """
    from_state = p.get('givens', [{}])[0].get('state', '') if p.get('givens') else ''
    post = p.get('post_state', '') or ''
    if '→' in post:
        post_state = post.split('→')[-1].strip().strip('()')
    else:
        post_state = post.strip().strip('()')
    if not from_state or not post_state or from_state in ('(初始)', '(None)', 'None'):
        return False
    d = state_pos.get((p.get('entity'), p.get('dimension')), {})
    pf, pt = d.get(from_state), d.get(post_state)
    if pf is None or pt is None:
        return False
    return pt <= pf


# ── v29 #3: Causal confidence ranking for cycle breaking ──────────────────
# Each dependency records its ORIGIN (the mechanism that added it).
# break_cycles uses this confidence to decide which edge to remove:
#   lower confidence = preferentially removed.
#
# Confidence scores (higher = more authoritative, less likely to be cut):
#   5  transition_upstream  — causal chain from transition graph (authoritative)
#   5  guard1_state_pred    — exact state machine predecessor (Guard 1)
#   4  co_enabler           — CO enabler_state binding (structural, HARD)
#   4  co_enabler_both_lateral        — CO weak (双 lateral: hard 语义不成立)
#   4  co_enabler_phase_inversion     — CO weak (相位反转: hard 违反 V01)
#   4  ve_co_ids            — Virtual entity CO binding (structural)
#   3  chain_ordering       — same-dim sort_key ordering (heuristic)
#   3  guard5_create_use    — create-before-use heuristic (Guard 5)
#   2  guard6_precond       — precondition TEXT matching (Guard 6, fragile)
#   1  weak_side_effect     — weak dep (always lowest)
DEP_CONFIDENCE: dict[str, int] = {
    "transition_upstream": 5,
    "guard1_state_pred": 5,
    "co_enabler": 4,
    "co_enabler_both_lateral": 4,
    "co_enabler_phase_inversion": 4,
    "ve_co_ids": 4,
    "chain_ordering": 3,
    "guard5_create_use": 3,
    "guard6_precond": 2,
    "domain_precond": 3,
    "composition_container": 3,
    "weak_side_effect": 1,
}


def _confidence_of(origin: str) -> int:
    """Return confidence score for a dep origin; unknown → 0 (lowest)."""
    return DEP_CONFIDENCE.get(origin, 0)


# ── Precondition state extraction (for Guard 6) ──────────────────────────
#
# TO.preconditions are free-form Chinese strings like:
#   "报名记录状态为报名成功"
#   "项目样品状态为已核查"
#   "报名记录样品状态推进(待发样->待收样->已收样)"
#   "项目状态为已结束"
#
# We extract the state value after "为" or after "状态" keywords, so we can
# match them against other procedures' post_state values.

# Pattern: capture state value after "为" or after "状态="
# P0 fix: regex must exclude ) and ） (closing parens) so patterns like
# "评价已完成(E-EVAL.评价状态=已确认)" capture "已确认" not "已确认)".
_PRECONDITION_STATE_RE = re.compile(
    r'(?:为|=|状态=)\s*[\u201c\u2018\"\']?([^\u201d\u2019\"\'，,；;（(（)）\s]+)[\u201d\u2019\"\']?'
)


def preconditions_extract_states(precond: str) -> list[str]:
    """Extract referenced state values from a single precondition string.

    Examples:
        "报名记录状态为报名成功" → ["报名成功"]
        "项目样品状态为已核查" → ["已核查"]
        "报名记录样品状态推进(待发样->待收样->已收样)" → ["待发样", "待收样", "已收样"]
        "项目状态为已结束" → ["已结束"]
    """
    if not precond or not isinstance(precond, str):
        return []
    results: list[str] = []
    # Strategy 1: "为XXX" or "=XXX" patterns
    for m in _PRECONDITION_STATE_RE.finditer(precond):
        val = m.group(1).strip()
        if val and len(val) >= 2 and val not in ("null", "None", "无", "初始"):
            results.append(val)
    # Strategy 2: arrow-separated states like "待发样->待收样->已收样"
    if "->" in precond or "→" in precond:
        normalized = precond.replace("→", "->")
        for chunk in normalized.split("->"):
            chunk = chunk.strip()
            # Strip leading/trailing punctuation
            chunk = re.sub(r'^[（(]+\s*', '', chunk)
            chunk = re.sub(r'\s*[）)]*$', '', chunk)
            if chunk and len(chunk) >= 2 and chunk not in results:
                results.append(chunk)
    return results



# ── 2026-09 排序修复 B：容器创建边 + 同动作共置 ─────────────────────────
# 排序问题 1（受理报名/预通知排在项目创建前）的根因：组合关系（composition）
# 从未被排序层消费——"容器先于内容"只存在于 SRS 数据声明里（E-XM
# —composition(high)→ E-BMJL），t41 受理报名故意不带 E-XM 门禁（诚实建模，
# 加门禁将时序倒置），父实体绑定只能靠 t40/t41 同动作对与 composition 承载，
# 而框架两者都不用于排序。
# B2 把组合关系变成创建序硬约束：对每条 composition P→C，C 的所有"依赖里
# 不含任何 P 侧 proc"的 proc 补一条指向 P 创建 proc 的硬依赖（单向、逐边
# 防环，不做全对全——否则 P 的后期 proc 会被拖到 C 之前且易成环）。
# v2 分支感知：父实体存在多分支创建（如 E-XM 同时有 t01 能力验证创建与
# t40 测量审核创建）时，v1 取 min sort_key 必然赌错分支（把 PROC-021 注入
# 测量审核流）；v2 只在唯一创建 proc 时加边，子 proc 自身是创建事件视图
# （base tids 与创建 proc 重叠，如 026 与 031 同挂 T-040）则跳过。
# v3（branch_values 生命周期归属改造）：多创建候选按归属消歧，恰一兼容即
# 命中；多兼容（共享模板，如报名记录维度 proc）或零兼容 → min-sort_key 兜底
# 挂最早创建（cands[0]），保证「首个项目在报名记录前」不回归。
# B1 让同动作组（声明式绑定）在最终序列中相邻，组内容器视图在前。

_CREATION_FROM_STATES = {'(初始)', '初始', '(none)', 'none', '(null)', 'null', '(None)', 'None'}


def _proc_is_creation(proc: dict) -> bool:
    """True if proc's transition creates its object (from-state is 初始/None)."""
    givens = proc.get('givens') or []
    if not givens or not isinstance(givens[0], dict):
        return False
    from_state = str(givens[0].get('state', '') or '').strip()
    return from_state in _CREATION_FROM_STATES


def _proc_base_tids(proc: dict) -> set:
    """Extract base transition ids ('T-041' ← 'T-041[a]' / 'T-041a') from source_ids."""
    tids = set()
    for sid in proc.get('source_ids', []) or []:
        if not isinstance(sid, str):
            continue
        m = re.match(r'^(T-\d+)', sid)
        if m:
            tids.add(m.group(1))
    return tids


# ── branch_values 生命周期归属改造：S3 依赖边分支感知 ─────────────────────
# TO 携带 branch_values/branch_path（生命周期身份，glm5pr §3.1 归属铁律：
# 平行流程型分支的每条分支后续推进转换都声明 branch_values，共有收尾共享）。
# proc 的归属 = source_ids 解析到的 TO 归属并集；空 set = 共享模板（每个
# 分支值下都实例化）或非分支义务。兼容规则：任一方无归属 → 兼容；
# 两个非空归属不相交 → 不同生命周期，禁止连边。
# P2 旧输出（无 branch_path/branch_values）时全部 proc 归属为空，
# 行为退化与改造前完全一致。


# P2 多组合展开变体 id 形态（T-032[a]/T-062[b]…）：唯一以 branch_path 取值
# 为互斥归属的形态。单组合无差异保留（id 无后缀、branch_values 缺省、仅
# branch_path 记注）与真共享（branch_path=[]）都是共享模板——若把记注值当
# 身份，跨维度同名词（评审结论'通过' vs 项目类型'能力验证'）会误杀合法依赖。
_P2_SPLIT_SUFFIX_RE = re.compile(r'\[[a-z]\]$')


def _to_branch_values(to: dict | None) -> set:
    """TO 的分支归属值集（生命周期身份）。

    优先级：branch_values 显式声明 > 展开变体（id 带 [a-z] 后缀）的
    branch_path 取值 > 空（共享模板）。空 set = 无归属，与所有分支兼容。
    全部元素 str 化，保证与 S0 dep_state_phase_map_by_branch 的键同空间可比。
    """
    if not isinstance(to, dict):
        return set()
    declared = {str(bv) for bv in (to.get("branch_values") or []) if bv}
    if declared:
        return declared
    if _P2_SPLIT_SUFFIX_RE.search(str(to.get("id", ""))):
        return {str(bp["value"]) for bp in (to.get("branch_path") or [])
                if isinstance(bp, dict) and bp.get("value")}
    return set()


def _proc_branch_values(proc: dict, to_by_id: dict) -> set:
    """proc 的生命周期归属 = source_ids 解析到的 TO 归属并集。

    无 TO 源的义务（Type5/7/9 的 EO/CO/RO id 查不到 to_by_id）→ 空 set
    （共享，与所有分支兼容）。"""
    bvs: set = set()
    for sid in proc.get("source_ids", []) or []:
        to = to_by_id.get(sid)
        if to is not None:
            bvs |= _to_branch_values(to)
    return bvs


def _branch_compatible(a: set, b: set) -> bool:
    """共享（空归属）与任何归属兼容；两个非空归属须相交才可连边。"""
    if not a or not b:
        return True
    return bool(a & b)


def _composition_parents(cm: dict) -> dict:
    """entity → composition parent（同对多声明取 confidence 最高者）。"""
    ctx = cm.get('_context', {}) or {}
    rank = {'high': 3, 'medium': 2, 'low': 1, '': 0}
    parents = {}
    for rel in ctx.get('structural_relations', []) or []:
        if not isinstance(rel, dict) or rel.get('relation_type') != 'composition':
            continue
        f, t = rel.get('from', ''), rel.get('to', '')
        if not f or not t or f == t:
            continue
        r = rank.get(rel.get('confidence', ''), 0)
        if t not in parents or r > parents[t][0]:
            parents[t] = (r, f)
    return {t: f for t, (_, f) in parents.items()}


def _bind_container_creation_edges(
    procedures: list,
    proc_by_id: dict,
    cm: dict,
    warnings: list,
    proc_bvs: dict | None = None,
) -> int:
    """B2 v2: composition P→C ⇒ C 侧无 P 依赖的 proc 补指向 P 创建 proc 的硬依赖。

    v2 分支感知：子 proc 自身是父实体创建事件视图（base tids 重叠）跳过。
    v3（branch_values 生命周期归属改造）：多创建候选时用生命周期归属消歧——
    子 proc 归属分支与父创建 proc 归属分支取交集，唯一兼容者入选；仍歧义
    则按 v1 语义兜底挂最早创建（min sort_key，cands[0]）：
      * 恰一兼容 → 分支命中（数据驱动消歧，杜绝赌错分支）；
      * 多兼容 → 子 proc 为共享模板（不属任一分支，如报名记录维度 proc）
        → min-sort_key 兜底，恢复「首个项目在报名记录前」（Issue 1 语义）；
      * 零兼容 → 子归属指向不存在的创建分支（理论退化态），同样兜底并告警。
    Single-level, per-edge cycle-checked（插入前做可达性检查，绝不依赖
    break_cycles 兜底删除本机制的边）。Returns added edge count.
    """
    parents = _composition_parents(cm)
    if not parents:
        return 0

    # 每实体的全部创建 proc（按 sort_key 稳定排序）。v1 只取 sort_key 最小
    # 者充当"唯一创建者"，多分支创建时必赌错分支（v1 实测 021 压过 031）。
    creation_procs: dict = {}
    for proc in procedures:
        if not _proc_is_creation(proc):
            continue
        ent = proc.get('entity', '')
        if not ent:
            continue
        creation_procs.setdefault(ent, []).append(proc['temp_id'])
    for ent in creation_procs:
        creation_procs[ent].sort(key=lambda pid: list(
            (proc_by_id.get(pid) or {}).get('_S2_fields', {}).get('sort_key') or []))
    # 各实体创建事件的全部基础 tid：识别"子 proc 自身是创建事件视图"
    creation_tids: dict = {}
    for ent, pids in creation_procs.items():
        tids: set = set()
        for pid in pids:
            tids |= _proc_base_tids(proc_by_id.get(pid) or {})
        creation_tids[ent] = tids

    def _reaches(src: str, dst: str, seen: set = None) -> bool:
        """True if dst reachable from src via dependency edges (src 传递依赖 dst)。"""
        if seen is None:
            seen = set()
        if src == dst:
            return True
        if src in seen:
            return False
        seen.add(src)
        p = proc_by_id.get(src)
        if not p:
            return False
        for d in (p.get('_S3_fields', {}).get('dependencies', []) or []):
            if _reaches(d, dst, seen):
                return True
        return False

    proc_entity = {p['temp_id']: p.get('entity', '') for p in procedures}
    added = 0
    for child_ent, parent_ent in sorted(parents.items()):
        cands = creation_procs.get(parent_ent) or []
        if not cands:
            warnings.append(
                f"S3.B2 跳过组合 {parent_ent}→{child_ent}: {parent_ent} 无创建 proc")
            continue
        parent_tids = creation_tids.get(parent_ent, set())
        for proc in procedures:
            if proc.get('entity', '') != child_ent:
                continue
            pid = proc['temp_id']
            if pid in cands:
                continue
            # v2: 子 proc 自身是父实体创建事件视图（base tids 与创建 proc 重
            # 叠，如 PROC-026 与 PROC-031 同挂 T-040）→ 它就是"容器诞生"事
            # 件本身，不需要容器创建边（v1 会给它补错分支的创建依赖）
            if parent_tids and (_proc_base_tids(proc) & parent_tids):
                warnings.append(
                    f"S3.B2 跳过(自身为创建事件视图): {pid} (组合 {parent_ent}→{child_ent})")
                continue
            s3 = proc.setdefault('_S3_fields', {})
            deps = s3.setdefault('dependencies', [])
            if any(proc_entity.get(d) == parent_ent for d in deps):
                continue
            if len(cands) > 1:
                # v3: 多创建候选 → 生命周期归属消歧（branch_values 改造，
                # 数据驱动替代 v2 的无条件留白；v1 取 min sort_key 赌分支
                # 实测赌错）。恰一兼容→分支命中；多兼容（共享模板）或零兼容
                # → min-sort_key 兜底（cands[0]=最早创建），恢复 v1 语义
                # 「首个项目在报名记录前」（Issue 1 修复，报名记录维度 proc
                # 不属任一 项目状态 分支，必须仍排在项目创建之后）。
                child_bvs = (proc_bvs or {}).get(pid, set())
                compat = [c for c in cands
                          if _branch_compatible(
                              child_bvs, (proc_bvs or {}).get(c, set()))]
                if len(compat) == 1:
                    p_creation = compat[0]
                    warnings.append(
                        f"S3.B2 分支消歧: {pid} ← {p_creation} "
                        f"(子归属 {sorted(child_bvs) or '共享'}，组合 {parent_ent}→{child_ent})")
                else:
                    p_creation = cands[0]
                    if not compat:
                        warnings.append(
                            f"S3.B2 兜底(零兼容): {pid} ← {p_creation} "
                            f"(子归属 {sorted(child_bvs)} 无创建候选，组合 {parent_ent}→{child_ent})")
            else:
                p_creation = cands[0]
            # 逐边防环：若 p_creation 已（传递）依赖 pid，则加边成环 → 跳过
            if _reaches(p_creation, pid):
                warnings.append(
                    f"S3.B2 容器创建边跳过(防环): {pid} ← {p_creation} "
                    f"(组合 {parent_ent}→{child_ent})")
                continue
            deps.append(p_creation)
            s3.setdefault('dep_origins', {})[p_creation] = 'composition_container'
            added += 1
    if added:
        warnings.append(f"S3.B2: added {added} container-creation ordering edges")
    return added


def _co_locate_same_action_groups(
    procedures: list,
    primary: str,
    cm: dict,
    warnings: list,
) -> int:
    """B1: 同动作组在最终序列中相邻，容器视图在前。

    在 topological_sort_procedures 之后、ID 重编号之前运行。只做可行性
    检查通过的位置移动，结果仍是合法拓扑序：
      Pass 1（拉拢）：以组内最早成员为块首，其余成员按当前位置序逐个拉到
        块尾——仅当 [目标位, 当前位) 窗口内没有该成员的依赖时才前移；
        否则向后扫描第一个可行位；完全不可行则放弃该成员（组保持部分相邻）。
      Pass 2（组内排序）：块内冒泡趋向期望序（组合祖先视图在前，其次主实体
        视图，再次保持相对序）；相邻交换 (a,b)→(b,a) 仅当 a 不被 b 依赖
        （a ∉ dep_map[b]），保证外部约束不变。
    返回完成相邻化的组数。
    """
    groups = _collect_same_action_groups(cm)
    if not groups:
        return 0

    tid_group: dict = {}
    for gi, g in enumerate(groups):
        for tid in g:
            tid_group[tid] = gi

    pos_of: dict = {p['temp_id']: i for i, p in enumerate(procedures)}
    dep_map: dict = {
        p['temp_id']: set(p.get('_S3_fields', {}).get('dependencies', []) or [])
        for p in procedures
    }

    group_members: dict = {}
    for p in procedures:
        for tid in _proc_base_tids(p):
            gi = tid_group.get(tid)
            if gi is not None:
                group_members.setdefault(gi, []).append(p['temp_id'])

    parents = _composition_parents(cm)

    def _entity_of(mid: str) -> str:
        return procedures[pos_of[mid]].get('entity', '')

    def _ancestor_of(a: str, b: str) -> bool:
        """True if composition chain from a reaches b（b 是 a 的组合祖先）。"""
        seen = set()
        cur = a
        while cur and cur not in seen:
            seen.add(cur)
            cur = parents.get(cur, '')
            if cur == b:
                return True
        return False

    def _apply_move(cur: int, tgt: int) -> None:
        proc = procedures.pop(cur)
        procedures.insert(tgt, proc)
        for i, p in enumerate(procedures):
            pos_of[p['temp_id']] = i

    done = 0
    for gi in sorted(group_members.keys()):
        members = group_members[gi]
        if len(members) < 2:
            continue
        members_by_pos = sorted(members, key=lambda m: pos_of[m])
        block_start = pos_of[members_by_pos[0]]

        # ── Pass 1: 拉拢相邻 ──
        # v2: 追踪实际落位的成员 id（v1 只计数，feasible>target 时块出现
        # 缺口，Pass 2 按下标取块会读写到非成员 proc）
        placed_ids = [members_by_pos[0]]
        for mid in members_by_pos[1:]:
            target = block_start + len(placed_ids)
            cur = pos_of[mid]
            if cur == target:
                placed_ids.append(mid)
                continue
            if cur < target:
                warnings.append(
                    f"S3.B1 同动作共置跳过: {mid} 位置异常(cur={cur}<target={target})")
                continue
            deps = dep_map.get(mid, set())
            feasible = None
            for t in range(target, cur):
                if not any(t <= pos_of[d] < cur for d in deps if d in pos_of):
                    feasible = t
                    break
            if feasible is None:
                warnings.append(
                    f"S3.B1 同动作共置部分失败: {mid} 无法前移至 {target}"
                    f"（依赖边界），组 {groups[gi]} 保持部分相邻")
                continue
            if feasible > target:
                warnings.append(
                    f"S3.B1 同动作共置: {mid} 落位 {feasible}>目标 {target}"
                    f"（依赖边界），块出现缺口")
            _apply_move(cur, feasible)
            placed_ids.append(mid)
        if len(placed_ids) < 2:
            continue

        # ── Pass 2: 组内排序（容器视图在前，其次主实体视图）──
        # v2: 按成员 id 收集块内实际位置；块不连续（成员被依赖卡住形成缺
        # 口）时跳过组内重排——位置槽语义不再成立，按下标取块必错。
        block_positions = sorted(pos_of[m] for m in placed_ids)
        first_pos = block_positions[0]
        if block_positions != list(range(first_pos, first_pos + len(placed_ids))):
            warnings.append(
                f"S3.B1 组 {groups[gi]} 块不连续（依赖边界），跳过组内排序")
            continue
        block_start = first_pos
        block = list(placed_ids)

        def _rank(mid: str) -> tuple:
            ent = _entity_of(mid)
            anc = sum(
                1 for other in block if other != mid and _ancestor_of(_entity_of(other), ent))
            is_primary = 0 if (primary and ent == primary) else 1
            return (-anc, is_primary, pos_of[mid])

        desired = sorted(block, key=_rank)
        cur_order = list(block)
        changed = True
        iters = 0
        while changed and iters <= len(cur_order) ** 2 + 1:
            changed = False
            iters += 1
            for i in range(len(cur_order) - 1):
                a, b = cur_order[i], cur_order[i + 1]
                if desired.index(a) > desired.index(b) and a not in dep_map.get(b, set()):
                    cur_order[i], cur_order[i + 1] = b, a
                    changed = True
        for i, mid in enumerate(cur_order):
            cur = pos_of[mid]
            if cur != block_start + i:
                _apply_move(cur, block_start + i)
        done += 1
        warnings.append(
            f"S3.B1 同动作共置: 组 {groups[gi]} → [{' → '.join(cur_order)}]")
    return done


def s3_dependency_node(state: AgentState) -> dict:
    """S3: Bind dependencies between procedures."""
    procedures = list(state.get("procedures", []))
    warnings = list(state.get("warnings", []))
    errors = list(state.get("errors", []))

    cm = state.get("coverage_model", {})
    tos = cm.get("transition_obligations", [])
    cos = cm.get("cross_entity_obligations", [])
    ves = state.get("virtual_entities", {})

    proc_by_id = {p["temp_id"]: p for p in procedures}
    proc_by_entity: dict[str, list] = {}
    for proc in procedures:
        proc_by_entity.setdefault(proc["entity"], []).append(proc)

    # Helper: sort dependency IDs by gen_seq (lower = more foundational = first).
    # gen_seq reflects the order procedures were generated in S1, which follows
    # CREATE → UPDATE → DELETE lifecycle. This makes dependency lists read in
    # a natural "prerequisites first" order.
    def _sort_deps(dep_ids: set) -> list:
        return sorted(dep_ids, key=lambda did: proc_by_id.get(did, {}).get("gen_seq", 999))

    to_by_id = {to["id"]: to for to in tos}
    co_by_id = {co["id"]: co for co in cos}
    # State lifecycle positions for back-edge detection (Guard 1 / chain)
    state_pos = _build_state_pos(cm.get("_context", {}).get("state_info", {}))

    # ── branch_values 生命周期归属改造：S3 分支感知上下文 ──────────────
    # proc 级生命周期归属（source_ids → TO.branch_values/branch_path 并集；
    # 无 TO 源的义务 = 共享）。per-branch 状态位相图 = 全局 state_pos 叠加
    # S0 dep_state_phase_map_by_branch 中声明了独立相位链的 (entity,dim)
    # 覆盖项——平行生命周期推进次序互逆，回退边判定与状态链必须用归属
    # 分支的相位图。
    proc_bvs: dict[str, set] = {
        p["temp_id"]: _proc_branch_values(p, to_by_id) for p in procedures
    }
    branch_pos: dict[str, dict] = {}
    for _bv, _dep_map in (state.get("dep_state_phase_map_by_branch") or {}).items():
        merged = {k: dict(v) for k, v in state_pos.items()}
        for _ent, _dims in (_dep_map or {}).items():
            if not isinstance(_dims, dict):
                continue
            for _dim, _states in _dims.items():
                if isinstance(_states, dict) and _states:
                    merged[(_ent, _dim)] = {
                        str(s): int(ph) for s, ph in _states.items()
                        if isinstance(ph, (int, float))
                    }
        branch_pos[str(_bv)] = merged
    branch_skip_stats: dict[str, int] = {}

    def _state_pos_for(p: dict) -> dict:
        """proc 生效的状态位相图：归属分支视图存在 → 分支视图；否则全局。"""
        for bv in sorted(proc_bvs.get(p.get("temp_id", ""), set())):
            if bv in branch_pos:
                return branch_pos[bv]
        return state_pos

    def _cross_branch(src_id: str, cand_id: str, origin: str) -> bool:
        """True = 跨分支候选（不连边）；按 origin 计数供审计。"""
        if _branch_compatible(proc_bvs.get(src_id, set()),
                              proc_bvs.get(cand_id, set())):
            return False
        branch_skip_stats[origin] = branch_skip_stats.get(origin, 0) + 1
        return True

    def _resolve_to(sid: str) -> dict | None:
        """Resolve a source_id to its transition obligation.

        Tries: exact match (id or transition_id), then strips branch suffix
        (e.g. "T-001a" → "T-001") since branch-variant source_ids may not
        have their own TO entry.
        """
        result = to_by_id.get(sid)
        if result:
            return result
        # Strip trailing lowercase letter (branch suffix)
        base = re.sub(r'[a-z]$', '', sid)
        if base != sid:
            return to_by_id.get(base)
        return None

    enabler_state_to_procs: dict[tuple, list] = {}
    for proc in procedures:
        post = proc.get("post_state", "")
        entity = proc["entity"]
        # Exclude rejection variants from enabler_state index — their post_state
        # "待开始(驳回)" is NOT "待开始" and should not be matched as enabler.
        if proc.get("risk_trait") == "audit_rejection":
            continue
        if "→" in post:
            state_part = post.split("→")[-1].strip()
            enabler_state_to_procs.setdefault((entity, state_part), []).append(proc["temp_id"])

    entity_dim_procs: dict[str, list] = {}
    for proc in procedures:
        if proc.get("dimension"):
            entity_dim_procs.setdefault(f"{proc['entity']}.{proc['dimension']}", []).append(proc["temp_id"])

    # ── I23: Business temporal guards (run FIRST — state-machine deps take priority) ──
    _apply_temporal_guards(procedures, proc_by_id, proc_by_entity, co_by_id, cm,
                           phase_table=state.get("phase_table"),
                           state_pos=state_pos, state=state,
                           cross_branch=_cross_branch,
                           state_pos_for=_state_pos_for)

    # ── Strong dependencies ──
    for proc in procedures:
        s3 = proc.get("_S3_fields", {})
        deps = set(s3.get("dependencies", []))
        # v29 #3: dep_origins tracks the source of each dep for confidence-based
        # cycle breaking. Each dep_id maps to its origin string (see DEP_CONFIDENCE).
        # When a dep is added by multiple mechanisms, the HIGHEST-confidence
        # origin wins (we overwrite only if new origin has higher confidence).
        dep_origins: dict[str, str] = dict(s3.get("dep_origins", {}))

        def _record_origin(dep_id: str, origin: str) -> None:
            """Record origin for a dep; keep highest-confidence origin on conflict."""
            existing = dep_origins.get(dep_id)
            if existing is None or _confidence_of(origin) > _confidence_of(existing):
                dep_origins[dep_id] = origin

        # Transition upstream deps are protected from cycle breaking.
        # They represent real business dependencies from the transition graph
        # and should never be removed. Stored separately and merged back after
        # break_cycles to preserve them through the cycle resolution process.
        # Guard 1 deps (state machine predecessor) are also protected.
        upstream_deps = set(s3.get("upstream_deps", []))
        upstream_deps |= set(s3.get("guard1_deps", []))
        # Carry over origins for upstream/guard1 deps (set by _apply_temporal_guards)
        for ud in s3.get("upstream_deps", []):
            if ud not in dep_origins:
                _record_origin(ud, "transition_upstream")
        for gd in s3.get("guard1_deps", []):
            _record_origin(gd, "guard1_state_pred")
        # Remove guard1 deps from regular deps (they're now protected)
        deps -= set(s3.get("guard1_deps", []))

        # my_phase: chain ordering / CO enabler 的相位守卫共用。
        my_phase = proc.get("_S2_fields", {}).get("phase", 0)

        # 1. Same-entity same-dimension chain ordering
        # Sort same-dim procedures by sort_key for deterministic chain
        # (independent of input list order, which may be arbitrary from S1)
        # I23-fix: validate that the predecessor's post_state feeds into this
        # procedure's from_state. Three cases:
        #   a) curr has no from_state → independent op (attr change, rule, gate)
        #      → skip chain (no meaningful state predecessor)
        #   b) curr is creation (from=初始/None) → root of chain → skip
        #   c) curr.from_state == prev.post_state → valid chain → add dep
        #   d) states don't match → skip (Guard 1 handles real state deps)
        if proc.get("dimension"):
            key = f"{proc['entity']}.{proc['dimension']}"
            same_dim_ids = entity_dim_procs.get(key, [])
            same_dim_sorted = sorted(
                same_dim_ids,
                key=lambda tid: (
                    proc_by_id.get(tid, {}).get("_S2_fields", {}).get("sort_key", [])
                ),
            )
            try:
                idx = same_dim_sorted.index(proc["temp_id"])
                if idx > 0:
                    prev_id = same_dim_sorted[idx - 1]
                    prev_proc = proc_by_id.get(prev_id, {})
                    # BDD: extract from_state from givens[0].state directly
                    # (was: parsing S-step input string in legacy AAA model)
                    curr_from_state = None
                    givens = proc.get("givens", [])
                    if givens:
                        curr_from_state = givens[0].get("state", "")
                    # Extract predecessor's post_state value (exact, no truncation)
                    prev_post = prev_proc.get("post_state", "")
                    prev_post_val = None
                    if "→" in prev_post:
                        prev_post_val = prev_post.split("→")[-1].strip()
                    # ── State-connection validation ──
                    # branch_values 改造：跨分支同名状态汇合点不构成状态链
                    # （平行生命周期共用词汇表，状态相等 ≠ 同生命周期前驱，
                    # 如测量审核 T-040 产出的报名中不是能力验证 T-002 的前驱）。
                    if not _branch_compatible(
                            proc_bvs.get(proc["temp_id"], set()),
                            proc_bvs.get(prev_id, set())):
                        branch_skip_stats["chain_ordering"] = \
                            branch_skip_stats.get("chain_ordering", 0) + 1
                        pass  # 跨分支不连边（等价 case d）
                    elif curr_from_state is None:
                        pass  # case (a): independent op — no chain predecessor
                    elif curr_from_state in ("(初始)", "(None)", "None", ""):
                        pass  # case (b): creation from null — root of chain
                    elif prev_post_val and curr_from_state == prev_post_val:
                        # case (c): valid state chain — but skip if prev already
                        # depends on curr (Guard 1 created the reverse edge).
                        # Adding both directions would create a cycle (e.g. 启用↔停用).
                        prev_deps = prev_proc.get("_S3_fields", {}).get("dependencies", [])
                        if proc["temp_id"] not in prev_deps:
                            # Phase guard: skip if predecessor is in a later phase
                            prev_phase = prev_proc.get("_S2_fields", {}).get("phase", 0)
                            if prev_phase <= my_phase:
                                deps.add(prev_id)
                                _record_origin(prev_id, "chain_ordering")
                    else:
                        pass  # case (d): states don't match
            except ValueError:
                pass

        # 2. CO enabler dependency
        # 修复 (2026-08-14): (1) S1 现注入 CO id 到 dependent proc 的 source_ids,
        # 此循环才会命中 co_by_id (原: source_ids 只有转换 id, 机制全死);
        # (2) 自环 CO (enabler==dependent) 与 S0 Source 3 的 dv==ev 守卫一致地
        #     跳过 (如 CO-005 T-061→T-061, 同状态自我引用只会产噪音 dep);
        # (3) 强度语义规则 (决定性论据): hard 依赖的语义前提是"前驱的状态推进
        #     是后继的条件"。lateral 转换 (from==to, 状态不变) 不推进任何状态
        #     → 该前提结构性不成立 → hard 语义不成立, 一律 weak。判据: enabler
        #     与 dependent 转换均 from==to (双 lateral), 如 CO-004 (T-058
        #     已登记→已登记 + T-062 正常→正常)。反例: 提醒系统宕机不会阻止
        #     限制触发——限制的条件是时间状态 (已到期未处理), 不是提醒的执行;
        #     时序 (提醒 12h 前) 是业务规则的时间差, 非因果门控。
        #     双 lateral → weak; 否则相位守卫: dep_phase <= my_phase → HARD
        #     (原始 conf=4 意图), > my_phase → weak (原始代码直接丢弃导致
        #     CO-001/002/003 完全消失, 降 weak 保留审计)。weak 边用语义可区分
        #     标签 `co_enabler_both_lateral` / `co_enabler_phase_inversion`,
        #     二者均已注册 DEP_CONFIDENCE=4 (同 co_enabler) — 若用未注册标签
        #     conf 归 0, break_cycles 会优先剪 CO 边、恢复倒退边 (实测)。
        #     区分标签既保方向又给审计保留 weak 原因。
        # 注意: S1/S2/S3 内部空间 proc.entity 是实体 ID (E-CAR), 与 CO 的
        # enabler_entity 同空间, 直接 (ee, es) 查表即可 (中文名翻译在输出层)。
        weak_origins_map = s3.setdefault("weak_origins", {})
        for sid in proc.get("source_ids", []):
            co = co_by_id.get(sid)
            if not co:
                continue
            if co.get("enabler_entity") == co.get("dependent_entity"):
                continue  # 自环 CO, 与 S0 dv==ev 守卫一致
            ee = co.get("enabler_entity")
            es = co.get("enabler_state")
            if ee and es:
                en_to = to_by_id.get(co.get("enabler_transition_id"))
                dep_to = to_by_id.get(co.get("dependent_transition_id"))
                both_lateral = bool(en_to and dep_to
                                    and en_to.get("from") == en_to.get("to")
                                    and dep_to.get("from") == dep_to.get("to"))
                for mid in enabler_state_to_procs.get((ee, es), []):
                    if mid != proc["temp_id"]:
                        # branch_values 改造：使能者须与 dependent 同生命周期
                        if _cross_branch(proc["temp_id"], mid, "co_enabler"):
                            continue
                        wd = s3.setdefault("weak_dependencies", [])
                        if both_lateral:
                            # hard 语义不成立 (lateral 不推进状态, 无门控可建)
                            if mid not in wd:
                                wd.append(mid)
                                weak_origins_map[mid] = "co_enabler_both_lateral"
                            _record_origin(mid, "weak_side_effect")
                            continue
                        dep_p = proc_by_id.get(mid, {})
                        dep_phase = dep_p.get("_S2_fields", {}).get("phase", 0)
                        if dep_phase > my_phase:
                            if mid not in wd:
                                wd.append(mid)
                                weak_origins_map[mid] = "co_enabler_phase_inversion"
                            _record_origin(mid, "weak_side_effect")
                        else:
                            deps.add(mid)
                            _record_origin(mid, "co_enabler")

        # 3. VE.co_ids dependency binding
        # (自环 CO 跳过; 内部空间 entity 是 ID 直接查表; 同 CO 块一律 weak)
        entity = proc["entity"]
        if entity in ves:
            ve = ves[entity]
            for co_id in ve.get("co_ids", []):
                co = co_by_id.get(co_id)
                if not co:
                    continue
                if co.get("enabler_entity") == co.get("dependent_entity"):
                    continue  # 自环 CO, 与 S0 dv==ev 守卫一致
                ee = co.get("enabler_entity")
                es = co.get("enabler_state")
                if ee and es:
                    for mid in enabler_state_to_procs.get((ee, es), []):
                        if mid != proc["temp_id"]:
                            # branch_values 改造：VE 使能者须同生命周期
                            if _cross_branch(proc["temp_id"], mid, "ve_co_ids"):
                                continue
                            wd = s3.setdefault("weak_dependencies", [])
                            if mid not in wd:
                                wd.append(mid)
                                weak_origins_map[mid] = "ve_co_ids"
                            _record_origin(mid, "weak_side_effect")

        s3["dependencies"] = _sort_deps(deps)
        s3["upstream_deps"] = _sort_deps(upstream_deps)
        s3["dep_origins"] = dep_origins  # v29 #3: persist for break_cycles

    # ── Weak dependencies (side_effects — filtered by target state) ──
    for proc in procedures:
        s3 = proc.get("_S3_fields", {})
        weak = set(s3.get("weak_dependencies", []))
        # v29 #3: weak deps always have the lowest confidence
        weak_origins: dict[str, str] = dict(s3.get("weak_origins", {}))

        for sid in proc.get("source_ids", []):
            to = _resolve_to(sid)
            if not to:
                continue
            for se in to.get("side_effects", []):
                te = se.get("target_entity")
                if not te or te == proc["entity"]:
                    continue
                td = se.get("target_dimension")
                effect = se.get("effect_desc", "")
                for other in proc_by_entity.get(te, []):
                    if other["temp_id"] == proc["temp_id"]:
                        continue
                    # branch_values 改造：side_effect 归属声在 TO 上，随其生命周期；
                    # 另一分支的 proc 不是正确副作用目标
                    if _cross_branch(proc["temp_id"], other["temp_id"],
                                     "weak_side_effect"):
                        continue
                    # BDD: only state-transition / CRUD / config procedures are
                    # valid weak-dep targets.  Rule-validation (Type7/8) and
                    # field-validation (Type9) describe business rules, not
                    # state changes — they should not be weak-dep targets of
                    # side_effect chains.
                    if other.get("obligation_type") in (
                            ObligationType.INVALID, ObligationType.RULE,
                            ObligationType.FIELD_VALIDATION):
                        continue
                    # Exclude rejection variants from weak-dep targets
                    if other.get("risk_trait") == "audit_rejection":
                        continue
                    if td and other.get("dimension") != td:
                        continue
                    if effect and other.get("post_state"):
                        post_st = other["post_state"].split("→")[-1].strip() if "→" in other["post_state"] else ""
                        if post_st and post_st not in effect:
                            continue
                    weak.add(other["temp_id"])
                    weak_origins[other["temp_id"]] = "weak_side_effect"

        # Independent Type7: weak dep to non-primary entity's closest phase proc
        if proc.get("obligation_type") == ObligationType.RULE:
            # BUGFIX #20: hoist cm.get out of the source_ids loop
            ros_raw = cm.get("constraint_obligations", [])
            if isinstance(ros_raw, dict):
                ros_all = [item for sublist in ros_raw.values() for item in sublist]
            elif isinstance(ros_raw, list):
                ros_all = ros_raw
            else:
                ros_all = []
            for sid in proc.get("source_ids", []):
                for r in ros_all:
                    if r.get("id") == sid or r.get("constraint_id") == sid:
                        entities_raw = r.get("entities_involved", r.get("entities", ""))
                        # BUGFIX #9: handle Chinese commas/顿号 via regex split
                        if isinstance(entities_raw, list):
                            br_entities = entities_raw
                        elif isinstance(entities_raw, str):
                            br_entities = re.split(r'[,，、\s]+', entities_raw)
                        else:
                            br_entities = []
                        for be in br_entities[1:]:
                            be = be.strip()
                            if be in proc_by_entity:
                                # BDD: only state-transition / CRUD / config
                                # procedures are valid weak-dep targets.
                                # Exclude Type7/8/9 (rule/field validation).
                                candidates = [
                                    p for p in proc_by_entity[be]
                                    if p.get("obligation_type") not in (
                                            ObligationType.INVALID, ObligationType.RULE,
                                            ObligationType.FIELD_VALIDATION)
                                    and _branch_compatible(
                                        proc_bvs.get(proc["temp_id"], set()),
                                        proc_bvs.get(p["temp_id"], set()))
                                ]
                                if candidates:
                                    closest = min(candidates,
                                                  key=lambda p: p.get("_S2_fields", {}).get("phase", 999))
                                    if closest:
                                        weak.add(closest["temp_id"])
                                        weak_origins[closest["temp_id"]] = "weak_side_effect"

        s3["weak_dependencies"] = _sort_deps(weak)
        s3["weak_origins"] = weak_origins  # v29 #3: persist for break_cycles

    # ── Merge ALL deps into one list BEFORE cycle breaking ──
    # upstream_deps and guard1_deps represent real business constraints
    # (transition graph edges). They must be part of the dependency graph
    # for cycle detection; otherwise cycle breaking works on an incomplete
    # graph and the Kahn sort discovers residual cycles from the unmerged edges.
    for proc in procedures:
        s3 = proc.get("_S3_fields", {})
        all_deps = set(s3.get("dependencies", []))
        for ud in s3.get("upstream_deps", []):
            all_deps.add(ud)
        for gd in s3.get("guard1_deps", []):
            all_deps.add(gd)
        s3["dependencies"] = _sort_deps(all_deps)
        # v29 #3: dep_origins already contains origins for all deps
        # (upstream_deps and guard1_deps origins were set when added).
        # No merge needed — origins are keyed by dep_id, not by source list.
        # Clear the now-merged fields so downstream code doesn't double-count
        s3["upstream_deps"] = []
        s3["guard1_deps"] = []

    # ── 2026-09 排序修复 B2：容器创建边（组合关系 → 创建序硬约束）──
    # 在全部依赖机制之后、break_cycles 之前运行；逐边防环，绝不产生新环。
    # v3: 传入 proc_bvs，多创建候选按生命周期归属消歧。
    _bind_container_creation_edges(procedures, proc_by_id, cm, warnings,
                                   proc_bvs=proc_bvs)

    # ── Cycle detection & breaking via graph_algo ──
    procedures, cycle_warnings = break_cycles(procedures)
    warnings.extend(cycle_warnings)

    # ── Final topological sort respecting dependency graph ──
    # Kahn algorithm naturally handles cross-phase deps: dependencies are
    # hard constraints, sort_key is only a tiebreaker among procedures
    # at the same topological level.
    procedures = topological_sort_procedures(procedures)

    # ── 2026-09 排序修复 B1：同动作组共置（可行性检查的位置移动）──
    # 拓扑排序后、ID 重编号前运行；只做不破坏依赖序的相邻化移动。
    _co_locate_same_action_groups(
        procedures, state.get("primary_entity") or "", cm, warnings)

    # ── Re-assign sequential IDs based on final topological order ──
    id_map: dict[str, str] = {}
    for i, proc in enumerate(procedures, 1):
        old_id = proc["temp_id"]
        new_id = f"PROC-{i:03d}"
        id_map[old_id] = new_id
        proc["temp_id"] = new_id

    # Update all dependency references to use new IDs, sorted by PROC number.
    # Sorting by PROC number ensures foundational procedures (earlier in the
    # final topo order = lower PROC number) appear first in dependency lists.
    def _proc_num(dep_id: str) -> int:
        try:
            return int(dep_id.split("-")[1].split(".")[0])
        except (IndexError, ValueError):
            return 999

    for proc in procedures:
        s3_final = proc.get("_S3_fields", {})
        # BDD: filter out dangling deps (referencing procedures removed by
        # S1 dedup or S3 cycle-break) before rewriting IDs.
        valid_deps = [d for d in s3_final.get("dependencies", []) if d in id_map]
        s3_final["dependencies"] = sorted(
            [id_map.get(d, d) for d in valid_deps],
            key=_proc_num,
        )
        valid_weak = [d for d in s3_final.get("weak_dependencies", []) if d in id_map]
        s3_final["weak_dependencies"] = sorted(
            [id_map.get(d, d) for d in valid_weak],
            key=_proc_num,
        )
        # Fix-1: rewrite dep_origins / weak_origins keys to new IDs.
        # These dicts were populated by _apply_temporal_guards and the weak-dep
        # pass using the original PROC-T1-N / PROC-T3-N temp_ids. Without
        # rewriting, downstream consumers (and human auditors reading the JSON)
        # see "ghost IDs" that don't exist in the final procedures list.
        # Filter out origins for deps that were dropped (cycle-break / dedup),
        # then remap surviving ones to their new PROC-NNN IDs.
        new_dep_origins: dict[str, str] = {}
        for old_dep_id, origin in s3_final.get("dep_origins", {}).items():
            if old_dep_id in id_map:
                new_dep_origins[id_map[old_dep_id]] = origin
        s3_final["dep_origins"] = new_dep_origins

        new_weak_origins: dict[str, str] = {}
        for old_dep_id, origin in s3_final.get("weak_origins", {}).items():
            if old_dep_id in id_map:
                new_weak_origins[id_map[old_dep_id]] = origin
        s3_final["weak_origins"] = new_weak_origins

        # Clear now-stale auxiliary fields that may also carry old IDs
        s3_final["upstream_deps"] = []
        s3_final["guard1_deps"] = []

    if branch_skip_stats:
        _stats_txt = ", ".join(f"{k}×{v}" for k, v in sorted(branch_skip_stats.items()))
        warnings.append(
            f"S3.B 分支感知（branch_values 生命周期归属改造）: 跨分支候选剔除 {_stats_txt}——"
            f"平行生命周期共用状态词汇表，状态匹配限同分支（或共享模板）内生效")

    has_strong = sum(1 for p in procedures if p.get("_S3_fields", {}).get("dependencies"))
    has_weak = sum(1 for p in procedures if p.get("_S3_fields", {}).get("weak_dependencies"))
    warnings.append(
        f"S3 bound dependencies ({has_strong} strong, {has_weak} weak), "
        f"topological sort complete, {len(procedures)} procedures re-ID'd"
    )

    return {
        "procedures": procedures,
        "dependency_graph": {"cycle_count": len(cycle_warnings)},
        "warnings": warnings,
        "errors": errors,
        "current_stage": "s3",
    }


def _apply_temporal_guards(
    procedures: list[dict],
    proc_by_id: dict,
    proc_by_entity: dict,
    co_by_id: dict,
    cm: dict,
    phase_table: dict | None = None,
    state_pos: dict | None = None,
    state: dict | None = None,
    cross_branch=None,
    state_pos_for=None,
):
    """I23: Apply business temporal guard rules as implicit strong dependencies.

    v29 #3: Each guard records the ORIGIN of the deps it adds, so break_cycles
    can use causal confidence (not chain_depth) to pick which edge to cut.

    state: S0 Engine State (topology_levels / dep_state_phase_map) — used by
    Guard 7 (Tier 2 domain precondition) to identify lifecycle entities.

    branch_values 生命周期归属改造：cross_branch(src_id, cand_id, origin) 为
    跨分支候选判定（True=剔除并计数）；state_pos_for(proc) 返回 proc 生效
    的状态位相图（归属分支视图优先）。两闭包由 s3_dependency_node 注入，
    缺省 None 时行为与改造前一致。"""
    # to_id → proc temp_ids (Tier 2 Guard 7 dep binding): branch TO ids like
    # T-015[a] map to their own Type1 proc, so binding all same-dim creation
    # branches is unambiguous.
    to_id_to_proc_ids: dict[str, list] = {}
    for p in procedures:
        for sid in p.get("source_ids", []):
            to_id_to_proc_ids.setdefault(sid, []).append(p["temp_id"])

    for proc in procedures:
        s3 = proc.get("_S3_fields", {})
        deps = set(s3.get("dependencies", []))
        # v29 #3: dep_origins dict — persisted alongside deps
        dep_origins: dict[str, str] = dict(s3.get("dep_origins", {}))

        def _record(dep_id: str, origin: str) -> None:
            """Record origin; keep highest-confidence origin on conflict."""
            existing = dep_origins.get(dep_id)
            if existing is None or _confidence_of(origin) > _confidence_of(existing):
                dep_origins[dep_id] = origin

        # Guard 1 deps are protected like upstream_deps (real business deps)
        guard1_deps = set(s3.get("guard1_deps", []))
        entity = proc["entity"]
        dim = proc.get("dimension", "")
        s2 = proc.get("_S2_fields", {})
        # v29 #3补强: my_phase needed by Guard 1 phase monotonicity check
        my_phase = s2.get("phase", 0)

        # Guard 1: State machine predecessor priority
        #
        # Design principle: use ONLY structural signals, not text matching.
        # The from_state comes from givens[0].state (set by S1 from TO.from).
        # We match it against other procedures' post_state EXACTLY.
        #
        # Strategy B (substring matching of post_state in description text)
        # has been REMOVED — it caused false positives where a phase 0 proc's
        # description happened to contain a phase 4 proc's post_state string,
        # creating cross-phase dependencies that broke ordering.
        #
        # Rules:
        # 1. EXCLUDE rejection variants — "待开始(驳回)" is NOT "待开始"
        # 2. EXACT match only — post_state must equal from_state exactly
        # 3. v29 #3补强: Phase monotonicity — dep phase must be ≤ my phase.
        # 4. v29 #23: Cap predecessors per from_state to avoid branch-variant
        #    inflation. When multiple branch variants (e.g. T-PROJ-007a/b/c/d)
        #    all produce the same post_state, Guard 1 would match ALL of them
        #    as predecessors, inflating dependency count to 20+. Fix: keep
        #    only the closest predecessors (by phase proximity, then gen_seq),
        #    capped at _GUARD1_MAX_PREDS per from_state.
        _GUARD1_MAX_PREDS = 3  # max predecessors per from_state
        s_steps = proc.get("givens", [])
        for s_step in s_steps:
            from_state = s_step.get("state", "")
            # Only use explicit state value (Strategy A)
            if not from_state or from_state in ("(初始)", "(None)", "None", ""):
                continue
            # Collect all candidate predecessors for this from_state
            # v29 #26i: deduplicate by (from_state, to_state) — multiple
            # branch variants of the same transition (e.g. T-PROJ-007a×10)
            # produce the same (from, to) pair. Only keep one representative
            # per unique pair, replacing the hard-coded _GUARD1_MAX_PREDS=3.
            seen_pairs: set[tuple[str, str]] = set()
            candidates_for_state: list[tuple[int, int, str]] = []  # (phase_diff, gen_seq, temp_id)
            for other in proc_by_entity.get(entity, []):
                if other["temp_id"] == proc["temp_id"]:
                    continue
                # Exclude rejection variants
                if other.get("risk_trait") == "audit_rejection":
                    continue
                # branch_values 改造：跨分支候选不连边（平行生命周期共用状态
                # 词汇表——状态相等 ≠ 同生命周期前驱，如能力验证 T-002 产出的
                # 报名中不是测量审核 T-044 的前驱）。
                if cross_branch and cross_branch(proc["temp_id"], other["temp_id"],
                                                 "guard1_state_pred"):
                    continue
                # Back-edge fix: a procedure whose transition loops back to an
                # EARLIER state (e.g. 归档评级 待归档→已选入) must not be a
                # predecessor — it would reverse lifecycle order.
                # branch_values 改造：按候选归属分支的相位图判定——全局链上
                # 互逆的推进（如报名中→待开始）在归属分支链内是顺向，全局图
                # 误判回退会排掉合法前驱。
                if _proc_is_back_edge(
                        other,
                        state_pos_for(other) if state_pos_for else state_pos):
                    continue
                post = other.get("post_state", "")
                if "→" in post:
                    post_state_val = post.split("→")[-1].strip()
                    if post_state_val == from_state:
                        # v29 #26i: deduplicate by (other_from, other_to)
                        other_givens = other.get("givens", [])
                        other_from = other_givens[0].get("state", "") if other_givens else ""
                        pair_key = (other_from, post_state_val)
                        if pair_key in seen_pairs:
                            continue  # already have a representative for this pair
                        # Check reverse: if other already depends on proc, skip
                        other_deps = other.get("_S3_fields", {}).get("dependencies", [])
                        if proc["temp_id"] in other_deps:
                            continue  # bidirectional inverse — skip
                        # v29 #3补强: Phase monotonicity check
                        other_phase = other.get("_S2_fields", {}).get("phase", 0)
                        if other_phase > my_phase:
                            continue
                        # v29 #26i: mark this pair as seen
                        seen_pairs.add(pair_key)
                        # v29 #23: collect candidates, sort by phase proximity
                        phase_diff = my_phase - other_phase
                        other_gen_seq = other.get("gen_seq", 0)
                        candidates_for_state.append((phase_diff, other_gen_seq, other["temp_id"]))
            # v29 #26i: no hard cap — dedup by (from, to) pair is sufficient
            candidates_for_state.sort()
            for _, _, tid in candidates_for_state:
                guard1_deps.add(tid)
                _record(tid, "guard1_state_pred")

        # Guard 2: Constraint gate (Type4a) before Type1
        if proc.get("obligation_type") == ObligationType.TRANSITION:
            # BDD: read precondition text from givens[0].description
            s_input = ""
            givens = proc.get("givens", [])
            if givens:
                s_input = givens[0].get("description", "") + " " + givens[0].get("state", "")
            for other in proc_by_entity.get(entity, []):
                # BDD: Type4a no longer generated — this guard is a no-op now.
                # CO ordering is handled by the CO enabler dependency (section 3).
                # Kept for documentation; will never match since ot=4 procs don't exist.
                if (other.get("obligation_type") == ObligationType.CONSTRAINT
                        and other["temp_id"] != proc["temp_id"]):
                    co = co_by_id.get(other.get("source_ids", [""])[0]) if other.get("source_ids") else None
                    if co and co.get("dependent_condition") and co.get("dependent_condition") in s_input:
                        deps.add(other["temp_id"])
                        _record(other["temp_id"], "guard2_constraint_gate")

        # Guard 5: Create-before-use (from==null creation before any modify/use)
        # More comprehensive: check if this proc's from-state matches a create proc's to-state
        is_creation = s2.get("operation_lifecycle") == 1
        if not is_creation and dim:
            for other in proc_by_entity.get(entity, []):
                if other["temp_id"] == proc["temp_id"]:
                    continue
                # branch_values 改造：创建者须与使用者同生命周期
                if cross_branch and cross_branch(proc["temp_id"], other["temp_id"],
                                                 "guard5_create_use"):
                    continue
                other_ol = other.get("_S2_fields", {}).get("operation_lifecycle", 0)
                # Creation proc: operation_lifecycle==1 or from=null in S step
                is_other_creation = other_ol == 1
                if not is_other_creation:
                    # BDD: check if other's givens[0].state indicates creation (from=null)
                    other_givens = other.get("givens", [])
                    if other_givens:
                        state_val = other_givens[0].get("state", "")
                        desc_val = other_givens[0].get("description", "")
                        if "(初始)" in state_val or "(初始)" in desc_val or "= None" in desc_val or "from=null" in desc_val.lower():
                            is_other_creation = True
                if is_other_creation and other.get("dimension") == dim:
                    # I25-fix: Type4b lifecycle procedures are side-effects of the
                    # enabler transition, not prerequisites. The architecture says
                    # "创建后同步创建" — lifecycle creation happens AFTER, not before.
                    if other.get("obligation_type") == ObligationType.LIFECYCLE:  # Type4b = lifecycle
                        continue
                    deps.add(other["temp_id"])
                    _record(other["temp_id"], "guard5_create_use")

        # ── Guard 6: Cross-dimension and cross-entity precondition state dependency ──
        #
        # v29 #2: Structured precondition lookup.
        # v28 used regex extraction from free-form Chinese precondition strings,
        # which is fragile (false positives from substring matches, misses
        # explicit E-XXX.维度=状态 references, etc.).
        #
        # v29 reads `precondition_state_refs` (populated by P2 build_obligations.py)
        # — a structured list of {entity, dimension, state} triples per TO.
        # S3 matches these against procedure post_state via structured lookup.
        #
        # Fallback: if `precondition_state_refs` is missing or empty (e.g.
        # older P2 output), falls back to the legacy regex-based
        # `preconditions_extract_states` to preserve backward compatibility.
        #
        # Rules preserved from v28:
        # 1. EXCLUDE rejection variants: "待开始(驳回)" is NOT "待开始"
        # 2. EXACT match only: post_state must equal prec_state exactly
        # 3. Phase monotonicity: candidate dep phase must be ≤ my phase
        # 4. Same-entity deps must be CROSS-DIMENSION (not same dim)
        primary_entity = phase_table.get('primary_entity', '') if phase_table else ''
        primary_dim = phase_table.get('primary_dimension', '') if phase_table else ''

        # my_phase already defined above (before Guard 1)
        tos_all = cm.get("transition_obligations", [])
        for sid in proc.get("source_ids", []):
            to = next((t for t in tos_all if t.get("id") == sid), None)
            if not to:
                continue

            # v29 #2: prefer structured precondition_state_refs; fall back to regex
            structured_refs = to.get("precondition_state_refs", []) or []
            preconds = to.get("preconditions", []) or []
            if structured_refs:
                # Structured path — match by (entity, dimension, state) triples
                for ref in structured_refs:
                    ref_entity = ref.get("entity", "")
                    ref_dim = ref.get("dimension", "")
                    ref_state = ref.get("state", "")
                    if not ref_state or len(ref_state) < 2:
                        continue
                    # Handle fuzzy "或" split
                    ref_state_clean = ref_state.split("或")[0].strip()
                    if not ref_state_clean or ref_state_clean in ("(初始)", "None", ""):
                        continue

                    # Case A: ref has explicit entity → match that entity only
                    if ref_entity and ref_entity != entity:
                        # Cross-entity: search procs of ref_entity
                        for other in proc_by_entity.get(ref_entity, []):
                            if other["temp_id"] == proc["temp_id"]:
                                continue
                            if other.get("risk_trait") == "audit_rejection":
                                continue
                            # branch_values 改造：前置态产出者须同生命周期
                            if cross_branch and cross_branch(
                                    proc["temp_id"], other["temp_id"],
                                    "guard6_precond"):
                                continue
                            # If ref_dim is specified, must match
                            if ref_dim and other.get("dimension") != ref_dim:
                                continue
                            post = other.get("post_state", "")
                            if "→" not in post:
                                continue
                            post_val = post.split("→")[-1].strip()
                            if post_val == ref_state_clean and post_val != "(初始)":
                                other_phase = other.get("_S2_fields", {}).get("phase", 0)
                                if other_phase > my_phase:
                                    continue
                                deps.add(other["temp_id"])
                                _record(other["temp_id"], "guard6_precond")
                    elif ref_entity == entity:
                        # Same-entity cross-dim: ref_dim must differ from curr dim
                        if not ref_dim or ref_dim == dim:
                            continue
                        for other in proc_by_entity.get(entity, []):
                            if other["temp_id"] == proc["temp_id"]:
                                continue
                            if other.get("risk_trait") == "audit_rejection":
                                continue
                            # branch_values 改造：前置态产出者须同生命周期
                            if cross_branch and cross_branch(
                                    proc["temp_id"], other["temp_id"],
                                    "guard6_precond"):
                                continue
                            if other.get("dimension") != ref_dim:
                                continue
                            post = other.get("post_state", "")
                            if "→" not in post:
                                continue
                            post_val = post.split("→")[-1].strip()
                            if post_val == ref_state_clean and post_val != "(初始)":
                                other_phase = other.get("_S2_fields", {}).get("phase", 0)
                                if other_phase > my_phase:
                                    continue
                                deps.add(other["temp_id"])
                                _record(other["temp_id"], "guard6_precond")
                    else:
                        # ref_entity is empty (state_info didn't resolve) —
                        # fall back to global post_state match across all procs.
                        # Use ref_dim as a filter when available.
                        for other in procedures:
                            if other["temp_id"] == proc["temp_id"]:
                                continue
                            if other.get("risk_trait") == "audit_rejection":
                                continue
                            # branch_values 改造：前置态产出者须同生命周期
                            if cross_branch and cross_branch(
                                    proc["temp_id"], other["temp_id"],
                                    "guard6_precond"):
                                continue
                            if ref_dim and other.get("dimension") != ref_dim:
                                continue
                            if (not ref_dim) and other.get("entity") == entity and other.get("dimension") == dim:
                                continue  # skip same-entity same-dim
                            post = other.get("post_state", "")
                            if "→" not in post:
                                continue
                            post_val = post.split("→")[-1].strip()
                            if post_val == ref_state_clean and post_val != "(初始)":
                                other_phase = other.get("_S2_fields", {}).get("phase", 0)
                                if other_phase > my_phase:
                                    continue
                                deps.add(other["temp_id"])
                                _record(other["temp_id"], "guard6_precond")
            else:
                # Legacy regex fallback (for older P2 output without
                # precondition_state_refs). Identical to v28 behavior.
                # v29 Engineering Optimization Gap 1: record this fallback
                # ONLY when there are preconditions to parse — otherwise
                # the regex would extract nothing and the log is noise.
                if preconds:
                    _record_fallback(
                        "s3.guard6.regex_fallback",
                        transition_id=sid,
                        detail=(
                            f"to.id={sid} has no precondition_state_refs; "
                            f"falling back to regex extraction on preconditions text"
                        ),
                        fallback_used="regex_extract_states",
                    )
                for prec_text in preconds:
                    # Normalize: preconds may be legacy strings OR new dicts.
                    if isinstance(prec_text, dict):
                        prec_text = prec_text.get("text", "") or ""
                    if not prec_text:
                        continue
                    for prec_state in preconditions_extract_states(prec_text):
                        # Handle fuzzy: split on "或" and take first part
                        prec_state_clean = prec_state.split("或")[0].strip()
                        if not prec_state_clean or len(prec_state_clean) < 2:
                            continue

                        # Search same-entity procs (cross-dimension)
                        for other in proc_by_entity.get(entity, []):
                            if other["temp_id"] == proc["temp_id"]:
                                continue
                            if other.get("risk_trait") == "audit_rejection":
                                continue
                            # branch_values 改造：前置态产出者须同生命周期
                            if cross_branch and cross_branch(
                                    proc["temp_id"], other["temp_id"],
                                    "guard6_precond"):
                                continue
                            post = other.get("post_state", "")
                            if "→" not in post:
                                continue
                            post_val = post.split("→")[-1].strip()
                            if post_val and post_val == prec_state_clean and post_val != "(初始)":
                                if other.get("dimension") == dim:
                                    continue
                                other_phase = other.get("_S2_fields", {}).get("phase", 0)
                                if other_phase > my_phase:
                                    continue
                                deps.add(other["temp_id"])
                                _record(other["temp_id"], "guard6_precond")

                        # Search cross-entity procs for ALL states
                        for other in procedures:
                            if other["temp_id"] == proc["temp_id"]:
                                continue
                            if other.get("entity") == entity:
                                continue
                            if other.get("risk_trait") == "audit_rejection":
                                continue
                            # branch_values 改造：前置态产出者须同生命周期
                            if cross_branch and cross_branch(
                                    proc["temp_id"], other["temp_id"],
                                    "guard6_precond"):
                                continue
                            post = other.get("post_state", "")
                            if "→" not in post:
                                continue
                            post_val = post.split("→")[-1].strip()
                            if post_val and post_val == prec_state_clean and post_val != "(初始)":
                                other_phase = other.get("_S2_fields", {}).get("phase", 0)
                                if other_phase > my_phase:
                                    continue
                                deps.add(other["temp_id"])
                                _record(other["temp_id"], "guard6_precond")

        # ── Guard 7: 领域前置 — CRUD/查看义务须对象实例已存在 ──
        # Tier 2: EO-CRU (Type5) 义务非状态转换, Guard 6 的 TO 查表路径够不到
        # (source_ids 是 EO id, _resolve_to 返回 None)。这里用
        # context.domain_precondition 派生对象存在性前置 (topology_level>0 的
        # 业务生命周期对象), 依赖边连到对象创建转换 (from=None) 的过程。
        # 管理类实体不派生 → 保持 "=存在", 不引入依赖。
        if state and proc.get("obligation_type") == ObligationType.CRUD and proc.get("entity"):
            dp_ref = object_existence(cm, state, proc["entity"])
            if dp_ref:
                for cid in dp_ref["creation_to_ids"]:
                    for cand in to_id_to_proc_ids.get(cid, []):
                        if cand == proc["temp_id"]:
                            continue
                        # branch_values 改造：对象创建者须与 CRUD 义务同生命周期
                        if cross_branch and cross_branch(
                                proc["temp_id"], cand, "domain_precond"):
                            continue
                        if proc_by_id.get(cand, {}).get("risk_trait") == "audit_rejection":
                            continue
                        cph = proc_by_id.get(cand, {}).get("_S2_fields", {}).get("phase", 0)
                        if cph > my_phase:
                            continue
                        if cand not in deps:
                            deps.add(cand)
                            _record(cand, "domain_precond")

        s3["dependencies"] = sorted(deps, key=lambda did: proc_by_id.get(did, {}).get("gen_seq", 999))
        s3["guard1_deps"] = sorted(guard1_deps, key=lambda did: proc_by_id.get(did, {}).get("gen_seq", 999))
        s3["dep_origins"] = dep_origins  # v29 #3: persist for break_cycles
