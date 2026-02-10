"""
utils/output_parser.py
----------------------
Parses and structures the raw AI response into a clean,
consistent format for display in the Streamlit UI.

Output format:
{
    "claim": str,
    "verdict": TRUE | FALSE | PARTIALLY TRUE | NOT ENOUGH EVIDENCE,
    "confidence": HIGH | MEDIUM | LOW,
    "reasoning": str,
    "citations": [{"source": str, "url": str, "snippet": str}],
    "evidence_quality": STRONG | WEAK | NONE
}
"""

import re
from typing import Any


# Verdict display config used by Streamlit UI
VERDICT_CONFIG = {
    "TRUE": {
        "emoji": "✅",
        "color": "green",
        "label": "TRUE"
    },
    "FALSE": {
        "emoji": "❌",
        "color": "red",
        "label": "FALSE"
    },
    "PARTIALLY TRUE": {
        "emoji": "⚠️",
        "color": "orange",
        "label": "PARTIALLY TRUE"
    },
    "NOT ENOUGH EVIDENCE": {
        "emoji": "🔍",
        "color": "gray",
        "label": "NOT ENOUGH EVIDENCE"
    }
}


def parse_verdict_response(raw_response: str, original_claim: str) -> dict:
    """
    Parses raw LLM text response into a structured verdict dictionary.

    Args:
        raw_response: Raw text from GPT-4o
        original_claim: The original claim submitted by the user

    Returns:
        Structured verdict dictionary

    Example:
        result = parse_verdict_response(llm_output, "India banned TikTok")
        print(result["verdict"])   # "TRUE"
        print(result["reasoning"]) # "India banned TikTok in 2020..."
    """
    result = {
        "claim": original_claim,
        "verdict": "NOT ENOUGH EVIDENCE",
        "confidence": "LOW",
        "reasoning": "",
        "citations": [],
        "evidence_quality": "NONE",
        "raw_response": raw_response
    }

    try:
        # ── Extract VERDICT ──────────────────────────────────────────
        verdict_pattern = r"VERDICT:\s*(TRUE|FALSE|PARTIALLY TRUE|NOT ENOUGH EVIDENCE)"
        verdict_match = re.search(verdict_pattern, raw_response, re.IGNORECASE)
        if verdict_match:
            result["verdict"] = verdict_match.group(1).upper()

        # ── Extract CONFIDENCE ───────────────────────────────────────
        confidence_pattern = r"CONFIDENCE:\s*(HIGH|MEDIUM|LOW)"
        confidence_match = re.search(confidence_pattern, raw_response, re.IGNORECASE)
        if confidence_match:
            result["confidence"] = confidence_match.group(1).upper()

        # ── Extract REASONING ────────────────────────────────────────
        reasoning_pattern = r"REASONING:\s*(.*?)(?=CITATIONS:|EVIDENCE QUALITY:|$)"
        reasoning_match = re.search(reasoning_pattern, raw_response, re.IGNORECASE | re.DOTALL)
        if reasoning_match:
            result["reasoning"] = reasoning_match.group(1).strip()

        # ── Extract EVIDENCE QUALITY ─────────────────────────────────
        eq_pattern = r"EVIDENCE QUALITY:\s*(STRONG|WEAK|NONE)"
        eq_match = re.search(eq_pattern, raw_response, re.IGNORECASE)
        if eq_match:
            result["evidence_quality"] = eq_match.group(1).upper()

        # ── Extract CITATIONS ────────────────────────────────────────
        citations_pattern = r"CITATIONS:\s*(.*?)(?=EVIDENCE QUALITY:|$)"
        citations_match = re.search(citations_pattern, raw_response, re.IGNORECASE | re.DOTALL)
        if citations_match:
            citations_text = citations_match.group(1).strip()
            result["citations"] = _parse_citations(citations_text)

    except Exception as e:
        print(f"⚠️ Parsing error: {e}. Using raw response.")
        result["reasoning"] = raw_response

    return result


def _parse_citations(citations_text: str) -> list:
    """
    Parses the citations section into a list of citation dicts.
    Handles both numbered and bulleted citation formats.
    """
    citations = []
    lines = citations_text.strip().split("\n")

    for line in lines:
        line = line.strip()
        # Skip empty lines or "None" / "No sources found" type lines
        if not line or line.lower() in ["none", "no sources found", "n/a"]:
            continue

        # Remove leading numbers/bullets: "1.", "2.", "-", "•"
        line = re.sub(r"^[\d\.\-\•\*]+\s*", "", line).strip()

        if not line:
            continue

        # Try to extract URL from the line
        url_match = re.search(r"https?://[^\s\)]+", line)
        url = url_match.group(0) if url_match else ""

        # Remove URL from line to get source name + snippet
        clean_line = re.sub(r"https?://[^\s\)]+", "", line).strip(" -:()[]")

        # Split on " - " or ": " to separate source name from snippet
        parts = re.split(r"\s[-:]\s", clean_line, maxsplit=1)
        source = parts[0].strip() if parts else clean_line
        snippet = parts[1].strip() if len(parts) > 1 else ""

        if source:
            citations.append({
                "source": source,
                "url": url,
                "snippet": snippet
            })

    return citations


def get_verdict_display(verdict: str) -> dict:
    """
    Returns display config (emoji, color, label) for a given verdict.
    Used by Streamlit UI to color-code results.
    """
    return VERDICT_CONFIG.get(
        verdict.upper(),
        VERDICT_CONFIG["NOT ENOUGH EVIDENCE"]
    )
