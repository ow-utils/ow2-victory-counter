from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset

# 後方互換性のため残す（使用されない）
LABEL_MAP = {"victory": 0, "defeat": 1, "draw": 2, "none": 3}


class VictoryDataset(Dataset):
    def __init__(self, root: Path):
        self.samples = []
        root = Path(root)

        # ディレクトリから自動的にラベルマップを生成
        label_dirs = sorted([d for d in root.iterdir() if d.is_dir()])
        if not label_dirs:
            raise ValueError(f"No label directories found under {root}")

        self.label_map = {d.name: idx for idx, d in enumerate(label_dirs)}
        self.idx_to_label = {idx: name for name, idx in self.label_map.items()}

        for label_name, label_idx in self.label_map.items():
            label_dir = root / label_name
            for path in label_dir.glob("*.png"):
                self.samples.append((path, label_idx))

        if not self.samples:
            raise ValueError(f"No samples found under {root}")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Tuple[torch.Tensor, int]:
        path, label = self.samples[index]
        image = Image.open(path).convert("RGB")
        array = np.array(image, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(array).permute(2, 0, 1)
        return tensor, label


def collate_variable_size(batch):
    """可変サイズの画像をバッチ処理するためのcollate関数。

    各画像を最大サイズに合わせてゼロパディングする。
    """
    tensors, labels = zip(*batch)

    # 最大サイズを計算
    max_h = max(t.shape[1] for t in tensors)
    max_w = max(t.shape[2] for t in tensors)

    # パディング
    padded_tensors = []
    for tensor in tensors:
        c, h, w = tensor.shape
        padded = torch.zeros(c, max_h, max_w)
        padded[:, :h, :w] = tensor
        padded_tensors.append(padded)

    return torch.stack(padded_tensors), torch.tensor(labels)
