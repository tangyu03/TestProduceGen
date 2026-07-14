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
        }
    }
    
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
                if title:
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

        if s2.get("phase_basis"):
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

            # Then clauses
            if thens:
                lines.append("")
                lines.append("**Then**")
                for t in thens:
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
            lines.append(f"**多实例**：{mc} × {mr}")

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
    for ro in coverage_model.get("constraint_obligations", []):
        rid = ro.get("id", "")
        text = ro.get("description") or ro.get("reason", "")
        if rid and text:
            lookup[rid] = text

    return lookup


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
        thens = proc.get("thens", [])
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