"""V04 内置对象保护：系统维护字段禁止被 3/9 类断言；readonly/no_form_page
实体(UI 事实,模型无法表达)由 case_spec 可选提供。

字段级保护的第一性原理：系统维护字段从模型属性 desc 推导
(自动继承/自动生成/自动设置/自动获取/系统维护/由系统/计算所得)——
实体限定为「实体.字段」精确模式，单一真相源在 P1 数据层。

case_spec 的 built_in_entities 仅承担 UI/测试设计事实：
  - readonly：字符串条目 = readonly 实体名（不可被 type3/9 误建）；
  - no_form_page：字符串或 dict {entity, clause, note} = 无编辑表单实体。

【废弃数据源】case_spec readonly 的 dict 条目（{entity: 字段名, clause,
note}）不再并入字段级保护：该测试架构为 AI 生成、未经人工确认，已出现误标
（"文件级别"列为系统维护字段，实际 E-SCN 4.13.1 为"只可选:A级、B级、C级"、
E-EXP 为上传时用户确定文件级别，均为用户选定）；且多数条目是系统级账号/角色/
默认值/展示快照，并非实体属性，字段名通配 `*.字段` 保护无意义，还会跨实体
误伤同名字段（同名在不同实体可编辑性不同）。
"""
import fnmatch

from .base import CheckResult, entity_names_of, get_procedures
from context.sysfields import is_sys_maintained

CHECK_ID = "V04"
FORBIDDEN_TYPES = {3, 9}


def _sysfields_from_model(model: dict) -> list:
    """从 _context.entity_details[].attributes 推导系统维护字段,
    格式 '实体名.字段名'(与用例 Then 目标一致)。

    单一真相源在 context/sysfields.py (与 Type9 生成器共享同一推导, 防止
    生成器/校验器两套正则漂移 —— 曾致生成器用 is_config 过滤误杀用户字段)。"""
    fields = []
    for e in (model.get("_context") or {}).get("entity_details", []) or []:
        ename = e.get("name", "")
        for a in e.get("attributes", []) or []:
            aname = a.get("name", "")
            if aname and is_sys_maintained(a.get("desc", "")):
                fields.append(f"{ename}.{aname}")
    return fields


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="blocker", suspected_stage="P2",
                      suspected_files=["build_obligations.py", "nodes/field_validation.py"])
    model = output.get("_model")
    builtin = (spec or {}).get("built_in_entities") or {}

    # 实体级只读(UI 事实)：readonly 字符串条目 = readonly 实体名；
    # dict 条目是已废弃的字段证据，不再参与保护(见模块 docstring)。
    readonly_ents = {str(it) for it in (builtin.get("readonly") or [])
                     if isinstance(it, str) and it}
    noform_ents = entity_names_of(builtin.get("no_form_page") or [])
    # 字段级保护：仅模型属性 desc 推导(实体限定「实体.字段」精确模式)
    sysfields = set(_sysfields_from_model(model)) if model else set()
    # 透明度：记录被废弃的 case_spec 字段证据条数，便于阅读 verdict 时理解
    dropped = {str(it.get("entity")) for it in (builtin.get("readonly") or [])
               if isinstance(it, dict) and it.get("entity")}
    if dropped:
        res.note = (f"case_spec readonly 字段证据 {len(dropped)} 条不参与字段级保护"
                    f"(AI 生成未确认、含误标；见代码注释): {sorted(dropped)}")

    if not (readonly_ents or noform_ents or sysfields):
        res.skip("no protected fields/entities derived (model) nor case_spec readonly/no_form_page")
        return res
    for p in get_procedures(output):
        ent, otype = p.get("entity", ""), p.get("obligation_type")
        srcs = " ".join(p.get("source_ids", []) or [])
        if ent in readonly_ents and otype in FORBIDDEN_TYPES:
            res.fail({"temp_id": p.get("temp_id"), "entity": ent,
                      "obligation_type": otype, "reason": "readonly entity misuse"})
        if ent in noform_ents and "FIELD-VAL" in srcs:
            res.fail({"temp_id": p.get("temp_id"), "entity": ent,
                      "reason": "no_form_page entity has FIELD-VAL case"})
        if otype in FORBIDDEN_TYPES:
            for t in p.get("thens", []) or []:
                tgt = t.get("target", "")
                for f in sysfields:
                    if fnmatch.fnmatch(tgt, f):
                        res.fail({"temp_id": p.get("temp_id"), "target": tgt,
                                  "reason": f"system-maintained field asserted: {f}"})
    return res
