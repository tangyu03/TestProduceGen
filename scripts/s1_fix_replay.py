#!/usr/bin/env python3
"""S1 修复回放 — 从归档 engine_state + coverage_obligations.json 重建 AgentState，
确定性重跑 S1→S2→S3→S4（全部 LLM 调用跳过），按结构键 overlay 归档的 title，
翻译实体码，输出 staging JSON + MD。

用户定调 (DECISIONS ㉛):
- 决策 1 A(回放重跑): 确定性主线不容破坏, 不重跑 S0 (含 _select_primary_via_llm
  兜底), 从归档 engine_state 重建。
- 决策 2: 不归档 action_classification; S1 注入空 stub 跳过动作分类 LLM, 重跑后
  按结构键 overlay 归档 title。actor 由 coverage 模型确定性派生 (已验证与归档
  零 diff), 不 overlay —— temp_id 主键会因拆分重编号而错配 (曾致 483/720 污染),
  故 overlay 一律结构键, 不动 actor。零 title diff。
- 决策 3: S1 givens 增加 given_type 字段 (state|flow|constraint|event|branch),
  渲染层变纯格式选择器。
- T-002 分支拆分 (scripts/t2_branch_split.py): T-002 → T-002[a-c] 按 项目评级
  拆 3 变体; occurrence_limit 归位于 T-002[b] (不合格), constraint_predicate 与
  branch_path 职责正交; t3_occ_limit_detach.py 已退役 (串线根因已消除)。

确定性: 每次在全新子进程运行 (tools.fallback_log 模块态不跨进程污染),
`python scripts/s1_fix_replay.py` 双跑 SHA-256 一致。

输出: p3_agent_output.s1fix.json / p3_agent_output.s1fix.md (不覆盖归档 JSON)。
"""
from __future__ import annotations

import copy
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

sys.stdout.reconfigure(encoding="utf-8")

from main import (  # noqa: E402
    _build_clause_coverage,
    _build_time_sensitive_metadata,
    _build_transition_phase_metadata,
    _generate_markdown,
    _translate_procedures,
)
from models.state import AgentState  # noqa: E402
from nodes.s1_generation import s1_generation_node  # noqa: E402
from nodes.s2_sorting import s2_sorting_node  # noqa: E402
from nodes.s3_dependency import s3_dependency_node  # noqa: E402
from nodes.s4_multi_instance import s4_multi_instance_node  # noqa: E402
import tools.fallback_log as _fl  # noqa: E402

# 归档/输出路径默认指向通用样例;其它需求(如 PT017)经 CLI 参数覆盖,
# 见 main() 的 argparse。p3_agent_output.* 为另一需求的产物,默认分支不变。
ARCHIVED_PATH = ROOT / "p3_agent_output.json"
COVERAGE_PATH = ROOT / "coverage_obligations.json"
OUT_JSON = ROOT / "p3_agent_output.s1fix.json"
OUT_MD = ROOT / "p3_agent_output.s1fix.md"


def _load(path: Path) -> dict:
    return json.load(open(path, encoding="utf-8"))


def _build_id_to_name(cm: dict) -> dict[str, str]:
    ctx = cm.get("_context", {})
    entity_list = ctx.get("entity_details", [])
    if isinstance(entity_list, dict):
        entity_list = [v for v in entity_list.values() if isinstance(v, dict)]
    elif not isinstance(entity_list, list):
        entity_list = []
    out = {}
    for e in entity_list:
        if e.get("id") and e.get("name"):
            out[e["id"]] = e["name"]
    return out


