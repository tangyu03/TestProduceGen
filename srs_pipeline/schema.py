"""字段注册表：LLM 层（DSL 参数）与框架层（输出 JSON）的单一事实源。

每对象一张 Field 表。写者语义（written_by）：
- LLM           LLM 写，框架不改。
- LLM_MUTATED   LLM 写，框架改写。mutation_conditions 区分改写时机：
                None      = 总是改写（如编号移交，_assign_ids 无条件执行）；
                "<C0X>"   = 条件性改写（仅在对应校验器触发时）；
                "_assign_ids" = 引用改写（编号移交的一部分，条件触发由调用结构决定）。
- FRAMEWORK     LLM 无名字（dsl=None），纯框架加工字段。

rename_reason（dsl≠out 的两类性质，避免维护时混为一谈）：
- py_keyword    参数名≠输出键纯为语法规避（frm→from），与框架行为无关、永不改变。
- id_transfer   局部标签→正式编号，属 _assign_ids 的加工行为。

约束：add_* 方法必须从 validate_llm 校验参数；凡 add_* 用到而注册表未登记的参数、
凡登记为 required 而未传的参数、凡枚举不合法，一律 fail-fast 报错——改 add_*
的人必须同步改本表，否则校验失败。反向校验脚本见 scripts/verify_schema.py。
"""
from __future__ import annotations

from .constants import (BR_CATEGORIES, BR_ENFORCEMENTS, BR_SIGNALS, CARDINALITIES,
                        CONFIDENCE, DIRECTIONS, ENTITY_TYPES, OWNERSHIP_DIMS,
                        PRIORITIES, RELATION_TYPES, TAGS, TRAITS, TRIGGER_SOURCES)

LLM = "llm"
LLM_MUTATED = "llm_mutated"
FRAMEWORK = "framework"


class Field:
    __slots__ = ("dsl", "out", "written_by", "rename_reason",
                 "mutation_conditions", "enum", "required", "derived_from", "desc")

    def __init__(self, out, dsl=None, written_by=LLM, rename_reason=None,
                 mutation_conditions=None, enum=None, required=False,
                 derived_from=None, desc=""):
        self.out = out                    # 输出 JSON 键
        self.dsl = dsl                    # LLM 侧参数名；None = 纯框架字段
        self.written_by = written_by
        self.rename_reason = rename_reason
        self.mutation_conditions = mutation_conditions
        self.enum = enum
        self.required = required
        self.derived_from = derived_from
        self.desc = desc

    @property
    def is_framework(self) -> bool:
        return self.written_by == FRAMEWORK

    def __repr__(self):
        return (f"<Field {self.out} dsl={self.dsl!r} {self.written_by}"
                f"{(' mc='+self.mutation_conditions) if self.mutation_conditions else ''}>")


# ---- 对象注册表：out 键 → Field ----
# 一级字段表。嵌套子结构（state_dimensions/operations/preconditions/branches）
# 在主表 desc 注明；子键的改写（如 operations[].note.comment、
# branches[].target_transition 的引用改写）标在父字段的 mutation_conditions。

