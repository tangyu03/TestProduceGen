#!/usr/bin/env python
"""正向断言：注册表 vs 实际代码/输出。可重复运行，是漂移的回归网。

覆盖三层：
1. LLM 视图一致性 —— 每个 add_* 方法签名参数集合 == 注册表 dsl 集合。
   （改 add_* 或注册表任一方不同步，这里即报错，双向锁死。）
2. 框架视图一致性 —— FRAMEWORK 字段必须 dsl=None（LLM 无名字，机制上不可泄漏）。
3. 输出校验 —— struct_srs assemble 输出逐对象过 validate_output，
   全部 required/enum 命中。

用法：python -m scripts.verify_schema
"""
from __future__ import annotations

import inspect
import sys

from srs_pipeline.model import DomainModel
from srs_pipeline.schema import (FRAMEWORK, META_SCHEMA, OBJECT_SCHEMA,
                                 llm_fields, validate_output)
from srs_data import struct_srs

# 对象 → (输出定位)。prohibition_config/permission 在 _context。
COLLECTIONS = {
    "entity": ("domain_model", "entities"),
    "role": ("domain_model", "roles"),
    "structural": ("domain_model", "structural_relations"),
    "causal": ("domain_model", "transition_relations"),
    "trans": ("state_and_flow", "transitions"),
    "xc": ("constraints", "cross_entity"),
    "invalid": ("constraints", "invalid_transitions"),
    "br": ("constraints", "business_rules"),
}
MAPPED_METHODS = {
    "entity": "add_entity",
    "role": "add_role",
    "structural": "add_structural",
    "causal": "add_causal",
    "trans": "add_trans",
    "xc": "add_xc",
    "invalid": "add_invalid",
    "br": "add_br",
    "permission": "add_permission",
}
# 签名参数集合（排除 self）。prohibition_config 的 config 是单 dict 参数，
# 其"字段"是 dict 键而非函数参数，故单独校验。
SIG_PARAMS = {otype: set(inspect.signature(
    getattr(DomainModel, meth)).parameters) - {"self"}
    for otype, meth in MAPPED_METHODS.items()}


def main() -> int:
    errs: list[str] = []

    # 1. add_* 签名参数集合 == 注册表 dsl 集合（双向锁死）
    for otype, sig_params in SIG_PARAMS.items():
        reg_params = set(llm_fields(otype))
        if sig_params != reg_params:
            errs.append(f"[视图] {otype}: add_{MAPPED_METHODS[otype]} 签名参数 "
                        f"{sorted(sig_params)} ≠ 注册表 dsl {sorted(reg_params)}")

    # 2. FRAMEWORK 字段不得有 dsl 名（LLM 不可见）
    for otype, fields in OBJECT_SCHEMA.items():
        for f in fields:
            if f.written_by == FRAMEWORK and f.dsl is not None:
                errs.append(f"[视图] {otype}.{f.out} 为 framework 字段却登记了 "
                            f"dsl={f.dsl!r}（LLM 会看见）")

    # 3. struct_srs 输出逐对象过注册表
    model = struct_srs.build()
    output, report = model.assemble()
    total = 0
    for otype, (sec, coll) in COLLECTIONS.items():
        for obj in output[sec][coll]:
            total += 1
            errs += validate_output(otype, obj)
    for bd in output["_meta"]["branch_dimensions"]:          # 分支维度归档在 _meta
        total += 1
        errs += validate_output("branch_dimension", bd)
    for p in output["_context"]["permissions"]:
        total += 1
        errs += validate_output("permission", p)
    cfg = output["_context"]["prohibition_config"]
    total += 1
    errs += validate_output("prohibition_config", cfg)
    for f in META_SCHEMA:                                     # _meta 必填
        if f.required and output["_meta"].get(f.out) is None:
            errs.append(f"_meta.{f.out} 缺失（required）")

    if errs:
        print(f"SCHEMA FAIL（{len(errs)} 项，前 30 条）：")
        for e in errs[:30]:
            print("  -", e)
        return 1
    print(f"SCHEMA OK：{total} 对象 / 0 错误 | "
          f"consistency_check={output['_meta']['consistency_check']}")
    print(f"LLM 视图：{sum(len(llm_fields(o)) for o in SIG_PARAMS)} 个可写参数，"
          f"均不含 framework 字段")
    return 0


if __name__ == "__main__":
    sys.exit(main())
