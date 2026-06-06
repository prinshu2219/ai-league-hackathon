"""Metrics helpers for classifier evaluation."""

from typing import Any, Dict


def compute_accuracy(eval_pred: Any) -> Dict[str, float]:
    import numpy as np

    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return {"accuracy": float((predictions == labels).mean())}


def classification_metrics(predictions: Any, labels: Any) -> Dict[str, float]:
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "macro_precision": float(precision_score(labels, predictions, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(labels, predictions, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(labels, predictions, average="macro", zero_division=0)),
    }
