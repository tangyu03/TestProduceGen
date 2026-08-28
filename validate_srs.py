#!/usr/bin/env python3
"""SRS DSL 数据文件校验脚本。

通过 mock srs_pipeline 框架，导入数据文件的 build() 函数，
对返回的 DomainModel 执行 10 项结构化校验，定位建模缺口。

用法：
    python validate_srs.py <data_file.py>

校验项：
    C1  角色悬浮：每个 add_role 声明的角色须在 transitions.role 中出现 ≥1 次
                  （readonly 角色豁免，仅 WARN）
    C2  局部标签引用：note/comment 中提到的 tXX/xXX/bXX/iXX 须实际存在
    C3  分支穿透完整性：受 branch_dimension 影响的转换，
                       每个分支值至少有 1 条独立转换（禁止仅用文字区分）
    C4  状态枚举完整性：转换的 frm/to 须在实体 states 列表中
    C5  终态约束：终态无出边；非终态有出边
    C6  分支 BR 覆盖：每个 branch_dimension 至少在 1 条 BR 中出现
    C7  XC desc 前缀：每条 XC desc 须带来源前缀
                     （镜像/由 Step 4.5/联动/分支[）
    C8  enforcement 合法性：每条 BR 的 enforcement ∈ {mandatory, conditional}
    C9  role 一致性：transitions 中的 role 须在 roles 中声明或为 "system"
    C10 direction 一致性：direction 与状态在 states 列表中的相对位置一致
    C11 operations role 字段：每条 operation 的 note 必须含 role 字段
                       （单角色字符串或多角色列表），防止 entity_obligations actor 空
"""

import sys
import re
import importlib.util
from pathlib import Path
from collections import defaultdict


# ============================================================
# Mock srs_pipeline 框架
# ============================================================

class DomainModel:
    def __init__(self, source="", document_scope=""):
        self.source = source
        self.document_scope = document_scope
        self.action_verbs = []
        self.prohibit_keywords = []
        self.roles = []          # [{"name": str, "readonly": bool}]
        self.permissions = []    # [{"role": str, "operations": [str]}]
        self.entities = []       # [{"id", "name", "desc", "type", "tags", "attributes", "state_dimensions", "operations"}]
        self.structurals = []
        self.branch_dimensions = []
        self.transitions = []
        self.causals = []
        self.xcs = []
        self.brs = []
        self.invalids = []

    def set_prohibition_config(self, config):
        self.action_verbs = list(config.get("action_verbs", []))
        self.prohibit_keywords = list(config.get("prohibit_keywords", []))

    def add_action_verbs(self, verbs):
        for v in verbs:
            if v not in self.action_verbs:
                self.action_verbs.append(v)

    def add_prohibit_keywords(self, keywords):
        self.prohibit_keywords.extend(keywords)

    def add_role(self, name, readonly=False):
        self.roles.append({"name": name, "readonly": readonly})

    def add_permission(self, role, operations):
        self.permissions.append({"role": role, "operations": list(operations)})

    def add_entity(self, id, name, desc, type="core", tags=None, attributes=None,
                   state_dimensions=None, operations=None):
        self.entities.append({
            "id": id, "name": name, "desc": desc, "type": type,
            "tags": tags or [], "attributes": attributes or [],
            "state_dimensions": state_dimensions or [],
            "operations": operations or [],
        })

    def add_structural(self, frm, to, relation_type, cardinality,
                       ownership_dimension, desc, confidence="high", note=None):
        self.structurals.append({
            "frm": frm, "to": to, "relation_type": relation_type,
            "cardinality": cardinality, "ownership_dimension": ownership_dimension,
            "desc": desc, "confidence": confidence, "note": note,
        })

    def add_branch_dimension(self, dimension, entity, values, impact_scope,
                             evidence, branches):
        self.branch_dimensions.append({
            "dimension": dimension, "entity": entity, "values": list(values),
            "impact_scope": impact_scope, "evidence": evidence,
            "branches": list(branches),
        })

    def add_trans(self, tid, entity, dimension, frm, to, action, role,
                  preconditions, expected_results, traits, direction, priority,
                  source_ref, note=None):
        self.transitions.append({
            "tid": tid, "entity": entity, "dimension": dimension,
            "frm": frm, "to": to, "action": action, "role": role,
            "preconditions": preconditions, "expected_results": expected_results,
            "traits": list(traits), "direction": direction,
            "priority": priority, "source_ref": source_ref, "note": note,
        })

    def add_causal(self, frm, to, desc, trigger, trigger_source,
                   evidence_transitions=None, rollback_propagation=False,
                   confidence="high", note=None):
        self.causals.append({
            "frm": frm, "to": to, "desc": desc, "trigger": trigger,
            "trigger_source": trigger_source,
            "evidence_transitions": evidence_transitions or [],
            "rollback_propagation": rollback_propagation,
            "confidence": confidence, "note": note,
        })

    def add_invalid(self, iid, entity, frm, to, reason, source_ref):
        self.invalids.append({
            "iid": iid, "entity": entity, "frm": frm, "to": to,
            "reason": reason, "source_ref": source_ref,
        })

    def add_xc(self, xid, source_entity, source_transition, source_state,
               target_entity, target_dimension, category, type, desc, source_ref):
        self.xcs.append({
            "xid": xid, "source_entity": source_entity,
            "source_transition": source_transition, "source_state": source_state,
            "target_entity": target_entity, "target_dimension": target_dimension,
            "category": category, "type": type, "desc": desc,
            "source_ref": source_ref,
        })

    def add_br(self, bid, category, desc, entities_involved, source_ref,
               note=None, constrained_entity=None,
               branch_dimensions=None, enforcement=None, restrictive=False):
        # branch_dimensions＝显式参数第一优先；note.branch_dimension＝遗留形态
        # （';'/'；'分隔字符串或列表），归一化去重保序、剥离 note 键。
        import re as _re
        dims = list(branch_dimensions or [])
        if isinstance(note, dict) and note.get("branch_dimension"):
            legacy = note["branch_dimension"]
            if isinstance(legacy, str):
                legacy = [x.strip() for x in _re.split(r"[;；]", legacy)
                          if x.strip()]
            dims.extend(legacy)
        dims = list(dict.fromkeys(dims))
        if isinstance(note, dict) and "branch_dimension" in note:
            note = {k: v for k, v in note.items()
                    if k != "branch_dimension"}
        self.brs.append({
            "bid": bid, "category": category, "desc": desc,
            "entities_involved": list(entities_involved),
            "source_ref": source_ref,
            "enforcement": enforcement or ("mandatory" if any(
                w in desc for w in ("必须", "禁止", "不得", "不可", "不能"))
                else "conditional"),
            "restrictive": bool(restrictive),
            "note": note, "branch_dimensions": dims,
        })


