import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.inference import predict_text


st.set_page_config(page_title="IMDb BERT Sentiment", layout="centered")

st.title("IMDb BERT Sentiment Classifier")

model_dir = st.sidebar.text_input("Model directory", "artifacts/model")
max_length = st.sidebar.slider("Max sequence length", 64, 512, 256, step=64)

review = st.text_area(
    "Movie review",
    value="The acting was excellent, the story was moving, and I would happily watch it again.",
    height=180,
)

if st.button("Predict sentiment", type="primary"):
    try:
        result = predict_text(review, model_dir=model_dir, max_length=max_length)
        st.metric("Sentiment", result["label"].upper(), f"{result['confidence']:.1%} confidence")
        st.progress(result["probabilities"]["positive"])
        st.json(result["probabilities"])
    except Exception as exc:
        st.error(str(exc))
