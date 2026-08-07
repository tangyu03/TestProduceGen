#!/usr/bin/env python3
"""Tier 2 领域前置机制 — 确定性验证 (S0→S3, 无 LLM, 全数据驱动).

只信确定性 Engine State (P3 LLM 随机, TC 编号跨 run 不可比)。
全量不变量扫描以机制自身为真相源 (context/domain_precondition.object_existence):
对每一条 Type5 proc 重算领域前置期望, 断言 given 结构 / desc 人读文本 /
创建锚定依赖 / 相位底 与机制输出一致; 管理类断言保持弱 Given 哨兵不变。
无任何硬编码实体 id / EO id / 状态名 / 转换 id / 中文名 —— 全部从
coverage_model (entity_obligations.entity_name, 创建转换 from=None) 与
S0 判别器 (topology_levels>0) 派生。handoff §5 点名的具体 TC 由全量扫描覆盖
(每条 proc 都被查, 包括那些 TC, 严格强于点名单查)。
"""
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

from graph import compile_p3_graph
import scripts.s3_probe as probe
from context.domain_precondition import lifecycle_entity_ids, object_existence


def main(cm_path: str):
    app = compile_p3_graph()
    result = dict(probe.initial_state(cm_path))
    for event in app.stream(result):
        for n, out in event.items():
            result.update(out)
    procs = result.get("procedures") or []
    errors = result.get("errors") or []
    cm = result.get("coverage_model") or {}
    lc_ids = lifecycle_entity_ids(result)          # S0 判别器, 数据驱动
    name_map = {e.get("entity"): e.get("entity_name")
                for e in cm.get("entity_obligations") or [] if e.get("entity_name")}
    phase_of = {p["temp_id"]: (p.get("_S2_fields") or {}).get("phase", 0) for p in procs}

    ok = True
    def check(name, cond, detail=""):
        nonlocal ok
        status = "PASS" if cond else "FAIL"
        if not cond:
            ok = False
        print(f"  [{status}] {name} {detail}")

    # ── 1. 判别器覆盖: 每个生命周期实体都能派生存在锚定 (防静默漏数) ──
    print("=== 1. 判别器覆盖: 生命周期实体均有创建锚定 ===")
    missing = [e for e in sorted(lc_ids) if object_existence(cm, result, e) is None]
    check(f"lifecycle_entity_ids={sorted(lc_ids)} 全部可派生存在锚定", not missing, f"missing={missing}")

    # ── 2. 全量不变量扫描 (机制为真相源, 每一条 Type5 proc) ──
    print("\n=== 2. 全量不变量扫描: 每条 Type5 proc 与 object_existence 一致 ===")

    def _has_creation_dep(p, creation_to_ids):
        for d in (p.get("_S3_fields") or {}).get("dependencies") or []:
            tgt = next((q for q in procs if q["temp_id"] == d), None)
            if tgt and any(cid in "|".join(tgt.get("source_ids") or []) for cid in creation_to_ids):
                return True
        return False

    def _creation_proc_phase(creation_to_ids):
        phs = [phase_of[q["temp_id"]] for q in procs
               if any(cid in "|".join(q.get("source_ids") or []) for cid in creation_to_ids)]
        return max(phs) if phs else 0

    mism = []
    n_lc = n_mgmt = 0
    for p in procs:
        if p.get("obligation_type") != 6:
            continue
        ent = p.get("entity")
        g0 = (p.get("givens") or [{}])[0]
        dp = object_existence(cm, result, ent)
        if dp:
            n_lc += 1
            zh = name_map.get(dp["object_entity"], dp["object_entity"])
            # 2a given 结构 (target/state = 机制锚定)
            if g0.get("target") != dp["object_entity"] or g0.get("state") != dp["object_state"]:
                mism.append((p["temp_id"], ent, "given", (g0.get("target"), g0.get("state")),
                             (dp["object_entity"], dp["object_state"])))
            # 2b desc 人读文本 (中文名 + 已存在 + 处于X状态)
            desc = g0.get("description", "")
            if not (zh in desc and "已存在" in desc and f"处于{dp['object_state']}状态" in desc):
                mism.append((p["temp_id"], ent, "desc", desc, f"{zh}已存在，处于{dp['object_state']}状态"))
            # 2c 创建锚定依赖
            if not _has_creation_dep(p, dp["creation_to_ids"]):
                mism.append((p["temp_id"], ent, "no_creation_dep", dp["creation_to_ids"], ""))
            # 2d 相位底 ≥ 创建相位 (防回落到创建之前)
            if phase_of[p["temp_id"]] < _creation_proc_phase(dp["creation_to_ids"]):
                mism.append((p["temp_id"], ent, "phase_floor", phase_of[p["temp_id"]],
                             _creation_proc_phase(dp["creation_to_ids"])))
        else:
            n_mgmt += 1
            if g0.get("state") != "存在":          # 管理类弱 Given 哨兵保持
                mism.append((p["temp_id"], ent, "mgmt_changed", g0.get("state"), "存在"))
    for m in mism[:10]:
        print(f"  [MISMATCH] {m}")
    check(f"{n_lc} 条生命周期 proc 全命中 (given/desc/创建依赖/相位底), {n_mgmt} 条管理类保持存在",
          len(mism) == 0, f"mismatch={len(mism)} lc={n_lc} mgmt={n_mgmt}")

    # ── 3. V01 相位单调性 ──
    print("\n=== 3. V01 相位单调性 ===")
    v01 = []
    for p in procs:
        my_ph = phase_of[p["temp_id"]]
        for d in (p.get("_S3_fields") or {}).get("dependencies") or []:
            if d in phase_of and phase_of[d] > my_ph:
                v01.append((p["temp_id"], my_ph, d, phase_of[d]))
    check("0 违例", len(v01) == 0, f"violations={v01[:5]}")

    # ── 4. errors == 0 ──
    print("\n=== 4. errors == 0 ===")
    check("errors 为空", len(errors) == 0, f"errors={errors[:3]}")

    # ── 量化 (实体集合/状态名均数据派生) ──
    print("\n=== 量化: lifecycle Type5 procs Given 分布 ===")
    cnt = Counter()
    for p in procs:
        if p.get("obligation_type") == 6:
            st = (p.get("givens") or [{}])[0].get("state")
            cnt[("lifecycle" if p["entity"] in lc_ids else "mgmt", st)] += 1
    print(f"  判别器 (topology_levels>0) = {sorted(lc_ids)}")
    for k in sorted(cnt):
        print(f"  {k}: {cnt[k]}")
    print("\n=== 量化: 依赖边 / domain_precond 来源 ===")
    total = sum(len((p.get("_S3_fields") or {}).get("dependencies") or []) for p in procs)
    dom = sum(1 for p in procs
              for o in ((p.get("_S3_fields") or {}).get("dep_origins") or {}).values()
              if o == "domain_precond")
    print(f"  总依赖边={total}, domain_precond 来源边={dom}")

    print(f"\nRESULT: {'ALL PASS' if ok else 'SOME FAILED'}")
    return ok


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "coverage_obligations.json")
