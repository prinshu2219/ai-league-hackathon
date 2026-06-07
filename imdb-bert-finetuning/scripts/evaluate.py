import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import TrainingConfig
from app.data import build_dataloaders
from app.evaluation import print_metrics, save_metrics
from app.training import evaluate_model, select_device


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a saved IMDb sentiment model.")
    parser.add_argument("--model-dir", default="artifacts/model")
    parser.add_argument("--cache-dir", default="hf_cache")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--max-eval-samples", type=int, default=1000)
    parser.add_argument("--output", default="artifacts/metrics.json")
    parser.add_argument("--cpu-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("Install dependencies with `pip install -r requirements.txt`.") from exc

    config = TrainingConfig(
        cache_dir=args.cache_dir,
        batch_size=args.batch_size,
        max_length=args.max_length,
        max_eval_samples=args.max_eval_samples,
        prefer_cuda=not args.cpu_only,
        prefer_mps=not args.cpu_only,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(args.model_dir)
    _, _, test_loader = build_dataloaders(config, tokenizer)
    device = select_device(config.prefer_mps, config.prefer_cuda)
    model.to(device)
    metrics = evaluate_model(model, test_loader, device)
    save_metrics(metrics, args.output)
    print_metrics(metrics)


if __name__ == "__main__":
    main()
