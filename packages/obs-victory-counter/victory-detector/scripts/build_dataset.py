"""学習用データセットを構築するスクリプト。

`data/samples` にある JSON メタデータを参照し、勝敗バナーを含む
領域をクロップ＆リサイズして `dataset/{variant}/{label}/` に出力する。
既定では `template_bbox` を利用するが、`--crop` で全サンプル共通の
矩形を指定することもでき、モード差分を吸収したい場合に便利。
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

    for json_path in sorted(args.samples.glob("*/**/*.json")):
        metadata = json.loads(json_path.read_text())
        variant = metadata.get("accessibility", "default")
        if isinstance(metadata.get("mode"), str):
            variant += f"_{metadata['mode']}"
        variant = variant.lower().replace(" ", "_")

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
                # fallback: 画面中央を切り出し
                w = int(width * 0.5)
                h = int(height * 0.3)
                x = (width - w) // 2
                y = (height - h) // 2

            x = max(0, min(x, width - 1))
            y = max(0, min(y, height - 1))
            w = max(1, min(w, width - x))
            h = max(1, min(h, height - y))

            crop = image[y : y + h, x : x + w]
            resized = cv2.resize(crop, (args.size, args.size))
            output_dir = args.output / variant / label
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / file_name
            cv2.imwrite(str(output_path), resized)
            print(f"[INFO] {output_path} を出力しました。 (crop=({x},{y},{w},{h}))")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
