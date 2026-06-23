"""
Raw Anthropic SDK client — fallback when OpenAI fails.

Extraction path: message.content[0].text
"""

import json
import logging

import anthropic

from app.config import config
from app.models import ClassificationResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a news classifier. Classify into exactly one of: "
    "politics, sports, tech, business. "
    "Return JSON with keys: category, confidence (0-1 float), summary (one sentence)."
)


def classify_raw_anthropic(headline: str, body: str) -> tuple[ClassificationResult, int]:
    """
    Anthropic Messages API — used as fallback provider.
    Returns (ClassificationResult, total_tokens).
    """
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    message = client.messages.create(
        model=config.FALLBACK_MODEL,
        max_tokens=1024,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Headline: {headline}\n\nBody: {body}"},
        ],
    )

    # ⭐ Exact extraction path — different from OpenAI
    text = message.content[0].text
    data = json.loads(text)
    tokens = message.usage.input_tokens + message.usage.output_tokens

    logger.info("Anthropic fallback succeeded (model=%s)", config.FALLBACK_MODEL)

    return ClassificationResult(
        category=data["category"],
        confidence=float(data["confidence"]),
        summary=data["summary"],
        provider="anthropic",
        method="raw_sdk",
    ), tokens
