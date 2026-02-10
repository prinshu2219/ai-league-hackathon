"""
utils/source_credibility.py
----------------------------
Scores sources by credibility tier so the AI weighs them properly.

WHY THIS MATTERS:
Without credibility scoring, the AI treats:
  Reddit post == BBC News == WHO report
That's wrong. A WHO report should carry far more weight.

TIERS:
  Tier 1 — Authoritative  (score: 1.0) → Official bodies, major wire services
  Tier 2 — Reliable       (score: 0.75) → Major newspapers, Wikipedia
  Tier 3 — Moderate       (score: 0.5)  → Regional news, smaller outlets
  Tier 4 — Low trust      (score: 0.25) → Blogs, forums, unknown sites
"""

# ── TIER 1: Authoritative sources ────────────────────────────────────────────
# Official bodies, major international wire services, scientific institutions
TIER_1_SOURCES = [
    # International bodies
    "who.int", "un.org", "worldbank.org", "imf.org",
    "unicef.org", "unesco.org",

    # Government / official
    "nasa.gov", "cdc.gov", "nih.gov", "meity.gov.in",
    "isro.gov.in", "pib.gov.in",

    # Major wire services (most reliable for breaking news)
    "reuters.com", "apnews.com", "afp.com",

    # Sports official bodies
    "icc-cricket.com", "fifa.com", "olympics.com",
    "nfl.com", "nba.com", "bcci.tv",
]

# ── TIER 2: Reliable sources ──────────────────────────────────────────────────
# Major international/national newspapers, fact-check sites, Wikipedia
TIER_2_SOURCES = [
    # International newspapers
    "bbc.com", "bbc.co.uk", "theguardian.com",
    "nytimes.com", "washingtonpost.com", "wsj.com",
    "economist.com", "ft.com", "bloomberg.com",

    # Indian major newspapers
    "thehindu.com", "hindustantimes.com", "indianexpress.com",
    "ndtv.com", "timesofindia.com", "livemint.com",

    # Fact-check sites
    "snopes.com", "factcheck.org", "politifact.com",
    "altnews.in", "boomlive.in",

    # Reference
    "wikipedia.org", "britannica.com",

    # Sports news
    "espn.com", "espncricinfo.com", "skysports.com",
    "cricbuzz.com", "sports.ndtv.com",
]

# ── TIER 3: Moderate sources ──────────────────────────────────────────────────
# Regional news outlets, smaller but legitimate sites
TIER_3_SOURCES = [
    "indiatoday.in", "scroll.in", "thewire.in",
    "firstpost.com", "business-standard.com",
    "deccanherald.com", "tribuneindia.com",
    "cnbc.com", "foxnews.com", "cnn.com",
    "timesofisrael.com", "aljazeera.com",
]

# Everything else is Tier 4 (blogs, forums, unknown)


def get_source_tier(url: str) -> int:
    """
    Returns the credibility tier (1-4) for a given URL.

    Args:
        url: The source URL to check

    Returns:
        1 = Most trusted, 4 = Least trusted

    Example:
        get_source_tier("https://reuters.com/...")  → 1
        get_source_tier("https://bbc.com/...")      → 2
        get_source_tier("https://reddit.com/...")   → 4
    """
    if not url:
        return 4

    url_lower = url.lower()

    for domain in TIER_1_SOURCES:
        if domain in url_lower:
            return 1

    for domain in TIER_2_SOURCES:
        if domain in url_lower:
            return 2

    for domain in TIER_3_SOURCES:
        if domain in url_lower:
            return 3

    return 4  # Unknown / blog / forum


def get_credibility_score(url: str) -> float:
    """
    Returns a 0.0-1.0 credibility score for a URL.

    Example:
        get_credibility_score("https://who.int/...")   → 1.0
        get_credibility_score("https://bbc.com/...")   → 0.75
        get_credibility_score("https://reddit.com/")   → 0.25
    """
    tier_scores = {1: 1.0, 2: 0.75, 3: 0.5, 4: 0.25}
    return tier_scores[get_source_tier(url)]


def get_credibility_label(url: str) -> str:
    """
    Returns a human-readable credibility label for display in UI.

    Example:
        get_credibility_label("https://reuters.com/") → "🟢 Authoritative"
        get_credibility_label("https://bbc.com/")     → "🟢 Reliable"
        get_credibility_label("https://reddit.com/")  → "🔴 Low Trust"
    """
    tier = get_source_tier(url)
    labels = {
        1: "🟢 Authoritative",
        2: "🟢 Reliable",
        3: "🟡 Moderate",
        4: "🔴 Low Trust"
    }
    return labels[tier]


def build_credibility_context(citations: list) -> str:
    """
    Builds a credibility summary string to append to the verification prompt.
    Tells GPT-4o how much to trust each source.

    Args:
        citations: List of citation dicts with 'url' and 'source' keys

    Returns:
        Formatted string describing source credibility tiers

    Example output:
        SOURCE CREDIBILITY GUIDE:
        - Reuters (reuters.com) → Tier 1: Authoritative ✅
        - Some Blog (blog.com)  → Tier 4: Low Trust ⚠️
    """
    if not citations:
        return ""

    lines = ["SOURCE CREDIBILITY GUIDE (prefer higher tier sources):"]
    for c in citations:
        url    = c.get("url", "")
        source = c.get("source", "Unknown")
        tier   = get_source_tier(url)
        label  = get_credibility_label(url)
        lines.append(f"  - {source} → Tier {tier}: {label}")

    return "\n".join(lines)