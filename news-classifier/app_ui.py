"""
Streamlit UI for News Classifier — demo + interview evidence.
Run: streamlit run app_ui.py
"""

import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="News Classifier", page_icon="📰", layout="wide")

st.title("📰 News Classifier")
st.caption("OpenAI + Anthropic fallback · LangChain LCEL · Exponential backoff · Tier rate limits")

with st.sidebar:
    st.header("Settings")
    user_id = st.text_input("User ID", value="demo-user")
    tier = st.selectbox("Tier", ["free", "paid"])
    use_chain = st.checkbox("Use LangChain LCEL chain", value=True)
    st.divider()
    st.markdown("**Architecture**")
    st.markdown("- Domain router → LLM → Anthropic fallback")
    st.markdown("- Exponential backoff on 429")
    st.markdown("- Context compaction for long articles")
    st.markdown(f"- Free: 10 RPM · Paid: 100 RPM")

col1, col2 = st.columns(2)

with col1:
    headline = st.text_input(
        "Headline",
        value="India wins cricket series against Australia",
    )

with col2:
    category_hint = st.selectbox(
        "Try an example",
        ["Custom", "Sports", "Tech", "Politics", "Business"],
    )

EXAMPLES = {
    "Sports": ("India wins cricket series", "The team scored 350 runs in the final test match at Melbourne."),
    "Tech": ("OpenAI launches new model", "The AI company released GPT-4o-mini with improved speed and lower cost."),
    "Politics": ("Election results announced", "The ruling party secured a majority in parliament with 290 seats."),
    "Business": ("Stock market hits record high", "Nifty 50 crossed 25000 as IT stocks rallied on strong earnings."),
}

if category_hint != "Custom":
    headline, body_default = EXAMPLES[category_hint]
    st.session_state.setdefault("body", body_default)

body = st.text_area(
    "Article body",
    value=st.session_state.get("body", "The team scored 350 runs in the final test match."),
    height=200,
)

if st.button("Classify", type="primary", use_container_width=True):
    with st.spinner("Classifying..."):
        try:
            resp = requests.post(
                f"{API_URL}/classify",
                json={
                    "headline": headline,
                    "body": body,
                    "user_id": user_id,
                    "tier": tier,
                    "use_chain": use_chain,
                },
                timeout=60,
            )

            if resp.status_code == 429:
                st.error("Rate limit exceeded — wait 1 minute or switch to paid tier.")
            elif resp.status_code != 200:
                st.error(f"Error {resp.status_code}: {resp.text}")
            else:
                data = resp.json()
                result = data["result"]

                colors = {
                    "sports": "🟢", "tech": "🔵",
                    "politics": "🟠", "business": "🟡",
                }
                emoji = colors.get(result["category"], "⚪")

                st.success(f"{emoji} **{result['category'].upper()}** — confidence {result['confidence']:.0%}")
                st.info(result["summary"])

                with st.expander("Technical details (for interview)"):
                    st.json({
                        "provider": result["provider"],
                        "method": result["method"],
                        "tokens_used": data.get("tokens_used"),
                        "article_compacted": data.get("article_compacted"),
                        "chunks_used": data.get("chunks_used"),
                        "rate_limit_remaining": data.get("rate_limit_remaining"),
                        "openai_extraction": "response.choices[0].message.content",
                        "anthropic_extraction": "message.content[0].text",
                        "langchain_chain": "prompt | llm | parser",
                    })

        except requests.exceptions.ConnectionError:
            st.warning(
                "API not running. Start it with:\n\n"
                "`uvicorn app.api:app --reload --port 8000`"
            )

st.divider()
st.markdown(
    "**Interview project:** Core LLM Frameworks · "
    "Raw SDK + LangChain + backoff + secrets + rate limits"
)
