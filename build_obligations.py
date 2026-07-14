#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
覆盖义务建模引擎 - Step 1-5
输入: P1 领域模型 JSON (structured_analysis.json)
输出: 覆盖义务模型 JSON
"""
import json
import re
from itertools import product
from copy import deepcopy

# ============================================================
# 加载 P1
# ============================================================
with open("/home/z/my-project/download/structured_analysis.json", "r", encoding="utf-8") as f:
    P1 = json.load(f)

# ============================================================
# Step 0: 输入校验
# ============================================================
required_roots = [
    "domain_model",
    "domain_model.entities",
    "domain_model.structural_relations",
    "domain_model.transition_relations",
    "state_and_flow.transitions",
    "constraints.cross_entity",
    "constraints.invalid_transitions",
    "constraints.business_rules",
    "_meta.branch_dimensions",
]
def get_nested(obj, path):
    parts = path.split(".")
    cur = obj
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur

missing = [r for r in required_roots if get_nested(P1, r) is None]
if missing:
    print(json.dumps({"error": f"P1 缺失必要根节点: {missing}"}, ensure_ascii=False))
    exit(1)

entities = P1["domain_model"]["entities"]
structural_relations = P1["domain_model"]["structural_relations"]
transition_relations_p1 = P1["domain_model"]["transition_relations"]
transitions_p1 = P1["state_and_flow"]["transitions"]
cross_entity_p1 = P1["constraints"]["cross_entity"]
invalid_transitions_p1 = P1["constraints"]["invalid_transitions"]
business_rules_p1 = P1["constraints"]["business_rules"]
branch_dimensions_p1 = P1["_meta"]["branch_dimensions"]
roles_p1 = P1["domain_model"]["roles"]

# ============================================================
# 工作内存
# ============================================================
entity_by_id = {e["id"]: e for e in entities}
transition_by_id = {t["id"]: t for t in transitions_p1}
to_index = {}          # tid -> TO[] (拆分后)
co_list = []           # [(enabler_entity, dependent_entity, causal_type, co_id)]
xc_status = {}         # xc_id -> "co"|"br"|"skipped"
judgments = []
warnings = {"data_check": [], "step3_1": [], "step3_2": [], "step3_5": []}

# ============================================================
# 辅助函数
# ============================================================
def note(inferred=False, comment="", conflict="", branch_dimension=""):
    return {"inferred": inferred, "comment": comment, "conflict": conflict, "branch_dimension": branch_dimension}

def parse_state(state_str):
    """解析 'dim=val' -> (dim, val)"""
    if not state_str:
        return ("", state_str)
    if "=" in state_str:
        parts = state_str.split("=", 1)
        return (parts[0].strip(), parts[1].strip())
    return ("", state_str)

def clean_state_value(val):
    """清理状态值: '可创建(报名待审核)' -> '报名待审核'"""
    if not val:
        return val
    m = re.search(r"\(([^)]+)\)", val)
    if m:
        return m.group(1).strip()
    # "可推进至待收样" -> "待收样"
    m = re.search(r"可推进至(\S+)", val)
    if m:
        return m.group(1).strip()
    return val.strip()

def get_states(entity_id, dimension):
    """获取实体的某维度的 states"""
    e = entity_by_id.get(entity_id)
    if not e:
        return []
    for sd in e.get("state_dimensions", []):
        if sd["dimension_name"] == dimension:
            return sd["states"]
    return []

def get_all_dimensions(entity_id):
    """获取实体的所有维度名"""
    e = entity_by_id.get(entity_id)
    if not e:
        return []
    return [sd["dimension_name"] for sd in e.get("state_dimensions", [])]

def find_transition_reaching(entity_id, dimension, state):
    """找到 entity_id 的 dimension 维度上 to==state 的转换ID"""
    for t in transitions_p1:
        if t["entity"] == entity_id and t["dimension"] == dimension and t["to"] == state:
            return t["id"]
    return None

def is_config_attr(entity_id, attr_name):
    """检查 attr_name 是否是 entity 的 is_config=true 属性"""
    e = entity_by_id.get(entity_id)
    if not e:
        return False
    for a in e.get("attributes", []):
        if a["name"] == attr_name and a.get("is_config"):
            return True
    return False

def priority_from_p1(p1_priority):
    """P0->critical, P1->high, P2->medium"""
    return {"P0": "critical", "P1": "high", "P2": "medium"}.get(p1_priority, "medium")

def coverage_priority_br(desc, severity, signal_type, category):
    """4.2 coverage_priority 计算"""
    base = "medium"
    if "金额" in (desc or "") or "计算" in (desc or ""):
        base = "high"
    if severity == "conditional":
        base = "low"
    if signal_type == "usability" and desc and any(k in desc for k in ["必填", "标识", "提示"]):
        base = "high"
    if category == "display":
        base = "medium"
    if signal_type == "field_constraint":
        base = "high"
    return base

def category_from_text(text):
    """语义双层: 含显示/展示/统计->display; 含查询/排序/分页/同步/一致/标识/提示->usability; 否则->validation"""
    if not text:
        return "validation"
    display_kw = ["显示", "展示", "统计"]
    usability_kw = ["查询", "排序", "分页", "同步", "一致", "标识", "提示"]
    has_display = any(k in text for k in display_kw)
    has_usability = any(k in text for k in usability_kw)
    if has_display and has_usability:
        return "display"  # 优先级 display>usability>validation
    if has_display:
        return "display"
    if has_usability:
        return "usability"
    return "validation"

# ============================================================
# Step 1: entity_obligations
# ============================================================
entity_obligations = []
eo_counter = 0
for e in entities:
    for attr in e.get("attributes", []):
        if attr.get("is_config"):
            eo_counter += 1
            eo = {
                "id": f"EO-ATC-{eo_counter:03d}",
                "type": "attribute_config",
                "entity": e["id"],
                "entity_name": e["name"],
                "attribute_name": attr["name"],
                "attribute_desc": attr["desc"],
                "dimension": None,
                "from": None,
                "to": None,
                "description": f"覆盖{e['name']}的配置属性{attr['name']}不同取值对流转的影响",
                "suggested_action": f"修改{e['name']}的{attr['name']}，影响{attr['desc'][:60]}",
                "coverage_priority": "medium"
            }
            entity_obligations.append(eo)

# ============================================================
# Step 2: transition_obligations (含 2.5 分支拆分 + 2.6 side_effects)
# ============================================================

# --- 2.5 分支拆分 ---
def get_matched_bds(tid):
    """获取覆盖该 tid 的分支维度"""
    matched = []
    for bd in branch_dimensions_p1:
        if tid in bd.get("coverage", {}).get("transitions", []):
            matched.append(bd)
    return matched

def get_relevant_values(bd, tid):
    """获取 BD 对该 tid 的相关值"""
    branch_vals = []
    for br in bd.get("branches", []):
        if br.get("target_transition") == tid:
            branch_vals.append(br["value"])
    if branch_vals:
        return branch_vals
    return bd.get("values", [])

def build_branch_combos(tid):
    """为 tid 构建分支组合"""
    t = transition_by_id.get(tid)
    if not t:
        return [([], None)]  # 无拆分
    
    matched_bds = get_matched_bds(tid)
    note_bd = t.get("note", {}).get("branch_dimension", "")
    
    # 2.5a: matched_dims 非空
    if matched_bds:
        dim_values = []
        for bd in matched_bds:
            vals = get_relevant_values(bd, tid)
            dim_values.append((bd["dimension"], vals, bd))
        # 过滤: 某value下转换不存在则不为该value生成 (语义判断)
        # 对评价人员角色维度, T-093/T-094 仅评价组长执行
        filtered_dv = []
        for dim, vals, bd in dim_values:
            if dim == "评价人员角色" and tid in ["T-093", "T-094"]:
                if "评价组长" in vals:
                    vals = ["评价组长"]
                    judgments.append({
                        "rule_point": "2.5a-值过滤",
                        "basis": "某value下转换不存在则不为该value生成",
                        "evidence": [f"{tid}为评价组长专属操作(确认/退回修改), 评价成员不执行"],
                        "affected_id": tid,
                        "decision": f"过滤{dim}至[评价组长]"
                    })
            filtered_dv.append((dim, vals))
        combos = list(product(*[[(d, v) for v in vs] for d, vs in filtered_dv]))
        if len(combos) > 16:
            warnings["data_check"].append(f"{tid} 笛卡尔积组合数>{len(combos)} 降级不拆分")
            return [([], None)]
        if not combos:
            combos = [()]
        result = []
        for combo in combos:
            result.append((list(combo), "2.5a"))
        return result
    
    # 2.5b/2.5c: note.branch_dimension 非空且 tid ∉ BD.coverage
    if note_bd and not matched_bds:
        # 找到对应的 BD
        bd = None
        for b in branch_dimensions_p1:
            if b["dimension"] == note_bd:
                bd = b
                break
        if bd:
            vals = bd.get("values", [])
            dim = bd["dimension"]
            combos = list(product(*[[(dim, v) for v in vals]]))
            result = []
            for combo in combos:
                result.append((list(combo), "2.5b"))
            return result
        return [([], None)]
    
    # 无拆分
    return [([], None)]

def split_transition(t):
    """拆分转换, 返回 TO 列表"""
    tid = t["id"]
    combos = build_branch_combos(tid)
    
    result = []
    for idx, (combo, split_rule) in enumerate(combos):
        suffix = ""
        if combo:  # 有分支组合
            suffix = chr(ord('a') + idx) if idx < 26 else f"-{idx+1}"
        
        new_id = f"{tid}{suffix}" if suffix else tid
        branch_path = [{"dimension": d, "value": v} for d, v in combo]
        
        # action 标注组合值
        action = t["action"]
        if combo:
            combo_desc = ", ".join(f"{d}={v}" for d, v in combo)
            action = f"{t['action']} [{combo_desc}]"
        
        # preconditions/expected_results 按组合细化 (简单追加组合描述)
        preconditions = list(t.get("preconditions", []))
        expected_results = list(t.get("expected_results", []))
        
        # 2.2 coverage_priority
        p1_pri = t.get("priority", "P2")
        cov_pri = priority_from_p1(p1_pri)
        # 判断 from 是否为终态
        from_is_terminal = False
        to_is_terminal = False
        e = entity_by_id.get(t["entity"])
        if e and t.get("dimension"):
            for sd in e.get("state_dimensions", []):
                if sd["dimension_name"] == t["dimension"]:
                    if t.get("from") in sd.get("terminal", []):
                        from_is_terminal = True
                    if t.get("to") in sd.get("terminal", []):
                        to_is_terminal = True
                    break
        # base 升级规则
        if t.get("from") is None or to_is_terminal:
            cov_pri = "critical"
        # 例外(P2调整点1): inferred=True AND from∈terminal → 降级为 medium
        is_inferred = t.get("note", {}).get("inferred", False)
        if is_inferred and from_is_terminal:
            cov_pri = "medium"
            warnings["data_check"].append(
                f"2.2 {tid}: inferred=True AND from={t.get('from')}(终态) → coverage_priority 降级为 medium")
        
        # 2.3 risk_traits
        risk_traits = list(t.get("traits", []))
        
        # 2.4 is_repeatable
        is_repeatable = (t.get("from") == t.get("to")) and t.get("from") is not None
        repeat_condition = None
        if is_repeatable:
            repeat_condition = t.get("note", {}).get("comment", "") or f"from==to=={t['from']}"
        
        # 2.6 side_effects
        side_effects = []
        # 渠道1: transition_relations 中 from==当前entity 且 evidence含tid
        for R in transition_relations_p1:
            if R["from"] == t["entity"] and tid in R.get("evidence_transitions", []):
                target_e = R["to"]
                # 找 target 的维度
                target_dims = get_all_dimensions(target_e)
                target_dim = target_dims[0] if target_dims else ""
                side_effects.append({
                    "target_entity": target_e,
                    "target_dimension": target_dim,
                    "effect_desc": R.get("desc", "")
                })
        # 渠道2: 扫描 expected_results 中其他实体状态变更
        for er in t.get("expected_results", []):
            for other_e in entities:
                if other_e["id"] == t["entity"]:
                    continue
                # 检查 expected_results 是否提及其他实体的状态变更
                for sd in other_e.get("state_dimensions", []):
                    dim_name = sd["dimension_name"]
                    if dim_name in er and ("变为" in er or "推进" in er or "创建" in er or "生成" in er):
                        # 去重
                        exists = any(se["target_entity"] == other_e["id"] and se["target_dimension"] == dim_name for se in side_effects)
                        if not exists:
                            side_effects.append({
                                "target_entity": other_e["id"],
                                "target_dimension": dim_name,
                                "effect_desc": er
                            })
        
        # note
        t_note = t.get("note", {})
        new_note = {
            "inferred": t_note.get("inferred", False),
            "comment": t_note.get("comment", ""),
            "conflict": t_note.get("conflict", ""),
            "branch_dimension": t_note.get("branch_dimension", "") if not combo else ", ".join(d for d, v in combo)
        }
        
        to = {
            "id": new_id,
            "type": "transition_obligation",
            "transition_id": tid,
            "entity": t["entity"],
            "dimension": t["dimension"],
            "from": t["from"],
            "to": t["to"],
            "action": action,
            "role": t["role"],
            "coverage_priority": cov_pri,
            "preconditions": preconditions,
            "expected_results": expected_results,
            "source_ref": t.get("source_ref", ""),
            "risk_traits": risk_traits,
            "is_repeatable": is_repeatable,
            "repeat_condition": repeat_condition,
            "branch_path": branch_path,
            "side_effects": side_effects,
            "note": new_note,
            "sub_steps": t.get("sub_steps", []),
            "suggested_action": None
        }
        result.append(to)
    
    return result

# 生成所有 TO
transition_obligations = []
for t in transitions_p1:
    tos = split_transition(t)
    transition_obligations.extend(tos)

# 构建 to_index
for to in transition_obligations:
    tid = to["transition_id"]
    if tid not in to_index:
        to_index[tid] = []
    to_index[tid].append(to)

# 2.5d 补充归属: 遍历 branch_path=[] 的 TO
for to in transition_obligations:
    if to["branch_path"]:
        continue
    tid = to["transition_id"]
    t = transition_by_id.get(tid)
    if not t or t.get("from") is None:
        continue
    # ① from 状态的所有入边 TO 的 branch_path 非空且指向同一组合
    incoming = [ito for ito in transition_obligations 
                if ito["entity"] == to["entity"] and ito["dimension"] == to["dimension"] 
                and ito["to"] == to["from"] and ito["branch_path"]]
    if incoming:
        combos_set = set(tuple((bp["dimension"], bp["value"]) for bp in ito["branch_path"]) for ito in incoming)
        if len(combos_set) == 1:
            to["branch_path"] = incoming[0]["branch_path"]
            continue
    # ② preconditions 显式引用某分支维度值
    for bd in branch_dimensions_p1:
        for br in bd.get("branches", []):
            for pre in to["preconditions"]:
                if br["value"] in pre and bd["dimension"] in pre:
                    to["branch_path"] = [{"dimension": bd["dimension"], "value": br["value"]}]
                    break

# --- 2.7 异常检测 (P2调整点2, 在 2.5d 之后执行) ---
for to in transition_obligations:
    tid = to["transition_id"]
    e = entity_by_id.get(to["entity"])
    from_is_term = False
    to_is_term = False
    if e and to.get("dimension"):
        for sd in e.get("state_dimensions", []):
            if sd["dimension_name"] == to["dimension"]:
                from_is_term = to.get("from") in sd.get("terminal", [])
                to_is_term = to.get("to") in sd.get("terminal", [])
                break
    is_inferred = to.get("note", {}).get("inferred", False)
    has_rollback = "rollback" in to.get("risk_traits", [])
    
    # ① from∈terminal AND to∈terminal → 降级为 low
    if from_is_term and to_is_term:
        to["coverage_priority"] = "low"
        warnings["data_check"].append(
            f"2.7 {to['id']}: from={to.get('from')}(终态) to={to.get('to')}(终态) → 终态→终态异常, 降级为 low")
    # ② inferred=True AND from∈terminal → 降级为 medium (2.2已处理, 此处补充warning)
    elif is_inferred and from_is_term:
        if to["coverage_priority"] != "medium":
            to["coverage_priority"] = "medium"
        warnings["data_check"].append(
            f"2.7 {to['id']}: inferred=True AND from={to.get('from')}(终态) → 推断终态出边, 降级为 medium")
    # ③ traits含rollback AND from∈terminal → warning
    if has_rollback and from_is_term:
        warnings["data_check"].append(
            f"2.7 {to['id']}: traits含rollback AND from={to.get('from')}(终态) → 终态不应有rollback出边")

# ============================================================
# Step 3: cross_entity_obligations
# ============================================================
cross_entity_obligations = []
co_counter = 0

def next_co_id():
    global co_counter
    co_counter += 1
    return f"CO-{co_counter:03d}"

# --- 3.1 C1 显式约束 ---
for xc in cross_entity_p1:
    xc_id = xc["id"]
    desc = xc.get("desc", "")
    source_entity = xc["source_entity"]
    source_transition = xc["source_transition"]
    source_state = xc["source_state"]
    target_entity = xc["target_entity"]
    target_dimension = xc.get("target_dimension", "")
    target_condition = xc.get("target_condition", "")
    
    # 判断 XC 类型
    is_mirror = desc.startswith("镜像") or "镜像" in desc[:10]
    is_linkage = desc.startswith("联动") or "联动" in desc[:10]
    is_step46 = "Step 4.6" in desc
    is_branch = desc.startswith("分支") or "分支[" in desc[:10]
    
    # 确定语义: enabler = gate state, dependent = gated transition
    # 镜像 type: enabler=source_entity.source_state, dependent=source_transition (on target_entity)
    # 联动 type: enabler=source_entity.source_state (source_transition), dependent=target_entity.target_condition
    
    if is_mirror:
        enabler_entity = source_entity
        enabler_dim_val = parse_state(source_state)
        enabler_dimension = enabler_dim_val[0]
        enabler_state = enabler_dim_val[1]
        dependent_entity = target_entity
        dependent_transition_id = source_transition
        dependent_dimension = target_dimension
        dependent_condition = clean_state_value(target_condition)
    elif is_linkage or is_step46:
        enabler_entity = source_entity
        enabler_transition_id = source_transition
        # 从 source_transition 获取 enabler dimension/state
        enabler_to = to_index.get(source_transition, [{}])[0]
        enabler_dimension = enabler_to.get("dimension", "")
        enabler_state = enabler_to.get("to", "")
        dependent_entity = target_entity
        dependent_dimension = target_dimension
        dependent_condition = clean_state_value(target_condition)
        # 找 dependent transition
        dependent_transition_id = find_transition_reaching(target_entity, target_dimension, dependent_condition)
    else:
        # 分支 type 或其他
        enabler_entity = source_entity
        enabler_dim_val = parse_state(source_state) if source_state else ("", "")
        enabler_dimension = enabler_dim_val[0]
        enabler_state = enabler_dim_val[1]
        dependent_entity = target_entity
        dependent_transition_id = source_transition
        dependent_dimension = target_dimension
        dependent_condition = clean_state_value(target_condition)
    
    # --- 统一门禁 G1-G6 ---
    skip_reason = None
    
    # G1: enabler_dimension ∈ config attrs
    if enabler_dimension and is_config_attr(enabler_entity, enabler_dimension):
        skip_reason = "G1: enabler_dimension为配置属性"
    
    # G2: enabler_dimension/state + dependent_dimension/condition 均无法提取
    if not skip_reason:
        if (not enabler_dimension and not enabler_state) or (not target_dimension and not target_condition):
            skip_reason = "G2: enabler或dependent维度/状态无法提取"
    
    # G3: dependent TO 所有 from==null
    if not skip_reason and dependent_transition_id:
        dep_tos = to_index.get(dependent_transition_id, [])
        if dep_tos and all(dto["from"] is None for dto in dep_tos):
            skip_reason = "G3: dependent转换所有TO.from==null(创建型转换)"
    elif not skip_reason and not dependent_transition_id:
        if not (is_mirror and source_transition):
            skip_reason = "G3: dependent_transition_id为空"
    
    # G5: enabler_state 非枚举状态值
    if not skip_reason and enabler_state:
        states = get_states(enabler_entity, enabler_dimension)
        if states and enabler_state not in states:
            # 语义双层: 上下文推断
            cleaned = clean_state_value(enabler_state)
            if cleaned in states:
                enabler_state = cleaned
                judgments.append({
                    "rule_point": "G5-状态推断",
                    "basis": "enabler_state非枚举值, 上下文推断清理",
                    "evidence": [f"原始={enabler_state}, 清理后={cleaned}, ∈{states}"],
                    "affected_id": xc_id,
                    "decision": f"修正enabler_state为{cleaned}"
                })
            else:
                # 查 enabler_entity 中哪个 dimension 含该 state
                found_dim = None
                for sd in entity_by_id.get(enabler_entity, {}).get("state_dimensions", []):
                    if cleaned in sd["states"]:
                        found_dim = sd["dimension_name"]
                        break
                if found_dim:
                    enabler_dimension = found_dim
                    enabler_state = cleaned
                    judgments.append({
                        "rule_point": "G5-维度修正",
                        "basis": "enabler_state非当前维度枚举, 查其他维度",
                        "evidence": [f"在{enabler_entity}.{found_dim}找到{cleaned}"],
                        "affected_id": xc_id,
                        "decision": f"修正enabler_dimension为{found_dim}"
                    })
                else:
                    skip_reason = f"G5: enabler_state={enabler_state}非合法枚举状态"
    
    # G4 不适用于 3.1
    
    if skip_reason:
        # 跳过后处理: 转 BR
        xc_status[xc_id] = "br"
        warnings["step3_1"].append(f"{xc_id} 跳过: {skip_reason}")
        continue
    
    # 通过门禁, 生成 CO
    # 找 enabler_transition_id (镜像 type 需查找)
    if is_mirror:
        enabler_transition_id = find_transition_reaching(enabler_entity, enabler_dimension, enabler_state)
    
    # 找 dependent TO 信息
    dep_tos = to_index.get(dependent_transition_id, [])
    dep_to = dep_tos[0] if dep_tos else {}
    # 仅当 dependent transition 的 entity 与 dependent_entity 一致时才覆盖 dimension
    # (镜像 type 中 source_transition 可能在 enabler_entity 上, 不应覆盖)
    if dep_to and dep_to.get("entity") == dependent_entity:
        if not dependent_dimension:
            dependent_dimension = dep_to.get("dimension", dependent_dimension)
        if not dependent_condition:
            dependent_condition = dep_to.get("to", "")
    elif dep_to and dep_to.get("entity") != dependent_entity:
        # source_transition 在 enabler_entity 上(镜像type跨实体), 保持 target_dimension/condition
        judgments.append({
            "rule_point": "3.1-镜像跨实体维度保持",
            "basis": "镜像type中source_transition可能在enabler_entity上, dependent_dimension应取target_dimension",
            "evidence": [f"{dependent_transition_id}.entity={dep_to.get('entity')} != dependent_entity={dependent_entity}, 保持target_dimension={target_dimension}"],
            "affected_id": xc_id,
            "decision": f"dependent_dimension={target_dimension}, dependent_condition={dependent_condition}"
        })
    
    # aggregation
    aggregation = None
    # 检查 structural_relations 中 enabler->dependent 是否 1:N composition
    for sr in structural_relations:
        if sr["from"] == enabler_entity and sr["to"] == dependent_entity:
            if sr["cardinality"] == "1:N" and sr["relation_type"] == "composition":
                aggregation = "all"
            break
    
    # coverage_priority: 取 dependent TO 的 priority (多条取最高)
    cov_pri = "medium"
    if dep_tos:
        pri_order = {"critical": 0, "high": 1, "medium": 2}
        cov_pri = min((dto["coverage_priority"] for dto in dep_tos), key=lambda p: pri_order.get(p, 3))
    
    # roles
    enabler_role = None
    if enabler_transition_id:
        enab_tos = to_index.get(enabler_transition_id, [])
        if enab_tos:
            r = enab_tos[0].get("role")
            enabler_role = r if r != "system" else None
    dependent_role = dep_to.get("role") if dep_to else None
    if dependent_role == "system":
        dependent_role = None
    
    # ref_to: dependent TO preconditions 含 enabler_state 引用
    ref_to = None
    if dep_to:
        pres = dep_to.get("preconditions", [])
        for pre in pres:
            if enabler_state and enabler_state in pre:
                ref_to = {
                    "obligation_type": "transition_obligation",
                    "obligation_id": dependent_transition_id,
                    "relation": "precondition_reference",
                    "detail": [pre]
                }
                break
    
    # desc
    desc_str = f"{enabler_entity}.{enabler_dimension}={enabler_state} 是 {dependent_entity}.{dependent_dimension} 推进至 {dependent_condition} 的前置条件"
    
    # suggested_action
    if aggregation == "all":
        sa = f"所有{enabler_entity}的{enabler_dimension}达到{enabler_state}是{dependent_entity}的{dependent_dimension}推进至{dependent_condition}的前置门禁"
    else:
        sa = f"{enabler_entity}的{enabler_dimension}达到{enabler_state}是{dependent_entity}的{dependent_dimension}推进至{dependent_condition}的前置门禁"
    
    co_id = next_co_id()
    co = {
        "id": co_id,
        "type": "cross_entity",
        "constraint_id": xc_id,
        "causal_type": "constraint",
        "enabler_entity": enabler_entity,
        "enabler_transition_id": enabler_transition_id,
        "enabler_dimension": enabler_dimension,
        "enabler_state": enabler_state,
        "dependent_entity": dependent_entity,
        "dependent_transition_id": dependent_transition_id,
        "dependent_dimension": dependent_dimension,
        "dependent_condition": dependent_condition,
        "aggregation": aggregation,
        "ref_to": ref_to,
        "trigger": None,
        "trigger_source": None,
        "rollback_propagation": False,
        "confidence": "high",
        "desc": desc_str,
        "coverage_priority": cov_pri,
        "enabler_role": enabler_role,
        "dependent_role": dependent_role,
        "suggested_action": sa,
        "merged_from": []
    }
    cross_entity_obligations.append(co)
    co_list.append((enabler_entity, dependent_entity, "constraint", co_id))
    xc_status[xc_id] = "co"

# --- 3.2 C1-auto ---
for R in transition_relations_p1:
    r_from = R["from"]
    r_to = R["to"]
    evidence = R.get("evidence_transitions", [])
    
    # 从 evidence 取 enabler端(R.from) 和 dependent端(R.to) 转换
    enabler_tids = [tid for tid in evidence if transition_by_id.get(tid, {}).get("entity") == r_from]
    dependent_tids = [tid for tid in evidence if transition_by_id.get(tid, {}).get("entity") == r_to]
    
    # G6: 同一 transition_relation (按evidence_transitions唯一标识) 已生成 3.2 CO
    already_co_32 = False
    r_evidence_key = tuple(sorted(evidence))
    for co in cross_entity_obligations:
        if co.get("constraint_id") is None and co.get("trigger_source") == R.get("trigger_source"):
            # 检查是否同一 R (evidence相同)
            co_ev = co.get("_r_evidence_key")
            if co_ev == r_evidence_key:
                already_co_32 = True
                break
    if already_co_32:
        warnings["step3_2"].append(f"R({r_from}->{r_to}) G6: 同一R(evidence相同)已生成3.2 CO, 跳过")
        continue
    
    if not enabler_tids:
        warnings["step3_2"].append(f"R({r_from}->{r_to}) 无enabler端转换, 跳过")
        continue
    if not dependent_tids:
        warnings["step3_2"].append(f"R({r_from}->{r_to}) 无dependent端转换, 跳过")
        continue
    
    enabler_tid = enabler_tids[0]
    dependent_tid = dependent_tids[0]
    
    # G3: dependent TO 所有 from==null
    dep_tos = to_index.get(dependent_tid, [])
    if dep_tos and all(dto["from"] is None for dto in dep_tos):
        warnings["step3_2"].append(f"R({r_from}->{r_to}) G3: dependent转换{dependent_tid}所有TO.from==null, 跳过")
        continue
    
    enab_tos = to_index.get(enabler_tid, [])
    enab_to = enab_tos[0] if enab_tos else {}
    enabler_dimension = enab_to.get("dimension", "")
    enabler_state = enab_to.get("to", "")
    
    # G1: enabler_dimension 为 config
    if enabler_dimension and is_config_attr(r_from, enabler_dimension):
        warnings["step3_2"].append(f"R({r_from}->{r_to}) G1: enabler_dimension={enabler_dimension}为配置属性, 跳过")
        continue
    
    # G2
    if not enabler_dimension or not enabler_state:
        warnings["step3_2"].append(f"R({r_from}->{r_to}) G2: enabler维度/状态无法提取, 跳过")
        continue
    
    # G5: enabler_state 非枚举
    states = get_states(r_from, enabler_dimension)
    if states and enabler_state not in states:
        warnings["step3_2"].append(f"R({r_from}->{r_to}) G5: enabler_state={enabler_state}非枚举, 跳过")
        continue
    
    # 通过门禁, 生成 CO
    dep_to = dep_tos[0] if dep_tos else {}
    dependent_dimension = dep_to.get("dimension", "")
    dependent_condition = dep_to.get("to", "")
    
    # aggregation
    aggregation = None
    for sr in structural_relations:
        if sr["from"] == r_from and sr["to"] == r_to:
            if sr["cardinality"] == "1:N" and sr["relation_type"] == "composition":
                aggregation = "all"
            break
    
    # coverage_priority
    trigger_source = R.get("trigger_source", "")
    rollback = R.get("rollback_propagation", False)
    confidence = R.get("confidence", "high")
    cov_pri = "high"
    if trigger_source == "bidi_coupling":
        cov_pri = "critical"
    if rollback:
        cov_pri = "critical"
    if confidence in ["low", "medium"]:
        cov_pri = "high" if cov_pri != "critical" else cov_pri
    if not evidence:
        cov_pri = "medium"
        confidence = "low"
    
    # roles
    enabler_role = enab_to.get("role") if enab_to else None
    if enabler_role == "system":
        enabler_role = None
    dependent_role = dep_to.get("role") if dep_to else None
    if dependent_role == "system":
        dependent_role = None
    
    # ref_to
    ref_to = None
    if dep_to:
        for pre in dep_to.get("preconditions", []):
            if enabler_state in pre:
                ref_to = {
                    "obligation_type": "transition_obligation",
                    "obligation_id": dependent_tid,
                    "relation": "precondition_reference",
                    "detail": [pre]
                }
                break
    
    desc_str = f"{r_from}.{enabler_dimension}={enabler_state} 是 {r_to}.{dependent_dimension} 推进至 {dependent_condition} 的前置条件"
    sa = f"{r_from}的{enabler_dimension}达到{enabler_state}是{r_to}的{dependent_dimension}推进至{dependent_condition}的前置门禁"
    
    co_id = next_co_id()
    co = {
        "id": co_id,
        "type": "cross_entity",
        "constraint_id": None,
        "causal_type": "constraint",
        "enabler_entity": r_from,
        "enabler_transition_id": enabler_tid,
        "enabler_dimension": enabler_dimension,
        "enabler_state": enabler_state,
        "dependent_entity": r_to,
        "dependent_transition_id": dependent_tid,
        "dependent_dimension": dependent_dimension,
        "dependent_condition": dependent_condition,
        "aggregation": aggregation,
        "ref_to": ref_to,
        "trigger": R.get("trigger"),
        "trigger_source": trigger_source,
        "rollback_propagation": rollback,
        "confidence": confidence,
        "desc": desc_str,
        "coverage_priority": cov_pri,
        "enabler_role": enabler_role,
        "dependent_role": dependent_role,
        "suggested_action": sa,
        "merged_from": [],
        "_r_evidence_key": r_evidence_key  # 内部字段, 输出前删除
    }
    cross_entity_obligations.append(co)
    co_list.append((r_from, r_to, "constraint", co_id))

# --- 3.3 lifecycle 1:1 (创建同步性感知, 仅安全网①②) ---
# P1 Step 2.3 三元分类已将"事件触发归属"类关系标为 reference + configuration_source,
# 不会进入本步 composition 流程。本前置过滤作为安全网, 防止 P1 误判时 P2 仍能拦截。
for sr in structural_relations:
    if (sr["relation_type"] == "composition" 
        and sr.get("ownership_dimension") == "business_ownership"
        and sr["cardinality"] == "1:1"
        and sr["relation_type"] != "self_reference"
        and sr["from"] != sr["to"]):
        
        from_e = sr["from"]
        to_e = sr["to"]
        
        # 前置过滤①(安全网): dependent_entity.state_dimensions 为空 → 跳过
        # (无法判定生命周期同步语义, B 无状态维度意味着无独立生命周期可同步)
        to_entity = entity_by_id.get(to_e)
        if to_entity and not to_entity.get("state_dimensions"):
            warnings["step3_5"].append(
                f"3.3 lifecycle {from_e}->{to_e} 跳过(安全网①): dependent_entity.state_dimensions 为空, 无法判定生命周期同步语义")
            continue
        
        # 前置过滤②(安全网): dependent 创建转换(from==null)的 preconditions 引用 enabler 之外实体的状态
        #   且引用的是 enabler 的后期状态(非 initial) → 跳过
        #   (B 的创建由 enabler 后期事件触发, 非随 A 创建自动产生, 实为"事件触发归属"类)
        to_creation_t = None
        for t in transitions_p1:
            if t["entity"] == to_e and t.get("from") is None:
                to_creation_t = t
                break
        if to_creation_t:
            pres = to_creation_t.get("preconditions", [])
            # 检查是否引用 enabler(from_e) 的后期状态
            from_entity = entity_by_id.get(from_e)
            if from_entity:
                from_states_all = set()
                from_initial = None
                for sd in from_entity.get("state_dimensions", []):
                    from_states_all.update(sd.get("states", []))
                    if sd.get("initial"):
                        from_initial = sd["initial"]
                for pre in pres:
                    if from_e in pre:
                        for state in from_states_all:
                            if state in pre and state != from_initial:
                                warnings["step3_5"].append(
                                    f"3.3 lifecycle {from_e}->{to_e} 跳过(安全网②): dependent创建转换{to_creation_t['id']} preconditions 引用 enabler 后期状态[{state}], 实为事件触发非 lifecycle cascade")
                                to_creation_t = None  # 标记跳过
                                break
                    if to_creation_t is None:
                        break
            if to_creation_t is None:
                continue
        
        # 找创建转换 (from==null)
        from_creation = None
        for t in transitions_p1:
            if t["entity"] == from_e and t.get("from") is None:
                from_creation = t["id"]
                break
        to_creation = None
        for t in transitions_p1:
            if t["entity"] == to_e and t.get("from") is None:
                to_creation = t["id"]
                break
        
        # dimension/state/condition
        from_dim = ""
        from_state = ""
        if from_creation:
            ft = to_index.get(from_creation, [{}])[0]
            from_dim = ft.get("dimension", "")
            from_state = ft.get("to", "")
        else:
            # initial state
            for sd in entity_by_id.get(from_e, {}).get("state_dimensions", []):
                from_dim = sd["dimension_name"]
                from_state = sd["initial"]
                break
        
        to_dim = ""
        to_state = ""
        if to_creation:
            tt = to_index.get(to_creation, [{}])[0]
            to_dim = tt.get("dimension", "")
            to_state = tt.get("to", "")
        else:
            for sd in entity_by_id.get(to_e, {}).get("state_dimensions", []):
                to_dim = sd["dimension_name"]
                to_state = sd["initial"]
                break
        
        # roles
        from_role = None
        if from_creation:
            ft = to_index.get(from_creation, [{}])[0]
            r = ft.get("role")
            from_role = r if r != "system" else None
        to_role = None
        if to_creation:
            tt = to_index.get(to_creation, [{}])[0]
            r = tt.get("role")
            to_role = r if r != "system" else None
        
        co_id = next_co_id()
        co = {
            "id": co_id,
            "type": "cross_entity",
            "constraint_id": None,
            "causal_type": "lifecycle",
            "enabler_entity": from_e,
            "enabler_transition_id": from_creation,
            "enabler_dimension": from_dim,
            "enabler_state": from_state,
            "dependent_entity": to_e,
            "dependent_transition_id": to_creation,
            "dependent_dimension": to_dim,
            "dependent_condition": to_state,
            "aggregation": None,
            "ref_to": None,
            "trigger": None,
            "trigger_source": None,
            "rollback_propagation": False,
            "confidence": "high",
            "desc": f"{from_e}与{to_e}一对一绑定，创建/删除同步",
            "coverage_priority": "high",
            "enabler_role": from_role,
            "dependent_role": to_role,
            "suggested_action": f"在{from_e}创建/删除时，{to_e}同步创建/删除",
            "merged_from": []
        }
        cross_entity_obligations.append(co)
        co_list.append((from_e, to_e, "lifecycle", co_id))

# --- 3.4 去重 ---
def co_signature(co):
    return (co["enabler_entity"], co["enabler_dimension"], co["enabler_state"],
            co["dependent_entity"], co["dependent_dimension"], co["dependent_condition"],
            co["causal_type"])

seen_sigs = {}
to_remove = []
for co in cross_entity_obligations:
    sig = co_signature(co)
    if sig in seen_sigs:
        # 去重, 合并到先生成版本
        keeper = seen_sigs[sig]
        # 合并 trigger/trigger_source
        if not keeper.get("trigger") and co.get("trigger"):
            keeper["trigger"] = co["trigger"]
        if not keeper.get("trigger_source") and co.get("trigger_source"):
            keeper["trigger_source"] = co["trigger_source"]
        # rollback
        if not keeper.get("rollback_propagation") and co.get("rollback_propagation"):
            keeper["rollback_propagation"] = True
        # confidence 取更高
        conf_order = {"high": 0, "medium": 1, "low": 2}
        if conf_order.get(co.get("confidence", "high"), 0) < conf_order.get(keeper.get("confidence", "high"), 0):
            keeper["confidence"] = co["confidence"]
        # merged_from
        keeper["merged_from"].append(co["id"])
        to_remove.append(co)
    else:
        seen_sigs[sig] = co

# 同实体跨维度去重: enabler==dependent AND constraint AND desc可由dependent TO的preconditions完全推出
for co in cross_entity_obligations:
    if co in to_remove:
        continue
    if (co["causal_type"] == "constraint" 
        and co["enabler_entity"] == co["dependent_entity"]
        and co["enabler_dimension"] != co["dependent_dimension"]):
        # 检查 dependent TO preconditions 是否含 enabler_state
        dep_tid = co["dependent_transition_id"]
        if dep_tid:
            dep_tos = to_index.get(dep_tid, [])
            if dep_tos:
                pres = dep_tos[0].get("preconditions", [])
                if any(co["enabler_state"] in pre for pre in pres):
                    judgments.append({
                        "rule_point": "3.4-同实体跨维度去重",
                        "basis": "enabler==dependent AND constraint AND desc可由dependent TO的preconditions完全推出",
                        "evidence": [f"{co['id']} enabler_state={co['enabler_state']} 在 {dep_tid} preconditions 中"],
                        "affected_id": co["id"],
                        "decision": "可去重但保留用于XC溯源"
                    })

cross_entity_obligations = [co for co in cross_entity_obligations if co not in to_remove]

# --- 3.5 生成后校验 ---
for co in cross_entity_obligations:
    # 1. 方向: dependent TO.preconditions 应引用 enabler 侧
    if co["causal_type"] == "constraint" and co["dependent_transition_id"]:
        dep_tos = to_index.get(co["dependent_transition_id"], [])
        if dep_tos:
            pres = dep_tos[0].get("preconditions", [])
            enabler_ref = any(co["enabler_state"] in pre for pre in pres)
            if not enabler_ref and co["enabler_state"]:
                warnings["step3_5"].append(
                    f"{co['id']} 方向: dependent {co['dependent_transition_id']} preconditions 未引用 enabler_state={co['enabler_state']}"
                )
    # 2. 自循环: suggested_action 禁止引用 dependent_transition 的 action 名
    if co["dependent_transition_id"]:
        dep_t = transition_by_id.get(co["dependent_transition_id"], {})
        dep_action = dep_t.get("action", "")
        if dep_action and dep_action in (co.get("suggested_action") or ""):
            warnings["step3_5"].append(
                f"{co['id']} 自循环: suggested_action 引用了 dependent action='{dep_action}'"
            )

# 3. (E,D,S) 复查: enabler_state ∈ states[] 或有 judgment
for co in cross_entity_obligations:
    if co["causal_type"] in ("constraint", "lifecycle") and co["enabler_state"]:
        states = get_states(co["enabler_entity"], co["enabler_dimension"])
        if states and co["enabler_state"] not in states:
            has_judgment = any(j["affected_id"] == (co.get("constraint_id") or co["id"]) for j in judgments)
            if not has_judgment:
                warnings["step3_5"].append(
                    f"{co['id']} (E,D,S)复查: enabler_state={co['enabler_state']} 不在 {co['enabler_entity']}.{co['enabler_dimension']}.states")

# 4. lifecycle 创建同步性复核: 对每个 causal_type=lifecycle 的 CO,
#    验证 dependent 创建转换的 preconditions 是否仅引用 enabler 实体本身;
#    若引用其他实体的后期状态 → warning (P1 可能误判, 建议 P1 复核)
for co in cross_entity_obligations:
    if co["causal_type"] != "lifecycle":
        continue
    dep_tid = co["dependent_transition_id"]
    if not dep_tid:
        continue
    dep_tos = to_index.get(dep_tid, [])
    if not dep_tos:
        continue
    pres = dep_tos[0].get("preconditions", [])
    enabler_e = co["enabler_entity"]
    # 检查 preconditions 是否引用 enabler 之外实体的状态
    for pre in pres:
        for other_e in entities:
            if other_e["id"] != enabler_e and other_e["id"] != co["dependent_entity"] and other_e["id"] in pre:
                warnings["step3_5"].append(
                    f"{co['id']} lifecycle 创建同步性复核: dependent创建转换{dep_tid} preconditions 引用 enabler 之外实体 {other_e['id']}, P1 可能误判, 建议 P1 复核")
                break

# ============================================================
# Step 4: constraint_obligations
# ============================================================
constraint_obligations = []

# --- 4.1 invalid_transition ---
it_counter = 0
for it in invalid_transitions_p1:
    it_counter += 1
    ro_it = {
        "id": f"RO-IT-{it_counter:03d}",
        "type": "invalid_transition",
        "constraint_id": it["id"],
        "entity": it["entity"],
        "dimension": "",
        "from": it["from"],
        "to": it["to"],
        "reason": it["reason"],
        "coverage_priority": "high",
        "suggested_action": f"在{it['entity']}处于{it['from']}状态时，执行{it['to']}操作"
    }
    # 尝试匹配 dimension
    for sd in entity_by_id.get(it["entity"], {}).get("state_dimensions", []):
        if it["from"] in sd["states"] or it["to"] in sd["states"]:
            ro_it["dimension"] = sd["dimension_name"]
            break
    constraint_obligations.append(ro_it)

# --- 4.2 business_rule ---
br_counter = 0
for br in business_rules_p1:
    br_counter += 1
    desc = br.get("desc", "")
    severity = br.get("severity", "mandatory")
    signal_type = br.get("signal_type")
    category = br.get("category", "validation")
    
    enforcement = "mandatory" if severity == "mandatory" else "conditional"
    cov_pri = coverage_priority_br(desc, severity, signal_type, category)
    
    # entities_involved 为数组形式 ["E-XXX"] 或 ["E-XXX", "E-YYY"]
    entities_involved = br.get("entities_involved", [])
    # suggested_action 中用逗号连接展示
    entities_display = ", ".join(entities_involved) if entities_involved else ""
    
    ro_br = {
        "id": f"RO-BR-{br_counter:03d}",
        "type": "business_rule",
        "constraint_id": br["id"],
        "entities_involved": entities_involved,
        "category": category,
        "signal_type": signal_type,
        "description": desc,
        "enforcement": enforcement,
        "source_xc": None,
        "ref_to_existing_br": None,
        "coverage_priority": cov_pri,
        "suggested_action": f"在{entities_display}涉及环节，按规则执行: {desc[:80]}"
    }
    constraint_obligations.append(ro_br)

# --- 3.1 跳过后处理: XC -> RO-BR (共享编号空间) ---
xc_to_br_mapping = []
for xc in cross_entity_p1:
    xc_id = xc["id"]
    if xc_status.get(xc_id) == "br":
        br_counter += 1
        desc = xc.get("desc", "")
        source_entity = xc["source_entity"]
        target_entity = xc["target_entity"]
        target_condition = xc.get("target_condition", "")
        
        category = category_from_text(desc + " " + target_condition)
        
        # ref_to_existing_br: 检查 P1 是否有同主题 BR
        ref_br = None
        if "消息发送" in desc or "接收人1" in target_condition:
            for br in business_rules_p1:
                if "消息发送" in br.get("desc", "") or "接收人" in br.get("desc", ""):
                    ref_br = br["id"]
                    break
        if "文件整理" in desc:
            for br in business_rules_p1:
                if "文件整理" in br.get("desc", ""):
                    ref_br = br["id"]
                    break
        
        ro_br_id = f"RO-BR-{br_counter:03d}"
        description = f"[来源于{xc_id}] {target_condition}; {desc}"
        severity = "mandatory"
        signal_type = None
        
        cov_pri = coverage_priority_br(description, severity, signal_type, category)
        
        ro_br = {
            "id": ro_br_id,
            "type": "business_rule",
            "constraint_id": xc_id,
            "entities_involved": [source_entity, target_entity],
            "category": category,
            "signal_type": signal_type,
            "description": description,
            "enforcement": "mandatory",
            "source_xc": xc_id,
            "ref_to_existing_br": ref_br,
            "coverage_priority": cov_pri,
            "suggested_action": f"在{source_entity}, {target_entity}涉及环节，按{target_condition[:40]}规则执行操作"
        }
        constraint_obligations.append(ro_br)
        
        # 找到该 XC 的具体跳过原因
        skip_reason_actual = "门禁跳过"
        for w in warnings["step3_1"]:
            if xc_id in w:
                skip_reason_actual = w
                break
        xc_to_br_mapping.append({
            "xc_id": xc_id,
            "ro_br_id": ro_br_id,
            "ref_to_existing_br": ref_br,
            "xc_content": json.dumps(xc, ensure_ascii=False)[:200],
            "skip_reason": skip_reason_actual
        })

# ============================================================
# Step 5: _context
# ============================================================

# branch_dimensions (补 entity, affected_obligations)
ctx_branch_dimensions = []
for bd in branch_dimensions_p1:
    bd_copy = deepcopy(bd)
    # 补 entity
    if "entity" not in bd_copy:
        bd_copy["entity"] = ""
    # target_transition 不在 P1 → 置空
    valid_tids = set(transition_by_id.keys())
    for br in bd_copy.get("branches", []):
        if br.get("target_transition") and br["target_transition"] not in valid_tids:
            br["target_transition"] = ""
    # 扫描 TO.branch_path → affected_obligations
    affected = []
    for to in transition_obligations:
        if to["branch_path"]:
            for bp in to["branch_path"]:
                if bp["dimension"] == bd_copy["dimension"]:
                    affected.append(to["id"])
                    break
    bd_copy["affected_obligations"] = affected
    ctx_branch_dimensions.append(bd_copy)

# structural_relations
ctx_structural_relations = []
for sr in structural_relations:
    ctx_structural_relations.append({
        "from": sr["from"],
        "to": sr["to"],
        "relation_type": sr["relation_type"],
        "ownership_dimension": sr.get("ownership_dimension", ""),
        "cardinality": sr["cardinality"],
        "confidence": sr.get("confidence", "high"),
        "desc": sr.get("desc", "")
    })

# transition_relations
ctx_transition_relations = []
for R in transition_relations_p1:
    ctx_transition_relations.append({
        "from": R["from"],
        "to": R["to"],
        "trigger": R.get("trigger"),
        "trigger_source": R.get("trigger_source"),
        "evidence_transitions": R.get("evidence_transitions", []),
        "rollback_propagation": R.get("rollback_propagation", False),
        "confidence": R.get("confidence", "high"),
        "desc": R.get("desc", "")
    })

# state_info
state_info = {}
for e in entities:
    state_info[e["id"]] = {}
    for sd in e.get("state_dimensions", []):
        state_info[e["id"]][sd["dimension_name"]] = {
            "initial": sd["initial"],
            "terminal": sd["terminal"],
            "states": sd["states"]
        }

# entity_details
entity_details = []
for e in entities:
    entity_details.append({
        "id": e["id"],
        "name": e["name"],
        "tags": e.get("tags", []),
        "type": e["type"],
        "desc": e["desc"],
        "attributes": [{"name": a["name"], "desc": a["desc"], "is_config": a.get("is_config", False)} for a in e.get("attributes", [])]
    })

# roles
ctx_roles = [{"id": r["id"], "name": r["name"], "readonly": r.get("readonly", False)} for r in roles_p1]

# transition_notes
transition_notes = {}
for t in transitions_p1:
    n = t.get("note", {})
    if n.get("comment") or n.get("conflict") or n.get("inferred"):
        transition_notes[t["id"]] = {
            "inferred": n.get("inferred", False),
            "comment": n.get("comment", ""),
            "conflict": n.get("conflict", ""),
            "branch_dimension": n.get("branch_dimension", "")
        }

# ============================================================
# 组装最终输出
# ============================================================
final = {
    "entity_obligations": entity_obligations,
    "transition_obligations": transition_obligations,
    "cross_entity_obligations": cross_entity_obligations,
    "constraint_obligations": constraint_obligations,
    "_context": {
        "branch_dimensions": ctx_branch_dimensions,
        "structural_relations": ctx_structural_relations,
        "transition_relations": ctx_transition_relations,
        "state_info": state_info,
        "entity_details": entity_details,
        "roles": ctx_roles,
        "transition_notes": transition_notes,
        "xc_to_br_mapping": xc_to_br_mapping,
        "judgments": judgments,
        "warnings": warnings
    }
}

# ============================================================
# 输出前确认
# ============================================================
# 删除内部字段 _r_evidence_key
for co in cross_entity_obligations:
    co.pop("_r_evidence_key", None)

# ① 无 branch_scenarios
for to in transition_obligations:
    assert "branch_scenarios" not in to, f"{to['id']} 含 branch_scenarios"

# ② 所有 XC 在 xc_status 有去向
for xc in cross_entity_p1:
    assert xc["id"] in xc_status, f"{xc['id']} 未在 xc_status"

# ③ enabler_state 通过 (E,D,S) 或有 judgment
for co in cross_entity_obligations:
    if co["causal_type"] == "constraint" and co["enabler_state"]:
        states = get_states(co["enabler_entity"], co["enabler_dimension"])
        if states and co["enabler_state"] not in states:
            has_judgment = any(j["affected_id"] == (co.get("constraint_id") or co["id"]) for j in judgments)
            if not has_judgment:
                warnings["step3_5"].append(f"{co['id']} (E,D,S)复查失败: {co['enabler_state']} 不在 {co['enabler_entity']}.{co['enabler_dimension']}.states")

# ④ signal_type/category 已透传 (在生成时已处理)

# ⑤ ID 全局唯一
all_ids = ([eo["id"] for eo in entity_obligations]
          + [to["id"] for to in transition_obligations]
          + [co["id"] for co in cross_entity_obligations]
          + [co["id"] for co in constraint_obligations])
assert len(all_ids) == len(set(all_ids)), f"ID重复: {len(all_ids)} vs {len(set(all_ids))}"

# ASCII 安全检查
def safety_check(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            safety_check(v)
    elif isinstance(obj, list):
        for x in obj:
            safety_check(x)
    elif isinstance(obj, str):
        for bad in ["\u2192", "\u2190", "\u2191", "\u2193", "\u201c", "\u201d", "\u2018", "\u2019"]:
            if bad in obj:
                raise AssertionError(f"禁止字符 {repr(bad)} in {obj[:80]}")
safety_check(final)

# ============================================================
# 输出前自检 checklist
# ============================================================
# ① 无 branch_scenarios
no_branch_scenarios = all("branch_scenarios" not in to for to in transition_obligations)

# ② 所有 XC 在 xc_status 有去向
all_xc_have_status = all(xc["id"] in xc_status for xc in cross_entity_p1)

# ③ enabler_state 通过 (E,D,S) 或有 judgment
enabler_state_valid = True
for co in cross_entity_obligations:
    if co["causal_type"] in ("constraint", "lifecycle") and co["enabler_state"]:
        states = get_states(co["enabler_entity"], co["enabler_dimension"])
        if states and co["enabler_state"] not in states:
            has_judgment = any(j["affected_id"] == (co.get("constraint_id") or co["id"]) for j in judgments)
            if not has_judgment:
                enabler_state_valid = False

# ④ signal_type/category 已透传
signal_type_preserved = True
for cob in constraint_obligations:
    if cob["type"] == "business_rule" and not cob.get("source_xc"):  # P1 透传的
        br_id = cob["constraint_id"]
        p1_br = next((b for b in business_rules_p1 if b["id"] == br_id), None)
        if p1_br:
            if cob.get("signal_type") != p1_br.get("signal_type"):
                signal_type_preserved = False
            if cob.get("category") != p1_br.get("category"):
                signal_type_preserved = False

# ⑤ ID 全局唯一
id_globally_unique = len(all_ids) == len(set(all_ids))

# ⑥ P1 根节点完整
p1_root_nodes_complete = not missing

self_check = {
    "no_branch_scenarios": no_branch_scenarios,
    "all_xc_have_status": all_xc_have_status,
    "enabler_state_valid_or_judgment": enabler_state_valid,
    "signal_type_category_preserved": signal_type_preserved,
    "id_globally_unique": id_globally_unique,
    "p1_root_nodes_complete": p1_root_nodes_complete
}

# 将 self_check 加入 _context
final["_context"]["self_check"] = self_check

# 写入文件
out_path = "/home/z/my-project/download/obligation_coverage_model.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(final, f, ensure_ascii=False, indent=2)

print(f"OK - 写入 {out_path}")
print(f"entity_obligations: {len(entity_obligations)}")
print(f"transition_obligations: {len(transition_obligations)}")
print(f"cross_entity_obligations: {len(cross_entity_obligations)}")
print(f"constraint_obligations: {len(constraint_obligations)} (IT: {len(invalid_transitions_p1)}, BR: {len(business_rules_p1)}, XC-BR: {len(xc_to_br_mapping)})")
print(f"xc_status: {dict(list(xc_status.items())[:5])}...")
print(f"judgments: {len(judgments)}")
print(f"warnings: data_check={len(warnings['data_check'])}, step3_1={len(warnings['step3_1'])}, step3_2={len(warnings['step3_2'])}, step3_5={len(warnings['step3_5'])}")
print(f"self_check: {json.dumps(self_check, ensure_ascii=False)}")