def _run_pipeline(archived: dict, cm: dict) -> AgentState:
    """S1→S2→S3→S4, 跳过全部 LLM。"""
    state: AgentState = copy.deepcopy(archived.get("engine_state") or {})
    state["coverage_model"] = cm
    state["warnings"] = []
    state["errors"] = []
    state["current_stage"] = "s1"
    state["action_classification"] = {}  # 跳过 S1 动作分类 LLM
    state["br_decomposition"] = {}       # 跳过 BR 分解 LLM

    r1 = s1_generation_node(state)
    state["procedures"] = r1["procedures"]
    state["br_classifications"] = r1["br_classifications"]
    state["type5_filtered"] = r1["type5_filtered"]
    state["warnings"] = r1["warnings"]
    state["errors"] = r1["errors"]
    state["gen_seq_counter"] = r1["gen_seq_counter"]

    state.update(s2_sorting_node(state))
    state.update(s3_dependency_node(state))
    state.update(s4_multi_instance_node(state))
    return state


def _instance_no(p: dict) -> int:
    """从 temp_id 提取实例号: 'PROC-135.3' → 3; 无后缀 → 0。"""
    tid = p.get("temp_id", "") or ""
    if "." in tid:
        try:
            return int(tid.rsplit(".", 1)[1])
        except ValueError:
            pass
    return 0


def _norm_event(ev: str) -> str:
    """归一化 When.event：剥离已退役的「（目标状态：X）」后缀。

    DECISIONS ㉝ 起 _derive_business_event 不再追加目标状态注解（它是 Then
    的断言内容, 对执行人员是干扰）。归档 when.event 仍带后缀, 回放新事件
    不带 → 内容键需两侧归一再匹配, 否则 title overlay 全失配。
    """
    return re.sub(r"（目标状态：[^）]*）$", "", ev or "")


def _content_key(p: dict) -> tuple:
    """结构键 — 拆分不变 + S1 确定性字段 (排除 temp_id/givens/actor/title/_S*)。

    source_ids 归一化: 'T-XXX[变体]' → 'T-XXX', 使拆分前后同源可匹配;
    thens 结构对齐; when.event 归一化去「目标状态」后缀。entity 须在翻译
    空间比较 (archived 已是翻译空间)。
    """
    srcs = tuple(sorted(
        re.sub(r"\[[a-z]\]$", "", s) for s in (p.get("source_ids") or [])
    ))
    thens = tuple(
        (t.get("target"), t.get("expectation"), t.get("kind"))
        for t in (p.get("thens") or [])
    )
    w = p.get("when") or {}
    return (
        srcs,
        p.get("obligation_type"),
        p.get("entity"),
        p.get("dimension") or "",
        _norm_event(w.get("event")),
        w.get("action"),
        thens,
    )


def _overlay(procedures: list[dict], archived_procs: list[dict],
             id_to_name: dict[str, str]) -> tuple[int, int]:
    """结构键 title overlay — 只补 title, 不动 actor。

    背景: 回放跳过动作分类 LLM, actor 由 coverage 模型确定性派生 (已验证
    762/762 与归档零 diff); title 是 LLM 产物, 回放为 None, 需从归档补回。
    temp_id 主键会因 T-002 拆分重编号而错配 (曾致 483/720 actor/title 污染),
    故改结构键: 内容键在翻译空间匹配 (archived 已是翻译空间, replayed 先翻译
    副本), 组内按实例号对齐 (同组 title 可能发散, 如 PROC-056.5 ≠ .1-.4)。

    返回 (命中, 未命中)。
    """
    idx: dict[tuple, list] = defaultdict(list)
    for ap in archived_procs:
        idx[_content_key(ap)].append(ap)
    for group in idx.values():
        group.sort(key=_instance_no)

    hit = miss = 0
    for p in procedures:
        pt = copy.deepcopy(p)
        _translate_procedures([pt], id_to_name)
        group = idx.get(_content_key(pt))
        if not group:
            miss += 1
            continue
        n = _instance_no(p)
        target = next((c for c in group if _instance_no(c) == n), group[0])
        p["title"] = target.get("title")
        hit += 1
    return hit, miss


