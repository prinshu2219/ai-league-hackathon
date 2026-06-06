"""Dataset preparation helpers for Hugging Face Datasets workflows."""

from typing import Any, Dict, Iterable, List, Tuple


def build_label_maps(label_names: Iterable[str]) -> Tuple[Dict[str, int], Dict[int, str]]:
    names = list(label_names)
    label2id = {label: index for index, label in enumerate(names)}
    id2label = {index: label for index, label in enumerate(names)}
    return label2id, id2label


def tokenize_batch(
    examples: Dict[str, List[Any]],
    tokenizer: Any,
    text_column: str,
    label_column: str,
    max_length: int,
) -> Dict[str, List[Any]]:
    tokenized = tokenizer(
        examples[text_column],
        truncation=True,
        padding="max_length",
        max_length=max_length,
    )
    tokenized["labels"] = examples[label_column]
    return tokenized


def prepare_hf_dataset(dataset: Any, tokenizer: Any, config: Any) -> Any:
    """Tokenize a Hugging Face DatasetDict and select columns for training."""

    def _tokenize(examples):
        return tokenize_batch(
            examples,
            tokenizer=tokenizer,
            text_column=config.text_column,
            label_column=config.label_column,
            max_length=config.max_length,
        )

    tokenized = dataset.map(_tokenize, batched=True)
    keep_columns = ["input_ids", "attention_mask", "labels"]
    return tokenized.remove_columns(
        [column for column in tokenized["train"].column_names if column not in keep_columns]
    )


def maybe_limit_split(split: Any, max_samples: int) -> Any:
    if max_samples is None:
        return split
    return split.select(range(min(max_samples, len(split))))
