#!/usr/bin/env python
"""反向校验：注册表标注 vs 框架实际加工行为（注册表校准，跑通后即冻结）。

正向断言（verify_schema.py）的 ground truth 是注册表自身——注册表标错它测
不出来。反向校验兜这个底：在框架加工写入点插桩，记录 (trigger, otype, field, op)，
跑 struct_srs assemble 后与注册表 written_by / mutation_conditions /
OBJECT_MUTATION 逐一比对。命中不匹配 = 注册表标注与框架实际行为不一致。

比对规则：
- 对象级（new/gone）：OBJECT_MUTATION[otype] 必须含 trigger。
- 字段级：written_by 必须 ≠ llm（llm_mutated/framework）；
  条件性改写（C0X）的 mutation_conditions 必须含 trigger；
  _assign_ids/_backfill_branch_coverage 属确定性加工，豁免条件检查。
- build 期间加工（enforcement 在 add_br 内派生，插桩覆盖不到）做值级验证：
  每条 BR 的 enforcement == derive_enforcement(signal_type, desc)。

用法：python -m scripts.verify_schema_reverse

数据驱动限制：反向校验只验证本次数据里真实发生的加工。声明了 mutation_conditions
但本次 assemble 未触发的 trigger（如 struct_srs 不触发 C02/C03/C08），其标注不会被
核查——覆盖报告（见文末 COVERAGE）会显式列出这类"声明了但未验证"项。
"""
from __future__ import annotations

import copy
import sys

from srs_pipeline.builders import N, precond, state_ref
from srs_pipeline.model import DomainModel, derive_enforcement
from srs_pipeline.schema import OBJECT_MUTATION, OBJECT_SCHEMA, out_fields
from srs_pipeline.validate import Validator
from srs_data import struct_srs

COLLS = {
    "entity": "entities", "role": "roles", "event": "events",
    "structural": "structural_relations", "causal": "transition_relations",
    "trans": "transitions", "invalid": "invalid_transitions",
    "xc": "cross_entity", "br": "business_rules",
    "branch_dimension": "branch_dimensions",
}

# 确定性加工（无条件执行，注册表 mutation_conditions 豁免条件性检查）
DETERMINISTIC = {"_assign_ids", "_backfill_branch_coverage",
                 "_backfill_semantic_branch_tt", "_resolve_role_refs"}


def snap_model(m):
    return {otype: {id(o): copy.deepcopy(o) for o in getattr(m, attr)}
            for otype, attr in COLLS.items()}


def diff(trigger, before, after, trace):
    for otype in before:
        b, a = before[otype], after[otype]
        for oid in a.keys() - b.keys():
            trace.append((trigger, otype, "new", None))
        for oid in b.keys() - a.keys():
            trace.append((trigger, otype, "gone", None))
        for oid in b.keys() & a.keys():
            if b[oid] != a[oid]:
                for k in set(b[oid]) | set(a[oid]):
                    if b[oid].get(k) != a[oid].get(k):
                        trace.append((trigger, otype, oid, k))


def build_triggers() -> DomainModel:
    """校准夹具：最小合法模型，专门触发 struct_srs 不覆盖的 C02/C03/C08。

    设计约束（让 assemble 走完全程不中断）：
    - 每维度有创建转换（C02 error 豁免）；无 operations（C11/C12 空跑）；
      无 evidence/doc（C16 早退）。
    - E-A.S 含双终态 → tA3 done→done2 触发 C02 整条删除。
    - tA4 的 state_ref 指向不存在状态 → 触发 C03 降级 constraint。
    - E-A→E-B 为 composition+business_ownership，且 B 创建转换（tB1）的
      state_ref 引用 E-C 后期状态 → 触发 C08 降级 reference。
      副作用：C04 会为 tB1 补一条镜像 XC（注册表已标 xc 可被 C04 追加）。
    """
    m = DomainModel(source="trigger-coverage")
    m.add_entity("E-A", "A", "触发 C02/C03 测试实体", type="core",
                 state_dimensions=[{
                     "dimension_name": "S",
                     "states": ["s1", "s2", "done", "done2"],
                     "initial": "s1", "terminal": ["done", "done2"]}])
    m.add_entity("E-B", "B", "组合子实体", type="core",
                 state_dimensions=[{
                     "dimension_name": "S",
                     "states": ["b1"], "initial": "b1", "terminal": []}])
    m.add_entity("E-C", "C", "被引用实体", type="core",
                 state_dimensions=[{
                     "dimension_name": "S",
                     "states": ["c1"], "initial": "c1", "terminal": []}])
    m.add_trans("tA1", "E-A", "S", None, "s1", "创建A", "system",
                [], ["状态初始化为 s1"], ["audit"], "forward", "P0", "t")
    m.add_trans("tB1", "E-B", "S", None, "b1", "创建B", "system",
                [precond("依赖C的c1状态", "state_ref",
                         state_ref("E-C", "S", "c1"))],
                ["状态初始化为 b1"], ["audit"], "forward", "P0", "t")
    m.add_trans("tC1", "E-C", "S", None, "c1", "创建C", "system",
                [], ["状态初始化为 c1"], ["audit"], "forward", "P0", "t")
    m.add_trans("tA3", "E-A", "S", "done", "done2", "归档回收", "system",
                [], ["由done变为done2"], ["audit"], "forward", "P0", "t")
    m.add_trans("tA4", "E-A", "S", "s1", "s2", "推进", "system",
                [precond("某不存在状态", "state_ref",
                         state_ref("E-A", "S", "不存在"))],
                ["由s1变为s2"], ["audit"], "forward", "P0", "t")
    m.add_structural("E-A", "E-B", "composition", "1:N",
                     "business_ownership", "B归A", confidence="high")
    return m


