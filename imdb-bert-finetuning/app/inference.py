from __future__ import annotations

import math
from pathlib import Path
from typing import Sequence


LABELS = {0: "negative", 1: "positive"}


def label_from_id(label_id: int) -> str:
    try:
        return LABELS[label_id]
    except KeyError as exc:
        raise ValueError(f"unknown label id: {label_id}") from exc


def softmax(values: Sequence[float]) -> list[float]:
    max_value = max(values)
    exps = [math.exp(value - max_value) for value in values]
    total = sum(exps)
    return [value / total for value in exps]


def prediction_from_logits(logits: Sequence[float]) -> dict:
    if len(logits) != 2:
        raise ValueError("binary sentiment logits must contain exactly two values")
    probabilities = softmax([float(value) for value in logits])
    label_id = 1 if probabilities[1] >= probabilities[0] else 0
    return {
        "label": label_from_id(label_id),
        "label_id": label_id,
        "confidence": round(probabilities[label_id], 4),
        "probabilities": {
            "negative": round(probabilities[0], 4),
            "positive": round(probabilities[1], 4),
        },
    }


def load_pipeline(model_dir: str | Path):
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "Install project dependencies with `pip install -r requirements.txt` "
            "before running inference."
        ) from exc

    model_dir = Path(model_dir)
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.eval()
    return tokenizer, model, torch


def predict_text(text: str, model_dir: str | Path = "artifacts/model", max_length: int = 256) -> dict:
    tokenizer, model, torch = load_pipeline(model_dir)
    encoded = tokenizer(
        text,
        truncation=True,
        padding="max_length",
        max_length=max_length,
        return_tensors="pt",
    )
    with torch.no_grad():
        outputs = model(**encoded)
    return prediction_from_logits(outputs.logits[0].detach().cpu().tolist())
