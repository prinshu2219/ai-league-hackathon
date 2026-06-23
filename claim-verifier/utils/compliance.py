"""
utils/compliance.py
-------------------
Organizational compliance controls, audit logging, and regulatory metadata.

Covers:
  - Data privacy (GDPR, DPDP Act) — minimization, PII masking, processor disclosure
  - Auditability — redacted JSONL audit trail
  - Explainability — structured verdict fields flagged for regulators
  - EU AI Act — limited-risk transparency classification
  - Human oversight — sensitive topic flagging for review queue
"""

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Regulatory constants ───────────────────────────────────────────────────────

AI_DISCLOSURE_TEXT = (
    "You are using an AI-powered fact-checking tool. Results may contain errors. "
    "Always verify critical claims with primary sources."
)

EU_AI_ACT_RISK_CATEGORY = "limited_risk"  # Chatbot / AI interaction transparency required

DATA_PROCESSORS = [
    {"name": "OpenAI", "purpose": "LLM inference + embeddings", "region": "US"},
    {"name": "Tavily", "purpose": "Live web search", "region": "US"},
]

# Sensitive topics → recommend human review when confidence is not HIGH
SENSITIVE_TOPIC_PATTERNS = {
    "health": re.compile(
        r"\b(vaccine|covid|cancer|diagnosis|medicine|drug|fda|who|cdc|"
        r"infertility|treatment|symptom|disease|pandemic)\b",
        re.IGNORECASE,
    ),
    "elections": re.compile(
        r"\b(election|vote|voting|ballot|president|prime minister|"
        r"democrat|republican|bjp|congress party|poll result)\b",
        re.IGNORECASE,
    ),
    "legal": re.compile(
        r"\b(guilty|innocent|convicted|sentenced|court ruling|"
        r"lawsuit|indictment|arrested for)\b",
        re.IGNORECASE,
    ),
    "financial": re.compile(
        r"\b(stock price|insider trading|sec filing|bankruptcy|"
        r"market crash|crypto scam)\b",
        re.IGNORECASE,
    ),
}

AUDIT_LOG_DIR = Path(__file__).resolve().parent.parent / "data" / "audit_logs"


def detect_sensitive_topics(text: str) -> list[str]:
    """Return topic categories that may require human oversight."""
    if not text:
        return []
    return [
        topic
        for topic, pattern in SENSITIVE_TOPIC_PATTERNS.items()
        if pattern.search(text)
    ]


def build_compliance_controls_status() -> dict:
    """
    Scorecard of compliance controls — implemented vs planned.
    Used in UI and interview discussions.
    """
    return {
        "data_privacy": {
            "pii_masking_before_apis": {"status": "implemented", "file": "utils/pii_masking.py"},
            "high_risk_pii_block": {"status": "implemented", "file": "utils/pii_masking.py"},
            "data_minimization_no_persistent_claims": {"status": "implemented", "note": "Stateless per request"},
            "user_consent_flow": {"status": "planned", "note": "Privacy policy + opt-in for production"},
            "dpa_with_processors": {"status": "planned", "note": "OpenAI/Tavily DPAs for enterprise"},
            "gdpr_right_to_deletion": {"status": "planned", "note": "Audit log retention policy"},
            "dpdp_act_consent": {"status": "planned", "note": "India DPDP 2023 consent banner"},
        },
        "auditability": {
            "agent_steps_in_ui": {"status": "implemented", "file": "app.py"},
            "downloadable_verdict_report": {"status": "implemented", "file": "app.py"},
            "safety_metadata_audit": {"status": "implemented", "file": "utils/guardrails.py"},
            "redacted_audit_log": {"status": "implemented", "file": "utils/compliance.py"},
            "immutable_server_logs": {"status": "planned", "note": "CloudWatch / immutable S3"},
        },
        "explainability": {
            "reasoning_field": {"status": "implemented", "file": "rag_engine/prompts.py"},
            "citations_with_urls": {"status": "implemented", "file": "utils/output_parser.py"},
            "confidence_and_evidence_quality": {"status": "implemented", "file": "utils/output_parser.py"},
            "source_credibility_tiers": {"status": "implemented", "file": "utils/source_credibility.py"},
        },
        "transparency": {
            "ai_disclosure_ui": {"status": "implemented", "file": "app.py"},
            "eu_ai_act_limited_risk": {"status": "implemented", "category": EU_AI_ACT_RISK_CATEGORY},
            "footer_disclaimer": {"status": "implemented", "file": "app.py"},
        },
        "security": {
            "api_keys_in_env": {"status": "implemented", "file": ".env.example"},
            "docker_isolation": {"status": "implemented", "file": "Dockerfile"},
            "owasp_llm_red_team_suite": {"status": "implemented", "file": "utils/red_team.py"},
            "user_authentication": {"status": "planned", "note": "Cognito/JWT for production"},
            "rate_limiting": {"status": "planned"},
        },
        "human_oversight": {
            "not_enough_evidence_verdict": {"status": "implemented", "file": "rag_engine/prompts.py"},
            "sensitive_topic_flagging": {"status": "implemented", "file": "utils/compliance.py"},
            "human_review_queue": {"status": "planned", "note": "Route flagged sessions to reviewers"},
        },
        "incident_response": {
            "guardrail_block_audit_trail": {"status": "implemented"},
            "incident_runbook": {"status": "planned", "note": "Wrong viral verdict escalation path"},
            "model_upgrade_regression": {"status": "implemented", "file": "scripts/run_red_team_suite.py"},
        },
    }


