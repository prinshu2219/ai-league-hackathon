"""
utils/pii_masking.py
--------------------
Layered PII detection and masking before text is sent to external LLM APIs.

Layers:
  1. Regex — emails, phones, SSN/Aadhaar-style IDs, credit cards
  2. Token replacement — [EMAIL_1], [PHONE_1], etc. with secure lookup table
  3. Validation — re-scan LLM output; block if raw PII leaked through
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ── High-risk patterns → block processing entirely ───────────────────────────
HIGH_RISK_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "aadhaar": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
}

# ── Maskable patterns (replaced with tokens) ───────────────────────────────────
MASK_PATTERNS = {
    "email": re.compile(r"\b[\w.+-]+@[\w.-]+\.\w{2,}\b", re.IGNORECASE),
    "phone": re.compile(
        r"(?:\+?\d{1,3}[-.\s]?)?(?:\(\d{2,4}\)|\d{2,4})[-.\s]?\d{3,4}[-.\s]?\d{4}\b"
    ),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "ip_address": re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"),
}


@dataclass
class PIIMaskResult:
    masked_text: str
    lookup: dict = field(default_factory=dict)
    found_types: list = field(default_factory=list)
    blocked: bool = False
    block_reason: Optional[str] = None


def detect_high_risk_pii(text: str) -> tuple[bool, Optional[str]]:
    """Return (should_block, reason) for SSN/Aadhaar-style identifiers."""
    if not text:
        return False, None
    for name, pattern in HIGH_RISK_PATTERNS.items():
        if pattern.search(text):
            return True, f"High-risk PII detected ({name}). Remove sensitive IDs before verifying."
    return False, None


def mask_pii(text: str) -> PIIMaskResult:
    """
    Mask PII in text. Returns masked text + lookup table for authorized remasking.
    """
    blocked, reason = detect_high_risk_pii(text)
    if blocked:
        return PIIMaskResult(masked_text="", lookup={}, found_types=[], blocked=True, block_reason=reason)

    lookup: dict = {}
    counters = {k: 0 for k in MASK_PATTERNS}
    found_types: list = []
    masked = text

    for pii_type, pattern in MASK_PATTERNS.items():
        matches = list(pattern.finditer(masked))
        for match in matches:
            original = match.group(0)
            counters[pii_type] += 1
            token = f"[{pii_type.upper()}_{counters[pii_type]}]"
            lookup[token] = original
            if pii_type not in found_types:
                found_types.append(pii_type)
            masked = masked.replace(original, token, 1)

    return PIIMaskResult(
        masked_text=masked,
        lookup=lookup,
        found_types=found_types,
        blocked=False,
    )


def validate_output_no_pii_leak(output_text: str, input_lookup: dict) -> tuple[bool, list]:
    """
    Layer 3 validation: scan LLM output for PII that should have stayed masked.
    Returns (is_clean, list of leaked value types).
    """
    if not output_text:
        return True, []

    leaked = []

    # Check if any original PII values from input appear verbatim in output
    for token, original in input_lookup.items():
        if original and original in output_text:
            leaked.append(f"unmasked_{token}")

    # Regex second pass on output for patterns that may appear in LLM response
    for pii_type, pattern in {**MASK_PATTERNS, **HIGH_RISK_PATTERNS}.items():
        if pattern.search(output_text):
            if pii_type not in leaked:
                leaked.append(pii_type)

    return len(leaked) == 0, leaked


def remask_for_display(text: str, lookup: dict) -> str:
    """Replace tokens back with originals — for authorized internal audit only."""
    result = text
    for token, original in lookup.items():
        result = result.replace(token, "[REDACTED]")
    return result
