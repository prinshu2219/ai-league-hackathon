"""
agents/__init__.py — Sprint 3D
────────────────────────────────
Multi-city routing added to:
  1. intent_parser_agent       → detects & extracts ordered city stops
  2. trip_options_builder_agent → generates options spanning all cities
  3. itinerary_architect_agent → assigns days per city, adds inter-city transit
  4. pdf_generator_agent       → passes city_stops to PDF
  5. map_generator_agent       → passes city_stops to map for route lines

All other agents unchanged.
"""

import time
import json
import re
from datetime import datetime, timedelta
from openai import OpenAI

from app.core.config import config
from langgraph.types import interrupt
from app.utils.mock_data import (
    get_mock_destination_info,
    get_mock_transport_options,
    get_mock_weather_forecast,
    get_mock_accommodation_options,
    get_mock_activities,
)

client = OpenAI(api_key=config.OPENAI_API_KEY)


# ─────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────

def gpt4o(system: str, user: str, temperature: float = 0.3) -> dict:
    response = client.chat.completions.create(
        model=config.PRIMARY_MODEL,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return json.loads(response.choices[0].message.content)


# ─────────────────────────────────────────────────────────
# LAYER 1: INTENT PARSER — Sprint 3D multi-city detection
# ─────────────────────────────────────────────────────────

def intent_parser_agent(state: dict) -> dict:
    """
    Sprint 3D: Detects multi-city trips and extracts ordered stops.
    Single-city trips work exactly as before.

    Multi-city example:
      "Delhi → Rishikesh → Haridwar → Dehradun, 7 days, ₹25,000"
    Produces:
      is_multi_city: True
      destination: "Rishikesh, Haridwar, Dehradun"  (joined for display)
      city_stops: [
        {city: "Rishikesh", days: 3, transport_from_prev: "bus",
         transport_time_hrs: 6, highlights: ["rafting","aarti"]},
        {city: "Haridwar",  days: 2, transport_from_prev: "bus",
         transport_time_hrs: 1, highlights: ["Har Ki Pauri"]},
        {city: "Dehradun",  days: 2, transport_from_prev: "bus",
         transport_time_hrs: 1.5, highlights: ["Robber's Cave"]},
      ]
    """
    print("🧠 [Intent Parser] GPT-4o extracting intent (multi-city aware)...")

    user_message = state["user_message"]
    today      = datetime.now()
    next_fri   = today + timedelta(days=(4 - today.weekday()) % 7 or 7)
    next_sun   = next_fri + timedelta(days=2)

    system_prompt = """You are a travel intent extraction AI. You MUST detect multi-city trips.

Multi-city signals: arrows (→ or ->), "then", "followed by", "via", listing 2+ destinations,
"circuit", "route", e.g. "Delhi to Rishikesh then Haridwar".

Return a JSON object with EXACTLY these fields:
{
  "is_multi_city": boolean,
  "destination": "primary destination or comma-joined list for multi-city",
  "origin": "departure city (default Delhi if not mentioned)",
  "budget": integer INR (default 15000),
  "duration_days": integer (default 4 for single, 7 for multi-city),
  "travel_style": one of "backpacking","budget","mid-range","luxury","family","adventure",
  "interests": array from ["adventure","spiritual","food","nature","culture","nightlife","shopping","wellness"],
  "num_travelers": integer (default 1),
  "food_preferences": one of "local","vegetarian","vegan","any",
  "assumptions_made": [{field, assumed_value, reason, can_edit: true}],

  "city_stops": [
    {
      "city": "city name",
      "days": integer days to spend here,
      "transport_from_prev": "train|bus|flight|car|ferry" (from previous stop),
      "transport_time_hrs": float hours travel time from previous stop,
      "highlights": ["top 2-3 things to do here"]
    }
  ]
}

RULES:
- If is_multi_city is false, city_stops should have exactly ONE entry (the main destination)
- city_stops[0].transport_from_prev is transport FROM origin TO first city
- days across all city_stops must sum to duration_days (minus 1 for return day)
- Be specific — mention real travel times and real highlights per city
- Always return valid JSON"""

    user_prompt = f"""Today: {today.strftime('%B %d, %Y')} ({today.strftime('%A')}).
Default next weekend: {next_fri.strftime('%b %d')} to {next_sun.strftime('%b %d, %Y')}.

User message: "{user_message}"

Extract travel intent (detect multi-city carefully):"""

    try:
        result = gpt4o(system_prompt, user_prompt, temperature=0.1)

        is_multi      = bool(result.get("is_multi_city", False))
        destination   = result.get("destination", "Rishikesh")
        origin        = result.get("origin", "Delhi")
        budget        = int(result.get("budget", 15000))
        duration      = int(result.get("duration_days", 4 if not is_multi else 7))
        travel_style  = result.get("travel_style", "backpacking")
        interests     = result.get("interests", ["adventure", "spiritual"])
        num_travelers = int(result.get("num_travelers", 1))
        food_prefs    = result.get("food_preferences", "any")
        assumptions   = result.get("assumptions_made", [])
        city_stops    = result.get("city_stops", [])

        # Ensure city_stops always has at least one entry
        if not city_stops:
            city_stops = [{
                "city": destination,
                "days": duration,
                "transport_from_prev": "train",
                "transport_time_hrs": 6,
                "highlights": [],
            }]

        # Add date assumption if needed
        date_words = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec",
                      "monday","tuesday","wednesday","thursday","friday","saturday","sunday",
                      "next week","weekend","tomorrow"]
        if not any(w in user_message.lower() for w in date_words):
            assumptions.append({
                "field": "dates",
                "assumed_value": f"{next_fri.strftime('%b %d')} onwards",
                "reason": "No dates mentioned — defaulted to next available Friday",
                "can_edit": True,
            })

        start_date = next_fri
        end_date   = start_date + timedelta(days=duration - 1)

        # Build city_itineraries mapping: which day numbers belong to each city
        city_itineraries = {}
        day_cursor = 2  # day 1 is always travel day
        for stop in city_stops:
            city     = stop["city"]
            n_days   = stop.get("days", 1)
            day_nums = list(range(day_cursor, day_cursor + n_days))
            city_itineraries[city] = day_nums
            day_cursor += n_days

        mode = "🗺️ Multi-city" if is_multi else "📍 Single-city"
        cities = " → ".join(s["city"] for s in city_stops)
        print(f"   ✅ {mode}: {cities} | ₹{budget:,} | {travel_style} | {duration}d")

        return {
            "destination":       destination,
            "origin":            origin,
            "budget":            budget,
            "duration_days":     duration,
            "travel_style":      travel_style,
            "interests":         interests,
            "travel_dates": {
                "start":       start_date.strftime("%Y-%m-%d"),
                "end":         end_date.strftime("%Y-%m-%d"),
                "is_flexible": True,
                "assumed":     True,
            },
            "num_travelers":     num_travelers,
            "food_preferences":  food_prefs,
            "assumptions_made":  assumptions,
            "interests_inferred": True,
            "is_multi_city":     is_multi,
            "city_stops":        city_stops,
            "city_itineraries":  city_itineraries,
            "current_phase":     "intent_parsed",
        }

    except Exception as e:
        print(f"   ⚠️ GPT-4o failed ({e}), fallback...")
        return _intent_fallback(state, next_fri)


