#!/usr/bin/env python3
"""Upload the trained adapter folder and model card to Hugging Face Hub."""

import argparse
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", default="outputs/emotion-lora")
    parser.add_argument("--repo-id", default=os.getenv("HF_REPO_ID"))
    parser.add_argument("--token", default=os.getenv("HF_TOKEN"))
    parser.add_argument("--private", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise SystemExit(
            "huggingface_hub is not installed. Run: pip install -r requirements.txt"
        ) from exc

    if not args.repo_id:
        raise SystemExit("Missing --repo-id or HF_REPO_ID.")
    if not args.token:
        raise SystemExit("Missing --token or HF_TOKEN.")

    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        raise SystemExit(f"Model directory not found: {model_dir}")

    api = HfApi(token=args.token)
    api.create_repo(repo_id=args.repo_id, private=args.private, exist_ok=True)
    api.upload_folder(
        repo_id=args.repo_id,
        folder_path=str(model_dir),
        path_in_repo=".",
        commit_message="Upload LoRA emotion classifier adapter",
    )

    model_card = Path("MODEL_CARD.md")
    if model_card.exists():
        api.upload_file(
            repo_id=args.repo_id,
            path_or_fileobj=str(model_card),
            path_in_repo="README.md",
            commit_message="Add model card",
        )

    print(f"Uploaded {model_dir} to https://huggingface.co/{args.repo_id}")


if __name__ == "__main__":
    main()
