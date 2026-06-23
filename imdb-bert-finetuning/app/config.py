from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TrainingConfig:
    model_name: str = "bert-base-uncased"
    dataset_name: str = "imdb"
    output_dir: str = "artifacts"
    cache_dir: str = "hf_cache"
    max_length: int = 256
    validation_size: float = 0.1
    batch_size: int = 16
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    epochs: int = 3
    warmup_ratio: float = 0.1
    seed: int = 42
    max_train_samples: int | None = None
    max_eval_samples: int | None = None
    prefer_mps: bool = True
    prefer_cuda: bool = True

    @property
    def output_path(self) -> Path:
        return Path(self.output_dir)

    @property
    def model_dir(self) -> Path:
        return self.output_path / "model"

    @property
    def metrics_path(self) -> Path:
        return self.output_path / "metrics.json"

    @property
    def history_path(self) -> Path:
        return self.output_path / "training_history.json"


def ensure_output_dirs(config: TrainingConfig) -> None:
    config.output_path.mkdir(parents=True, exist_ok=True)
    config.model_dir.mkdir(parents=True, exist_ok=True)
