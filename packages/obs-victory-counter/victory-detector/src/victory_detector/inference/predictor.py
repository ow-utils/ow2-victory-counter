"""CNN-based victory/defeat predictor."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import cv2  # type: ignore
import numpy as np
import torch
import torch.nn.functional as F

from victory_detector.core.vision import DetectionResult
from victory_detector.training.model import VictoryClassifier

# 5クラス分類結果から勝敗へのマッピング
CLASS_TO_OUTCOME: dict[str, Literal["victory", "defeat", "unknown"]] = {
    "victory_text": "victory",
    "victory_progressbar": "victory",
    "defeat_text": "defeat",
    "defeat_progressbar": "defeat",
    "none": "unknown",  # 検知なし
}


def _resize_keep_aspect_ratio(image: cv2.typing.MatLike, max_size: int) -> cv2.typing.MatLike:
    """画像のアスペクト比を維持しながらリサイズする。長辺がmax_sizeになるように縮小。"""
    h, w = image.shape[:2]
    if h == 0 or w == 0:
        return image

    # 長辺を基準にスケールを計算
    scale = max_size / max(h, w)
    new_w = int(w * scale)
    new_h = int(h * scale)

    # リサイズ（最低1pxは確保）
    new_w = max(1, new_w)
    new_h = max(1, new_h)

    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    return resized


class VictoryPredictor:
    """学習済みCNNモデルを使った勝敗判定クラス。"""

    def __init__(
        self,
        model_path: Path,
        device: str = "auto",
        crop_region: tuple[int, int, int, int] = (460, 378, 995, 550),
        image_size: int | None = None,
        mask_regions: list[tuple[int, int, int, int]] | None = None,
    ) -> None:
        """VictoryPredictorを初期化する。

        Args:
            model_path: 学習済みモデル(.pth)のパス（label_map含む）
            device: 使用デバイス ("auto", "cpu", "cuda")
            crop_region: クロップ領域 (x, y, width, height)
            image_size: リサイズ後の画像サイズ（長辺）。Noneの場合はリサイズしない
            mask_regions: マスク領域のリスト [(x, y, width, height), ...]。Noneの場合はマスクなし
        """
        self.crop_region = crop_region
        self.image_size = image_size
        self.mask_regions = mask_regions

        # デバイス設定
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # モデルとメタデータ読み込み
        checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)
        self.label_map = checkpoint['label_map']
        self.idx_to_label = checkpoint['idx_to_label']
        num_classes = len(self.label_map)

        # モデル初期化
        self.model = VictoryClassifier(num_classes=num_classes)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.to(self.device)
        self.model.eval()

    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        """画像を前処理してテンソルに変換する。

        Args:
            image: 入力画像 (H, W, C) BGR形式

        Returns:
            前処理済みテンソル (1, C, H', W')
        """
        # 1. マスク適用（元画像の座標）
        if self.mask_regions:
            image = image.copy()  # 元画像を変更しないようコピー
            for mx, my, mw, mh in self.mask_regions:
                height, width = image.shape[:2]
                # マスク領域のクリッピング
                mx = max(0, min(mx, width - 1))
                my = max(0, min(my, height - 1))
                mw = max(1, min(mw, width - mx))
                mh = max(1, min(mh, height - my))
                image[my : my + mh, mx : mx + mw] = 0  # 黒で塗りつぶす

        # 2. クロップ
        x, y, w, h = self.crop_region
        height, width = image.shape[:2]

        # クロップ領域のクリッピング
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        w = max(1, min(w, width - x))
        h = max(1, min(h, height - y))

        cropped = image[y : y + h, x : x + w]

        # 3. アスペクト比維持リサイズ（image_size指定時のみ）
        if self.image_size is not None:
            resized = _resize_keep_aspect_ratio(cropped, self.image_size)
        else:
            resized = cropped

        # 4. BGR -> RGB変換
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # 5. 0-1正規化
        normalized = rgb.astype(np.float32) / 255.0

        # 6. テンソル変換 (H, W, C) -> (C, H, W)
        tensor = torch.from_numpy(normalized).permute(2, 0, 1)

        # 7. バッチ次元追加
        return tensor.unsqueeze(0)

    def _map_class_to_outcome(self, class_name: str) -> Literal["victory", "defeat", "unknown"]:
        """5クラス分類結果を勝敗結果にマッピングする。

        Args:
            class_name: 分類クラス名

        Returns:
            勝敗結果 ("victory", "defeat", "unknown")
        """
        return CLASS_TO_OUTCOME.get(class_name, "unknown")

    def predict(self, image: np.ndarray) -> DetectionResult:
        """画像から勝敗を推論する。

        Args:
            image: 入力画像 (H, W, C) BGR形式

        Returns:
            推論結果
        """
        # 前処理
        input_tensor = self._preprocess(image).to(self.device)

        # 推論
        with torch.no_grad():
            logits = self.model(input_tensor)
            probabilities = F.softmax(logits, dim=1)[0]

        # 最高確率のクラスを取得
        predicted_idx = probabilities.argmax().item()
        confidence = probabilities[predicted_idx].item()
        class_name = self.idx_to_label[predicted_idx]

        # 6クラス→3種類マッピング
        outcome = self._map_class_to_outcome(class_name)

        return DetectionResult(
            outcome=outcome,
            confidence=confidence,
            predicted_class=class_name,
        )
