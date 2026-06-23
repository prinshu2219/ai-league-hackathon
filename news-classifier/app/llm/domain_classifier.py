"""
Lightweight domain router — stand-in for a fine-tuned HuggingFace classifier.

High-confidence keyword matches skip the expensive LLM call.
In production you'd swap this for: pipeline("text-classification", model="your-news-model")
"""

import re
from app.models import ClassificationResult

DOMAIN_PATTERNS: dict[str, list[str]] = {
    "sports": [
        r"\bcricket\b", r"\bfootball\b", r"\bmatch\b", r"\bscore\b", r"\btournament\b",
        r"\bolympics\b", r"\bgoal\b", r"\bwicket\b", r"\bchampionship\b",
    ],
    "tech": [
        r"\bai\b", r"\bsoftware\b", r"\bstartup\b", r"\biphone\b", r"\bgoogle\b",
        r"\bnvidia\b", r"\bcyber\b", r"\bapp\b", r"\bchip\b", r"\blaptop\b",
    ],
    "politics": [
        r"\belection\b", r"\bparliament\b", r"\bminister\b", r"\bgovernment\b",
        r"\bvote\b", r"\bpolicy\b", r"\bcongress\b", r"\bmodi\b", r"\bbiden\b",
    ],
    "business": [
        r"\bstock\b", r"\bmarket\b", r"\brevenue\b", r"\bprofit\b", r"\bipo\b",
        r"\binflation\b", r"\btrade\b", r"\bearnings\b", r"\bnifty\b", r"\bsensex\b",
    ],
}


def classify_with_domain_router(headline: str, body: str) -> ClassificationResult | None:
    """
    Fast keyword-based classification. Returns None if confidence too low → use LLM.
    """
    text = f"{headline} {body}".lower()
    scores: dict[str, int] = {cat: 0 for cat in DOMAIN_PATTERNS}

    for category, patterns in DOMAIN_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                scores[category] += 1

    if not any(scores.values()):
        return None

    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]
    total = sum(scores.values())
    confidence = min(0.95, best_score / max(total, 1) + 0.3)

    if confidence < 0.85:
        return None

    return ClassificationResult(
        category=best_category,  # type: ignore[arg-type]
        confidence=round(confidence, 2),
        summary=f"Domain router classified based on keyword signals ({best_score} matches).",
        provider="domain_router",
        method="domain_model",
    )
