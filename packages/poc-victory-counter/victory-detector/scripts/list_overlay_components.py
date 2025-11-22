"""オーバーレイ画像から候補領域を抽出するユーティリティ。

ImageMagick の `convert` コマンドを呼び出し、明度ベースでしきい値処理を行った結果の
連結成分一覧を出力する。テンプレート切り出しの座標を決める際の参考情報として利用する。

使い方例:

    PYTHONPATH=src uv run python scripts/list_overlay_components.py \\
        data/samples/20251103_run03/20251103_run03_victory_default.png --threshold 65

複数の閾値を試したい場合は `--threshold` オプションを複数回指定する。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable


def run_convert(path: Path, thresholds: Iterable[int]) -> None:
    for threshold in thresholds:
        cmd = [
            "convert",
            str(path),
            "-colorspace",
            "HCL",
            "-channel",
            "l",
            "-separate",
            "+channel",
            "-threshold",
            f"{threshold}%",
            "-define",
            "connected-components:area-threshold=5000",
            "-define",
            "connected-components:verbose=true",
            "-connected-components",
            "8",
            "null:",
        ]
        print(f"=== {path.name} (threshold={threshold}%) ===")
        try:
            out = subprocess.check_output(cmd, text=True)
        except subprocess.CalledProcessError as exc:  # pragma: no cover
            print(f"[ERROR] convert failed: {exc}", file=sys.stderr)
            continue
        for line in out.splitlines():
            line = line.rstrip()
            if not line:
                continue
            print(f"  {line}")
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List connected components candidates for overlay templates."
    )
    parser.add_argument(
        "images",
        type=Path,
        nargs="+",
        help="解析する PNG ファイル",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        action="append",
        default=[70, 65, 60],
        help="明度しきい値 (percent)。複数指定可。既定: 70,65,60",
    )
    return parser.parse_args()


def main(argv: list[str] | None = None) -> int:
    args = parse_args()
    for image_path in args.images:
        if not image_path.is_file():
            print(f"[WARN] {image_path} はファイルではありません。", file=sys.stderr)
            continue
        run_convert(image_path, args.threshold)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