def _intent_fallback(state: dict, next_fri: datetime) -> dict:
    user_message = state["user_message"].lower()
    budget_match = re.search(r'₹\s*(\d+(?:,\d+)*)', state["user_message"])
    budget = int(budget_match.group(1).replace(",", "")) if budget_match else 15000
    travel_style = "backpacking"
    if any(w in user_message for w in ["luxury","5 star"]): travel_style = "luxury"
    elif any(w in user_message for w in ["family","kids"]): travel_style = "family"
    interests = ["adventure", "spiritual"]
    start = next_fri
    return {
        "destination": "Rishikesh", "origin": "Delhi",
        "budget": budget, "duration_days": 4,
        "travel_style": travel_style, "interests": interests,
        "travel_dates": {"start": start.strftime("%Y-%m-%d"),
                         "end": (start + timedelta(days=3)).strftime("%Y-%m-%d"),
                         "is_flexible": True, "assumed": True},
        "num_travelers": 1, "food_preferences": "any",
        "assumptions_made": [{"field": "destination", "assumed_value": "Rishikesh",
                               "reason": "Fallback", "can_edit": True}],
        "interests_inferred": True,
        "is_multi_city": False,
        "city_stops": [{"city": "Rishikesh", "days": 4,
                        "transport_from_prev": "train",
                        "transport_time_hrs": 6, "highlights": []}],
        "city_itineraries": {"Rishikesh": [2, 3, 4]},
        "current_phase": "intent_parsed",
    }


# ─────────────────────────────────────────────────────────
# LAYER 2: PARALLEL RESEARCH — unchanged
# ─────────────────────────────────────────────────────────

def destination_research_agent(state: dict) -> dict:
    print(f"🔍 [Research] Researching {state['destination']}...")
    from app.tools.research import get_destination_info
    info = get_destination_info(state["destination"])
    return {"destination_info": info}


def transport_scout_agent(state: dict) -> dict:
    print(f"🚌 [Transport] {state['origin']} → {state['destination']}...")
    from app.tools.transport import get_transport_options
    options = get_transport_options(
        origin        = state["origin"],
        destination   = state["destination"],
        travel_date   = state["travel_dates"].get("start", "2025-03-01"),
        budget        = state.get("budget", 15000),
        num_travelers = state.get("num_travelers", 1),
    )
    affordable = [o for o in options if o["price"] * 2 <= state["budget"] * 0.20]
    rec_id = affordable[0]["id"] if affordable else (options[0]["id"] if options else "")
    return {"transport_options": options, "recommended_transport_id": rec_id}


def weather_analyst_agent(state: dict) -> dict:
    print(f"🌤️  [Weather] {state['destination']}...")
    from app.tools.weather import get_weather_forecast
    forecast = get_weather_forecast(
        destination = state["destination"],
        start_date  = state["travel_dates"].get("start", "2025-03-01"),
        days        = state["duration_days"],
    )
    return {"weather_forecast": forecast}


def accommodation_scout_agent(state: dict) -> dict:
    print(f"🏨 [Accommodation] {state['destination']}...")
    from app.tools.hotels import get_accommodation_options
    from datetime import datetime, timedelta
    start_str  = state["travel_dates"].get("start", "2025-03-01")
    duration   = state.get("duration_days", 4)
    check_in   = start_str
    check_out  = (datetime.strptime(start_str, "%Y-%m-%d") +
                  timedelta(days=duration - 1)).strftime("%Y-%m-%d")
    options = get_accommodation_options(
        destination   = state["destination"],
        style         = state.get("travel_style", "mid-range"),
        check_in      = check_in,
        check_out     = check_out,
        duration_days = duration,
        budget        = state.get("budget", 15000),
        num_travelers = state.get("num_travelers", 1),
    )
    budget_per_night = (state["budget"] * 0.25) / max(duration, 1)
    affordable = [o for o in options if o["price_per_night"] <= budget_per_night * 1.2]
    rec_id = affordable[0]["id"] if affordable else (options[0]["id"] if options else "")
    return {"accommodation_options": options, "recommended_accommodation_id": rec_id}


