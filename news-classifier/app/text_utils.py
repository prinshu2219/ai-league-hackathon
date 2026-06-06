"""Prepare long articles — compact, strip HTML, chunk for context window."""

import re
from html import unescape


def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def compact_article(headline: str, body: str, max_chars: int) -> tuple[str, bool]:
    """
    Shrink article to fit context window.
    Returns (prepared_text, was_compacted).
    """
    clean_body = strip_html(body)
    text = f"Headline: {headline}\n\nBody: {clean_body}"

    if len(text) <= max_chars:
        return text, False

    truncated = f"Headline: {headline}\n\nBody: {clean_body[: max_chars - len(headline) - 20]}..."
    return truncated, True


def split_into_chunks(body: str, chunk_size: int) -> list[str]:
    """Split body into chunks for majority-vote classification."""
    clean = strip_html(body)
    if len(clean) <= chunk_size:
        return [clean]
    return [clean[i : i + chunk_size] for i in range(0, len(clean), chunk_size)]
