#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""System-maintained field derivation — shared by the Type9 field-validation
generator (nodes/s1_generation.py) and the V04 builtin-entity protect gate
(verify/checks/v04_builtin_entity_protect.py).

Single source of truth for "which fields are maintained by the system rather
than entered by the user": derived from the P1 attribute ``desc`` marker regex
below. Both consumers MUST go through here so they cannot drift — the same
rule co_derivation.py / context/entity_operators.py establish for the other
shared derivations.

Historical defect this prevents:
  Type9's generator filtered "non-editable" fields with ``is_config=False`` —
  but attr() defaults is_config=False, so EVERY non-config field (including
  文件或资料名称 / 载体来源 / 原载体编号 / 纸张页数, all user-editable) was dropped,
  and the LLM's full field-validation lists (cache/fv_495d86b0f56b94fa.json:
  E-REG has 12 thens) were reduced to only the config dropdowns (载体类别/级别).
  V04 derived the same concept from desc markers; the two implementations
  drifted and the generator lost most of the field validations. Now both share
  this module.

The regex is deliberately narrow: it does NOT include generic "不可编辑/不可修改"
(readonly ≠ system-maintained — a system-generated field on a separate managed
record can still be validated for uniqueness/format). Keeping it narrow avoids
dropping user-facing validations.
"""
import re

_SYS_MAINTAINED_MARKERS = re.compile(
    r"自动继承|自动生成|自动设置|自动获取|系统维护|由系统|自动记录|"
    r"根据.*计算|计算所得|系统自动|不可编辑且自动")


def is_sys_maintained(desc: str) -> bool:
    """True if the attribute desc marks the field as system-maintained
    (auto-generated / auto-derived, not a user-editable input)."""
    return bool(desc) and bool(_SYS_MAINTAINED_MARKERS.search(desc))


def sys_maintained_pairs(entity_details) -> list[tuple[str, str]]:
    """(entity_key, attr_name) pairs for every system-maintained field.

    entity_key carries BOTH the E-XXX id and the Chinese name, so a caller
    matching Then targets never has to know which form the target uses:
    the generator filters pre-translation targets like 'E-REG.文件或资料名称',
    while the V04 gate matches post-translation '载体登记任务.文件或资料名称'.
    """
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for ed in entity_details or []:
        if not isinstance(ed, dict):
            continue
        eid = ed.get("id", "")
        ename = ed.get("name", "")
        for attr in ed.get("attributes", []) or []:
            if not isinstance(attr, dict):
                continue
            aname = attr.get("name", "")
            if not aname or not is_sys_maintained(attr.get("desc", "")):
                continue
            for key in (eid, ename):
                if key and (key, aname) not in seen:
                    seen.add((key, aname))
                    pairs.append((key, aname))
    return pairs
