"""画像解析 PoC スクリプト

Victory / Defeat / Draw のバナー検出を試行するための雛形。

利用方法:
    python scripts/poc_detect.py data/samples victory

現時点ではテンプレートマッチングの骨組みのみで、OpenCV(cv2) を使用する想定。
"""

from __future__ import annotations

import argparse
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


def load_templates(template_dir: Path) -> dict[Label, Path]:
    """テンプレート画像のパスを取得する。

    現状は `templates/{label}.png` という命名を想定。
    実際の PoC ではサブディレクトリや別名も考慮する必要がある。
    """

    mapping: dict[Label, Path] = {}
    for label in ("victory", "defeat", "draw"):
        candidate = template_dir / f"{label}.png"
        if candidate.exists():
            mapping[label] = candidate
    return mapping


def match_template(image: "np.ndarray", template: "np.ndarray") -> float:
    """テンプレートマッチングを行い、類似度を返す。

    PoC では cv2.matchTemplate + minMaxLoc を利用する予定。
    """

    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return float(max_val)


def run_detection(samples: Iterable[Path], templates: dict[Label, Path], threshold: float) -> None:
    if cv2 is None or np is None:
        raise RuntimeError("OpenCV(cv2) がインストールされていません。PoC 実行には cv2 をインストールしてください。")

    loaded_templates = {
        label: cv2.imread(str(path), cv2.IMREAD_COLOR)
        for label, path in templates.items()
    }

    for sample_path in samples:
        image = cv2.imread(str(sample_path), cv2.IMREAD_COLOR)
        if image is None:
            print(f"[WARN] {sample_path} を読み込めませんでした。")
            continue

        scores: list[tuple[Label, float]] = []
        for label, template_img in loaded_templates.items():
            if template_img is None:
                continue
            score = match_template(image, template_img)
            scores.append((label, score))

        scores.sort(key=lambda item: item[1], reverse=True)
        best = scores[0] if scores else ("victory", 0.0)
        detected_label = best[0] if best[1] >= threshold else "unknown"
        print(f"{sample_path.name}: {detected_label} (score={best[1]:.3f})")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Victory banner detection PoC")
    parser.add_argument("sample_dir", type=Path, help="サンプル画像を格納したディレクトリ")
    parser.add_argument("template_dir", type=Path, help="テンプレート画像を格納したディレクトリ")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="テンプレートマッチングで勝敗を確定させる閾値 (default: 0.75)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    if not args.sample_dir.is_dir() or not args.template_dir.is_dir():
        print("[ERROR] sample_dir と template_dir は存在するディレクトリである必要があります。", file=sys.stderr)
        return 1

    templates = load_templates(args.template_dir)
    if not templates:
        print("[ERROR] テンプレート画像が見つかりませんでした。templates/{victory,defeat,draw}.png を追加してください。", file=sys.stderr)
        return 1

    samples = sorted(args.sample_dir.glob("*.png"))
    if not samples:
        print("[WARN] サンプル画像が見つかりませんでした。PNG 形式のファイルを追加してください。")
        return 0

    run_detection(samples, templates, args.threshold)
    return 0


if __name__ == "__main__":  # pragma: no cover - PoC 実行
    raise SystemExit(main())