# 辅助构造函数：返回值本身（便于链式调用）
def N(inferred=False, comment="", conflict="", branch_dimension=""):
    return {"inferred": inferred, "comment": comment,
            "conflict": conflict, "branch_dimension": branch_dimension}


def attr(name, desc, is_config=False):
    return {"name": name, "desc": desc, "is_config": is_config}


def op(name, category, expected_results, source_ref, note=None):
    return {"name": name, "category": category,
            "expected_results": expected_results, "source_ref": source_ref,
            "note": note}


def precond(text, ptype, ref=None, note=None):
    return {"text": text, "ptype": ptype, "ref": ref, "note": note}


def state_ref(entity, dimension, state):
    return {"entity": entity, "dimension": dimension, "state": state}


# 构造 mock 模块
class MockModule:
    DomainModel = DomainModel
    N = staticmethod(N)
    attr = staticmethod(attr)
    op = staticmethod(op)
    precond = staticmethod(precond)
    state_ref = staticmethod(state_ref)


# ============================================================
# 加载数据文件
# ============================================================

def load_model(data_file_path):
    """加载数据文件并返回 DomainModel 实例"""
    data_file = Path(data_file_path)
    if not data_file.exists():
        print(f"ERROR: 文件不存在: {data_file}")
        sys.exit(1)

    spec = importlib.util.spec_from_file_location("srs_data_module", str(data_file))
    module = importlib.util.module_from_spec(spec)

    # 注入 mock srs_pipeline
    sys.modules["srs_pipeline"] = MockModule()
    try:
        spec.loader.exec_module(module)
    finally:
        del sys.modules["srs_pipeline"]

    return module.build()


# ============================================================
# 校验器
# ============================================================