def _build_output(state: AgentState, cm: dict, es_orig: dict,
                  id_to_name: dict[str, str]) -> dict:
    procedures = _translate_procedures(copy.deepcopy(state["procedures"]), id_to_name)

    # 与 main.py 真实流水线同构: type_counts 按 obligation_type 映射
    # (非 type_label), 保证提升为 canonical 后 statistics 结构一致。
    type_labels = {
        1: "Type1(Transition)", 3: "Type3(Attribute)",
        4: "Type4a(Constraint)", 5: "Type4b(Lifecycle)",
        6: "Type5(CRUD)", 7: "Type6(Invalid)", 8: "Type7(BR)"
    }
    type_counts: dict[str, int] = {}
    phase_counts: dict[str, int] = {}
    for p in procedures:
        ot = p.get("obligation_type", 0)
        label = type_labels.get(ot, f"Type{ot}")
        type_counts[label] = type_counts.get(label, 0) + 1
        ph = p.get("_S2_fields", {}).get("phase_name", "?")
        phase_counts[ph] = phase_counts.get(ph, 0) + 1

    return {
        "engine_state": es_orig,
        "procedures": procedures,
        "br_classifications": state.get("br_classifications", []),
        "type5_filtered": state.get("type5_filtered", []),
        "entity_instance_counts": state.get("entity_instance_counts", {}),
        "warnings": state.get("warnings", []),
        "errors": state.get("errors", []),
        "statistics": {
            "total_procedures": len(procedures),
            "type_counts": type_counts,
            "phase_counts": phase_counts,
            "elapsed_seconds": 0,
        },
        "clause_coverage": _build_clause_coverage(procedures, cm),
        "transition_phase_metadata": _build_transition_phase_metadata(cm),
        "time_sensitive_metadata": _build_time_sensitive_metadata(procedures, cm),
        "fallback_report": _fl.get_fallback_report_dict(),
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="S1 确定性回放重建")
    ap.add_argument("--archive", default=str(ARCHIVED_PATH))
    ap.add_argument("--coverage", default=str(COVERAGE_PATH))
    ap.add_argument("--out-json", default=str(OUT_JSON))
    ap.add_argument("--out-md", default=str(OUT_MD))
    a = ap.parse_args()
    archived_path = Path(a.archive)
    coverage_path = Path(a.coverage)
    out_json = Path(a.out_json)
    out_md = Path(a.out_md)

    archived = _load(archived_path)
    cm = _load(coverage_path)

    state = _run_pipeline(archived, cm)
    replayed = state["procedures"]

    # 校验 temp_id 集与归档一致 (S1 修复不改变 dedup/排序, 结构应 1:1)
    archived_ids = {p.get("temp_id") for p in archived["procedures"]}
    replayed_ids = {p.get("temp_id") for p in replayed}
    only_replayed = sorted(replayed_ids - archived_ids)
    only_archived = sorted(archived_ids - replayed_ids)
    print(f"[S1] replayed {len(replayed)} procs; temp_id diff: "
          f"+{len(only_replayed)} / -{len(only_archived)}")
    if only_replayed:
        print(f"      only replayed: {only_replayed[:20]}")
    if only_archived:
        print(f"      only archived: {only_archived[:20]}")

    # 决策 2: 结构键 title overlay (actor 不动)
    id_to_name = _build_id_to_name(cm)
    hit, miss = _overlay(replayed, archived["procedures"], id_to_name)
    print(f"[OVERLAY] title overlay (content-keyed): {hit} hit, {miss} miss")

    output = _build_output(state, cm, archived.get("engine_state") or {},
                           id_to_name)

    out_bytes = json.dumps(output, ensure_ascii=False, indent=2).replace("\n", "\r\n")
    out_json.write_bytes(out_bytes.encode("utf-8"))
    _generate_markdown(output["procedures"], str(out_md), cm)
    print(f"[OK] wrote {out_json.name} ({len(out_bytes)} bytes) + {out_md.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
