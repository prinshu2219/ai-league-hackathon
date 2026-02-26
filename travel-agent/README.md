# AI Travel Planning Agent

## Run with Docker (app + PostgreSQL)

From this directory:

```bash
docker-compose up --build
```

- App: http://localhost:8501
- Postgres: localhost:5432 (user/password/db from `.env` or defaults in `docker-compose.yml`)

## Run Postgres in Docker + app locally (recommended for local dev)

Use this when you want only the database in Docker and run the Streamlit app on your machine.

### 1. Start only the Postgres container

From the `travel-agent` directory:

```bash
docker-compose up postgres -d
```

This starts Postgres with defaults: user `travel_agent`, password `travel_agent_secret`, database `travel_agent`. It maps to **port 5433** on your machine (so it doesn't clash with a local Postgres on 5432).

### 2. Set up your `.env`

Copy the example and set at least `OPENAI_API_KEY` and `DATABASE_URL` so the app can reach the DB:

```bash
cp .env.example .env
```

Edit `.env` and set:

- `OPENAI_API_KEY=your_openai_key_here`
- `DATABASE_URL=postgresql://travel_agent:travel_agent_secret@localhost:5433/travel_agent`

(If you changed `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` in `.env`, use those values in `DATABASE_URL` instead.)

### 3. Install dependencies and run the app

```bash
pip install -r requirements.txt
streamlit run app/main.py
```

Open http://localhost:8501. Trip history will be stored in the Postgres container.

### 4. Optional: stop Postgres when done

```bash
docker-compose stop postgres
```

To start it again later: `docker-compose up postgres -d`.

---

## Run everything locally (no Docker)

1. Install and start Postgres on your machine (e.g. `brew services start postgresql@15`).
2. Create the database: `createdb travel_agent` (or via psql).
3. Copy `.env.example` to `.env`, set `OPENAI_API_KEY` and `DATABASE_URL=postgresql://user:pass@localhost:5432/travel_agent`.
4. Run: `pip install -r requirements.txt && streamlit run app/main.py`.

## Deploy on EC2 (or any VM)

1. Install Docker and Docker Compose.
2. Clone the repo and copy `.env` (include `OPENAI_API_KEY`; Postgres defaults work if using compose).
3. From the `travel-agent` directory:

```bash
docker-compose up -d --build
```

4. Open port 8501 in the security group. Open 5432 only if you need direct DB access.