class Report:
    def __init__(self):
        self.errors = []   # 必须修复
        self.warns = []    # 建议关注

    def err(self, code, msg):
        self.errors.append(f"[{code}] {msg}")

    def warn(self, code, msg):
        self.warns.append(f"[{code}] {msg}")

    def summary(self):
        total = len(self.errors) + len(self.warns)
        print(f"\n{'=' * 60}")
        print(f"校验完成：{len(self.errors)} ERROR, {len(self.warns)} WARN")
        print(f"{'=' * 60}")
        if self.errors:
            print("\n--- ERRORS ---")
            for e in self.errors:
                print(f"  {e}")
        if self.warns:
            print("\n--- WARNINGS ---")
            for w in self.warns:
                print(f"  {w}")
        return 1 if self.errors else 0


def get_states_for_entity(model, eid, dimension_name=None):
    """获取实体的状态列表（按声明顺序），返回 (states_list, terminal_set, initial)"""
    for ent in model.entities:
        if ent["id"] == eid:
            for dim in ent["state_dimensions"]:
                if dimension_name is None or dim["dimension_name"] == dimension_name:
                    states = []
                    for s in dim["states"]:
                        if isinstance(s, dict):
                            states.append(s["value"])
                        else:
                            states.append(s)
                    return states, set(dim.get("terminal", [])), dim.get("initial")
    return [], set(), None


def extract_label_refs(text):
    """从文本中提取局部标签引用 (tXX, xXX, bXX, iXX)"""
    if not text:
        return []
    # 匹配 t01, t02b, x01, b03, i02 等
    return re.findall(r'\b([txbi]\d+[a-z]?)\b', text)


def flatten_note_text(note):
    """递归展平 note 字典为文本，用于标签引用扫描"""
    if note is None:
        return ""
    if isinstance(note, str):
        return note
    if isinstance(note, dict):
        parts = []
        for v in note.values():
            parts.append(flatten_note_text(v))
        return " ".join(parts)
    if isinstance(note, list):
        return " ".join(flatten_note_text(v) for v in note)
    return str(note)


# ============================================================
# 10 项校验
# ============================================================

def check_c1_role_coverage(model, report):
    """C1 角色覆盖：
    - 所有非 readonly 角色未出现在 transitions.role → WARN（可能是 crud-only 角色）
    - 角色名含'审批'/'执行'等转换型动词但未出现在 transitions → ERROR（一定是建模遗漏）
    """
    transition_roles = set(t["role"] for t in model.transitions)
    # 转换型角色关键词：角色名含这些词的，理应在 transitions 中出现
    transition_role_keywords = ("审批", "执行", "审批员")

    for role in model.roles:
        name = role["name"]
        if name == "system":
            continue
        if name not in transition_roles:
            # 检查角色名是否暗示转换型操作
            is_transition_role = any(kw in name for kw in transition_role_keywords)
            if is_transition_role:
                report.err("C1", f"角色 '{name}' 名称含转换型关键词但未出现在 transitions.role —— "
                                  f"一定是建模遗漏，需补转换")
            elif role["readonly"]:
                report.warn("C1", f"readonly 角色 '{name}' 在 transitions.role 中出现 0 次（仅 crud 可接受）")
            else:
                report.warn("C1", f"角色 '{name}' 在 transitions.role 中出现 0 次 —— "
                                  f"若为 crud-only 角色请确认权限声明完整；若应有转换操作则需补转换")


def check_c2_label_refs(model, report):
    """C2 局部标签引用：note/comment 中提到的标签须实际存在"""
    valid_tids = set(t["tid"] for t in model.transitions)
    valid_xids = set(x["xid"] for x in model.xcs)
    valid_bids = set(b["bid"] for b in model.brs)
    valid_iids = set(i["iid"] for i in model.invalids)
    all_valid = valid_tids | valid_xids | valid_bids | valid_iids

    # 扫描 transitions 的 note
    for t in model.transitions:
        text = flatten_note_text(t["note"])
        refs = extract_label_refs(text)
        for ref in refs:
            # 过滤掉非标签的匹配（如 "t1" 在 "fmt1" 中）
            if ref[0] in ("t", "x", "b", "i") and ref[1:].isdigit() or \
               (ref[0] in ("t", "x", "b", "i") and len(ref) > 1 and ref[1:].rstrip("abcdefghijklmnopqrstuvwxyz").isdigit()):
                if ref not in all_valid:
                    report.err("C2", f"transition {t['tid']} note 引用了不存在的标签 '{ref}'")


