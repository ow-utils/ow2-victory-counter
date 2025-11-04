"""学習用データセットを構築するスクリプト。

`data/samples` にある JSON メタデータの `template_bbox` を利用して
テンプレート領域を切り出し、`dataset/{variant}/{label}/` 以下に
128x128 PNG として保存する。
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.samples.is_dir():
        print(f"[ERROR] サンプルディレクトリが見つかりません: {args.samples}")
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
            if label not in ("victory", "defeat", "draw") or not bbox or not file_name:
                continue

            sample_path = json_path.parent / file_name
            if not sample_path.exists():
                continue

            x, y, w, h = bbox
            image = cv2.imread(str(sample_path), cv2.IMREAD_COLOR)
            if image is None:
                continue

            crop = image[y : y + h, x : x + w]
            resized = cv2.resize(crop, (args.size, args.size))
            output_dir = args.output / variant / label
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / file_name
            cv2.imwrite(str(output_path), resized)
            print(f"[INFO] {output_path} を出力しました。")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
