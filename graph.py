"""P3 Agent Engine — LangGraph Pipeline Definition.

Defines the state machine: S0 → S1 → S2 → S3 → Done
"""
from langgraph.graph import StateGraph, END

from models.state import AgentState
from nodes.s0_topology import s0_topology_node
from nodes.s1_generation import s1_generation_node
from nodes.s2_sorting import s2_sorting_node
from nodes.s3_dependency import s3_dependency_node


def should_continue_after_s0(state: AgentState) -> str:
    """Router: if S0 failed, go to END; otherwise proceed to S1."""
    if state.get("current_stage") == "s0_failed":
        return "end"
    return "s1"


def should_continue_after_s1(state: AgentState) -> str:
    """Router: if S1 produced no procedures, go to END; otherwise proceed to S2."""
    procs = state.get("procedures", [])
    if not procs:
        return "end"
    return "s2"


def build_p3_graph() -> StateGraph:
    """Build the P3 agent pipeline graph.
    
    Architecture:
        S0 (Topology Discovery)
         │
         ├─ failed → END
         └─ success → S1 (Procedure Generation)
                       │
                       ├─ empty → END
                       └─ success → S2 (Sorting)
                                     │
                                     └─ S3 (Dependency Binding)
                                         │
                                         └─ END
    
    All nodes are deterministic. S0 has an LLM fallback path.
    """
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("s0", s0_topology_node)
    graph.add_node("s1", s1_generation_node)
    graph.add_node("s2", s2_sorting_node)
    graph.add_node("s3", s3_dependency_node)
    
    # Set entry point
    graph.set_entry_point("s0")
    
    # Add conditional edges
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
    
    # Linear edges
    graph.add_edge("s2", "s3")
    graph.add_edge("s3", END)
    
    return graph


def compile_p3_graph():
    """Compile the P3 graph into a runnable."""
    graph = build_p3_graph()
    return graph.compile()
