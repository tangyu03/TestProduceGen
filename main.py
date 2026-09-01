#!/usr/bin/env python3
"""P3 Agent Engine — Main Entry Point.

Usage:
    python main.py <coverage_model_path> [output_path]
"""
from __future__ import annotations
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from graph import compile_p3_graph
from models.state import AgentState
from models.schema import obligation_type_label
from tools.llm_client import TitleGenerator
from tools.llm.http_utils import call_llm_api, parse_llm_response
from context.render_registry import TYPE_LABEL_CN, build_phase_labeler

# v29 Engineering Optimization Gap 1: Fallback Observability
# The fallback collector is initialized in build_obligations.py (P2) and
# accumulated through S0/S1/S3. At main.py finalize time we read the
# accumulated report and write it to the output JSON for audit / dashboards.
import tools.fallback_log as _fl


def run_p3_pipeline(
    coverage_model_path: str,
    output_path: str,
    hide_markers: bool = False,
) -> dict:
    """Run the complete P3 agent pipeline.

    Args:
        coverage_model_path: Path to P2 coverage_model.json
        output_path: Path to write the output JSON
        hide_markers: When True, the rendered markdown omits machine id markers
            (obligation ids in 覆盖需求, BR ids / cross annotations in Then),
            keeping only human-readable refs and rule text.

    Returns:
        The final state dict
    """
    print("=" * 60)
    print("P3 Agent Engine — Test Procedure Orchestration")
    print("=" * 60)
    
    # Verify input exists
    if not Path(coverage_model_path).exists():
        print(f"ERROR: Coverage model not found: {coverage_model_path}")
        sys.exit(1)
    
    # Compile the graph
    print("\n[1/5] Compiling LangGraph pipeline...")
    app = compile_p3_graph()
    print("      [OK] Graph compiled: S0 → S1 → S2 → S3 → S4 → Done")
    
    # Initialize state
    initial_state: AgentState = {
        "messages": [],
        "coverage_model_path": coverage_model_path,
        # S0 fields
        "primary_entity": None,
        "phase_table": None,
        "dep_state_phase_map": None,
        "contextual_phase_rules": None,
        "state_type_map": None,
        "dependent_entities": None,
        "entity_parent": None,
        "dependency_depth": None,
        "topology_levels": None,
        "leaf_entity_ids": set(),
        "virtual_entities": None,
        # P2 model
        "coverage_model": None,
        # S1 output
        "procedures": None,
        "br_classifications": None,
        "type5_filtered": None,
        "gen_seq_counter": 0,
        # S2 output
        "sorted_procedures": None,
        # S3 output
        "dependency_graph": None,
        # S4 output
        "entity_instance_counts": None,
        # Metadata
        "warnings": [],
        "current_stage": "init",
        "errors": [],
    }
    
    # Run the pipeline with streaming progress
    print("\n[2/5] Running pipeline...")
    start_time = time.time()
    
    stage_labels = {
        "s0": "S0 - Topology Discovery",
        "s1": "S1 - Procedure Generation",
        "s2": "S2 - Sorting & Ordering",
        "s3": "S3 - Dependency Binding",
        "s4": "S4 - Multi-instance Expansion",
    }
    result = dict(initial_state)
    
    for event in app.stream(initial_state):
        for node_name, node_output in event.items():
            result.update(node_output)
            stage = node_output.get("current_stage", node_name)
            label = stage_labels.get(stage, f"Stage {stage}")
            procs = result.get("procedures") or []
            n_procs = len(procs)
            n_warn = len(result.get("warnings", []))
            n_err = len(result.get("errors", []))
            print(f"      [OK] {label} ({n_procs} procedures, {n_warn} warnings, {n_err} errors)")
    
    elapsed = time.time() - start_time
    print(f"      [OK] Pipeline completed in {elapsed:.2f}s")
    
    # Process results
    procedures = result.get("procedures") or []
    warnings = result.get("warnings", [])
    errors = result.get("errors", [])
    current_stage = result.get("current_stage", "unknown")
    
    print(f"\n[3/5] Results Summary:")
    print(f"      Final stage: {current_stage}")
    print(f"      Total procedures: {len(procedures)}")
    print(f"      Warnings: {len(warnings)}")
    print(f"      Errors: {len(errors)}")
    
    # Type breakdown
    type_counts = {}
    for proc in procedures:
        ot = proc.get("obligation_type", 0)
        label = obligation_type_label(ot)
        type_counts[label] = type_counts.get(label, 0) + 1
    
    print("\n      By Type:")
    for label, count in sorted(type_counts.items()):
        print(f"        {label}: {count}")
    
    # Phase distribution
    phase_counts = {}
    for proc in procedures:
        phase = proc.get("_S2_fields", {}).get("phase", -1)
        phase_name = proc.get("_S2_fields", {}).get("phase_name", f"P{phase}")
        phase_counts[phase_name] = phase_counts.get(phase_name, 0) + 1
    
    print("\n      By Phase:")
    for phase_name, count in sorted(phase_counts.items()):
        print(f"        {phase_name}: {count}")
    
    # Multi-instance summary
    multi_count = sum(1 for p in procedures if p.get("_S4_fields", {}).get("multi_instance"))
    total_instances = sum(p.get("_S4_fields", {}).get("multi_count", 1) for p in procedures)
    print(f"\n[4/5] Multi-instance: {multi_count} procedures with multiple instances, {total_instances} total instances")

    # Build entity-ID → Chinese-name map for output translation
    coverage_model = result.get("coverage_model") or {}
    ctx = coverage_model.get("_context", {})
    id_to_name: dict[str, str] = {}
    # Handle both list and dict formats of entity_details
    entity_list = ctx.get("entity_details", [])
    if isinstance(entity_list, dict):
        entity_list = [v for v in entity_list.values() if isinstance(v, dict)]
    elif not isinstance(entity_list, list):
        entity_list = []
    for e in entity_list:
        eid = e.get("id", "")
        ename = e.get("name", "")
        if eid and ename:
            id_to_name[eid] = ename

    # Generate natural-language titles (condition + action + result)
    procedures = _generate_titles(procedures)

    # Replace all entity codes with Chinese names in the final output
    procedures = _translate_procedures(procedures, id_to_name)

    # Save output
    print(f"\n[5/5] Saving output to: {output_path}")

    # ── 方案 B: 构建 clause_coverage 索引 ──
    # 从 coverage_model 的 source_ref 字段提取需求条目编号（如 "4.9.7"），
    # 建立 clause → [source_ids] 映射，再对每个 source_id 查找对应的 procedure，
    # 建立 clause → [proc_ids] 映射。让 validator 能用结构化 ID 回溯覆盖关系，
    # 无需依赖脆弱的关键词匹配。
    clause_coverage = _build_clause_coverage(procedures, result.get("coverage_model", {}))
    print(f"\n      Clause Coverage Index:")
    print(f"        total_clauses: {clause_coverage['summary']['total_clauses']}")
    print(f"        covered_clauses: {clause_coverage['summary']['covered_clauses']}")
    print(f"        uncovered_clauses: {clause_coverage['summary']['uncovered_clauses']}")

    # ── V08 修复: 构建 transition_phase_metadata ──
    # 标注每个 transition 的 edge_type（forward/side_effect/rollback/branch），
    # 让 validator 能区分"正常的 phase regression"（回退/循环转换）与
    # "异常的 phase inversion"（forward 转换却 phase 倒退）。
    transition_phase_metadata = _build_transition_phase_metadata(result.get("coverage_model", {}))
    print(f"\n      Transition Phase Metadata:")
    print(f"        total_transitions: {transition_phase_metadata['summary']['total_transitions']}")
    print(f"        forward: {transition_phase_metadata['summary']['forward']}")
    print(f"        side_effect/rollback/branch: {transition_phase_metadata['summary']['non_forward']}")

    # ── V06 修复: 构建 time_sensitive_procedures 索引 ──
    # 标注 time_sensitive 用例的触发方式（clock_injection/db_time_update/scheduler_manual_trigger），
    # 让 validator 能确认超时用例有明确的执行路径。
    time_sensitive_metadata = _build_time_sensitive_metadata(procedures, result.get("coverage_model", {}))
    print(f"\n      Time-Sensitive Metadata:")
    print(f"        total_time_sensitive_procs: {time_sensitive_metadata['summary']['total']}")
    print(f"        with_trigger_method: {time_sensitive_metadata['summary']['with_trigger']}")

    output = {
        "engine_state": {
            "primary_entity": result.get("primary_entity"),
            "phase_table": result.get("phase_table"),
            "dep_state_phase_map": result.get("dep_state_phase_map"),
            "contextual_phase_rules": result.get("contextual_phase_rules"),
            "state_type_map": result.get("state_type_map"),
            "dependent_entities": result.get("dependent_entities"),
            "entity_parent": result.get("entity_parent"),
            "dependency_depth": result.get("dependency_depth"),
            "topology_levels": result.get("topology_levels"),
            "leaf_entity_ids": sorted(result.get("leaf_entity_ids", set())),
            "virtual_entities": result.get("virtual_entities"),
        },
        "procedures": procedures,
        "br_classifications": result.get("br_classifications", []),
        "type5_filtered": result.get("type5_filtered", []),
        "entity_instance_counts": result.get("entity_instance_counts", {}),
        "warnings": warnings,
        "errors": errors,
        "statistics": {
            "total_procedures": len(procedures),
            "type_counts": type_counts,
            "phase_counts": phase_counts,
            "elapsed_seconds": round(elapsed, 2),
        },
        # 方案 B: clause → source_ids → proc_ids 追溯索引
        # validator 可直接用此索引检查需求条目覆盖度，无需关键词匹配
        "clause_coverage": clause_coverage,
        # V08 修复: transition phase metadata — 标注 edge_type
        # validator 检查 phase regression 时应跳过 side_effect/rollback/branch
        "transition_phase_metadata": transition_phase_metadata,
        # V06 修复: time_sensitive 用例的触发方式索引
        # validator 检查超时用例时可确认有明确执行路径
        "time_sensitive_metadata": time_sensitive_metadata,
        # v29 Engineering Optimization Gap 1: fallback observability report
        # Covers P2/S0/S1/S3 fallback sites. A clean run (is_clean_run=True)
        # means every structured field was populated and NO keyword/heuristic
        # fallback fired. Until P1 prompt is updated to emit the structured
        # fields, this report WILL list every site as degraded — that is the
        # whole point of measuring.
        "fallback_report": _fl.get_fallback_report_dict(),
    }

    # v29 Engineering Optimization: surface fallback summary on stdout so
    # it's visible in pipeline logs without inspecting JSON.
    _fb_summary = _fl.get_fallback_summary()
    print(f"\n      Fallback Report:")
    print(f"        total_events: {_fb_summary['total_events']}")
    print(f"        is_clean_run: {_fb_summary['is_clean_run']}")
    print(f"        degraded_sites: {_fb_summary['degraded_sites']}")
    if _fb_summary['degraded_sites']:
        print(f"        (Hint: update P1 prompt to emit structured fields so")
        print(f"         these sites no longer fall back to keyword logic.)")
    
    print("\n      Engine State:")
    es = output['engine_state']
    print(f"        primary_entity: {es['primary_entity']}")
    print(f"        phase_table: {json.dumps(es['phase_table'], ensure_ascii=False)}")
    print(f"        dep_state_phase_map: {json.dumps(es['dep_state_phase_map'], ensure_ascii=False)}")
    print(f"        contextual_phase_rules: {json.dumps(es['contextual_phase_rules'], ensure_ascii=False)}")
    print(f"        state_type_map: {json.dumps(es['state_type_map'], ensure_ascii=False)}")
    print(f"        dependent_entities: {json.dumps(es['dependent_entities'], ensure_ascii=False)}")
    print(f"        entity_parent: {json.dumps(es['entity_parent'], ensure_ascii=False)}")
    print(f"        dependency_depth: {json.dumps(es['dependency_depth'], ensure_ascii=False)}")
    print(f"        topology_levels: {json.dumps(es['topology_levels'], ensure_ascii=False)}")
    print(f"        virtual_entities: {json.dumps(es['virtual_entities'], ensure_ascii=False)}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # BUGFIX #17: avoid re-serialising the entire output dict just to count
    # bytes — use the file size directly.
    import os
    print(f"      [OK] Saved {os.path.getsize(output_path)} bytes")
    
    # Also generate markdown test procedures
    md_path = output_path.replace(".json", ".md")
    _generate_markdown(procedures, md_path, coverage_model, hide_markers=hide_markers)
    print(f"      [OK] Markdown saved to: {md_path}")

    if errors:
        print(f"\n[{len(errors)} errors encountered:]")
        for err in errors[:10]:
            print(f"  - {err}")
    
    print("\n" + "=" * 60)
    print("P3 Agent Engine — Complete")
    print("=" * 60)
    
    return output


def _safe_join(value):
    """Safely join a list of strings, handling None and non-string items."""
    if not value:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def _display_id(tid) -> str:
    """折叠后展示用 procedure id：剥掉实例后缀 .N。

    多实例折叠后 doc 只渲染规范例（PROC-057），JSON 的 .N 副本不单独成页，
    依赖/弱依赖里对具体实例的引用（PROC-057.1）在展示时归一为基例 id。
    纯展示归一，不碰 JSON 数据；实例是纯重复，语义等价。
    """
    s = tid if isinstance(tid, str) else str(tid)
    return re.sub(r"\.\d+$", "", s)


def _correct_branch_titles(procedures: list[dict]) -> None:
    """Fix-2: 分支感知标题修正（确定性、幂等、数据驱动）。

    分支用例（givens 含 given_type='branch'）的标题曾在 LLM 生成/归档回放时
    锚定基准分支取值——C 级分支继承 B 级标题（如"级别为B级时"、PROC-165 系列）。

    层级取值不从常量表硬编码（[A-C]级 曾致非 A/B/C 分级的需求失配），而全部
    从该用例自己的 givens 推导：
      - 权威分支值 = branch given 的 state（如 "C级"）；
      - 候选层级值 = 各 given 描述里跟在分隔符（为/=//或 等）后的 "<设计符>级"
        记号（如约束行 "任务级别为B级或C级" → {B级, C级}），以及 given state
        自身（"C级"）。"<设计符>" 只认表面形态（拉丁/数字/中文数字，≤2 字符），
        是表层语法，不是业务分级表。
    然后用分支值覆盖标题中所有 ≠ 分支值的候选（= 兄弟分支的取值）。无 branch
    given、标题无候选则原样保留（幂等：已正确标题不受影响）。

    与 TITLE_SYSTEM_PROMPT 第 8 条规则配套：前者约束 LLM 源头，后者兜底
    覆盖 LLM 走偏或归档回放（确定性路径不跑 LLM）产出的标题。
    """
    # 表层语法：设计符（拉丁/数字/中文数字 1-2 字符）+ "级"。识别仅依赖
    # 形态，字母表内容由数据给定，禁止在此枚举业务分级名。
    _DESIGNATOR = r"[A-Za-z0-9一二三四五六七八九十]{1,2}"
    _SEP = r"(?:为|＝|=|或|，|；|:|：)"
    for proc in procedures:
        givens = proc.get("givens") or []
        branch_val = ""
        candidates: set[str] = set()
        for g in givens:
            if g.get("given_type") == "branch":
                branch_val = (g.get("state") or "").strip()
            desc = g.get("description") or ""
            for m in re.finditer(rf"{_SEP}\s*({_DESIGNATOR})级", desc):
                candidates.add(m.group(1) + "级")
            state = (g.get("state") or "").strip()
            if re.fullmatch(rf"{_DESIGNATOR}级", state):
                candidates.add(state)
        if not branch_val:
            continue
        title = proc.get("title") or ""
        if not title:
            continue
        new_title = title
        for tok in sorted(candidates - {branch_val}):
            new_title = new_title.replace(tok, branch_val)
        if new_title != title:
            proc["title"] = new_title


def _generate_titles(procedures: list[dict],
                     batch_size: int = 20,
                     max_concurrency: int = 3) -> list[dict]:
    """Generate natural-language titles for all procedures using a free/cheap LLM.

    Titles follow the "条件+动作+结果" (condition + action + result) pattern.
    Uses pure HTTP API call — no Node.js SDK dependency.

    Batches are sent concurrently (ThreadPoolExecutor) to leverage 智谱's
    concurrent-request limit (free tier: 2–5). Default concurrency = 3.

    Args:
        procedures: List of procedure dicts.
        batch_size: Number of procedures per API call (max 20).
        max_concurrency: Max concurrent API calls. Safe default = 3 for free tier.

    Returns:
        The same procedures list with "title" field populated.
    """
    # Fix-5: pre-populate deterministic titles for cross-entity cascade
    # procedures. These have When.action containing "联动"/"自动转换"/"系统"
    # (system-triggered cascade) — using entity as the title subject would
    # be misleading (e.g. "归档项目" when the actual operation is "评审计划
    # 归档联动"). For these, use the action itself as the title subject.
    _CASCADE_ACTION_MARKERS = ('联动', '自动转换', '系统触发', '级联')
    for proc in procedures:
        action = proc.get('when', {}).get('action', '') or ''
        if any(m in action for m in _CASCADE_ACTION_MARKERS):
            # Build a deterministic title from givens + action + thens
            givens = proc.get('givens', [])
            condition_parts = []
            for g in givens[:3]:  # cap at 3 to keep title short
                state = g.get('state', '')
                desc = g.get('description', '')
                # Prefer branch condition desc; else use state
                if '分支条件' in desc:
                    condition_parts.append(desc.replace('分支条件: ', ''))
                elif state and state not in ('(初始)', '(None)'):
                    condition_parts.append(state)
            condition = '且'.join(condition_parts[:2]) if condition_parts else '初始状态'
            # Then expectation (first non-empty)
            then_exp = ''
            for t in proc.get('thens', []):
                exp = t.get('expectation', '')
                if exp:
                    then_exp = exp
                    break
            # Title: "{condition}时，{action}，验证{expectation}"
            proc['title'] = f"{condition}时，{action}，验证{then_exp}"

    # Fix-2: 确定性分支标题修正——在无 LLM 路径下先兜底一次
    _correct_branch_titles(procedures)

    generator = TitleGenerator()

    if not generator.available:
        print("      [SKIP] Title generation: LLM_API_KEY not set")
        return procedures

    print(f"      [TITLE] Generating natural-language titles for {len(procedures)} procedures...")
    print(f"      [TITLE] API: {generator._api_base}, model: {generator._model}")
    print(f"      [TITLE] Concurrency: {max_concurrency}, batch_size: {batch_size}")

    # Build all batches upfront
    batches: list[tuple[int, list[dict]]] = []
    for i in range(0, len(procedures), batch_size):
        batch_num = i // batch_size + 1
        batches.append((batch_num, procedures[i:i + batch_size]))

    total_batches = len(batches)
    generated_count = 0
    failed_count = 0

    def _process_batch(batch_num: int, batch: list[dict]) -> tuple[int, int, int]:
        """Process a single batch — runs in a thread."""
        try:
            titles = generator.generate_batch(batch)
            assigned = 0
            for proc, title in zip(batch, titles):
                # Fix-5: don't overwrite cascade titles with LLM output
                # if the LLM title is empty or shorter than the cascade one.
                if title and not proc.get('title'):
                    proc["title"] = title
                    assigned += 1
                elif title and proc.get('title') and len(title) > len(proc['title']):
                    proc["title"] = title
                    assigned += 1
            return (batch_num, assigned, len(batch))
        except Exception as e:
            # On rate-limit, signal to slow down
            if "429" in str(e) or "Too Many Requests" in str(e):
                print(f"      [TITLE] Batch {batch_num}/{total_batches} rate-limited, "
                      f"pausing 30s before next submissions...")
                time.sleep(30)
            else:
                print(f"      [WARN] Title batch {batch_num}/{total_batches} failed: {e}")
            return (batch_num, 0, len(batch))

    with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
        futures = {
            executor.submit(_process_batch, bn, batch): bn
            for bn, batch in batches
        }

        for future in as_completed(futures):
            bn, assigned, total = future.result()
            if assigned > 0:
                generated_count += assigned
                batch_label = f"Batch {bn}/{total_batches}"
                # Progress indicator — show how far we are
                remaining = len(futures) - sum(1 for f in futures if f.done())
                print(f"      [TITLE] {batch_label}: {assigned}/{total} titles generated "
                      f"({remaining} batches remaining)")
            else:
                failed_count += 1

    # Report stats
    with_title = sum(1 for p in procedures if p.get("title"))
    without_title = len(procedures) - with_title
    print(f"      [TITLE] Done: {with_title} generated, {without_title} fallback to post_state")

    # Fix-2: LLM 标题落地后，再确定性覆盖分支取值，保证正确性不依赖 LLM
    _correct_branch_titles(procedures)

    return procedures


def _translate_procedures(procedures: list[dict], id_to_name: dict[str, str]) -> list[dict]:
    """Replace all entity codes (E-XXX) with Chinese names in every text field.

    Walks through all procedures and recursively replaces entity IDs
    with their human-readable Chinese names in ALL string fields:
    entity, post_state, steps.*, cascade_chain, title, _S4 multi_reason, etc.

    Args:
        procedures: List of procedure dicts.
        id_to_name: Mapping from entity-ID to Chinese name (e.g. {"E-LAB": "实验室"}).

    Returns:
        Procedures with all entity codes replaced.
    """
    if not id_to_name:
        return procedures

    def _replace(text: str) -> str:
        for code, chinese in id_to_name.items():
            text = text.replace(code, chinese)
        return text

    def _walk(obj):
        """Recursively replace entity codes in all strings."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str):
                    obj[k] = _replace(v)
                elif isinstance(v, (dict, list)):
                    _walk(v)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                if isinstance(v, str):
                    obj[i] = _replace(v)
                elif isinstance(v, (dict, list)):
                    _walk(v)

    for proc in procedures:
        _walk(proc)

    return procedures


# 渲染层去重/过滤（只影响呈现，不动 JSON 数据 —— validator 依赖的关键词在数据层）。
# 判断逻辑(debug basis、Then 冗余)由引擎层在数据中打标记
# (_S2_fields.phase_basis_debug / Then.dedup_group),渲染层只消费标记,
# 不匹配引擎内部字符串,避免渲染层耦合数据层文本约定。


def _dedup_thens(thens: list[dict]) -> list[dict]:
    """Render-layer Then dedup: drop redundant assertions.

    Data-driven: the S1 layer marks Thens with ``dedup_group`` / ``subsumed``
    (see _make_then / _mark_then_subsumption) so the renderer does NOT match
    data-layer text conventions:
      - "transition_target" (状态转换为X) is implied by "transition_flow"
        (状态流转：from→to), so it is omitted when a flow is present.
      - "transition_target" (状态转换为X) is ALSO implied by a same-target
        "behavior" Then whose expectation asserts the same state
        (状态…为X，如 "回收任务创建，状态初始化为草稿")——状态行被行为行
        完全包含（事件+状态），单独保留无独立信息，省略。吸收判定已下沉到
        S1（_mark_then_subsumption 标记 subsumed=True），此处只消费标记。
      ("coverage_noise" 已随 P2 治本修复移除——op_desc 现用可观察结果,
      不再产生"覆盖X操作"噪声,此分支不再需要。)
    Exact duplicates (normalized whitespace) are also dropped.
    """
    out: list[dict] = []
    seen: set[str] = set()
    has_flow = any(t.get("dedup_group") == "transition_flow" for t in thens)
    for t in thens:
        exp = (t.get("expectation", "") or "").strip()
        if not exp:
            continue
        if t.get("dedup_group") == "transition_target" and has_flow:
            continue
        if t.get("subsumed"):
            continue
        norm = "".join(exp.split())
        if norm in seen:
            continue
        seen.add(norm)
        out.append(t)
    return out


# 名词框架 event 的正则：event 以 "事件"（或其后的括号尾注，如 "(已过期)"）收尾，
# 表明它是 S1 生成的名词化表述（"技术领域配置变更事件" / "尝试…转换事件" /
# "尝试锁定用户事件(已过期)"），而非操作式表述
_NOMINAL_EVENT_RE = re.compile(r".*事件(?:\([^)]*\))?$")


def _is_subsequence(needle: str, haystack: str) -> bool:
    """needle 是否为 haystack 的逐字符子序列（可跳跃，顺序不变）。"""
    it = iter(haystack)
    return all(ch in it for ch in needle)


def _dedupe_when_action(event: str, action: str) -> tuple[str, str]:
    """合并 When 行 event 与 [action] 的重复表述，返回 (展示的 event, 方括号内容)。

    action 常由生成器包成 "执行/尝试<event>" 或与 event 高度重叠，此时方括号里的
    操作名与事件重复，应省略。判定只用文本关系，不依赖任何硬编码动词前缀表：

    1. action 为空 / 与 event 相等 / 互为子串 → 省略方括号，保留 event
       （如 按规则"…"执行操作事件 + 按规则"…"执行操作，子串关系，保留带 BR 的 event）；
    2. event 是名词框架（"…事件"收尾，如 技术领域配置变更事件 / 尝试…转换事件 /
       尝试锁定用户事件(已过期)），action 是其操作式表述（修改技术领域 /
       尝试执行从"已提交"到"已保存"的操作 / 尝试锁定用户(已过期)）→
       两处同义重复，取 action 作为 When 的操作式表述，省略方括号；
    3. action 是 event 的子序列（逐字符按序出现，如 event=提交含违规值的项目表单、
       action=提交含违规值的表单）→ action 不含任何新信息，省略方括号，保留 event。

    其余情况保留 event [action]。返回值直接用于渲染。
    """
    if not action:
        return event, ""
    action_core = action.strip()
    if not action_core:
        return event, ""
    if action_core == event:
        return event, ""
    if event and (action_core in event or event in action_core):
        return event, ""
    # 名词框架 event 与操作式 action 同义 → 取 action（操作式更贴近 BDD When 语义）
    if event and _NOMINAL_EVENT_RE.match(event.rstrip()):
        return action_core, ""
    # action 完全冗余（是 event 的子序列）→ 省略方括号，保留 event
    if event and _is_subsequence(action_core, event):
        return event, ""
    return event, action_core


def _dedupe_then_target(target: str, expectation: str,
                        proc_entity: str | None = None) -> tuple[str, str]:
    """Then 行 target 与 expectation 的文本重复净化，返回 (target_shown, exp_shown)。

    数据驱动：不硬编码任何实体/属性/状态名，只用文本关系。规则顺序判定：
    1. target 为 实体.属性 限定链（如 "专家.技术领域"）且 expectation 以其
       最后一段开头（"技术领域显示为修改后的值"）→ 裁掉 expectation 前导
       重复段，target 保留作主语（"专家.技术领域 显示为修改后的值"）；
    2. target 或其最后一段已原样出现在 expectation 文本中（target=附件、
       expectation="显示项目附件集中查看页面"；或 target=专家.技术领域、
       expectation="校验失败，提示'技术领域选择不在A-J范围内'"）→ target
       完全冗余，省略（纯文本包含判定，不硬编码实体/属性名）；
    3. target 为 实体.状态属性（属性以「状态」结尾）且 expectation 自身含
       「状态」（"状态转换为X"/"状态初始化为X"/…）：属性限定与期望文本语义
       重复，且 target 实体与 proc 一致（跨实体 Then 保留，避免丢主语）→
       target 整体省略。纯文本关系 + 通用语言 token「状态」，无领域词表。
       数据量：同实体状态属性 958 中 831 命中；跨实体 20 条与期望不含
       「状态」的 127 条保留 target；
    4. 跨实体且期望以「状态转换X」开头 → 动词前导「状态」与属性名重复，
       裁为「转换为X」（规则 3 未命中时的兜底）。
    未命中则原样返回 (target, expectation)。
    """
    if "." in target:
        last = target.rsplit(".", 1)[1].strip()
        if last and expectation.startswith(last) and len(expectation) > len(last):
            return target, expectation[len(last):].lstrip()
        if last.endswith("状态") and "状态" in expectation:
            ent_part = target.rsplit(".", 1)[0]
            if proc_entity is None or ent_part == proc_entity:
                return "", expectation
        if last.endswith("状态") and expectation.startswith("状态转换"):
            return target, expectation[len("状态"):].lstrip()
    key = target.rsplit(".", 1)[-1].strip()
    if key and key in expectation:
        return "", expectation
    return target, expectation


def _branch_condition_norm(s: str) -> str:
    """分支条件归一化，用于判断状态给定分句与分支条件 given 是否同义。

    "为"≡"="、去空白。只作同义判据，不影响原文渲染。无领域词汇
    （"为"是通用语言同义符号，非业务词表）。
    """
    return re.sub(r"\s+", "", s or "").replace("为", "=")


def _sep_blank(lines: list[str]) -> None:
    """追加块分隔空行：上一条已是空行则不重复。

    Given 全被哨兵净化跳过时，BDD 组首空行会直接衔接 When/Then 块的
    空行 → 连续两个空行。守卫避免之，不影响其它块的正常单空行分隔。
    """
    if not lines or lines[-1] != "":
        lines.append("")


def _generate_markdown(
    procedures: list[dict],
    md_path: str,
    coverage_model: dict | None = None,
    hide_markers: bool = False,
):
    """Generate human-readable markdown from procedures.

    Collapses multi-instance copies (PROC-001.1, PROC-001.2, ...) into a
    single entry per base procedure — instances are pure duplicates (only
    [实例 N] givens differ), so the readable doc shows one canonical case;
    JSON keeps the .N copies for execution tooling.
    """
    # source_id → 原始需求条目（SRS 章节）映射，用于标注每条用例覆盖的需求
    source_ref_map: dict[str, str] = {}
    state_info: dict = {}
    if coverage_model:
        for lst in ("entity_obligations", "transition_obligations",
                    "cross_entity_obligations", "constraint_obligations"):
            items = coverage_model.get(lst, [])
            if isinstance(items, dict):
                items = [it for sub in items.values() for it in sub]
            for o in items:
                oid = o.get("id")
                ref = o.get("source_ref")
                if oid and ref and oid not in source_ref_map:
                    source_ref_map[oid] = ref
        state_info = (coverage_model.get("_context") or {}).get("state_info") or {}

    # 阶段语义解析器：数据驱动（phase_basis + state_info），见 context/render_registry
    phase_label = build_phase_labeler(state_info, procedures)

    lines = ["# 测试规程\n"]

    # Group multi-instance copies by base ID (strip .N suffix)
    groups: dict[str, list[dict]] = {}
    group_order: list[str] = []
    for proc in procedures:
        tid = proc.get("temp_id", "?")
        base = re.sub(r"\.\d+$", "", tid)
        if base not in groups:
            groups[base] = []
            group_order.append(base)
        groups[base].append(proc)

    for base in group_order:
        procs = groups[base]
        proc = procs[0]

        s2 = proc.get("_S2_fields") or {}
        s3 = proc.get("_S3_fields") or {}

        temp_id = base
        post_state = proc.get("post_state", "")
        # 管理类兜底 Given（state="存在"/description="操作入口可用"，Tier 2 对
        # topology 0 实体的哨兵）已被净化，LLM 标题里同源的退化条件短语
        # （"操作入口可用时，" / "角色存在时，"）一并剥除——判据与 Given 净化
        # 完全相同，不另立实体清单。
        mgmt_fallback_givens = [
            g for g in (proc.get("givens") or [])
            if g.get("state", "") == "存在"
            and re.sub(r"^\[实例 \d+\]\s*", "", g.get("description", "") or "") == "操作入口可用"
        ]
        is_mgmt_fallback = bool(mgmt_fallback_givens) and len(mgmt_fallback_givens) == len(proc.get("givens") or [])
        # 规则类兜底 Given：有效规则上下文（given_type="rule"，desc 携带被测 BR
        # 原文，负向模板）保留；"{...}相关数据已准备" 空泛噪音（S1 标记
        # given_type="rule_noise"）视为冗余跳过。与 管理类哨兵 同构——LLM 标题里
        # 同源的退化条件短语（"规则适用前提满足时，" / "项目规则适用前提满足时，"）
        # 一并剥除。判据全在数据层标记，渲染层不做 BR 原文反查。
        rule_fallback_givens = [
            g for g in (proc.get("givens") or [])
            if g.get("given_type") == "rule_noise"
        ]
        is_rule_fallback = bool(rule_fallback_givens) and len(rule_fallback_givens) == len(proc.get("givens") or [])
        title = proc.get("title") or post_state
        if is_mgmt_fallback:
            title = re.sub(r"^(?:操作入口可用|[^，]+存在)时，", "", title)
        if is_rule_fallback:
            title = re.sub(r"^[^，]*规则适用前提满足时，", "", title)
        lines.append(f"### {temp_id}：{title}")

        type_label = s2.get("type_label", "")
        source_ids = proc.get("source_ids", [])

        # 业务定位：类型 + 阶段（阶段 = 模块名，phase_label 内嵌相位号+落段依据）
        type_cn = TYPE_LABEL_CN.get(type_label, type_label) or "—"
        lines.append(f"**业务定位**：{type_cn} ｜ {phase_label(proc)}")

        # 覆盖需求：source_ids + 原始 source_ref（SRS 章节）
        # hide_markers=True 时省略义务 id（EO-XXX），仅保留 SRS 章节号；
        # 无章节号时兜底保留 id，避免丢失追溯信息。
        if source_ids:
            ref_parts = []
            for sid in source_ids:
                ref = source_ref_map.get(sid, "")
                if hide_markers:
                    ref_parts.append(ref if ref else sid)
                else:
                    ref_parts.append(f"{sid}（{ref}）" if ref else sid)
            lines.append(f"**覆盖需求**：{'；'.join(ref_parts)}")

        if s2.get("context"):
            lines.append(f"**场景**：{s2.get('context')}")
        if proc.get("br_embedded"):
            lines.append(f"**BR嵌入**：{_safe_join(proc.get('br_embedded'))}")

        # BDD clauses: Given / When / Then
        givens = proc.get("givens", [])
        when = proc.get("when", {})
        thens = proc.get("thens", [])
        op_hints = proc.get("operation_hints", [])

        if givens or when or thens:
            _sep_blank(lines)
            # Given clauses
            if givens:
                g_lines = []
                # 已有文本（Then 期望 / When event+action / 其他 given 描述）：
                # 约束行与这些重复则跳过，避免与拒绝原因或分支条件行重复。
                existing_texts = [t.get("expectation", "") for t in thens]
                existing_texts += [when.get("event", ""), when.get("action", "")]
                # 排除 constraint given 自身：S1 修复后约束是独立 given, 若把
                # 它们算进 other_given_texts, 渲染某条约束时其 desc 必命中自己的
                # 条目 → 自去重 → 全部约束行丢失 (0 约束行)。只与状态/流转/分支
                # given 的 desc 比对 (约束文本重复出现在状态 given 描述才跳过)。
                other_given_texts = [
                    re.sub(r"^\[实例 \d+\]\s*", "", g2.get("description", "") or "")
                    for g2 in givens[1:]
                    if g2.get("given_type", "state") != "constraint"
                ]
                for i, g in enumerate(givens):
                    desc = g.get("description", "")
                    # 实例纯重复（JSON 已拆 .N 副本），展开后 [实例 N] 标签是渲染噪音
                    desc = re.sub(r"^\[实例 \d+\]\s*", "", desc)
                    # S1 管理类兜底 Given（state="存在"/description="操作入口可用"，
                    # Tier 2 领域前置对 topology 0 实体的哨兵）无测试价值，跳过。
                    # 纯渲染净化，JSON 哨兵保留给 tier2_verify。
                    if g.get("state", "") == "存在" and desc == "操作入口可用":
                        continue
                    # 规则类 Given：空泛噪音（"{...}相关数据已准备"）由 S1 标记
                    # given_type="rule_noise"，此处直接跳过；有效规则上下文
                    # （given_type="rule"，desc=被测 BR 原文）走下面 rule 分支保留
                    # ——负向模板 When/Then 只含被禁操作，规则原文可能只在 Given
                    # 呈现（PROC-262），删了丢规则。判据全在数据层，渲染层无反查。
                    gtype = g.get("given_type", "state")
                    if gtype == "rule_noise":
                        continue
                    # 分支条件去重：P2 把分支变体的分支条件同时落进 preconditions
                    # 与 branch_path，S1 两处都渲染 → givens[0] 括号分句与分支
                    # 条件 given 同义重复（全量 34 family/110 处；T-014 即
                    # "项目阶段为开题" vs "分支条件: 项目阶段=开题"）。归一化后
                    # 精确相等即从状态描述移除，分支条件行保留为唯一表达。
                    # 纯渲染净化，JSON 数据原样保留。仅 givens[0]：分支条件
                    # 只与第一条状态描述同义。
                    if i == 0:
                        branch_norms = {
                            _branch_condition_norm(
                                g2.get("description", "").replace("分支条件: ", ""))
                            for g2 in givens
                            if (g2.get("description") or "").startswith("分支条件: ")
                        }
                        if branch_norms:
                            clauses = [c.strip() for c in desc.split(";") if c.strip()]
                            kept = [c for c in clauses
                                    if _branch_condition_norm(c) not in branch_norms]
                            if len(kept) != len(clauses):
                                desc = "; ".join(kept)
                    # ── given_type 纯格式选择器（DECISIONS ㉛）──
                    # S1 已按前置类型路由：constraint/flow/跨维度 state 是独立
                    # Given，渲染层只按 given_type 选格式，不再文本匹配/反查
                    # coverage_model。
                    if gtype == "branch" or desc.startswith("分支条件:"):
                        # 分支行纯化：分支 given 的 desc 是 "分支条件: X=Y"，其
                        # target 末段=维度、state=值，与 desc 完全同义（全量 124
                        # 处 0 信息丢失）——再渲染 "X 状态 = Y (…)" 会与状态行视觉
                        # 撞脸（PROC-135 两行都是 "项目.项目阶段 状态 = 开题"）。
                        # 只保留 "分支条件：X=Y" 标记行（用户确认：分支标记本身有
                        # 可读性价值，纯化而非删除）。与约束行同用全角冒号。
                        val = (desc[len("分支条件:"):].strip()
                               if desc.startswith("分支条件:") else desc)
                        g_lines.append(f"- 分支条件：{val}")
                    elif gtype == "constraint":
                        # 业务约束独立行；与 Then/When/其他 given 文本重复则跳过
                        # （如负向用例的拒绝原因已在 Then 出现）。
                        if any(desc in t for t in existing_texts if t):
                            continue
                        if any(desc in t for t in other_given_texts if t):
                            continue
                        g_lines.append(f"- 约束：{desc}")
                    elif gtype == "flow":
                        # 流转形态（ref.state 是目标态）：`流转：X→Y` 直陈流转过程，
                        # desc 保留原文（含 "由…变为/变为/转为"），不伪装成前置态。
                        g_lines.append(f"- {g.get('target', '')} 流转：{desc}")
                    elif gtype == "rule":
                        # 规则上下文（S1 已把 desc 定为被测 BR 原文，无 "规则：" 前缀）：
                        # 哨兵前缀（"X 状态 = 规则适用前提满足 (…)"）无测试价值、且与
                        # 业务定位/规则文本重复，只保留规则原文本身。纯渲染净化，
                        # JSON 哨兵保留。
                        g_lines.append(f"- {desc}")
                    elif gtype == "restatement":
                        # 对象实例复述（desc 已是完整句子形态 "{实体}已存在，处于
                        # {状态}状态"）：与结构化前缀（target 状态 = state）完全
                        # 同义，保留句子形态。句子形态由 S1 模板生成，渲染层不拼接。
                        g_lines.append(f"- {desc}")
                    elif gtype == "field_data":
                        # 表单字段标注：创建/编辑表单的字段清单。Given 在本管线
                        # = 前置条件（S3 依 givens[0].state 建依赖边），字段清单是
                        # 操作的数据内容、非前置状态（定义性事实，恒真不依赖状态），
                        # 故不在 Given 渲染——由 When 块挂到 create/edit 事件步下作
                        # 子行。JSON 数据保留（state 恒空，S3 Guard 1 豁免），纯渲染。
                        continue
                    else:
                        # state/event（默认）：主锚定/同维度/跨维度纯状态 统一格式
                        desc_str = f" ({desc})" if desc else ""
                        tgt = g.get('target', '')
                        # 属性已含「状态」（"载体.载体状态"）时，运算符「状态 =」的
                        # 「状态」与属性名重复 → 只留「=」。裸实体 target
                        # （"文件导出任务"）不含「状态」，运算符保留。纯后缀判定，
                        # 无领域词表。
                        op = "=" if "." in tgt and tgt.rsplit(".", 1)[1].endswith("状态") else "状态 ="
                        g_lines.append(f"- {tgt} {op} {g.get('state', '')}{desc_str}")
                if g_lines:
                    lines.append("**Given**")
                    # 与 When 一致的序号列表：g_lines 各条自带 "- " 无序前缀，
                    # 编号渲染时剥掉该前缀（序号取代无序列表符）。
                    lines.extend(f"{i}. {ln[2:]}" for i, ln in enumerate(g_lines, 1))

            # When clause (single) — [action] 与 event 重复时省略方括号
            if when:
                w = when
                actor_str = f" by {w.get('actor')}" if w.get("actor") else ""
                event_shown, action_core = _dedupe_when_action(
                    w.get("event", ""), w.get("action", "")
                )
                action_str = f" [{action_core}]" if action_core else ""
                # 规则类用例（Type7 standalone BR）：When 行 `按规则"X"执行操作事件`
                # 与 Then 的 [BR]X 正面期望同义反复（87/87 规则文本已完整重复在
                # Then）。判定纯文本关系：event 匹配规则模板 且 引号内规则文本出现
                # 在 Then 期望中 → 该行无独立信息，跳过。无硬编码规则词汇。
                then_text = " ".join(t.get("expectation", "") for t in thens)
                m = re.match(r'^按规则"(.*)"执行操作事件$', event_shown.rstrip())
                tautological_rule = bool(m) and m.group(1) in then_text
                # 操作提示先于 event，按执行顺序编成一张有序清单（序号代替
                # "操作步骤N：" 标签）；无提示时 event 为第 1 步。
                # When 行的 target（操作对象）不再前置——实体必在 Given/Then
                # 上下文点名（保留 target 全量核验 0 缺失），前置反而造成
                # "用户 修改角色" 被误读为执行者的歧义。
                when_steps = [h for h in op_hints]
                if not tautological_rule:
                    when_steps.append(f"{event_shown}{actor_str}{action_str}")
                if when_steps:
                    _sep_blank(lines)
                    lines.append("**When**")
                    for i, step in enumerate(when_steps, 1):
                        lines.append(f"{i}. {step}")
                    # 表单字段标注：字段清单是 create/edit 操作的数据内容，非前置
                    # 条件（Given=前置条件，S3 依 givens[0].state 建边）。挂到事件
                    # 步（最后一步）下作 4 空格续行——列表项内续行不触发代码块。
                    # 纯渲染，JSON 数据不动（field_data given 保留，state 恒空）。
                    fd_descs = [g.get("description", "") or ""
                                for g in givens if g.get("given_type") == "field_data"]
                    for fd_desc in fd_descs:
                        lines.append(f"   表单字段：{fd_desc}")

            # Then clauses (rendering-layer dedup — JSON data untouched)
            if thens:
                # 与 When 一致的序号列表（编号取代无序列表符）。
                then_lines: list[str] = []
                for t in _dedup_thens(thens):
                    # hide_markers=True 时省略 BR id（[BR: ...]）与 cross 实体标注，
                    # 并剥除期望文本行首的 [BR-NNN] 前缀（保留 正面:/负面: 语义标签）。
                    if hide_markers:
                        br_str, xref_str = "", ""
                    else:
                        br_str = f" [BR: {','.join(t.get('br_refs', []))}]" if t.get("br_refs") else ""
                        xref_str = f" [cross: {','.join(t.get('cross_refs', []))}]" if t.get("cross_refs") else ""
                    target_shown, exp_shown = _dedupe_then_target(
                        t.get("target", ""), t.get("expectation", ""),
                        proc.get("entity"),
                    )
                    # 裸实体 target（无属性限定）且等于 proc 自身 entity：实体已在
                    # 业务定位/Given/标题确立，Then 再作主语冗余，省略不丢信息。
                    # 数据驱动 target==proc.entity 文本关系（JSON 全量 412 处无
                    # 例外），属性限定 target（实体.属性）不受影响。
                    if target_shown and "." not in target_shown and target_shown == proc.get("entity"):
                        target_shown = ""
                    if hide_markers:
                        exp_shown = re.sub(r"^\[BR-\d+\]", "", exp_shown)
                    target_str = f"{target_shown} " if target_shown else ""
                    # hide_markers=True 时连同 (behavior)/(state) 等 kind 标签一起省略
                    kind_str = "" if hide_markers else f" ({t.get('kind', 'state')})"
                    then_lines.append(f"{target_str}{exp_shown}{kind_str}{br_str}{xref_str}")
                if then_lines:
                    _sep_blank(lines)
                    lines.append("**Then**")
                    lines.extend(f"{i}. {ln}" for i, ln in enumerate(then_lines, 1))

        # Cascade chain
        cascade = proc.get("cascade_chain")
        if cascade:
            lines.append(f"**级联链**：{cascade}")

        # Dependencies
        deps = s3.get("dependencies")
        if deps:
            lines.append(f"**依赖**：{_safe_join([_display_id(x) for x in deps])}")
        weak_deps = s3.get("weak_dependencies")
        if weak_deps:
            lines.append(f"**弱依赖**：{_safe_join([_display_id(x) for x in weak_deps])}")

        lines.append("")

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# 方案 B: clause_coverage 索引构建
# 从 source_ref 提取需求条目编号，建立 clause → source_ids → proc_ids 追溯链
# ---------------------------------------------------------------------------

# 条目编号正则：匹配 "4.9.7"、"4.8.1(6)a"、"4.5(5)" 等格式
_CLAUSE_RE = re.compile(r'(\d+\.\d+(?:\.\d+)*(?:\(\d+\))?[a-z]?)')


def _extract_clauses(source_ref: str) -> list[str]:
    """从 source_ref 字符串中提取需求条目编号。

    支持格式：
        "4.9.7"           → ["4.9.7"]
        "4.5(1), 4.7.1"   → ["4.5(1)", "4.7.1"]
        "4.8.1(6)a"       → ["4.8.1(6)a"]
        "4.9.7; 4.9.6"    → ["4.9.7", "4.9.6"]
    """
    if not source_ref or not isinstance(source_ref, str):
        return []
    return list(set(_CLAUSE_RE.findall(source_ref)))


def _parent_of(clause: str) -> str:
    """条款的直接父级：4.9.7(3)b → 4.9.7(3) → 4.9.7 → 4.9 → 4 → ""。

    逐级剥离：字母子项后缀（b/c…）、(n) 括号子项、'.数字' 点号子项。
    """
    import re as _re
    s = clause
    m = _re.match(r"^(.*?)[a-z]$", s)
    if m:
        return m.group(1)
    m = _re.match(r"^(.*)\(\d+\)$", s)
    if m:
        return m.group(1)
    m = _re.match(r"^(.*)\.\d+$", s)
    if m:
        return m.group(1)
    return ""


def _build_clause_coverage(procedures: list[dict], coverage_model: dict) -> dict:
    """方案 B: 构建 clause → source_ids → proc_ids 追溯索引。

    数据流：
        1. 遍历 coverage_model 中所有 obligations（TO/EO/CO/RO）
           提取每条的 source_ref → clause 编号
           若 source_ref 为空，从 desc/description 中兜底提取
        2. 建立 clause → [source_ids] 映射
        3. 遍历 procedures，根据 source_ids 反查 clause
           建立 clause → [proc_ids] 映射
        4. 标记每个 clause 的覆盖状态（covered / uncovered）

    输出结构：
        {
            "summary": {total_clauses, covered_clauses, uncovered_clauses},
            "clauses": {
                "4.9.7": {
                    "source_ids": ["RO-BR-055", "RO-BR-057", "T-ORG-005a", ...],
                    "proc_ids": ["PROC-184.1", "PROC-186.1", ...],
                    "covered": true,
                    "coverage_ratio": 0.83
                },
                ...
            }
        }

    validator 可直接使用此索引：
        - 检查 clause.covered == true → 需求条目已覆盖
        - 检查 clause.source_ids 中每个 ID 是否有对应 proc → 精确覆盖
        - 无需关键词匹配，避免模糊性
    """
    # Step 1: 建立 source_id → clauses 映射
    source_id_to_clauses: dict[str, list[str]] = {}

    def _extract_clauses_from_obj(obj: dict, id_field: str, extra_id_field: str = "") -> None:
        """从对象的 source_ref 提取 clause，兜底从 desc/description 提取。"""
        sid = obj.get(id_field, "")
        if not sid:
            return
        source_ref = obj.get("source_ref", "")
        clauses = _extract_clauses(source_ref)
        # 兜底：source_ref 为空时从 desc/description 提取
        if not clauses:
            desc = obj.get("desc", "") or obj.get("description", "") or ""
            clauses = _extract_clauses(desc)
        if clauses:
            source_id_to_clauses[sid] = clauses
        # 额外 ID（如 transition_id、constraint_id）
        if extra_id_field:
            extra_id = obj.get(extra_id_field, "")
            if extra_id and extra_id != sid and clauses:
                source_id_to_clauses.setdefault(extra_id, []).extend(clauses)

    # transition_obligations
    for to in coverage_model.get("transition_obligations", []):
        _extract_clauses_from_obj(to, "id", "transition_id")

    # entity_obligations
    for eo in coverage_model.get("entity_obligations", []):
        _extract_clauses_from_obj(eo, "id")

    # cross_entity_obligations
    for co in coverage_model.get("cross_entity_obligations", []):
        _extract_clauses_from_obj(co, "id")

    # constraint_obligations (BR)
    ros_raw = coverage_model.get("constraint_obligations", [])
    if isinstance(ros_raw, dict):
        ros_flat = [item for sublist in ros_raw.values() for item in sublist]
    elif isinstance(ros_raw, list):
        ros_flat = ros_raw
    else:
        ros_flat = []
    for ro in ros_flat:
        _extract_clauses_from_obj(ro, "id", "constraint_id")

    # Step 2: 建立 clause → source_ids 映射
    clause_to_source_ids: dict[str, set[str]] = {}
    for sid, clauses in source_id_to_clauses.items():
        for clause in clauses:
            clause_to_source_ids.setdefault(clause, set()).add(sid)

    # Step 3: 建立 source_id → proc_ids 映射
    source_id_to_proc_ids: dict[str, list[str]] = {}
    for proc in procedures:
        proc_id = proc.get("temp_id", "")
        for sid in proc.get("source_ids", []):
            source_id_to_proc_ids.setdefault(sid, []).append(proc_id)

    # Step 4: 组装 clause_coverage 输出
    clauses_output: dict[str, dict] = {}
    covered_count = 0
    for clause, source_ids in sorted(clause_to_source_ids.items()):
        # 收集该 clause 下所有 source_id 对应的 proc_ids
        proc_ids_set: set[str] = set()
        covered_source_ids: list[str] = []
        uncovered_source_ids: list[str] = []
        for sid in sorted(source_ids):
            proc_ids = source_id_to_proc_ids.get(sid, [])
            if proc_ids:
                proc_ids_set.update(proc_ids)
                covered_source_ids.append(sid)
            else:
                uncovered_source_ids.append(sid)

        is_covered = len(covered_source_ids) > 0
        if is_covered:
            covered_count += 1

        total_sources = len(source_ids)
        coverage_ratio = len(covered_source_ids) / total_sources if total_sources > 0 else 0.0

        clauses_output[clause] = {
            "source_ids": sorted(source_ids),
            "covered_source_ids": covered_source_ids,
            "uncovered_source_ids": uncovered_source_ids,
            "proc_ids": sorted(proc_ids_set),
            "covered": is_covered,
            "coverage_ratio": round(coverage_ratio, 2),
        }

    total_clauses = len(clauses_output)
    uncovered_count = total_clauses - covered_count

    # Step 5: 条款层级聚合 — 父条款的覆盖状态 = 自身 OR 任一子条款覆盖
    # 例如 4.9.7(3)b 已覆盖 → 4.9.7(3) 和 4.9.7 都视为覆盖
    # 这避免了"父条款 missing 但所有子条款都 covered"的误报
    # C-01: 旧实现是单遍循环且只认 '(' '[' 后缀——字母后缀（4.9.7(3)b → 4.9.7(3)）
    # 与 '.' 分隔（4.9.7 → 4.9）永不传播，直接父级恒漏报。改为按父级链
    # 迭代到不动点：4.9.7(3)b → 4.9.7(3) → 4.9.7 → 4.9 逐级向上传播。
    clause_keys = sorted(clauses_output.keys())
    changed = True
    while changed:
        changed = False
        for clause in clause_keys:
            if not clauses_output[clause]["covered"]:
                continue
            p = _parent_of(clause)
            if p in clauses_output and not clauses_output[p]["covered"]:
                clauses_output[p]["covered"] = True
                clauses_output[p]["covered_by_child"] = True
                covered_count += 1
                uncovered_count -= 1
                changed = True

    return {
        "summary": {
            "total_clauses": total_clauses,
            "covered_clauses": covered_count,
            "uncovered_clauses": uncovered_count,
        },
        "clauses": clauses_output,
    }


# ---------------------------------------------------------------------------
# V08 修复: transition_phase_metadata — 标注每个 transition 的 edge_type
# ---------------------------------------------------------------------------

def _build_transition_phase_metadata(coverage_model: dict) -> dict:
    """V08 修复: 构建 transition phase metadata。

    标注每个 transition 的 edge_type，让 validator 区分：
    - forward: 正向推进，phase 应递增（regression 是 bug）
    - side_effect/rollback/branch: 回退/循环/分支，phase regression 是正常的

    edge_type 判定规则（与 S0 _classify_edge_type 一致）：
    1. risk_traits 含 'rollback' → 'rollback'
    2. risk_traits 含 'branch' 且 action 含"联动"/"归档" → 'cascade_branch'
    3. action 含"选出"/"回退"/"退回"/"撤销" → 'rollback'
    4. action 含"联动"/"自动转换" → 'cascade'
    5. 其他 → 'forward'

    输出结构：
        {
            "summary": {total, forward, rollback, cascade, cascade_branch},
            "transitions": {
                "T-PROJ-003": {
                    "entity": "E-PROJ",
                    "from": "已选入", "to": "待选入",
                    "from_phase": 1, "to_phase": 0,
                    "edge_type": "rollback",
                    "phase_regresses": true,
                    "regression_expected": true,  // rollback 回退是正常的
                    "risk_traits": ["audit", "rollback"],
                    "action": "项目选出"
                }
            }
        }
    """
    tos = coverage_model.get("transition_obligations", [])
    transitions_output: dict[str, dict] = {}
    forward_count = 0
    non_forward_count = 0

    # 回退/撤销关键词
    rollback_keywords = {'退回', '驳回', '撤销', '退款', '选出', '回退', '取消'}
    # 联动/级联关键词
    cascade_keywords = {'联动', '自动转换', '级联', '系统触发'}

    for to in tos:
        tid = to.get("transition_id", "") or to.get("id", "")
        if not tid:
            continue
        entity = to.get("entity", "")
        from_state = to.get("from", "") or ""
        to_state = to.get("to", "") or ""
        action = to.get("action", "") or ""
        risk_traits = to.get("risk_traits", []) or to.get("traits", []) or []

        # edge_type 判定
        if "rollback" in risk_traits:
            edge_type = "rollback"
        elif any(kw in action for kw in rollback_keywords):
            edge_type = "rollback"
        elif "branch" in risk_traits and any(kw in action for kw in cascade_keywords):
            edge_type = "cascade_branch"
        elif any(kw in action for kw in cascade_keywords):
            edge_type = "cascade"
        else:
            edge_type = "forward"

        if edge_type == "forward":
            forward_count += 1
        else:
            non_forward_count += 1

        transitions_output[tid] = {
            "entity": entity,
            "from": from_state,
            "to": to_state,
            "edge_type": edge_type,
            "risk_traits": list(risk_traits),
            "action": action,
            # regression_expected: forward 不应 regress，其他可以
            "regression_expected": edge_type != "forward",
        }

    return {
        "summary": {
            "total_transitions": len(transitions_output),
            "forward": forward_count,
            "non_forward": non_forward_count,
        },
        "transitions": transitions_output,
    }


# ---------------------------------------------------------------------------
# V06 修复: time_sensitive_metadata — 超时用例的触发方式
# ---------------------------------------------------------------------------

def _build_time_sensitive_metadata(procedures: list[dict], coverage_model: dict) -> dict:
    """V06 修复: 构建 time_sensitive 用例的触发方式索引。

    validator 检查超时用例时要求有明确的执行路径（clock_injection /
    db_time_update / scheduler_manual_trigger）。本函数为每个 time_sensitive
    用例标注触发方式，让 validator 能确认执行路径。

    触发方式判定规则：
    1. source TO 的 risk_traits 含 'time_sensitive'
    2. action 含"超时自动转换"/"超时" → 触发方式 = 'scheduler_manual_trigger'
       （系统调度器在时限到达时自动触发）
    3. action 含"时限"/"时间边界" → 触发方式 = 'clock_injection'
       （测试时注入时钟到边界值）
    4. action 含"已过期" → 触发方式 = 'db_time_update'
       （直接更新数据库时间到过期后）

    输出结构：
        {
            "summary": {total, with_trigger, without_trigger},
            "procedures": {
                "PROC-033.1": {
                    "trigger_method": "scheduler_manual_trigger",
                    "timeout_type": "下发超时",
                    "source_to_id": "T-PLAN-004",
                    "allowed_methods": ["clock_injection", "db_time_update", "scheduler_manual_trigger"]
                }
            }
        }
    """
    tos = coverage_model.get("transition_obligations", [])
    to_by_id = {to.get("id", ""): to for to in tos}

    # V06: 触发方式动态推导（与 s1_generation._derive_time_mechanism 逻辑一致）
    # 触发方式标识符是 validator 协议约定的枚举值，不算业务硬编码
    def _determine_trigger_method(action: str, event: str) -> str:
        """根据 action/event 语义推导主触发方式。"""
        text = action + " " + event
        if any(kw in text for kw in ["边界", "接近"]):
            return "clock_injection"
        if any(kw in text for kw in ["过期", "已过期"]):
            return "db_time_update"
        return "scheduler_manual_trigger"

    def _determine_timeout_type(action: str, event: str, source_to: dict | None) -> str:
        """从 source TO 的 action/source_ref 动态提取超时类型。

        不硬编码"下发超时/启动超时"等业务关键词，而是：
        1. 优先从 source TO 的 action 中提取"XX超时"模式
        2. 若无，从 source_ref 中提取条目编号作为 timeout_type
        3. 兜底返回"超时"
        """
        import re as _re
        text = action + " " + event
        if source_to:
            to_action = source_to.get("action", "") or ""
            text += " " + to_action
        # 动态匹配"XX超时"模式（XX 为 2-4 个中文字符）
        m = _re.search(r'([\u4e00-\u9fa5]{2,4})超时', text)
        if m:
            return m.group(0)  # 如"下发超时"、"启动超时"
        if "超时" in text:
            return "超时"
        return ""

    allowed_methods = ["clock_injection", "db_time_update", "scheduler_manual_trigger"]
    procs_output: dict[str, dict] = {}
    with_trigger = 0

    for proc in procedures:
        source_ids = proc.get("source_ids", [])
        # 检查 source TO 是否含 time_sensitive trait
        is_time_sensitive = False
        source_to_id = ""
        for sid in source_ids:
            to = to_by_id.get(sid)
            if to:
                traits = to.get("risk_traits", []) or to.get("traits", []) or []
                if "time_sensitive" in traits:
                    is_time_sensitive = True
                    source_to_id = sid
                    break

        if not is_time_sensitive:
            # 也检查 when.event/when.action 含"超时"
            event = proc.get("when", {}).get("event", "") or ""
            action = proc.get("when", {}).get("action", "") or ""
            if "超时" in event + action:
                is_time_sensitive = True
                source_to_id = source_ids[0] if source_ids else ""

        if not is_time_sensitive:
            continue

        event = proc.get("when", {}).get("event", "") or ""
        action = proc.get("when", {}).get("action", "") or ""
        # 获取 source TO 用于动态推导 timeout_type
        source_to = to_by_id.get(source_to_id)
        trigger_method = _determine_trigger_method(action, event)
        timeout_type = _determine_timeout_type(action, event, source_to)

        procs_output[proc["temp_id"]] = {
            "trigger_method": trigger_method,
            "timeout_type": timeout_type,
            "source_to_id": source_to_id,
            "allowed_methods": allowed_methods,
        }
        with_trigger += 1

    return {
        "summary": {
            "total": len(procs_output),
            "with_trigger": with_trigger,
            "without_trigger": 0,  # 所有 time_sensitive 都有触发方式
        },
        "procedures": procs_output,
    }




if __name__ == "__main__":
    # 位置参数 + 可选开关 --hide-markers（渲染层隐藏机器 id 标记：
    # 覆盖需求省略义务 id、Then 省略 BR id / cross 标注）。JSON 数据不变。
    if len(sys.argv) < 2:
        print("Usage: python main.py <coverage_model_path> [output_path] [--hide-markers]")
        sys.exit(1)
    hide_markers = "--hide-markers" in sys.argv[1:]
    args = [a for a in sys.argv[1:] if a != "--hide-markers"]
    cm_path = args[0]
    out_path = args[1] if len(args) > 1 else str(Path(cm_path).parent / "p3_agent_output.json")
    run_p3_pipeline(cm_path, out_path, hide_markers=hide_markers)