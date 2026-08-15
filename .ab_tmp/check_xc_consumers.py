# 一次性核对脚本：对每条手动镜像/联动 XC 列出匹配消费者。
# 消费者 = target_entity 上持有 state_ref 前置条件 ref.entity==source_entity
#        且 ref.state==source_state 的转换。
# 运行：PYTHONIOENCODING=utf-8 python .ab_tmp/check_xc_consumers.py
import importlib

MODULES = ["srs_data.struct_srs", "srs_data.CASC-STEC-PT017"]

for modname in MODULES:
    print("=" * 70)
    print(f"### {modname}")
    m = importlib.import_module(modname).build()
    trans = m.transitions  # 局部标签 t01...
    # 每个转换的跨实体 state_ref 前置条件，按 (ref.entity, ref.state) 索引
    from collections import defaultdict
    by_ref = defaultdict(list)  # (ref_entity, ref_state) -> [t_id]
    for t in trans:
        for p in t["preconditions"]:
            if p["type"] == "state_ref" and p.get("ref") and p["ref"]["entity"] != t["entity"]:
                by_ref[(p["ref"]["entity"], p["ref"]["state"])].append(t["id"])
    print(f"跨实体前置条件索引（ref -> 消费者）:")
    for k in sorted(by_ref, key=str):
        print(f"   {k[0]}:{k[1]} -> {by_ref[k]}")
    print()
    for x in m.cross_entity:
        if not x["id"].startswith("x"):
            continue
        src = (x["source_entity"], x["source_state"])
        cands = [tid for tid in by_ref.get(src, [])
                 if tid.startswith("t") and tid in {t["id"] for t in trans if t["entity"] == x["target_entity"]}]
        # 候选消费者限定 target_entity 上
        te = x["target_entity"]
        cands = [tid for tid in by_ref.get(src, []) if any(t["id"] == tid and t["entity"] == te for t in trans)]
        print(f"{x['id']:5s} {x['source_entity']}:{x['source_state']:8s} -> "
              f"target={x['target_entity']} [{x['target_condition']}] 消费者={sorted(cands) or '∅'}")
