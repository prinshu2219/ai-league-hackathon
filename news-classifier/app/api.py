"""
FastAPI REST API — exposes the News Classifier with tier-based rate limiting.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.secrets import load_secrets
from app.config import config
from app.models import ClassifyRequest, ClassifyResponse
from app.rate_limiter import rate_limiter
from app.llm.classifier import classify_news

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_secrets()
    missing = config.validate()
    if missing and config.APP_ENV != "test":
        logger.warning("Missing config keys: %s", missing)
    yield


app = FastAPI(
    title="News Classifier API",
    description="Classify news articles with OpenAI, Anthropic fallback, LangChain LCEL",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "env": config.APP_ENV,
        "primary_model": config.PRIMARY_MODEL,
        "fallback_model": config.FALLBACK_MODEL,
    }


@app.post("/classify", response_model=ClassifyResponse)
def classify(request: ClassifyRequest):
    """
    Classify a news article.
    Rate limit checked BEFORE any LLM call.
    """
    allowed, remaining = rate_limiter.check(request.user_id, request.tier)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for {request.tier} tier. Try again in 1 minute.",
            headers={"Retry-After": "60"},
        )

    try:
        response = classify_news(
            headline=request.headline,
            body=request.body,
            use_chain=request.use_chain,
        )
        response.rate_limit_remaining = remaining
        return response

    except Exception as e:
        logger.exception("Classification failed")
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.get("/kb/stats")
def stats():
    """API stats for interview talking point."""
    return {
        "free_tier_rpm": config.FREE_TIER_RPM,
        "paid_tier_rpm": config.PAID_TIER_RPM,
        "max_retries": config.MAX_RETRIES,
        "max_article_chars": config.MAX_ARTICLE_CHARS,
        "models": {
            "primary": config.PRIMARY_MODEL,
            "fallback": config.FALLBACK_MODEL,
        },
    }
