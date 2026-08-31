"""DomainModel：Step1-5 产物容器；assemble() 执行 Step6（coverage 回填、trace、
校验、中断）。P1.5：已集成文档挂载通道（source_ref 反幻觉 C15 + 双通道对账）。"""
from __future__ import annotations

import re
import warnings
from datetime import datetime, timedelta, timezone

from .builders import N
from .constants import LOCAL_LABEL as _LOCAL
from .constants import XC_DESC_TPL, XC_LEGACY_RE
from .escape import esc
from .schema import validate_llm

SCHEMA_VERSION = "19.2"

# 局部标签(铁律14: 编号一律局部标签, 框架统一改写为正式编号)。形态单一事实源
# 在 constants.LOCAL_LABEL（模型/校验器共享），此处仅复引。

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


# 回喂标签：正式号（BR-008/T-001/XC-001/IT-001）∪ 局部标签（t07/b01/x01/e01…）。
# 负向断言词界（勿用 \b——CJK 吞界，「源自e01」匹配不出，见 constants.LOCAL_LABEL）。
_FEEDBACK_LABEL = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Z]{2,}-\d{3}[a-z]?|[a-z]{1,3}\d{2,3}[a-z]?)"
    r"(?![A-Za-z0-9])")


def build_feedback(items) -> list:
    """critical 歧义清单 → glm5pr §5 回喂格式 [{"check","labels","expected"}]。

    确定性，无 LLM：check=校验码（concept）；labels=消息文本抽取的标签
    （候选承载/被修条目）；expected=消息修法指引全文（C20「修法：…示例：
    候选承载…」即最小修复指令）。供 CLI --feedback 落盘，直接投给 LLM 触发
    再生成（回喂触发的补事件/补挂是合法回修通道，glm5pr §5）。
    """
    return [{
        "check": it.get("concept", ""),
        "labels": sorted(set(_FEEDBACK_LABEL.findall(it.get("description", "")))),
        "expected": it.get("description", ""),
    } for it in items]


def build_deviation_feedback(deviations) -> list:
    """分支回填偏差（meta.branch_tt_deviations）→ §5 回喂格式。

    偏差＝LLM 写了匹配器解不开的描述（0/多候选），按 action 词锚重写即解——
    走与 critical 相同的回喂通道（glm5pr §5），在正常完成路径控制台打印。"""
    return [{
        "check": "BRANCH_TT_DEVIATION",
        "labels": sorted(set(_FEEDBACK_LABEL.findall(d["target_transition"]))),
        "expected": (
            f"分支维度[{d['dimension']}] 值[{d['value']}] 的 target_transition 语义描述"
            f"「{d['target_transition']}」回填无唯一候选（{d['reason']}）。"
            f"修法：改写描述为动作词锚定形态（如「xxx转换（frm变为to）」），"
            f"使其唯一命中该维度实体的转换，勿用裸状态名或歧义动作词。"),
    } for d in deviations]


def build_downgrade_feedback(report) -> list:
    """自动降级事件（C03 锚点/C08 组合降级）→ glm5pr §5 回喂格式。

    降级＝无原文依据的修补（铁律5），须在数据源头修正（契约句）——与 critical/
    分支偏差同通道，正常完成路径控制台打印。C03 锚点警告消息已含精确修法
    （端点非法+已建模维度+改指持有该状态的实体），整段作 expected；C08 的
    fix 是后果描述，补一句标准修法（B 创建转换携带指向父实体 A 的 state_ref，
    第三方前置视为业务门禁）。labels 用共享正则抽取，命中多少算多少——真正
    投喂内容是 expected。"""
    items = []
    for i in report.warnings:
        if i.check == "C03" and "降级" in i.message:
            items.append({
                "check": "C03",
                "labels": sorted(set(_FEEDBACK_LABEL.findall(i.message))),
                "expected": i.message,
            })
    for m in report.fixes:
        if m.startswith("C08"):
            items.append({
                "check": "C08",
                "labels": sorted(set(_FEEDBACK_LABEL.findall(m))),
                "expected": (
                    m + "。修法：该关系若确为组合（A 为业务归属容器），令 B 的"
                    "创建转换携带指向父实体 A 的 state_ref 前置（如 E-XM.项目状态"
                    "=报名中），第三方前置仅视为业务门禁不影响组合判定；否则降级"
                    "成立，应改判 (d) reference+configuration_source。"),
            })
    return items

