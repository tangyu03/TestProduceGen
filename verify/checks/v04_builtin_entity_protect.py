"""V04 内置对象保护：系统维护字段禁止被 3/9 类断言；readonly/no_form_page
实体(UI 事实,模型无法表达)由 case_spec 可选提供。

第一性原理：系统维护字段从模型属性 desc 推导(自动继承/自动生成/自动设置/
自动获取/系统维护/由系统/计算所得)——单一真相源在 P1 数据层,而非 case_spec
手写清单。readonly/no_form_page 是 UI/测试设计事实(哪些实体无编辑表单),
非模型结构知识,保留在 case_spec(可选)。
"""
import fnmatch
import re

from .base import CheckResult, get_procedures

CHECK_ID = "V04"
FORBIDDEN_TYPES = {3, 9}

# 系统维护字段标记: 由系统设置/自动派生,非用户可编辑输入
_SYS_MAINTAINED_MARKERS = re.compile(
    r"自动继承|自动生成|自动设置|自动获取|系统维护|由系统|自动记录|"
    r"根据.*计算|计算所得|系统自动|不可编辑且自动")


def _sysfields_from_model(model: dict) -> list:
    """从 _context.entity_details[].attributes 推导系统维护字段,
    格式 '实体名.字段名'(与用例 Then 目标一致)。"""
    fields = []
    for e in (model.get("_context") or {}).get("entity_details", []) or []:
        ename = e.get("name", "")
        for a in e.get("attributes", []) or []:
            desc = a.get("desc", "")
            aname = a.get("name", "")
            if aname and _SYS_MAINTAINED_MARKERS.search(desc):
                fields.append(f"{ename}.{aname}")
    return fields


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="blocker", suspected_stage="P2",
                      suspected_files=["build_obligations.py", "nodes/field_validation.py"])
    model = output.get("_model")
    builtin = (spec or {}).get("built_in_entities") or {}
    readonly = set(builtin.get("readonly") or [])
    noform = set(builtin.get("no_form_page") or [])
    sysfields = _sysfields_from_model(model) if model else []
    if not model:
        res.skip("no coverage model passed (--model); skipping model-derived V04")
        return res
    if not (readonly or noform or sysfields):
        res.skip("no protected fields derived (model) nor case_spec.built_in_entities")
        return res
    for p in get_procedures(output):
        ent, otype = p.get("entity", ""), p.get("obligation_type")
        srcs = " ".join(p.get("source_ids", []) or [])
        if ent in readonly and otype in FORBIDDEN_TYPES:
            res.fail({"temp_id": p.get("temp_id"), "entity": ent,
                      "obligation_type": otype, "reason": "readonly entity misuse"})
        if ent in noform and "FIELD-VAL" in srcs:
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