OBJECT_SCHEMA: dict[str, list[Field]] = {
    "role": [
        Field("id", "id", LLM, desc="局部标签，prompt 承诺 R-xxx 移交未实现（漂移#2）"),
        Field("name", "name", LLM, required=True),
        Field("readonly", "readonly", LLM, required=True),
    ],
    "permission": [
        Field("role", "role", LLM, required=True, desc="与 add_role 的 name 逐字对齐"),
        Field("operations", "operations", LLM, required=True),
    ],
    "prohibition_config": [
        Field("action_verbs", "action_verbs", LLM, required=True),
        Field("prohibit_keywords", "prohibit_keywords", LLM),
        Field("negation_prefixes", "negation_prefixes", LLM),
        Field("transition_indicators", "transition_indicators", LLM),
        Field("success_hints", "success_hints", LLM),
    ],
    "entity": [
        Field("id", "id", LLM, required=True, desc="E-{缩写}，LLM 写正式格式，框架不改"),
        Field("name", "name", LLM, required=True),
        Field("desc", "desc", LLM, required=True),
        Field("type", "type", LLM, enum=ENTITY_TYPES, required=True),
        Field("tags", "tags", LLM, enum=TAGS, desc="数组元素 ∈ TAGS"),
        Field("attributes", "attributes", LLM,
              desc="嵌套 [{name,desc,is_config}]"),
        Field("state_dimensions", "state_dimensions", LLM,
              desc="嵌套 [{dimension_name,states[],initial,terminal,note}]，"
                   "states 元素为字符串或 {value,inferred?,note?}"),
        Field("operations", "operations", LLM_MUTATED, mutation_conditions="_assign_ids",
              desc="嵌套 op(); note.comment 的引用被 _assign_ids 改写"),
    ],
    "structural": [
        Field("from", written_by=LLM, rename_reason="py_keyword", required=True,
              dsl="frm"),
        Field("to", "to", LLM, required=True),
        Field("relation_type", "relation_type", LLM_MUTATED, enum=RELATION_TYPES,
              required=True, mutation_conditions="C08", desc="C08 可降级 reference"),
        Field("cardinality", "cardinality", LLM, enum=CARDINALITIES, required=True),
        Field("ownership_dimension", "ownership_dimension", LLM_MUTATED, enum=OWNERSHIP_DIMS,
              required=True, mutation_conditions="C08", desc="C08 可降级 configuration_source"),
        Field("desc", "desc", LLM, required=True),
        Field("confidence", "confidence", LLM, enum=CONFIDENCE),
        Field("note", "note", LLM),
    ],
    "branch_dimension": [
        Field("dimension", "dimension", LLM, required=True),
        Field("entity", "entity", LLM, required=True),
        Field("values", "values", LLM, required=True),
        Field("impact_scope", "impact_scope", LLM, required=True),
        Field("evidence", "evidence", LLM, required=True),
        Field("branches", "branches", LLM_MUTATED, required=True, mutation_conditions="_assign_ids",
              desc="嵌套 [{value,target_transition,desc}]；target_transition 被改写"),
        Field("coverage", None, FRAMEWORK, required=True,
              derived_from="_backfill_branch_coverage", desc="T/XC/BR 三层回填"),
    ],
    "trans": [
        Field("id", written_by=LLM_MUTATED, rename_reason="id_transfer",
              required=True, dsl="tid"),
        Field("entity", "entity", LLM, required=True),
        Field("dimension", "dimension", LLM, required=True),
        Field("from", written_by=LLM, rename_reason="py_keyword", dsl="frm",
              desc="创建转换可为 None"),
        Field("to", "to", LLM, required=True),
        Field("action", "action", LLM, required=True),
        Field("role", "role", LLM, required=True),
        Field("preconditions", "preconditions", LLM_MUTATED, required=True,
              mutation_conditions="C03",
              desc="嵌套 precond(); C03 可将 state_ref 降级 constraint"),
        Field("expected_results", "expected_results", LLM, required=True),
        Field("traits", "traits", LLM, enum=TRAITS, required=True),
        Field("direction", "direction", LLM, enum=DIRECTIONS, required=True),
        Field("priority", "priority", LLM, enum=PRIORITIES, required=True),
        Field("source_ref", "source_ref", LLM, required=True),
        Field("note", "note", LLM_MUTATED, mutation_conditions="C03; _assign_ids",
              desc="C03 追加降级 comment；comment 引用被 _assign_ids 改写"),
    ],
    "causal": [
        Field("from", written_by=LLM, rename_reason="py_keyword", required=True, dsl="frm"),
        Field("to", "to", LLM, required=True),
        Field("desc", "desc", LLM_MUTATED, mutation_conditions="_assign_ids",
              desc="引用被 _assign_ids 改写"),
        Field("trigger", "trigger", LLM_MUTATED, mutation_conditions="_assign_ids; C07",
              desc="引用被 _assign_ids 改写；C07 铁律8 升级时改写"),
        Field("trigger_source", "trigger_source", LLM_MUTATED, enum=TRIGGER_SOURCES,
              required=True, mutation_conditions="C07", desc="C07 铁律8 升级时改写"),
        Field("evidence_transitions", "evidence_transitions", LLM_MUTATED, required=True,
              mutation_conditions="_assign_ids; C07",
              desc="引用被 _assign_ids 改写；C07 铁律8 并集合并"),
        Field("rollback_propagation", "rollback_propagation", LLM),
        Field("confidence", "confidence", LLM, enum=CONFIDENCE),
        Field("note", "note", LLM),
    ],
    "invalid": [
        Field("id", written_by=LLM_MUTATED, rename_reason="id_transfer", required=True, dsl="iid"),
        Field("entity", "entity", LLM, required=True),
        Field("from", written_by=LLM, rename_reason="py_keyword", required=True, dsl="frm"),
        Field("to", "to", LLM, required=True),
        Field("reason", "reason", LLM, required=True),
        Field("source_ref", "source_ref", LLM, required=True),
    ],
    "xc": [
        Field("id", written_by=LLM_MUTATED, rename_reason="id_transfer", required=True, dsl="xid"),
        Field("source_entity", "source_entity", LLM, required=True),
        Field("source_transition", "source_transition", LLM_MUTATED, required=True,
              mutation_conditions="_assign_ids"),
        Field("source_state", "source_state", LLM, required=True),
        Field("target_entity", "target_entity", LLM, required=True),
        Field("target_dimension", "target_dimension", LLM, required=True),
        Field("target_condition", "target_condition", LLM, required=True),
        Field("desc", "desc", LLM_MUTATED, required=True, mutation_conditions="_assign_ids",
              desc="引用被 _assign_ids 改写；来源前缀约定见 prompt Step 5"),
        Field("source_ref", "source_ref", LLM, required=True, desc="继承宿主"),
    ],
    "br": [
        Field("id", written_by=LLM_MUTATED, rename_reason="id_transfer", required=True, dsl="bid"),
        Field("category", "category", LLM, enum=BR_CATEGORIES, required=True),
        Field("desc", "desc", LLM, required=True),
        Field("entities_involved", "entities_involved", LLM, required=True),
        Field("source_ref", "source_ref", LLM, required=True),
        Field("signal_type", "signal_type", LLM, enum=BR_SIGNALS, required=True),
        Field("note", "note", LLM),
        Field("enforcement", None, FRAMEWORK, enum=BR_ENFORCEMENTS, required=True,
              derived_from="derive_enforcement(signal_type, desc)"),
    ],
}

