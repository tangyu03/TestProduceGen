"""模型内确定性推导。与 validate.py 的分工：derive 事前生成，validate 事后兜底。
同一规则两处同源（XC 镜像：这里生成、C04 兜底；BR③：这里生成、C05 校验穿透）。"""
from __future__ import annotations
import re
from .builders import N, precond, state_ref

_STATE_OF = re.compile(r"(?:处于|为)(.{1,10}?)状态")
_CONSTRAINT_WORDS = ("不可", "不得", "禁止", "累计", "按", "计算", "超过", "只能")
_EVENT_WORDS = ("已完成", "已上传", "已启动", "已提交", "已下发")
_CHANGE = re.compile(r"(.{2,8}?)状态?由(.{1,12}?)变为(.{1,12}?)(?=[（(，。；;]|$)")
_FIELD_WORDS = ("长度", "必填", "唯一", "默认", "不超过", "取值范围", "只能由", "验证规则")

def resolve_precondition(model, entity_id, text):
    """4.2.1 判定程序的代码化：state_ref > event_ref > constraint。
    返回 (precond_dict, extra_note)；消歧失败按明文规定降级 constraint。"""
    if any(w in text for w in _CONSTRAINT_WORDS):
        return precond(text, "constraint"), ""
    m = _STATE_OF.search(text)
    if m:
        val = m.group(1)
        hits = [(e["id"], d["dimension_name"]) for e in model.entities
                for d in e["state_dimensions"] if val in d["states"]]
        own = [h for h in hits if h[0] == entity_id]          # 先匹配当前实体
        chosen = own[0] if len(own) == 1 else (hits[0] if len(hits) == 1 else None)
        if chosen:
            return precond(text, "state_ref", state_ref(*chosen, val)), ""
        return precond(text, "constraint"), \
            f"状态值[{val}]匹配多个维度{hits}，无法消歧，降级 constraint（4.2.1）"
    if any(w in text for w in _EVENT_WORDS):
        return precond(text, "event_ref"), ""
    return precond(text, "constraint"), ""

def infer_direction(dim, frm, to, lateral_states=()):
    """4.1 规则②：文档未明确方向时按 states 索引推断。
    返回 None → 调用方按规则③标 inferred:true 并注明依据。"""
    if frm is None:
        return "forward"                                      # C13：创建必须 forward
    if to in lateral_states:
        return "lateral"
    if frm in lateral_states:
        return "resume"
    states = dim["states"]
    if frm in states and to in states:
        return "forward" if states.index(to) > states.index(frm) else "backward"
    return None

def gen_xc_mirrors(model, start_seq=1):
    """Step5 XC 来源①：跨实体 state_ref 前置条件 → 镜像 XC（纯机械生成）。

    与 validate.py C04 同源：覆盖判定按 target_transition（消费者）去重，
    source_transition 反查生产者。本函数当前未被调用，保持与 C04 一致防漂移。
    """
    out, covered = [], {x["target_transition"] for x in model.cross_entity
                        if x.get("target_transition")}
    covered_refs = {(x["source_entity"], x["source_state"], x["target_entity"])
                    for x in model.cross_entity}
    for t in model.transitions:
        if t["id"] in covered:
            continue
        for p in t["preconditions"]:
            if p["type"] == "state_ref" and p.get("ref") \
                    and p["ref"]["entity"] != t["entity"] \
                    and (p["ref"]["entity"], p["ref"]["state"], t["entity"]) \
                        not in covered_refs:
                producer = next((tp["id"] for tp in model.transitions
                                 if tp["entity"] == p["ref"]["entity"]
                                 and tp["dimension"] == p["ref"]["dimension"]
                                 and tp["to"] == p["ref"]["state"]), None)
                out.append({
                    "id": f"XC-{start_seq + len(out):03d}",
                    "source_entity": p["ref"]["entity"],
                    "source_transition": producer or t["id"],
                    "source_state": p["ref"]["state"], "target_entity": t["entity"],
                    "target_transition": t["id"],
                    "target_dimension": t["dimension"],
                    "target_condition": f"状态={t['from']}",
                    "desc": f"precondition'{p['text']}'",
                    "xc_source": "镜像",
                    "source_ref": t["source_ref"]})           # 输入契约：继承宿主
                break
    return out

def gen_field_constraint_brs(model, start_seq=1):
    """Step5 信号③：字段约束属性 → validation BR，desc 复用属性完整约束。"""
    out = []
    for e in model.entities:
        for a in e["attributes"]:
            if any(w in a["desc"] for w in _FIELD_WORDS):
                out.append({"id": f"BR-F{start_seq + len(out):03d}",
                            "category": "validation",
                            "desc": f"{e['name']}.{a['name']}：{a['desc']}",
                            "entities_involved": [e["id"]], "enforcement": "mandatory",
                            "source_ref": "属性定义（字段约束回填）",
                            "signal_type": "field_constraint", "note": N()})
    return out

def derive_causal_from_results(model):
    """4.5 来源2 第1行：T.expected_results 提及他实体状态变化 → 因果候选。
    对当前数据可独立推出 E-PLAN→E-PROJ、E-SCORE→E-PLAN 等，用于与 LLM 产物对账。"""
    names = {e["id"]: e["name"] for e in model.entities}
    out = []
    for t in model.transitions:
        for res in t["expected_results"]:
            m = _CHANGE.search(res)
            if not m:
                continue
            target = next((eid for eid, nm in names.items()
                           if nm in m.group(1) and eid != t["entity"]), None)
            if target:
                out.append({"from": t["entity"], "to": target, "trigger": res,
                            "trigger_source": "expected_results",
                            "evidence_transitions": [t["id"]]})
    return out
