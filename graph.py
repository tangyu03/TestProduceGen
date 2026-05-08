"""P3 Agent Engine — LangGraph Pipeline Definition.

Defines the state machine: S0 → S1 → S2 → S3 → S4 → Done
"""
from langgraph.graph import StateGraph, END

from models.state import AgentState
from nodes.s0_topology import s0_topology_node
from nodes.s1_generation import s1_generation_node
from nodes.s2_sorting import s2_sorting_node
from nodes.s3_dependency import s3_dependency_node
from nodes.s4_multi_instance import s4_multi_instance_node


def should_continue_after_s0(state: AgentState) -> str:
    if state.get("current_stage") == "s0_failed":
        return "end"
    return "s1"


def should_continue_after_s1(state: AgentState) -> str:
    procs = state.get("procedures") or []
    if not procs:
        return "end"
    return "s2"


def build_p3_graph() -> StateGraph:
    """Build the P3 agent pipeline graph.

    S0 → S1 → S2 → S3 → S4 → END
    """
    graph = StateGraph(AgentState)

    graph.add_node("s0", s0_topology_node)
    graph.add_node("s1", s1_generation_node)
    graph.add_node("s2", s2_sorting_node)
    graph.add_node("s3", s3_dependency_node)
    graph.add_node("s4", s4_multi_instance_node)

    graph.set_entry_point("s0")

    graph.add_conditional_edges(
        "s0",
        should_continue_after_s0,
        {"s1": "s1", "end": END}
    )

    graph.add_conditional_edges(
        "s1",
        should_continue_after_s1,
        {"s2": "s2", "end": END}
    )

    graph.add_edge("s2", "s3")
    graph.add_edge("s3", "s4")
    graph.add_edge("s4", END)

    return graph


def compile_p3_graph():
    graph = build_p3_graph()
    return graph.compile()
