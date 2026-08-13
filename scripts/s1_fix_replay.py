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
- 决策 3: S1 givens 增加 given_type 字段 (state|flow|constraint|event|branch|
  rule|rule_noise|restatement), 渲染层变纯格式选择器。语义净化下沉:
  rule=被测 BR 原文上下文, rule_noise=空泛占位跳过, restatement=对象实例复述
  句子形态; 另 S1 标记 subsumed=True (transition_target 状态行被同 target
  behavior 行完全包含 → 渲染省略)。
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
    _correct_branch_titles,
    _generate_markdown,
    _translate_procedures,
)
from models.state import AgentState  # noqa: E402
from models.schema import ObligationType, obligation_type_label  # noqa: E402
from nodes.s0_topology import _compute_s0_deterministic  # noqa: E402
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


def _partial_key(p: dict) -> tuple:
    """放松的结构键 — content-key 失配但语义孪生仍可匹配。

    Fix 3/4 改变 thens/embedded_brs 后 content-key 失配, 但 source_ids +
    obligation_type + entity + when.action + 首条 then 期望 不变的用例
    （如 PROC-014/026）仍可对回归档的语义孪生标题。
    """
    srcs = tuple(sorted(
        re.sub(r"\[[a-z]\]$", "", s) for s in (p.get("source_ids") or [])
    ))
    w = p.get("when") or {}
    first_then = ""
    for t in (p.get("thens") or []):
        e = t.get("expectation", "") if isinstance(t, dict) else (t or "")
        if e:
            first_then = e
            break
    return (
        srcs,
        p.get("obligation_type"),
        p.get("entity"),
        _norm_event(w.get("event")),
        w.get("action"),
        first_then,
    )


def _fill_missing_titles(procedures: list[dict], archived_procs: list[dict],
                         id_to_name: dict[str, str]) -> int:
    """对 overlay 失配的空标题用例兜底：放松结构键语义孪生 + 确定性构建。

    只填 (p.get("title") 为空) 的用例, 不覆盖已命中标题。
    """
    idx: dict[tuple, list] = defaultdict(list)
    for ap in archived_procs:
        if ap.get("title"):
            idx[_partial_key(ap)].append(ap)
    for group in idx.values():
        group.sort(key=_instance_no)

    filled = 0
    for p in procedures:
        if p.get("title"):
            continue
        pt = copy.deepcopy(p)
        _translate_procedures([pt], id_to_name)
        group = idx.get(_partial_key(pt))
        if group:
            n = _instance_no(p)
            target = next((c for c in group if _instance_no(c) == n), group[0])
            p["title"] = target.get("title")
            filled += 1
            continue
        # 确定性构建：首条 then 期望去 [BR-xxx] 前缀
        exp = ""
        for t in (p.get("thens") or []):
            e = t.get("expectation", "") if isinstance(t, dict) else (t or "")
            e = re.sub(r"^\[[A-Z0-9-]+\]\s*", "", (e or "").strip())
            if e:
                exp = e
                break
        if exp:
            p["title"] = f"验证{exp}"
            filled += 1
    return filled


def _build_output(state: AgentState, cm: dict, es_orig: dict,
                  id_to_name: dict[str, str]) -> dict:
    procedures = _translate_procedures(copy.deepcopy(state["procedures"]), id_to_name)

    # 与 main.py 真实流水线同构: type_counts 按 obligation_type 映射
    # (非 type_label), 保证提升为 canonical 后 statistics 结构一致。
    type_counts: dict[str, int] = {}
    phase_counts: dict[str, int] = {}
    for p in procedures:
        ot = p.get("obligation_type", 0)
        label = obligation_type_label(ot)
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
    ap.add_argument("--recompute-s0", action="store_true",
                    help="重算 S0 (确定性) 取代归档 engine_state — leaf_level/leaf_entity_ids "
                         "只有重跑 S0 才会产出 (S0 是拓扑单一事实源)。S0 警告并入输出。")
    a = ap.parse_args()
    archived_path = Path(a.archive)
    coverage_path = Path(a.coverage)
    out_json = Path(a.out_json)
    out_md = Path(a.out_md)

    archived = _load(archived_path)
    cm = _load(coverage_path)

    warn0: list[str] = []
    if a.recompute_s0:
        es = _compute_s0_deterministic(cm, warn0)
        # set → 确定性 sorted list (JSON 可序列化; 谓词侧 leaf_entity_ids() 会再 set())
        es["leaf_entity_ids"] = sorted(es.get("leaf_entity_ids", set()))
        archived_es = es
        state = _run_pipeline({"engine_state": es}, cm)
        # S0 警告并入 (重跑 S0 时 S1 起始为空, 否则 S0 警告丢失)
        state["warnings"] = warn0 + list(state.get("warnings", []))
    else:
        archived_es = archived.get("engine_state") or {}
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

    # Type9 确定性标题兜底: overlay 按结构键匹配, Type9 的 then 增删会改变内容
    # 键导致失配 (标题 None)。字段校验用例标题由模板确定性补全 (不依赖 LLM),
    # entity 取中文名与渲染一致。
    filled = 0
    for p in replayed:
        if p.get("obligation_type") == ObligationType.FIELD_VALIDATION and not p.get("title"):
            ent = id_to_name.get(p.get("entity"), p.get("entity", ""))
            p["title"] = f"{ent}信息录入页面打开时，提交含违规值表单，验证校验失败并提示"
            filled += 1
    print(f"[TYPE9] filled {filled} deterministic Type9 titles")

    # 空标题兜底: overlay 失配(语义孪生) + 确定性构建, 补 Fix 3/4 变更用例
    filled2 = _fill_missing_titles(replayed, archived["procedures"], id_to_name)
    print(f"[FILL] filled {filled2} missing titles (relaxed-key + deterministic)")

    # Fix-2: 分支标题确定性修正 (B级/C级 取值覆盖 LLM 标题中的级别字样)
    _correct_branch_titles(replayed)

    output = _build_output(state, cm, archived_es, id_to_name)

    out_bytes = json.dumps(output, ensure_ascii=False, indent=2).replace("\n", "\r\n")
    out_json.write_bytes(out_bytes.encode("utf-8"))
    _generate_markdown(output["procedures"], str(out_md), cm)
    print(f"[OK] wrote {out_json.name} ({len(out_bytes)} bytes) + {out_md.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
