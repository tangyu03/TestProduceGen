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
from tools.llm_client import TitleGenerator
from tools.llm.http_utils import call_llm_api, parse_llm_response

# v29 Engineering Optimization Gap 1: Fallback Observability
# The fallback collector is initialized in build_obligations.py (P2) and
# accumulated through S0/S1/S3. At main.py finalize time we read the
# accumulated report and write it to the output JSON for audit / dashboards.
import tools.fallback_log as _fl


def run_p3_pipeline(
    coverage_model_path: str,
    output_path: str,
) -> dict:
    """Run the complete P3 agent pipeline.
    
    Args:
        coverage_model_path: Path to P2 coverage_model.json
        output_path: Path to write the output JSON
    
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
        "virtual_entities": None,
        "transition_upstream_map": None,
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
    type_labels = {
        1: "Type1(Transition)", 3: "Type3(Attribute)", 
        4: "Type4a(Constraint)", 5: "Type4b(Lifecycle)",
        6: "Type5(CRUD)", 7: "Type6(Invalid)", 8: "Type7(BR)"
    }
    for proc in procedures:
        ot = proc.get("obligation_type", 0)
        label = type_labels.get(ot, f"Type{ot}")
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
            "virtual_entities": result.get("virtual_entities"),
            "transition_upstream_map": result.get("transition_upstream_map"),
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
    print(f"        transition_upstream_map: {json.dumps(es['transition_upstream_map'], ensure_ascii=False)}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # BUGFIX #17: avoid re-serialising the entire output dict just to count
    # bytes — use the file size directly.
    import os
    print(f"      [OK] Saved {os.path.getsize(output_path)} bytes")
    
    # Also generate markdown test procedures
    md_path = output_path.replace(".json", ".md")
    _generate_markdown(procedures, md_path)
    print(f"      [OK] Markdown saved to: {md_path}")

    # Generate readable (card-style) test case document
    readable_md_path = output_path.replace(".json", "_readable.md")
    _generate_readable_markdown(procedures, coverage_model, readable_md_path)
    print(f"      [OK] Readable markdown saved to: {readable_md_path}")

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

    Data-driven: the S1 layer marks Thens with ``dedup_group`` (see
    _make_then) so the renderer does NOT match data-layer text conventions:
      - "transition_target" (状态转换为X) is implied by "transition_flow"
        (状态流转：from→to), so it is omitted when a flow is present.
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
        norm = "".join(exp.split())
        if norm in seen:
            continue
        seen.add(norm)
        out.append(t)
    return out


def _generate_markdown(procedures: list[dict], md_path: str):
    """Generate human-readable markdown from procedures.

    Collapses multi-instance copies (PROC-001.1, PROC-001.2, ...) into
    a single entry per base procedure with an instance-count badge.
    """
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
        instance_count = len(procs)
        has_multi = instance_count > 1

        s2 = proc.get("_S2_fields") or {}
        s3 = proc.get("_S3_fields") or {}
        s4 = proc.get("_S4_fields") or {}

        temp_id = base
        if has_multi:
            temp_id = f"{base} (×{instance_count})"
        post_state = proc.get("post_state", "")
        # Title line — prefer LLM-generated natural-language title
        title = proc.get("title") or post_state
        lines.append(f"### {temp_id}：{title}")

        phase_name = s2.get("phase_name", "")
        type_label = s2.get("type_label", "")
        source_ids = _safe_join(proc.get("source_ids"))
        lines.append(f"**业务定位**：{phase_name} ｜ {type_label} ｜ 溯源: `{source_ids}`")

        if s2.get("phase_basis") and not s2.get("phase_basis_debug"):
            lines.append(f"**阶段依据**：{s2.get('phase_basis')}")
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
            lines.append("")
            # Given clauses
            if givens:
                lines.append("**Given**")
                for g in givens:
                    desc = g.get("description", "")
                    desc_str = f" ({desc})" if desc else ""
                    lines.append(f"- {g.get('target', '')} 状态 = {g.get('state', '')}{desc_str}")

            # When clause (single)
            if when:
                lines.append("")
                lines.append("**When**")
                w = when
                actor_str = f" by {w.get('actor')}" if w.get("actor") else ""
                action_str = f" [{w.get('action')}]" if w.get("action") else ""
                lines.append(f"- {w.get('target', '')} {w.get('event', '')}{actor_str}{action_str}")

            # Then clauses (rendering-layer dedup — JSON data untouched)
            if thens:
                lines.append("")
                lines.append("**Then**")
                for t in _dedup_thens(thens):
                    br_str = f" [BR: {','.join(t.get('br_refs', []))}]" if t.get("br_refs") else ""
                    xref_str = f" [cross: {','.join(t.get('cross_refs', []))}]" if t.get("cross_refs") else ""
                    lines.append(f"- {t.get('target', '')} {t.get('expectation', '')} ({t.get('kind', 'state')}){br_str}{xref_str}")

            # Operation hints (separate from spec)
            if op_hints:
                lines.append("")
                lines.append("**操作提示**")
                for i, hint in enumerate(op_hints, 1):
                    lines.append(f"{i}. {hint}")

        # Post state
        if proc.get("post_state"):
            lines.append(f"\n**后置状态**：{proc.get('post_state')}")

        # Cascade chain
        cascade = proc.get("cascade_chain")
        if cascade:
            lines.append(f"**级联链**：{cascade}")

        # Dependencies
        deps = s3.get("dependencies")
        if deps:
            lines.append(f"**依赖**：{_safe_join(deps)}")
        weak_deps = s3.get("weak_dependencies")
        if weak_deps:
            lines.append(f"**弱依赖**：{_safe_join(weak_deps)}")

        # Multi instance
        if s4.get("multi_instance"):
            mc = s4.get("multi_count", "?")
            mr = s4.get("multi_reason", "")
            lines.append(
                f"**多实例**：{mc} 个实例（{mr}），每个实例需使用独立测试数据")

        lines.append("")

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# Readable (card-style) test case markdown
# ---------------------------------------------------------------------------

def _build_source_lookup(coverage_model: dict) -> dict[str, str]:
    """Build a {source_id: requirement_text} map from the coverage model.

    Traverses all four obligation lists and extracts human-readable
    requirement descriptions keyed by obligation ID.
    """
    lookup: dict[str, str] = {}

    # transition_obligations: action + preconditions
    for to in coverage_model.get("transition_obligations", []):
        tid = to.get("id", "")
        if not tid:
            continue
        parts = []
        action = to.get("action", "")
        if action:
            parts.append(action)
        preconds = to.get("preconditions", [])
        if preconds:
            parts.append("前置: " + "; ".join(str(p) for p in preconds))
        results = to.get("expected_results", [])
        if results:
            parts.append("预期: " + "; ".join(str(r) for r in results))
        lookup[tid] = "；".join(parts) if parts else tid

    # entity_obligations: description
    for eo in coverage_model.get("entity_obligations", []):
        eid = eo.get("id", "")
        desc = eo.get("description", "")
        if eid and desc:
            lookup[eid] = desc

    # cross_entity_obligations: desc > suggested_action
    for co in coverage_model.get("cross_entity_obligations", []):
        cid = co.get("id", "")
        text = co.get("desc") or co.get("suggested_action", "")
        if cid and text:
            lookup[cid] = text

    # constraint_obligations: description > reason
    ros_raw = coverage_model.get("constraint_obligations", [])
    if isinstance(ros_raw, dict):
        ros_flat = [item for sublist in ros_raw.values() for item in sublist]
    elif isinstance(ros_raw, list):
        ros_flat = ros_raw
    else:
        ros_flat = []
    for ro in ros_flat:
        rid = ro.get("id", "")
        text = ro.get("description") or ro.get("reason", "")
        if rid and text:
            lookup[rid] = text

    return lookup


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
    clause_keys = sorted(clauses_output.keys())
    for clause in clause_keys:
        if clauses_output[clause]["covered"]:
            continue
        # 检查是否有已覆盖的子条款（clause 后缀匹配）
        prefix = clause
        has_covered_child = False
        for other in clause_keys:
            if other != clause and other.startswith(prefix):
                # 确保是子条款（如 4.9.7 的子条款 4.9.7(3)b）
                rest = other[len(prefix):]
                if rest and rest[0] in '([':
                    if clauses_output[other]["covered"]:
                        has_covered_child = True
                        break
        if has_covered_child:
            clauses_output[clause]["covered"] = True
            clauses_output[clause]["covered_by_child"] = True
            # 重新计算 covered_count
            covered_count += 1
            uncovered_count -= 1

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
    to_by_tid = {to.get("transition_id", ""): to for to in tos if to.get("transition_id")}

    # V06: 触发方式动态推导（与 s1_generation._build_timeout_hints 逻辑一致）
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
            to = to_by_id.get(sid) or to_by_tid.get(sid)
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
        source_to = to_by_id.get(source_to_id) or to_by_tid.get(source_to_id)
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


# ---------------------------------------------------------------------------
# V-step expected-text polish (batched LLM call → natural language)
# ---------------------------------------------------------------------------

# Shared API config for polish calls (loaded once)
_polish_api_config: tuple[str, str, str] | None = None


def _get_polish_api_config() -> tuple[str, str, str]:
    """Load API config for polish LLM calls (cached)."""
    global _polish_api_config
    if _polish_api_config is not None:
        return _polish_api_config
    import os as _os
    api_base = _os.environ.get("LLM_API_BASE",
                               "https://open.bigmodel.cn/api/paas/v4").rstrip("/")
    api_key = _os.environ.get("LLM_API_KEY", "")
    model = _os.environ.get("LLM_POLISH_MODEL", "glm-4-flash")
    if not api_key:
        cfg_path = Path(__file__).parent / "config.json"
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            llm_cfg = cfg.get("llm", {})
            api_base = llm_cfg.get("api_base", api_base).rstrip("/")
            api_key = llm_cfg.get("api_key", api_key)
            task_models = llm_cfg.get("task_models", {})
            model = task_models.get("polish", llm_cfg.get("polish_model", model))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    _polish_api_config = (api_base, api_key, model)
    return _polish_api_config


_POLISH_SYSTEM_PROMPT = """你是一个测试用例语言润色器。请将"预期结果"中的文本改写为流畅的自然语言，保持所有关键信息不变。

