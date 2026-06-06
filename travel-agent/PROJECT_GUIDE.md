# Travel Agent — Project Guide

## Overview

**AI Travel Planning Agent** is a Streamlit app that builds end-to-end trip plans using a **LangGraph** workflow with **GPT-4o**, human-in-the-loop checkpoints, and optional real APIs (weather, research, flights, hotels). Trip history can be stored in **PostgreSQL**.

---

## Architecture

### High-level flow

```
User prompt → Intent Parser (GPT-4o)
    → Parallel research (destination, transport, weather, accommodation)
    → Merge → Trip Options Builder (3 options A/B/C)
    → CHECKPOINT 1: user picks option
    → Parallel: Activities Finder + Budget Architect
    → Merge → CHECKPOINT 2: user approves/adjusts budget
    → Booking Cart
    → CHECKPOINT 3: user confirms or modifies plan
    → Itinerary Architect → PDF + Map (parallel)
    → Merge → Done (or Replan loop)
```

### Key components

| Component | Role |
|-----------|------|
| **app/main.py** | Streamlit UI: input, 3 checkpoints, final output, demo mode, trip history, replan |
| **app/core/graph.py** | LangGraph state machine; checkpoints use `interrupt()` and resume via `Command(resume=...)` |
| **app/core/state.py** | `TravelPlanState` TypedDict and `create_initial_state()`; all fields use reducers |
| **app/core/config.py** | Env-based config; feature flags `USE_REAL_*` switch mock vs real APIs |
| **app/agents/__init__.py** | All nodes: intent, research, options, checkpoints 1–3, activities, budget, cart, itinerary, PDF, map, replan, error |
| **app/tools/** | research, transport, weather, hotels, activities — call external APIs or return mocks |
| **app/db/trips.py** | PostgreSQL: save_trip, list_trips, get_trip; no-op when `DATABASE_URL` unset |
| **app/utils/** | mock_data, demo_data (pre-built state), pdf_generator, map_generator |

### Checkpoints (human-in-the-loop)

- **Checkpoint 1**: Plan selection — options A/B/C, assumptions, weather summary.
- **Checkpoint 2**: Budget approval — breakdown sliders, projected total, warnings.
- **Checkpoint 3**: Booking confirmation — cart (transport, stay, activities), confirm or “Modify plan”.

Resume payloads: `{"chosen_option": "A"}`, `{"approved_budget": {...}}`, `{"confirmed": True|False}`.

### Session state (Streamlit)

- `thread_id` — LangGraph checkpointer thread.
- `graph_state` — latest state from graph.
- `interrupt_data` — current checkpoint payload (or None when done).
- `checkpoint_num` — 1, 2, or 3.
- `planning_done` — True when flow is complete.
- `is_demo_mode` — True when “Load Demo” was used (no DB save).

---

## Configuration

### Required

- **OPENAI_API_KEY** — used by all GPT-4o agents.

### Optional (feature flags in config)

- **USE_REAL_WEATHER** + OPENWEATHER_API_KEY
- **USE_REAL_RESEARCH** + TAVILY_API_KEY
- **USE_REAL_ACTIVITIES** — tools may use Google/Foursquare keys
- **USE_REAL_FLIGHTS** — AMADEUS_*, RAPIDAPI (IRCTC)
- **USE_REAL_HOTELS** — HOTELBEDS_*

If flags are false, agents use **app/utils/mock_data.py** (no keys needed).

### Database

- **DATABASE_URL** — e.g. `postgresql://user:pass@host:5432/dbname`
- When set: trips are saved on plan completion; sidebar shows “Trip history” and load-by-id.
- When unset: DB calls no-op; no trip history.

---

## Docker

### Dockerfile

- **Base**: `python:3.11-slim`
- **WORKDIR**: `/app`
- **Copy**: `requirements.txt`, then `app/` → `./app/`
- **CMD**: `streamlit run app/main.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true`
- **Healthcheck**: Uses Python to hit Streamlit health URL (slim image has no `curl`).

### docker-compose.yml

- **postgres**: Postgres 15, port 5433→5432, env from `.env` or defaults (`travel_agent` / `travel_agent_secret` / `travel_agent`).
- **travel-agent**: build `.`, port 8501, `env_file: .env`, `DATABASE_URL` overridden to point at `postgres:5432`. Depends on postgres healthy. Optional volume `./app:/app/app` for dev hot-reload (comment out for production).

---

## Running

### Local (no Docker)

```bash
pip install -r requirements.txt
# Optional: start Postgres (e.g. docker-compose up postgres -d)
# Set .env: OPENAI_API_KEY, DATABASE_URL if using DB
streamlit run app/main.py
```

### Local with Postgres in Docker

```bash
docker-compose up postgres -d
# .env: DATABASE_URL=postgresql://travel_agent:travel_agent_secret@localhost:5433/travel_agent
streamlit run app/main.py
```

### Full stack (Docker)

```bash
docker-compose up --build
# App: http://localhost:8501
```

---

## Known issues & fixes for AWS deployment

1. **Dockerfile healthcheck**  
   - **Issue**: `python:3.11-slim` has no `curl`; `HEALTHCHECK` with `curl` fails.  
   - **Fix**: Use a healthcheck that runs inside the container with Python (e.g. `python -c` hitting `http://localhost:8501/_stcore/health`) or install `curl` in the image. (Fixed in this repo.)

2. **Path / module resolution**  
   - **Issue**: Running `streamlit run app/main.py` can put `app/` on path instead of project root.  
   - **Fix**: `main.py` prepends project root to `sys.path` at startup so `from app.core.state` etc. resolve. Keep this when deploying.

3. **Database URL in Docker**  
   - Compose overrides `DATABASE_URL` so the app talks to `postgres:5432`. On AWS, use RDS or similar and set `DATABASE_URL` in the task/container env (no override from compose if you run the app alone).

4. **Secrets**  
   - Do not commit `.env`. Use AWS Secrets Manager, Parameter Store, or ECS task env for `OPENAI_API_KEY`, `DATABASE_URL`, and any API keys you enable.

5. **Recursion limit**  
   - Graph compiled with `recursion_limit=50`. For very complex multi-city flows, consider increasing in `get_config()` in `main.py` if you see recursion errors.

6. **Trip history and RDS**  
   - Ensure RDS (or managed Postgres) is in same VPC as the app and security group allows the app’s port. Run migrations/tables on first deploy; `create_trips_table()` is idempotent and called from `save_trip`/`list_trips`.

7. **Streamlit in production**  
   - For production, consider reverse proxy (ALB/Nginx) and HTTPS. Streamlit’s `--server.headless=true` is already set. You may want to set `--server.enableCORS=false` or configure CORS if needed.

---

## File map (quick reference)

```
travel-agent/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── README.md
├── PROJECT_GUIDE.md          # this file
└── app/
    ├── main.py               # Streamlit entry; graph run/resume; checkpoints; demo; history
    ├── core/
    │   ├── config.py         # Env + feature flags
    │   ├── state.py          # TravelPlanState, create_initial_state
    │   └── graph.py          # build_travel_graph(), travel_graph
    ├── agents/
    │   └── __init__.py       # All LangGraph nodes (intent → research → options → CP1–3 → itinerary → PDF/map)
    ├── tools/
    │   ├── research.py       # Tavily + GPT-4o or mock
    │   ├── transport.py
    │   ├── weather.py
    │   ├── hotels.py
    │   └── activities.py
    ├── db/
    │   ├── __init__.py
    │   └── trips.py          # PostgreSQL trip history
    └── utils/
        ├── mock_data.py      # Fallback data when APIs off
        ├── demo_data.py      # Full demo state for “Load Demo”
        ├── pdf_generator.py
        └── map_generator.py
```

---

## Next steps for AWS

1. Fix any remaining issues (e.g. healthcheck — done in Dockerfile).
2. Build and run with `docker-compose` locally to confirm DB and app work.
3. Choose deployment: ECS (Fargate) + ALB, or EC2 + Docker, or App Runner.
4. Store secrets in Secrets Manager/Parameter Store; inject as env into the task/container.
5. Point `DATABASE_URL` to RDS (or Aurora Postgres); ensure schema (trips table) exists.
6. Open only required ports (e.g. 8501 or 80/443 via ALB) in security groups.
7. (Optional) Add CloudWatch logs and metrics for the app container.
