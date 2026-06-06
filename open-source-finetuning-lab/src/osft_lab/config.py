"""Project configuration shared by scripts and the Streamlit app."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "emotion-lora"
REPORTS_DIR = PROJECT_ROOT / "reports"

LABEL_NAMES = ["sadness", "joy", "love", "anger", "fear", "surprise"]


@dataclass(frozen=True)
class TrainingConfig:
    dataset_name: str = "dair-ai/emotion"
    base_model_name: str = "distilbert-base-uncased"
    output_dir: Path = OUTPUT_DIR
    reports_dir: Path = REPORTS_DIR
    text_column: str = "text"
    label_column: str = "label"
    max_length: int = 128
    epochs: float = 3.0
    batch_size: int = 8
    learning_rate: float = 2e-4
    weight_decay: float = 0.01
    warmup_ratio: float = 0.06
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    seed: int = 42
    max_train_samples: Optional[int] = None
    max_eval_samples: Optional[int] = None
    max_steps: int = -1
    push_to_hub: bool = False
    hf_repo_id: Optional[str] = None


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}
