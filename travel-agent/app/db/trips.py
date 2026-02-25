"""
app.db.trips — Trip history persistence.
Uses PostgreSQL; if DATABASE_URL is not set, all functions no-op or return empty.
"""

import base64
import json
import uuid
from contextlib import contextmanager
from typing import Any

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from app.core.config import config

STATE_KEY_PDF_BYTES = "pdf_bytes"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS trips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    state JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trips_created_at ON trips(created_at DESC);
"""


def get_connection():
    """Return a DB connection or None if DATABASE_URL is not set."""
    if not config.DATABASE_URL:
        return None
    try:
        return psycopg2.connect(config.DATABASE_URL)
    except Exception:
        return None


@contextmanager
def _conn_ctx():
    conn = get_connection()
    if conn is None:
        yield None
        return
    try:
        yield conn
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def create_trips_table(conn) -> None:
    """Idempotent create of trips table. Safe to call on startup."""
    if conn is None:
        return
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)


def _state_to_json(state: dict) -> str:
    """Serialize state for JSONB; encode pdf_bytes as base64."""
    out = dict(state)
    if isinstance(out.get(STATE_KEY_PDF_BYTES), bytes):
        out[STATE_KEY_PDF_BYTES] = base64.b64encode(out[STATE_KEY_PDF_BYTES]).decode("ascii")
    return json.dumps(out, default=str)


def _state_from_json(raw: str | dict) -> dict:
    """Deserialize state from JSONB; decode base64 pdf_bytes back to bytes."""
    data = raw if isinstance(raw, dict) else json.loads(raw)
    if isinstance(data.get(STATE_KEY_PDF_BYTES), str):
        try:
            data[STATE_KEY_PDF_BYTES] = base64.b64decode(data[STATE_KEY_PDF_BYTES])
        except Exception:
            data[STATE_KEY_PDF_BYTES] = b""
    return data


def save_trip(thread_id: str | None, state: dict) -> str | None:
    """
    Insert or update a trip by thread_id. Returns trip id or None.
    State is serialized (pdf_bytes -> base64) before storing.
    """
    tid = thread_id or str(uuid.uuid4())
    with _conn_ctx() as conn:
        if conn is None:
            return None
        create_trips_table(conn)
        state_json = _state_to_json(state)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO trips (thread_id, state, updated_at)
                VALUES (%s, %s::jsonb, now())
                ON CONFLICT (thread_id) DO UPDATE SET
                    state = EXCLUDED.state,
                    updated_at = now()
                RETURNING id
                """,
                (tid, state_json),
            )
            row = cur.fetchone()
            return str(row[0]) if row else None

    return None


def list_trips(limit: int = 50) -> list[dict[str, Any]]:
    """
    Return list of recent trips: id, thread_id, created_at, updated_at, destination.
    destination is taken from state->'trip_summary'->>'destination' or state->>'destination'.
    """
    with _conn_ctx() as conn:
        if conn is None:
            return []
        create_trips_table(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, thread_id, created_at, updated_at,
                       COALESCE(
                         state->'trip_summary'->>'destination',
                         state->>'destination',
                         'Unknown'
                       ) AS destination
                FROM trips
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    return []


def get_trip(trip_id: str) -> dict | None:
    """Load full trip state by id. Returns state dict or None. Decodes pdf_bytes from base64."""
    with _conn_ctx() as conn:
        if conn is None:
            return None
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT thread_id, state FROM trips WHERE id = %s", (trip_id,))
            row = cur.fetchone()
            if not row or row.get("state") is None:
                return None
            state = _state_from_json(row["state"])
            state["thread_id"] = row.get("thread_id") or trip_id
            return state
    return None