# Step5 enforcement 映射的确定性实现：enforcement 由 restrictive 派生——
# restrictive=True→mandatory，否则 conditional。restrictive 是 LLM 显式给的
# 拦截性标记（glm5pr :194 强制措辞定义，作者逐条判定），enforcement 是其
# 确定性子集，LLM 不手写 enforcement。原 desc 强词推导已删（词检不可复现：
# v6/v7 短信规则与 v8 同文规则分类相反），signal_type 迁移固化的显式
# enforcement="mandatory" 一并退役（改走 restrictive 通道）。
def derive_enforcement(restrictive: bool) -> str:
    """enforcement 派生：restrictive=True→mandatory，否则 conditional。"""
    return "mandatory" if restrictive else "conditional"

class DomainModel:
    def __init__(self, source, document_scope="", version=SCHEMA_VERSION):
        self.meta = {"version": version, "generated_at": _now(),
                     "source": source or "未命名文档",
                     "document_scope": esc(document_scope),
                     "has_critical_ambiguity": False,
                     "consistency_check": "passed",
                     "ambiguity_list": [], "pipeline_trace": {},
                     "branch_dimensions": []}
        self.entities, self.roles = [], []
        self.structural_relations, self.transition_relations = [], []
        self.events = []                # 事件台账输出（§2）：转换/关系 note 引用的事件注册表
        self._events = {}               # 内部标签映射表（eid→记录）：F4/F10/F15 校验的单一读取源
        self.transitions = []
        self.invalid_transitions, self.cross_entity, self.business_rules = [], [], []
        self.branch_dimensions = []
        self.op_links = []          # op→转换结构化关联（link_op_transition 追加）
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

    # ---------- Step 0（事件台账）----------
    def add_event(self, eid, entity, dimension, action, actor, precondition,
                  consequence, source_ref):
        """登记事件台账条目（glm5pr §2，8 列契约）。entity=主体映射的已登记实体 E-XXX id；
        执行者为 system 时 actor 传"system"。precondition 无前置传"无"。"""
        validate_llm("event", {"eid": eid, "entity": entity,
                               "dimension": dimension, "action": action,
                               "actor": actor, "precondition": precondition,
                               "consequence": consequence,
                               "source_ref": source_ref})
        record = {"id": eid, "entity": entity, "dimension": dimension,
                  "action": action, "actor": actor,
                  "precondition": precondition, "consequence": consequence,
                  "source_ref": esc(source_ref)}
        self._events[eid] = record      # 内部标签映射表（eid→记录）：F4/F10/F15 读取源
        self.events.append(record)      # 输出 payload（_build_output）
        return self

    # ---------- Step 1 ----------
    def add_entity(self, id, name, desc, type="core", tags=None,
                   attributes=None, state_dimensions=None, operations=None):
        validate_llm("entity", {"id": id, "name": name, "desc": desc, "type": type,
                                "tags": tags, "attributes": attributes,
                                "state_dimensions": state_dimensions,
                                "operations": operations})
        dims = [{"dimension_name": d["dimension_name"], "states": list(d["states"]),
                 "initial": d["initial"], "terminal": list(d.get("terminal", [])),
                 "note": _esc_note(d.get("note")),   # 铁律4：状态维度 note 亦须转义
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
                               "expected_results": expected_results, "traits": [],
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
               source_ref, target_transition=None, xc_source=None):
        # xc_source=None（缺省）＝未显式传：assemble 从旧 desc 前缀反推来源
        # （golden 冻结兼容）；新数据一律显式传（prompt Step 5 必填）。
        validate_llm("xc", {"xid": xid, "source_entity": source_entity,
                            "source_transition": source_transition,
                            "source_state": source_state,
                            "target_entity": target_entity,
                            "target_transition": target_transition,
                            "target_dimension": target_dimension,
                            "target_condition": target_condition,
                            "desc": desc, "source_ref": source_ref,
                            "xc_source": xc_source})
        self.cross_entity.append({
            "id": xid, "source_entity": source_entity,
            "source_transition": source_transition, "source_state": source_state,
            "target_entity": target_entity, "target_transition": target_transition,
            "target_dimension": target_dimension,
            "target_condition": target_condition, "desc": esc(desc),
            "xc_source": xc_source,
            "source_ref": esc(source_ref)})     # 输入契约：XC 无 note 字段
        return self

    def add_br(self, bid, category, desc, entities_involved, source_ref,
               note=None, constrained_entity=None,
               branch_dimensions=None, restrictive=False):
        validate_llm("br", {"bid": bid, "category": category, "desc": desc,
                            "entities_involved": entities_involved,
                            "source_ref": source_ref,
                            "note": note, "constrained_entity": constrained_entity,
                            "branch_dimensions": branch_dimensions,
                            "restrictive": restrictive})
        # 单实体 BR 的受约束实体是唯一元素：确定性派生（LLM 缺失/多实体时由 C24 兜底）
        if constrained_entity is None and len(entities_involved) == 1:
            constrained_entity = entities_involved[0]
        # branch_dimensions＝第一优先的显式参数；note.branch_dimension＝遗留形态
        # （字符串 ';'/'；' 分隔或列表），框架归一化：去重保序、逐项 esc、剥离 note 键。
        dims = []
        if branch_dimensions:
            dims.extend(branch_dimensions)
        if isinstance(note, dict) and note.get("branch_dimension"):
            legacy = note["branch_dimension"]
            if isinstance(legacy, str):
                legacy = [x.strip() for x in re.split(r"[;；]", legacy)
                          if x.strip()]
            dims.extend(legacy)
        dims = [esc(x) for x in dict.fromkeys(dims)]
        if isinstance(note, dict) and "branch_dimension" in note:
            note = {k: v for k, v in note.items()
                    if k != "branch_dimension"}
        self.business_rules.append({
            "id": bid, "category": category, "desc": esc(desc),
            "entities_involved": list(entities_involved),
            "constrained_entity": constrained_entity,
            "enforcement": derive_enforcement(bool(restrictive)),
            "restrictive": bool(restrictive),
            "source_ref": esc(source_ref),
            "note": _esc_note(note), "branch_dimensions": dims})
        return self

    def link_op_transition(self, entity, op, transitions, note=None):
        """op→转换结构化关联（glm5pr 3.3 自检 / §5 API）：替代 note.comment
        自由文本"crud 关联 tXX"约定——引用进参数、注释进 note。3.3 时点追加
        调用（转换已落盘，无需回改 1.4 的 add_entity）；assemble 时 _assign_ids
        把 transitions 改写为正式编号，渲染并入 op 记录 linked_transitions。
        跨实体关联须在 note 点名目标实体（C30 校验）。"""
        validate_llm("op_link", {"entity": entity, "op": op,
                                 "transitions": transitions, "note": note})
        self.op_links.append({"entity": entity, "op": op,
                              "transitions": list(transitions),
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
        self._backfill_semantic_branch_tt()   # 3.3 回填：语义描述→精确 tid，须在钩子前
        self._resolve_role_refs()             # 角色引用 id→name 归一化，输出统一 name
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
        # op_links → op.linked_transitions 渲染并入（输出侧合流；不反写
        # self.entities——避免框架改写 LLM 字段被反向校验拒。tid 已由
        # _assign_ids 统一为正式号）。
        by_link = {}
        for link in self.op_links:
            by_link.setdefault(link["entity"], {}).setdefault(
                link["op"], []).extend(link["transitions"])
        entities_out = []
        for e in self.entities:
            ops = []
            for o in e["operations"]:
                oo = dict(o)
                lts = by_link.get(e["id"], {}).get(o["name"])
                if lts:
                    oo["linked_transitions"] = list(lts)
                ops.append(oo)
            ee = dict(e)
            ee["operations"] = ops
            entities_out.append(ee)
        return {"_meta": self.meta,
                "_context": {"prohibition_config": self.prohibition_config,
                            "permissions": self.permissions},
                "domain_model": {
                    "entities": entities_out, "roles": self.roles,
                    "events": self.events,
                    "structural_relations": self.structural_relations,
                    "transition_relations": self.transition_relations},
                "state_and_flow": {"transitions": self.transitions},
                "constraints": {"invalid_transitions": self.invalid_transitions,
                                "cross_entity": self.cross_entity,
                                "business_rules": self.business_rules}}

    def _backfill_branch_coverage(self):
        """Step6：按转换 note.branch_dimension（支持';'分隔多值）与
        BR 顶层 branch_dimensions（add_br 归一化）、XC 的'分支[维度='前缀或
        source_transition 命中，回填三层 coverage。"""
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
                                   if name in (b.get("branch_dimensions") or [])]}

    def _backfill_semantic_branch_tt(self):
        """Step3.3 回填：branch target_transition 语义描述 → 精确 tid（确定性，无 LLM）。
        glm5pr :112/:155：前向引用先写语义描述，assemble 时框架回填为精确 tid；
        无唯一候选 → inferred＋记偏差（meta.branch_tt_deviations），P2 走 all-values 兜底。

        描述形态（LLM 前向引用）与匹配信号（按优先级）：
        - 动作等值：s == action（「报名审核通过」→ t08）
        - 路径形态：s 含「{frm}变为{to}」（esc 把 → 归一为 变为；
          「设计方案编制（待开始变为报名中路径）」→ t02，压制仅动作子串命中的 t01）
        - 动作包含：s 含 action 或 action 含 s（「评价人员开始评价（分值录入）」→
          action=评价人员开始评价；「实验室审核通过」→ action=审核通过）
        - 分支值消歧：同动作多候选时，to 为 s 中出现分支值者胜
          （「参加者测试与结果提交（已还样分支）」→ t19.to=已还样）
        搜索空间＝标注转换集 ∪ 维度实体全部转换（评分方式 分支指向未标
        branch_dimension 的 t41 即证——仅按标签作用域会漏）。跨实体标注有正当用例：
        v9「业务类型」(E-XM) 分支目标 t16/t16b 在 E-BMJL（§19.2 平行流程汇合点），
        故标注集不得收敛为本实体。跨实体候选仅作兜底：本实体有任意正分候选时外实
        体候选禁入（污染防护——外实体误标同维+动作撞车可唯一但错填）。创建转换
        （frm=None）不作路径匹配对象。唯一候选才回填，0/多候选一律记偏差（绝不猜）。"""
        formal_re = re.compile(r"[A-Z]+-\d{3}[a-z]?")
        backfilled, deviations = [], []
        for d in self.branch_dimensions:
            dim = d["dimension"]
            vals = [b["value"] for b in d["branches"] if b.get("value")]
            scope = {t["id"]: t for t in self.transitions
                     if dim in re.split(r"[;；]",
                                        t["note"].get("branch_dimension", ""))}
            for t in self.transitions:
                if t["entity"] == d["entity"]:
                    scope.setdefault(t["id"], t)

            def match(s):
                scored = []             # (id, entity, total)
                d_eq = f"{esc(dim)}={s}"
                # 描述引用分支值（取最长值，防 需还样⊂无需还样 子串碰撞）→
                # 命中 {D}={值} 约束前置的转换显著胜出（「…转换（需还样分支）」
                # → t30 的 还样要求=需还样 前置；描述无动作/落点信号可依）。
                v_star = max((v for v in vals if v in s), key=len, default=None)
                v_eq = f"{esc(dim)}={esc(v_star)}" if v_star else None
                # 创建转换目标：描述带「初始(变为|→)X」＝创建转换落点唯一锚 →
                # 仅候选 frm=None 且 to==X 命中（「设计方案编制创建转换（…初始变为
                # 待开始）」→ t01；frm=None 使 path 信号失效，须此锚；「受理用户
                # 测量审核报名创建转换（…初始变为报名中）」→ 只有 t40.to=报名中，
                # 报名创建族 to≠报名中 全让位）。
                m_init = re.search(r"初始变为([^）\s]+)", s)   # s 已 esc，→ 已归一为 变为
                init_to = m_init.group(1) if m_init else None
                self_loop = "自环" in s          # 描述标自环 → 候选 frm==to 命中
                for t in scope.values():
                    a = esc(t.get("action", ""))
                    to = esc(t.get("to", ""))
                    frm = t.get("from")             # add_trans 参数 frm，落盘键 from
                    path = bool(frm) and f"{esc(frm)}变为{to}" in s
                    # s 已 esc（add_branch_dimension），字面 → 恒不存在；约束前置按
                    # PRECOND_TYPES 权威枚举只取 constraint（state_ref/event_ref 不承载
                    # 「{D}={值}」门控文本）。
                    cons = [esc(p.get("text", ""))
                            for p in t.get("preconditions", [])
                            if p.get("type") == "constraint"]
                    total = 0
                    # 信号叠加而非取最高分：描述常携带多族信号，取最高分会丢弃
                    # 专属信号（「批量审核退回转换（待审批→审批退回）」的 path 30
                    # 被跨实体同名维度「审核结果=退回」约束 56 压掉 → 须相加）。
                    if any(d_eq in c for c in cons):
                        total += 60         # 约束前置精确形态 {D}={S}（最强信号：
                                            # 「报名审核结果=退回修改」→ t08b，动作层无信号）
                    elif v_eq and any(v_eq in c for c in cons):
                        total += 56         # 描述引用分支值 + 转换按 {D}={值} 前置
                                            # 门控（次强：比子串更具体，比精确 {D}={S} 弱）
                    elif any(s in c for c in cons):
                        total += 55         # 约束前置子串兜底
                    if s == to:
                        total += 50         # to 状态相等（落点差异经转换分立承载）
                    if s == a:
                        total += 40         # action 精确等值
                    if init_to and frm is None and to == esc(init_to):
                        total += 45         # 创建转换目标：frm=None 且 to==初始落点
                    if path:
                        total += 30         # {frm}变为{to} 路径
                    if self_loop and frm and frm == t.get("to"):
                        total += 40         # 描述标自环且候选为自环（自环无状态迁移，
                                            # 方向词不判，落点差异经转换分立承载）
                    if (a in s or s in a) and s != a:
                        total += 20         # action 子串（s==a 已由 40 族承载，不重复）
                    if to in s and to in vals:
                        total += 2          # 分支值落在该转换的 to → 消歧胜出
                    if dim in re.split(r"[;；]",
                                       t["note"].get("branch_dimension", "")):
                        total += 6          # 候选标注同维度 → 跨维度同名候选让位
                                            # （还样情况「已核查→待核查」t22 胜
                                            # t24——后者标项目类型非本维）
                    if total:
                        scored.append((t["id"], t["entity"], total))
                # 实体门：本实体有任意正分 → 外实体候选禁入（跨实体汇合仅作兜底，
                # 6 条合法跨实体回填均发生在本实体零正分时——v9 t16/t16b、v10/v11
                # t32；外实体靠误标+动作撞车胜出＝污染错填，须让位本实体）。
                if any(e == d["entity"] for _, e, _ in scored):
                    scored = [c for c in scored if c[1] == d["entity"]]
                if not scored:
                    return []
                top = max(t for _, _, t in scored)
                return sorted({i for i, _, t in scored if t == top})

            for br in d["branches"]:
                tt = br.get("target_transition", "")
                if not tt or formal_re.fullmatch(tt):   # 空=纯配置/展示；正式号=已回填
                    continue
                s = tt                                  # 已 esc（add_branch_dimension）
                uniq = match(s)
                if len(uniq) == 1:
                    br["target_transition"] = uniq[0]
                    backfilled.append({"dimension": dim, "entity": d["entity"],
                                       "value": br["value"], "from": s,
                                       "target_transition": uniq[0]})
                else:
                    br["inferred"] = True
                    deviations.append({"dimension": dim, "entity": d["entity"],
                                       "value": br["value"], "target_transition": s,
                                       "reason": "no_candidate" if not uniq
                                                 else f"ambiguous:{len(uniq)}"})
                    warnings.warn(
                        f"branch target_transition={s!r} (dimension={dim!r}, "
                        f"entity={d['entity']!r}) 非正式号形态，语义回填无唯一候选"
                        f"（{len(uniq)} 个），已记偏差(inferred=True)，"
                        f"P2 精确匹配将失败（走 all-values 兜底）", stacklevel=2)
        self.meta["branch_tt_backfilled"] = backfilled
        self.meta["branch_tt_deviations"] = deviations

    def _resolve_role_refs(self):
        """角色引用 id→name 归一化（数据层写 id 或 name，输出统一 name）。

        与编号移交同向（引用→正式形态）：id 是 LLM 自 mint 的精确句柄（r05），
        name 是原文逐字串——数据作者/LLM 优先写 id，name 引用也保留；
        输出统一为 name（人读可辨、与 name 系数据文件输出一致、下游透传零改动）。
        未知引用原样保留（悬空由 C01/C18 双键校验兜底）。确定性，无 LLM。"""
        name_by_id = {r["id"]: r["name"] for r in self.roles}

        def resolve(v):
            if isinstance(v, (list, tuple)):
                return [name_by_id.get(x, x) for x in v]
            return name_by_id.get(v, v) if isinstance(v, str) else v

        for e in self.entities:
            for o in e["operations"]:
                note = o.get("note")
                if isinstance(note, dict) and note.get("role") is not None:
                    note["role"] = resolve(note["role"])
        for p in self.permissions:
            if p.get("role"):
                p["role"] = name_by_id.get(p["role"], p["role"])
        for t in self.transitions:
            t["role"] = resolve(t["role"])

    def _build_trace(self):
        pre = [p for t in self.transitions for p in t["preconditions"]]
        sr = [p for p in pre if p["type"] == "state_ref"]
        return {
            "step0_events": len(self.events),
            "step1_entities": [e["id"] for e in self.entities],
            "step2_structural_relations": len(self.structural_relations),
            "step3_branch_dimensions": len(self.branch_dimensions),
            "step3_branch_tt_backfilled": len(self.meta.get("branch_tt_backfilled", [])),
            "step3_branch_tt_deviations": len(self.meta.get("branch_tt_deviations", [])),
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
            x["target_transition"] = rw(x["target_transition"])
            # desc 不直接 rw：改为按 xc_source 重建（前缀 + 注入正式标签），
            # 根治手写 "T-tXX" 双前缀（T-T-019）与 desc 残留局部标签。
            if x.get("xc_source"): 
                x["desc"] = rw(x["desc"])  
            x["desc"] = self._rebuild_xc_desc(x)
        for r in self.transition_relations:
            r["evidence_transitions"] = [rw(e) for e in r["evidence_transitions"]]
            r["desc"], r["trigger"] = rw(r["desc"]), rw(r["trigger"])
        # 分支 target_transition 三态归一化（在局部标签映射 rw 之上）：
        #  1) 局部标签（t01）→ rw 映射为正式号
        #  2) 纯正式号（T-001）→ 原样保留
        #  3) 「正式号+尾缀」（"T-001 设计方案编制（创建转换）"）→ 剥离尾缀归一到
        #     正式号（尾缀是语义描述，P2 精确匹配只认 tid；核心号须真实存在才剥离，
        #     防把任意文本误剥成不存在的号——不存在时留原样交给下方防御校验报错）。
        formal_ids = set(allmap.values())
        def _rw_branch_tt(tt):
            if not isinstance(tt, str):
                return tt
            tt = tt.strip()
            m = re.match(r"^([A-Z]+-\d{3}[a-z]?)\s+\S", tt)
            if m and m.group(1) in formal_ids:
                return m.group(1)
            return rw(tt)
        for d in self.branch_dimensions:
            for br in d["branches"]:
                br["target_transition"] = _rw_branch_tt(br.get("target_transition", ""))
        for t in self.transitions:
            if t["note"].get("comment"):
                t["note"]["comment"] = rw(t["note"]["comment"])
        for e in self.entities:
            for o in e["operations"]:
                if o["note"].get("comment"):
                    o["note"]["comment"] = rw(o["note"]["comment"])
        # op_links（结构化 op→转换通道，3.3 追加时点）：局部→正式 tid 改写，
        # 与 note.comment 文本通道并行，双通道统一编号（渲染并入见 _build_output）。
        for link in self.op_links:
            link["transitions"] = [rw(t) for t in link["transitions"]]
        # note 全域改写：结构/因果/BR note 与 invalid reason 补上，避免输出残留
        # 局部标签（如"XC x10"）与正式号不一致（INV-4 依赖此一致性）。
        for rel in self.structural_relations:
            note = rel.get("note")
            if isinstance(note, dict) and note.get("comment"):
                note["comment"] = rw(note["comment"])
        for r in self.transition_relations:
            note = r.get("note")
            if isinstance(note, dict) and note.get("comment"):
                note["comment"] = rw(note["comment"])
        for b in self.business_rules:
            note = b.get("note")
            if isinstance(note, dict) and note.get("comment"):
                note["comment"] = rw(note["comment"])
        for i in self.invalid_transitions:
            if i.get("reason"):
                i["reason"] = rw(i["reason"])
        # 语义描述拦截已迁至 _backfill_semantic_branch_tt（3.3 回填后残留=真偏差）。

    def _rebuild_xc_desc(self, x):
        """按 xc_source 重建 XC desc：前缀（XC_DESC_TPL）+ 注入正式标签。

        新数据（xc_source 显式传）→ desc 已是纯语义内容；旧数据（None）→ 用
        XC_LEGACY_RE 从旧 desc 前缀反推来源并剥掉前缀+残留"T-tXX"标签（golden
        冻结兼容）。label 注入：镜像/分支差异取 target_transition（消费者），
        联动取 source_transition（生产者）；缺省回退另一侧，再空则无 label。"""
        src = x.get("xc_source")
        semantic = x["desc"]
        if src is None:
            for cand, pat in XC_LEGACY_RE:
                if pat.match(semantic):
                    src, semantic = cand, pat.sub("", semantic)
                    break
            src = src or "镜像"                     # 兜底：无可识别前缀按镜像
        label = x.get("target_transition") or x.get("source_transition") or ""
        if src == "联动":
            label = x.get("source_transition") or x.get("target_transition") or ""
        x["xc_source"] = src
        tpl = XC_DESC_TPL.get(src)
        if not tpl:
            warnings.warn(f"XC {x['id']} xc_source={src!r} 无模板，desc 原样保留",
                          stacklevel=2)
            return semantic.strip()
        return tpl.format(label=label, desc=semantic.strip())