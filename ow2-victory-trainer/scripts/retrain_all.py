"""全言語のモデルを一括で再学習するスクリプト。

data/samples/ 配下の言語ディレクトリ（shared を除く）を自動検出し、
各言語に対して scripts/retrain.py --lang {lang} を順次実行する。

retrain.py が受け付けるオプションはそのまま透過される。

Usage:
    uv run python scripts/retrain_all.py
    uv run python scripts/retrain_all.py --clean-dataset --mask
    uv run python scripts/retrain_all.py --epochs 50 --batch-size 16
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SAMPLES_ROOT = Path("data/samples")
SHARED_DIR_NAME = "shared"


def detect_languages(samples_root: Path) -> list[str]:
    """data/samples/ 配下から言語ディレクトリ（shared を除く）を検出する。"""
    if not samples_root.is_dir():
        raise FileNotFoundError(
            f"サンプルルートが見つかりません: {samples_root}"
        )
    langs = sorted(
        d.name
        for d in samples_root.iterdir()
        if d.is_dir() and d.name != SHARED_DIR_NAME
    )
    if not langs:
        raise RuntimeError(
            f"言語ディレクトリが見つかりません: {samples_root}"
        )
    return langs


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    """既知の引数はパースし、残りは retrain.py に透過する。"""
    parser = argparse.ArgumentParser(
        description="全言語のモデルを一括で再学習するスクリプト。",
        add_help=True,
    )
    parser.add_argument(
        "--samples-root",
        type=Path,
        default=SAMPLES_ROOT,
        help="言語ディレクトリを検出するルート (デフォルト: data/samples)",
    )
    # 残りの引数（retrain.py に透過する引数）は parse_known_args で取得
    args, remainder = parser.parse_known_args()
    return args, remainder


def run_for_language(lang: str, extra_args: list[str]) -> int:
    """指定言語に対して retrain.py を実行する。"""
    command = [
        sys.executable,
        "scripts/retrain.py",
        "--lang",
        lang,
        *extra_args,
    ]
    print(f"\n{'=' * 60}")
    print(f"[LANG] {lang}")
    print(f"{'=' * 60}")
    print(f"[RUN] {' '.join(command)}")
    result = subprocess.run(command, check=False)
    return result.returncode


def main() -> int:
    args, extra_args = parse_args()

    try:
        langs = detect_languages(args.samples_root)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"[ERROR] {exc}")
        return 1

    print(f"[INFO] 検出された言語: {', '.join(langs)}")

    for lang in langs:
        rc = run_for_language(lang, extra_args)
        if rc != 0:
            print(f"\n[ERROR] {lang} の学習に失敗しました (exit code {rc})")
            return rc

    print("\n[SUCCESS] 全言語の再学習が完了しました。")
    print(f"[INFO] 処理した言語: {', '.join(langs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