def merge_research_node(state: dict) -> dict:
    print("\n🔗 [Merge Research] Done...")
    warnings = list(state.get("weather_forecast", {}).get("warnings", []))
    return {"current_phase": "research_merged", "warnings": warnings}


# ─────────────────────────────────────────────────────────
# LAYER 3: TRIP OPTIONS BUILDER — multi-city aware
# ─────────────────────────────────────────────────────────

def trip_options_builder_agent(state: dict) -> dict:
    print(f"✨ [Options Builder] GPT-4o creating options...")

    is_multi     = state.get("is_multi_city", False)
    city_stops   = state.get("city_stops", [])
    destination  = state["destination"]
    budget       = state["budget"]
    duration     = state["duration_days"]
    interests    = state["interests"]
    travel_style = state["travel_style"]
    weather_sum  = state.get("weather_forecast", {}).get("summary", "")

    if is_multi:
        route_str  = " → ".join(s["city"] for s in city_stops)
        stops_desc = "\n".join([
            f"- {s['city']}: {s['days']} days "
            f"({s['transport_from_prev']}, {s['transport_time_hrs']}hrs from prev stop)"
            for s in city_stops
        ])
        route_context = f"""This is a MULTI-CITY trip along this route:
{route_str}

Stop breakdown:
{stops_desc}

Each option must cover ALL cities in the route."""
    else:
        route_context = f"Single destination: {destination}"

    system_prompt = """You are an expert travel planner. Create 3 distinct trip options.

Return JSON with EXACTLY this structure:
{
  "options": {
    "A": {
      "style_name": "short name",
      "style_tag": "one-line descriptor",
      "highlights": ["highlight 1", "highlight 2", "highlight 3", "highlight 4"],
      "estimated_total": integer INR under budget,
      "rough_breakdown": {
        "travel": integer,
        "stay": integer,
        "food": integer,
        "activities": integer,
        "local_transport": integer,
        "buffer": integer
      },
      "why_this_works": "2-3 sentences",
      "trade_offs": "1-sentence honest trade-off",
      "activities_included": ["tag1", "tag2"]
    },
    "B": { same },
    "C": { same }
  },
  "recommendation": "A"|"B"|"C",
  "recommendation_reason": "one sentence"
}

Rules:
- estimated_total must be under the total budget
- rough_breakdown values must sum to estimated_total
- Be specific to the actual places — mention real things to do
- Options A/B/C should feel genuinely different (pace, depth, spend pattern)"""

    user_prompt = f"""{route_context}

Budget: Rs {budget:,} total
Duration: {duration} days
Style: {travel_style}
Interests: {', '.join(interests)}
Weather: {weather_sum}

Create 3 genuinely different options:"""

    try:
        result  = gpt4o(system_prompt, user_prompt, temperature=0.7)
        options = result.get("options", {})
        rec     = result.get("recommendation", "A")
        reason  = result.get("recommendation_reason", "")
        cities  = " → ".join(s["city"] for s in city_stops) if is_multi else destination
        print(f"   ✅ Options built for: {cities}")
        return {
            "plan_options":          options,
            "system_recommendation": rec,
            "recommendation_reason": reason,
            "current_phase":         "options_built",
        }
    except Exception as e:
        print(f"   ⚠️ GPT-4o failed ({e}), fallback...")
        return _options_fallback(state)


def _options_fallback(state: dict) -> dict:
    budget = state["budget"]
    options = {
        "A": {
            "style_name": "Balanced Explorer", "style_tag": "Best of everything",
            "highlights": ["Sightseeing", "Local food", "Key attractions", "Cultural experience"],
            "estimated_total": int(budget * 0.85),
            "rough_breakdown": {"travel": int(budget*0.08), "stay": int(budget*0.25),
                                 "food": int(budget*0.17), "activities": int(budget*0.23),
                                 "local_transport": int(budget*0.05), "buffer": int(budget*0.07)},
            "why_this_works": "Perfect mix within budget.",
            "trade_offs": "Not the deepest dive into any one thing.",
            "activities_included": state.get("interests", []),
        },
        "B": {
            "style_name": "Budget Maximizer", "style_tag": "More for less",
            "highlights": ["Free attractions", "Local transport", "Street food", "Self-guided"],
            "estimated_total": int(budget * 0.65),
            "rough_breakdown": {"travel": int(budget*0.08), "stay": int(budget*0.18),
                                 "food": int(budget*0.12), "activities": int(budget*0.15),
                                 "local_transport": int(budget*0.05), "buffer": int(budget*0.07)},
            "why_this_works": "Maximizes time with minimal spend.",
            "trade_offs": "Some premium experiences skipped.",
            "activities_included": ["culture", "food"],
        },
        "C": {
            "style_name": "Experience First", "style_tag": "Splurge on what matters",
            "highlights": ["Premium activity", "Better stay", "Guided tours", "Special dinner"],
            "estimated_total": int(budget * 0.95),
            "rough_breakdown": {"travel": int(budget*0.08), "stay": int(budget*0.30),
                                 "food": int(budget*0.18), "activities": int(budget*0.28),
                                 "local_transport": int(budget*0.04), "buffer": int(budget*0.07)},
            "why_this_works": "Invest in quality experiences.",
            "trade_offs": "Tight buffer.",
            "activities_included": state.get("interests", []),
        },
    }
    return {"plan_options": options, "system_recommendation": "A",
            "recommendation_reason": "Best balance within budget.",
            "current_phase": "options_built"}


# ─────────────────────────────────────────────────────────
# CHECKPOINTS — unchanged
# ─────────────────────────────────────────────────────────

