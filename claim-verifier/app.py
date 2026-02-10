"""
app.py
------
Main Streamlit application — the UI for the Claim Verifier.

Run with:
    streamlit run app.py

Features:
- Submit a claim for verification
- See verdict with color coding (True/False/Partial/Not Enough Evidence)
- View reasoning and citations
- Expandable "Show Agent Thinking" section for transparency
- Knowledge base stats in sidebar
"""

import streamlit as st
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
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .verdict-box {
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        font-size: 18px;
        font-weight: bold;
    }
    .verdict-true    { background-color: #d4edda; color: #155724; border: 2px solid #28a745; }
    .verdict-false   { background-color: #f8d7da; color: #721c24; border: 2px solid #dc3545; }
    .verdict-partial { background-color: #fff3cd; color: #856404; border: 2px solid #ffc107; }
    .verdict-unknown { background-color: #e2e3e5; color: #383d41; border: 2px solid #6c757d; }

    .citation-box {
        background-color: #f8f9fa;
        padding: 10px 15px;
        border-left: 4px solid #0d6efd;
        margin: 5px 0;
        border-radius: 0 5px 5px 0;
    }
    .step-box {
        background-color: #f0f0f0;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        font-family: monospace;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ System Info")

    # Knowledge Base Stats
    st.subheader("📚 Knowledge Base")
    kb_stats = get_kb_stats()

    if kb_stats["total_chunks"] == 0:
        st.warning("⚠️ Knowledge base is empty!\nRun: `python scripts/build_knowledge_base.py`")
    else:
        st.success(f"✅ {kb_stats['total_chunks']} chunks loaded")

    st.divider()

    # How it works
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

# ── Example Claims ───────────────────────────────────────────────────────────

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

st.divider()

# ── Claim Input ───────────────────────────────────────────────────────────────

st.subheader("✍️ Or enter your own claim:")

# Pre-fill with selected example if button was clicked
default_text = selected_example if selected_example else ""

claim_input = st.text_area(
    label="Enter the claim to verify",
    value=default_text,
    placeholder="e.g. The Earth is flat and NASA is hiding the truth...",
    height=100,
    label_visibility="collapsed"
)

verify_button = st.button(
    "🔍 Verify Claim",
    type="primary",
    use_container_width=True,
    disabled=not claim_input.strip()
)


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICATION LOGIC
# ─────────────────────────────────────────────────────────────────────────────

if verify_button and claim_input.strip():

    with st.spinner("🤖 Agent is researching the claim... This may take 15-30 seconds"):
        result = verify_claim(claim_input.strip())

    st.divider()

    # ── Verdict Display ───────────────────────────────────────────────────────

    verdict = result.get("verdict", "NOT ENOUGH EVIDENCE")
    confidence = result.get("confidence", "LOW")
    display = get_verdict_display(verdict)

    # Map verdict to CSS class
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

    # ── Claim Submitted ───────────────────────────────────────────────────────
    st.markdown(f"**📌 Claim:** *{result.get('claim', claim_input)}*")

    st.divider()

    # ── Reasoning ─────────────────────────────────────────────────────────────
    st.subheader("📝 Reasoning")
    reasoning = result.get("reasoning", "No reasoning provided.")
    st.markdown(reasoning if reasoning else "*No reasoning available.*")

    st.divider()

    # ── Citations ─────────────────────────────────────────────────────────────
    citations = result.get("citations", [])

    st.subheader(f"📚 Citations ({len(citations)} sources)")

    if citations:
        for i, citation in enumerate(citations, 1):
            source = citation.get("source", "Unknown")
            url = citation.get("url", "")
            snippet = citation.get("snippet", "")

            citation_html = f"""
            <div class="citation-box">
                <strong>[{i}] {source}</strong><br>
                {"<a href='" + url + "' target='_blank'>🔗 " + url + "</a><br>" if url else ""}
                {"<small>" + snippet + "</small>" if snippet else ""}
            </div>
            """
            st.markdown(citation_html, unsafe_allow_html=True)
    else:
        st.info("🔍 No specific citations found. The verdict is based on the AI's analysis of available evidence.")

    st.divider()

    # ── Evidence Quality Badge ────────────────────────────────────────────────
    eq = result.get("evidence_quality", "NONE")
    eq_colors = {"STRONG": "🟢", "WEAK": "🟡", "NONE": "🔴"}
    st.markdown(f"**Evidence Quality:** {eq_colors.get(eq, '⚪')} {eq}")

    # ── Agent Thinking Steps (Expandable) ─────────────────────────────────────
    agent_steps = result.get("agent_steps", [])

    if agent_steps:
        with st.expander(f"🧠 Show Agent Thinking ({len(agent_steps)} steps)", expanded=False):
            st.markdown("*Here's how the agent researched this claim:*")

            for i, step in enumerate(agent_steps, 1):
                tool = step.get("tool_used", "unknown")
                query = step.get("query", "")
                preview = step.get("result_preview", "")

                tool_emoji = "📚" if "knowledge" in tool else "🌐"

                st.markdown(f"""
                <div class="step-box">
                    <strong>Step {i}: {tool_emoji} {tool}</strong><br>
                    🔎 Query: <em>{query}</em><br>
                    📄 Result preview: {preview}
                </div>
                """, unsafe_allow_html=True)

    # ── Share / Copy Result ───────────────────────────────────────────────────
    st.divider()

    summary_text = f"""
CLAIM: {result.get('claim', '')}
VERDICT: {verdict}
CONFIDENCE: {confidence}
REASONING: {result.get('reasoning', '')}
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
