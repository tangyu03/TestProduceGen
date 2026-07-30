"""
AgentState — Global state pool for the P3 Agent Engine (LangGraph).

This TypedDict flows through every stage node:
    S0 (EngineState) → S1 (Procedures) → S2 (Sorted) → S3 (Dependencies) → S4 (Multi-instance)

It extends ``langgraph.graph.MessagesState`` so that every node can emit
structured messages (tool calls, reasoning, etc.) that LangGraph stores
automatically alongside the domain-specific fields below.
"""

from __future__ import annotations

from typing import Annotated, Optional

from langgraph.graph import MessagesState, add_messages
from langchain_core.messages import AnyMessage


class AgentState(MessagesState):
    """Global state that is passed between all LangGraph nodes.

    Field ordering follows the pipeline stages so that the life-cycle of
    every piece of data is easy to trace:

    * **Input** — supplied by the caller before the graph starts.
    * **S0 Output** — produced by the Engine-State node.
    * **P2 Coverage Model** — consumed by S1.
    * **S1 Output** — procedure generation results.
    * **S2 Output** — sorted procedures.
    * **S3 Output** — dependency graph / cycle detection.
    * **S4 Output** — multi-instance expansion.
    * **Metadata** — warnings, current stage tracker, errors.
    """

    # ── Input ──────────────────────────────────────────────────────────
    coverage_model_path: str  # Path to P2 coverage_model.json

    # ── S0 Output: EngineState ─────────────────────────────────────────
    primary_entity: Optional[str]
    phase_table: Optional[dict]  # {primary_dimension, state_to_phase, phase_names, phase_count}
    dep_state_phase_map: Optional[dict]  # entity → dim → state → phase
    contextual_phase_rules: Optional[dict]  # entity.dim → context rules
    state_type_map: Optional[dict]  # entity → dim → state → driving/side_effect
    dependent_entities: Optional[list[str]]
    entity_parent: Optional[dict]  # entity → parent entity
    dependency_depth: Optional[dict]  # entity → depth
    topology_levels: Optional[dict]  # entity → level
    virtual_entities: Optional[dict]  # VE name → {original_entity, parent_entity, transitions, context, co_ids, resolved_phase, trigger_source}
    transition_upstream_map: Optional[dict]  # transition_id → [upstream_ids]

    # ── P2 Coverage Model (consumed by S1) ────────────────────────────
    coverage_model: Optional[dict]  # Full P2 coverage model

    # ── S1 Output: Procedures ──────────────────────────────────────────
    procedures: Optional[list[dict]]  # List of Procedure dicts
    br_classifications: Optional[list[dict]]  # BR classification results
    type5_filtered: Optional[list[str]]  # Filtered Type5 EO IDs
    gen_seq_counter: int  # Global sequence counter

    # ── S2 Output: Sorted procedures ───────────────────────────────────
    sorted_procedures: Optional[list[dict]]

    # ── S3 Output: Dependencies bound ──────────────────────────────────
    dependency_graph: Optional[dict]  # For cycle detection results

    # ── S4 Output: Multi-instance ──────────────────────────────────────
    entity_instance_counts: Optional[dict]

    # ── Metadata ───────────────────────────────────────────────────────
    warnings: list[str]
    current_stage: str  # "init", "s0", "s1", "s2", "s3", "s4", "done"
    errors: list[str]