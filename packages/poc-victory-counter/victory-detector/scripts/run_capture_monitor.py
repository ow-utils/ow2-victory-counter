"""勝敗バナーの自動検出監視スクリプト。

OBS スクリプトが保存するスクリーンショットディレクトリを監視し、
新しい PNG が現れたら `poc_detect.py` を呼び出して勝敗を判定する。

※ PoC 用の簡易スクリプト。大量運用時には削除処理や例外ハンドリングを拡張すること。
"""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

CAPTURE_GLOB = "*.png"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor capture directory for new screenshots.")
    parser.add_argument(
        "--capture-dir",
        type=Path,
        required=True,
        help="OBS がスクリーンショットを保存するディレクトリ",
    )
    parser.add_argument(
        "--templates",
        type=Path,
        required=True,
        help="テンプレート画像のルートディレクトリ",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.9,
        help="検出時の閾値 (default: 0.9)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="ディレクトリー監視間隔 (秒)",
    )
    parser.add_argument(
        "--poc-script",
        type=Path,
        default=Path(__file__).with_name("poc_detect.py"),
        help="poc_detect.py のパス",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    capture_dir = args.capture_dir.resolve()
    if not capture_dir.exists():
        print(f"[ERROR] capture_dir {capture_dir} が存在しません。")
        return 1

    seen: set[Path] = set(capture_dir.glob(CAPTURE_GLOB))
    print(f"[INFO] 監視を開始します: {capture_dir}")

    try:
        while True:
            current = set(capture_dir.glob(CAPTURE_GLOB))
            new_files = sorted(current - seen)
            if new_files:
                print(f"[INFO] {len(new_files)} 件の新しいキャプチャを検出しました。")
                sample_dir = capture_dir
                cmd = [
                    "python",
                    str(args.poc_script),
                    "--samples",
                    str(sample_dir),
                    "--templates",
                    str(args.templates),
                    "--threshold",
                    str(args.threshold),
                ]
                subprocess.run(cmd, check=False)
                seen.update(new_files)
            time.sleep(max(args.interval, 0.5))
    except KeyboardInterrupt:
        print("[INFO] 監視を終了します。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
