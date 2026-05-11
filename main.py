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
    print("      [OK] Graph compiled: S0 -> S1 -> S2 -> S3 -> S4 -> Done")
    
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

    # Print engine state
    print(f"\n────────────────────────── Engine State ──────────────────────────")
    print(f"  primary_entity       : {result.get('primary_entity')}")
    print(f"  dependent_entities   : {result.get('dependent_entities')}")
    print(f"  entity_parent        :")
    for child, parent in (result.get("entity_parent") or {}).items():
        print(f"    {child} -> {parent}")
    print(f"  topology_levels      :")
    topo = result.get("topology_levels") or {}
    for entity, level in sorted(topo.items(), key=lambda x: (x[1], x[0])):
        depth = (result.get("dependency_depth") or {}).get(entity, "-")
        print(f"    L{level}  {entity}  (depth={depth})")
    print(f"  virtual_entities ({len(result.get('virtual_entities') or {})}):")
    for ve_name, ve in (result.get("virtual_entities") or {}).items():
        orig = ve.get("original_entity", "")
        parent = ve.get("parent_entity", "")
        context = ve.get("context", "")
        phase = ve.get("resolved_phase", "-")
        print(f"    {ve_name}  orig={orig}  parent={parent}  phase={phase}  context={context[:40]}...")
    print(f"  transition_upstream  : {len(result.get('transition_upstream_map') or {})} entries")
    phase_table = result.get("phase_table") or {}
    print(f"  phase_table          : {phase_table.get('phase_count', 0)} phases, primary_dim={phase_table.get('primary_dimension', '-')}")
    print(f"  dep_state_phase_map  : {(result.get('dep_state_phase_map') or {}) and 'present' or 'none'}")
    print(f"  state_type_map       : {(result.get('state_type_map') or {}) and 'present' or 'none'}")
    print(f"──────────────────────────────────────────────────────────────────")

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
    
    print(f"      [OK] Saved {len(json.dumps(output, ensure_ascii=False))} bytes")
    
    # Also generate markdown test procedures
    md_path = output_path.replace(".json", ".md")
    _generate_markdown(procedures, md_path)
    print(f"      [OK] Markdown saved to: {md_path}")
    
    if errors:
        print(f"\n[WARN] {len(errors)} errors encountered:")
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
    """Generate V2-aligned markdown — grouped by base ID with instance count badge."""
    lines = ["# 测试规程\n"]

    for proc in procedures:
        s2 = proc.get("_S2_fields") or {}
        s3 = proc.get("_S3_fields") or {}
        s4 = proc.get("_S4_fields") or {}

        temp_id = proc.get("temp_id", "?")
        post_state = proc.get("post_state", "")
        mc = s4.get("multi_count", 1)

        # Title with instance badge
        if mc > 1:
            lines.append(f"### {temp_id} (×{mc})：{post_state}")
        else:
            lines.append(f"### {temp_id}：{post_state}")

        phase_name = s2.get("phase_name", "")
        type_label = s2.get("type_label", "")
        source_ids = _safe_join(proc.get("source_ids"))
        lines.append(f"**业务定位**：{phase_name} ｜ {type_label} ｜ 溯源: `{source_ids}`")

        if s2.get("phase_basis"):
            lines.append(f"**阶段依据**：{s2.get('phase_basis')}")
        if s2.get("context"):
            lines.append(f"**场景**：{s2.get('context')}")

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

        if proc.get("post_state"):
            lines.append(f"\n**后置状态**：{proc.get('post_state')}")

        cascade = proc.get("cascade_chain")
        if cascade:
            lines.append(f"**级联链**：{cascade}")

        deps = s3.get("dependencies")
        if deps:
            lines.append(f"**依赖**：{_safe_join(deps)}")
        weak_deps = s3.get("weak_dependencies")
        if weak_deps:
            lines.append(f"**弱依赖**：{_safe_join(weak_deps)}")

        # Multi instance (V2 format: metadata only)
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
