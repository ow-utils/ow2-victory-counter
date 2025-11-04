from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset

LABEL_MAP = {"victory": 0, "defeat": 1, "draw": 2, "none": 3}


class VictoryDataset(Dataset):
    def __init__(self, root: Path):
        self.samples = []
        root = Path(root)
        for label_name, label_idx in LABEL_MAP.items():
            label_dir = root / label_name
            if not label_dir.exists():
                continue
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
