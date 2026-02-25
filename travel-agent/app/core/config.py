"""
config.py
─────────
Centralized configuration.
All API keys and settings loaded from environment variables.
Import this anywhere you need a key or setting.
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Config:
    """All application configuration in one place."""

    # ── LLM ───────────────────────────────────────────────
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Primary model for all critical agents
    PRIMARY_MODEL: str = "gpt-4o"

    # Cheaper model for simple tasks (future optimization)
    FAST_MODEL: str = "gpt-4o-mini"

    # ── Flight APIs ───────────────────────────────────────
    AMADEUS_API_KEY: str    = os.getenv("AMADEUS_API_KEY", "")
    AMADEUS_API_SECRET: str = os.getenv("AMADEUS_API_SECRET", "")
    DUFFEL_API_KEY: str     = os.getenv("DUFFEL_API_KEY", "")

    # ── Transport ─────────────────────────────────────────
    ROME2RIO_API_KEY: str   = os.getenv("ROME2RIO_API_KEY",   "")
    RAPIDAPI_KEY: str       = os.getenv("RAPIDAPI_KEY",       "")

    # ── Accommodation ─────────────────────────────────────
    BOOKING_COM_API_KEY: str   = os.getenv("BOOKING_COM_API_KEY",   "")
    HOSTELWORLD_API_KEY: str   = os.getenv("HOSTELWORLD_API_KEY",   "")
    HOTELBEDS_API_KEY: str     = os.getenv("HOTELBEDS_API_KEY",     "")
    HOTELBEDS_API_SECRET: str  = os.getenv("HOTELBEDS_API_SECRET",  "")

    # ── Activities & Maps ─────────────────────────────────
    GOOGLE_PLACES_API_KEY: str = os.getenv("GOOGLE_PLACES_API_KEY", "")
    GOOGLE_MAPS_API_KEY: str   = os.getenv("GOOGLE_MAPS_API_KEY", "")
    FOURSQUARE_API_KEY: str    = os.getenv("FOURSQUARE_API_KEY", "")

    # ── Weather ───────────────────────────────────────────
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    TOMORROW_IO_API_KEY: str = os.getenv("TOMORROW_IO_API_KEY", "")

    # ── Research & Tips ───────────────────────────────────
    TAVILY_API_KEY: str        = os.getenv("TAVILY_API_KEY", "")
    REDDIT_CLIENT_ID: str      = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str  = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT: str     = os.getenv(
        "REDDIT_USER_AGENT", "TravelPlannerBot/1.0"
    )

    # ── Database (trip history) ───────────────────────────
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "",
    )

    # ── App Settings ──────────────────────────────────────
    APP_ENV: str    = os.getenv("APP_ENV", "development")
    DEBUG: bool     = os.getenv("DEBUG", "true").lower() == "true"
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    CACHE_TTL: int  = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

    # ── Feature Flags (Sprint 3A) ─────────────────────────
    # Set each to true once the corresponding key is in .env
    # Each flag independently switches one agent: mock → real API
    USE_REAL_WEATHER: bool    = os.getenv("USE_REAL_WEATHER",    "false").lower() == "true"
    USE_REAL_RESEARCH: bool   = os.getenv("USE_REAL_RESEARCH",   "false").lower() == "true"
    USE_REAL_ACTIVITIES: bool = os.getenv("USE_REAL_ACTIVITIES", "false").lower() == "true"
    USE_REAL_FLIGHTS: bool    = os.getenv("USE_REAL_FLIGHTS",    "false").lower() == "true"
    USE_REAL_HOTELS: bool     = os.getenv("USE_REAL_HOTELS",     "false").lower() == "true"

    @classmethod
    def validate(cls) -> list[str]:
        """
        Check which required keys are missing.
        Returns list of missing key names.
        Call this at startup to warn about missing config.
        """
        missing = []

        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")

        # Only warn about API keys that are actually needed
        if cls.USE_REAL_FLIGHTS:
            if not cls.AMADEUS_API_KEY:
                missing.append("AMADEUS_API_KEY")
            if not cls.RAPIDAPI_KEY:
                missing.append("RAPIDAPI_KEY (for IRCTC trains)")

        if cls.USE_REAL_HOTELS:
            if not cls.HOTELBEDS_API_KEY:
                missing.append("HOTELBEDS_API_KEY")
            if not cls.HOTELBEDS_API_SECRET:
                missing.append("HOTELBEDS_API_SECRET")

        if cls.USE_REAL_WEATHER:
            if not cls.OPENWEATHER_API_KEY:
                missing.append("OPENWEATHER_API_KEY")

        if cls.USE_REAL_RESEARCH:
            if not cls.TAVILY_API_KEY:
                missing.append("TAVILY_API_KEY")

        return missing

    @classmethod
    def is_production(cls) -> bool:
        return cls.APP_ENV == "production"


# Single instance used everywhere
config = Config()