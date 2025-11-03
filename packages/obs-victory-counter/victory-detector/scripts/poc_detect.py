"""画像解析 PoC スクリプト

Victory / Defeat / Draw のバナー検出を試行するための雛形。

利用方法:
    python scripts/poc_detect.py --samples data/samples/20251103_run03 --templates data/templates

`data/samples` 配下の JSON に含まれる `template_bbox` を利用して、
同じく `data/templates/<label>/<variant>/` に保存されたテンプレートとの
類似度（正規化相関係数）を計算する。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Literal, Optional

try:
    import cv2  # type: ignore
    import numpy as np
except ImportError:  # pragma: no cover - 開発環境でのみ利用
    cv2 = None
    np = None

Label = Literal["victory", "defeat", "draw"]


def preprocess(image: "np.ndarray") -> "np.ndarray":
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def match_template(image: "np.ndarray", template: "np.ndarray") -> float:
    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return float(max_val)


def run_detection(
    samples: Iterable[dict[str, object]],
    sample_root: Path,
    template_root: Path,
    variant: str,
    threshold: float,
) -> None:
    if cv2 is None or np is None:
        raise RuntimeError("OpenCV(cv2) がインストールされていません。PoC 実行には cv2 をインストールしてください。")

    for entry in samples:
        file_name = entry.get("file")
        label = entry.get("label")
        bbox = entry.get("template_bbox")

        if not isinstance(file_name, str) or label not in ("victory", "defeat", "draw"):
            continue
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue

        sample_path = sample_root / file_name
        if not sample_path.exists():
            print(f"[WARN] {sample_path} が見つかりません。")
            continue

        x, y, width, height = map(int, bbox)
        image = cv2.imread(str(sample_path), cv2.IMREAD_COLOR)
        if image is None:
            print(f"[WARN] {sample_path} を読み込めませんでした。")
            continue

        crop = image[y : y + height, x : x + width]
        processed_crop = preprocess(crop)

        template_dir = template_root / label / variant
        template_scores: list[float] = []
        for template_path in sorted(template_dir.glob("*.png")):
            template_img = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
            if template_img is None:
                continue
            processed_template = preprocess(template_img)
            if processed_template.shape != processed_crop.shape:
                processed_template = cv2.resize(processed_template, (processed_crop.shape[1], processed_crop.shape[0]))
            score = match_template(processed_crop, processed_template)
            template_scores.append(score)

        if not template_scores:
            print(f"[WARN] {template_dir} にテンプレートが存在しません。")
            continue

        best_score = max(template_scores)
        detected = label if best_score >= threshold else "unknown"
        print(f"{file_name}: expected={label}, detected={detected}, score={best_score:.3f}")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Victory/Defeat/Draw banner detection PoC (shape-based)")
    parser.add_argument(
        "--samples",
        type=Path,
        required=True,
        help="サンプル画像と JSON メタデータを格納したディレクトリ",
    )
    parser.add_argument(
        "--templates",
        type=Path,
        required=True,
        help="切り出したテンプレート画像を格納したルートディレクトリ",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="類似度がこの値以上であれば一致とみなす (default: 0.85)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    if not args.samples.is_dir() or not args.templates.is_dir():
        print("[ERROR] samples と templates は存在するディレクトリである必要があります。", file=sys.stderr)
        return 1

    json_files = sorted(args.samples.glob("*.json"))
    if not json_files:
        print("[ERROR] サンプルディレクトリに JSON メタデータが見つかりませんでした。", file=sys.stderr)
        return 1

    for json_path in json_files:
        metadata = json.loads(json_path.read_text())
        samples = metadata.get("samples", [])
        if not isinstance(samples, list):
            continue

        variant = metadata.get("accessibility", "default")
        if not isinstance(variant, str):
            variant = "default"
        variant_slug = variant.lower().replace(" ", "_")

        print(f"=== {json_path.name} (variant={variant_slug}) ===")
        run_detection(samples, args.samples, args.templates, variant_slug, args.threshold)
    return 0


if __name__ == "__main__":  # pragma: no cover - PoC 実行
    raise SystemExit(main())
