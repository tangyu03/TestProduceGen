"""V08 相位一致性（重构版）。

语义约定（case_spec v1.1+）：
- transitions[*].direction ∈ {forward, backward, lateral, resume, self}
    forward   主链推进：相位必须严格递增（output 与 spec 派生相位中都成立）
    backward  合法回退（选出/解锁/归档回退/重启/提试用）：豁免相位检查，须携带 note
    lateral   侧挂状态入口（暂停等主链外状态）：豁免相位检查，须携带 note
    resume    从侧挂状态恢复回主链（重启评审计划/解锁用户等，P1 直出）：豁免相位检查，须携带 note
    self      自环：豁免相位检查
- 相位派生规则（与 phase_mapping.auto_derived 对齐）：
    forward/lateral 边 BFS 传播深度；backward/self 仅用于可达性补全；
    terminal_states 统一拉至最大派生相位。
- 动态目标（to 以 "$" 开头，如 $pre_pause_state）不参与相位比对。
- 环状状态机中派生相位不递增的 forward 边（如 机构 试用→合格 的升级边）
  自动识别为 anomaly，豁免单调检查并记入 hygiene 观察。

旧版启发式（trigger 白名单 / side_effect / indirect_via / guard 关键词）已移除：
启发式会把真正错误的相位映射误判为"设计意图"（如 trigger 含"取消"会豁免
T-PLAN-004 的相位错误）。方向必须由 spec 显式标注才可审计。
兼容：无 direction 字段时退回读 regression_allowed；再缺省按 forward 处理。
"""
from collections import deque

from .base import CheckResult, get_procedures
from models.schema import ObligationType

CHECK_ID = "V08"

_EXEMPT_DIRECTIONS = {"backward", "lateral", "resume", "self"}
_DYNAMIC_PREFIX = "$"
STRICT_FORWARD = True          # True: forward 要求严格递增(>)；False: 仅禁止倒退(>=)


def _direction_of(t: dict) -> str:
    """解析迁移方向：显式 direction > 旧字段 regression_allowed > 默认 forward。

    P1 直出的 direction 含 resume(从侧挂状态恢复回主链，如 重启评审计划/解锁用户)，
    与 backward 一样豁免相位单调检查。不能识别的取值退回 forward(safe default)。
    """
    d = str(t.get("direction") or "").strip().lower()
    if d in {"forward", "backward", "lateral", "resume", "self"}:
        return d
    if t.get("regression_allowed"):
        return "backward"
    return "forward"


def _derive_phases(m: dict) -> tuple:
    """从 transitions 派生相位，并找出偏序无法自洽的 forward 边（anomaly）。

    返回 (phases, anomaly_forward_ids)。
    BFS：初始迁移(from="(初始)")的 to 深度为 0；forward/lateral 边传播深度+1；
    随后用全图补可达性（环状机中仅经 backward 可达的状态，如 机构.试用）；
    最后 terminal_states 拉至最大深度。
    """
    states = [s for s in (m.get("states") or [])]
    transitions = m.get("transitions") or []
    fwd_adj, all_adj = {}, {}
    initials = []
    for t in transitions:
        f, to = t.get("from"), t.get("to")
        if not (isinstance(f, str) and isinstance(to, str)):
            continue
        if to.startswith(_DYNAMIC_PREFIX):
            continue
        if f == "(初始)":
            initials.append(to)
            continue
        d = _direction_of(t)
        all_adj.setdefault(f, []).append(to)
        if d in {"forward", "lateral"}:
            fwd_adj.setdefault(f, []).append(to)

    phases = {}
    q = deque()
    for s in initials:
        if s not in phases:
            phases[s] = 0
            q.append(s)
    if not q:  # 无显式初始迁移时，取入度为 0 的状态
        has_in = {to for adjs in all_adj.values() for to in adjs}
        for s in states:
            if s not in has_in:
                phases.setdefault(s, 0)
                q.append(s)
    while q:
        cur = q.popleft()
        for nxt in fwd_adj.get(cur, []):
            cand = phases[cur] + 1
            if nxt not in phases or cand < phases[nxt]:
                phases[nxt] = cand
                q.append(nxt)
    # 可达性补全（backward-only 可达态）
    changed = True
    while changed:
        changed = False
        for f, adjs in all_adj.items():
            if f not in phases:
                continue
            for nxt in adjs:
                if nxt not in phases:
                    phases[nxt] = phases[f] + 1
                    changed = True
    # 终态拉至最大相位
    terminals = m.get("terminal_states") or []
    if terminals and phases:
        maxp = max(phases.values())
        for s in terminals:
            if s in phases:
                phases[s] = maxp
    # anomaly：派生相位下不递增的 forward 边（环状机特征，如 试用→合格）
    anomaly = []
    for t in transitions:
        if _direction_of(t) != "forward":
            continue
        f, to = t.get("from"), t.get("to")
        if f in phases and to in phases and phases[to] <= phases[f]:
            anomaly.append(t.get("id"))
    return phases, anomaly


