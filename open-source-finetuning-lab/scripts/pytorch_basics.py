#!/usr/bin/env python3
"""Small PyTorch walkthrough: tensors, device movement, train loop, eval loop."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from osft_lab.device import describe_device, select_best_device


def main() -> None:
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, TensorDataset
    except ImportError as exc:
        raise SystemExit(
            "PyTorch is not installed. Run: pip install -r requirements.txt"
        ) from exc

    device = select_best_device()
    print("Device details:", describe_device())

    features = torch.tensor(
        [[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]],
        dtype=torch.float32,
    )
    labels = torch.tensor([0, 1, 1, 0], dtype=torch.long)
    print("Tensor shape:", features.shape)
    print("Tensor dtype:", features.dtype)

    dataset = TensorDataset(features, labels)
    dataloader = DataLoader(dataset, batch_size=2, shuffle=True)
    model = nn.Sequential(nn.Linear(2, 8), nn.ReLU(), nn.Linear(8, 2)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.05)
    loss_fn = nn.CrossEntropyLoss()

    model.train()
    for epoch in range(20):
        epoch_loss = 0.0
        for batch_features, batch_labels in dataloader:
            batch_features = batch_features.to(device)
            batch_labels = batch_labels.to(device)

            optimizer.zero_grad()
            logits = model(batch_features)
            loss = loss_fn(logits, batch_labels)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()

        if epoch in {0, 9, 19}:
            print(f"epoch={epoch + 1} loss={epoch_loss:.4f}")

    model.eval()
    with torch.no_grad():
        logits = model(features.to(device))
        predictions = logits.argmax(dim=-1).cpu()

    print("Predictions:", predictions.tolist())
    print("Labels:", labels.tolist())


if __name__ == "__main__":
    main()
