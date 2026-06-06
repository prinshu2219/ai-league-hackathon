"""
utils/bias_detection.py
-----------------------
Detects potential source bias and evidence imbalance before final verdict display.

Checks:
  - Source tier distribution (too many Tier 4 / low-trust sources)
  - Single-source dominance (one domain provides >60% of citations)
  - Insufficient source diversity (< 2 distinct domains)
  - Confidence cap recommendation when bias signals are strong
"""

from dataclasses import dataclass, field
from urllib.parse import urlparse

from utils.source_credibility import get_source_tier, get_credibility_label


@dataclass
class BiasReport:
    warnings: list = field(default_factory=list)
    tier_distribution: dict = field(default_factory=dict)
    domain_counts: dict = field(default_factory=dict)
    diversity_score: float = 1.0
    confidence_cap: str = "HIGH"
    bias_detected: bool = False


def _extract_domain(url: str) -> str:
    if not url:
        return "unknown"
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return (parsed.netloc or "unknown").lower().replace("www.", "")
    except Exception:
        return "unknown"


def analyze_source_bias(citations: list, evidence_text: str = "") -> BiasReport:
    """
    Analyze citation list and evidence for bias signals.
    Returns BiasReport with warnings and recommended confidence cap.
    """
    report = BiasReport()

    if not citations:
        report.warnings.append("No citations available — verdict relies on limited evidence.")
        report.diversity_score = 0.0
        report.confidence_cap = "LOW"
        report.bias_detected = True
        return report

    tiers = []
    domains = []

    for c in citations:
        url = c.get("url", "")
        tier = get_source_tier(url)
        tiers.append(tier)
        domain = _extract_domain(url)
        domains.append(domain)
        report.tier_distribution[tier] = report.tier_distribution.get(tier, 0) + 1
        report.domain_counts[domain] = report.domain_counts.get(domain, 0) + 1

    total = len(citations)
    tier4_pct = report.tier_distribution.get(4, 0) / total
    tier1_pct = report.tier_distribution.get(1, 0) / total

    # Diversity score: 1.0 = many distinct domains + mix of tiers
    unique_domains = len(set(d for d in domains if d != "unknown"))
    report.diversity_score = min(1.0, (unique_domains / max(total, 1)) * 0.5 + (1 - tier4_pct) * 0.5)

    # ── Bias signals ──────────────────────────────────────────────────────
    if tier4_pct > 0.5:
        report.warnings.append(
            f"⚠️ Source bias: {int(tier4_pct * 100)}% of citations are low-trust (Tier 4) sources."
        )
        report.bias_detected = True
        report.confidence_cap = "MEDIUM"

    if unique_domains < 2 and total >= 2:
        report.warnings.append(
            "⚠️ Low source diversity: citations come from fewer than 2 distinct domains."
        )
        report.bias_detected = True
        report.confidence_cap = "MEDIUM"

    # Single domain dominance
    if report.domain_counts:
        top_domain, top_count = max(report.domain_counts.items(), key=lambda x: x[1])
        if top_count / total > 0.6 and top_domain != "unknown":
            report.warnings.append(
                f"⚠️ Single-source dominance: {top_domain} provides {int(top_count/total*100)}% of citations."
            )
            report.bias_detected = True
            report.confidence_cap = "MEDIUM"

    if tier1_pct == 0 and total >= 3:
        report.warnings.append(
            "⚠️ No authoritative (Tier 1) sources cited — consider seeking official sources."
        )
        report.bias_detected = True

    if tier4_pct > 0.7:
        report.confidence_cap = "LOW"

    return report


def apply_confidence_cap(current_confidence: str, bias_report: BiasReport) -> str:
    """Lower confidence if bias signals detected (never increase above LLM value)."""
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    current = order.get(current_confidence.upper(), 0)
    cap = order.get(bias_report.confidence_cap, 2)
    if current > cap:
        final = [k for k, v in order.items() if v == cap][0]
        return final
    return current_confidence.upper()
