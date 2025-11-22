#!/usr/bin/env python3
"""
単発画像推論スクリプト (ONNX)

Usage:
    uv run python scripts/inference_onnx.py \
        --image path/to/image.png \
        --model ../ow2-victory-counter-rs/models/victory_classifier.onnx \
        [--output result.json]
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
import torch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="単発画像推論 (ONNX)")
    parser.add_argument("--image", type=Path, required=True, help="入力画像パス")
    parser.add_argument("--model", type=Path, required=True, help="ONNXモデルファイルパス (.onnx)")
    parser.add_argument("--label-map", type=Path, help="label_map.json のパス（省略時は自動検出）")
    parser.add_argument("--output", type=Path, help="結果出力先JSON（オプション）")
    parser.add_argument("--size", type=int, default=512, help="リサイズサイズ（デフォルト: 512）")
    parser.add_argument("--no-crop", action="store_true", help="クロップをスキップ")
    return parser.parse_args()


def load_label_map(label_map_path: Path) -> dict:
    """label_map.jsonを読み込む。"""
    with label_map_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # idx_to_labelのキーを整数に変換
    idx_to_label = {int(k): v for k, v in data["idx_to_label"].items()}
    return idx_to_label


def preprocess_image(
    image: np.ndarray,
    crop_region: tuple[int, int, int, int] | None,
    image_size: int | None,
) -> np.ndarray:
    """画像を前処理してテンソルに変換する。

    Args:
        image: 入力画像 (H, W, C) BGR形式
        crop_region: クロップ領域 (x, y, width, height) または None
        image_size: リサイズ後の画像サイズ（長辺）。Noneの場合はリサイズしない

    Returns:
        前処理済みテンソル (1, C, H', W')
    """
    # 1. クロップ
    if crop_region:
        x, y, w, h = crop_region
        height, width = image.shape[:2]

        # クロップ領域のクリッピング
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        w = max(1, min(w, width - x))
        h = max(1, min(h, height - y))

        cropped = image[y : y + h, x : x + w]
    else:
        cropped = image

    # 2. アスペクト比維持リサイズ（image_size指定時のみ）
    if image_size is not None:
        h, w = cropped.shape[:2]
        if h == 0 or w == 0:
            resized = cropped
        else:
            scale = image_size / max(h, w)
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            resized = cv2.resize(cropped, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    else:
        resized = cropped

    # 3. BGR -> RGB変換
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

    # 4. 0-1正規化
    normalized = rgb.astype(np.float32) / 255.0

    # 5. テンソル変換 (H, W, C) -> (C, H, W)
    tensor = np.transpose(normalized, (2, 0, 1))

    # 6. バッチ次元追加
    return np.expand_dims(tensor, axis=0)


def main() -> int:
    args = parse_args()

    # 画像読み込み
    if not args.image.exists():
        print(f"Error: Image not found: {args.image}", file=sys.stderr)
        return 1

    image = cv2.imread(str(args.image))
    if image is None:
        print(f"Error: Failed to load image: {args.image}", file=sys.stderr)
        return 1

    print(f"Image loaded: {image.shape[1]}x{image.shape[0]} (WxH)", file=sys.stderr)

    # label_map.jsonのパスを自動検出
    if args.label_map:
        label_map_path = args.label_map
    else:
        label_map_path = args.model.parent / f"{args.model.stem}.label_map.json"

    if not label_map_path.exists():
        print(f"Error: Label map not found: {label_map_path}", file=sys.stderr)
        print(f"Please specify --label-map option", file=sys.stderr)
        return 1

    # label_mapを読み込む
    idx_to_label = load_label_map(label_map_path)
    print(f"Label map loaded: {idx_to_label}", file=sys.stderr)

    # ONNX Runtime セッションを作成
    ort_session = ort.InferenceSession(str(args.model))

    # 画像を前処理
    crop_region = None if args.no_crop else (460, 378, 995, 550)
    input_tensor = preprocess_image(image, crop_region, args.size)

    print(f"Input tensor shape: {input_tensor.shape}", file=sys.stderr)

    # 推論実行
    onnx_output = ort_session.run(None, {"input": input_tensor})[0]

    # Softmaxで確率に変換
    probabilities = torch.softmax(torch.from_numpy(onnx_output), dim=1).numpy()[0]

    # 最高確率のクラスを取得
    predicted_idx = int(probabilities.argmax())
    confidence = float(probabilities[predicted_idx])
    predicted_class = idx_to_label[predicted_idx]

    # 5クラス分類結果から勝敗へのマッピング
    class_to_outcome = {
        "victory_text": "victory",
        "victory_progressbar": "victory",
        "defeat_text": "defeat",
        "defeat_progressbar": "defeat",
        "none": "unknown",
    }
    outcome = class_to_outcome.get(predicted_class, "unknown")

    # 結果を辞書化
    result_dict = {
        "image": str(args.image),
        "outcome": outcome,
        "confidence": confidence,
        "predicted_class": predicted_class,
        "probabilities": [
            {"class": idx_to_label[i], "probability": float(probabilities[i])}
            for i in range(len(idx_to_label))
        ],
    }

    # 出力
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
        print(f"Result saved to: {args.output}", file=sys.stderr)
    else:
        print(json.dumps(result_dict, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
