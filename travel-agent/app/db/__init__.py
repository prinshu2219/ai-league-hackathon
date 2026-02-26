"""
app.db — Trip history persistence (PostgreSQL).
When DATABASE_URL is not set, all functions no-op or return empty.
"""

from app.db.trips import (
    create_trips_table,
    get_connection,
    get_trip,
    list_trips,
    save_trip,
)

__all__ = [
    "create_trips_table",
    "get_connection",
    "get_trip",
    "list_trips",
    "save_trip",
]