def check_c3_branch_penetration(model, report):
    """C3 分支穿透完整性：受 branch_dimension 影响的转换，
    每个分支值至少有 1 条独立转换"""
    for bd in model.branch_dimensions:
        dim_name = bd["dimension"]
        dim_values = bd["values"]
        entity_id = bd["entity"]

        # 收集该实体上受此分支维度影响的转换
        affected = []
        for t in model.transitions:
            if t["entity"] != entity_id:
                continue
            note = t["note"] or {}
            if note.get("branch_dimension") == dim_name:
                affected.append(t)

        # 对每个分支值，检查是否有独立转换
        for val in dim_values:
            val_pattern = f"若{dim_name}={val}"
            val_pattern2 = f"若任务级别={val}"  # 兼容实际写法

            matching = []
            for t in affected:
                er_text = " ".join(t["expected_results"])
                if val_pattern in er_text or val_pattern2 in er_text:
                    matching.append(t["tid"])

            if not matching:
                report.err("C3", f"分支维度'{dim_name}'的值'{val}'在 {entity_id} 的 transitions 中无独立转换 "
                                 f"（expected_results 未含'若{dim_name}={val}'句式）")
            else:
                # 进一步检查：是否有独立 tid（不是共用一条转换）
                # 如果只有1条且该条 expected_results 含多个"若...=..."，说明是共用转换
                if len(matching) == 1:
                    t = next(t for t in affected if t["tid"] == matching[0])
                    er_text = " ".join(t["expected_results"])
                    val_count = er_text.count(f"={val}")
                    if val_count < 1:
                        report.warn("C3", f"分支维度'{dim_name}'的值'{val}'仅由 {matching[0]} 单条转换承载，"
                                          f"建议拆分为独立转换")


def check_c4_state_completeness(model, report):
    """C4 状态枚举完整性：转换的 frm/to 须在实体 states 列表中"""
    # 构建实体→维度→状态集合
    entity_states = defaultdict(lambda: defaultdict(set))
    for ent in model.entities:
        for dim in ent["state_dimensions"]:
            for s in dim["states"]:
                val = s["value"] if isinstance(s, dict) else s
                entity_states[ent["id"]][dim["dimension_name"]].add(val)

    for t in model.transitions:
        states, _, _ = get_states_for_entity(model, t["entity"], t["dimension"])
        if not states:
            continue  # 无状态维度的实体跳过
        state_set = set(states)
        if t["frm"] not in state_set:
            report.err("C4", f"transition {t['tid']} frm='{t['frm']}' 不在 {t['entity']} 的 states 列表中")
        if t["to"] not in state_set:
            report.err("C4", f"transition {t['tid']} to='{t['to']}' 不在 {t['entity']} 的 states 列表中")


def check_c5_terminal_constraint(model, report):
    """C5 终态约束：终态无出边；非终态有出边"""
    # 构建实体→维度→(states, terminal_set)
    entity_dims = {}
    for ent in model.entities:
        for dim in ent["state_dimensions"]:
            states = []
            for s in dim["states"]:
                val = s["value"] if isinstance(s, dict) else s
                states.append(val)
            entity_dims[(ent["id"], dim["dimension_name"])] = (states, set(dim.get("terminal", [])))

    # 收集每个 (entity, dimension, state) 的出边
    outgoing = defaultdict(list)
    for t in model.transitions:
        outgoing[(t["entity"], t["dimension"], t["frm"])].append(t["tid"])

    # 检查
    for (eid, dim_name), (states, terminal_set) in entity_dims.items():
        for state in states:
            edges = outgoing.get((eid, dim_name, state), [])
            if state in terminal_set and edges:
                report.err("C5", f"{eid}.{dim_name} 终态'{state}'有出边: {edges}")
            if state not in terminal_set and not edges:
                report.warn("C5", f"{eid}.{dim_name} 非终态'{state}'无出边（可能为隐式初态或遗漏）")


def check_c6_branch_br_coverage(model, report):
    """C6 分支 BR 覆盖：每个 branch_dimension 至少在 1 条 BR 中出现
    （add_br 归一化的顶层 branch_dimensions 列表）"""
    br_dims = {d for br in model.brs for d in (br.get("branch_dimensions") or [])}

    for bd in model.branch_dimensions:
        if bd["dimension"] not in br_dims:
            report.err("C6", f"分支维度'{bd['dimension']}'未在任何 BR 的 branch_dimensions 中出现")


def check_c7_xc_desc_prefix(model, report):
    """C7 XC desc 前缀：每条 XC desc 须带来源前缀"""
    valid_prefixes = ["镜像", "由 Step 4.5", "联动", "分支["]
    for xc in model.xcs:
        desc = xc["desc"]
        if not any(desc.startswith(p) for p in valid_prefixes):
            report.err("C7", f"XC {xc['xid']} desc 缺少来源前缀: '{desc[:50]}...'")


