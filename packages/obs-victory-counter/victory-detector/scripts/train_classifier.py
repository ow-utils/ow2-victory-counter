"""Victory/Defeat/Draw 分類器の学習スクリプト。"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.data.dataset import random_split

from victory_detector.training.dataset import VictoryDataset
from victory_detector.training.model import VictoryClassifier


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train victory classifier")
    parser.add_argument("--data", type=Path, default=Path("dataset"))
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--checkpoint", type=Path, default=Path("artifacts/models/victory_classifier.pth"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    data_dir = args.data
    if not data_dir.exists():
        print(f"[ERROR] dataset {data_dir} が見つかりません。先に build_dataset.py を実行してください。")
        return 1

    dataset = VictoryDataset(data_dir)
    total = len(dataset)
    train_len = int(total * 0.7)
    val_len = total - train_len
    train_set, val_set = random_split(dataset, [train_len, val_len])

    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=args.batch_size)

    model = VictoryClassifier(num_classes=4).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.lr)

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        total_correct = 0
        for inputs, labels in train_loader:
            inputs = inputs.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * inputs.size(0)
            total_correct += (outputs.argmax(dim=1) == labels).sum().item()

        train_loss = total_loss / len(train_loader.dataset)
        train_acc = total_correct / len(train_loader.dataset) * 100

        model.eval()
        val_loss = 0.0
        val_correct = 0
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs = inputs.to(device)
                labels = labels.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                val_loss += loss.item() * inputs.size(0)
                val_correct += (outputs.argmax(dim=1) == labels).sum().item()

        val_loss /= len(val_loader.dataset)
        val_acc = val_correct / len(val_loader.dataset) * 100

        print(f"Epoch {epoch}/{args.epochs} - train_loss: {train_loss:.4f} train_acc: {train_acc:.2f}% val_loss: {val_loss:.4f} val_acc: {val_acc:.2f}%")

    args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), args.checkpoint)
    print(f"[INFO] Saved model to {args.checkpoint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
