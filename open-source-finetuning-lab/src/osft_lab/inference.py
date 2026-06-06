"""Inference helpers shared by CLI evaluation and Streamlit."""

import math
from typing import Any, Dict, Iterable, List


def softmax(values: Iterable[float]) -> List[float]:
    logits = list(values)
    if not logits:
        return []
    max_logit = max(logits)
    exp_values = [math.exp(value - max_logit) for value in logits]
    total = sum(exp_values)
    return [value / total for value in exp_values]


def top_prediction(logits: Iterable[float], id2label: Dict[int, str]) -> Dict[str, float]:
    probabilities = softmax(logits)
    best_index = max(range(len(probabilities)), key=probabilities.__getitem__)
    return {"label": id2label[best_index], "score": probabilities[best_index]}


def format_probabilities(
    probabilities: Iterable[float],
    id2label: Dict[int, str],
) -> List[Dict[str, float]]:
    formatted = [
        {"label": id2label[index], "score": score}
        for index, score in enumerate(probabilities)
    ]
    return sorted(formatted, key=lambda item: item["score"], reverse=True)


def load_classifier(model_dir: str, base_model_name: str, label_names: List[str]):
    """Load tokenizer and PEFT adapter for local inference."""
    from peft import PeftModel
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    id2label = {index: label for index, label in enumerate(label_names)}
    label2id = {label: index for index, label in id2label.items()}
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    base_model = AutoModelForSequenceClassification.from_pretrained(
        base_model_name,
        num_labels=len(label_names),
        id2label=id2label,
        label2id=label2id,
    )
    model = PeftModel.from_pretrained(base_model, model_dir)
    model.eval()
    return tokenizer, model


def predict_text(text: str, tokenizer: Any, model: Any, device: str, id2label: Dict[int, str]):
    import torch

    encoded = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
    encoded = {key: value.to(device) for key, value in encoded.items()}
    model.to(device)
    model.eval()

    with torch.no_grad():
        outputs = model(**encoded)
        logits = outputs.logits[0].detach().cpu().tolist()

    probs = softmax(logits)
    return {
        "top": top_prediction(logits, id2label),
        "probabilities": format_probabilities(probs, id2label),
        "logits": logits,
        "tokens": tokenizer.convert_ids_to_tokens(encoded["input_ids"][0].cpu().tolist()),
    }
