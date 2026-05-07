#!/usr/bin/env python3
"""P3 Agent Engine — Main Entry Point.

Usage:
    python main.py [coverage_model_path] [output_path]

Defaults:
    coverage_model_path = /home/z/my-project/download/coverage_model.json
    output_path         = /home/z/my-project/download/p3_agent_output.json
"""
import json
import sys
import time
from pathlib import Path

from p3_agent_engine.graph import compile_p3_graph
from p3_agent_engine.models.state import AgentState


def run_p3_pipeline(
    coverage_model_path: str = "/home/z/my-project/download/coverage_model.json",
    output_path: str = "/home/z/my-project/download/p3_agent_output.json",
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
    print("\n[1/4] Compiling LangGraph pipeline...")
    app = compile_p3_graph()
    print("      ✓ Graph compiled: S0 → S1 → S2 → S3 → Done")
    
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
    
    # Run the pipeline
    print("\n[2/4] Running pipeline...")
    start_time = time.time()
    
    result = app.invoke(initial_state)
    
    elapsed = time.time() - start_time
    print(f"      ✓ Pipeline completed in {elapsed:.2f}s")
    
    # Process results
    procedures = result.get("procedures", [])
    warnings = result.get("warnings", [])
    errors = result.get("errors", [])
    current_stage = result.get("current_stage", "unknown")
    
    print(f"\n[3/4] Results Summary:")
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
    
    # Save output
    print(f"\n[4/4] Saving output to: {output_path}")
    
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


def _generate_markdown(procedures: list[dict], md_path: str):
    """Generate human-readable markdown from procedures."""
    lines = ["# 测试规程\n"]
    
    for proc in procedures:
        s2 = proc.get("_S2_fields", {})
        s3 = proc.get("_S3_fields", {})
        s4 = proc.get("_S4_fields", {})
        
        lines.append(f"### {proc['temp_id']}：{proc.get('post_state', '')}")
        lines.append(f"**业务定位**：{s2.get('phase_name', '')} ｜ "
                     f"{s2.get('type_label', '')} ｜ "
                     f"溯源: `{', '.join(proc.get('source_ids', []))}`")
        
        if s2.get("phase_basis"):
            lines.append(f"**阶段依据**：{s2['phase_basis']}")
        if s2.get("context"):
            lines.append(f"**场景**：{s2['context']}")
        if proc.get("br_embedded"):
            lines.append(f"**BR嵌入**：{', '.join(proc['br_embedded'])}")
        
        # Steps table
        lines.append("\n| # | AAA | 位置 | 输入 | 预期 |")
        lines.append("|---|-----|------|------|------|")
        for i, step in enumerate(proc.get("steps", []), 1):
            lines.append(f"| {i} | {step['aaa']} | {step['location']} | "
                        f"{step['input']} | {step['expected']} |")
        
        # Post state
        if proc.get("post_state"):
            lines.append(f"\n**后置状态**：{proc['post_state']}")
        
        # Cascade chain
        if proc.get("cascade_chain"):
            lines.append(f"**级联链**：{proc['cascade_chain']}")
        
        # Dependencies
        if s3.get("dependencies"):
            lines.append(f"**依赖**：{', '.join(s3['dependencies'])}")
        if s3.get("weak_dependencies"):
            lines.append(f"**弱依赖**：{', '.join(s3['weak_dependencies'])}")
        
        # Multi instance
        if s4.get("multi_instance"):
            lines.append(f"**多实例**：{s4['multi_count']} × {s4['multi_reason']}")
        
        lines.append("")
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


if __name__ == "__main__":
    cm_path = sys.argv[1] if len(sys.argv) > 1 else "/home/z/my-project/download/coverage_model.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "/home/z/my-project/download/p3_agent_output.json"
    
    run_p3_pipeline(cm_path, out_path)
