"""V11 聚合门禁镜像(纯结构校验):composition 父容器阶段转换须不早于子记录同动作转换的 from 态相位。

第一性原理:聚合/记录成对动作(如 编制结果报告/通知单 同时落 E-XM.项目状态 与
E-BMJL.报名记录状态)在相位标尺上必须对齐——聚合级转换到达的目标态相位不得低于
子记录同动作转换出发的 from 态相位。否则聚合级用例(编制结果报告)会排到记录级
里程碑(结果已提交)之前,破坏语义先后(如 PROC-068~070 先于 PROC-074~077)。

判别完全基于相位数值(engine_state.phase_table / dep_state_phase_map),不含任何
领域词(不依赖"结果/报告/审核"等状态名):任何实体、任何状态的相位错位都能检出。

豁免(结构性,与领域无关):
- 入口转换:from=该维度 initial(跟踪标尺独立,如通知状态 未发送→待确认);
- 回退/重发边:目标相位 < 来源相位(相位标尺上倒退,如 已审核→待确认),不要求
  对齐记录里程碑,因为那是重发/纠错通道而非新里程碑推进。

缺 --model 或 engine_state 时跳过(无法推导期望相位)。
"""
from collections import defaultdict

from .base import CheckResult

CHECK_ID = "V11"


def _entry_state(state_info: dict, entity: str, dim: str):
    ent = state_info.get(entity) or {}
    for d in ent.get("dimensions", []) or []:
        if d.get("dimension_name") == dim:
            return d.get("initial")
    return None


def _composition_children(model: dict) -> dict:
    """composition 关系:父容器实体 -> 子实体列表。"""
    children = defaultdict(list)
    for rel in (model.get("_context") or {}).get("structural_relations", []) or []:
        if rel.get("relation_type") == "composition":
            children.setdefault(rel.get("from"), []).append(rel.get("to"))
    return dict(children)


def _gate_violations(model: dict, output: dict) -> tuple[list, list]:
    """返回 (违规列表, note 片段列表)。"""
    es = output.get("engine_state") or {}
    pt = es.get("phase_table") or {}
    stp = pt.get("state_to_phase") or {}
    dep = es.get("dep_state_phase_map") or {}
    primary_entity = pt.get("primary_entity", "")
    primary_dim = pt.get("primary_dimension", "")
    tos = model.get("transition_obligations", []) or []
    state_info = (model.get("_context") or {}).get("state_info", {}) or {}
    children = _composition_children(model)

    def phase_of(entity, dim, state):
        if entity == primary_entity:
            tbl = stp.get(dim) or stp.get(primary_dim) or {}
        else:
            tbl = (dep.get(entity) or {}).get(dim) or {}
        return tbl.get(state)

    by_ent_act = defaultdict(list)
    for t in tos:
        by_ent_act[(t.get("entity"), t.get("action"))].append(t)

    fails = []
    for parent in sorted(children):
        for pt_ in tos:
            if pt_.get("entity") != parent:
                continue
            pdim = pt_.get("dimension")
            pfrm = (pt_.get("from") or "").strip()
            pto = (pt_.get("to") or "").strip()
            if not pto or not pdim or not pfrm:
                continue
            entry = _entry_state(state_info, parent, pdim)
            if entry and pfrm == entry:
                continue  # 入口转换:跟踪标尺独立,不参与对齐
            pph_to = phase_of(parent, pdim, pto)
            pph_from = phase_of(parent, pdim, pfrm)
            if pph_to is None or pph_from is None:
                continue
            if pph_to < pph_from:
                continue  # 回退/重发边:相位倒退,不要求对齐记录里程碑
            for child in children[parent]:
                for ct in by_ent_act.get((child, pt_.get("action")), []):
                    cfrm = (ct.get("from") or "").strip()
                    if not cfrm:
                        continue
                    cph = phase_of(child, ct.get("dimension"), cfrm)
                    if cph is None:
                        continue
                    if pph_to < cph:
                        fails.append({
                            "parent_transition": pt_.get("id"),
                            "child_transition": ct.get("id"),
                            "action": pt_.get("action"),
                            "parent_leg": (f"{parent}.{pdim} {pfrm}->{pto} "
                                           f"P{pph_to}"),
                            "child_leg": (f"{child}.{ct.get('dimension')} "
                                          f"from={cfrm} P{cph}"),
                        })
    return fails, [f"composition_pairs={sum(len(v) for v in children.values())}",
                   f"phase_map={len(stp) + len(dep)} dims"]


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="blocker", suspected_stage="P1",
                      suspected_files=["build_obligations.py", "nodes/s0_topology.py"])
    model = output.get("_model")
    if not model:
        res.skip("no coverage model passed (--model); skipping model-derived V11")
        return res
    if not (output.get("engine_state") or {}).get("phase_table"):
        res.skip("output has no engine_state.phase_table; skipping phase-based V11")
        return res

    fails, notes = _gate_violations(model, output)
    for f in fails:
        res.fail(f)
    res.note = " | ".join(notes + [f"gate_mirror_fails={len(fails)}"])
    return res