def checkpoint_1_node(state: dict) -> dict:
    print("\n⏸  [Checkpoint 1] Waiting for plan selection...")
    human_response = interrupt({
        "type":            "plan_selection",
        "options":         state.get("plan_options", {}),
        "recommendation":  state.get("system_recommendation", "A"),
        "assumptions":     state.get("assumptions_made", []),
        "weather_summary": state.get("weather_forecast", {}).get("summary", ""),
        "is_multi_city":   state.get("is_multi_city", False),
        "city_stops":      state.get("city_stops", []),
    })
    chosen  = human_response.get("chosen_option", "A")
    options = state.get("plan_options", {})
    print(f"   ✅ User selected Option {chosen}")
    update = {
        "chosen_option":         chosen,
        "chosen_option_details": options.get(chosen, {}),
        "awaiting_human":        False,
        "current_phase":         "option_selected",
    }
    if human_response.get("updated_dates"):
        update["travel_dates"] = human_response["updated_dates"]
    if human_response.get("updated_interests"):
        update["interests"] = human_response["updated_interests"]
    return update


def checkpoint_2_node(state: dict) -> dict:
    print("\n⏸  [Checkpoint 2] Waiting for budget approval...")
    human_response = interrupt({
        "type":            "budget_approval",
        "breakdown":       state.get("budget_breakdown", {}),
        "projected_total": state.get("projected_total", 0),
        "budget":          state.get("budget", 0),
        "warnings":        state.get("budget_warnings", []),
    })
    approved = human_response.get("approved_budget", state.get("budget_breakdown", {}))
    modified = approved != state.get("budget_breakdown", {})
    print(f"   ✅ Budget {'modified' if modified else 'approved'}")
    return {
        "approved_budget": approved, "budget_modified": modified,
        "awaiting_human": False, "current_phase": "budget_approved",
    }


def checkpoint_3_node(state: dict) -> dict:
    print("\n⏸  [Checkpoint 3] Waiting for booking confirmation...")
    human_response = interrupt({
        "type":              "booking_confirmation",
        "cart":              state.get("booking_cart", []),
        "cart_total":        state.get("cart_total", 0),
        "full_trip_estimate": state.get("full_trip_estimate",
                                state.get("projected_total", 0)),
        "budget":            state.get("budget", 0),
    })
    confirmed = human_response.get("confirmed", False)
    print(f"   ✅ Bookings {'confirmed' if confirmed else 'rejected'}")
    if not confirmed:
        return {"bookings_confirmed": False, "awaiting_human": True, "current_phase": "options_built"}
    return {"bookings_confirmed": True, "awaiting_human": False, "current_phase": "bookings_confirmed"}


# ─────────────────────────────────────────────────────────
# LAYER 4: DEEP SEARCH — unchanged
# ─────────────────────────────────────────────────────────

def activities_finder_agent(state: dict) -> dict:
    print(f"🎯 [Activities] Finding activities...")
    from app.tools.activities import get_activities
    chosen = state.get("chosen_option_details", {})
    tags   = chosen.get("activities_included", state.get("interests", []))
    acts   = get_activities(
        destination   = state["destination"],
        interests     = tags,
        duration_days = state.get("duration_days", 4),
    )
    return {"activities": acts}


