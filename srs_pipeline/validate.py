"""Step6 校验清单。每项校验对应 prompt 编号；能机械修复的自动修复并记入 report.fixes，
修复不了的报 error → 由 model.assemble 按 critical 中断（校验修复失败 → critical）。"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field

from .constants import (BR_SIGNALS, DIRECTIONS, LOCAL_LABEL, OP_CATEGORIES,
                        OWNERSHIP_BY_RELATION, PRECOND_TYPES, RESERVED_ROLES,
                        TRIGGER_PRIORITY, TRIGGER_SOURCES, XC_SOURCES)
from .escape import find_forbidden, find_unescaped

# 分支穿透豁免词：分支维度 impact_scope 含这些词时，transitions 层可无 branch
# 转换（纯计算/展示/筛选/查询型），BR 层仍须承载（INV-7 由 C20 硬校验）。
PURE_BRANCH_WORDS = ("纯计算", "计算型", "纯展示", "展示型",
                     "纯筛选", "筛选型", "纯查询", "查询型", "仅影响")


@dataclass
class Issue:
    check: str
    severity: str          # error | warning
    message: str
    ref: str = ""

@dataclass
class Report:
    issues: list = field(default_factory=list)
    fixes: list = field(default_factory=list)

    @property
    def errors(self):
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self):
        return [i for i in self.issues if i.severity == "warning"]

    def error(self, check, message, ref=""):
        self.issues.append(Issue(check, "error", message, ref))

    def warn(self, check, message, ref=""):
        self.issues.append(Issue(check, "warning", message, ref))

    def fix(self, message):
        self.fixes.append(message)

    def print(self):
        for i in self.issues:
            suffix = f" ({i.ref})" if i.ref else ""
            print(f"[{i.severity.upper():7}] {i.check}: {i.message}{suffix}")
        for f in self.fixes:
            print(f"[FIX    ] {f}")
        print(f"校验完成: {len(self.errors)} error / "
              f"{len(self.warnings)} warning / {len(self.fixes)} autofix")

class Validator:
    def __init__(self, model, output):
        self.m = model
        self.out = output
        self.report = Report()
        self._extra = []
        self.entities = {e["id"]: e for e in model.entities}
        # role 引用键: 转换的 role 用角色名(与 Step 4.3 的 name 逐字对齐, prompt
        # Step 0.5/4.1),C01 同时接受角色 ID 与角色名;system 为保留角色。
        self.role_ids = ({r["id"] for r in model.roles}
                         | {r["name"] for r in model.roles}
                         | set(RESERVED_ROLES))
        self.trans = {t["id"]: t for t in model.transitions}
        self.dims = {(e["id"], d["dimension_name"]): d
                     for e in model.entities for d in e["state_dimensions"]}
        # 侧挂状态 = lateral 转换的 to，同时记录来源转换 id 供 C13 定位
        # （键=状态名，值=标记它的 lateral 转换 id；dict 的 in 默认查 key）
        self.lateral_states = {t["to"]: t["id"] for t in model.transitions
                               if t["direction"] == "lateral"}

    @staticmethod
    def _hint(obj, problem, fix, example=""):
        """统一报错模板：对象定位｜问题｜修法｜示例。"""
        msg = f"{obj}: {problem}。修法：{fix}"
        if example:
            msg += f"。示例：{example}"
        return msg

    def register_check(self, fn):
        """扩展点：项目自定义校验 fn(validator, report)，在内置 13 项之后执行。"""
        self._extra.append(fn)
        return fn

    def run_all(self) -> Report:
        for c in (self.c01_reference_integrity, self.c02_state_structure,
                  self.c03_precondition_structure, self.c04_mirror_integrity,
                  self.c05_branch_penetration, self.c06_structural_consistency,
                  self.c07_causal_consistency, self.c08_composition_sync,
                  self.c09_cross_module, self.c10_char_safety,
                  self.c11_null_spec, self.c12_operations, self.c13_direction,
                  self.c14_expected_direction, self.c16_state_whitelist,
                  self.c17_structural_cd_review, self.c18_inv_operations_role,
                  self.c19_inv_signal_type, self.c20_inv_branch_br_coverage,
                  self.c21_inv_label_refs, self.c22_inv_role_coverage,
                  self.c23_inv_xc_desc_prefix, self.c24_inv_br_constrained_entity,
                  self.c25_inv_mirror_target_transition,
                  self.c26_inv_event_entity, self.c27_inv_event_coverage):
            c()
        for fn in self._extra:
            fn(self, self.report)
        return self.report

    # 1. 引用完整性
    def c01_reference_integrity(self):
        r = self.report
        declared_roles = sorted({x["name"] for x in self.m.roles})
        for t in self.m.transitions:
            d = self.dims.get((t["entity"], t["dimension"]))
            if t["entity"] not in self.entities:
                r.error("C01", self._hint(
                    t["id"], f"引用未建模实体 {t['entity']}",
                    "核对实体 ID 拼写或补建 add_entity",
                    f"已登记实体: {sorted(self.entities)}"), t["id"])
            elif d is None:
                r.error("C01", self._hint(
                    t["id"], f"引用未建模维度 {t['entity']}.{t['dimension']}",
                    "在该实体 state_dimensions 中补建该维度"), t["id"])
            else:
                for s in (t["from"], t["to"]):
                    if s is not None and s not in d["states"]:
                        r.error("C01", self._hint(
                            t["id"], f"状态[{s}]不在 {t['dimension']} 的 states 中",
                            "将该状态补入 states，或修正 from/to 取值"), t["id"])
            if t["role"] not in self.role_ids:
                r.error("C01", self._hint(
                    t["id"], f"引用未收录角色 {t['role']}",
                    "角色须先 add_role 登记，或用 system",
                    f"已登记角色: {declared_roles}"), t["id"])
        for x in self.m.cross_entity:
            if x["source_transition"] not in self.trans:
                r.error("C01", self._hint(
                    x["id"], f"XC 引用不存在的转换 {x['source_transition']}",
                    "改为已存在转换的局部标签/正式号",
                    f"已登记转换: {sorted(self.trans)}"), x["id"])
            tt = x.get("target_transition")
            if tt and tt not in self.trans:
                r.error("C01", self._hint(
                    x["id"], f"XC 引用不存在的消费者转换 {tt}",
                    "改为已存在转换的局部标签/正式号",
                    f"已登记转换: {sorted(self.trans)}"), x["id"])
            for eid in (x["source_entity"], x["target_entity"]):
                if eid not in self.entities:
                    r.error("C01", self._hint(
                        x["id"], f"XC 引用未建模实体 {eid}",
                        "核对实体 ID 或补建 add_entity",
                        f"已登记实体: {sorted(self.entities)}"), x["id"])
        for b in self.m.business_rules:
            for eid in b["entities_involved"]:
                if eid not in self.entities:
                    r.error("C01", self._hint(
                        b["id"], f"BR 引用未建模实体 {eid}",
                        "核对实体 ID 或补建 add_entity",
                        f"已登记实体: {sorted(self.entities)}"), b["id"])
        for rel in self.m.structural_relations + self.m.transition_relations:
            for eid in (rel["from"], rel["to"]):
                if eid not in self.entities:
                    r.error("C01", self._hint(
                        f"关系 {rel['from']}→{rel['to']}", f"引用未建模实体 {eid}",
                        "核对实体 ID 或补建 add_entity",
                        f"已登记实体: {sorted(self.entities)}"))

    # 2. 状态结构（铁律10）
    def c02_state_structure(self):
        r = self.report
        by_dim = {}
        for t in self.m.transitions:
            by_dim.setdefault((t["entity"], t["dimension"]), []).append(t)
        for key, d in self.dims.items():
            ts, terminal = by_dim.get(key, []), set(d["terminal"])
            if not any(t["from"] is None and t["to"] == d["initial"] for t in ts):
                r.error("C02", self._hint(
                    f"{key[0]}.{key[1]}", f"初始状态[{d['initial']}]无创建转换",
                    "补一条 frm=None 的创建转换",
                    f"add_trans(frm=None, to='{d['initial']}', …)"))
            outs = {t["from"] for t in ts if t["from"] is not None}
            for s in d["states"]:
                if s not in terminal and s not in outs:
                    r.warn("C02", f"{key[0]}.{key[1]} 非终态[{s}]无出边（4.4①）")
            for t in list(ts):
                if t["from"] in terminal:
                    if t["to"] in terminal:
                        self.m.transitions.remove(t)
                        r.fix(f"C02 铁律10: 移除终态间转换 {t['id']}"
                              f"（{t['from']}→{t['to']}），原数据应标 conflict")
                    elif "rollback" in t["traits"]:
                        r.warn("C02", f"rollback 转换的 from 为终态[{t['from']}]", t["id"])
                    else:
                        if t["from"] in d["terminal"]:
                            d["terminal"].remove(t["from"])
                            r.fix(
                                f"C02: {key[0]}.{key[1]} 终态[{t['from']}]有出边"
                                f"（转换 {t['id']}: {t['from']}→{t['to']}），"
                                f"已从 terminal 移除该状态（states/转换保持不变）"
                            )

    # 3. preconditions 结构（铁律12）
    def c03_precondition_structure(self):
        r = self.report
        for t in self.m.transitions:
            for p in t["preconditions"]:
                if not isinstance(p, dict) or not p.get("text"):
                    r.error("C03", self._hint(
                        t["id"], "precondition 必须为含非空 text 的对象",
                        "补 text 字段"), t["id"])
                    continue
                ptype = p.get("type")
                if ptype not in PRECOND_TYPES:
                    r.error("C03", self._hint(
                        t["id"], f"precondition type 非法: {ptype!r}",
                        "改为 PRECOND_TYPES 之一", f"合法值: {PRECOND_TYPES}"), t["id"])
                    continue
                if ptype == "state_ref":
                    ref = p.get("ref")
                    d = self.dims.get((ref.get("entity"), ref.get("dimension"))) \
                        if isinstance(ref, dict) else None
                    if d is None or ref.get("state") not in d["states"]:
                        p["type"], p["ref"] = "constraint", None
                        c = t["note"].get("comment", "")
                        t["note"]["comment"] = (c + "；" if c else "") + \
                            "state_ref 无法解析，降级 constraint（4.2.1）"
                        r.fix(f"C03: {t['id']} 前置条件[{p['text'][:20]}…] "
                              f"state_ref 解析失败，已降级 constraint")
                elif p.get("ref") is not None:
                    p["ref"] = None
                    r.fix(f"C03: {t['id']} {ptype} 的 ref 已置空")

    # 4. 镜像完整性（缺失则补）
    def c04_mirror_integrity(self):
        r = self.report
        # 覆盖判定按消费者侧去重：target_transition 记录「哪个转换持有跨实体
        # 前置条件」（手动 XC 与 C04 补全同语义）；source_transition 统一为
        # 生产者转换。旧版按 source_transition 去重会把手动 XC 的生产者 id
        # 与消费者 t["id"] 比较，误判每条手动 XC 未覆盖而重复补镜像。
        covered = {x["target_transition"] for x in self.m.cross_entity
                   if x.get("target_transition")}
        # 多消费者天然支持：同一 (source_entity, source_state, target_entity) 的
        # 消费者共享一个镜像 XC（如 struct x03 覆盖 t07-t10——它们都持有「评审
        # 计划状态=结束」这一跨实体前置状态）。XC 无 source_dimension 字段，故取
        # 三元组作最细粒度；golden 反向数据（source=消费者）不命中此集，走上面
        # 的 target_transition 去重。
        covered_refs = {(x["source_entity"], x["source_state"], x["target_entity"])
                        for x in self.m.cross_entity}
        for rel in self.m.transition_relations:
            covered.update(rel["evidence_transitions"])
        seq = len(self.m.cross_entity)
        for t in self.m.transitions:
            for p in t["preconditions"]:
                if p["type"] == "state_ref" and p.get("ref") \
                        and p["ref"]["entity"] != t["entity"] and t["id"] not in covered \
                        and (p["ref"]["entity"], p["ref"]["state"], t["entity"]) \
                            not in covered_refs:
                    seq += 1
                    xid = f"XC-{seq:03d}"
                    # 反查生产者：source_entity 上到达 source_state 的转换
                    # （与 P2 find_to_by_state 同语义，first-match）。
                    producer = next((tp["id"] for tp in self.m.transitions
                                     if tp["entity"] == p["ref"]["entity"]
                                     and tp["dimension"] == p["ref"]["dimension"]
                                     and tp["to"] == p["ref"]["state"]), None)
                    self.m.cross_entity.append({
                        "id": xid, "source_entity": p["ref"]["entity"],
                        "source_transition": producer or t["id"],
                        "source_state": p["ref"]["state"],
                        "target_entity": t["entity"],
                        "target_transition": t["id"],
                        "target_dimension": t["dimension"],
                        "target_condition": f"状态={t['from']}",
                        "desc": f"precondition'{p['text']}'",
                        "xc_source": "镜像",
                        "source_ref": t["source_ref"]})   # 输入契约：继承宿主
                    covered.add(t["id"])
                    r.fix(f"C04: 补镜像 {xid}（源自 {t['id']} 的跨实体前置条件）")

    # 5. 分支穿透
    def c05_branch_penetration(self):
        """分支穿透三层覆盖。transitions 层豁免纯计算/展示/筛选型维度
        （prompt：仅影响计算/展示的分支维度转换层无 branch 转换属合法，
        impact_scope 注明即可）；BR 层必填（INV-7 由 C20 硬校验）。
        cross_entity 层不设检查：分支差异 XC 可缺省（仅存在分支差异约束时写）。"""
        r = self.report
        for d in self.m.branch_dimensions:
            cov = d.get("coverage") or {}
            impact = d.get("impact_scope") or ""
            pure = any(w in impact for w in PURE_BRANCH_WORDS)
            if not cov.get("transitions") and not pure:
                r.warn("C05", self._hint(
                    f"分支维度[{d['dimension']}]", "在 transitions 层无体现",
                    "有 branch 转换则补 traits=['branch']；若属纯计算/展示/筛选型，"
                    "在 impact_scope 注明 '纯计算/纯展示/纯筛选' 等字样",
                    f"impact_scope='…；纯筛选型，不影响任何状态流转'"))
            if not cov.get("business_rules"):
                r.warn("C05", self._hint(
                    f"分支维度[{d['dimension']}]", "在 business_rules 层无体现",
                    "建/改一条 BR，在 note.branch_dimension 填维度名",
                    f"m.add_br(..., note={{\"branch_dimension\": \"{d['dimension']}\"}})"))
        # cross_entity 层：分支差异 XC 可缺省，不设检查

    # 6. structural 一致性
    def c06_structural_consistency(self):
        r = self.report
        for rel in self.m.structural_relations:
            tag = f"{rel['from']}→{rel['to']}"
            if rel["cardinality"] == "N:1":
                r.error("C06", self._hint(
                    tag, "cardinality 为 N:1（方向必须父→子）",
                    "调换 frm/to，或改为 1:N / M:N"))
            expect = OWNERSHIP_BY_RELATION.get(rel["relation_type"])
            if expect and rel["ownership_dimension"] != expect:
                r.error("C06", self._hint(
                    tag, f"违反联动约束：{rel['relation_type']} 应配 {expect}",
                    "修正 relation_type 或 ownership_dimension 使成套",
                    "合法配对仅 composition↔business_ownership、"
                    "reference↔configuration_source"))
            if rel["ownership_dimension"] == "management_dimension" \
                    and "复核" not in rel["note"].get("comment", ""):
                r.warn("C06", f"{tag} 为 management_dimension 但缺复核结论")

    # 7. transition_relations 一致性（铁律8 去重仅升级）
    def c07_causal_consistency(self):
        r = self.report
        seen = {}
        for rel in list(self.m.transition_relations):
            key = (rel["from"], rel["to"])
            if not rel.get("trigger"):
                r.error("C07", self._hint(
                    f"因果 {key[0]}→{key[1]}", "缺 trigger",
                    "补充触发描述（原文句式）"))
            if rel["trigger_source"] not in TRIGGER_SOURCES:
                r.error("C07", self._hint(
                    f"因果 {key[0]}→{key[1]}", f"trigger_source={rel['trigger_source']!r} 非法",
                    "改为 TRIGGER_SOURCES 之一", f"合法值: {TRIGGER_SOURCES}"))
            ev = rel["evidence_transitions"]
            # bidi_coupling 同 desc/business_rule: 双向同步可无单一转换证据
            # (如 E-EXP↔E-USER 操作级同步,实体无状态机),note.comment 注明
            # 证据位置即可(4.5);否则按证据必填处理。
            if rel["trigger_source"] in ("desc", "business_rule", "bidi_coupling"):
                if not ev and not rel["note"].get("comment"):
                    r.warn("C07", f"{key[0]}→{key[1]} 证据为空且未注明证据位置（4.5）")
            elif not ev:
                r.error("C07", self._hint(
                    f"因果 {key[0]}→{key[1]}", "evidence_transitions 必填（4.5）",
                    "填驱动方转换的局部标签/正式号"))
            if rel["trigger_source"] == "bidi_coupling" and not any(
                    s["from"] == rel["to"] and s["to"] == rel["from"]
                    for s in self.m.structural_relations):
                r.error("C07", self._hint(
                    f"因果 {key[0]}→{key[1]}", "bidi_coupling 缺反向结构关系",
                    "补一条反向 structural 关系",
                    f"add_structural(frm='{key[1]}', to='{key[0]}', …)"))
            if key in seen:                                    # 铁律8：去重，仅升级
                old = seen[key]
                if TRIGGER_PRIORITY[rel["trigger_source"]] < \
                        TRIGGER_PRIORITY[old["trigger_source"]]:
                    old["trigger_source"] = rel["trigger_source"]
                    old["trigger"] = rel["trigger"]
                old["evidence_transitions"] = sorted(
                    set(old["evidence_transitions"]) | set(ev))
                self.m.transition_relations.remove(rel)
                r.fix(f"C07 铁律8: 去重 {key[0]} 至 {key[1]}，"
                      f"保留 trigger_source={old['trigger_source']}")
            else:
                seen[key] = rel

    # 8. composition 同步性（违反则降级 reference）
    def c08_composition_sync(self):
        for rel in self.m.structural_relations:
            if rel["relation_type"] == "composition" \
                    and rel["ownership_dimension"] == "business_ownership":
                a, b = rel["from"], rel["to"]
                create = next((t for t in self.m.transitions
                               if t["entity"] == b and t["from"] is None), None)
                if not create:
                    continue
                ext = [p for p in create["preconditions"]
                       if p["type"] == "state_ref" and p.get("ref")
                       and p["ref"]["entity"] not in (a, b)]
                if ext:
                    rel["relation_type"] = "reference"
                    rel["ownership_dimension"] = "configuration_source"
                    self.report.fix(f"C08: {a} 至 {b} 降级 reference（B 创建依赖 "
                                    f"{ext[0]['ref']['entity']} 的后期状态）")

    # 9. 跨模块对账
    def c09_cross_module(self):
        r = self.report
        for coll in (self.m.transitions, self.m.invalid_transitions,
                     self.m.cross_entity, self.m.business_rules):
            ids = [x["id"] for x in coll]
            for i in sorted({i for i in ids if ids.count(i) > 1}):
                r.error("C09", f"编号重复: {i}")
        # 按起讫边分组，组内 action 不一致时做区分性检查
        by_edge = {}
        for t in self.m.transitions:
            key = (t["entity"], t["dimension"], t["from"], t["to"])
            by_edge.setdefault(key, []).append(t)
        for key, ts in by_edge.items():
            actions = {t["action"] for t in ts}
            if len(actions) <= 1:
                continue
            if not self._variants_distinguishable(ts):
                r.warn("C09",
                       f"同起讫转换动作不一致：{' / '.join(sorted(actions))}",
                       ts[0]["id"])

    @staticmethod
    def _extract_refs(t):
        """提取 precondition 中 state_ref 的 (entity, dimension, state) 三元组集合。"""
        return {(p["ref"]["entity"], p["ref"]["dimension"], p["ref"]["state"])
                for p in t["preconditions"]
                if p["type"] == "state_ref" and isinstance(p.get("ref"), dict)}

    def _variants_distinguishable(self, ts):
        """同起讫多动作转换是否可被 role 或 state_ref 区分为独立路径。"""
        for i, a in enumerate(ts):
            for b in ts[i + 1:]:
                if a["action"] == b["action"]:
                    continue
                if a["role"] != b["role"]:
                    continue              # role 不同 → 可区分，跳过
                if self._extract_refs(a) != self._extract_refs(b):
                    continue              # state_ref 不同 → 可区分，跳过
                return False              # role 和 state_ref 都相同 → 不可区分
        return True

    # 10. 字符安全（铁律4，等效 json.loads 验证）
    def c10_char_safety(self):
        r = self.report
        try:
            json.loads(json.dumps(self.out, ensure_ascii=False))
        except (TypeError, ValueError) as e:
            r.error("C10", f"JSON 序列化往返失败: {e}")
            return
        hits = find_forbidden(self.out)
        if hits:
            r.error("C10", f"残留箭头/弯引号 {len(hits)} 处，如 {hits[0][0]!r}"
                           f"（{hits[0][1]}…）")
        hits = find_unescaped(self.out)
        if hits:
            r.error("C10", f"残留未转义 <>& {len(hits)} 处，如 {hits[0][0]!r}"
                           f"（{hits[0][1]}…）")

    # 11. 空值规范（source_ref 豁免铁律9，必须非空）
    def c11_null_spec(self):
        r = self.report

        def need(obj, ref):
            if not obj.get("source_ref"):
                r.error("C11", self._hint(
                    ref, "source_ref 必须非空",
                    "补充原文定位引用",
                    "格式: 章节号（子项号），如 20.4.1.2（1）；20.5.1.3"))

        for e in self.m.entities:
            for o in e["operations"]:
                need(o, f"{e['id']}.{o['name']}")
        for coll in (self.m.transitions, self.m.cross_entity,
                     self.m.invalid_transitions, self.m.business_rules):
            for x in coll:
                need(x, x["id"])

    # 12. operations 完整性（铁律13 + 4.4⑤）
    def c12_operations(self):
        r = self.report
        nonstate = {"session", "ui", "file", "query", "config"}
        for e in self.m.entities:
            seen, actions = set(), {t["action"] for t in self.m.transitions
                                    if t["entity"] == e["id"]}
            for o in e["operations"]:
                ref = f"{e['id']}.{o['name']}"
                if o["category"] not in OP_CATEGORIES:
                    r.error("C12", self._hint(
                        ref, f"category 非法: {o['category']!r}",
                        "改为 OP_CATEGORIES 之一", f"合法值: {OP_CATEGORIES}"))
                if not o.get("expected_results"):
                    r.error("C12", self._hint(
                        ref, "expected_results 至少 1 条",
                        "补充可观察结果（含提示语）；原文未述以操作名短语补 + inferred"))
                if o["name"] in seen:
                    r.error("C12", f"同实体同名操作重复", ref)
                seen.add(o["name"])
                if o["category"] in nonstate and o["name"] in actions:
                    r.warn("C12", "无状态操作疑似误入 transitions（铁律13）", ref)
                if o["category"] == "crud":
                    # 4.4⑤ 回填两种合法形态: ①局部标签引用(如 "对应转换 t01;tp01",
                    # 铁律14 编号一律局部标签, 或框架改写后的 T-xxx); ②显式注明
                    # "无对应转换"及理由。二者皆满足即视为已回填。
                    comment = o["note"].get("comment", "")
                    _has_trans_ref = bool(re.search(
                        r"(?<![A-Za-z])(?:T-\d+|[tpou][a-z]*\d+)(?![A-Za-z])",
                         comment))
                    _has_explicit_none = "无对应转换" in comment
                    if not _has_trans_ref and not _has_explicit_none:
                        # 定位提示：候选转换 = 同实体上动作同名 / expected_result
                        # 与前提文本或结果一致的转换（正式号；P2 侧对应其 TO）。
                        # 纯数据驱动、无领域词。空 → 属性操作，提示"无对应转换"。
                        er0 = (o.get("expected_results") or [""])[0]
                        hits = [t for t in self.m.transitions
                                if t["entity"] == e["id"]
                                and (o["name"] == t.get("action")
                                     or (er0 and (er0 in [p.get("text") or ""
                                                          for p in t.get("preconditions") or []]
                                                  or er0 in (t.get("expected_results") or []))))]
                        if len(hits) == 1:
                            c = o["note"].get("comment") or ""
                            o["note"]["comment"] = f"{c}；对应转换 {hits[0]['id']}".lstrip("；")
                            r.fix(f"C12: 自动回填 {ref} → {hits[0]['id']}")
                        elif not hits:
                            c = o["note"].get("comment") or ""
                            o["note"]["comment"] = f"{c}；无对应转换（属性操作）".lstrip("；")
                            r.fix(f"C12: 未命中候选，自动标注 {ref} 为属性操作")
                        else:
                            ids = "、".join(t["id"] for t in hits[:4])
                            r.warn("C12", self._hint(
                                ref, f"crud 操作命中多条候选转换 [{ids}]",
                                "合并入口类，人工在 comment 指定对应转换",
                                f"note=N(..., comment=\"对应转换 {'；'.join(t['id'] for t in hits[:4])}\")"))

    # 13. direction 完整性
    def c13_direction(self):
        r = self.report
        for t in self.m.transitions:
            d = t.get("direction")
            if d not in DIRECTIONS:
                r.error("C13", self._hint(
                    t["id"], f"direction 缺失或非法: {d!r}",
                    "改为 DIRECTIONS 之一", f"合法值: {DIRECTIONS}"), t["id"])
                continue
            if t["from"] is None and d != "forward":
                t["direction"] = "forward"
                r.fix(f"C13: {t['id']} 创建转换 direction 已强制为 forward")
            if d == "resume" and t["from"] not in self.lateral_states:
                r.error("C13", self._hint(
                    t["id"], f"resume 的 from[{t['from']}]非侧挂状态",
                    "from 须为被 lateral 转换标记的状态",
                    f"当前侧挂状态: {sorted(self.lateral_states)}"), t["id"])
            if d == "backward":
                dim = self.dims.get((t["entity"], t["dimension"]))
                if dim and t["from"] in dim["states"] and t["to"] in dim["states"]:
                    comment = t["note"].get("comment", "")
                    semantic_override = any(
                        w in comment for w in ("环状机", "语义优先", "语义backward",
                                   "语义 backward", "语义优先backward"))
                    if dim["states"].index(t["to"]) >= dim["states"].index(t["from"]) \
                        and not semantic_override:
                        r.warn("C13", "backward 但 to 索引不小于 from，"
                          "且未注明环状机/语义优先", t["id"])

        resumes = {t["from"] for t in self.m.transitions if t["direction"] == "resume"}
        for s, src_id in self.lateral_states.items():
            if s in resumes:
                continue
            has_out = any(t["from"] == s for t in self.m.transitions)
            if has_out:
                r.warn("C13", f"侧挂状态[{s}]无 resume 返回边"
                      f"（由 {src_id} 标记为 lateral）", src_id)
            # 无出边的终态侧挂（如已撤销）无需 resume：无返回路径属设计语义，豁免

    def c14_expected_direction(self):
        """expected_results 中"由X变为Y"与 from/to 对账（抓 T-003 类笔误）。"""
        pat = re.compile(r"由(.{1,12}?)变为(.{1,12}?)(?=[（(，。；;]|$)")
        for t in self.m.transitions:
            for e in t["expected_results"]:
                hit = pat.search(e)
                if not hit:
                    continue
                if t["from"] and hit.group(1) != t["from"]:
                    self.report.warn("C14", f"结果文本起态[{hit.group(1)}]≠"
                                            f"from[{t['from']}]", t["id"])
                if t["to"] and not hit.group(2).startswith(t["to"]):
                    self.report.warn("C14", f"结果文本讫态[{hit.group(2)}]≠"
                                            f"to[{t['to']}]", t["id"])

    # 17. structural (c)/(d) 判定一致性复核（4.4 框架兜底窄版）
    def c17_structural_cd_review(self):
        """composition+business_ownership 的 B 若满足独立创建且非被持有
        → warning 疑似应判 (d) reference。仅单向：B 属 (b)（创建依赖 A）或 (c)
        （被 A 持有）时豁免。(c) 的"A 为业务归属容器"语义无法直接机械判定，
        用两个代理信号：① B 自身为某 composition 的 frm（有 dependent）；
        ② A 的删除约束涉及 B（A 不可在有 B 时删除，如"机构下无项目才可删除"），
        ② 比 ① 更贴近归属本质，覆盖"叶子实体被容器持有"场景。B 的 core/managed
        类型不参与豁免——容器信号本身即可判定（如 E-YH 为 managed 但被 E-JG
        持有且自身也是 E-XTRG 的 frm）。反向（reference 但 B 实为 (c)）同依赖
        "A 为业务归属容器"语义，机械不可判，不做。C08 已处理创建依赖第三方后期
        状态的另一条降级路径，本检查补充"独立创建"分支。"""
        r = self.report
        # B 是否有独立创建流程：存在 from=None 且其 precondition 不 state_ref 指向 A
        # （指向 A 说明 B 是 A 的产物，属 (b) composition，豁免）。
        creates = {}
        for t in self.m.transitions:
            if t["from"] is None:
                creates.setdefault(t["entity"], []).append(t)
        # B 是否有 dependent：B 是否作为某 composition 的 frm（被其他实体挂靠）
        comp_frms = {rel["from"] for rel in self.m.structural_relations
                     if rel["relation_type"] == "composition"}
        for rel in self.m.structural_relations:
            if not (rel["relation_type"] == "composition"
                    and rel["ownership_dimension"] == "business_ownership"):
                continue
            a, b = rel["from"], rel["to"]
            creates_b = creates.get(b) or []
            if not creates_b:
                continue                                  # 无独立创建 → (b) 豁免
            driven_by_a = any(
                p["type"] == "state_ref" and p.get("ref")
                and p["ref"]["entity"] == a
                for t in creates_b for p in t["preconditions"])
            if driven_by_a:
                continue                                  # 创建依赖 A → (b) 豁免
            be = self.entities.get(b)
            b_type = be["type"] if be else None
            if b in comp_frms or self._a_is_container(a, b):
                continue                                  # 满足 (c) → 豁免
            r.warn("C17",
                   f"结构关系 {a}→{b} 为 composition+business_ownership，"
                   f"但 B 有独立创建流程[{', '.join(t['id'] for t in creates_b)}]"
                   f"且不满足 (c)（type={b_type}，有 dependent={b in comp_frms}，"
                   f"comp_frms={sorted(comp_frms)}），疑似应判 (d) reference"
                   f"+configuration_source（Step 2）",
                   rel.get("desc", f"{a}→{b}"))

    def _a_is_container(self, a, b):
        """A 是否为 B 的业务归属容器（C17 (c) 豁免代理②）：A 的删除约束涉及 B。
        首选结构判定——删除类 BR 的 entities_involved 同时含 A 与 B（如 b46
        "机构下无项目、无用户才可删除" 列 E-JG/E-XM/E-YH），无需文本匹配；
        兜底——A 的删除类 crud op 的 expected_results 文本含 B 的实体名
        （覆盖删除 op 尚无配对 BR 的场景）。数据驱动，无硬编码实体名。"""
        # ① 删除类 BR：entities_involved 结构判定
        for br in self.m.business_rules:
            inv = br.get("entities_involved", [])
            if a in inv and b in inv and "删除" in br.get("desc", ""):
                return True
        # ② 删除类 crud op：expected_results 文本兜底
        b_name = (self.entities.get(b) or {}).get("name", "")
        if not b_name:
            return False
        a_entity = self.entities.get(a)
        if a_entity:
            for op in a_entity.get("operations", []):
                if "删除" not in op.get("name", ""):
                    continue
                if any(b_name in text for text in op.get("expected_results", [])):
                    return True
        return False

    def c16_state_whitelist(self):
        """状态值/顺序与原文枚举对账（铁律2 的机器版，替代一切'禁止改名'补丁）。
        三级判定：不在任何枚举但出现在原文其他位置 → warning（合理推断）；
        经 inferred 显式声明的推断态 → warning（如 E-SCORE 隐式初态'未打分'）；
        全文查无此值且未声明 → error（改写漂移，如'正常'之于'未锁定'）。"""
        if not getattr(self.m, "evidence", None):
            return
        from .evidence import best_enum_match
        for e in self.m.entities:
            for d in e["state_dimensions"]:
                span, covered = best_enum_match(d["states"], self.m.evidence)
                missing = [s for s in d["states"] if s not in covered]
                declared = set(d.get("inferred", []) or [])
                for s in missing:
                    if s in declared:
                        self.report.warn(
                            "C16", f"{e['id']}.{d['dimension_name']} 状态[{s}]"
                                   f"原文无逐字状态名，但已在 inferred 声明"
                                   f"为合理推断", e["id"])
                    elif s in (self.m.doc_text or ""):
                        self.report.warn(
                            "C16", f"{e['id']}.{d['dimension_name']} 状态[{s}]"
                                   f"不在原文枚举行中（全文其他位置出现，"
                                   f"请确认是推断值）", e["id"])
                    else:
                        self.report.error(
                            "C16", self._hint(
                                f"{e['id']}.{d['dimension_name']} 状态[{s}]",
                                "在原文全文中不存在",
                                "状态值必须逐字取自原文；确需保留则在 inferred 声明",
                                "inferred=[...] + note.comment 写依据"), e["id"])
                if span and not missing:
                    ordered = [v for v in span.values if v in set(d["states"])]
                    if d["states"] != ordered:
                        self.report.warn(
                            "C16", f"{e['id']}.{d['dimension_name']} states 顺序"
                                   f"与原文枚举不一致：{d['states']} ≠ {ordered}",
                            e["id"])

    # ============ C18-C23：glm5pr §6 全局不变量机器化 ============
    # 吸收自 validate_srs.py（C11/C8/C6/C2/C1/C7）。豁免集只含 RESERVED_ROLES，
    # 不追加项目角色名（项目角色一律进 add_role 声明）；标签形态与 XC 前缀取自
    # constants 单一事实源，不内联硬编码。
    # 正式号（编号移交后形态）：T-065 / XC-010 / BR-023 / IT-002
    _FORMAL_LABEL = re.compile(r"\b(?:T|XC|BR|IT)-\d{3}[a-z]?\b")

    @staticmethod
    def _flatten(obj):
        """递归展平 note/comment 为文本，用于局部标签扫描。"""
        if obj is None:
            return ""
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            return " ".join(Validator._flatten(v) for v in obj.values())
        if isinstance(obj, list):
            return " ".join(Validator._flatten(v) for v in obj)
        return str(obj)

    def c18_inv_operations_role(self):
        """INV-6/R-OPROLE：每条 operation 的 note 必须含 role（单角色字符串或
        多角色列表），且逐一命中已声明角色或保留角色。缺失 → entity_obligations
        actor 为空，静默退化。"""
        declared = {r["name"] for r in self.m.roles} | set(RESERVED_ROLES)
        role_names = sorted({r["name"] for r in self.m.roles})
        for e in self.m.entities:
            for o in e["operations"]:
                ref = f"{e['id']}.{o['name']}"
                note = o.get("note")
                if not isinstance(note, dict) or "role" not in note:
                    self.report.error(
                        "C18", self._hint(
                            ref, "operation 缺 note.role",
                            "在 op 的 note 加 role 字段（取 add_role 的 name 或 system）",
                            f"note=N(role=\"项目管理员\") 或 note=N(role=[\"a\",\"b\"])；"
                            f"已登记角色: {role_names}"))
                    continue
                roles = note["role"]
                for r in ([roles] if isinstance(roles, str) else roles):
                    if r not in declared:
                        self.report.error(
                            "C18", self._hint(
                                ref, f"note.role 引用未声明角色 {r!r}",
                                "改为已登记角色或 system",
                                f"已登记角色: {role_names}"))

    def c19_inv_signal_type(self):
        """INV-8/BR 信号：signal_type ∈ BR_SIGNALS。"""
        for b in self.m.business_rules:
            if b.get("signal_type") not in BR_SIGNALS:
                self.report.error(
                    "C19", self._hint(
                        b["id"], f"signal_type={b.get('signal_type')!r} 非法",
                        "改为 BR_SIGNALS 之一", f"合法值: {BR_SIGNALS}"))

    def c20_inv_branch_br_coverage(self):
        """INV-7：每个分支维度须在 ≥1 条 BR 的 note.branch_dimension 出现。"""
        br_dims = {b["note"].get("branch_dimension")
                   for b in self.m.business_rules
                   if isinstance(b.get("note"), dict)}
        for d in self.m.branch_dimensions:
            if d["dimension"] not in br_dims:
                self.report.error(
                    "C20", self._hint(
                        f"分支维度[{d['dimension']}]", "无任何 BR 的 note.branch_dimension 承载",
                        "建/改一条 BR 并在 note 挂 branch_dimension",
                        f"m.add_br(..., note={{\"branch_dimension\": \"{d['dimension']}\"}})"),
                    d["entity"])

    def c21_inv_label_refs(self):
        """INV-4：note/comment 中的标签引用须指向已存在条目。正式号（T-xxx…
        编号移交后形态）直查 valid；残存局部标签 = 未映射/已删除条目的引用
        （_assign_ids 已全域改写，残留即失联），报错。扫描面含 operation
        comment（C12 回填引用所在）。"""
        valid = ({t["id"] for t in self.m.transitions}
                 | {x["id"] for x in self.m.cross_entity}
                 | {b["id"] for b in self.m.business_rules}
                 | {i["id"] for i in self.m.invalid_transitions}
                 | {r["id"] for r in self.m.roles}
                 | {ev["id"] for ev in self.m.events})
        scanned = []
        for t in self.m.transitions:
            scanned.append((t["id"], self._flatten(t.get("note"))))
        for e in self.m.entities:
            for o in e["operations"]:
                scanned.append((f"{e['id']}.{o['name']}",
                                self._flatten(o.get("note"))))
        for x in self.m.cross_entity:
            scanned.append((x["id"], self._flatten(x.get("desc"))))
        for b in self.m.business_rules:
            scanned.append((b["id"], self._flatten(b.get("note"))))
        for i in self.m.invalid_transitions:
            scanned.append((i["id"], self._flatten(i.get("reason"))))
        for rel in self.m.transition_relations + self.m.structural_relations:
            scanned.append((f"rel:{rel['from']}→{rel['to']}",
                            self._flatten(rel.get("note"))))
        for src, text in scanned:
            text = text or ""
            for ref in self._FORMAL_LABEL.findall(text):
                if ref not in valid:
                    self.report.error(
                        "C21", f"{src} 引用不存在的正式号 {ref!r}（INV-4）")
            for ref in LOCAL_LABEL.findall(text):
                if ref not in valid:
                    self.report.error(
                        "C21", f"{src} 引用未映射的局部标签 {ref!r}（INV-4）")

    def c22_inv_role_coverage(self):
        """INV-1：承担转换型职责的角色须在 transitions.role ≥1 次。转换型语义
        用项目自声明的 action_verbs 判定（角色名含动词且 0 次 → 强警告），零内联
        硬编码；note 说明无转换职责可豁免，故不升 error。"""
        verbs = list(self.m.prohibition_config.get("action_verbs") or [])
        used = {t["role"] for t in self.m.transitions}
        for r in self.m.roles:
            if r["name"] in RESERVED_ROLES or r["readonly"]:
                continue
            if r["name"] not in used:
                if any(v in r["name"] for v in verbs):
                    self.report.warn(
                        "C22", self._hint(
                            f"角色[{r['name']}]", "名含转换动词但 transitions.role 0 次",
                            "若确无转换职责，在相关 note 说明理由"))
                else:
                    self.report.warn(
                        "C22", f"角色[{r['name']}]在 transitions.role 0 次"
                               f"（crud-only 可接受，INV-1）")

    def c23_inv_xc_desc_prefix(self):
        """INV-8/XC：desc 来源分类须显式（xc_source ∈ 四来源）。desc 前缀现由
        assemble 按 xc_source 生成，不再作为来源判定依据。"""
        for x in self.m.cross_entity:
            if x.get("xc_source") not in XC_SOURCES:
                self.report.warn(
                    "C23", self._hint(
                        x["id"], f"XC 缺来源分类 xc_source（应在 {XC_SOURCES} 内）",
                        "显式传 xc_source 之一", f"合法值: {XC_SOURCES}"))

    def c25_inv_mirror_target_transition(self):
        """INV-XC：镜像类 XC 必须持有跨实体前置条件，即 target_transition 非空
        （记录「哪个转换持有该前置条件」，C04 补全与手动镜像同语义）。"""
        for x in self.m.cross_entity:
            if x.get("xc_source") == "镜像" and not x.get("target_transition"):
                self.report.error(
                    "C25", self._hint(
                        x["id"], "镜像 XC 缺 target_transition",
                        "填持有该跨实体前置条件的消费者转换（局部标签/正式号）"),
                    x["id"])

    def c24_inv_br_constrained_entity(self):
        """INV-BR/constrained_entity：BR 的受约束实体须显式、合法且一致。

        运行受 BR 门禁的实体是确定性宿主选择的基础（S1 crud/negative_test 依赖）。
        - 缺失：多实体 BR 未填（单实体已由 add_br 派生，恒有值）
        - 不在 entities_involved：声明了非本 BR 涉及的实体
        - 未建模：引用不存在的实体 ID
        - 单实体错位：与唯一元素不一致（防御 add_br 派生逻辑未来的改动）
        """
        for b in self.m.business_rules:
            bid = b["id"]
            ce = b.get("constrained_entity")
            inv = b.get("entities_involved", [])
            if ce in (None, ""):
                self.report.error(
                    "C24", self._hint(
                        f"BR[{bid}]", "缺 constrained_entity",
                        "增删改门禁→填操作对象实体；对称规则→取任一 involved 实体"
                        "并在 note.comment 注明'代表实体'",
                        'constrained_entity="E-XXX"'))
            elif ce not in inv:
                self.report.error(
                    "C24", self._hint(
                        f"BR[{bid}]", f"constrained_entity={ce!r} 不在 "
                                      f"entities_involved={inv} 中",
                        "改为 involved 实体之一", f"involved: {inv}"))
            elif ce not in self.entities:
                self.report.error(
                    "C24", self._hint(
                        f"BR[{bid}]", f"constrained_entity={ce!r} 引用未建模实体",
                        "改为已登记实体", f"已登记实体: {sorted(self.entities)}"))
            elif len(inv) == 1 and ce != inv[0]:
                self.report.error(
                    "C24", self._hint(
                        f"BR[{bid}]", f"单实体 BR constrained_entity={ce!r} "
                                      f"≠ 唯一元素 {inv[0]!r}",
                        "与唯一元素保持一致", f"应填: {inv[0]}"))

    def c26_inv_event_entity(self):
        """F15：事件台账主体列映射的实体须已登记。台账是转换推导的唯一输入，
        主体未建模 → 转换 entity 落空、下游不可用。"""
        registered = {e["id"] for e in self.m.entities}
        for ev in self.m.events:
            if ev["entity"] not in registered:
                self.report.error(
                    "C26", self._hint(
                        f"事件[{ev['id']}]", f"主体映射实体 {ev['entity']!r} 未建模",
                        "改为已登记实体 id", f"已登记: {sorted(registered)}"),
                    ev["id"])

    def c27_inv_event_coverage(self):
        """F10：台账双向覆盖——每事件被 ≥1 产物（转换/结构·因果关系的 note）消费，
        每转换 note 引用 ≥1 事件 id。inferred 转换（状态机闭环、无台账事件对应，
        note.comment 含「inferred」）豁免反向检查。台账完备性是根本职责，无机械兜底。"""
        event_ids = {ev["id"] for ev in self.m.events}
        if not event_ids:
            return
        consumed: set[str] = set()
        reverse_bad: list[str] = []
        for t in self.m.transitions:
            note = self._flatten(t.get("note")) or ""
            refs = set(LOCAL_LABEL.findall(note)) & event_ids
            consumed |= refs
            if not refs and "inferred" not in note:
                reverse_bad.append(t["id"])
        for rel in self.m.transition_relations + self.m.structural_relations:
            consumed |= set(LOCAL_LABEL.findall(self._flatten(rel.get("note")))) & event_ids
        for ev in self.m.events:
            if ev["id"] not in consumed:
                self.report.error(
                    "C27", self._hint(
                        f"事件[{ev['id']}]",
                        f"{ev['entity']}.{ev['dimension']} 的 {ev['action']!r} "
                        f"未被任何转换/关系 note 消费",
                        "确认该事件对应的转换已建且 note.comment 引用其 id"))
        for tid in reverse_bad:
            self.report.error(
                "C27", self._hint(
                    f"转换[{tid}]", "note 未引用任何事件 id",
                    "note.comment 引用其来源事件 id（如「源自 e03」）；"
                    "状态机闭环转换在 note 注明 inferred 豁免"))
