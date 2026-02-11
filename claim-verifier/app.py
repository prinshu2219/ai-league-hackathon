"""
app.py
------
Main Streamlit application — the UI for the Claim Verifier.

Run with:
    streamlit run app.py
"""

import streamlit as st
from urllib.parse import unquote_plus
from rag_engine.agent import verify_claim
from rag_engine.knowledge_base import get_kb_stats
from utils.output_parser import get_verdict_display
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Claim Verifier — AI Fact Checker",
    page_icon="🔍",
    layout="centered"
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS — Dark mode compatible
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* ── Verdict boxes ── */
    .verdict-box {
        padding: 18px 22px;
        border-radius: 10px;
        margin: 10px 0;
        font-size: 18px;
        font-weight: bold;
    }
    .verdict-true    { background-color: #1a3d2b; color: #6fcf97; border: 2px solid #27ae60; }
    .verdict-false   { background-color: #3d1a1a; color: #eb5757; border: 2px solid #e74c3c; }
    .verdict-partial { background-color: #3d3010; color: #f2c94c; border: 2px solid #f39c12; }
    .verdict-unknown { background-color: #2a2a2a; color: #bdbdbd; border: 2px solid #757575; }

    /* ── Citation cards ── */
    .citation-card {
        background-color: #1e2a3a;
        border: 1px solid #2d4a6e;
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 8px 0;
    }
    .citation-number {
        display: inline-block;
        background-color: #3b82f6;
        color: white;
        font-weight: bold;
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 12px;
        margin-bottom: 8px;
        letter-spacing: 0.5px;
    }
    .citation-source {
        color: #e2e8f0;
        font-weight: 600;
        font-size: 15px;
        margin: 6px 0 4px 0;
    }
    .citation-url a {
        color: #60a5fa;
        font-size: 13px;
        word-break: break-all;
        text-decoration: none;
    }
    .citation-url a:hover { text-decoration: underline; }
    .citation-snippet {
        color: #94a3b8;
        font-size: 13px;
        margin-top: 8px;
        font-style: italic;
        border-top: 1px solid #2d4a6e;
        padding-top: 8px;
        line-height: 1.5;
    }

    /* ── Agent thinking step cards ── */
    .step-card {
        background-color: #1a1f2e;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 10px 0;
    }
    .step-header {
        color: #a78bfa;
        font-weight: 700;
        font-size: 14px;
        margin-bottom: 10px;
        letter-spacing: 0.5px;
    }
    .step-label {
        color: #6b7280;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 10px;
        margin-bottom: 4px;
    }
    .step-query {
        color: #fbbf24;
        font-size: 13px;
        font-family: monospace;
        background-color: #2d2d2d;
        padding: 5px 10px;
        border-radius: 4px;
    }
    .step-result {
        color: #d1d5db;
        font-size: 12px;
        line-height: 1.6;
        font-family: monospace;
        background-color: #111827;
        padding: 10px 12px;
        border-radius: 4px;
        white-space: pre-wrap;
        word-break: break-word;
        max-height: 160px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ System Info")

    st.subheader("📚 Knowledge Base")
    kb_stats = get_kb_stats()

    if kb_stats["total_chunks"] == 0:
        st.warning("⚠️ Knowledge base is empty!\nRun: `python scripts/build_knowledge_base.py`")
    else:
        st.success(f"✅ {kb_stats['total_chunks']} chunks loaded")

    st.divider()

    st.subheader("🧠 How It Works")
    st.markdown("""
    1. **Submit** a claim
    2. Agent **searches** knowledge base
    3. Agent **searches** live web
    4. GPT-4o **analyzes** evidence
    5. **Verdict** with citations
    """)

    st.divider()

    st.subheader("📊 Verdict Guide")
    st.markdown("""
    - ✅ **TRUE** — Supported by evidence
    - ❌ **FALSE** — Contradicted by evidence
    - ⚠️ **PARTIALLY TRUE** — Mixed evidence
    - 🔍 **NOT ENOUGH EVIDENCE** — Can't verify
    """)

    st.divider()
    st.caption("Built with LangChain + GPT-4o + ChromaDB")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────────────────────────────────────

st.title("🔍 AI Claim Verifier")
st.markdown("*Fact-check any claim using AI-powered RAG with real-time web search*")
st.divider()

# ── Session state: keep claim text across runs (fixes reset on Verify click) ──
if "claim_text" not in st.session_state:
    st.session_state.claim_text = ""

# ── URL query param: pre-fill claim when opened from extension or shared link ──
url_claim = st.query_params.get("claim")
if url_claim is not None:
    st.session_state.claim_text = unquote_plus(url_claim)

# ── Example Claims ────────────────────────────────────────────────────────────

st.subheader("💡 Try an example claim:")

example_claims = [
    "India banned TikTok permanently in 2020",
    "Neil Armstrong walked on the Moon in 1969",
    "COVID-19 vaccines cause infertility",
    "India became the most populous country in 2023",
    "Arvind Kejriwal was arrested in 2024",
]

cols = st.columns(2)
selected_example = None

for i, example in enumerate(example_claims):
    col = cols[i % 2]
    if col.button(f"📌 {example[:45]}...", key=f"ex_{i}"):
        selected_example = example

# When user picks an example, store it so the text area shows it
if selected_example is not None:
    st.session_state.claim_text = selected_example

st.divider()

# ── Claim Input ───────────────────────────────────────────────────────────────

st.subheader("✍️ Or enter your own claim:")

# Use session state so claim is NOT cleared when Verify is clicked (same run re-renders with value="")
claim_input = st.text_area(
    label="Enter the claim to verify",
    value=st.session_state.claim_text,
    placeholder="e.g. The Earth is flat and NASA is hiding the truth...",
    height=100,
    label_visibility="collapsed",
    key="claim_input",
)
# Keep session state in sync with what user typed
st.session_state.claim_text = claim_input

verify_button = st.button(
    "🔍 Verify Claim",
    type="primary",
    use_container_width=True,
    disabled=not claim_input.strip(),
)


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICATION RESULT
# ─────────────────────────────────────────────────────────────────────────────

if verify_button and claim_input.strip():
    claim_to_verify = claim_input.strip()
    print(f"[App] Verify clicked — claim: {claim_to_verify[:80]}...")

    with st.spinner("🤖 Agent is researching the claim... This may take 15-30 seconds"):
        result = verify_claim(claim_to_verify)

    st.divider()

    # ── Verdict ───────────────────────────────────────────────────────────────
    verdict    = result.get("verdict", "NOT ENOUGH EVIDENCE")
    confidence = result.get("confidence", "LOW")
    display    = get_verdict_display(verdict)

    css_map = {
        "TRUE": "verdict-true",
        "FALSE": "verdict-false",
        "PARTIALLY TRUE": "verdict-partial",
        "NOT ENOUGH EVIDENCE": "verdict-unknown"
    }
    css_class = css_map.get(verdict, "verdict-unknown")

    st.markdown(f"""
    <div class="verdict-box {css_class}">
        {display['emoji']} VERDICT: {verdict} &nbsp;&nbsp;|&nbsp;&nbsp; Confidence: {confidence}
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"**📌 Claim:** *{result.get('claim', claim_input)}*")
    st.divider()

    # ── Reasoning ─────────────────────────────────────────────────────────────
    st.subheader("📝 Reasoning")
    st.markdown(result.get("reasoning", "*No reasoning available.*"))
    st.divider()

    # ── Citations ─────────────────────────────────────────────────────────────
    citations = result.get("citations", [])
    st.subheader(f"📚 Citations ({len(citations)} sources)")

    if citations:
        for i, citation in enumerate(citations, 1):
            source  = citation.get("source", "Unknown Source")
            url     = citation.get("url", "")
            snippet = citation.get("snippet", "")

            url_html     = f'<div class="citation-url"><a href="{url}" target="_blank">🔗 {url}</a></div>' if url else ""
            snippet_html = f'<div class="citation-snippet">"{snippet}"</div>' if snippet else ""

            st.markdown(f"""
            <div class="citation-card">
                <span class="citation-number">SOURCE {i}</span>
                <div class="citation-source">📰 {source}</div>
                {url_html}
                {snippet_html}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("🔍 No specific citations found. Verdict is based on AI analysis of available evidence.")

    st.divider()

    # ── Evidence Quality ──────────────────────────────────────────────────────
    eq = result.get("evidence_quality", "NONE")
    eq_emoji = {"STRONG": "🟢", "WEAK": "🟡", "NONE": "🔴"}.get(eq, "⚪")
    st.markdown(f"**Evidence Quality:** {eq_emoji} **{eq}**")
    st.divider()

    # ── Agent Thinking Steps ──────────────────────────────────────────────────
    agent_steps = result.get("agent_steps", [])

    if agent_steps:
        with st.expander(f"🧠 Show Agent Thinking ({len(agent_steps)} steps)", expanded=False):
            st.markdown("*Here's exactly how the agent researched this claim step by step:*")

            for i, step in enumerate(agent_steps, 1):
                tool    = step.get("tool_used", "unknown")
                query   = step.get("query", "")
                preview = step.get("result_preview", "No result preview available.")

                tool_emoji = "📚" if "knowledge" in tool else "🌐"
                tool_label = "Knowledge Base Search" if "knowledge" in tool else "Live Web Search"

                st.markdown(f"""
                <div class="step-card">
                    <div class="step-header">{tool_emoji} Step {i} — {tool_label}</div>
                    <div class="step-label">🔎 Search Query</div>
                    <div class="step-query">{query}</div>
                    <div class="step-label">📄 What Was Found</div>
                    <div class="step-result">{preview}</div>
                </div>
                """, unsafe_allow_html=True)

    # ── Download ──────────────────────────────────────────────────────────────
    st.divider()

    citation_lines = "\n".join([
        f"[{i+1}] {c.get('source', 'Unknown')} — {c.get('url', 'No URL')}"
        for i, c in enumerate(citations)
    ])

    summary_text = f"""CLAIM VERIFICATION RESULT
{'='*50}
CLAIM:      {result.get('claim', '')}
VERDICT:    {verdict}
CONFIDENCE: {confidence}
EVIDENCE:   {eq}

REASONING:
{result.get('reasoning', '')}

CITATIONS:
{citation_lines if citation_lines else 'No citations found'}
{'='*50}
Built with AI Claim Verifier | GPT-4o + LangChain + ChromaDB
""".strip()

    st.download_button(
        label="📥 Download Result",
        data=summary_text,
        file_name="claim_verification_result.txt",
        mime="text/plain"
    )


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────

st.divider()
st.caption("⚠️ This tool is AI-powered and may make mistakes. Always verify critical claims with primary sources.")
st.caption("Built for AI League Hackathon #1 | Powered by GPT-4o + LangChain + ChromaDB")