# 对象级加工（非字段改写，整条增删/合并）。反向校验脚本据此核对插桩。
OBJECT_MUTATION: dict[str, str] = {
    "trans": "C02 可整条删除终态间转换",
    "causal": "C07 铁律8 去重合并/删除",
    "xc": "C04 可自动追加镜像 XC",
    "structural": "C08 可改 relation_type/ownership_dimension（字段级已标）",
}

# 输出顶层包裹结构（_meta 与各集合）。键 → 写者/来源。
OUTPUT_WRAP: dict[str, str] = {
    "_meta": FRAMEWORK,
    "_context": FRAMEWORK,
    "domain_model": FRAMEWORK,
    "state_and_flow": FRAMEWORK,
    "constraints": FRAMEWORK,
}

META_SCHEMA: list[Field] = [
    Field("version", None, FRAMEWORK, required=True),
    Field("generated_at", None, FRAMEWORK, required=True),
    Field("source", "source", LLM, required=True),
    Field("document_scope", "document_scope", LLM),
    Field("has_critical_ambiguity", None, FRAMEWORK, required=True),
    Field("consistency_check", None, FRAMEWORK, required=True),
    Field("ambiguity_list", None, FRAMEWORK, required=True),
    Field("pipeline_trace", None, FRAMEWORK, required=True),
    Field("branch_dimensions", None, FRAMEWORK, required=True),
]


# ---- 两层视图 ----

def llm_fields(otype: str) -> dict[str, Field]:
    """LLM 契约视图：只含 LLM 可写参数（dsl→Field）。机制上不含 FRAMEWORK 字段。"""
    return {f.dsl: f for f in OBJECT_SCHEMA[otype]
            if f.dsl is not None and not f.is_framework}


def out_fields(otype: str) -> dict[str, Field]:
    """框架输出视图：全部 out 键→Field。"""
    return {f.out: f for f in OBJECT_SCHEMA[otype]}


# ---- LLM 参数校验（add_* fail-fast）----

def validate_llm(otype: str, params: dict) -> None:
    """校验 add_* 的 LLM 参数：未知字段 / required 缺失 / 枚举非法，任一即报错。

    - 未知字段：add_* 用到而注册表未登记（漏登记）或试图写 FRAMEWORK 字段（泄漏）。
    - required：登记为 required 的 LLM 参数必须传且非空。
    - enum：参数值必须在枚举内。
    """
    table = llm_fields(otype)
    unknown = [k for k in params if k not in table]
    if unknown:
        raise ValueError(f"[schema:{otype}] 未知参数 {unknown}（注册表未登记，"
                         f"或 LLM 侧试图写框架字段）")
    for dsl, f in table.items():
        val = params.get(dsl)
        if f.required:
            if isinstance(val, (list, tuple, dict)):
                if val is None:
                    raise ValueError(f"[schema:{otype}] 必填参数 {dsl!r} 缺失")
            elif val in (None, ""):
                raise ValueError(f"[schema:{otype}] 必填参数 {dsl!r} 缺失或为空")
        if val is not None and f.enum:
            if isinstance(val, (list, tuple)):
                bad = [v for v in val if v not in f.enum]
                if bad:
                    raise ValueError(f"[schema:{otype}] {dsl} 元素非法: {bad}，"
                                     f"枚举 {f.enum}")
            elif val not in f.enum:
                raise ValueError(f"[schema:{otype}] {dsl} 非法: {val!r}，枚举 {f.enum}")


# ---- 输出校验（正向断言 / 下游契约）----

def validate_output(otype: str, obj: dict) -> list[str]:
    """校验一个输出对象：required 非空 + 枚举合法。返回错误列表（空=通过）。"""
    errs = []
    for f in out_fields(otype).values():
        val = obj.get(f.out)
        if f.required:
            if isinstance(val, (list, tuple, dict)):
                if val is None:
                    errs.append(f"{otype}.{f.out} 缺失（required）")
                    continue
            elif val in (None, ""):
                errs.append(f"{otype}.{f.out} 缺失或为空（required）")
                continue
        if val is not None and f.enum:
            if isinstance(val, (list, tuple)):
                bad = [v for v in val if v not in f.enum]
                if bad:
                    errs.append(f"{otype}.{f.out} 元素非法: {bad}")
            elif val not in f.enum:
                errs.append(f"{otype}.{f.out} 非法: {val!r}")
    return errs
