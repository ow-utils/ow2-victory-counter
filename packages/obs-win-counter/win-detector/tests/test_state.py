from pathlib import Path

import pytest

from win_detector.core import state
from win_detector.core.vision import DetectionResult


@pytest.fixture()
def event_log(tmp_path: Path) -> state.EventLog:
    return state.EventLog(tmp_path / "events.log")


def test_record_detection_and_reload(event_log: state.EventLog) -> None:
    manager = state.StateManager(event_log)
    manager.record_detection(DetectionResult("win", 0.8))
    manager.record_detection(DetectionResult("loss", 0.9))

    summary = manager.summary
    assert summary.wins == 1
    assert summary.losses == 1

    reloaded = manager.reload()
    assert reloaded.wins == 1
    assert reloaded.losses == 1


def test_record_adjustment(event_log: state.EventLog) -> None:
    manager = state.StateManager(event_log)
    manager.record_detection(DetectionResult("win", 0.75))
    manager.record_adjustment("loss", 1, note="manual fix")

    assert manager.summary.wins == 1
    assert manager.summary.losses == 1
    assert manager.summary.adjustments[-1].note == "manual fix"


def test_event_log_tail(event_log: state.EventLog) -> None:
    manager = state.StateManager(event_log)
    for _ in range(3):
        manager.record_detection(DetectionResult("win", 0.7))
    tail = event_log.tail(2)
    assert len(tail) == 2
    assert tail[0].type == "result"
