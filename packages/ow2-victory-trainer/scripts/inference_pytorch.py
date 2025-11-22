#!/usr/bin/env python3
"""
単発画像推論スクリプト (PyTorch)

Usage:
    uv run python scripts/inference_pytorch.py \
        --image path/to/image.png \
        --model artifacts/models/victory_classifier.pth \
        [--output result.json]
"""

import argparse
import json
import sys
from pathlib import Path

import cv2

from victory_trainer.inference.predictor import VictoryPredictor


def main():
    parser = argparse.ArgumentParser(description="単発画像推論 (PyTorch)")
    parser.add_argument("--image", type=Path, required=True, help="入力画像パス")
    parser.add_argument("--model", type=Path, required=True, help="モデルファイルパス (.pth)")
    parser.add_argument("--output", type=Path, help="結果出力先JSON（オプション）")
    parser.add_argument("--size", type=int, default=512, help="リサイズサイズ（デフォルト: 512）")
    parser.add_argument("--no-crop", action="store_true", help="クロップをスキップ")
    args = parser.parse_args()

    # 画像読み込み
    if not args.image.exists():
        print(f"Error: Image not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    image = cv2.imread(str(args.image))
    if image is None:
        print(f"Error: Failed to load image: {args.image}", file=sys.stderr)
        sys.exit(1)

    print(f"Image loaded: {image.shape[1]}x{image.shape[0]} (WxH)", file=sys.stderr)

    # Predictor 初期化
    crop_region = None if args.no_crop else (460, 378, 995, 550)
    predictor = VictoryPredictor(
        model_path=args.model,
        crop_region=crop_region,
        image_size=args.size,
    )

    # 推論実行
    result = predictor.predict(image)

    # 結果を辞書化
    result_dict = {
        "image": str(args.image),
        "outcome": result.outcome,
        "confidence": float(result.confidence),
        "predicted_class": result.predicted_class,
    }

    # probabilitiesが存在する場合のみ追加（辞書形式で返される）
    if hasattr(result, 'probabilities'):
        result_dict["probabilities"] = [
            {"class": cls, "probability": float(prob)}
            for cls, prob in result.probabilities.items()
        ]
    else:
        result_dict["probabilities"] = []

    # 出力
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
        print(f"Result saved to: {args.output}", file=sys.stderr)
    else:
        print(json.dumps(result_dict, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
