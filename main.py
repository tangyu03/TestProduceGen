#!/usr/bin/env python3
"""P3 Agent Engine — Main Entry Point.

Usage:
    python main.py <coverage_model_path> [output_path]
"""
import json
import re
import sys
import time
from pathlib import Path

from graph import compile_p3_graph
from models.state import AgentState


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
    print("      ✓ Graph compiled: S0 → S1 → S2 → S3 → S4 → Done")
    
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
            print(f"      ✓ {label} ({n_procs} procedures, {n_warn} warnings, {n_err} errors)")
    
    elapsed = time.time() - start_time
    print(f"      ✓ Pipeline completed in {elapsed:.2f}s")
    
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
        4: "Type4(Cross-Entity)",  # Type4a和Type4b都是4
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
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"      ✓ Saved {len(json.dumps(output, ensure_ascii=False))} bytes")
    
    # Also generate markdown test procedures
    md_path = output_path.replace(".json", ".md")
    _generate_markdown(procedures, md_path)
    print(f"      ✓ Markdown saved to: {md_path}")
    
    if errors:
        print(f"\n⚠ {len(errors)} errors encountered:")
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
        lines.append(f"### {temp_id}：{post_state}")

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

        # Steps table
        steps = proc.get("steps")
        if steps:
            lines.append("\n| # | AAA | 位置 | 输入 | 预期 |")
            lines.append("|---|-----|------|------|------|")
            for i, step in enumerate(steps, 1):
                aaa = step.get("aaa", "")
                loc = step.get("location", "")
                inp = step.get("input", "")
                exp = step.get("expected", "")
                lines.append(f"| {i} | {aaa} | {loc} | {inp} | {exp} |")

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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <coverage_model_path> [output_path]")
        sys.exit(1)
    cm_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else str(Path(cm_path).parent / "p3_agent_output.json")
    run_p3_pipeline(cm_path, out_path)
