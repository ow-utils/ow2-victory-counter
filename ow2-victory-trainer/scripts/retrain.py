"""データセット構築、学習、ONNX変換をまとめて実行するスクリプト。"""

from __future__ import annotations

import argparse
import json
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
DEFAULT_OPSET = 22
VERIFY_LABELS = ("defeat", "none", "victory")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dataset, train classifier, and convert it to ONNX."
    )

    parser.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--onnx-output", type=Path, default=DEFAULT_ONNX_OUTPUT)
    parser.add_argument(
        "--verify-samples",
        type=Path,
        default=None,
        help="推論確認に使うサンプル画像ディレクトリ（省略時は --samples と同じ）。",
    )

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
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="ONNX変換後の victory/defeat/none 推論確認をスキップする。",
    )
    parser.add_argument(
        "--verify-count-per-class",
        type=int,
        default=1,
        help="推論確認で各クラスから使用する画像数。",
    )

    parser.add_argument(
        "--lang",
        type=str,
        default=None,
        help="学習対象の言語コード (例: ja, en)。指定時はパスに言語を含める。",
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
    if args.lang:
        command.extend(["--shared", "data/samples/shared"])
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


def inference_args(args: argparse.Namespace, image_path: Path) -> list[str]:
    return [
        sys.executable,
        "scripts/inference_onnx.py",
        "--image",
        str(image_path),
        "--model",
        str(args.onnx_output),
        "--height",
        str(args.height),
        "--width",
        str(args.width),
    ]


def collect_verify_samples(
    samples_root: Path,
    count_per_class: int,
    shared_root: Path | None = None,
) -> list[tuple[str, Path]]:
    if count_per_class < 1:
        raise ValueError("--verify-count-per-class は 1 以上を指定してください。")

    verify_samples: list[tuple[str, Path]] = []
    for label in VERIFY_LABELS:
        label_dir = samples_root / label
        if not label_dir.is_dir() and shared_root is not None:
            fallback_dir = shared_root / label
            if fallback_dir.is_dir():
                label_dir = fallback_dir
        if not label_dir.is_dir():
            raise FileNotFoundError(
                f"検証用サンプルディレクトリが見つかりません: {label_dir}"
            )

        image_paths = sorted(label_dir.rglob("*.png"))
        if len(image_paths) < count_per_class:
            raise FileNotFoundError(
                f"検証用サンプルが不足しています: {label_dir} "
                f"(required={count_per_class}, found={len(image_paths)})"
            )

        verify_samples.extend((label, path) for path in image_paths[:count_per_class])

    return verify_samples


def verify_predictions(args: argparse.Namespace) -> None:
    samples_root = args.verify_samples if args.verify_samples else args.samples
    shared_root = Path("data/samples/shared") if args.lang else None
    verify_samples = collect_verify_samples(
        samples_root, args.verify_count_per_class, shared_root
    )

    print("\n[STEP] 推論確認")
    for expected_label, image_path in verify_samples:
        command = inference_args(args, image_path)
        print(f"[RUN] {' '.join(command)}")
        result = subprocess.run(command, check=True, capture_output=True, text=True)

        try:
            prediction = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            raise RuntimeError(f"推論結果JSONの読み込みに失敗しました: {exc}") from exc

        predicted_class = prediction["predicted_class"]
        confidence = float(prediction["confidence"])
        outcome = prediction["outcome"]

        print(
            "[VERIFY] "
            f"expected={expected_label} predicted={predicted_class} "
            f"outcome={outcome} confidence={confidence:.4f} image={image_path}"
        )

        if predicted_class != expected_label:
            raise RuntimeError(
                "推論確認に失敗しました: "
                f"expected={expected_label}, predicted={predicted_class}, "
                f"confidence={confidence:.4f}, image={image_path}"
            )


def main() -> int:
    args = parse_args()

    if args.lang:
        lang = args.lang
        if args.samples == DEFAULT_SAMPLES:
            args.samples = Path(f"data/samples/{lang}")
        if args.dataset == DEFAULT_DATASET:
            args.dataset = Path(f"dataset/{lang}")
        if args.checkpoint == DEFAULT_CHECKPOINT:
            args.checkpoint = Path(f"artifacts/models/{lang}/victory_classifier.pth")
        if args.onnx_output == DEFAULT_ONNX_OUTPUT:
            args.onnx_output = Path(
                f"../ow2-victory-counter-rs/models/{lang}/victory_classifier.onnx"
            )
        if args.verify_samples is None:
            args.verify_samples = args.samples

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
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return 1

    if args.skip_convert and not args.skip_verify:
        print("[INFO] ONNX変換をスキップしたため、推論確認もスキップします。")
    elif not args.skip_verify:
        try:
            verify_predictions(args)
        except subprocess.CalledProcessError as exc:
            print(f"[ERROR] 推論確認ステップが失敗しました: exit code {exc.returncode}")
            if exc.stdout:
                print(exc.stdout)
            if exc.stderr:
                print(exc.stderr, file=sys.stderr)
            return exc.returncode
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            print(f"[ERROR] {exc}")
            return 1

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
