#!/usr/bin/env python3
"""Fine-tune DistilBERT for emotion classification with a LoRA adapter."""

import argparse
import inspect
import json
from dataclasses import replace
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from osft_lab.config import LABEL_NAMES, TrainingConfig, parse_bool
from osft_lab.dataset_utils import build_label_maps, maybe_limit_split, prepare_hf_dataset
from osft_lab.device import describe_device, select_best_device
from osft_lab.lora_utils import attach_lora_adapter, trainable_parameter_summary
from osft_lab.metrics import compute_accuracy


def _training_args_kwargs(training_args_cls, config: TrainingConfig):
    eval_strategy_name = (
        "eval_strategy"
        if "eval_strategy" in inspect.signature(training_args_cls.__init__).parameters
        else "evaluation_strategy"
    )
    eval_strategy = "steps" if config.max_steps and config.max_steps > 0 else "epoch"
    kwargs = {
        "output_dir": str(config.output_dir),
        "per_device_train_batch_size": config.batch_size,
        "per_device_eval_batch_size": config.batch_size,
        "learning_rate": config.learning_rate,
        "weight_decay": config.weight_decay,
        "warmup_ratio": config.warmup_ratio,
        "num_train_epochs": config.epochs,
        "max_steps": config.max_steps,
        "logging_steps": 10,
        "save_strategy": eval_strategy,
        "load_best_model_at_end": True,
        "metric_for_best_model": "accuracy",
        "greater_is_better": True,
        "seed": config.seed,
        "push_to_hub": config.push_to_hub,
    }
    kwargs[eval_strategy_name] = eval_strategy
    if eval_strategy == "steps":
        kwargs["eval_steps"] = 5
        kwargs["save_steps"] = 5
    if config.hf_repo_id:
        kwargs["hub_model_id"] = config.hf_repo_id
    return kwargs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-name", default=TrainingConfig.dataset_name)
    parser.add_argument("--base-model-name", default=TrainingConfig.base_model_name)
    parser.add_argument("--output-dir", default=str(TrainingConfig.output_dir))
    parser.add_argument("--epochs", type=float, default=TrainingConfig.epochs)
    parser.add_argument("--batch-size", type=int, default=TrainingConfig.batch_size)
    parser.add_argument("--learning-rate", type=float, default=TrainingConfig.learning_rate)
    parser.add_argument("--max-train-samples", type=int, default=None)
    parser.add_argument("--max-eval-samples", type=int, default=None)
    parser.add_argument("--max-steps", type=int, default=-1)
    parser.add_argument("--push-to-hub", default="false")
    parser.add_argument("--hf-repo-id", default=None)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run a tiny 10-step training job for local verification.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from datasets import load_dataset
        from peft import PeftModel
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            EarlyStoppingCallback,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        raise SystemExit(
            "Missing ML dependencies. Run: pip install -r requirements.txt"
        ) from exc

    config = TrainingConfig(
        dataset_name=args.dataset_name,
        base_model_name=args.base_model_name,
        output_dir=Path(args.output_dir),
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        max_train_samples=args.max_train_samples,
        max_eval_samples=args.max_eval_samples,
        max_steps=args.max_steps,
        push_to_hub=parse_bool(args.push_to_hub),
        hf_repo_id=args.hf_repo_id,
    )
    if args.smoke:
        config = replace(
            config,
            epochs=1.0,
            max_train_samples=256,
            max_eval_samples=128,
            max_steps=10,
        )

    print("Device details:", describe_device())
    device = select_best_device()
    label2id, id2label = build_label_maps(LABEL_NAMES)

    raw_dataset = load_dataset(config.dataset_name)
    tokenizer = AutoTokenizer.from_pretrained(config.base_model_name)
    tokenized = prepare_hf_dataset(raw_dataset, tokenizer, config)
    train_dataset = maybe_limit_split(tokenized["train"], config.max_train_samples)
    eval_dataset = maybe_limit_split(tokenized["validation"], config.max_eval_samples)

    base_model = AutoModelForSequenceClassification.from_pretrained(
        config.base_model_name,
        num_labels=len(LABEL_NAMES),
        id2label=id2label,
        label2id=label2id,
    )
    model = attach_lora_adapter(base_model, config)
    model.to(device)
    print("Parameter summary:", trainable_parameter_summary(model))

    training_args = TrainingArguments(**_training_args_kwargs(TrainingArguments, config))
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        compute_metrics=compute_accuracy,
        tokenizer=tokenizer,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    train_result = trainer.train()
    metrics = trainer.evaluate()

    config.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(config.output_dir)
    tokenizer.save_pretrained(config.output_dir)

    summary = {
        "base_model_name": config.base_model_name,
        "dataset_name": config.dataset_name,
        "label_names": LABEL_NAMES,
        "device": device,
        "train_metrics": train_result.metrics,
        "eval_metrics": metrics,
        "parameter_summary": trainable_parameter_summary(model),
        "artifact_type": "peft_lora_adapter",
    }
    with (config.output_dir / "training_summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    if config.push_to_hub and config.hf_repo_id:
        model.push_to_hub(config.hf_repo_id)
        tokenizer.push_to_hub(config.hf_repo_id)

    if isinstance(model, PeftModel):
        print(f"Saved LoRA adapter to {config.output_dir}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