def coverage_report(trace) -> tuple[list[str], list[str]]:
    """注册表声明 vs trace 实际验证，分已覆盖/未覆盖。

    声明来源：字段 mutation_conditions 拆解 + OBJECT_MUTATION 对象级登记。
    未覆盖 = 声明了但本次数据没触发，其标注未经反向校验核查（数据驱动盲区）。
    """
    import re
    declared: set[str] = set()
    for otype, fields in OBJECT_SCHEMA.items():
        for f in fields:
            for trig in (f.mutation_conditions or "").split(";"):
                if trig.strip():
                    declared.add(trig.strip())
    # OBJECT_MUTATION：对象级登记，值为描述串，trigger 是其中的 C\d{2} 名
    for desc in OBJECT_MUTATION.values():
        declared |= set(re.findall(r"C\d{2}", desc))
    declared |= DETERMINISTIC                      # 确定性加工也计入声明
    verified = {t for t, *_ in trace}
    covered = sorted(declared & verified)
    uncovered = sorted(declared - verified)
    return covered, uncovered


def main(build=struct_srs.build) -> int:
    m = build()
    errs: list[str] = []

    # 1. build 期间加工（enforcement）值级验证
    bad_enf = [b["id"] for b in m.business_rules
               if b["enforcement"]
               != derive_enforcement(b["signal_type"], b["desc"])]
    if bad_enf:
        errs.append(f"[enforcement] {len(bad_enf)} 条 BR 与 derive_enforcement "
                    f"不一致: {bad_enf}")

    # 1b. build 期间加工（constrained_entity 单实体派生）值级验证
    bad_ce = [b["id"] for b in m.business_rules
              if len(b.get("entities_involved", [])) == 1
              and b.get("constrained_entity") != b["entities_involved"][0]]
    if bad_ce:
        errs.append(f"[constrained_entity] {len(bad_ce)} 条单实体 BR "
                    f"未派生为唯一元素: {bad_ce}")

    # 2. assemble 期间加工：插桩写入点
    trace: list[tuple] = []

    def wrap_model(name):
        orig = getattr(DomainModel, name)
        def wrapper(self, *a, **kw):
            before = snap_model(self)
            orig(self, *a, **kw)
            diff(name, before, snap_model(self), trace)
        return wrapper

    for name in ("_assign_ids", "_backfill_branch_coverage",
                 "_backfill_semantic_branch_tt", "_resolve_role_refs"):
        setattr(DomainModel, name, wrap_model(name))

    def wrap_validator(cname):
        orig = getattr(Validator, cname)
        trig = cname[:3].upper()
        def wrapper(self, *a, **kw):
            before = snap_model(self.m)
            orig(self, *a, **kw)
            diff(trig, before, snap_model(self.m), trace)
        return wrapper

    for cname in ("c02_state_structure", "c03_precondition_structure",
                  "c04_mirror_integrity", "c07_causal_consistency",
                  "c08_composition_sync"):
        setattr(Validator, cname, wrap_validator(cname))

    output, report = m.assemble()

    # 3. trace 与注册表比对
    for trigger, otype, oid, field in trace:
        if field is None:
            if trigger not in OBJECT_MUTATION.get(otype, ""):
                errs.append(f"[反向] {otype} 对象{'新增' if oid == 'new' else '删除'} "
                            f"由 {trigger} 触发，OBJECT_MUTATION 未登记")
            continue
        f = out_fields(otype).get(field)
        if f is None:
            errs.append(f"[反向] {otype}.{field} 被 {trigger} 改写，注册表无此字段")
            continue
        if f.written_by == "llm":
            errs.append(f"[反向] {otype}.{field} 被 {trigger} 改写，"
                        f"注册表却标 written_by=llm")
        elif trigger not in DETERMINISTIC \
                and trigger not in (f.mutation_conditions or ""):
            errs.append(f"[反向] {otype}.{field} 被 {trigger} 改写，"
                        f"但 mutation_conditions={f.mutation_conditions!r}")

    covered, uncovered = coverage_report(trace)
    if errs:
        print(f"REVERSE FAIL（{len(errs)} 项，前 30）：")
        for e in errs[:30]:
            print("  -", e)
        print(f"trace 共 {len(trace)} 条")
        print(f"COVERAGE 已验证 {len(covered)}: {covered}")
        print(f"COVERAGE 未覆盖 {len(uncovered)}: {uncovered}")
        return 1
    print(f"REVERSE OK：trace {len(trace)} 条全部命中注册表标注 | "
          f"consistency_check={output['_meta']['consistency_check']}")
    print(f"COVERAGE 已验证 {len(covered)}: {covered}")
    if uncovered:
        print(f"COVERAGE 未覆盖 {len(uncovered)}（本次数据未触发，标注未经核查）: "
              f"{uncovered}")
    return 0


if __name__ == "__main__":
    # --triggers：追加校准夹具，覆盖 struct_srs 不触发的 C02/C03/C08
    if len(sys.argv) > 1 and sys.argv[1] == "--triggers":
        sys.exit(main(build_triggers))
    sys.exit(main())
