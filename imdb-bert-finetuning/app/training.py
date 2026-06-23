import json
import random
from pathlib import Path

from app.config import TrainingConfig, ensure_output_dirs
from app.evaluation import compute_binary_metrics, save_metrics


class _StringDevice:
    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name


def select_device(prefer_mps: bool = True, prefer_cuda: bool = True):
    try:
        import torch
    except ImportError:
        return _StringDevice("cpu")

    if prefer_cuda and torch.cuda.is_available():
        return torch.device("cuda")
    if prefer_mps and getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def set_seed(seed: int) -> None:
    random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        return


def _move_batch_to_device(batch: dict, device):
    return {key: value.to(device) for key, value in batch.items()}


def train_one_epoch(model, dataloader, optimizer, scheduler, device) -> dict:
    model.train()
    total_loss = 0.0
    labels = []
    predictions = []

    for batch in dataloader:
        batch = _move_batch_to_device(batch, device)
        optimizer.zero_grad()
        outputs = model(**batch)
        loss = outputs.loss
        loss.backward()
        optimizer.step()
        if scheduler is not None:
            scheduler.step()

        total_loss += loss.item()
        batch_predictions = outputs.logits.argmax(dim=-1)
        predictions.extend(batch_predictions.detach().cpu().tolist())
        labels.extend(batch["labels"].detach().cpu().tolist())

    metrics = compute_binary_metrics(labels, predictions)
    metrics["loss"] = round(total_loss / max(len(dataloader), 1), 4)
    return metrics


def evaluate_model(model, dataloader, device) -> dict:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("PyTorch is required for model evaluation.") from exc

    model.eval()
    total_loss = 0.0
    labels = []
    predictions = []

    with torch.no_grad():
        for batch in dataloader:
            batch = _move_batch_to_device(batch, device)
            outputs = model(**batch)
            total_loss += outputs.loss.item()
            batch_predictions = outputs.logits.argmax(dim=-1)
            predictions.extend(batch_predictions.detach().cpu().tolist())
            labels.extend(batch["labels"].detach().cpu().tolist())

    metrics = compute_binary_metrics(labels, predictions)
    metrics["loss"] = round(total_loss / max(len(dataloader), 1), 4)
    return metrics


def fine_tune(config: TrainingConfig) -> dict:
    try:
        import torch
        from torch.optim import AdamW
        from transformers import AutoModelForSequenceClassification, get_linear_schedule_with_warmup
    except ImportError as exc:
        raise RuntimeError(
            "Install project dependencies with `pip install -r requirements.txt` before training."
        ) from exc

    from app.data import build_dataloaders, load_tokenizer

    set_seed(config.seed)
    ensure_output_dirs(config)

    tokenizer = load_tokenizer(config)
    train_loader, validation_loader, test_loader = build_dataloaders(config, tokenizer)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.model_name,
        num_labels=2,
        id2label={0: "negative", 1: "positive"},
        label2id={"negative": 0, "positive": 1},
        cache_dir=config.cache_dir,
    )

    device = select_device(config.prefer_mps, config.prefer_cuda)
    model.to(device)

    optimizer = AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    total_steps = len(train_loader) * config.epochs
    warmup_steps = int(total_steps * config.warmup_ratio)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    history = []
    for epoch in range(1, config.epochs + 1):
        train_metrics = train_one_epoch(model, train_loader, optimizer, scheduler, device)
        validation_metrics = evaluate_model(model, validation_loader, device)
        epoch_result = {"epoch": epoch, "train": train_metrics, "validation": validation_metrics}
        history.append(epoch_result)
        print(
            f"epoch {epoch}: "
            f"train_loss={train_metrics['loss']:.4f} "
            f"validation_f1={validation_metrics['f1']:.4f}"
        )

    test_metrics = evaluate_model(model, test_loader, device)
    test_metrics["model_name"] = config.model_name
    test_metrics["dataset_name"] = config.dataset_name
    test_metrics["epochs"] = config.epochs
    test_metrics["batch_size"] = config.batch_size
    test_metrics["learning_rate"] = config.learning_rate

    model.save_pretrained(config.model_dir)
    tokenizer.save_pretrained(config.model_dir)
    save_metrics(test_metrics, config.metrics_path)
    Path(config.history_path).write_text(json.dumps(history, indent=2) + "\n")
    return test_metrics

