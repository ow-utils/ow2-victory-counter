from pathlib import Path

from win_detector import cli


def test_cli_run(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots.json"
    snapshots.write_text(
        """
[
  {"match_complete": true, "victory_banner_confidence": 0.85, "defeat_banner_confidence": 0.1},
  {"match_complete": true, "victory_banner_confidence": 0.2, "defeat_banner_confidence": 0.75}
]
""".strip(),
        encoding="utf-8",
    )

    result = cli.run(snapshots)
    assert result["victories"] == 1
    assert result["defeats"] == 1

    log_path = Path(result["log"])
    assert log_path.exists()
    contents = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(contents) == 2