def _redact_claim_for_log(claim: str, pii_tokens: list = None) -> str:
    """Never store raw PII in audit logs — truncate and note if masked."""
    if not claim:
        return ""
    preview = claim[:120] + ("..." if len(claim) > 120 else "")
    if pii_tokens:
        return f"[REDACTED_CLAIM len={len(claim)} pii_tokens={len(pii_tokens)}] {preview[:60]}..."
    return preview


def write_audit_log(
    result: dict,
    session_id: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> Optional[str]:
    """
    Append redacted audit entry to data/audit_logs/verification_audit.jsonl.
    Returns log file path if written, else None.
    """
    if enabled is None:
        enabled = os.getenv("ENABLE_AUDIT_LOG", "true").strip().lower() in ("1", "true", "yes")
    if not enabled:
        return None

    AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = AUDIT_LOG_DIR / "verification_audit.jsonl"

    safety = result.get("safety_metadata", {})
    compliance = result.get("compliance_metadata", {})

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id or str(uuid.uuid4()),
        "claim_redacted": _redact_claim_for_log(
            result.get("claim", ""),
            safety.get("pii_masked_types"),
        ),
        "verdict": result.get("verdict"),
        "confidence": result.get("confidence"),
        "evidence_quality": result.get("evidence_quality"),
        "blocked_by_guardrails": result.get("blocked_by_guardrails", False),
        "citation_count": len(result.get("citations", [])),
        "agent_step_count": len(result.get("agent_steps", [])),
        "guardrail_warnings_count": len(safety.get("guardrail_warnings", [])),
        "bias_detected": safety.get("bias_detected", False),
        "pii_leak_detected": safety.get("pii_leak_detected", False),
        "citations_removed_count": safety.get("citations_removed_count", 0),
        "sensitive_topics": compliance.get("sensitive_topics", []),
        "human_review_recommended": compliance.get("human_review_recommended", False),
        "eu_ai_act_category": compliance.get("eu_ai_act_risk_category"),
        "data_processors": [p["name"] for p in DATA_PROCESSORS],
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return str(log_path)


def attach_compliance_metadata(
    result: dict,
    original_claim: str,
    session_id: Optional[str] = None,
) -> dict:
    """
    Attach compliance_metadata to verification result for UI and audit.
    """
    sensitive = detect_sensitive_topics(original_claim)
    confidence = result.get("confidence", "LOW")
    verdict = result.get("verdict", "NOT ENOUGH EVIDENCE")

    human_review = bool(sensitive) and (
        confidence != "HIGH"
        or verdict in ("PARTIALLY TRUE", "NOT ENOUGH EVIDENCE")
        or result.get("safety_metadata", {}).get("bias_detected")
    )

    result["compliance_metadata"] = {
        "ai_disclosure": AI_DISCLOSURE_TEXT,
        "eu_ai_act_risk_category": EU_AI_ACT_RISK_CATEGORY,
        "eu_ai_act_requirement": "Inform users they are interacting with AI (transparency obligation)",
        "regulations_addressed": {
            "GDPR": "PII masking, data minimization, processor list disclosed",
            "India_DPDP_Act_2023": "Purpose limitation (fact-check only), PII block/mask",
            "EU_AI_Act": f"{EU_AI_ACT_RISK_CATEGORY} — AI disclosure in UI",
            "CCPA": "No sale of personal data; claims not persisted by default",
        },
        "data_processors": DATA_PROCESSORS,
        "sensitive_topics": sensitive,
        "human_review_recommended": human_review,
        "human_review_reason": (
            f"Sensitive topic ({', '.join(sensitive)}) with {confidence} confidence"
            if human_review and sensitive
            else ("Low confidence or bias detected" if human_review else None)
        ),
        "audit_session_id": session_id or str(uuid.uuid4()),
        "controls_scorecard": build_compliance_controls_status(),
    }

    return result
