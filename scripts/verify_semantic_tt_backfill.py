"""往返确定性验证：3.3 语义回填（_backfill_semantic_branch_tt）——数据驱动，零硬编码分支名。

对数据文件（默认 pt_srsv6，可传其他模块）中所有「非空 target_transition」分支做往返：
1) 局部标签形态 → _assign_ids() → 捕获 {value → 正式 tid} 基准（编号移交结果）。
2) 语义描述形态（target_transition := value 文本）→ _assign_ids() + 回填
   → 断言不变量（对每个分支恰居其一）：
   - 回填成功（meta.branch_tt_backfilled 命中）→ 最终 tt == 基准正式号（精确等价）；
   - 回填失败（无唯一候选，meta.branch_tt_deviations 记录）→ br.inferred=True、
     语义描述保留（最终 tt == value ≠ 正式号）；
   - 既未回填也未记偏差 → 失败（无第三态）。
   另有：警告条数 == 偏差数；数据须为局部标签形态（回填对正式号 no-op）。

全确定性，无 LLM。用法：python scripts/verify_semantic_tt_backfill.py [数据模块]
"""
import importlib
import os
import re
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FORMAL = re.compile(r"[A-Z]+-\d{3}[a-z]?")


def build(module):
    return importlib.import_module(module).build()


def collect_branches(m):
    """(dimension, value) → target_transition；跳过空 tt（纯配置/展示型分支）。"""
    out = {}
    for d in m.branch_dimensions:
        for br in d["branches"]:
            tt = br.get("target_transition", "")
            if tt:
                out[(d["dimension"], br["value"])] = tt
    return out


def revert_to_semantic(m, pairs):
    """把指定分支 target_transition 改写为语义描述形态（=value 文本）。"""
    for d in m.branch_dimensions:
        for br in d["branches"]:
            if (d["dimension"], br["value"]) in pairs:
                br["target_transition"] = br["value"]


def main(module):
    fail = 0

    # ---- 1. 基准：局部标签形态的编号移交结果 ----
    base = build(module)
    base._assign_ids()                     # 语义回填对正式号 no-op
    ground = collect_branches(base)
    if not ground:
        print(f"FAIL 数据无分支可验: {module}"); return 1
    for pair, tt in ground.items():
        if not FORMAL.fullmatch(tt):
            print(f"FAIL 数据非局部标签形态: {pair} -> {tt!r}"); fail += 1

    # ---- 2. 语义描述形态往返 ----
    m = build(module)
    revert_to_semantic(m, set(ground))
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        m._assign_ids()
        m._backfill_semantic_branch_tt()
        warns = [str(w.message) for w in ws]

    backfilled = {(e["dimension"], e["value"]): e["target_transition"]
                  for e in m.meta["branch_tt_backfilled"]}
    deviations = {(e["dimension"], e["value"]): e
                  for e in m.meta["branch_tt_deviations"]}
    final = collect_branches(m)

    # 2a. 每分支恰居其一：回填等价 / 偏差标记 / 第三态
    for pair, g in ground.items():
        if pair in backfilled:
            if final.get(pair) != g:
                print(f"FAIL 回填不等价: {pair} backfilled={final.get(pair)!r} "
                      f"ground={g}"); fail += 1
        elif pair in deviations:
            if final.get(pair) != pair[1]:      # 语义描述保留 == value
                print(f"FAIL 偏差未保留语义描述: {pair} final={final.get(pair)!r}"
                      f"（应为 {pair[1]!r}）"); fail += 1
        else:
            print(f"FAIL 未回填也未记偏差（第三态）: {pair} final={final.get(pair)!r}"
                  f" ground={g}"); fail += 1

    # 2b. 偏差分支须标 inferred
    for d in m.branch_dimensions:
        for br in d["branches"]:
            if (d["dimension"], br["value"]) in deviations \
                    and not br.get("inferred"):
                print(f"FAIL 缺 inferred: {(d['dimension'], br['value'])}"); fail += 1

    # 2c. 警告只对偏差（每偏差一条）
    wdev = [w for w in warns if "非正式号形态" in w]
    if len(wdev) != len(deviations):
        print(f"FAIL 警告数 {len(wdev)} != 偏差数 {len(deviations)}"); fail += 1

    print(f"分支总数={len(ground)} 回填={len(backfilled)} 偏差={len(deviations)} "
          f"警告={len(wdev)}")
    print("基准（value → 正式 tid）:")
    for k, v in sorted(ground.items()):
        mark = "dev" if k in deviations else "ok "
        print(f"  [{mark}] {k[0]:<8} {k[1]:<6} -> {v}")
    if fail:
        print(f"RESULT: FAIL ({fail})")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "srs_data.pt_srsv6"))
