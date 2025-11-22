"""PyTorchモデルをONNX形式に変換するスクリプト。

Usage:
    python scripts/convert_to_onnx.py \
        --input artifacts/models/victory_classifier.pth \
        --output ../ow2-victory-counter-rs/models/victory_classifier.onnx
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from victory_trainer.model import VictoryClassifier


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert PyTorch model to ONNX")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("artifacts/models/victory_classifier.pth"),
        help="Path to PyTorch checkpoint (.pth)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("../ow2-victory-counter-rs/models/victory_classifier.onnx"),
        help="Path to output ONNX file (.onnx)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=550,
        help="Input image height (default: 550)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=995,
        help="Input image width (default: 995)",
    )
    parser.add_argument(
        "--opset",
        type=int,
        default=17,
        help="ONNX opset version (default: 17)",
    )
    return parser.parse_args()


def load_checkpoint(checkpoint_path: Path) -> tuple[VictoryClassifier, dict, dict]:
    """PyTorchチェックポイントを読み込む。

    Args:
        checkpoint_path: チェックポイントファイルのパス

    Returns:
        (model, label_map, idx_to_label) のタプル
    """
    print(f"[INFO] Loading checkpoint from {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

    # チェックポイント形式を確認
    if "model_state_dict" not in checkpoint:
        raise ValueError(
            f"Invalid checkpoint format. Expected 'model_state_dict' key, got {list(checkpoint.keys())}"
        )

    label_map = checkpoint.get("label_map", {})
    idx_to_label = checkpoint.get("idx_to_label", {})
    num_classes = len(label_map)

    print(f"[INFO] Label map: {label_map}")
    print(f"[INFO] Number of classes: {num_classes}")

    # モデルの初期化
    model = VictoryClassifier(num_classes=num_classes)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    print(f"[INFO] Model loaded successfully")
    return model, label_map, idx_to_label


def export_to_onnx(
    model: VictoryClassifier,
    output_path: Path,
    height: int,
    width: int,
    opset_version: int,
) -> None:
    """PyTorchモデルをONNX形式にエクスポートする。

    Args:
        model: PyTorchモデル
        output_path: 出力先のONNXファイルパス
        height: 入力画像の高さ
        width: 入力画像の幅
        opset_version: ONNXオペレーターセットのバージョン
    """
    # ダミー入力を作成 (batch_size=1, channels=3, height, width)
    dummy_input = torch.randn(1, 3, height, width)

    print(f"[INFO] Exporting to ONNX with input shape: {dummy_input.shape}")

    # 出力ディレクトリを作成
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ONNX形式にエクスポート
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={
            "input": {0: "batch_size"},  # バッチサイズを動的に
            "output": {0: "batch_size"},
        },
        external_data=False,  # 単一ファイル形式で保存
    )

    print(f"[INFO] ONNX model exported to {output_path}")


def save_label_map(label_map: dict, idx_to_label: dict, output_path: Path) -> None:
    """label_map.jsonを保存する。

    Args:
        label_map: ラベル名→インデックスのマッピング
        idx_to_label: インデックス→ラベル名のマッピング
        output_path: ONNXファイルのパス (label_map.jsonは同じディレクトリに保存される)
    """
    label_map_path = output_path.parent / f"{output_path.stem}.label_map.json"

    # idx_to_labelのキーを整数に変換（JSONでは文字列になる可能性があるため）
    idx_to_label_int = {int(k): v for k, v in idx_to_label.items()}

    data = {
        "label_map": label_map,
        "idx_to_label": idx_to_label_int,
    }

    with label_map_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[INFO] Label map saved to {label_map_path}")


def main() -> int:
    args = parse_args()

    # チェックポイントが存在するか確認
    if not args.input.exists():
        print(f"[ERROR] Checkpoint file not found: {args.input}")
        return 1

    # PyTorchモデルを読み込む
    try:
        model, label_map, idx_to_label = load_checkpoint(args.input)
    except Exception as e:
        print(f"[ERROR] Failed to load checkpoint: {e}")
        return 1

    # ONNX形式にエクスポート
    try:
        export_to_onnx(model, args.output, args.height, args.width, args.opset)
    except Exception as e:
        print(f"[ERROR] Failed to export to ONNX: {e}")
        return 1

    # label_map.jsonを保存
    try:
        save_label_map(label_map, idx_to_label, args.output)
    except Exception as e:
        print(f"[ERROR] Failed to save label map: {e}")
        return 1

    print(f"\n[SUCCESS] ✅ Conversion completed successfully!")
    print(f"[INFO] ONNX model: {args.output}")
    print(f"[INFO] Label map: {args.output.parent / f'{args.output.stem}.label_map.json'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
