"""
main.py — Streamlit UI for AI Travel Planning Agent

KEY RULE: Use `with col:` syntax for all column operations.
Never call col.method() as a bare expression — Streamlit's magic
mode will wrap it with st.write() and display the DeltaGenerator repr.
"""

import sys
from pathlib import Path

# Ensure project root is on path when running: streamlit run app/main.py
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st
import uuid
from langgraph.types import Command

from app.core.state import create_initial_state
from app.core.graph import travel_graph
from app.utils.demo_data import get_demo_state
from app.db import get_trip, list_trips, save_trip

st.set_page_config(page_title="AI Travel Planner", page_icon="🌍", layout="wide")


# ── Session init ──────────────────────────────────────────

def init_session():
    defaults = {
        "thread_id":      None,
        "graph_state":    None,
        "interrupt_data": None,
        "checkpoint_num": 0,
        "planning_done":  False,
        "started":        False,
        "is_demo_mode":   False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Graph helpers ─────────────────────────────────────────

def get_config():
    return {
        "configurable":    {"thread_id": st.session_state["thread_id"]},
        "recursion_limit": 50,
    }


def get_interrupt_from_graph():
    """Read pending interrupt payload from the graph checkpointer."""
    try:
        snap = travel_graph.get_state(get_config())
        if snap and snap.tasks:
            for task in snap.tasks:
                if hasattr(task, "interrupts") and task.interrupts:
                    return task.interrupts[0].value
    except Exception:
        pass
    return None


def get_state_values():
    """Read latest state values from the graph checkpointer."""
    try:
        snap = travel_graph.get_state(get_config())
        if snap:
            return snap.values
    except Exception:
        pass
    return {}


def run_graph(input_data):
    """
    Run or resume the graph.
    Captures state directly from the stream — never reads stale
    checkpointer data from a previous thread.
    Returns (state_dict, interrupt_payload_or_None).
    """
    latest_state = {}
    try:
        for chunk in travel_graph.stream(
            input_data,
            config=get_config(),
            stream_mode="values",
        ):
            # Each chunk IS the full state at that point — keep the last one
            if isinstance(chunk, dict):
                latest_state = chunk
    except Exception as e:
        err_type = type(e).__name__
        if "Interrupt" not in err_type and "interrupt" not in err_type.lower():
            st.error(f"Graph error: {e}")

    # Fall back to checkpointer only if stream gave us nothing
    if latest_state:
        # Merge: start from previous session state so no fields are lost
        # across checkpoint boundaries, then overlay latest stream values
        prev = st.session_state.get("graph_state") or {}
        state = {**prev, **latest_state}
    else:
        state = get_state_values()

    interrupt_data = get_interrupt_from_graph()
    return state, interrupt_data


# ── Helpers ───────────────────────────────────────────────

def checkpoint_num_from_interrupt(interrupt_data):
    if not interrupt_data:
        return 0
    itype = interrupt_data.get("type", "")
    if itype == "plan_selection":
        return 1
    if itype == "budget_approval":
        return 2
    if itype == "booking_confirmation":
        return 3
    return 0


# ── Header ────────────────────────────────────────────────

def render_header():
    is_demo = st.session_state.get("is_demo_mode", False)
    demo_badge = (
        " &nbsp;<span style='background:#F59E0B;color:#000;font-size:12px;"
        "font-weight:700;padding:3px 10px;border-radius:20px;vertical-align:middle'>"
        "🎬 DEMO MODE</span>"
        if is_demo else ""
    )
    st.markdown(f"""
    <div style='text-align:center;padding:2rem 0 1rem'>
      <h1 style='font-size:2.6rem;font-weight:800;margin:0'>
        🌍 AI Travel Planning Agent{demo_badge}
      </h1>
      <p style='color:#9CA3AF;font-size:1.05rem;margin-top:.4rem'>
        Multi-agent LangGraph system · GPT-4o powered · 9 parallel agents
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Agent pipeline visualisation — always visible
    st.markdown("""
    <div style='background:#111827;border:1px solid #1F2937;border-radius:12px;
                padding:14px 20px;margin-bottom:1.2rem'>
      <div style='font-size:11px;font-weight:600;color:#6B7280;
                  letter-spacing:.08em;margin-bottom:10px'>AGENT PIPELINE</div>
      <div style='display:flex;align-items:center;flex-wrap:wrap;gap:6px;font-size:12px'>
        <span style='background:#1E3A5F;color:#93C5FD;padding:4px 10px;border-radius:6px'>🧠 Intent Parser</span>
        <span style='color:#374151'>→</span>
        <span style='background:#1A2F1A;color:#86EFAC;padding:4px 10px;border-radius:6px'>🔍 Research</span>
        <span style='background:#1A2F1A;color:#86EFAC;padding:4px 10px;border-radius:6px'>🌤️ Weather</span>
        <span style='background:#1A2F1A;color:#86EFAC;padding:4px 10px;border-radius:6px'>🚌 Transport</span>
        <span style='background:#1A2F1A;color:#86EFAC;padding:4px 10px;border-radius:6px'>🏨 Hotels</span>
        <span style='font-size:10px;color:#4B5563;padding:4px 6px'>parallel</span>
        <span style='color:#374151'>→</span>
        <span style='background:#2D1B4E;color:#C4B5FD;padding:4px 10px;border-radius:6px'>✨ Options Builder</span>
        <span style='color:#374151'>→</span>
        <span style='background:#2D1B4E;color:#C4B5FD;padding:4px 10px;border-radius:6px'>💰 Budget Architect</span>
        <span style='color:#374151'>→</span>
        <span style='background:#2D1B4E;color:#C4B5FD;padding:4px 10px;border-radius:6px'>🗓️ Itinerary</span>
        <span style='color:#374151'>→</span>
        <span style='background:#1E3A2A;color:#6EE7B7;padding:4px 10px;border-radius:6px'>📄 PDF + 🗺️ Map</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Input screen ──────────────────────────────────────────

def render_input():
    st.markdown("""
    <div style='background:#111827;border:1px solid #1F2937;border-radius:12px;
                padding:1.4rem 1.6rem 1rem;margin-bottom:1rem'>
      <div style='font-size:1.2rem;font-weight:700;margin-bottom:.3rem'>✍️ Describe Your Trip</div>
      <div style='color:#6B7280;font-size:.85rem'>
        Include: destination · origin · budget · duration · travel style
      </div>
    </div>
    """, unsafe_allow_html=True)

    user_input = st.text_area(
        "Your travel request:",
        placeholder="Plan a 4-day solo trip to Rishikesh under ₹15,000 from Delhi...",
        height=100,
        label_visibility="collapsed",
        key="travel_request",
    )

    col_plan, col_demo = st.columns(2)
    with col_plan:
        clicked = st.button(
            "🚀 Start Planning",
            type="primary",
            use_container_width=True,
            disabled=not user_input.strip(),
        )
    with col_demo:
        demo_clicked = st.button(
            "🎬 Demo Mode — instant preview (no API calls)",
            use_container_width=True,
            help="Load a pre-built Rishikesh trip instantly — no API calls. Perfect for live demos.",
        )

    if demo_clicked:
        return "__DEMO__"
    if clicked and user_input.strip():
        return user_input.strip()
    return None


# ── Checkpoint 1 — Plan options ───────────────────────────

def render_checkpoint_1(interrupt_data: dict):
    st.markdown("---")

    col_title, col_badge = st.columns([5, 1])
    with col_title:
        st.markdown("## 📋 Step 1 — Choose Your Trip Style")
    with col_badge:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🤖 Powered by GPT-4o")

    state = st.session_state.get("graph_state") or {}

    # ── Multi-city route banner ──────────────────────
    is_multi   = interrupt_data.get("is_multi_city", False)
    city_stops = interrupt_data.get("city_stops", [])
    if is_multi and city_stops:
        origin = state.get("origin", "Origin")
        parts  = [f"**{origin}**"]
        for s in city_stops:
            parts.append(f"→ **{s['city']}** _{s['days']}d_")
        parts.append(f"→ **{origin}**")
        st.info("🗺️ Multi-city route: " + "  ".join(parts))
        stop_cols = st.columns(len(city_stops))
        for stop, col in zip(city_stops, stop_cols):
            with col:
                st.metric(stop["city"], f"{stop['days']} days",
                          f"{stop['transport_from_prev']} · {stop['transport_time_hrs']}hrs")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Destination", state.get("destination", ""))
        with c2:
            st.metric("Budget", f"₹{state.get('budget', 0):,}")
        with c3:
            st.metric("Duration", f"{state.get('duration_days', 0)} days")

    for a in interrupt_data.get("assumptions", []):
        st.warning(f"⚠️ **{a['field'].title()}** assumed as '{a['assumed_value']}' — {a['reason']}")

    weather = interrupt_data.get("weather_summary", "")
    if weather:
        st.info(f"🌤️ {weather}")

    st.markdown("### 🗺️ Pick a Trip Style")
    options     = interrupt_data.get("options", {})
    recommended = interrupt_data.get("recommendation", "A")
    col_a, col_b, col_c = st.columns(3)
    chosen = None

    for key, col in [("A", col_a), ("B", col_b), ("C", col_c)]:
        opt    = options.get(key, {})
        is_rec = key == recommended
        with col:
            if is_rec:
                st.success("⭐ RECOMMENDED")
            st.markdown(f"**Option {key} — {opt.get('style_name', '')}**")
            st.caption(opt.get("style_tag", ""))
            st.markdown(f"💰 **~₹{opt.get('estimated_total', 0):,}**")
            for h in opt.get("highlights", [])[:3]:
                st.markdown(f"• {h}")
            with st.expander("Why this works"):
                st.write(opt.get("why_this_works", ""))
                if opt.get("trade_offs"):
                    st.warning(opt["trade_offs"])
            if st.button(f"Select Option {key}", key=f"opt_{key}",
                         type="primary" if is_rec else "secondary",
                         use_container_width=True):
                chosen = key

    return {"chosen_option": chosen} if chosen else None

# ── Checkpoint 2 — Budget ─────────────────────────────────

def render_checkpoint_2(interrupt_data: dict):
    st.markdown("---")
    st.markdown("## 💰 Step 2 — Budget Allocation")

    breakdown = interrupt_data.get("breakdown", {})
    budget    = interrupt_data.get("budget", 0)
    projected = interrupt_data.get("projected_total", 0)

    for w in interrupt_data.get("warnings", []):
        st.warning(w)

    # Clear explanation so user understands what these numbers mean
    remaining_after_trip = max(budget - projected, 0)
    colour = "#22C55E" if budget >= projected else "#EF4444"
    st.markdown(f"""
    <div style='background:#111827;border:1px solid #1F2937;border-radius:10px;
                padding:12px 16px;margin-bottom:1rem;display:flex;gap:2rem'>
      <div>
        <div style='color:#6B7280;font-size:11px;font-weight:600'>YOUR BUDGET</div>
        <div style='font-size:1.3rem;font-weight:700'>₹{budget:,}</div>
      </div>
      <div>
        <div style='color:#6B7280;font-size:11px;font-weight:600'>FULL TRIP ESTIMATE</div>
        <div style='font-size:1.3rem;font-weight:700'>₹{projected:,}</div>
      </div>
      <div>
        <div style='color:#6B7280;font-size:11px;font-weight:600'>REMAINING</div>
        <div style='font-size:1.3rem;font-weight:700;color:{colour}'>₹{remaining_after_trip:,}</div>
      </div>
    </div>
    <div style='color:#6B7280;font-size:12px;margin-bottom:1rem'>
      ✏️ Drag sliders to reallocate spend across categories.
      The total below updates live — keep it under your budget.
    </div>
    """, unsafe_allow_html=True)

    st.progress(min(projected / budget, 1.0) if budget else 0)

    icons = {
        "travel": "✈️", "stay": "🏨", "food": "🍛",
        "activities": "🎯", "local_transport": "🛺", "buffer": "🛡️",
    }

    updated = {}
    total   = 0

    slider_cap = max(budget, projected)
    for cat, data in breakdown.items():
        c1, c2, c3 = st.columns([2, 3, 1])
        with c1:
            st.markdown(f"**{icons.get(cat, '💰')} {cat.replace('_', ' ').title()}**")
            st.caption(data.get("notes", ""))
        with c2:
            allocated = data.get("allocated", 0)
            val = st.slider(
                f"Budget for {cat}",
                min_value=0,
                max_value=max(slider_cap, allocated),
                value=allocated,
                step=100,
                key=f"sl_{cat}",
                label_visibility="collapsed",
            )
        with c3:
            st.markdown(f"**₹{val:,}**")
        updated[cat] = {**data, "allocated": val}
        total += val

    st.markdown("---")
    # Show live totals — this is the number that flows into every future step
    over = total > budget
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Your Budget", f"₹{budget:,}")
    with col2:
        st.metric("Allocated (full trip)", f"₹{total:,}",
                  delta=f"₹{total - projected:,} vs estimate",
                  delta_color="inverse")
    with col3:
        rem = max(budget - total, 0)
        st.metric("Remaining", f"₹{rem:,}",
                  delta="over budget" if over else "within budget",
                  delta_color="inverse" if over else "normal")

    if over:
        st.warning(
            f"⚠️ Allocated ₹{total:,} exceeds your budget ₹{budget:,} by "
            f"₹{total-budget:,}. You can reduce sliders or approve as-is "
            f"(your budget will be updated to ₹{total:,})."
        )

    col_l, col_btn, col_r = st.columns([1, 2, 1])
    with col_btn:
        if st.button("✅ Approve Budget", type="primary",
                     use_container_width=True):
            return {"approved_budget": updated}
    return None


# ── Checkpoint 3 — Booking cart ───────────────────────────

def _source_badge(source: str) -> str:
    """Return coloured HTML badge for data source."""
    colors = {
        "IRCTC":     ("#0369A1", "#DBEAFE"),
        "Amadeus":   ("#7C3AED", "#EDE9FE"),
        "Hotelbeds": ("#0D9488", "#CCFBF1"),
        "GPT-4o":    ("#EA580C", "#FFF7ED"),
    }
    fg, bg = colors.get(source, ("#64748B", "#F1F5F9"))
    return (f'<span style="background:{bg};color:{fg};font-size:10px;'
            f'font-weight:bold;padding:2px 7px;border-radius:10px;'
            f'margin-left:6px">{source}</span>')


def render_checkpoint_3(interrupt_data: dict):
    st.markdown("---")
    st.markdown("## 🛒 Step 3 — Confirm Bookings")

    cart               = interrupt_data.get("cart", [])
    cart_total         = interrupt_data.get("cart_total", 0)
    full_trip_estimate = interrupt_data.get("full_trip_estimate", 0)
    budget             = interrupt_data.get("budget", 0)

    # Use full_trip_estimate (approved in Step 2) as the real trip cost.
    # cart_total only covers transport + hotel + activities — it deliberately
    # excludes food, local transport and buffer (can't pre-book those).
    display_total   = full_trip_estimate if full_trip_estimate > 0 else cart_total
    remaining_total = max(budget - display_total, 0)
    colour_total    = "#22C55E" if budget >= display_total else "#EF4444"

    st.markdown(f"""
    <div style='background:#111827;border:1px solid #1F2937;border-radius:10px;
                padding:12px 16px;margin-bottom:.8rem;display:flex;gap:2rem;flex-wrap:wrap'>
      <div>
        <div style='color:#6B7280;font-size:11px;font-weight:600'>FULL TRIP COST</div>
        <div style='font-size:1.3rem;font-weight:700'>₹{display_total:,}</div>
        <div style='color:#6B7280;font-size:11px'>approved in Step 2</div>
      </div>
      <div>
        <div style='color:#6B7280;font-size:11px;font-weight:600'>TO BOOK NOW</div>
        <div style='font-size:1.3rem;font-weight:700'>₹{cart_total:,}</div>
        <div style='color:#6B7280;font-size:11px'>transport + hotel + activities</div>
      </div>
      <div>
        <div style='color:#6B7280;font-size:11px;font-weight:600'>BUDGET REMAINING</div>
        <div style='font-size:1.3rem;font-weight:700;color:{colour_total}'>₹{remaining_total:,}</div>
        <div style='color:#6B7280;font-size:11px'>food + local travel in cash</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Source summary badges
    sources = list(dict.fromkeys(
        item.get("source","") for item in cart if item.get("source")
    ))
    if sources:
        badge_html = "Data sources: " + " ".join(_source_badge(s) for s in sources)
        st.markdown(badge_html, unsafe_allow_html=True)

    for section_label, cat_key in [
        ("🚆 Travel",    "transport"),
        ("🏨 Stay",      "stay"),
        ("🎯 Activities","activity"),
    ]:
        items = [i for i in cart if i["category"] == cat_key]
        if not items:
            continue
        st.markdown(f"### {section_label}")
        for item in items:
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                source_html = _source_badge(item["source"]) if item.get("source") else ""
                st.markdown(
                    f"**{item['name']}**{source_html}",
                    unsafe_allow_html=True,
                )
                st.caption(item["details"])
                if item.get("notes"):
                    st.caption(f"💡 {item['notes']}")
            with c2:
                st.markdown(f"₹{item['cost']:,}")
            with c3:
                if item.get("booking_link"):
                    st.link_button("Book →", item["booking_link"])

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Confirm All Bookings", type="primary", use_container_width=True):
            return {"confirmed": True}
    with c2:
        if st.button("↩️ Modify Plan", use_container_width=True):
            return {"confirmed": False}
    return None


# ── Final output ──────────────────────────────────────────

def render_final_output(state: dict):
    is_demo = st.session_state.get("is_demo_mode", False)

    # ── 5D: Show error state if something went wrong ──────
    errors = state.get("errors", [])
    if errors and state.get("current_phase") != "complete":
        st.markdown("""
        <div style='background:#1F0A0A;border:1px solid #7F1D1D;border-radius:12px;padding:1.2rem'>
          <div style='color:#FCA5A5;font-size:1.1rem;font-weight:700'>⚠️ Something went wrong</div>
          <div style='color:#9CA3AF;margin-top:.4rem;font-size:.9rem'>
            The planner hit an issue. You can retry or start fresh.
          </div>
        </div>
        """, unsafe_allow_html=True)
        for e in errors:
            st.caption(f"• {e}")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Retry", type="primary", use_container_width=True):
                user_msg = state.get("user_message", "")
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.session_state["thread_id"]  = str(uuid.uuid4())
                st.session_state["started"]    = True
                with st.spinner("Retrying..."):
                    s, interrupt = run_graph(create_initial_state(user_msg))
                st.session_state["graph_state"]    = s
                st.session_state["interrupt_data"] = interrupt
                st.session_state["checkpoint_num"] = checkpoint_num_from_interrupt(interrupt)
                st.rerun()
        with c2:
            if st.button("🏠 Start Fresh", use_container_width=True):
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()
        return

    # ── Persistent replan feedback (survives st.rerun) ───
    feedback = st.session_state.pop("replan_feedback", None)
    if feedback:
        if feedback["type"] == "success":
            st.success(feedback["message"])
        else:
            st.error(feedback["message"])

    # ── 5A: Upgraded success banner ───────────────────────
    summary    = state.get("trip_summary", {})
    dest       = summary.get("destination", state.get("destination", ""))
    cost       = summary.get("estimated_cost", "")
    savings    = summary.get("savings", "")
    demo_note  = " &nbsp;<span style='background:#F59E0B;color:#000;font-size:11px;font-weight:700;padding:2px 8px;border-radius:10px'>DEMO</span>" if is_demo else ""

    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#064E3B,#065F46);
                border:1px solid #047857;border-radius:14px;
                padding:1.4rem 1.8rem;margin-bottom:1.2rem'>
      <div style='font-size:1.4rem;font-weight:800;color:#ECFDF5'>
        ✅ Your {dest} Trip Plan is Ready{demo_note}
      </div>
      <div style='color:#A7F3D0;font-size:.9rem;margin-top:.3rem'>
        {cost} estimated &nbsp;·&nbsp; {savings} &nbsp;·&nbsp;
        Powered by GPT-4o + {len(state.get("daily_itinerary", []))} agent steps
      </div>
    </div>
    """, unsafe_allow_html=True)

    summary    = state.get("trip_summary", {})
    itinerary  = state.get("daily_itinerary", [])
    bsum       = state.get("final_budget_summary", {})
    is_multi   = summary.get("is_multi_city", False)
    city_stops = summary.get("city_stops", [])

    # ── Trip summary metrics ───────────────────────────────
    st.markdown("## 📍 Trip Summary")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Destination",    summary.get("destination", ""))
    with c2: st.metric("Duration",       summary.get("duration", ""))
    with c3: st.metric("Estimated Cost", summary.get("estimated_cost", ""))
    with c4: st.metric("Savings",        summary.get("savings", ""))

    # ── Multi-city route strip ─────────────────────────────
    if is_multi and city_stops:
        st.markdown("#### 🗺️ Route")
        n_cols = len(city_stops) * 2 - 1
        city_cols = st.columns(n_cols)
        for i, stop in enumerate(city_stops):
            with city_cols[i * 2]:
                st.info(f"**{stop['city']}**\n\n{stop['days']} days")
            if i < len(city_stops) - 1:
                arrow_html = (
                    f"<div style='text-align:center;padding-top:18px;color:#64748B'>"
                    f"→<br><small>{city_stops[i+1]['transport_from_prev']}<br>"
                    f"{city_stops[i+1]['transport_time_hrs']}h</small></div>"
                )
                with city_cols[i * 2 + 1]:
                    st.markdown(arrow_html, unsafe_allow_html=True)

    # ── Day-by-day itinerary ───────────────────────────────
    st.markdown("## 🗓️ Day-by-Day Itinerary")
    colors    = ["🔵", "🟠", "🟢", "🟣", "🔴", "🟡"]
    seg_icons = {
        "transport": "🚌", "checkin": "🏨",
        "activity": "🎯", "meal": "🍛", "free_time": "🌅",
    }

    if is_multi and city_stops:
        # Group days by city using the "city" field on each day
        city_day_map = {}
        for day in itinerary:
            city = day.get("city", "")
            city_day_map.setdefault(city, []).append(day)

        for stop in city_stops:
            city      = stop["city"]
            days_here = city_day_map.get(city, [])
            if not days_here:
                continue
            st.markdown(f"### 📍 {city}")
            _render_days(days_here, colors, seg_icons)
    else:
        _render_days(itinerary, colors, seg_icons)

    # ── Interactive Folium Map ─────────────────────────────
    map_html = state.get("map_html", "")
    if map_html and "<div" in map_html:
        st.markdown("## 🗺️ Interactive Route Map")
        if is_multi:
            st.caption("City-colored markers · Thick lines show inter-city connections")
        else:
            st.caption("Click markers for details · Dashed lines show each day's route")
        import streamlit.components.v1 as components
        components.html(map_html, height=500, scrolling=False)

    # ── Local tips ────────────────────────────────────────
    local_tips = summary.get("local_tips", [])
    if local_tips:
        st.markdown("## 💡 Local Tips")
        for tip in local_tips:
            st.info(f"💡 {tip}")

    # ── Budget breakdown ──────────────────────────────────
    st.markdown("## 💰 Budget Breakdown")
    if bsum:
        for lbl, key in [
            ("✈️ Travel", "travel"), ("🏨 Stay", "stay"),
            ("🍛 Food", "food"), ("🎯 Activities", "activities"),
            ("🛺 Local Transport", "local_transport"),
        ]:
            c1, c2 = st.columns([3, 1])
            with c1: st.markdown(lbl)
            with c2: st.markdown(f"₹{bsum.get(key, 0):,}")
        st.markdown("---")
        b = state.get("budget", 0)
        t = bsum.get("estimated_total", 0)
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Budget",    f"₹{b:,}")
        with c2: st.metric("Total",     f"₹{t:,}")
        with c3: st.metric("Remaining", f"₹{max(b - t, 0):,}")

    # ── PDF Download ──────────────────────────────────────
    st.markdown("---")
    pdf_bytes = state.get("pdf_bytes", b"")
    raw_dest  = summary.get("destination", "trip")
    dest_name = raw_dest.lower().replace(" ", "_").replace("→", "").replace(",", "")[:30]

    c1, c2 = st.columns(2)
    with c1:
        if pdf_bytes:
            st.download_button(
                label="📥 Download PDF Itinerary",
                data=pdf_bytes,
                file_name=f"{dest_name}_itinerary.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
        else:
            st.button("📥 PDF (generating...)", disabled=True, use_container_width=True)
    with c2:
        if st.button("🏠 Plan Another Trip", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    st.caption("🤖 Itinerary by GPT-4o · Map geocoded by GPT-4o-mini · Prices are estimates")

    # ── 5C: Replan quick-actions ──────────────────────────
    if not st.session_state.get("is_demo_mode"):
        st.markdown("---")
        st.markdown("### 🔄 Tweak Your Plan")
        st.caption("Instantly regenerate specific parts of your trip without starting over.")

        # Store pending replan instruction
        if "replan_instruction" not in st.session_state:
            st.session_state["replan_instruction"] = ""

        col1, col2, col3, col4 = st.columns(4)
        replan_actions = {
            "💸 Make it cheaper":    "Reduce overall costs — find cheaper accommodation and cut activity spend by 20%",
            "🏨 Better hotel":       "Find a higher-rated hotel or better-located accommodation option",
            "🏕️ More adventure":     "Replace cultural activities with more adventure and outdoor activities",
            "🧘 More spiritual":     "Replace adventure activities with yoga, meditation and temple visits",
        }
        clicked_action = None
        for col, (label, instruction) in zip([col1, col2, col3, col4], replan_actions.items()):
            with col:
                if st.button(label, use_container_width=True):
                    clicked_action = instruction

        # Custom replan text input
        custom = st.text_input(
            "Or describe your own change:",
            placeholder="e.g. Add a day trip to a nearby waterfall...",
            key="custom_replan_input",
        )
        c_apply, _ = st.columns([1, 3])
        with c_apply:
            if st.button("Apply Change →", type="primary") and custom.strip():
                clicked_action = custom.strip()

        if clicked_action:
            with st.spinner(f"🔄 GPT-4o is updating your plan..."):
                try:
                    from app.agents import (
                        replan_agent,
                        accommodation_scout_agent,
                        activities_finder_agent,
                        budget_architect_agent,
                        booking_cart_agent,
                        itinerary_architect_agent,
                        pdf_generator_agent,
                        map_generator_agent,
                    )

                    updated_state = {**state,
                                     "replan_instruction": clicked_action,
                                     "replan_requested":   True}
                    replan_result = replan_agent(updated_state)
                    updated_state.update(replan_result)

                    scope = updated_state.get("replan_scope", [])
                    ran_accommodation = False
                    ran_activities = False

                    # Step 1: re-fetch accommodation if "Better hotel" etc.
                    if "accommodation_scout" in scope:
                        acc = accommodation_scout_agent(updated_state)
                        updated_state.update(acc)
                        ran_accommodation = True

                    # Step 2: re-fetch activities if "More adventure" / "More spiritual" etc.
                    if "activities_finder" in scope:
                        acts = activities_finder_agent(updated_state)
                        updated_state.update(acts)
                        ran_activities = True

                    # Step 3: rebuild budget if "make it cheaper" etc.
                    if "budget_architect_node" in scope:
                        bgt = budget_architect_agent(updated_state)
                        updated_state.update(bgt)
                        updated_state["approved_budget"] = updated_state.get("budget_breakdown", {})
                        updated_state["projected_total"] = updated_state.get("projected_total",
                                                                state.get("projected_total", 0))

                    # Step 4: rebuild cart when accommodation, activities, or cart in scope
                    if ("booking_cart_node" in scope or ran_accommodation or ran_activities):
                        cart_result = booking_cart_agent(updated_state)
                        updated_state.update(cart_result)

                    # Step 5: rebuild itinerary, PDF, map
                    itin = itinerary_architect_agent(updated_state)
                    updated_state.update(itin)
                    pdf = pdf_generator_agent(updated_state)
                    updated_state.update(pdf)
                    mp = map_generator_agent(updated_state)
                    updated_state.update(mp)
                    updated_state["current_phase"] = "complete"

                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    # Store error so it survives st.rerun()
                    st.session_state["_replan_error"] = f"⚠️ Replan error: {e}"
                    print(f"Replan exception:\n{tb}")
                    updated_state = state  # fall back to original plan on error

            st.session_state["graph_state"]    = updated_state
            st.session_state["planning_done"]  = True
            # Store feedback in session state so it PERSISTS across st.rerun()
            st.session_state["replan_feedback"] = {
                "type":    "error" if updated_state is state else "success",
                "message": st.session_state.get("_replan_error", f"✅ Plan updated: {clicked_action[:60]}"),
            }
            st.session_state.pop("_replan_error", None)
            st.rerun()


def _render_days(days: list, colors: list, seg_icons: dict):
    """Render a list of day expanders — shared by single and multi-city."""
    for day in days:
        color    = colors[(day["day_number"] - 1) % len(colors)]
        city_tag = f" · {day['city']}" if day.get("city") else ""
        day_total = day["daily_cost_estimate"]
        with st.expander(
            f"{color} Day {day['day_number']}{city_tag} — {day['theme']} "
            f"(~₹{day_total:,})",
            expanded=(day["day_number"] == 1),
        ):
            # ── Segments (what you actually do) ──────────────────────
            seg_sum = 0
            for seg in day.get("segments", []):
                icon = seg_icons.get(seg["type"], "📍")
                c1, c2, c3 = st.columns([1, 4, 1])
                with c1: st.markdown(f"**{seg['time']}**")
                with c2:
                    st.markdown(f"{icon} **{seg['title']}**")
                    st.caption(seg["description"])
                    if seg.get("notes"):
                        st.caption(f"💡 {seg['notes']}")
                with c3:
                    seg_cost = seg.get("cost", 0)
                    seg_sum += seg_cost
                    cost = f"₹{seg_cost:,}" if seg_cost > 0 else "Free"
                    st.markdown(cost)
                    if seg.get("maps_link"):
                        st.link_button("📍 Map", seg["maps_link"])

            # ── Budget allocation breakdown for this day ──────────────
            # Shows the "hidden" costs (stay, transport proration, buffer)
            # so the header total is explained and makes sense.
            overhead = day_total - seg_sum
            if overhead > 50:  # only show if meaningful
                st.markdown(
                    f"<div style='margin-top:10px;padding:8px 12px;"
                    f"background:#111827;border-radius:8px;border-left:3px solid #374151'>"
                    f"<span style='color:#6B7280;font-size:11px;font-weight:600'>"
                    f"DAILY BUDGET ALLOCATION</span><br>"
                    f"<span style='color:#9CA3AF;font-size:12px'>"
                    f"Activities & meals shown above: "
                    f"<b style='color:#D1D5DB'>₹{seg_sum:,}</b>"
                    f" &nbsp;+&nbsp; "
                    f"Prorated stay, transport & buffer: "
                    f"<b style='color:#D1D5DB'>₹{overhead:,}</b>"
                    f" &nbsp;=&nbsp; "
                    f"<b style='color:#F9FAFB'>Day total ₹{day_total:,}</b>"
                    f"</span></div>",
                    unsafe_allow_html=True,
                )


# ── MAIN ──────────────────────────────────────────────────

def main():
    init_session()
    render_header()

    # ── Sidebar ────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 🌍 Travel Planner")
        st.markdown("---")

        if st.button("🏠 Plan New Trip", use_container_width=True, type="primary"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        if st.button("🎬 Load Demo", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.session_state["thread_id"]     = str(uuid.uuid4())
            st.session_state["started"]       = True
            st.session_state["is_demo_mode"]  = True
            st.session_state["planning_done"] = True
            st.session_state["graph_state"]   = get_demo_state()
            st.rerun()

        # Trip history (when DB is configured)
        try:
            recent = list_trips(limit=10)
            if recent:
                st.markdown("---")
                with st.expander("📁 Trip history", expanded=False):
                    for t in recent:
                        dest = t.get("destination", "Unknown")
                        updated = t.get("updated_at") or t.get("created_at")
                        if hasattr(updated, "strftime"):
                            date_str = updated.strftime("%b %d, %Y")
                        else:
                            date_str = str(updated)[:10]
                        tid = t.get("id")
                        if st.button(f"Load: {dest} ({date_str})", key=f"load_trip_{tid}", use_container_width=True):
                            loaded = get_trip(tid)
                            if loaded:
                                for k in list(st.session_state.keys()):
                                    del st.session_state[k]
                                st.session_state["thread_id"]    = loaded.get("thread_id") or str(uuid.uuid4())
                                st.session_state["started"]     = True
                                st.session_state["planning_done"] = True
                                st.session_state["graph_state"] = loaded
                                st.rerun()
        except Exception:
            pass

        st.markdown("---")
        state = st.session_state.get("graph_state") or {}
        dest  = state.get("destination", "")
        phase = state.get("current_phase", "")
        if dest:
            st.markdown(f"**Destination:** {dest}")
        if phase:
            phase_labels = {
                "intent_parsed":    "✅ Intent parsed",
                "research_merged":  "✅ Research complete",
                "options_built":    "✅ Options ready",
                "option_selected":  "✅ Option selected",
                "budget_approved":  "✅ Budget approved",
                "bookings_confirmed": "✅ Bookings confirmed",
                "itinerary_built":  "✅ Itinerary built",
                "complete":         "✅ Plan complete",
            }
            st.caption(phase_labels.get(phase, f"⏳ {phase}"))

        st.markdown("---")
        st.markdown("**Built with:**")
        st.caption("🔗 LangGraph · Parallel agents")
        st.caption("🤖 GPT-4o · Smart generation")
        st.caption("🌤️ OpenWeatherMap · Real weather")
        st.caption("🔍 Tavily · Live research")
        st.caption("📍 Google Places · Activities")

        with st.expander("🔧 Debug"):
            st.json({
                "demo":        st.session_state.get("is_demo_mode"),
                "checkpoint":  st.session_state.get("checkpoint_num"),
                "done":        st.session_state.get("planning_done"),
                "phase":       phase,
                "destination": dest,
            })

        # ── Not started: show input ────────────────────────────
    if not st.session_state["started"]:
        user_input = render_input()
        if user_input == "__DEMO__":
            # 5B: Demo mode — load pre-built state instantly, skip all API calls
            st.session_state["thread_id"]    = str(uuid.uuid4())
            st.session_state["started"]      = True
            st.session_state["is_demo_mode"] = True
            st.session_state["planning_done"] = True
            st.session_state["graph_state"]  = get_demo_state()
            st.rerun()
        elif user_input:
            fresh_tid = str(uuid.uuid4())
            st.session_state["thread_id"]    = fresh_tid
            st.session_state["started"]      = True
            st.session_state["is_demo_mode"] = False
            with st.spinner("🤖 GPT-4o is parsing your request and preparing personalised options..."):
                state, interrupt_data = run_graph(create_initial_state(user_input))
            st.session_state["graph_state"]    = state
            st.session_state["interrupt_data"] = interrupt_data
            st.session_state["checkpoint_num"] = checkpoint_num_from_interrupt(interrupt_data)
            st.rerun()
        return

    # ── Planning done: show final output ──────────────────
    if st.session_state["planning_done"]:
        render_final_output(st.session_state["graph_state"])
        return

    # ── At a checkpoint ───────────────────────────────────
    interrupt_data = st.session_state.get("interrupt_data")
    checkpoint     = st.session_state.get("checkpoint_num", 0)

    if not interrupt_data:
        st.info("⏳ Processing...")
        return

    response = None
    if checkpoint == 1:
        response = render_checkpoint_1(interrupt_data)
    elif checkpoint == 2:
        response = render_checkpoint_2(interrupt_data)
    elif checkpoint == 3:
        response = render_checkpoint_3(interrupt_data)

    if response:
        # Checkpoint 3 "Modify Plan" — start a fresh graph thread so the
        # workflow properly hits checkpoints 1 → 2 → 3 again.  Simply
        # resetting the UI to show CP1 doesn't work because the old thread
        # is still paused at the CP3 interrupt; Command(resume=...) would
        # feed the CP1 response into CP3 and skip straight to the itinerary.
        if checkpoint == 3 and not response.get("confirmed", True):
            old_state = st.session_state.get("graph_state") or {}
            user_msg = old_state.get("user_message", "")
            if not user_msg:
                st.error("Cannot modify: original request not found. Please start a new plan.")
                return

            fresh_tid = str(uuid.uuid4())
            st.session_state["thread_id"] = fresh_tid
            with st.spinner("🔄 Re-generating plan options — this may take a moment..."):
                new_state, new_interrupt = run_graph(create_initial_state(user_msg))
            st.session_state["graph_state"]    = new_state
            st.session_state["interrupt_data"] = new_interrupt
            st.session_state["checkpoint_num"] = checkpoint_num_from_interrupt(new_interrupt)
            st.rerun()
            return

        msgs = {
            1: "🤖 GPT-4o building smart budget breakdown...",
            2: "🛒 Assembling booking cart...",
            3: "🤖 GPT-4o writing day-by-day itinerary...",
        }
        # 5D: wrap in try/except so a crash shows a retry UI instead of a blank page
        try:
            with st.spinner(msgs.get(checkpoint, "Processing...")):
                state, next_interrupt = run_graph(Command(resume=response))
            st.session_state["graph_state"] = state
            if next_interrupt:
                st.session_state["interrupt_data"] = next_interrupt
                st.session_state["checkpoint_num"] = checkpoint_num_from_interrupt(next_interrupt)
            else:
                st.session_state["interrupt_data"] = None
                st.session_state["planning_done"]  = True
                # Persist trip history when plan completes (skip in demo mode)
                if not st.session_state.get("is_demo_mode") and state.get("current_phase") == "complete":
                    try:
                        save_trip(st.session_state.get("thread_id"), state)
                    except Exception:
                        pass
        except Exception as e:
            # Surface the error in the UI with a retry option
            current_state = st.session_state.get("graph_state") or {}
            current_state["errors"] = current_state.get("errors", []) + [str(e)]
            st.session_state["graph_state"]   = current_state
            st.session_state["planning_done"] = True  # go to final output error view
        st.rerun()


main()