def budget_architect_agent(state: dict) -> dict:
    print(f"💰 [Budget Architect] Building breakdown...")
    budget   = state["budget"]
    duration = state["duration_days"]
    chosen   = state.get("chosen_option_details", {})
    rough    = chosen.get("rough_breakdown", {})

    NOTES = {
        "travel": "Return transport", "stay": f"{duration-1} nights",
        "food": "Food & drinks", "activities": "Experiences",
        "local_transport": "Local travel", "buffer": "Emergency",
    }
    CATS = ["travel", "stay", "food", "activities", "local_transport", "buffer"]

    if rough and all(k in rough for k in CATS):
        breakdown = {
            cat: {
                "allocated": int(rough[cat]),
                "per_day":   int(rough[cat]) // max(duration, 1) if cat not in ["travel","buffer"] else 0,
                "actual":    0,
                "notes":     NOTES.get(cat, ""),
            }
            for cat in CATS
        }
        raw_projected = sum(v["allocated"] for v in breakdown.values())

        # ── KEY FIX: normalize so breakdown sums exactly to chosen option's
        # estimated_total. GPT-4o generates rough_breakdown values independently
        # and they rarely sum to the advertised total. ──────────────────────
        chosen_total = int(chosen.get("estimated_total", 0))
        if chosen_total > 0 and raw_projected != chosen_total:
            scale = chosen_total / raw_projected
            for cat in CATS:
                breakdown[cat]["allocated"] = int(breakdown[cat]["allocated"] * scale)
            # Fix rounding residual on the largest category
            residual = chosen_total - sum(v["allocated"] for v in breakdown.values())
            if residual != 0:
                largest = max(CATS, key=lambda c: breakdown[c]["allocated"])
                breakdown[largest]["allocated"] += residual
            # Recompute per_day with normalized values
            for cat in CATS:
                if cat not in ["travel", "buffer"]:
                    breakdown[cat]["per_day"] = breakdown[cat]["allocated"] // max(duration, 1)

        projected = sum(v["allocated"] for v in breakdown.values())
        feasible  = projected <= budget
        warnings  = [f"⚠️ Projected Rs {projected:,} slightly over budget Rs {budget:,}"]                     if not feasible else []
        print(f"   ✅ Budget: Rs {projected:,} (option estimate: Rs {chosen_total:,})")
        return {"budget_breakdown": breakdown, "projected_total": projected,
                "budget_feasible": feasible, "budget_warnings": warnings}

    # ── Percentage fallback (no rough_breakdown from GPT-4o) ──────────────
    # Use 90% of total budget as a reasonable estimate
    target = int(budget * 0.88)
    allocs = {"travel": 0.09, "stay": 0.28, "food": 0.19,
              "activities": 0.28, "local_transport": 0.07, "buffer": 0.09}
    breakdown = {
        cat: {
            "allocated": int(target * pct),
            "per_day":   int(target * pct // duration) if cat not in ["travel","buffer"] else 0,
            "actual":    0,
            "notes":     NOTES.get(cat, cat.replace("_"," ").title()),
        }
        for cat, pct in allocs.items()
    }
    # Normalize to target
    raw = sum(v["allocated"] for v in breakdown.values())
    residual = target - raw
    if residual:
        breakdown["activities"]["allocated"] += residual
    projected = sum(v["allocated"] for v in breakdown.values())
    return {"budget_breakdown": breakdown, "projected_total": projected,
            "budget_feasible": True, "budget_warnings": []}


def merge_deep_search_node(state: dict) -> dict:
    print("\n🔗 [Merge Deep Search] Done...")
    return {"current_phase": "deep_search_merged"}


# ─────────────────────────────────────────────────────────
# LAYER 5: BOOKING CART — unchanged
# ─────────────────────────────────────────────────────────

def booking_cart_agent(state: dict) -> dict:
    print(f"🛒 [Booking Cart] Assembling...")
    time.sleep(0.2)
    transport_options = state.get("transport_options", [])
    rec_id    = state.get("recommended_transport_id", "")
    transport = next((t for t in transport_options if t["id"] == rec_id),
                     transport_options[0] if transport_options else {})
    accommodation_options = state.get("accommodation_options", [])
    rec_acc   = state.get("recommended_accommodation_id", "")
    accommodation = next((a for a in accommodation_options if a["id"] == rec_acc),
                         accommodation_options[0] if accommodation_options else {})
    activity_budget = state.get("approved_budget",{}).get("activities",{}).get("allocated",4000)
    selected_acts, running = [], 0
    for act in sorted(state.get("activities",[]), key=lambda x: -x["price"]):
        if running + act["price"] <= activity_budget:
            selected_acts.append(act); running += act["price"]
        if len(selected_acts) >= 4: break

    cart = []
    if transport:
        cart.append({
            "category":             "transport",
            "name":                 f"{transport.get('mode','').title()} — {transport.get('operator','')}",
            "details":              f"{state['origin']} → {state['destination']}",
            "cost":                 transport.get("price", 0) * 2,
            "booking_link":         transport.get("booking_link", ""),
            "notes":                transport.get("notes", ""),
            "source":               transport.get("source", ""),
            "confirmation_required": True,
        })
    if accommodation:
        nights = max(state["duration_days"] - 1, 1)
        cart.append({
            "category":             "stay",
            "name":                 accommodation.get("name", ""),
            "details":              f"Rs {accommodation.get('price_per_night',0):,}/night × {nights} nights",
            "cost":                 accommodation.get("total_price",
                                        accommodation.get("price_per_night", 0) * nights),
            "booking_link":         accommodation.get("booking_link", ""),
            "notes":                accommodation.get("why_recommended", ""),
            "source":               accommodation.get("source", ""),
            "confirmation_required": True,
        })
    for act in selected_acts:
        cart.append({
            "category":             "activity",
            "name":                 act["name"],
            "details":              f"Day {act['best_day']} | {act['duration_hours']}hrs",
            "cost":                 act["price"],
            "booking_link":         act.get("booking_link", ""),
            "notes":                act.get("why_recommended", ""),
            "source":               act.get("source", ""),
            "confirmation_required": act["price"] > 0,
        })
    cart_total = sum(i["cost"] for i in cart)
    # full_trip_estimate = the approved projected_total from Step 2
    # This is what the WHOLE TRIP costs (including food, local transport, buffer)
    # cart_total is only the bookable subset
    full_trip_estimate = state.get("projected_total", 0)
    print(f"   ✅ Cart (bookable): Rs {cart_total:,} | Full trip: Rs {full_trip_estimate:,}")
    return {
        "booking_cart":          cart,
        "cart_total":            cart_total,
        "full_trip_estimate":    full_trip_estimate,
        "selected_transport":    transport,
        "selected_accommodation": accommodation,
        "selected_activities":   selected_acts,
        "current_phase":         "cart_ready",
    }


# ─────────────────────────────────────────────────────────
# LAYER 6: ITINERARY ARCHITECT — Sprint 3D multi-city
# ─────────────────────────────────────────────────────────

def itinerary_architect_agent(state: dict) -> dict:
    """
    Sprint 3D: Builds itinerary for both single and multi-city trips.

    Multi-city logic:
    - Day 1: Depart origin → arrive first city
    - Per city block: sightseeing days + final day has inter-city transit
    - Last day: morning in last city + return to origin
    - GPT-4o gets full city_stops context so it plans correctly
    """
    is_multi   = state.get("is_multi_city", False)
    city_stops = state.get("city_stops", [])
    mode_label = "multi-city" if is_multi else "single-destination"
    print(f"🗓️  [Itinerary] GPT-4o building {state['duration_days']}-day {mode_label} plan...")

    destination   = state["destination"]
    origin        = state["origin"]
    duration      = state["duration_days"]
    interests     = state["interests"]
    travel_style  = state.get("travel_style","backpacking")
    transport     = state.get("selected_transport",{})
    hotel         = state.get("selected_accommodation",{})
    activities    = state.get("selected_activities",[])
    budget        = state["budget"]
    start_date    = state["travel_dates"]["start"]
    num_travelers = state.get("num_travelers",1)
    food_pref     = state.get("food_preferences","local")

    act_list = "\n".join([f"- {a['name']}: Rs {a['price']} ({a['duration_hours']}hrs)"
                           for a in activities]) or "No pre-booked activities"

    if is_multi:
        route_str  = " → ".join(s["city"] for s in city_stops)
        stops_desc = "\n".join([
            f"  City {i+1}: {s['city']} — {s['days']} days"
            f" | arrive by {s['transport_from_prev']} ({s['transport_time_hrs']}hrs from prev)"
            f" | key things: {', '.join(s.get('highlights', []))}"
            for i, s in enumerate(city_stops)
        ])
        route_context = f"""MULTI-CITY ROUTE: {origin} → {route_str} → {origin} (return)

Stop details:
{stops_desc}

IMPORTANT RULES for multi-city itinerary:
- Day 1: Travel from {origin} to {city_stops[0]['city']}
- Each city block ends with a transit day to next city
- Build a transit segment at the START of each new city's first day
- Last day: morning in {city_stops[-1]['city']} + return to {origin}
- Spread the booked activities across relevant cities"""
    else:
        route_context = f"Single destination: {destination} (depart from {origin})"

    system_prompt = """You are an expert travel planner with deep local knowledge.
Create a detailed day-by-day itinerary as JSON.

Return EXACTLY this structure:
{
  "days": [
    {
      "day_number": 1,
      "date": "YYYY-MM-DD",
      "city": "which city this day is in",
      "theme": "short theme",
      "segments": [
        {
          "time": "HH:MM",
          "type": "transport|checkin|activity|meal|free_time",
          "title": "short title",
          "description": "1-2 sentences",
          "duration_mins": integer,
          "cost": integer INR,
          "notes": "practical tip",
          "maps_query": "google maps search query"
        }
      ],
      "daily_cost_estimate": integer,
      "highlights": ["highlight 1", "highlight 2"]
    }
  ],
  "total_estimated_cost": integer,
  "local_tips": ["tip 1", "tip 2", "tip 3"]
}

Rules:
- Day 1 always starts with departure from origin
- Each day must have "city" field
- For transit days between cities: include a transport segment at the START
- Times must be realistic
- Meals included naturally throughout"""

    user_prompt = f"""{route_context}

Trip details:
- Start date: {start_date}
- Duration: {duration} days
- Style: {travel_style}, Interests: {', '.join(interests)}
- Travelers: {num_travelers}, Food: {food_pref}
- First leg transport: {transport.get('mode','train')} ({transport.get('operator','')}, Rs {transport.get('price',550)})
- Primary accommodation: {hotel.get('name','hostel')} (Rs {hotel.get('price_per_night',900)}/night)

Pre-booked activities to distribute across days:
{act_list}

Build the complete itinerary:"""

    try:
        result = gpt4o(system_prompt, user_prompt, temperature=0.5)
        days   = result.get("days", [])
        if not days:
            raise ValueError("Empty days from GPT-4o")

        itinerary = []
        for day in days:
            segs = []
            for seg in day.get("segments", []):
                mq = seg.get("maps_query", "")
                segs.append({
                    "time":          seg.get("time","09:00"),
                    "type":          seg.get("type","activity"),
                    "title":         seg.get("title",""),
                    "description":   seg.get("description",""),
                    "duration_mins": int(seg.get("duration_mins",60)),
                    "cost":          int(seg.get("cost",0)),
                    "notes":         seg.get("notes",""),
                    "maps_link":     f"https://maps.google.com/?q={mq.replace(' ','+')}" if mq else "",
                    "booking_link":  "",
                    "weather_note":  "",
                })
            itinerary.append({
                "day_number":          day.get("day_number",1),
                "date":                day.get("date",""),
                "city":                day.get("city", destination),
                "theme":               day.get("theme",""),
                "segments":            segs,
                "daily_cost_estimate": int(day.get("daily_cost_estimate",0)),
                "highlights":          day.get("highlights",[]),
            })

        # Build city_itineraries from actual day data
        city_itineraries = {}
        for day in itinerary:
            city = day.get("city", destination)
            city_itineraries.setdefault(city, []).append(day["day_number"])

        # ── USE projected_total FROM STEP 2 AS AUTHORITATIVE COST ──────
        projected_total = state.get("projected_total", 0)
        approved        = state.get("budget_breakdown", {})
        daily_sum_raw   = sum(d["daily_cost_estimate"] for d in itinerary)
        total_cost      = (projected_total if projected_total > 0
                           else int(result.get("total_estimated_cost", daily_sum_raw)))

        # ── REDISTRIBUTE DAILY COSTS SO THEY SUM TO total_cost ──────────
        # Each day's headline cost = prorated share of EVERY budget category.
        # This means the day‑by‑day numbers and the budget breakdown
        # always add up to the same figure.
        if total_cost > 0 and len(itinerary) > 0:
            # Pull per-category allocations (fall back to zeroes gracefully)
            a_travel   = approved.get("travel",          {}).get("allocated", transport.get("price",0)*2)
            a_stay     = approved.get("stay",            {}).get("allocated", hotel.get("price_per_night",0)*(duration-1))
            a_food     = approved.get("food",            {}).get("allocated", 0)
            a_acts     = approved.get("activities",      {}).get("allocated", 0)
            a_local    = approved.get("local_transport", {}).get("allocated", 0)
            a_buffer   = approved.get("buffer",          {}).get("allocated", 0)

            nights     = max(duration - 1, 1)
            stay_pn    = a_stay / nights          # stay cost per night
            food_pd    = a_food / duration         # food per day
            local_pd   = a_local / duration        # local transport per day
            buffer_pd  = a_buffer / duration       # buffer per day
            transport_ow = a_travel / 2            # one-way transport cost

            # Per-day activity cost = sum of actual activity segment costs on that day
            day_act_costs = {}
            for d in itinerary:
                day_act_costs[d["day_number"]] = sum(
                    s["cost"] for s in d.get("segments", [])
                    if s["type"] == "activity"
                )
            total_act_segments = sum(day_act_costs.values())
            # If segment costs don't match allocated, scale them
            act_scale = (a_acts / total_act_segments) if total_act_segments > 0 else 0

            new_daily = {}
            for d in itinerary:
                dn = d["day_number"]
                is_first = (dn == 1)
                is_last  = (dn == duration)
                act_cost = day_act_costs[dn] * act_scale if act_scale > 0 else (a_acts / duration)
                # Transport: split between first and last day
                travel_today = transport_ow if (is_first or is_last) else 0
                # Stay: every night except checkout day (last day)
                stay_today   = stay_pn if not is_last else 0
                new_daily[dn] = int(travel_today + stay_today + food_pd + act_cost + local_pd + buffer_pd)

            # Normalize: ensure sum == total_cost (fix integer rounding)
            current_sum = sum(new_daily.values())
            if current_sum != total_cost:
                residual = total_cost - current_sum
                # Add residual to the middle day (most natural)
                mid_day = itinerary[len(itinerary)//2]["day_number"]
                new_daily[mid_day] += residual

            # Apply back to itinerary
            for d in itinerary:
                d["daily_cost_estimate"] = new_daily[d["day_number"]]

        final_budget = {
            "travel":          approved.get("travel",      {}).get("allocated", transport.get("price",0)*2),
            "stay":            approved.get("stay",        {}).get("allocated", hotel.get("price_per_night",0)*(duration-1)),
            "food":            approved.get("food",        {}).get("allocated", 0),
            "activities":      approved.get("activities",  {}).get("allocated", sum(a["price"] for a in activities)),
            "local_transport": approved.get("local_transport",{}).get("allocated", 800),
            "buffer":          approved.get("buffer",      {}).get("allocated", 0),
            "estimated_total": total_cost,
            "remaining":       budget - total_cost,
        }

        # Build route label for summary
        if is_multi:
            route_label = " → ".join(s["city"] for s in city_stops)
        else:
            route_label = destination

        trip_summary = {
            "destination":    route_label,
            "duration":       f"{duration} Days",
            "budget":         f"Rs {budget:,}",
            "style":          state.get("chosen_option_details",{}).get("style_name", travel_style),
            "travelers":      num_travelers,
            "dates":          f"{state['travel_dates']['start']} to {state['travel_dates']['end']}",
            "estimated_cost": f"Rs {total_cost:,}",
            "savings":        f"Rs {budget-total_cost:,} remaining",
            "local_tips":     result.get("local_tips",[]),
            "is_multi_city":  is_multi,
            "city_stops":     city_stops,
        }

        print(f"   ✅ {len(itinerary)}-day itinerary | {len(city_itineraries)} cities | Rs {total_cost:,}")
        return {
            "daily_itinerary":      itinerary,
            "final_budget_summary": final_budget,
            "trip_summary":         trip_summary,
            "city_itineraries":     city_itineraries,
            "current_phase":        "itinerary_built",
        }

    except Exception as e:
        print(f"   ⚠️ GPT-4o failed ({e}), fallback...")
        return _itinerary_fallback(state)


def _itinerary_fallback(state: dict) -> dict:
    """Template fallback — single-city only."""
    start     = datetime.strptime(state["travel_dates"]["start"], "%Y-%m-%d")
    transport = state.get("selected_transport",{})
    hotel     = state.get("selected_accommodation",{})
    activities = state.get("selected_activities",[])
    duration  = state["duration_days"]
    dest      = state["destination"]

    itinerary = [{
        "day_number":1, "date":start.strftime("%Y-%m-%d"),
        "city": dest, "theme":"Travel + Arrival",
        "segments":[
            {"time":"06:00","type":"transport","title":f"Depart {state['origin']}",
             "description":f"{transport.get('operator','Train')} → {dest}",
             "duration_mins":transport.get("duration_mins",360),
             "cost":transport.get("price",0),"notes":"","maps_link":"","booking_link":"","weather_note":""},
            {"time":"14:00","type":"checkin","title":f"Check in — {hotel.get('name','Hotel')}",
             "description":"Check in","duration_mins":60,
             "cost":hotel.get("price_per_night",0),"notes":"","maps_link":"","booking_link":"","weather_note":""},
        ],
        "daily_cost_estimate":transport.get("price",0)+hotel.get("price_per_night",0)+300,
        "highlights":["Arrival"],
    }]
    for d in range(2, duration):
        day_date = (start+timedelta(days=d-1)).strftime("%Y-%m-%d")
        acts = [a for a in activities if a.get("best_day")==d] or activities[:1]
        segs = [{"time":"08:00","type":"meal","title":"Breakfast","description":"",
                 "duration_mins":45,"cost":150,"notes":"","maps_link":"","booking_link":"","weather_note":""}]
        day_cost = 150
        for a in acts[:2]:
            segs.append({"time":"10:00","type":"activity","title":a["name"],
                         "description":a.get("description",""),
                         "duration_mins":int(a.get("duration_hours",2)*60),
                         "cost":a["price"],"notes":"","maps_link":"","booking_link":"","weather_note":""})
            day_cost += a["price"]
        itinerary.append({"day_number":d,"date":day_date,"city":dest,
                          "theme":f"Day {d}","segments":segs,
                          "daily_cost_estimate":day_cost+hotel.get("price_per_night",0),
                          "highlights":[a["name"] for a in acts[:2]]})
    last = (start+timedelta(days=duration-1)).strftime("%Y-%m-%d")
    itinerary.append({"day_number":duration,"date":last,"city":dest,"theme":"Return",
                      "segments":[{"time":"12:00","type":"transport",
                                   "title":f"Return to {state['origin']}",
                                   "description":"Return journey",
                                   "duration_mins":transport.get("duration_mins",360),
                                   "cost":transport.get("price",0),"notes":"",
                                   "maps_link":"","booking_link":"","weather_note":""}],
                      "daily_cost_estimate":transport.get("price",0)+200,
                      "highlights":["Safe return"]})
    # Use projected_total from Step 2 as authoritative cost (same fix as main path)
    projected_total = state.get("projected_total", 0)
    approved        = state.get("budget_breakdown", {})
    daily_sum       = sum(d["daily_cost_estimate"] for d in itinerary)
    total           = projected_total if projected_total > 0 else daily_sum

    return {
        "daily_itinerary": itinerary,
        "final_budget_summary": {
            "travel":          approved.get("travel",      {}).get("allocated", transport.get("price",0)*2),
            "stay":            approved.get("stay",        {}).get("allocated", hotel.get("price_per_night",0)*(duration-1)),
            "food":            approved.get("food",        {}).get("allocated", 450*duration),
            "activities":      approved.get("activities",  {}).get("allocated", sum(a["price"] for a in activities)),
            "local_transport": approved.get("local_transport",{}).get("allocated", 800),
            "buffer":          approved.get("buffer",      {}).get("allocated", 0),
            "estimated_total": total,
            "remaining":       state["budget"] - total,
        },
        "trip_summary": {
            "destination":    dest,
            "duration":       f"{duration} Days",
            "budget":         f"Rs {state['budget']:,}",
            "style":          travel_style,
            "travelers":      state.get("num_travelers",1),
            "dates":          f"{state['travel_dates']['start']} to {state['travel_dates']['end']}",
            "estimated_cost": f"Rs {total:,}",
            "savings":        f"Rs {state['budget']-total:,} remaining",
            "is_multi_city":  False,
            "city_stops":     state.get("city_stops", []),
        },
        "city_itineraries": {dest: list(range(1, duration+1))},
        "current_phase": "itinerary_built",
    }


# ─────────────────────────────────────────────────────────
# LAYER 7: OUTPUTS — pass city_stops to PDF and map
# ─────────────────────────────────────────────────────────

def pdf_generator_agent(state: dict) -> dict:
    print(f"📄 [PDF] Generating...")
    try:
        from app.utils.pdf_generator import generate_pdf_bytes
        pdf_bytes = generate_pdf_bytes(
            trip_summary         = state.get("trip_summary",{}),
            daily_itinerary      = state.get("daily_itinerary",[]),
            final_budget_summary = state.get("final_budget_summary",{}),
        )
        print(f"   ✅ PDF: {len(pdf_bytes):,} bytes")
        return {"pdf_bytes": pdf_bytes}
    except Exception as e:
        print(f"   ⚠️ PDF failed: {e}")
        return {"pdf_bytes": b""}


def map_generator_agent(state: dict) -> dict:
    print(f"🗺️  [Map] Generating...")
    try:
        from app.utils.map_generator import generate_map_html
        html = generate_map_html(
            destination     = state.get("destination",""),
            daily_itinerary = state.get("daily_itinerary",[]),
            city_stops      = state.get("city_stops",[]),
            is_multi_city   = state.get("is_multi_city",False),
        )
        print(f"   ✅ Map generated")
        return {"map_html": html}
    except Exception as e:
        print(f"   ⚠️ Map failed: {e}")
        return {"map_html": "<div style='padding:40px;text-align:center'><h3>Map unavailable</h3></div>"}


def merge_output_node(state: dict) -> dict:
    dest = state.get("destination","")
    print(f"\n✅ COMPLETE: {dest} | {state.get('duration_days')} days")
    return {"current_phase": "complete"}


# ─────────────────────────────────────────────────────────
# LAYER 8: REPLAN + ERROR — unchanged
# ─────────────────────────────────────────────────────────

def replan_agent(state: dict) -> dict:
    instruction = state.get("replan_instruction","").lower()
    if any(w in instruction for w in ["budget","cheaper","cost","cheap","reduce","money"]):
        # Rebuild budget at lower allocation, then itinerary
        scope = ["budget_architect_node","activities_finder","itinerary_architect"]
    elif any(w in instruction for w in ["hotel","stay","hostel","accommodation"]):
        # Re-scout accommodation, rebuild booking cart + itinerary
        scope = ["accommodation_scout","booking_cart_node","itinerary_architect"]
    elif any(w in instruction for w in ["adventure","outdoor","sport","trek","raft","bungee"]):
        # Re-fetch activities with adventure filter, rebuild itinerary
        scope = ["activities_finder","itinerary_architect"]
    elif any(w in instruction for w in ["spiritual","yoga","meditation","temple","ashram","calm"]):
        # Re-fetch activities with spiritual filter, rebuild itinerary
        scope = ["activities_finder","itinerary_architect"]
    else:
        # Default: rebuild activities + itinerary (covers custom instructions too)
        scope = ["activities_finder","itinerary_architect"]
    print(f"   🔄 Replan scope: {scope}")
    return {"replan_scope": scope,
            "replan_count": state.get("replan_count", 0) + 1,
            "current_phase": "replanning"}


def handle_error_node(state: dict) -> dict:
    errors = state.get("errors",[])
    print(f"\n❌ [Error] {errors}")
    return {"awaiting_human":True,"checkpoint_data":{
        "type":"error","message":"Something went wrong. Please try again.","errors":errors}}