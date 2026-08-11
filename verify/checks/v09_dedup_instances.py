"""V09 实例去重与多实例一致性：givens/when/thens 规范化哈希相同必须合并；
同一实例组 source_ids 必须一致；内置/单例实体 multi_count 必须为 1。"""
from .base import CheckResult, entity_names_of, get_procedures, text_hash

CHECK_ID = "V09"


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="blocker", suspected_stage="S4",
                      suspected_files=["nodes/s4_multi_instance.py"])
    builtin = (spec or {}).get("built_in_entities") or {}
    singletons = (entity_names_of(builtin.get("readonly") or [])
                  | entity_names_of(builtin.get("no_form_page") or []))
    seen, groups = {}, {}
    for p in get_procedures(output):
        sig = text_hash([p.get("givens"), p.get("when"), p.get("thens"), p.get("entity")])
        if sig in seen:
            res.fail({"kind": "exact_duplicate", "kept": seen[sig],
                      "dup": p.get("temp_id")})
        else:
            seen[sig] = p.get("temp_id")
        base = str(p.get("temp_id", "")).split(".")[0]
        groups.setdefault(base, []).append(p)
    for base, g in groups.items():
        if len(g) < 2:
            continue
        src0 = set(g[0].get("source_ids", []) or [])
        for p in g[1:]:
            if set(p.get("source_ids", []) or []) != src0:
                res.fail({"kind": "source_mismatch", "group": base,
                          "temp_id": p.get("temp_id")})
        ent = g[0].get("entity", "")
        mc = (g[0].get("_S4_fields", {}) or {}).get("multi_count", 1)
        if ent in singletons and (len(g) > 1 or mc > 1):
            res.fail({"kind": "builtin_multi_instance", "group": base,
                      "entity": ent, "count": len(g)})
    return res
