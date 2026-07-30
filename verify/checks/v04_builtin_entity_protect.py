"""V04 内置对象保护：readonly 实体禁止配置变更/字段校验型用例；
no_form_page 实体禁止 FIELD-VAL 用例；系统维护字段禁止被 3/9 类断言。"""
import fnmatch

from .base import CheckResult, get_procedures

CHECK_ID = "V04"
FORBIDDEN_TYPES = {3, 9}


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="blocker", suspected_stage="P2",
                      suspected_files=["build_obligations.py", "nodes/field_validation.py"])
    builtin = (spec or {}).get("built_in_entities") or {}
    readonly = set(builtin.get("readonly") or [])
    noform = set(builtin.get("no_form_page") or [])
    sysfields = [f for f in (builtin.get("system_maintained_fields") or []) if "." in f]
    if not (readonly or noform or sysfields):
        res.skip("case_spec.built_in_entities missing")
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
