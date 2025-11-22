"""サンプル画像からテンプレート PNG を切り出すスクリプト。

`data/samples` 配下の JSON を読み込み、`template_bbox` が付与されている
エントリについて ImageMagick の `convert` を用いて切り出した画像を
`data/templates/<label>/<variant>/` に保存する。

利用例:

    python packages/obs-victory-counter/victory-detector/scripts/export_templates.py

あらかじめ ImageMagick がインストールされている必要がある。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SAMPLES_ROOT = Path("data/samples")
OUTPUT_ROOT = Path("data/templates")


def slugify(value: str) -> str:
    return value.lower().replace(" ", "_")


def export_template(source: Path, dest: Path, bbox: list[int]) -> None:
    x, y, width, height = bbox
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "convert",
        str(source),
        "-crop",
        f"{width}x{height}+{x}+{y}",
        "+repage",
        "-strip",
        str(dest),
    ]
    subprocess.check_call(cmd)


def main() -> int:
    if not SAMPLES_ROOT.exists():
        print(f"[ERROR] {SAMPLES_ROOT} が見つかりません。", file=sys.stderr)
        return 1

    outputs = 0
    for json_path in sorted(SAMPLES_ROOT.glob("*/**/*.json")):
        parent = json_path.parent
        with json_path.open("r", encoding="utf-8") as fh:
            metadata = json.load(fh)

        accessibility = slugify(metadata.get("accessibility", "default"))
        mode = metadata.get("mode")
        variant_parts = [accessibility or "default"]
        if isinstance(mode, str) and mode.strip():
            variant_parts.append(slugify(mode))
        variant = "_".join(filter(None, variant_parts)) or "default"

        for sample in metadata.get("samples", []):
            bbox = sample.get("template_bbox")
            if not bbox:
                continue

            source_path = parent / sample["file"]
            if not source_path.exists():
                print(f"[WARN] {source_path} が存在しません。スキップします。")
                continue

            label = slugify(sample.get("label", "unknown"))
            dest_dir = OUTPUT_ROOT / label / variant
            dest_path = dest_dir / f"{source_path.stem}.png"
            export_template(source_path, dest_path, bbox)
            outputs += 1
            print(f"[INFO] {dest_path} を出力しました。")

    if outputs == 0:
        print("[WARN] 出力対象がありませんでした。")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI 実行のみ
    raise SystemExit(main())
