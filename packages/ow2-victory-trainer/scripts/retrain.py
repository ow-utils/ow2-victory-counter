"""データセット構築、学習、ONNX変換をまとめて実行するスクリプト。"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_SAMPLES = Path("data/samples")
DEFAULT_DATASET = Path("dataset")
DEFAULT_CHECKPOINT = Path("artifacts/models/victory_classifier.pth")
DEFAULT_ONNX_OUTPUT = Path("../ow2-victory-counter-rs/models/victory_classifier.onnx")
DEFAULT_CROP = "42,156,245,108"
DEFAULT_MASK = "0,534,1920,295"
DEFAULT_HEIGHT = 108
DEFAULT_WIDTH = 245
DEFAULT_OPSET = 23


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dataset, train classifier, and convert it to ONNX."
    )

    parser.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--onnx-output", type=Path, default=DEFAULT_ONNX_OUTPUT)

    parser.add_argument("--crop", default=DEFAULT_CROP)
    parser.add_argument("--size", type=int, default=None)
    parser.add_argument(
        "--mask",
        nargs="?",
        const=DEFAULT_MASK,
        default=None,
        help="マスク領域。値を省略した場合は 0,534,1920,295 を使用する。",
    )

    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)

    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--opset", type=int, default=DEFAULT_OPSET)

    parser.add_argument(
        "--clean-dataset",
        action="store_true",
        help="データセット構築前に --dataset のディレクトリを削除する。",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="データセット構築をスキップする。",
    )
    parser.add_argument(
        "--skip-convert",
        action="store_true",
        help="ONNX変換をスキップする。",
    )

    return parser.parse_args()


def run_step(name: str, command: list[str]) -> None:
    print(f"\n[STEP] {name}")
    print(f"[RUN] {' '.join(command)}")
    subprocess.run(command, check=True)


def build_dataset_args(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        "scripts/build_dataset.py",
        "--samples",
        str(args.samples),
        "--output",
        str(args.dataset),
        "--crop",
        args.crop,
    ]
    if args.size is not None:
        command.extend(["--size", str(args.size)])
    if args.mask is not None:
        command.extend(["--mask", args.mask])
    return command


def train_args(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        "scripts/train_classifier.py",
        "--data",
        str(args.dataset),
        "--epochs",
        str(args.epochs),
        "--batch-size",
        str(args.batch_size),
        "--lr",
        str(args.lr),
        "--checkpoint",
        str(args.checkpoint),
    ]


def convert_args(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        "scripts/convert_to_onnx.py",
        "--input",
        str(args.checkpoint),
        "--output",
        str(args.onnx_output),
        "--height",
        str(args.height),
        "--width",
        str(args.width),
        "--opset",
        str(args.opset),
    ]


def main() -> int:
    args = parse_args()

    try:
        if not args.skip_build:
            if not args.samples.is_dir():
                print(f"[ERROR] サンプルディレクトリが見つかりません: {args.samples}")
                return 1
            if args.clean_dataset and args.dataset.exists():
                print(f"[INFO] Removing dataset directory: {args.dataset}")
                shutil.rmtree(args.dataset)
            run_step("データセット構築", build_dataset_args(args))

        run_step("モデル学習", train_args(args))

        if not args.skip_convert:
            run_step("ONNX変換", convert_args(args))

    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] ステップが失敗しました: exit code {exc.returncode}")
        return exc.returncode

    print("\n[SUCCESS] 再学習手順が完了しました。")
    print(f"[INFO] PyTorch model: {args.checkpoint}")
    if not args.skip_convert:
        print(f"[INFO] ONNX model: {args.onnx_output}")
        print(
            f"[INFO] Label map: {args.onnx_output.parent / f'{args.onnx_output.stem}.label_map.json'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