def _is_state_phase_map(tbl) -> bool:
    """True if tbl maps state names → int phases (the structure V08 needs)."""
    if not isinstance(tbl, dict) or not tbl:
        return False
    return all(isinstance(v, (int, float)) for v in tbl.values())


def _flatten_dep_tables(dep: dict) -> list:
    """Flatten dep_state_phase_map {entity: {dim: {state: phase}}} to a list
    of {state: phase} dicts, one per (entity, dim).
    """
    out = []
    for ent_map in (dep or {}).values():
        if not isinstance(ent_map, dict):
            continue
        for dim_map in ent_map.values():
            if isinstance(dim_map, dict) and _is_state_phase_map(dim_map):
                out.append(dim_map)
    return out


def _phase_map(output: dict, m: dict, name: str) -> dict:
    """定位 output 中该状态机的相位表。

    候选键：spec.dimension → "{实体名}状态" → 实体名 → 主实体维度；
    最后以 states 重合度兜底（修复"计划状态"与 output 键"评审计划状态"不一致
    导致整机被静默跳过的问题）。

    返回的 dict 必须是 {state_name: int_phase}。如果匹配到的结构是
    {dim: {state: phase}}（如 dep_state_phase_map 的内层），会自动 unwrap
    到 {state: phase}。这修复了 spec.dimension 与 dep[entity] 的 key 同名时
    误返回整层 {dim: {state: phase}} 导致 max() 崩溃的问题。
    """
    es = output.get("engine_state", {}) or {}
    pt = es.get("phase_table", {}) or {}
    stp = pt.get("state_to_phase", {}) or {}
    dep = es.get("dep_state_phase_map", {}) or {}
    candidates = [m.get("dimension"), f"{name}状态", name]
    if pt.get("primary_entity") in (name, f"E-{name}"):
        candidates.append(pt.get("primary_dimension"))

    # Build a flat list of {state: phase} tables from both stp and dep.
    # stp values are already {state: phase}; dep values are {dim: {state: phase}}
    # and must be flattened.
    stp_tables = [v for v in stp.values() if _is_state_phase_map(v)]
    dep_tables = _flatten_dep_tables(dep)
    tables = stp_tables + dep_tables

    for cand in candidates:
        if not cand:
            continue
        # 1. Direct hit in stp (stp[cand] is {state: phase})
        if cand in stp and _is_state_phase_map(stp[cand]):
            return stp[cand]
        # 2. cand matches a dim name inside dep[entity] — return the inner
        #    {state: phase} map. This handles the common case where
        #    spec.dimension == dep[entity][dim] (e.g. "项目状态" matches
        #    dep["E-PROJ"]["项目状态"]).
        for ent_map in dep.values():
            if isinstance(ent_map, dict) and cand in ent_map:
                dim_map = ent_map[cand]
                if _is_state_phase_map(dim_map):
                    return dim_map

    # 3. States-overlap fallback (pick the table with most state-name overlap)
    states = set(m.get("states") or [])
    best, best_hit = {}, 0
    for tbl in tables:
        hit = len(states & set(tbl.keys()))
        if hit > best_hit:
            best, best_hit = tbl, hit
    return best if states and best_hit >= max(1, len(states) // 2) else {}


def _machines_from_model(model: dict) -> dict:
    """从模型 state_info + transition_obligations 推导状态机定义。

    第一性原理: 状态机的 states/terminal/transitions 是模型的结构知识
    (state_info + TO),不必由 case_spec.state_machines 重复编码。
    返回 {实体名: {dimension, states, terminal_states, transitions}}。
    """
    si = (model.get("_context") or {}).get("state_info", {}) or {}
    tos = model.get("transition_obligations", []) or []
    machines = {}
    for ent, info in si.items():
        name = info.get("entity_name") or ent
        for dim in info.get("dimensions", []) or []:
            dim_name = dim.get("dimension_name", "")
            trans = [t for t in tos
                     if t.get("entity") == ent and t.get("dimension") == dim_name]
            # C-05: key 必须带维度——多维实体（如 E-XM 的 项目状态/项目阶段）
            # 旧实现按实体名作 key，后写维度覆盖先写，主链维度静默丢失校验。
            key = f"{name}.{dim_name}"
            machines[key] = {
                "entity": name,          # 实体名单独存，供相位表候选匹配
                "dimension": dim_name,
                "states": dim.get("states", []) or [],
                "terminal_states": dim.get("terminal", []) or [],
                "transitions": [
                    {"id": t["id"],
                     "from": t.get("from") or "(初始)",
                     "to": t.get("to", ""),
                     "direction": t.get("direction") or "forward",
                     "note": t.get("note")}
                    for t in trans],
            }
    return machines


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="blocker", suspected_stage="S0",
                      suspected_files=["nodes/s0_topology.py", "nodes/s2_sorting.py"])
    model = output.get("_model")
    machines = _machines_from_model(model) if model else {}
    if not machines:
        res.skip("no coverage model passed (--model) or no state_info; skipping V08")
        return res
    hygiene = []  # spec 卫生观察（不阻断，汇总进 res.note，正式检查归 spec_lint）

    for key, m in machines.items():
        name = m.get("entity") or key          # C-05: 相位表候选用实体名，非维度限定 key
        pmap = _phase_map(output, m, name)
        derived, anomaly_fw = _derive_phases(m)
        anomaly_fw = set(anomaly_fw)
        if not pmap:
            hygiene.append(f"{name}: output 未找到相位表，整机跳过")
            continue
        max_phase = max(pmap.values())

        # 1. 终态必须处于 output 最大相位
        for st in m.get("terminal_states", []) or []:
            if st in pmap and pmap[st] != max_phase:
                res.fail({"machine": name, "state": st,
                          "reason": "terminal state not at max phase",
                          "phase": pmap[st], "max_phase": max_phase})

        # 2. forward 迁移在 output 相位中必须严格递增
        for t in m.get("transitions", []) or []:
            f, to = t.get("from"), t.get("to")
            if not (isinstance(f, str) and isinstance(to, str)):
                continue
            if f == "(初始)" or to.startswith(_DYNAMIC_PREFIX):
                continue
            d = _direction_of(t)
            if d in _EXEMPT_DIRECTIONS:
                if not t.get("note"):
                    hygiene.append(f"{name}.{t.get('id')}: {d} 迁移缺少 note 依据")
                continue
            if t.get("id") in anomaly_fw:
                hygiene.append(
                    f"{name}.{t.get('id')}: 环状机 forward 边（派生相位不递增），"
                    f"豁免单调检查" + ("" if t.get("note") else "，建议补充 note"))
                continue
            if f in pmap and to in pmap:
                violates = pmap[to] <= pmap[f] if STRICT_FORWARD else pmap[to] < pmap[f]
                if violates:
                    res.fail({"machine": name, "transition": t.get("id"),
                              "from": f, "to": to, "direction": "forward",
                              "phase_from": pmap[f], "phase_to": pmap[to],
                              "reason": "forward transition must increase phase"})

        # 3. 相位坍缩：≥3 个状态不得全部映射到同一相位
        vals = {pmap.get(s) for s in (m.get("states") or []) if s in pmap}
        if len(m.get("states", [])) >= 3 and len(vals) == 1:
            res.fail({"machine": name,
                      "reason": "all states collapsed into one phase; ordering lost"})

    # 4. Type1 用例 post_state 非空
    for p in get_procedures(output):
        if p.get("obligation_type") == ObligationType.TRANSITION and not (p.get("post_state") or "").strip():
            res.fail({"temp_id": p.get("temp_id"), "reason": "Type1 empty post_state"})

    if hygiene:
        res.note = "spec hygiene: " + " | ".join(hygiene[:10])
    return res
