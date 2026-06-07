from __future__ import annotations

from app.config import TrainingConfig


def _limit_dataset(dataset, max_samples: int | None):
    if max_samples is None:
        return dataset
    return dataset.select(range(min(max_samples, len(dataset))))


def load_tokenizer(config: TrainingConfig):
    try:
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "Install project dependencies with `pip install -r requirements.txt` before loading a tokenizer."
        ) from exc

    return AutoTokenizer.from_pretrained(config.model_name, cache_dir=config.cache_dir)


def load_imdb_splits(config: TrainingConfig):
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError(
            "Install project dependencies with `pip install -r requirements.txt` before loading IMDb."
        ) from exc

    dataset = load_dataset(config.dataset_name, cache_dir=config.cache_dir)
    train_validation = dataset["train"].train_test_split(
        test_size=config.validation_size,
        seed=config.seed,
        stratify_by_column="label",
    )
    train_dataset = _limit_dataset(train_validation["train"], config.max_train_samples)
    validation_dataset = _limit_dataset(train_validation["test"], config.max_eval_samples)
    test_dataset = _limit_dataset(dataset["test"], config.max_eval_samples)
    return train_dataset, validation_dataset, test_dataset


def tokenize_dataset(dataset, tokenizer, config: TrainingConfig):
    def tokenize_batch(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            padding="max_length",
            max_length=config.max_length,
        )

    tokenized = dataset.map(tokenize_batch, batched=True)
    tokenized = tokenized.rename_column("label", "labels")
    columns = ["input_ids", "attention_mask", "labels"]
    if "token_type_ids" in tokenized.column_names:
        columns.insert(2, "token_type_ids")
    tokenized.set_format(type="torch", columns=columns)
    return tokenized


def build_dataloaders(config: TrainingConfig, tokenizer):
    try:
        from torch.utils.data import DataLoader
    except ImportError as exc:
        raise RuntimeError("PyTorch is required to build dataloaders.") from exc

    train_dataset, validation_dataset, test_dataset = load_imdb_splits(config)
    train_dataset = tokenize_dataset(train_dataset, tokenizer, config)
    validation_dataset = tokenize_dataset(validation_dataset, tokenizer, config)
    test_dataset = tokenize_dataset(test_dataset, tokenizer, config)

    return (
        DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True),
        DataLoader(validation_dataset, batch_size=config.batch_size),
        DataLoader(test_dataset, batch_size=config.batch_size),
    )
