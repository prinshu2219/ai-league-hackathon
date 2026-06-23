import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.inference import predict_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict IMDb movie review sentiment.")
    parser.add_argument("--text", required=True, help="Movie review text to classify.")
    parser.add_argument("--model-dir", default="artifacts/model")
    parser.add_argument("--max-length", type=int, default=256)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = predict_text(args.text, model_dir=args.model_dir, max_length=args.max_length)
    print(f"label: {result['label']}")
    print(f"confidence: {result['confidence']:.4f}")
    print(f"probabilities: {result['probabilities']}")


if __name__ == "__main__":
    main()

