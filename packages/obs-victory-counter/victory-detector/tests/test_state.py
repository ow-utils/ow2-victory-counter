from pathlib import Path

import pytest

from victory_detector.core import state
from victory_detector.core.vision import DetectionResult


@pytest.fixture()
def event_log(tmp_path: Path) -> state.EventLog:
    return state.EventLog(tmp_path / "events.log")


def test_record_detection_and_reload(event_log: state.EventLog) -> None:
    manager = state.StateManager(event_log)
    manager.record_detection(DetectionResult("victory", 0.8))
    manager.record_detection(DetectionResult("defeat", 0.9))

    summary = manager.summary
    assert summary.victories == 1
    assert summary.defeats == 1

    reloaded = manager.reload()
    assert reloaded.victories == 1
    assert reloaded.defeats == 1


def test_record_adjustment(event_log: state.EventLog) -> None:
    manager = state.StateManager(event_log)
    manager.record_detection(DetectionResult("victory", 0.75))
    manager.record_adjustment("defeat", 1, note="manual fix")

    assert manager.summary.victories == 1
    assert manager.summary.defeats == 1
    assert manager.summary.adjustments[-1].note == "manual fix"


def test_event_log_tail(event_log: state.EventLog) -> None:
    manager = state.StateManager(event_log)
    for _ in range(3):
        manager.record_detection(DetectionResult("victory", 0.7))
    tail = event_log.tail(2)
    assert len(tail) == 2
    assert tail[0].type == "result"
