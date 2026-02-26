# Design Document — AI Travel Planning Agent

## Table of Contents

1. [Why LangGraph](#1-why-langgraph)
2. [Shared State Architecture](#2-shared-state-architecture)
3. [Real-Time Data Handling](#3-real-time-data-handling)
4. [Budget Optimization Strategy](#4-budget-optimization-strategy)
5. [Why This Architecture](#5-why-this-architecture)
6. [Agent Roles and Collaboration](#6-agent-roles-and-collaboration)

---

## 1. Why LangGraph

We evaluated three leading multi-agent frameworks before settling on LangGraph.

### Framework Comparison

| Criterion | LangGraph | CrewAI | AutoGen |
|---|---|---|---|
| **Execution model** | Explicit state graph with parallel edges and conditional routing | Sequential task delegation via role-based crew | Conversational agent-to-agent message passing |
| **Parallel execution** | Native — `add_edge(A, B)` + `add_edge(A, C)` fans out; merge node waits for all | Not native — sequential by default; async workaround possible | Not native — conversation is inherently serial |
| **Human-in-the-loop** | First-class `interrupt()` pauses the graph; `Command(resume=...)` continues with user data | Requires custom callback injection; no built-in pause/resume | `human_input_mode` exists but blocks the entire agent loop |
| **State management** | Typed `StateGraph` with annotated reducers — each field declares its merge strategy | Shared memory via `CrewOutput`; no field-level conflict resolution | Agents pass messages; shared state needs external store |
| **Checkpointing** | Built-in `MemorySaver` (or any checkpointer) — graph resumes from exact pause point | Manual persistence | Manual persistence |
| **Determinism** | Graph edges are explicit and inspectable — same input, same execution path (LLM aside) | Depends on agent delegation decisions at runtime | Conversation flow varies with LLM responses |
| **Debuggability** | Graph can be visualized; each node's input/output is the full typed state | Crew logs exist but execution path is implicit | Chat logs only |

### Why LangGraph Won

**1. Parallel execution is a graph primitive, not a workaround.**
Our Layer 2 fans out to 4 research agents simultaneously (destination research, transport scout, weather analyst, accommodation scout). In LangGraph, this is just 4 edges from `intent_parser` to each agent, plus 4 edges converging on `merge_research`. The runtime handles concurrency. In CrewAI, we'd need to manually spawn async tasks and synchronize results.

**2. `interrupt()` gives us exactly the HITL pattern we need.**
The project requires 3 human checkpoints (pick a plan, approve budget, confirm bookings). LangGraph's `interrupt()` pauses the graph mid-execution and serializes the full state. When the user responds, `Command(resume=value)` injects their choice and continues from the exact node. This is fundamentally different from CrewAI's callback approach where the "pause" is an external polling loop, not a graph-level primitive.

**3. Typed state with reducers prevents parallel agent conflicts.**
When 4 agents write to the same state dict concurrently, we need deterministic merge rules. LangGraph's `Annotated[type, reducer]` pattern lets us declare per-field merge strategies (e.g., `_keep_last` for scalars, `operator.add` for error lists). CrewAI and AutoGen have no equivalent — concurrent writes either overwrite silently or raise conflicts.

**4. The graph is the documentation.**
The `build_travel_graph()` function in `graph.py` is a complete, executable specification of the workflow. You can read it top-to-bottom and know exactly which agents run, in what order, with what branching logic. This matters for a 17-node, 7-layer system.

---

## 2. Shared State Architecture

### TravelPlanState — The Shared Typed Dict

All agents read from and write to a single `TravelPlanState` (a Python `TypedDict` with 50+ fields). This is the **only** communication channel between agents — there are no side-channel messages, shared databases, or event buses within the graph.

```python
class TravelPlanState(TypedDict):
    # Every field uses Annotated + reducer
    user_message:    Annotated[str, _keep_last]
    destination:     Annotated[str, _keep_last]
    budget:          Annotated[int, _keep_last]
    transport_options: Annotated[List[Any], _keep_last_list]
    errors:          Annotated[List[Any], operator.add]   # additive!
    # ... 50+ fields across 7 layers
```

### Why Reducers Matter

When Layer 2 runs 4 agents in parallel, all 4 return partial state updates simultaneously. LangGraph must merge these into a single state. Without reducers, the last agent to finish would overwrite everyone else's work.

Our reducer strategy:

| Reducer | Used For | Behavior |
|---|---|---|
| `_keep_last` | Scalar fields (budget, destination, etc.) | Last write wins — safe because each field is written by exactly one agent |
| `_keep_last_list` | List fields (transport_options, activities) | Last write wins — again, one agent owns each list |
| `operator.add` | `errors` and `warnings` | Additive — all agents can append errors, nothing is lost |

This design enforces a critical invariant: **each data field is owned by exactly one agent**. `transport_options` is only written by `transport_scout_agent`. `weather_forecast` is only written by `weather_analyst_agent`. The reducers are a safety net, not a conflict resolution mechanism — they guarantee that even if ownership is violated by a bug, the graph doesn't crash.

### State Lifecycle

```
User message
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  create_initial_state(user_message)                     │
│  → 50+ fields initialized to sensible defaults          │
│  → budget=0, duration=0, errors=[], etc.                │
└─────────────────────────────────────────────────────────┘
    │
    ▼  Layer 1: intent_parser writes ~15 fields
    │
    ▼  Layer 2: 4 agents write ~8 fields in parallel
    │
    ▼  Layer 3: options builder writes plan_options
    │
    ▼  ── interrupt() → Checkpoint 1 ──
    │  (user picks option → written to chosen_option)
    │
    ▼  Layer 4: 2 agents write ~6 fields in parallel
    │
    ▼  ── interrupt() → Checkpoint 2 ──
    │  (user adjusts sliders → written to approved_budget)
    │
    ▼  Layer 5: booking cart writes ~5 fields
    │
    ▼  ── interrupt() → Checkpoint 3 ──
    │  (user confirms → written to bookings_confirmed)
    │
    ▼  Layer 6: itinerary architect writes ~3 fields
    │
    ▼  Layer 7: PDF + map generators write pdf_bytes, map_html
    │
    ▼  Final state: all 50+ fields populated → persisted to PostgreSQL
```

Every field is available to every downstream agent. The itinerary architect can read `weather_forecast` (from Layer 2), `approved_budget` (from Checkpoint 2), and `selected_activities` (from Layer 5) simultaneously — no extra wiring needed.

---

## 3. Real-Time Data Handling

### The Three-Tier Fallback Chain

Every external data source follows the same pattern:

```
Real API → GPT Fallback → Mock Data
```

This is controlled by **feature flags** in `config.py`:

```python
USE_REAL_WEATHER:    bool   # OpenWeatherMap API
USE_REAL_RESEARCH:   bool   # Tavily web search
USE_REAL_ACTIVITIES: bool   # Google Places API
USE_REAL_FLIGHTS:    bool   # (reserved for future)
USE_REAL_HOTELS:     bool   # (reserved for future)
```

### How Each Data Source Works

**Weather (OpenWeatherMap)**

| Tier | Trigger | Source |
|---|---|---|
| Real API | `USE_REAL_WEATHER=true` + valid key | OpenWeatherMap 5-day forecast → geocoded coordinates |
| GPT fallback | API returns error or key missing | GPT-4o generates realistic seasonal forecast |
| Mock data | All above fail | Static forecast from `mock_data.py` |

The weather tool also performs **activity impact analysis** — it rates how weather affects each planned activity (e.g., "Boat ride on Lake: High impact — heavy rain expected, bring waterproof gear").

**Destination Research (Tavily)**

| Tier | Trigger | Source |
|---|---|---|
| Real API | `USE_REAL_RESEARCH=true` + valid key | Tavily web search for travel tips, visa info, local customs |
| GPT fallback | API error | GPT-4o generates destination overview from training data |
| Mock data | All above fail | Pre-built research from `mock_data.py` |

Search queries are location-aware — domestic destinations get ", India" appended; international ones don't.

**Activities (Google Places)**

| Tier | Trigger | Source |
|---|---|---|
| Real API | `USE_REAL_ACTIVITIES=true` + valid key | Google Places text search → GPT-4o price enrichment |
| GPT fallback | API error | GPT-4o generates popular activities |
| Mock data | All above fail | Static activities from `mock_data.py` |

The Google Places integration deserves special attention. Raw Places data includes `priceLevel` (0–4 scale) but not actual ticket prices. We solve this with a **two-stage enrichment**:

1. Google Places returns real attraction names, ratings, addresses, and categories
2. GPT-4o receives the attraction list and estimates realistic entry prices in INR based on its knowledge of that specific venue (e.g., "Statue of Liberty ferry: ₹4,500" vs "Central Park: ₹0")

This hybrid approach gives us real venue data with realistic pricing that the raw API cannot provide.

**Transport & Accommodation (GPT-4o primary)**

Transport and hotel options are generated by GPT-4o with carefully engineered prompts that inject:
- Route awareness (domestic vs international, city pair distances)
- Current market context (INR exchange rates, typical fare ranges)
- Booking links (Google Flights, MakeMyTrip, Booking.com, Hostelworld deep links)
- Number of travelers for correct total pricing

The system prompt switches dynamically based on `_is_international_route()` to use appropriate carriers, price ranges, and transport modes.

### Why Feature Flags?

Feature flags decouple API availability from code correctness. This gives us:

1. **Development without API keys** — `USE_REAL_*=false` lets the full pipeline run with mock data
2. **Incremental rollout** — Enable one real API at a time, verify quality, then enable the next
3. **Cost control** — Google Places and Tavily have per-request costs; flags let us disable them for testing
4. **Graceful degradation** — If an API goes down in production, flip the flag; the system keeps working with GPT fallbacks

---

## 4. Budget Optimization Strategy

Budget optimization is the most complex subsystem, spanning 6 stages across the entire pipeline.

### Stage 1: Feasibility Validation (Intent Parser)

Before any research happens, `_validate_trip_feasibility()` catches impossible trips:

```
User: "Delhi to New York, 1 day, ₹100"
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Feasibility Validator                                  │
│                                                         │
│  1. Is destination international? → Yes (New York)      │
│  2. Minimum duration for international? → 5 days        │
│     User said 1 day → auto-adjust to 5, add warning     │
│  3. Look up cost tier → "americas"                      │
│     - Flight: ₹50,000 minimum                           │
│     - Daily: ₹30,000/day × 5 days = ₹150,000           │
│     - Minimum total: ₹200,000                           │
│  4. User's budget ₹100 << ₹200,000                     │
│     → auto-adjust to ₹200,000, add warning              │
│  5. Transport mode? → forced to "flight" (international)│
└─────────────────────────────────────────────────────────┘
```

**Cost tiers** are a lookup table keyed by destination region:

| Tier | Example Cities | Min Flight (₹) | Daily Rate (₹) |
|---|---|---|---|
| `budget_india` | Jaipur, Varanasi, Rishikesh | 3,000 | 2,000 |
| `mid_india` | Goa, Kerala, Shimla | 5,000 | 4,000 |
| `premium_india` | Mumbai, Ladakh, Andaman | 7,000 | 7,000 |
| `budget_asia` | Bangkok, Bali, Kathmandu | 15,000 | 5,000 |
| `mid_asia` | Singapore, Tokyo, Seoul | 25,000 | 12,000 |
| `europe` | London, Paris, Rome | 40,000 | 22,000 |
| `americas` | New York, San Francisco | 50,000 | 30,000 |

For multi-city trips, `_lookup_tier()` splits the comma-separated destination string, looks up each city individually, and takes the **most expensive** tier to avoid underestimation.

### Stage 2: Real Cost Injection (Parallel Research)

Layer 2 agents fetch actual transport and hotel prices. These real numbers override GPT's initial estimates:

- **Transport Scout**: GPT-4o generates 3-5 options with realistic per-person one-way prices; the cheapest is identified as the floor
- **Accommodation Scout**: GPT-4o generates 3-5 options with per-night prices; filtered by budget-per-night-per-room

### Stage 3: Cost-Aware Options (Trip Options Builder)

The Trip Options Builder receives real transport/hotel prices and injects them into its GPT prompt:

```
"Cheapest round-trip transport for {num_travelers} travelers: ₹{X}"
"Cheapest per-night stay for {rooms_needed} rooms: ₹{Y}"
"Remaining for activities/food/local: ₹{Z}"
```

This prevents GPT from hallucinating unrealistic totals. The fallback (`_options_fallback`) calculates option costs purely arithmetically — no LLM involved — ensuring at least one set of consistent numbers.

### Stage 4: Budget Normalization (Budget Architect)

After the user picks an option, the Budget Architect:

1. Takes the chosen option's `rough_breakdown`
2. Normalizes category percentages so they sum to the `estimated_total`
3. Guards against `ZeroDivisionError` when all breakdowns are zero
4. If the user approved a higher total at Checkpoint 2, updates `state["budget"]` accordingly

### Stage 5: Slider Adjustment (Checkpoint 2 UI)

The Streamlit UI presents budget sliders for each category (transport, accommodation, activities, food, misc). Key decisions:

- **Slider max**: `max(budget, projected_total, individual_allocation)` — prevents the slider from being capped below the actual allocation
- **Over-budget warning**: Shown as a warning, not a blocker — the user can choose to increase their budget
- **Budget update**: If approved total exceeds original budget, the state's `budget` field is updated to match

### Stage 6: Traveler-Aware Pricing (Booking Cart)

The final pricing stage scales costs by actual group size:

```
Transport cost = one_way_price × 2 (round trip) × num_travelers
Hotel cost     = price_per_night × nights × rooms_needed
    where rooms_needed = max(1, (num_travelers + 1) // 2)
Activities     = sum of per-person entry fees × num_travelers
```

Activities are selected with a priority system: free activities first (up to 6), then cheapest paid activities — ensuring culturally important free experiences (temple visits, public parks, riverfront walks) aren't dropped in favor of expensive paid attractions.

### End-to-End Budget Flow

```
User input (₹100)
    │
    ▼  Feasibility: "Too low for NYC" → auto-adjust to ₹200,000
    │
    ▼  Research: Real flights ₹90K, hotels ₹8K/night
    │
    ▼  Options: 3 plans with costs based on real data
    │
    ▼  CP1: User picks "Balanced Explorer" (₹350K)
    │
    ▼  Budget Architect: Normalizes breakdown to ₹350K
    │
    ▼  CP2: User adjusts sliders (maybe increases to ₹400K)
    │       → state["budget"] updated to ₹400K
    │
    ▼  Booking Cart: ₹90K×2×4 travelers + ₹8K×10×2 rooms + activities
    │
    ▼  CP3: User sees exact costs, confirms or modifies
    │
    ▼  Itinerary: Day-by-day with exact costs per segment
```

---

## 5. Why This Architecture

### Design Principles

**1. Parallel layers for speed**

A sequential pipeline through all agents would take 45-60 seconds per run (each GPT-4o call is ~3-5s). By running independent agents in parallel:

- Layer 2 (4 agents): ~5s instead of ~20s
- Layer 4 (2 agents): ~5s instead of ~10s
- Layer 7 (2 agents): ~3s instead of ~6s

Total wall-clock time: ~25s instead of ~50s for a complete plan.

**2. Checkpoints for control**

The 3-checkpoint design isn't just about user preference — it's about **cost efficiency**. Each checkpoint gates expensive downstream work:

| Checkpoint | What it gates | Why it matters |
|---|---|---|
| CP1 (Pick plan) | Activities search, budget computation | Don't search for activities in a plan the user rejected |
| CP2 (Approve budget) | Booking assembly | Don't assemble bookings with a budget the user hasn't approved |
| CP3 (Confirm bookings) | Full itinerary generation, PDF, map | Don't generate a 10-page PDF for unconfirmed bookings |

If the user modifies their plan at CP3, we restart from Layer 1 with a new `thread_id` — this is cheaper than trying to "undo" partially computed state.

**3. Merge nodes for consistency**

After parallel execution, merge nodes provide a synchronization point where we can:
- Validate that all parallel agents completed successfully
- Check for errors before proceeding (e.g., `route_after_research` checks `state["errors"]`)
- Ensure downstream agents see a complete, consistent state

Without merge nodes, the next agent after a parallel fan-out would start as soon as **any** predecessor completes, operating on partial data.

### Error Handling Strategy

Errors propagate through the state, not through exceptions:

```python
errors: Annotated[List[Any], operator.add]
```

Using `operator.add` as the reducer means errors from parallel agents are **accumulated**, not overwritten. The `merge_research` node checks `state["errors"]` and routes to `handle_error` if any agent failed, displaying all errors to the user.

Individual agents use `try/except` internally and append to the errors list rather than crashing the graph. This means a weather API failure doesn't prevent transport options from being displayed.

### Replan Without Restart

After the complete plan is generated, the user can request modifications ("make it cheaper", "better hotels", "add a beach day"). The `replan_agent`:

1. Reads `replan_instruction` from state
2. Identifies which categories to modify (transport, accommodation, activities, or full replan)
3. Uses GPT-4o to adjust the existing itinerary, respecting all prior user choices
4. Writes updated fields back to state

This avoids rerunning the entire 25-second pipeline for minor tweaks.

---

## 6. Agent Roles and Collaboration

### Agent Inventory

| Agent | Layer | Model | Primary Responsibility | External APIs |
|---|---|---|---|---|
| **Intent Parser** | 1 | GPT-4o | Extract structured travel intent from natural language; run feasibility validation | OpenAI |
| **Destination Research** | 2 | GPT-4o | Gather travel tips, visa info, safety, best areas, local customs | Tavily, OpenAI |
| **Transport Scout** | 2 | GPT-4o | Generate 3-5 transport options with realistic prices and booking links | OpenAI |
| **Weather Analyst** | 2 | GPT-4o-mini | 5-day forecast + activity impact analysis | OpenWeatherMap, OpenAI |
| **Accommodation Scout** | 2 | GPT-4o | Generate 3-5 hotel/hostel options with prices and booking links | OpenAI |
| **Trip Options Builder** | 3 | GPT-4o | Synthesize research into 3 distinct trip plans (A/B/C) | OpenAI |
| **Activities Finder** | 4 | GPT-4o-mini | Find real attractions + estimate entry prices | Google Places, OpenAI |
| **Budget Architect** | 4 | GPT-4o | Normalize budget breakdown; handle over/under-budget scenarios | OpenAI |
| **Booking Cart** | 5 | — | Assemble cheapest viable transport + hotel + activities with traveler-aware pricing | None (pure logic) |
| **Itinerary Architect** | 6 | GPT-4o | Write day-by-day itinerary with exact costs, timings, and tips | OpenAI |
| **PDF Generator** | 7 | — | Generate downloadable PDF itinerary | ReportLab |
| **Map Generator** | 7 | — | Generate interactive HTML map with route markers | Folium, Geopy |
| **Replan Agent** | 8 | GPT-4o | Modify existing plan based on user feedback | OpenAI |

### How Agents Collaborate

Agents never communicate directly. All collaboration happens through the shared `TravelPlanState`:

```
Transport Scout writes:
    transport_options: [{id: "T1", mode: "flight", price: 45000, ...}, ...]

        ↓  (via state)

Trip Options Builder reads transport_options to compute:
    plan_options.A.rough_breakdown.transport = 45000 * 2 * num_travelers

        ↓  (via state)

Budget Architect reads chosen_option_details to normalize:
    budget_breakdown.transport = approved_transport_amount

        ↓  (via state)

Booking Cart reads transport_options + budget_breakdown to select:
    selected_transport = cheapest option within approved budget

        ↓  (via state)

Itinerary Architect reads selected_transport to write:
    Day 1: "Depart Delhi → JFK, IndiGo 6E-123, ₹45,000/person"
```

This **data-flow** pattern (vs message-passing) means:
- Any agent can be replaced without changing others
- Testing is simple: set state fields, run one agent, check output fields
- Debugging is straightforward: inspect state at any layer boundary

---

*Last updated: February 2026*
