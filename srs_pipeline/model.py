"""DomainModel：Step1-5 产物容器；assemble() 执行 Step6（coverage 回填、trace、
校验、中断）。P1.5：已集成文档挂载通道（source_ref 反幻觉 C15 + 双通道对账）。"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from .builders import N
from .escape import esc
from .schema import validate_llm

SCHEMA_VERSION = "19.2"

# 局部标签(铁律14: 编号一律局部标签, 框架统一改写为正式编号)。
# 匹配形如 t01 / t07a / tp01 / p04 / u01 / o01 / s01 / x01 / b01 / i01 的
# 交叉引用 token。中文需求文本中"小写字母+数字"几乎必是标签, 误伤可忽略。
_LOCAL = re.compile(r"\b[a-z]{1,3}\d{2,3}[a-z]?\b")

def _esc_note(note):
    """note 统一转义：数据文件可直接传原始 dict（{comment/conflict/branch_dimension}）
    或字符串，落盘前对自由文本键跑 esc，避免绕过硬转义铁律（C10）。"""
    if note is None:
        return N()
    if isinstance(note, str):
        return N(comment=note)
    n = dict(note)
    for k in ("comment", "conflict", "branch_dimension"):
        if n.get(k):
            n[k] = esc(str(n[k]))
    return n

def _now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")

def ambiguity(amb_id, concept, description, assumption="", suggestion="",
              severity="minor") -> dict:
    return {"amb_id": amb_id, "severity": severity, "concept": concept,
            "description": description, "assumption": assumption,
            "suggestion": suggestion}

class CriticalAmbiguity(Exception):
    """铁律5 / critical 清单：校验修复失败 → 中断，仅输出中断 Schema。"""
    def __init__(self, items):
        self.items = list(items)
        super().__init__("; ".join(i.get("concept", "") for i in self.items))

def interrupt_schema(source, items) -> dict:
    return {"_meta": {"version": SCHEMA_VERSION, "generated_at": _now(),
                      "source": source or "未命名文档",
                      "has_critical_ambiguity": True,
                      "ambiguity_list": list(items)}}

# Step5 enforcement 映射的确定性实现：把 prompt 里 7 行的"severity 默认映射表"
# 坍缩为 2 条规则——field_constraint 恒 mandatory；desc 含强措辞(必须/禁止/
# 不得/不可/不能) → mandatory；其余(许可措辞/展示/易用性) → conditional。
# 注：表内 display/usability 的"升级条件=原文含必须"在此泛化为"含任一强措辞"
# (严格超集，如"不得显示"也归 mandatory)。enforcement 由框架推导，LLM 不手写。
_STRONG_WORDS = ("必须", "禁止", "不得", "不可", "不能")

def derive_enforcement(signal_type: str, desc: str) -> str:
    if signal_type == "field_constraint":
        return "mandatory"
    if any(w in desc for w in _STRONG_WORDS):
        return "mandatory"
    return "conditional"

class DomainModel:
    def __init__(self, source, document_scope="", version=SCHEMA_VERSION):
        self.meta = {"version": version, "generated_at": _now(),
                     "source": source or "未命名文档",
                     "document_scope": document_scope,
                     "has_critical_ambiguity": False,
                     "consistency_check": "passed",
                     "ambiguity_list": [], "pipeline_trace": {},
                     "branch_dimensions": []}
        self.entities, self.roles = [], []
        self.structural_relations, self.transition_relations = [], []
        self.transitions = []
        self.invalid_transitions, self.cross_entity, self.business_rules = [], [], []
        self.branch_dimensions = []
        # 项目操作词汇(prohibition_config)由数据模块声明 —— 领域词汇的唯一
        # 真相源在 P1 数据层,而非 P2/S1 引擎硬编码。P2 读取 p1._context.
        # prohibition_config,缺省时用 P2 的通用兜底。
        self.prohibition_config: dict = {}
        # 角色→可执行操作权限。第一性原理:权限矩阵的单一真相源在 P1 数据层
        # (而非 case_spec 手写矩阵)——由授权类 BR(如"机构管理员对本机构的项目
        # 进行管理")与各操作的角色归属汇总。V07 校验器从 _context.permissions
        # + transition_obligations.role 推导矩阵。
        self.permissions: list[dict] = []
        self._check_hooks = []          # 扩展点：项目自定义校验
        self._before_assemble = []      # 扩展点：组装前钩子
        # ---- P1.5 挂载点 ----
        self.doc_text = None            # attach_document 挂载原文后启用 C15 与对账
        self.review_queue = []          # 对账产生的评审队列

    # ---------- Step 1 ----------
    def add_entity(self, id, name, desc, type="core", tags=None,
                   attributes=None, state_dimensions=None, operations=None):
        validate_llm("entity", {"id": id, "name": name, "desc": desc, "type": type,
                                "tags": tags, "attributes": attributes,
                                "state_dimensions": state_dimensions,
                                "operations": operations})
        dims = [{"dimension_name": d["dimension_name"], "states": list(d["states"]),
                 "initial": d["initial"], "terminal": list(d.get("terminal", [])),
                 "note": d.get("note") or N(),
                 "inferred": list(d.get("inferred", []) or [])}
                for d in (state_dimensions or [])]
        self.entities.append({
            "id": id, "name": name, "desc": esc(desc), "type": type,
            "tags": list(tags or []), "attributes": list(attributes or []),
            "state_dimensions": dims, "operations": list(operations or [])})
        return self

    # ---------- Step 2 ----------
    def add_structural(self, frm, to, relation_type, cardinality,
                       ownership_dimension, desc, confidence="high", note=None):
        validate_llm("structural", {"frm": frm, "to": to,
                                    "relation_type": relation_type,
                                    "cardinality": cardinality,
                                    "ownership_dimension": ownership_dimension,
                                    "desc": desc, "confidence": confidence,
                                    "note": note})
        self.structural_relations.append({
            "from": frm, "to": to, "relation_type": relation_type,
            "cardinality": cardinality, "ownership_dimension": ownership_dimension,
            "desc": esc(desc), "confidence": confidence,
            "note": _esc_note(note)})
        return self

    # ---------- Step 3 ----------
    def add_branch_dimension(self, dimension, entity, values, impact_scope,
                             evidence, branches):
        validate_llm("branch_dimension", {"dimension": dimension, "entity": entity,
                                          "values": values, "impact_scope": impact_scope,
                                          "evidence": evidence, "branches": branches})
        escaped_branches = [
            {k: esc(v) if isinstance(v, str) else v for k, v in b.items()}
            for b in branches
        ]
        self.branch_dimensions.append({
            "dimension": dimension, "entity": entity, "values": list(values),
            "impact_scope": esc(impact_scope), "evidence": esc(evidence),
            "branches": escaped_branches, "coverage": {}})   # coverage 由 Step6 回填
        return self

    # ---------- Step 4 ----------
    def add_role(self, id, name, readonly=False):
        validate_llm("role", {"id": id, "name": name, "readonly": readonly})
        self.roles.append({"id": id, "name": name, "readonly": bool(readonly)})
        return self

    def add_trans(self, tid, entity, dimension, frm, to, action, role,
                  preconditions, expected_results, traits, direction,
                  priority, source_ref, note=None):
        validate_llm("trans", {"tid": tid, "entity": entity, "dimension": dimension,
                               "frm": frm, "to": to, "action": action, "role": role,
                               "preconditions": preconditions,
                               "expected_results": expected_results, "traits": traits,
                               "direction": direction, "priority": priority,
                               "source_ref": source_ref, "note": note})
        t = {"id": tid, "entity": entity, "dimension": dimension,
             "from": frm, "to": to, "action": action, "role": role,
             "preconditions": list(preconditions),
             "expected_results": [esc(e) for e in expected_results],
             "traits": list(traits), "direction": direction, "priority": priority,
             "source_ref": esc(source_ref), "note": _esc_note(note)}
        self.transitions.append(t)
        return self

    def add_causal(self, frm, to, desc, trigger, trigger_source,
                   evidence_transitions=None, rollback_propagation=False,
                   confidence="high", note=None):
        validate_llm("causal", {"frm": frm, "to": to, "desc": desc, "trigger": trigger,
                                "trigger_source": trigger_source,
                                "evidence_transitions": evidence_transitions,
                                "rollback_propagation": rollback_propagation,
                                "confidence": confidence, "note": note})
        self.transition_relations.append({
            "from": frm, "to": to, "desc": esc(desc), "trigger": esc(trigger),
            "trigger_source": trigger_source,
            "evidence_transitions": list(evidence_transitions or []),
            "rollback_propagation": bool(rollback_propagation),
            "confidence": confidence, "note": _esc_note(note)})
        return self

    # ---------- Step 5 ----------
    def add_invalid(self, iid, entity, frm, to, reason, source_ref):
        validate_llm("invalid", {"iid": iid, "entity": entity, "frm": frm,
                                 "to": to, "reason": reason, "source_ref": source_ref})
        self.invalid_transitions.append({
            "id": iid, "entity": entity, "from": frm, "to": to,
            "reason": esc(reason), "source_ref": esc(source_ref)})
        return self

    def add_xc(self, xid, source_entity, source_transition, source_state,
               target_entity, target_dimension, target_condition, desc,
               source_ref):
        validate_llm("xc", {"xid": xid, "source_entity": source_entity,
                            "source_transition": source_transition,
                            "source_state": source_state,
                            "target_entity": target_entity,
                            "target_dimension": target_dimension,
                            "target_condition": target_condition,
                            "desc": desc, "source_ref": source_ref})
        self.cross_entity.append({
            "id": xid, "source_entity": source_entity,
            "source_transition": source_transition, "source_state": source_state,
            "target_entity": target_entity, "target_dimension": target_dimension,
            "target_condition": target_condition, "desc": esc(desc),
            "source_ref": esc(source_ref)})     # 输入契约：XC 无 note 字段
        return self

    def add_br(self, bid, category, desc, entities_involved, source_ref,
               signal_type, note=None):
        validate_llm("br", {"bid": bid, "category": category, "desc": desc,
                            "entities_involved": entities_involved,
                            "source_ref": source_ref, "signal_type": signal_type,
                            "note": note})
        self.business_rules.append({
            "id": bid, "category": category, "desc": esc(desc),
            "entities_involved": list(entities_involved),
            "enforcement": derive_enforcement(signal_type, desc),
            "source_ref": esc(source_ref), "signal_type": signal_type,
            "note": _esc_note(note)})
        return self

    # ---------- 扩展点 ----------
    def add_permission(self, role: str, operations: list):
        """声明角色可执行的操作(role→operations)。

        权限矩阵的单一真相源在 P1 数据层——V07 校验器据此推导矩阵,不再依赖
        case_spec 手写矩阵。role 用角色名(与用例 actor 一致,如"评审管理员")。
        例:
            m.add_permission("评审管理员", ["建立评审计划", "下发评审计划", ...])
        """
        validate_llm("permission", {"role": role, "operations": operations})
        self.permissions.append({"role": role, "operations": list(operations)})
        return self

    def set_prohibition_config(self, config: dict):
        """声明项目操作词汇(prohibition_config)。

        领域动词/禁止短语的唯一真相源在 P1 数据层 —— P2 读取
        p1._context.prohibition_config,缺省时回退到 P2 的通用兜底。
        数据模块在 build() 中调用,示例:
            m.set_prohibition_config({
                "negation_prefixes": [...],
                "action_verbs": ["选入", "归档", ...],   # 项目业务操作
                "prohibit_keywords": [...],
                "success_hints": [...],
            })
        """
        validate_llm("prohibition_config", config or {})
        self.prohibition_config = dict(config or {})
        return self

    def add_action_verbs(self, verbs):
        """Step 1–5 增量回写 action_verbs（通用回写协议）。

        发现新动词时在当前位置追加，无需回到 Step 0 修改原调用；
        追加去重，已收录的动词不重复。prompt.md 规定此协议。
        """
        validate_llm("prohibition_config", self.prohibition_config or {})
        existing = list(self.prohibition_config.get("action_verbs") or [])
        for v in verbs:
            if v not in existing:
                existing.append(v)
        self.prohibition_config["action_verbs"] = existing
        return self

    def add_prohibit_keywords(self, keywords):
        """Step 1–5 增量回写 prohibit_keywords（通用回写协议）。

        追加去重，语义同 add_action_verbs。
        """
        validate_llm("prohibition_config", self.prohibition_config or {})
        existing = list(self.prohibition_config.get("prohibit_keywords") or [])
        for k in keywords:
            if k not in existing:
                existing.append(k)
        self.prohibition_config["prohibit_keywords"] = existing
        return self

    def add_check(self, fn):
        """注册项目自定义校验，签名 fn(validator, report)。"""
        self._check_hooks.append(fn)
        return self

    def on_before_assemble(self, fn):
        self._before_assemble.append(fn)
        return self

    # ---------- P1.5：文档挂载 ----------
    def attach_document(self, text: str):
        """挂载原文：建证据库，启用 C15 反幻觉、C16 枚举对账与双通道对账。"""
        from .evidence import build_evidence
        self.doc_text = text
        self.evidence = build_evidence(text)
        return self


    # ---------- Step 6 ----------
    def assemble(self):
        from .validate import Validator
        # 编号移交(铁律14): 局部标签 → 正式编号, 无条件执行。
        # 此前误放 _before_assemble 钩子循环内 —— 无钩子时编号移交失效,
        # 输出残留局部标签(t01/t07a), 下游 P2/S1 无法按 T-xxx 关联。
        self._assign_ids()
        for fn in self._before_assemble:
            fn(self)
        self._backfill_branch_coverage()
        self.meta["branch_dimensions"] = self.branch_dimensions
        output = self._build_output()
        validator = Validator(self, output)
        for fn in self._check_hooks:
            validator.register_check(fn)
        report = validator.run_all()

        # ---- 文档挂载通道（必须在 errors 判断之前，C15 造假要触发中断）----
        if self.doc_text:
            from .signals import audit_source_refs, scan
            from .reconcile import reconcile_causal, reconcile_signals
            for msg in audit_source_refs(self, self.doc_text):
                report.error("C15", msg)                 # 引文造假 = error
            self.review_queue = reconcile_signals(scan(self.doc_text), self) \
                              + reconcile_causal(self)

        self._backfill_branch_coverage()                 # 二次回填，纳入 C04 补的镜像
        # 自动修复属"无原文依据的修补"→ 登记 minor 歧义（铁律1/铁律5）
        for i, fix in enumerate(report.fixes, 1):
            self.meta["ambiguity_list"].append(
                ambiguity(f"AMB-FIX-{i:03d}", concept="Step6 自动修复",
                          description=esc(fix), severity="minor"))
        self.meta["pipeline_trace"] = self._build_trace()   # 修复后重算
        if report.errors:
            raise CriticalAmbiguity([
                ambiguity(f"AMB-VAL-{i:03d}", concept=e.check,
                          description=e.message, severity="critical")
                for i, e in enumerate(report.errors, 1)])
        output["_meta"]["consistency_check"] = \
            "warnings" if report.warnings else "passed"
        return output, report

    def _build_output(self):
        self.meta["pipeline_trace"] = self._build_trace()
        return {"_meta": self.meta,
                "_context": {"prohibition_config": self.prohibition_config,
                            "permissions": self.permissions},
                "domain_model": {
                    "entities": self.entities, "roles": self.roles,
                    "structural_relations": self.structural_relations,
                    "transition_relations": self.transition_relations},
                "state_and_flow": {"transitions": self.transitions},
                "constraints": {"invalid_transitions": self.invalid_transitions,
                                "cross_entity": self.cross_entity,
                                "business_rules": self.business_rules}}

    def _backfill_branch_coverage(self):
        """Step6：按 note.branch_dimension（支持';'分隔多值）与
        XC 的'分支[维度='前缀或 source_transition 命中，回填三层 coverage。"""
        for d in self.branch_dimensions:
            name = d["dimension"]
            t_ids = [t["id"] for t in self.transitions
                     if name in re.split(r"[;；]",
                                         t["note"].get("branch_dimension", ""))]
            d["coverage"] = {
                "transitions": t_ids,
                "cross_entity": sorted({x["id"] for x in self.cross_entity
                                        if x["desc"].startswith(f"分支[{name}=")
                                        or x["source_transition"] in t_ids}),
                "business_rules": [b["id"] for b in self.business_rules
                                   if name in re.split(
                                       r"[;；]", b["note"].get(
                                           "branch_dimension", ""))]}

    def _build_trace(self):
        pre = [p for t in self.transitions for p in t["preconditions"]]
        sr = [p for p in pre if p["type"] == "state_ref"]
        return {
            "step1_entities": [e["id"] for e in self.entities],
            "step2_structural_relations": len(self.structural_relations),
            "step3_branch_dimensions": len(self.branch_dimensions),
            "step4_transitions": len(self.transitions),
            "step4_transition_relations": len(self.transition_relations),
            "step4_roles": len(self.roles),
            "step4_precondition_stats": {
                "total_preconditions": len(pre),
                "state_ref_count": len(sr),
                "event_ref_count": sum(1 for p in pre if p["type"] == "event_ref"),
                "constraint_count": sum(1 for p in pre
                                      if p["type"] == "constraint"),
                "state_ref_resolved_count": sum(1 for p in sr if p.get("ref")),
                "state_ref_unresolved_count": sum(1 for p in sr
                                                 if not p.get("ref"))},
            "step5_invalid_transitions": len(self.invalid_transitions),
            "step5_cross_entity": len(self.cross_entity),
            "step5_business_rules": len(self.business_rules)}

    def _assign_ids(self):
        """局部标签 → 正式编号，按调用顺序（prompt 要求=文档顺序）统一分配，
        并改写全部交叉引用。LLM 不再拥有编号权 → 编号跨次生成天然稳定。"""
        def renumber(items, prefix):
            m = {}
            for i, it in enumerate(items, 1):
                old = it["id"]
                if not re.fullmatch(r"[A-Z]+-\d{3}[a-z]?", old):   # 已是正式号则跳过
                    it["id"] = f"{prefix}-{i:03d}"
                m[old] = it["id"]
            return m
        allmap = {**renumber(self.transitions, "T"),
                  **renumber(self.cross_entity, "XC"),
                  **renumber(self.business_rules, "BR"),
                  **renumber(self.invalid_transitions, "IT")}

        def rw(s):
            return _LOCAL.sub(lambda mm: allmap.get(mm.group(0), mm.group(0)),
                              s) if isinstance(s, str) else s

        for x in self.cross_entity:
            x["source_transition"] = rw(x["source_transition"])
            x["desc"] = rw(x["desc"])
        for r in self.transition_relations:
            r["evidence_transitions"] = [rw(e) for e in r["evidence_transitions"]]
            r["desc"], r["trigger"] = rw(r["desc"]), rw(r["trigger"])
        for d in self.branch_dimensions:
            for br in d["branches"]:
                br["target_transition"] = rw(br.get("target_transition", ""))
        for t in self.transitions:
            if t["note"].get("comment"):
                t["note"]["comment"] = rw(t["note"]["comment"])
        for e in self.entities:
            for o in e["operations"]:
                if o["note"].get("comment"):
                    o["note"]["comment"] = rw(o["note"]["comment"])