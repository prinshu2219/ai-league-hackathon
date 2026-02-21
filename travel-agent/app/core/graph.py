"""
graph.py
────────
LangGraph workflow. Checkpoints use interrupt() to pause —
no looping conditional edges needed.
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.core.state import TravelPlanState
from app.agents import (
    intent_parser_agent,
    destination_research_agent,
    transport_scout_agent,
    weather_analyst_agent,
    accommodation_scout_agent,
    merge_research_node,
    trip_options_builder_agent,
    checkpoint_1_node,
    activities_finder_agent,
    budget_architect_agent,
    merge_deep_search_node,
    checkpoint_2_node,
    booking_cart_agent,
    checkpoint_3_node,
    itinerary_architect_agent,
    pdf_generator_agent,
    map_generator_agent,
    merge_output_node,
    replan_agent,
    handle_error_node,
)


def route_after_research(state: dict) -> str:
    if state.get("errors"):
        return "handle_error"
    return "trip_options_builder"


def route_after_complete(state: dict) -> str:
    if state.get("replan_requested"):
        return "replan"
    return END


def build_travel_graph():
    graph = StateGraph(TravelPlanState)

    # ── Add nodes ─────────────────────────────────────────
    graph.add_node("intent_parser",          intent_parser_agent)

    # Layer 2: parallel research
    graph.add_node("destination_research",   destination_research_agent)
    graph.add_node("transport_scout",        transport_scout_agent)
    graph.add_node("weather_analyst",        weather_analyst_agent)
    graph.add_node("accommodation_scout",    accommodation_scout_agent)
    graph.add_node("merge_research",         merge_research_node)

    # Layer 3: options + checkpoint 1
    graph.add_node("trip_options_builder",   trip_options_builder_agent)
    graph.add_node("checkpoint_1",           checkpoint_1_node)

    # Layer 4: parallel deep search + checkpoint 2
    graph.add_node("activities_finder_node", activities_finder_agent)
    graph.add_node("budget_architect_node",  budget_architect_agent)
    graph.add_node("merge_deep_search",      merge_deep_search_node)
    graph.add_node("checkpoint_2",           checkpoint_2_node)

    # Layer 5: booking cart + checkpoint 3
    graph.add_node("booking_cart_node",      booking_cart_agent)
    graph.add_node("checkpoint_3",           checkpoint_3_node)

    # Layer 6: itinerary
    graph.add_node("itinerary_architect",    itinerary_architect_agent)

    # Layer 7: parallel outputs
    graph.add_node("pdf_generator",          pdf_generator_agent)
    graph.add_node("map_generator",          map_generator_agent)
    graph.add_node("merge_outputs",          merge_output_node)

    # Layer 8: replan + error
    graph.add_node("replan",                 replan_agent)
    graph.add_node("handle_error",           handle_error_node)

    # ── Edges ─────────────────────────────────────────────

    # Entry → fan out to 4 parallel research agents
    graph.set_entry_point("intent_parser")
    graph.add_edge("intent_parser",          "destination_research")
    graph.add_edge("intent_parser",          "transport_scout")
    graph.add_edge("intent_parser",          "weather_analyst")
    graph.add_edge("intent_parser",          "accommodation_scout")

    # 4 agents → merge → conditional route
    graph.add_edge("destination_research",   "merge_research")
    graph.add_edge("transport_scout",        "merge_research")
    graph.add_edge("weather_analyst",        "merge_research")
    graph.add_edge("accommodation_scout",    "merge_research")

    graph.add_conditional_edges(
        "merge_research",
        route_after_research,
        {"trip_options_builder": "trip_options_builder", "handle_error": "handle_error"}
    )

    # Options builder → checkpoint 1 (interrupt pauses here)
    graph.add_edge("trip_options_builder",   "checkpoint_1")

    # After checkpoint 1 resumes → fan out to 2 parallel agents
    graph.add_edge("checkpoint_1",           "activities_finder_node")
    graph.add_edge("checkpoint_1",           "budget_architect_node")

    # 2 agents → merge → checkpoint 2
    graph.add_edge("activities_finder_node", "merge_deep_search")
    graph.add_edge("budget_architect_node",  "merge_deep_search")
    graph.add_edge("merge_deep_search",      "checkpoint_2")

    # Checkpoint 2 → booking cart → checkpoint 3
    graph.add_edge("checkpoint_2",           "booking_cart_node")
    graph.add_edge("booking_cart_node",      "checkpoint_3")

    # Checkpoint 3 → itinerary → fan out to 2 output agents
    graph.add_edge("checkpoint_3",           "itinerary_architect")
    graph.add_edge("itinerary_architect",    "pdf_generator")
    graph.add_edge("itinerary_architect",    "map_generator")

    # 2 output agents → merge → end
    graph.add_edge("pdf_generator",          "merge_outputs")
    graph.add_edge("map_generator",          "merge_outputs")

    graph.add_conditional_edges(
        "merge_outputs",
        route_after_complete,
        {"replan": "replan", END: END}
    )

    graph.add_edge("replan",                 END)
    graph.add_edge("handle_error",           END)

    memory = MemorySaver()
    compiled = graph.compile(checkpointer=memory)
    print("✅ Travel Planning Graph compiled successfully")
    return compiled


travel_graph = build_travel_graph()