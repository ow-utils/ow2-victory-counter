"""学習用データセットを構築するスクリプト。

以下の 2 通りの入力構成に対応する。

1. 従来形式 (`data/samples/YYYYMMDD_runXX/*.json`)
   - JSON の `template_bbox` を利用してクロップ。
2. 新形式 (`samples/<label>/*.png`)
   - JSON が存在しない場合はこちらを想定。label ごとに
     画像を配置するだけで処理できる。

どちらの場合も `--crop x,y,width,height` を指定すると、共通の矩形を
使ってクロップできる。値はピクセル、または 0〜1 の比率指定。

出力は `dataset/<label>/` の構造で保存される。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2  # type: ignore

DATASET_ROOT = Path("dataset")
SAMPLES_ROOT = Path("data/samples")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build dataset from samples.")
    parser.add_argument("--samples", type=Path, default=SAMPLES_ROOT)
    parser.add_argument("--output", type=Path, default=DATASET_ROOT)
    parser.add_argument("--size", type=int, default=128, help="出力画像の一辺のサイズ")
    parser.add_argument(
        "--crop",
        type=str,
        default=None,
        help="クロップ矩形を 'x,y,width,height' 形式で指定 (値はピクセルまたは 0〜1 の比率)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.samples.is_dir():
        print(f"[ERROR] サンプルディレクトリが見つかりません: {args.samples}")
        return 1

    crop_rect = None
    if args.crop:
        try:
            crop_rect = tuple(float(part.strip()) for part in args.crop.split(","))
            if len(crop_rect) != 4:
                raise ValueError
        except ValueError as exc:
            print("[ERROR] --crop は 'x,y,width,height' 形式で指定してください。", exc)
            return 1

    json_files = sorted(args.samples.glob("*/**/*.json"))

    if json_files:
        _process_metadata_samples(json_files, args.output, args.size, crop_rect)
    else:
        _process_structured_samples(args.samples, args.output, args.size, crop_rect)

    return 0


def _process_metadata_samples(
    json_paths: list[Path],
    output_root: Path,
    size: int,
    crop_rect: tuple[float, float, float, float] | None,
) -> None:
    for json_path in json_paths:
        metadata = json.loads(json_path.read_text())

        for sample in metadata.get("samples", []):
            label = sample.get("label")
            bbox = sample.get("template_bbox")
            file_name = sample.get("file")
            if not file_name:
                continue

            if label not in ("victory", "defeat", "draw", "none"):
                continue

            if crop_rect is None and (not bbox or label == "none"):
                # テンプレート矩形が無い場合は後続のクロップで全体を使用
                bbox = None

            if crop_rect is None and bbox is None:
                continue

            sample_path = json_path.parent / file_name
            if not sample_path.exists():
                continue

            image = cv2.imread(str(sample_path), cv2.IMREAD_COLOR)
            if image is None:
                continue

            height, width = image.shape[:2]

            if crop_rect:
                cx, cy, cw, ch = crop_rect
                x = int(round(cx * width)) if abs(cx) <= 1 else int(round(cx))
                y = int(round(cy * height)) if abs(cy) <= 1 else int(round(cy))
                w = int(round(cw * width)) if abs(cw) <= 1 else int(round(cw))
                h = int(round(ch * height)) if abs(ch) <= 1 else int(round(ch))
            elif bbox:
                x, y, w, h = map(int, bbox)
            else:
                # fallback: 推奨クロップ領域を使用
                x, y, w, h = 460, 378, 995, 550

            x = max(0, min(x, width - 1))
            y = max(0, min(y, height - 1))
            w = max(1, min(w, width - x))
            h = max(1, min(h, height - y))

            _write_sample(
                image=image,
                crop=(x, y, w, h),
                output_root=output_root,
                label=label,
                file_name=file_name,
                size=size,
            )


def _process_structured_samples(
    samples_root: Path,
    output_root: Path,
    size: int,
    crop_rect: tuple[float, float, float, float] | None,
) -> None:
    for label_dir in sorted(samples_root.iterdir()):
        if not label_dir.is_dir():
            continue
        label = label_dir.name.lower()
        if label not in ("victory", "defeat", "draw", "none"):
            continue
        for image_path in sorted(label_dir.glob("*.png")):
            image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
            if image is None:
                continue
            height, width = image.shape[:2]
            if crop_rect:
                cx, cy, cw, ch = crop_rect
                x = int(round(cx * width)) if abs(cx) <= 1 else int(round(cx))
                y = int(round(cy * height)) if abs(cy) <= 1 else int(round(cy))
                w = int(round(cw * width)) if abs(cw) <= 1 else int(round(cw))
                h = int(round(ch * height)) if abs(ch) <= 1 else int(round(ch))
            else:
                # fallback: 推奨クロップ領域を使用
                x, y, w, h = 460, 378, 995, 550

            x = max(0, min(x, width - 1))
            y = max(0, min(y, height - 1))
            w = max(1, min(w, width - x))
            h = max(1, min(h, height - y))

            _write_sample(
                image=image,
                crop=(x, y, w, h),
                output_root=output_root,
                label=label,
                file_name=image_path.name,
                size=size,
            )


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


def _write_sample(
    image: cv2.typing.MatLike,
    crop: tuple[int, int, int, int],
    output_root: Path,
    label: str,
    file_name: str,
    size: int,
) -> None:
    x, y, w, h = crop
    cropped = image[y : y + h, x : x + w]
    resized = _resize_keep_aspect_ratio(cropped, size)
    output_dir = output_root / label
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / file_name
    cv2.imwrite(str(output_path), resized)
    print(f"[INFO] {output_path} を出力しました。 (crop=({x},{y},{w},{h}), resized=({resized.shape[1]},{resized.shape[0]}))")


if __name__ == "__main__":
    raise SystemExit(main())
