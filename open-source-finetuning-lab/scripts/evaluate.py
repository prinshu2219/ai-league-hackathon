#!/usr/bin/env python3
"""Evaluate a saved LoRA adapter on the emotion test split."""

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from osft_lab.config import LABEL_NAMES, TrainingConfig
from osft_lab.dataset_utils import build_label_maps, maybe_limit_split, prepare_hf_dataset
from osft_lab.device import select_best_device
from osft_lab.metrics import classification_metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", default=str(TrainingConfig.output_dir))
    parser.add_argument("--base-model-name", default=TrainingConfig.base_model_name)
    parser.add_argument("--dataset-name", default=TrainingConfig.dataset_name)
    parser.add_argument("--max-test-samples", type=int, default=None)
    parser.add_argument("--reports-dir", default=str(TrainingConfig.reports_dir))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        from datasets import load_dataset
        from peft import PeftModel
        from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix
        from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer
    except ImportError as exc:
        raise SystemExit(
            "Missing evaluation dependencies. Run: pip install -r requirements.txt"
        ) from exc

    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    device = select_best_device()
    label2id, id2label = build_label_maps(LABEL_NAMES)

    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    raw_dataset = load_dataset(args.dataset_name)
    config = TrainingConfig(
        dataset_name=args.dataset_name,
        base_model_name=args.base_model_name,
    )
    tokenized = prepare_hf_dataset(raw_dataset, tokenizer, config)
    test_dataset = maybe_limit_split(tokenized["test"], args.max_test_samples)

    base_model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model_name,
        num_labels=len(LABEL_NAMES),
        id2label=id2label,
        label2id=label2id,
    )
    model = PeftModel.from_pretrained(base_model, args.model_dir)
    model.to(device)
    model.eval()

    trainer = Trainer(model=model, tokenizer=tokenizer)
    output = trainer.predict(test_dataset)
    predictions = np.argmax(output.predictions, axis=-1)
    labels = output.label_ids
    metrics = classification_metrics(predictions, labels)

    metrics_path = reports_dir / "eval_metrics.json"
    with metrics_path.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)

    matrix = confusion_matrix(labels, predictions, labels=list(range(len(LABEL_NAMES))))
    display = ConfusionMatrixDisplay(confusion_matrix=matrix, display_labels=LABEL_NAMES)
    figure, axis = plt.subplots(figsize=(8, 8))
    display.plot(ax=axis, xticks_rotation=45, colorbar=False)
    figure.tight_layout()
    figure.savefig(reports_dir / "confusion_matrix.png", dpi=160)
    plt.close(figure)

    print(json.dumps(metrics, indent=2))
    print(f"Wrote {metrics_path}")


if __name__ == "__main__":
    main()
