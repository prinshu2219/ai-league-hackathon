"""
utils/guardrails.py
-------------------
Five-layer guardrail pipeline for Claim Verifier.

Layer 1 — Input validation (length, injection patterns, PII masking)
Layer 2 — Prompt constraints (defined in rag_engine/prompts.py)
Layer 3 — Context grounding (two-phase agent in rag_engine/agent.py)
Layer 4 — Output validation (parse, citation URL check, PII leak scan, bias)
Layer 5 — Transparency metadata (guardrail audit trail for UI)
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional

from utils.pii_masking import mask_pii, validate_output_no_pii_leak, PIIMaskResult
from utils.bias_detection import analyze_source_bias, apply_confidence_cap


MAX_CLAIM_LENGTH = int(os.getenv("MAX_CLAIM_LENGTH", "2000"))

# Common prompt-injection phrases — flag and strip from active instruction path
INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"ignore\s+(all\s+)?prior\s+instructions",
        r"disregard\s+(all\s+)?(previous|above)",
        r"you\s+are\s+now\s+",
        r"new\s+instructions\s*:",
        r"system\s*:\s*",
        r"<\s*/?\s*system\s*>",
        r"do\s+not\s+(fact.?check|verify|search)",
        r"for\s+a\s+creative\s+writing",
        r"with\s+no\s+rules",
        r"return\s+verdict\s*:\s*true",
        r"jailbreak",
    ]
]


@dataclass
class InputGuardrailResult:
    allowed: bool
    claim_for_processing: str
    original_claim: str
    pii_result: Optional[PIIMaskResult] = None
    warnings: list = field(default_factory=list)
    block_reason: Optional[str] = None
    injection_detected: bool = False


@dataclass
class OutputGuardrailResult:
    result: dict
    citations_removed: list = field(default_factory=list)
    pii_leak_detected: bool = False
    guardrail_warnings: list = field(default_factory=list)


def _detect_prompt_injection(text: str) -> tuple[bool, list]:
    warnings = []
    detected = False
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            detected = True
            warnings.append(f"Prompt injection pattern detected: '{pattern.pattern[:40]}...'")
    return detected, warnings


def run_input_guardrails(claim: str) -> InputGuardrailResult:
    """
    Layer 1 — validate and sanitize user claim before any LLM call.
    """
    original = claim.strip()

    if not original:
        return InputGuardrailResult(
            allowed=False,
            claim_for_processing="",
            original_claim=original,
            block_reason="Claim cannot be empty.",
        )

    if len(original) > MAX_CLAIM_LENGTH:
        return InputGuardrailResult(
            allowed=False,
            claim_for_processing="",
            original_claim=original,
            block_reason=f"Claim exceeds maximum length of {MAX_CLAIM_LENGTH} characters.",
        )

    warnings = []
    injection_detected, injection_warnings = _detect_prompt_injection(original)
    warnings.extend(injection_warnings)

    # PII: block high-risk; mask rest before sending to OpenAI/Tavily
    pii_result = mask_pii(original)
    if pii_result.blocked:
        return InputGuardrailResult(
            allowed=False,
            claim_for_processing="",
            original_claim=original,
            pii_result=pii_result,
            block_reason=pii_result.block_reason,
        )

    claim_for_llm = pii_result.masked_text
    if pii_result.found_types:
        warnings.append(
            f"PII masked before API calls: {', '.join(pii_result.found_types)}"
        )

    return InputGuardrailResult(
        allowed=True,
        claim_for_processing=claim_for_llm,
        original_claim=original,
        pii_result=pii_result,
        warnings=warnings,
        injection_detected=injection_detected,
    )


def extract_evidence_urls(evidence_text: str) -> set:
    """Collect all URLs present in agent evidence for citation validation."""
    pattern = re.compile(r"https?://[^\s\]\)\"\'<>]+")
    return set(pattern.findall(evidence_text or ""))


def validate_citations_against_evidence(citations: list, evidence_urls: set) -> tuple[list, list]:
    """
    Layer 4 — remove citation URLs that never appeared in retrieved evidence (hallucination catch).
    URLs without evidence match are dropped; empty-url citations kept if source name present.
    """
    validated = []
    removed = []

    for c in citations:
        url = (c.get("url") or "").strip()
        if not url:
            validated.append(c)
            continue

        # Normalize for comparison (strip trailing punctuation)
        url_clean = url.rstrip(".,;)")

        if evidence_urls and not any(
            url_clean in ev or ev in url_clean for ev in evidence_urls
        ):
            removed.append({"url": url, "source": c.get("source", ""), "reason": "URL not in evidence"})
            continue

        validated.append(c)

    return validated, removed


def run_output_guardrails(
    result: dict,
    evidence_text: str,
    pii_lookup: dict,
) -> OutputGuardrailResult:
    """
    Layer 4 + 5 — validate parsed verdict, citations, PII leaks, bias; attach audit metadata.
    """
    guardrail_warnings = []
    output_text = " ".join([
        result.get("reasoning", ""),
        str(result.get("citations", [])),
        result.get("raw_response", ""),
    ])

    # PII leak validation (Layer 4)
    pii_clean, leaked = validate_output_no_pii_leak(output_text, pii_lookup)
    pii_leak_detected = not pii_clean
    if pii_leak_detected:
        guardrail_warnings.append(
            f"PII validation failed — possible leak detected: {', '.join(leaked)}. Reasoning redacted."
        )
        result["reasoning"] = "[Response withheld: potential sensitive information detected.]"
        result["confidence"] = "LOW"

    # Citation URL validation (Layer 4)
    evidence_urls = extract_evidence_urls(evidence_text)
    citations, removed = validate_citations_against_evidence(
        result.get("citations", []), evidence_urls
    )
    result["citations"] = citations
    if removed:
        guardrail_warnings.append(
            f"Removed {len(removed)} citation(s) not found in retrieved evidence (anti-hallucination)."
        )
        if result.get("confidence") == "HIGH":
            result["confidence"] = "MEDIUM"

    # Bias detection (Layer 4)
    bias_report = analyze_source_bias(citations, evidence_text)
    guardrail_warnings.extend(bias_report.warnings)
    result["confidence"] = apply_confidence_cap(result.get("confidence", "LOW"), bias_report)

    if bias_report.bias_detected and result.get("evidence_quality") == "STRONG":
        result["evidence_quality"] = "WEAK"

    # Layer 5 — transparency / audit metadata
    result["safety_metadata"] = {
        "guardrail_layers_applied": [
            "input_validation",
            "prompt_constraints",
            "context_grounding",
            "output_validation",
            "transparency",
        ],
        "pii_masked_types": list(pii_lookup.keys()) if pii_lookup else [],
        "pii_leak_detected": pii_leak_detected,
        "citations_removed_count": len(removed),
        "citations_removed": removed,
        "bias_detected": bias_report.bias_detected,
        "source_diversity_score": round(bias_report.diversity_score, 2),
        "tier_distribution": bias_report.tier_distribution,
        "guardrail_warnings": guardrail_warnings,
    }

    return OutputGuardrailResult(
        result=result,
        citations_removed=removed,
        pii_leak_detected=pii_leak_detected,
        guardrail_warnings=guardrail_warnings,
    )


def build_blocked_result(original_claim: str, block_reason: str, warnings: list = None) -> dict:
    """Safe response when Layer 1 blocks processing."""
    return {
        "claim": original_claim,
        "verdict": "NOT ENOUGH EVIDENCE",
        "confidence": "LOW",
        "reasoning": block_reason,
        "citations": [],
        "evidence_quality": "NONE",
        "agent_steps": [],
        "blocked_by_guardrails": True,
        "safety_metadata": {
            "guardrail_layers_applied": ["input_validation"],
            "block_reason": block_reason,
            "guardrail_warnings": warnings or [],
        },
    }
