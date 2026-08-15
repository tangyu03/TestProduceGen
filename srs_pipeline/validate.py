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
                  self.c25_inv_mirror_target_transition):
            c()
        for fn in self._extra:
            fn(self, self.report)
        return self.report

    # 1. 引用完整性
    def c01_reference_integrity(self):
        r = self.report
        for t in self.m.transitions:
            d = self.dims.get((t["entity"], t["dimension"]))
            if t["entity"] not in self.entities:
                r.error("C01", f"引用未建模实体 {t['entity']}", t["id"])
            elif d is None:
                r.error("C01", f"引用未建模维度 {t['entity']}.{t['dimension']}", t["id"])
            else:
                for s in (t["from"], t["to"]):
                    if s is not None and s not in d["states"]:
                        r.error("C01", f"状态[{s}]不在 {t['dimension']} 的 states 中", t["id"])
            if t["role"] not in self.role_ids:
                r.error("C01", f"引用未收录角色 {t['role']}（system 豁免）", t["id"])
        for x in self.m.cross_entity:
            if x["source_transition"] not in self.trans:
                r.error("C01", f"XC 引用不存在的转换 {x['source_transition']}", x["id"])
            tt = x.get("target_transition")
            if tt and tt not in self.trans:
                r.error("C01", f"XC 引用不存在的消费者转换 {tt}", x["id"])
            for eid in (x["source_entity"], x["target_entity"]):
                if eid not in self.entities:
                    r.error("C01", f"XC 引用未建模实体 {eid}", x["id"])
        for b in self.m.business_rules:
            for eid in b["entities_involved"]:
                if eid not in self.entities:
                    r.error("C01", f"BR 引用未建模实体 {eid}", b["id"])
        for rel in self.m.structural_relations + self.m.transition_relations:
            for eid in (rel["from"], rel["to"]):
                if eid not in self.entities:
                    r.error("C01", f"关系引用未建模实体 {eid}")

    # 2. 状态结构（铁律10）
    def c02_state_structure(self):
        r = self.report
        by_dim = {}
        for t in self.m.transitions:
            by_dim.setdefault((t["entity"], t["dimension"]), []).append(t)
        for key, d in self.dims.items():
            ts, terminal = by_dim.get(key, []), set(d["terminal"])
            if not any(t["from"] is None and t["to"] == d["initial"] for t in ts):
                r.error("C02", f"{key[0]}.{key[1]} 初始状态[{d['initial']}]无创建转换")
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
                        r.warn("C02", f"终态[{t['from']}]有出边：该状态可能非终态，"
                                      f"复核 terminal（铁律10）", t["id"])

    # 3. preconditions 结构（铁律12）
    def c03_precondition_structure(self):
        r = self.report
        for t in self.m.transitions:
            for p in t["preconditions"]:
                if not isinstance(p, dict) or not p.get("text"):
                    r.error("C03", "precondition 必须为含非空 text 的对象（铁律12）", t["id"])
                    continue
                ptype = p.get("type")
                if ptype not in PRECOND_TYPES:
                    r.error("C03", f"precondition type 非法: {ptype!r}", t["id"])
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
        for d in self.m.branch_dimensions:
            cov = d.get("coverage") or {}
            for layer in ("transitions", "cross_entity", "business_rules"):
                if not cov.get(layer):
                    self.report.warn("C05", f"分支维度[{d['dimension']}]在 {layer} 层"
                                            f"无体现（穿透缺口；铁律2 不补生成，仅标记）")

    # 6. structural 一致性
    def c06_structural_consistency(self):
        r = self.report
        for rel in self.m.structural_relations:
            tag = f"{rel['from']}→{rel['to']}"
            if rel["cardinality"] == "N:1":
                r.error("C06", f"结构关系 {tag} 为 N:1（方向必须父→子）")
            expect = OWNERSHIP_BY_RELATION.get(rel["relation_type"])
            if expect and rel["ownership_dimension"] != expect:
                r.error("C06", f"{tag} 违反联动约束：{rel['relation_type']} 应配 {expect}")
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
                r.error("C07", f"因果 {key[0]}→{key[1]} 缺 trigger")
            if rel["trigger_source"] not in TRIGGER_SOURCES:
                r.error("C07", f"因果 {key[0]}→{key[1]} trigger_source 非法")
            ev = rel["evidence_transitions"]
            # bidi_coupling 同 desc/business_rule: 双向同步可无单一转换证据
            # (如 E-EXP↔E-USER 操作级同步,实体无状态机),note.comment 注明
            # 证据位置即可(4.5);否则按证据必填处理。
            if rel["trigger_source"] in ("desc", "business_rule", "bidi_coupling"):
                if not ev and not rel["note"].get("comment"):
                    r.warn("C07", f"{key[0]}→{key[1]} 证据为空且未注明证据位置（4.5）")
            elif not ev:
                r.error("C07", f"{key[0]}→{key[1]} evidence_transitions 必填（4.5）")
            if rel["trigger_source"] == "bidi_coupling" and not any(
                    s["from"] == rel["to"] and s["to"] == rel["from"]
                    for s in self.m.structural_relations):
                r.error("C07", f"bidi_coupling 缺反向结构关系 {key[1]}→{key[0]}")
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
                r.error("C11", "source_ref 必须非空（输入契约）", ref)

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
                    r.error("C12", f"category 非法: {o['category']!r}", ref)
                if not o.get("expected_results"):
                    r.error("C12", "expected_results 至少 1 条", ref)
                if o["name"] in seen:
                    r.error("C12", "同实体同名操作重复", ref)
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
                                                          for p in t.get(
                                                              "preconditions")
                                                          or []]
                                                  or er0 in (t.get(
                                                      "expected_results")
                                                      or []))))]
                        cands = [t["id"] for t in hits][:3]
                        cand_s = "、".join(cands) if cands \
                            else "无匹配转换（属性操作）"
                        r.warn(
                            "C12",
                            f"crud 操作未回填 T-xxx 关联（4.4⑤）；候选转换 "
                            f"{cand_s}：有状态效果→回填「对应转换 "
                            f"{cands[0] if cands else 'T-xxx'}」，属性操作→"
                            f"注明「无对应转换」及理由",
                            ref)

    # 13. direction 完整性
    def c13_direction(self):
        r = self.report
        for t in self.m.transitions:
            d = t.get("direction")
            if d not in DIRECTIONS:
                r.error("C13", f"direction 缺失或非法: {d!r}", t["id"])
                continue
            if t["from"] is None and d != "forward":
                r.error("C13", "创建转换 direction 必须为 forward", t["id"])
            if d == "resume" and t["from"] not in self.lateral_states:
                r.error("C13", f"resume 的 from[{t['from']}]非侧挂状态", t["id"])
            if d == "backward":
                dim = self.dims.get((t["entity"], t["dimension"]))
                if dim and t["from"] in dim["states"] and t["to"] in dim["states"]:
                    if dim["states"].index(t["to"]) >= dim["states"].index(t["from"]) \
                            and "环状机" not in t["note"].get("comment", ""):
                        r.warn("C13", "backward 但 to 索引不小于 from，"
                                      "且未注明环状机", t["id"])
        resumes = {t["from"] for t in self.m.transitions if t["direction"] == "resume"}
        for s, src_id in self.lateral_states.items():
            if s not in resumes:
                r.warn("C13",
                       f"侧挂状态[{s}]无 resume 返回边"
                       f"（由 {src_id} 标记为 lateral）", src_id)

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
                            "C16", f"{e['id']}.{d['dimension_name']} 状态[{s}]"
                                   f"在原文全文中不存在：状态值必须逐字取自原文"
                                   f"（如需保留请在 inferred 声明）", e["id"])
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
        for e in self.m.entities:
            for o in e["operations"]:
                ref = f"{e['id']}.{o['name']}"
                note = o.get("note")
                if not isinstance(note, dict) or "role" not in note:
                    self.report.error(
                        "C18", "operation 缺 note.role —— entity_obligations "
                               "actor 将为空（INV-6）", ref)
                    continue
                roles = note["role"]
                for r in ([roles] if isinstance(roles, str) else roles):
                    if r not in declared:
                        self.report.error(
                            "C18", f"note.role 引用未声明角色 {r!r}（INV-6）", ref)

    def c19_inv_signal_type(self):
        """INV-8/BR 信号：signal_type ∈ BR_SIGNALS。"""
        for b in self.m.business_rules:
            if b.get("signal_type") not in BR_SIGNALS:
                self.report.error(
                    "C19", f"signal_type={b.get('signal_type')!r} 不在 "
                           f"{BR_SIGNALS}（INV-8）", b["id"])

    def c20_inv_branch_br_coverage(self):
        """INV-7：每个分支维度须在 ≥1 条 BR 的 note.branch_dimension 出现。"""
        br_dims = {b["note"].get("branch_dimension")
                   for b in self.m.business_rules
                   if isinstance(b.get("note"), dict)}
        for d in self.m.branch_dimensions:
            if d["dimension"] not in br_dims:
                self.report.error(
                    "C20", f"分支维度[{d['dimension']}]无任何 BR 的 "
                           f"note.branch_dimension 承载（INV-7）", d["entity"])

    def c21_inv_label_refs(self):
        """INV-4：note/comment 中的标签引用须指向已存在条目。正式号（T-xxx…
        编号移交后形态）直查 valid；残存局部标签 = 未映射/已删除条目的引用
        （_assign_ids 已全域改写，残留即失联），报错。扫描面含 operation
        comment（C12 回填引用所在）。"""
        valid = ({t["id"] for t in self.m.transitions}
                 | {x["id"] for x in self.m.cross_entity}
                 | {b["id"] for b in self.m.business_rules}
                 | {i["id"] for i in self.m.invalid_transitions})
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
                        "C22", f"角色[{r['name']}]名含转换动词但 transitions.role "
                               f"0 次（INV-1）——若确无转换职责请在相关 note 说明理由")
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
                    "C23", f"XC 缺来源分类 xc_source（应在 {XC_SOURCES} 内）: "
                           f"{x['desc'][:40]!r}（INV-8）",
                    x["id"])

    def c25_inv_mirror_target_transition(self):
        """INV-XC：镜像类 XC 必须持有跨实体前置条件，即 target_transition 非空
        （记录「哪个转换持有该前置条件」，C04 补全与手动镜像同语义）。"""
        for x in self.m.cross_entity:
            if x.get("xc_source") == "镜像" and not x.get("target_transition"):
                self.report.error(
                    "C25", "镜像 XC 缺 target_transition（持有跨实体前置条件的"
                           "消费者转换）", x["id"])

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
                    "C24", f"BR[{bid}] 缺 constrained_entity（单实体应已派生，"
                           f"多实体须显式填写增删改 subject）")
            elif ce not in inv:
                self.report.error(
                    "C24", f"BR[{bid}] constrained_entity={ce!r} 不在 "
                           f"entities_involved={inv} 中")
            elif ce not in self.entities:
                self.report.error(
                    "C24", f"BR[{bid}] constrained_entity={ce!r} 引用未建模实体")
            elif len(inv) == 1 and ce != inv[0]:
                self.report.error(
                    "C24", f"BR[{bid}] 单实体 BR constrained_entity={ce!r} "
                           f"≠ 唯一元素 {inv[0]!r}（add_br 应已派生）")
