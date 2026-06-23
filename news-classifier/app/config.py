"""Centralized configuration — all settings from environment variables."""

import os


class Config:
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # LLM keys (loaded by secrets.py before Config is used)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Models — be specific in interviews
    PRIMARY_MODEL: str = os.getenv("PRIMARY_MODEL", "gpt-4o-mini")
    FALLBACK_MODEL: str = os.getenv("FALLBACK_MODEL", "claude-3-5-sonnet-20241022")
    HARD_CASE_MODEL: str = os.getenv("HARD_CASE_MODEL", "gpt-4o")

    # Retry / reliability
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "4"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    USE_ANTHROPIC_FALLBACK: bool = os.getenv("USE_ANTHROPIC_FALLBACK", "true").lower() == "true"
    USE_DOMAIN_ROUTER: bool = os.getenv("USE_DOMAIN_ROUTER", "true").lower() == "true"
    DOMAIN_CONFIDENCE_THRESHOLD: float = float(os.getenv("DOMAIN_CONFIDENCE_THRESHOLD", "0.85"))

    # Context window
    MAX_ARTICLE_CHARS: int = int(os.getenv("MAX_ARTICLE_CHARS", "12000"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "3000"))

    # User rate limits (requests per minute)
    FREE_TIER_RPM: int = int(os.getenv("FREE_TIER_RPM", "10"))
    PAID_TIER_RPM: int = int(os.getenv("PAID_TIER_RPM", "100"))

    # AWS Secrets Manager (production)
    AWS_SECRET_NAME: str = os.getenv("AWS_SECRET_NAME", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-south-1")

    # Circuit breaker
    CIRCUIT_BREAKER_THRESHOLD: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
    CIRCUIT_BREAKER_COOLDOWN: int = int(os.getenv("CIRCUIT_BREAKER_COOLDOWN", "60"))

    @classmethod
    def validate(cls) -> list[str]:
        missing = []
        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if cls.USE_ANTHROPIC_FALLBACK and not cls.ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY (required when USE_ANTHROPIC_FALLBACK=true)")
        return missing

    @classmethod
    def is_production(cls) -> bool:
        return cls.APP_ENV == "production"


config = Config()
