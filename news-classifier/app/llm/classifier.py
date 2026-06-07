"""Main classifier orchestrator — ties together all layers."""

import logging
from collections import Counter

from app.config import config
from app.models import ClassificationResult, ClassifyResponse
from app.text_utils import compact_article, split_into_chunks
from app.circuit_breaker import openai_circuit
from app.llm.domain_classifier import classify_with_domain_router
from app.llm.chain import classify_with_chain
from app.llm.openai_client import classify_raw_openai
from app.llm.anthropic_client import classify_raw_anthropic

logger = logging.getLogger(__name__)


def _classify_single(headline: str, body: str, use_chain: bool) -> tuple[ClassificationResult, int]:
    """Classify one text block with OpenAI → Anthropic fallback."""
    tokens = 0

    if openai_circuit.is_open():
        logger.warning("OpenAI circuit open — skipping to Anthropic")
        if config.USE_ANTHROPIC_FALLBACK and config.ANTHROPIC_API_KEY:
            result, tokens = classify_raw_anthropic(headline, body)
            return result, tokens
        raise RuntimeError("OpenAI circuit open and Anthropic fallback disabled")

    try:
        if use_chain:
            result = classify_with_chain(headline, body)
            return result, tokens
        result, tokens = classify_raw_openai(headline, body)
        return result, tokens

    except Exception as e:
        logger.error("OpenAI/chain failed: %s", e)
        openai_circuit.record_failure()

        if config.USE_ANTHROPIC_FALLBACK and config.ANTHROPIC_API_KEY:
            result, tokens = classify_raw_anthropic(headline, body)
            return result, tokens
        raise


def classify_news(
    headline: str,
    body: str,
    use_chain: bool = True,
) -> ClassifyResponse:
    """
    Full pipeline:
    1. Domain router (cheap) — skip LLM if high confidence
    2. Compact long articles
    3. Chunk + majority vote if still too long
    4. LangChain chain OR raw OpenAI SDK
    5. Anthropic fallback on failure
    """
    tokens_used = 0
    compacted = False
    chunks_used = 1

    # Layer 1: domain router (optional cheap path)
    if config.USE_DOMAIN_ROUTER:
        domain_result = classify_with_domain_router(headline, body)
        if domain_result is not None:
            logger.info("Domain router hit: %s (%.2f)", domain_result.category, domain_result.confidence)
            return ClassifyResponse(
                result=domain_result,
                tokens_used=0,
                article_compacted=False,
                chunks_used=1,
            )

    # Layer 2: compact for context window
    prepared, compacted = compact_article(headline, body, config.MAX_ARTICLE_CHARS)
    clean_body = prepared.split("\n\nBody: ", 1)[-1] if "\n\nBody: " in prepared else body

    # Layer 3: chunk if extremely long (after compact still huge)
    if len(clean_body) > config.CHUNK_SIZE * 2:
        chunks = split_into_chunks(clean_body, config.CHUNK_SIZE)
        chunks_used = len(chunks)
        categories: list[str] = []
        confidences: list[float] = []
        summaries: list[str] = []

        for chunk in chunks:
            result, chunk_tokens = _classify_single(headline, chunk, use_chain)
            tokens_used += chunk_tokens
            categories.append(result.category)
            confidences.append(result.confidence)
            summaries.append(result.summary)

        winner = Counter(categories).most_common(1)[0][0]
        avg_conf = sum(confidences) / len(confidences)

        return ClassifyResponse(
            result=ClassificationResult(
                category=winner,  # type: ignore[arg-type]
                confidence=round(avg_conf, 2),
                summary=summaries[0],
                provider="openai",
                method="langchain" if use_chain else "raw_sdk",
            ),
            tokens_used=tokens_used,
            article_compacted=compacted,
            chunks_used=chunks_used,
        )

    # Normal path — single LLM call
    result, tokens_used = _classify_single(headline, clean_body, use_chain)

    return ClassifyResponse(
        result=result,
        tokens_used=tokens_used,
        article_compacted=compacted,
        chunks_used=chunks_used,
    )
