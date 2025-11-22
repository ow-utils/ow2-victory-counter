"""テンプレートの整合性をチェックするスクリプト。

`data/samples` 配下の JSON を読み込み、`template_bbox` が定義されたサンプルに対して
`data/templates/<label>/<variant>/` に対応する PNG が存在するかを検証する。

使い方:

    python packages/obs-victory-counter/victory-detector/scripts/check_templates.py

ImageMagick は不要。結果は標準出力に要約され、終了コードで成否を返す。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Literal

Label = Literal["victory", "defeat", "draw"]

SAMPLES_ROOT = Path("data/samples")
TEMPLATES_ROOT = Path("data/templates")


def slugify(value: str) -> str:
    return value.lower().replace(" ", "_")


def check_templates() -> int:
    if not SAMPLES_ROOT.exists():
        print(f"[ERROR] {SAMPLES_ROOT} が見つかりません。", file=sys.stderr)
        return 1
    if not TEMPLATES_ROOT.exists():
        print(f"[ERROR] {TEMPLATES_ROOT} が見つかりません。", file=sys.stderr)
        return 1

    missing = []
    checked = 0

    for json_path in sorted(SAMPLES_ROOT.glob("*/**/*.json")):
        metadata = json.loads(json_path.read_text())
        samples = metadata.get("samples", [])
        if not isinstance(samples, list):
            continue

        accessibility = metadata.get("accessibility", "default")
        if not isinstance(accessibility, str) or not accessibility.strip():
            accessibility = "default"
        mode = metadata.get("mode")

        variant_parts = [slugify(accessibility)]
        if isinstance(mode, str) and mode.strip():
            variant_parts.append(slugify(mode))
        variant_slug = "_".join(filter(None, variant_parts)) or "default"

        for sample in samples:
            label = sample.get("label")
            bbox = sample.get("template_bbox")
            if label not in ("victory", "defeat", "draw"):
                continue
            if not isinstance(bbox, list) or len(bbox) != 4:
                continue
            checked += 1
            template_dir = TEMPLATES_ROOT / slugify(label) / variant_slug
            if not template_dir.exists():
                missing.append((json_path, sample["file"], template_dir))
                continue
            if not any(template_dir.glob("*.png")):
                missing.append((json_path, sample["file"], template_dir))

    if missing:
        print("[ERROR] 以下のテンプレートが不足しています:")
        for json_path, sample_file, template_dir in missing:
            print(f"  - json={json_path} sample={sample_file} templates={template_dir}")
        return 2

    print(f"[INFO] {checked} 件のサンプルに対応するテンプレートが確認されました。")
    return 0


def main() -> int:
    try:
        return check_templates()
    except Exception as exc:  # pragma: no cover - 補足ログ用
        print(f"[ERROR] 予期しないエラーが発生しました: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
