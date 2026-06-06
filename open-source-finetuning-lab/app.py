#!/usr/bin/env python3
"""Streamlit demo for the local LoRA emotion classifier."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import streamlit as st

from osft_lab.config import LABEL_NAMES, TrainingConfig
from osft_lab.device import describe_device, select_best_device
from osft_lab.inference import load_classifier, predict_text


@st.cache_resource(show_spinner=False)
def _load_model(model_dir: str, base_model_name: str):
    return load_classifier(model_dir, base_model_name, LABEL_NAMES)


def main() -> None:
    st.set_page_config(page_title="Open Source Fine-Tuning Lab", layout="wide")
    st.title("Open Source Fine-Tuning Lab")

    model_dir = st.sidebar.text_input("Adapter path", str(TrainingConfig.output_dir))
    base_model = st.sidebar.text_input("Base model", TrainingConfig.base_model_name)
    device = select_best_device()
    st.sidebar.json(describe_device())

    adapter_path = Path(model_dir)
    if not adapter_path.exists():
        st.warning(
            "No trained adapter found yet. Run "
            "`python3 scripts/train_lora_classifier.py --smoke` from this project directory."
        )
        st.stop()

    tokenizer, model = _load_model(model_dir, base_model)
    id2label = {index: label for index, label in enumerate(LABEL_NAMES)}

    text = st.text_area(
        "Text",
        "I finally finished the interview preparation project and I feel confident.",
        height=120,
    )

    if st.button("Classify", type="primary"):
        result = predict_text(text, tokenizer, model, device, id2label)
        left, right = st.columns([1, 2])
        with left:
            st.metric("Prediction", result["top"]["label"])
            st.metric("Confidence", f"{result['top']['score']:.3f}")
            st.caption(f"Device: {device}")
        with right:
            st.bar_chart(
                {
                    item["label"]: item["score"]
                    for item in result["probabilities"]
                }
            )

        with st.expander("Tokenizer Output"):
            st.write(result["tokens"])
        with st.expander("Raw Logits"):
            st.write(result["logits"])


if __name__ == "__main__":
    main()
