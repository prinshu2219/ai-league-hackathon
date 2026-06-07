"""
Raw OpenAI SDK client with exponential backoff.

Extraction path: response.choices[0].message.content
"""

import json
import logging
import random
import time

from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError

from app.config import config
from app.models import ClassificationResult
from app.circuit_breaker import openai_circuit

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a news classifier. Classify into exactly one of: "
    "politics, sports, tech, business. "
    "Return JSON with keys: category, confidence (0-1 float), summary (one sentence)."
)


def _get_client() -> OpenAI:
    return OpenAI(api_key=config.OPENAI_API_KEY, timeout=config.REQUEST_TIMEOUT)


def classify_raw_openai(headline: str, body: str, model: str | None = None) -> tuple[ClassificationResult, int]:
    """
    Call OpenAI chat completions API with exponential backoff on 429/timeout.
    Returns (ClassificationResult, total_tokens).
    """
    client = _get_client()
    model = model or config.PRIMARY_MODEL
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Headline: {headline}\n\nBody: {body}"},
    ]

    last_error: Exception | None = None

    for attempt in range(config.MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=messages,
            )

            # ⭐ Exact extraction path for interview
            text = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            if finish_reason == "length":
                logger.warning("OpenAI response truncated (finish_reason=length)")

            data = json.loads(text)
            tokens = response.usage.total_tokens if response.usage else 0
            openai_circuit.record_success()

            return ClassificationResult(
                category=data["category"],
                confidence=float(data["confidence"]),
                summary=data["summary"],
                provider="openai",
                method="raw_sdk",
            ), tokens

        except (RateLimitError, APITimeoutError, APIConnectionError) as e:
            last_error = e
            openai_circuit.record_failure()
            if attempt == config.MAX_RETRIES - 1:
                break
            wait = min(2 ** attempt + random.uniform(0, 1), 60)
            logger.warning("OpenAI retry %d/%d after %.1fs: %s", attempt + 1, config.MAX_RETRIES, wait, e)
            time.sleep(wait)

    raise last_error or RuntimeError("OpenAI classification failed")