## 改写规则
1. 去掉"状态验证:"、"验证:"、"预期结果:"等生硬前缀
2. 将"状态变更为XXX"改写为"页面显示状态已更新为XXX"或"状态成功切换为XXX"
3. 将"操作被拒绝"改写为"系统拒绝该操作"或"操作无法执行"
4. 保留所有具体数值、状态名、提示文案原文
5. 每条的改写结果长度应与原文接近，不要无意义扩写
6. 如果原文已经是流畅自然语言，保持不变

## 示例
原文: 状态验证: 待开始
改写: 项目状态成功变更为"待开始"

原文: 验证: 删除项目
改写: 项目已被删除，列表中不再显示该项目

原文: 操作被拒绝，提示'待开始状态的项目不可删除'，项目状态不变
改写: 系统拒绝删除操作，弹出提示"待开始状态的项目不可删除"，项目仍保持当前状态

原文: [BR-02]验证: 待开始状态不可删除项目
改写: [BR-02] 系统阻止删除操作，待开始状态的项目不允许被删除

## 输出格式
每行一个 JSON 对象（JSONL）：
{"original": "原文", "polished": "改写后的自然语言"}

只输出 JSONL，不要额外文字。"""


def _polish_expected_text(procedures: list[dict]) -> dict[str, str]:
    """Polish V-step expected texts: regex (fast) + LLM (hard cases).

    Stage 1 — regex cleanup covers deterministic template patterns (~80%):
      "状态验证: 待开始" → "状态成功变更为'待开始'"
      "验证: 删除项目" → "项目已被删除"
      "操作被拒绝,提示'xxx'" → "系统拒绝操作，提示'xxx'"

    Stage 2 — remaining texts with "验证"/"状态" prefixes go to LLM.

    Returns ``{original → polished}`` map.
    """
    # Collect unique expected texts from BDD Then clauses
    texts_set: dict[str, None] = {}
    for proc in procedures:
        for then in proc.get("thens", []):
            exp = then.get("expectation", "").strip()
            if exp and len(exp) >= 4:
                texts_set[exp] = None

    if not texts_set:
        return {}

    unique_texts = list(texts_set.keys())
    result: dict[str, str] = {}

    # ── Stage 1: regex-based cleanup ─────────────────────────────────
    still_needs_polish: list[str] = []

    for text in unique_texts:
        polished = _regex_polish(text)
        if polished != text:
            result[text] = polished
        elif re.search(r'(状态验证|验证[:：]|预期结果)', text):
            still_needs_polish.append(text)
        # else: already natural — no change needed

    print(f"      [POLISH] Stage 1 (regex): {len(result)} polished, "
          f"{len(still_needs_polish)} need LLM")

    if not still_needs_polish:
        return result

    # ── Stage 2: LLM for remaining hard cases ────────────────────────
    api_base, api_key, model = _get_polish_api_config()
    if not api_key:
        print("      [POLISH] LLM_API_KEY not set — skipping Stage 2")
        return result

    # Check cache for the hard cases
    cache_path = _polish_cache_path(still_needs_polish)
    cached = _polish_load_cache(cache_path)
    if cached is not None:
        result.update(cached)
        return result

    batch_size = 30
    all_entries: list[dict] = []

    for batch_idx in range(0, len(still_needs_polish), batch_size):
        batch = still_needs_polish[batch_idx:batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1
        total_batches = (len(still_needs_polish) + batch_size - 1) // batch_size

        user_lines = ["请将以下预期结果改写为自然语言：", ""]
        for i, text in enumerate(batch):
            user_lines.append(f"### {batch_idx + i + 1}.")
            user_lines.append(f"原文: {text}")
            user_lines.append("")
        user_msg = "\n".join(user_lines)

        try:
            raw = call_llm_api(
                api_base=api_base, api_key=api_key, model=model,
                messages=[
                    {"role": "system", "content": _POLISH_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
                max_tokens=len(batch) * 120 + 200,
                timeout=120,
                max_retries=2,
            )
            entries = parse_llm_response(raw, prefer_jsonl=True)
            if isinstance(entries, dict):
                entries = [entries]
            all_entries.extend(entries or [])
            print(f"      [POLISH] Stage 2 Batch {batch_num}/{total_batches}: "
                  f"{len(entries or [])} entries")
        except Exception as e:
            print(f"      [POLISH] Stage 2 Batch {batch_num}/{total_batches} failed: {e}")

        if total_batches > 1 and batch_num < total_batches:
            time.sleep(1)

    for entry in all_entries:
        orig = entry.get("original", "")
        pol = entry.get("polished", "")
        if orig and pol and pol != orig:
            result[orig] = pol

    _polish_save_cache(cache_path, {k: v for k, v in result.items() if k in still_needs_polish})
    print(f"      [POLISH] Stage 2 (LLM): {len(all_entries)} texts polished")
    return result


def _regex_polish(text: str) -> str:
    """Fast regex-based cleanup for deterministic template patterns."""
    t = text.strip()

    # "状态验证: XXX" → "状态成功变更为'XXX'" or "状态保持为'XXX'"
    # Skip if the "state" contains entity references (e.g. "项目.项目状态 = 待开始")
    m = re.match(r'状态验证[:：]\s*(.+)', t)
    if m:
        state = m.group(1).strip()
        # Don't polish cross-entity state references
        if '=' not in state and '.' not in state and '项目' not in state:
            if '不变' in state:
                return f"状态保持不变，仍为'{state.replace('不变', '').strip()}'"
            return f"状态成功变更为'{state}'"
        # Cross-entity: keep as-is or make slightly more readable
        return t

    # "验证: XXX" → make it declarative
    m = re.match(r'验证[:：]\s*(.+)', t)
    if m:
        content = m.group(1).strip()
        # If it describes an action result
        if '删除' in content:
            return f"{content}，操作已生效"
        if '审核' in content:
            return f"{content}，审核流程已完成"
        return content

    # "操作被拒绝，提示'XXX'" → "系统拒绝操作，提示'XXX'"
    t = re.sub(r'操作被拒绝[,，]', '系统拒绝该操作，', t)

    # "预期结果: XXX" → "XXX"
    t = re.sub(r'^预期结果[:：]\s*', '', t)

    # "[BR-XX]验证: XXX" → "[BR-XX] XXX"
    t = re.sub(r'(\[BR-\d+\S*\])验证[:：]\s*', r'\1', t)

    # "校验失败，提示'XXX'" → "校验不通过，输入框提示'XXX'"
    t = re.sub(r"校验失败[,，]提示['‘]", "校验不通过，输入框下方提示'", t)

    # "校验通过" → standalone polish
    t = re.sub(r'^校验通过$', '输入通过所有校验规则，提交按钮可用', t)

    return t


# ── Polish cache helpers ──

def _polish_cache_path(texts: list[str]) -> Path:
    import hashlib
    stable = json.dumps(sorted(texts), ensure_ascii=True, sort_keys=True)
    h = hashlib.sha256(stable.encode()).hexdigest()[:16]
    return Path(__file__).parent / "cache" / f"pol_{h}.json"


def _polish_load_cache(cache_path: Path) -> dict[str, str] | None:
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _polish_save_cache(cache_path: Path, result: dict[str, str]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Readable (card-style) test case markdown
# ---------------------------------------------------------------------------


def _generate_readable_markdown(
    procedures: list[dict],
    coverage_model: dict,
    md_path: str,
) -> None:
    """Generate card-style readable test case markdown.

    Each procedure becomes a card with:
    1. 测试用例名称 + 元信息（阶段/类型/需求来源）
    2. 对应需求内容
    3. 前置条件
    4. 测试步骤（含操作数据+操作位置）
    5. 预期结果
    6. 后置状态
    7. 依赖 + 级联链（有则显示）
    """
    lookup = _build_source_lookup(coverage_model)

    # ── Polish V-step expected texts (batched LLM → natural language) ──
    polish_map = _polish_expected_text(procedures)

    # ── Build translation helpers ──────────────────────────────────────
    # Entity ID → Chinese name
    ctx = coverage_model.get("_context", {})
    id_to_name: dict[str, str] = {}
    entity_list = ctx.get("entity_details", [])
    if isinstance(entity_list, dict):
        entity_list = list(entity_list.values())
    for e in entity_list:
        eid = e.get("id", "")
        ename = e.get("name", "")
        if eid and ename:
            id_to_name[eid] = ename

    def _translate_entity(text: str) -> str:
        """Replace entity codes like E-PROJ with Chinese names."""
        for code, chinese in id_to_name.items():
            text = text.replace(code, chinese)
        return text

    # Phase names: try entity state info → readable phase label
    state_info = ctx.get("state_info", {})
    phase_names = ctx.get("phase_names", ["P0", "P1", "P2"])
    if isinstance(phase_names, dict):
        phase_names = list(phase_names.values())

    # Type label → Chinese
    type_label_cn = {
        "happy": "正向流程", "branch": "分支路径", "audit": "审批流程",
        "audit_rejection": "审批驳回", "time_sensitive": "时效约束",
        "data_constraint": "数据约束", "rollback": "回退验证",
        "constraint": "前置门禁", "lifecycle": "生命周期",
        "crud": "数据操作", "invalid": "非法验证", "rule": "业务规则",
    }

    # Procedure temp_id → title (for translating dependency references)
    proc_title_map: dict[str, str] = {}
    for p in procedures:
        tid = p.get("temp_id", "")
        # Store both full ID (PROC-001.1) and base ID (PROC-001)
        base = re.sub(r"\.\d+$", "", tid)
        t = p.get("title") or p.get("post_state", "")
        proc_title_map[tid] = t
        if base not in proc_title_map:
            proc_title_map[base] = t

    lines = ["# 测试用例（可读版）\n"]

    # Group multi-instance copies by base ID
    groups: dict[str, list[dict]] = {}
    group_order: list[str] = []
    for proc in procedures:
        tid = proc.get("temp_id", "?")
        base = re.sub(r"\.\d+$", "", tid)
        if base not in groups:
            groups[base] = []
            group_order.append(base)
        groups[base].append(proc)

    tc_counter = 0

    for base in group_order:
        procs = groups[base]
        proc = procs[0]
        instance_count = len(procs)
        tc_counter += 1
        s2 = proc.get("_S2_fields", {})
        s3 = proc.get("_S3_fields", {})

        # ── Title ──
        title = proc.get("title") or proc.get("post_state", "")
        multi_badge = f" ×{instance_count}" if instance_count > 1 else ""
        lines.append(f"---\n")
        lines.append(f"### TC-{tc_counter:03d}：{title}\n")

        # ── Meta line: 阶段 | 类型 | 需求来源 ──
        phase_name = s2.get("phase_name", "")
        type_label = s2.get("type_label", "")
        type_cn = type_label_cn.get(type_label, type_label)
        source_ids = proc.get("source_ids", [])

        # Build readable requirement source from source_ids
        req_refs: list[str] = []
        for sid in source_ids:
            req_text = lookup.get(sid, sid)
            # Truncate long requirement text for the meta line
            if len(req_text) > 60:
                req_text = req_text[:57] + "..."
            req_refs.append(req_text)
        req_ref_str = "；".join(req_refs) if req_refs else "—"

        lines.append(f"> **{phase_name}** | {type_cn} | 需求: {req_ref_str}\n")

        # 多实例提示：所有实例 Given/When/Then 相同，需分别使用独立测试数据
        if instance_count > 1:
            lines.append(
                f"> ⚠ **{instance_count} 个实例**：内容一致，每个实例需使用独立测试数据\n")

        # ── 1. 对应需求内容 ──
        req_texts: list[str] = []
        for sid in source_ids:
            req = lookup.get(sid, "")
            if req and req not in req_texts:
                req_texts.append(req)
        requirement = "；".join(req_texts) if req_texts else "（未找到对应需求）"
        lines.append(f"| 字段 | 内容 |")
        lines.append(f"|---|---|")
        lines.append(f"| **对应需求内容** | {requirement} |")

        # ── 2. BDD Given（前置业务状态）──
        givens = proc.get("givens", [])
        if givens:
            precond_parts: list[str] = []
            for i, g in enumerate(givens, 1):
                target = _translate_entity(g.get("target", ""))
                state = g.get("state", "")
                desc = g.get("description", "")
                desc_str = f"（{desc}）" if desc else ""
                precond_parts.append(f"{i}. {target} = {state}{desc_str}")
            lines.append(f"| **Given（前置状态）** | {'<br>'.join(precond_parts)} |")
        else:
            lines.append(f"| **Given（前置状态）** | （无特殊前置状态） |")

        # ── 3. BDD When（业务事件）──
        when = proc.get("when", {})
        if when and when.get("event"):
            w_target = _translate_entity(when.get("target", ""))
            w_event = when.get("event", "")
            w_actor = when.get("actor", "")
            w_action = when.get("action", "")
            actor_str = f" by {w_actor}" if w_actor and w_actor != "系统" else ""
            action_str = f" [{w_action}]" if w_action and w_action != w_event else ""
            lines.append(f"| **When（业务事件）** | {w_target} {w_event}{actor_str}{action_str} |")
        else:
            lines.append(f"| **When（业务事件）** | （未指定业务事件） |")

        # ── 4. BDD Then（可观察结果）──
        # 渲染层去重（_dedup_thens 只影响呈现，JSON 数据不动）
        thens = _dedup_thens(proc.get("thens", []))
        if thens:
            expectations: list[str] = []
            for i, t in enumerate(thens, 1):
                t_target = _translate_entity(t.get("target", ""))
                exp_raw = t.get("expectation", "")
                exp = _translate_entity(polish_map.get(exp_raw, exp_raw))
                kind = t.get("kind", "state")
                br_refs = t.get("br_refs", [])
                cross_refs = t.get("cross_refs", [])
                # Simplify target: strip entity prefix if redundant
                entity = proc.get("entity", "")
                entity_cn = id_to_name.get(entity, entity)
                if t_target.startswith(entity_cn + "."):
                    loc_short = t_target[len(entity_cn) + 1:]
                elif t_target.startswith(entity + "."):
                    loc_short = t_target[len(entity) + 1:]
                else:
                    loc_short = t_target
                loc_tag = f"[{loc_short}] " if loc_short and loc_short not in (entity_cn, entity) else ""
                br_tag = f" [BR:{','.join(br_refs)}]" if br_refs else ""
                xref_tag = f" [cross:{','.join(cross_refs)}]" if cross_refs else ""
                kind_tag = f"({kind})" if kind != "state" else ""
                expectations.append(f"{i}. {loc_tag}{exp}{kind_tag}{br_tag}{xref_tag}")
            lines.append(f"| **Then（预期结果）** | {'<br>'.join(expectations)} |")
        else:
            lines.append(f"| **Then（预期结果）** | （无可观察结果） |")

        # ── 4b. Operation Hints（执行提示，与规范分离）──
        op_hints = proc.get("operation_hints", [])
        if op_hints:
            hints_str = "<br>".join(f"{i}. {h}" for i, h in enumerate(op_hints, 1))
            lines.append(f"| **操作提示** | {hints_str} |")

        # ── 5. 后置状态 ──
        post_state = proc.get("post_state", "")
        if post_state:
            post_state_cn = _translate_entity(post_state)
            # Make it more readable: "项目.项目状态→待开始" → "项目状态变更为待开始"
            if "→" in post_state_cn:
                parts = post_state_cn.split("→", 1)
                post_state_readable = f"执行后，{parts[0].strip()}变更为{parts[1].strip()}"
            else:
                post_state_readable = post_state_cn
            lines.append(f"| **后置状态** | {post_state_readable} |")

        # ── 6. 依赖 + 级联链 ──
        extras: list[str] = []

        deps = s3.get("dependencies", [])
        if deps:
            dep_titles = []
            for d in deps:
                dt = proc_title_map.get(d, d)
                # Truncate if too long
                if len(dt) > 40:
                    dt = dt[:37] + "..."
                dep_titles.append(dt)
            extras.append(f"前置用例: {' → '.join(dep_titles)}")

        cascade = proc.get("cascade_chain", "")
        if cascade:
            cascade_cn = _translate_entity(cascade)
            # "项目.项目状态=待开始→报名.报名状态=待审核"
            # → "项目进入待开始 → 报名状态自动变为待审核"
            cascade_readable = cascade_cn.replace("=", "设为").replace("→", " → ")
            extras.append(f"级联效果: {cascade_readable}")

        if extras:
            lines.append(f"| **关联** | {'<br>'.join(extras)} |")

        lines.append("")

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <coverage_model_path> [output_path]")
        sys.exit(1)
    cm_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else str(Path(cm_path).parent / "p3_agent_output.json")
    run_p3_pipeline(cm_path, out_path)