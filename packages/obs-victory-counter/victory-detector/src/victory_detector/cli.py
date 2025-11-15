"""CLI entry points for manual testing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .core import state, vision


def _load_snapshots(path: Path) -> list[vision.VisionSnapshot]:
    data = json.loads(path.read_text(encoding="utf-8"))
    snapshots: list[vision.VisionSnapshot] = []
    for item in data:
        snapshots.append(
            vision.VisionSnapshot(
                match_complete=bool(item.get("match_complete", False)),
                victory_banner_confidence=float(
                    item.get("victory_banner_confidence", 0.0)
                ),
                defeat_banner_confidence=float(
                    item.get("defeat_banner_confidence", 0.0)
                ),
                payload_advantage=float(item.get("payload_advantage", 0.0)),
            )
        )
    return snapshots


def _default_event_log_path(base: Path) -> Path:
    return base / "events.log"


def run(
    snapshot_file: Path,
    event_log: Path | None = None,
    *,
    required_consecutive: int = 1,
    required_none_consecutive: int = 0,
    cooldown_seconds: int = 0,
) -> dict[str, Any]:
    """CLI本体。スナップショットを読み込み、勝敗推定とイベント追記を行う。"""

    snapshots = _load_snapshots(snapshot_file)
    log_path = event_log or _default_event_log_path(snapshot_file.parent)
    manager = state.StateManager(
        state.EventLog(log_path),
        cooldown_seconds=cooldown_seconds,
        required_consecutive=required_consecutive,
        required_none_consecutive=required_none_consecutive,
    )

    for snapshot in snapshots:
        detection = vision.evaluate_snapshot(snapshot)
        manager.record_detection(detection)

    summary = manager.summary
    return {
        "victories": summary.victories,
        "defeats": summary.defeats,
        "draws": summary.draws,
        "total": summary.total,
        "log": str(log_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run victory-detector against snapshot data."
    )
    parser.add_argument(
        "snapshot_file", type=Path, help="Path to a JSON file containing snapshot data."
    )
    parser.add_argument(
        "--event-log",
        type=Path,
        help="Path to output event log (defaults next to snapshot file).",
    )
    parser.add_argument(
        "--required-consecutive",
        type=int,
        default=1,
        help="連続検知が必要な回数（CLIデフォルト: 1）",
    )
    parser.add_argument(
        "--required-none",
        type=int,
        default=0,
        help="クールダウン解除後に必要な none 連続回数（CLIデフォルト: 0）",
    )
    parser.add_argument(
        "--cooldown",
        type=int,
        default=0,
        help="クールダウン秒数（CLIデフォルト: 0=無効）",
    )
    args = parser.parse_args()

    result = run(
        args.snapshot_file,
        args.event_log,
        required_consecutive=args.required_consecutive,
        required_none_consecutive=args.required_none,
        cooldown_seconds=args.cooldown,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