def check_c8_signal_type(model, report):
    """C8 enforcement/restrictive 合法性（signal_type 已删，随迁移替换）"""
    valid = {"mandatory", "conditional"}
    for br in model.brs:
        if br.get("enforcement") not in valid:
            report.err("C8", f"BR {br['bid']} enforcement='{br.get('enforcement')}' 不在合法集合 {valid}")


def check_c9_role_consistency(model, report):
    """C9 role 一致性：transitions 中的 role 须在 roles 中声明或为 'system'"""
    declared_roles = set(r["name"] for r in model.roles) | {"system"}
    for t in model.transitions:
        if t["role"] not in declared_roles:
            report.err("C9", f"transition {t['tid']} role='{t['role']}' 未在 add_role 中声明")


def check_c10_direction_consistency(model, report):
    """C10 direction 一致性：direction 与状态在 states 列表中的相对位置一致"""
    for t in model.transitions:
        if t["direction"] == "lateral" or t["direction"] == "resume":
            continue  # 侧挂/恢复不检查顺序
        states, _, _ = get_states_for_entity(model, t["entity"], t["dimension"])
        if not states or t["frm"] not in states or t["to"] not in states:
            continue  # C4 已报错
        frm_idx = states.index(t["frm"])
        to_idx = states.index(t["to"])
        if t["direction"] == "forward" and frm_idx > to_idx:
            report.err("C10", f"transition {t['tid']} direction='forward' 但 frm='{t['frm']}'(idx={frm_idx}) "
                              f"在 to='{t['to']}'(idx={to_idx}) 之后")
        elif t["direction"] == "backward" and frm_idx < to_idx:
            report.err("C10", f"transition {t['tid']} direction='backward' 但 frm='{t['frm']}'(idx={frm_idx}) "
                              f"在 to='{t['to']}'(idx={to_idx}) 之前")


def check_c11_operations_role(model, report):
    """C11 operations role 字段：每条 operation 的 note 必须含 role 字段
    （单角色字符串或多角色列表），防止 entity_obligations 的 actor 字段全空。
    """
    declared_roles = set(r["name"] for r in model.roles) | {"system", "普通用户"}
    # 普通用户作为通用 actor 兜底（登录/注销等无显式角色归属）

    for ent in model.entities:
        for op_obj in ent["operations"]:
            note = op_obj.get("note")
            if not isinstance(note, dict) or "role" not in note:
                report.err("C11", f"{ent['id']}.operations['{op_obj['name']}'] note 缺 role 字段 —— "
                                  f"导致 entity_obligations actor 空")
                continue

            role = note["role"]
            # 统一为列表校验
            roles_to_check = [role] if isinstance(role, str) else role
            for r in roles_to_check:
                if r not in declared_roles:
                    report.err("C11", f"{ent['id']}.operations['{op_obj['name']}'] role='{r}' "
                                      f"未在 add_role 中声明")


# ============================================================
# 主入口
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("用法: python validate_srs.py <data_file.py>")
        sys.exit(1)

    data_file = sys.argv[1]
    model = load_model(data_file)

    print(f"加载数据文件: {data_file}")
    print(f"  source: {model.source}")
    print(f"  角色: {len(model.roles)}")
    print(f"  实体: {len(model.entities)}")
    print(f"  转换: {len(model.transitions)}")
    print(f"  因果: {len(model.causals)}")
    print(f"  XC: {len(model.xcs)}")
    print(f"  BR: {len(model.brs)}")
    print(f"  IT: {len(model.invalids)}")
    print(f"  分支维度: {len(model.branch_dimensions)}")
    print(f"  结构关系: {len(model.structurals)}")

    report = Report()
    check_c1_role_coverage(model, report)
    check_c2_label_refs(model, report)
    check_c3_branch_penetration(model, report)
    check_c4_state_completeness(model, report)
    check_c5_terminal_constraint(model, report)
    check_c6_branch_br_coverage(model, report)
    check_c7_xc_desc_prefix(model, report)
    check_c8_signal_type(model, report)
    check_c9_role_consistency(model, report)
    check_c10_direction_consistency(model, report)
    check_c11_operations_role(model, report)

    sys.exit(report.summary())


if __name__ == "__main__":
    main()
