"""
state.py — Sprint 3D
─────────────────────
Added multi-city fields: is_multi_city, city_stops, city_itineraries.

KEY RULE: Every field uses Annotated + reducer to prevent
parallel agent conflicts.
"""

import operator
from typing import TypedDict, List, Optional, Any, Annotated


def _keep_last(existing, new):
    return new

def _keep_last_list(existing, new):
    return new


class TravelPlanState(TypedDict):

    # ── RAW INPUT ─────────────────────────────────────────
    user_message: Annotated[str, _keep_last]

    # ── PARSED INTENT ─────────────────────────────────────
    destination:        Annotated[str, _keep_last]
    origin:             Annotated[str, _keep_last]
    budget:             Annotated[int, _keep_last]
    duration_days:      Annotated[int, _keep_last]
    travel_style:       Annotated[str, _keep_last]
    interests:          Annotated[List[Any], _keep_last_list]
    travel_dates:       Annotated[dict, _keep_last]
    num_travelers:      Annotated[int, _keep_last]
    food_preferences:   Annotated[str, _keep_last]
    assumptions_made:   Annotated[List[Any], _keep_last_list]
    origin_detected:    Annotated[bool, _keep_last]
    interests_inferred: Annotated[bool, _keep_last]

    # ── MULTI-CITY (Sprint 3D) ────────────────────────────
    # is_multi_city: True when user mentions 2+ destinations
    # city_stops: ordered list of stop dicts:
    #   {city, days, transport_from_prev, transport_time_hrs, highlights}
    # city_itineraries: {city_name: [day_numbers]} for UI grouping
    is_multi_city:    Annotated[bool, _keep_last]
    city_stops:       Annotated[List[Any], _keep_last_list]
    city_itineraries: Annotated[dict, _keep_last]

    # ── LAYER 2: PARALLEL RESEARCH ────────────────────────
    destination_info:             Annotated[dict, _keep_last]
    transport_options:            Annotated[List[Any], _keep_last_list]
    recommended_transport_id:     Annotated[str, _keep_last]
    weather_forecast:             Annotated[dict, _keep_last]
    accommodation_options:        Annotated[List[Any], _keep_last_list]
    recommended_accommodation_id: Annotated[str, _keep_last]

    # ── LAYER 3: PLAN OPTIONS ─────────────────────────────
    plan_options:          Annotated[dict, _keep_last]
    system_recommendation: Annotated[str, _keep_last]
    recommendation_reason: Annotated[str, _keep_last]

    # ── CHECKPOINT 1 RESULT ───────────────────────────────
    chosen_option:         Annotated[str, _keep_last]
    chosen_option_details: Annotated[dict, _keep_last]

    # ── LAYER 4: DEEP SEARCH ──────────────────────────────
    activities:       Annotated[List[Any], _keep_last_list]
    budget_breakdown: Annotated[dict, _keep_last]
    projected_total:  Annotated[int, _keep_last]
    budget_feasible:  Annotated[bool, _keep_last]
    budget_warnings:  Annotated[List[Any], _keep_last_list]

    # ── CHECKPOINT 2 RESULT ───────────────────────────────
    approved_budget: Annotated[dict, _keep_last]
    budget_modified: Annotated[bool, _keep_last]

    # ── LAYER 5: BOOKING CART ─────────────────────────────
    booking_cart:           Annotated[List[Any], _keep_last_list]
    cart_total:             Annotated[int, _keep_last]
    selected_transport:     Annotated[dict, _keep_last]
    selected_accommodation: Annotated[dict, _keep_last]
    selected_activities:    Annotated[List[Any], _keep_last_list]

    # ── CHECKPOINT 3 RESULT ───────────────────────────────
    bookings_confirmed: Annotated[bool, _keep_last]

    # ── LAYER 6: ITINERARY ────────────────────────────────
    daily_itinerary:      Annotated[List[Any], _keep_last_list]
    final_budget_summary: Annotated[dict, _keep_last]
    trip_summary:         Annotated[dict, _keep_last]

    # ── LAYER 7: OUTPUTS ──────────────────────────────────
    pdf_path:  Annotated[str,   _keep_last]
    pdf_bytes: Annotated[bytes, _keep_last]
    map_html:  Annotated[str,   _keep_last]

    # ── REPLANNING ────────────────────────────────────────
    replan_requested:       Annotated[bool, _keep_last]
    replan_instruction:     Annotated[str, _keep_last]
    replan_category_to_cut: Annotated[str, _keep_last]
    replan_scope:           Annotated[List[Any], _keep_last_list]
    replan_count:           Annotated[int, _keep_last]

    # ── WORKFLOW CONTROL ──────────────────────────────────
    current_phase:     Annotated[str, _keep_last]
    awaiting_human:    Annotated[bool, _keep_last]
    checkpoint_number: Annotated[int, _keep_last]
    checkpoint_data:   Annotated[dict, _keep_last]
    human_response:    Annotated[Optional[dict], _keep_last]
    errors:            Annotated[List[Any], operator.add]
    warnings:          Annotated[List[Any], operator.add]
    retry_count:       Annotated[int, _keep_last]


def create_initial_state(user_message: str) -> dict:
    return {
        "user_message":                user_message,
        "destination":                 "",
        "origin":                      "",
        "budget":                      0,
        "duration_days":               0,
        "travel_style":                "",
        "interests":                   [],
        "travel_dates":                {},
        "num_travelers":               1,
        "food_preferences":            "any",
        "assumptions_made":            [],
        "origin_detected":             False,
        "interests_inferred":          False,
        # multi-city defaults
        "is_multi_city":               False,
        "city_stops":                  [],
        "city_itineraries":            {},
        # research
        "destination_info":            {},
        "transport_options":           [],
        "recommended_transport_id":    "",
        "weather_forecast":            {},
        "accommodation_options":       [],
        "recommended_accommodation_id": "",
        # plan
        "plan_options":                {},
        "system_recommendation":       "",
        "recommendation_reason":       "",
        "chosen_option":               "",
        "chosen_option_details":       {},
        # deep search
        "activities":                  [],
        "budget_breakdown":            {},
        "projected_total":             0,
        "budget_feasible":             True,
        "budget_warnings":             [],
        "approved_budget":             {},
        "budget_modified":             False,
        # cart
        "booking_cart":                [],
        "cart_total":                  0,
        "selected_transport":          {},
        "selected_accommodation":      {},
        "selected_activities":         [],
        "bookings_confirmed":          False,
        # itinerary
        "daily_itinerary":             [],
        "final_budget_summary":        {},
        "trip_summary":                {},
        # outputs
        "pdf_path":                    "",
        "pdf_bytes":                   b"",
        "map_html":                    "",
        # replan
        "replan_requested":            False,
        "replan_instruction":          "",
        "replan_category_to_cut":      "",
        "replan_scope":                [],
        "replan_count":                0,
        # control
        "current_phase":               "start",
        "awaiting_human":              False,
        "checkpoint_number":           0,
        "checkpoint_data":             {},
        "human_response":              None,
        "errors":                      [],
        "warnings":                    [],
        "retry_count":                 0,
    }