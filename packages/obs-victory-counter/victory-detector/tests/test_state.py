from pathlib import Path

import pytest

from victory_detector.core import state
from victory_detector.core.vision import DetectionResult


def _manager(
    event_log: state.EventLog,
    *,
    cooldown: int = 0,
    required_consecutive: int = 1,
    required_none: int = 0,
) -> state.StateManager:
    return state.StateManager(
        event_log,
        cooldown_seconds=cooldown,
        required_consecutive=required_consecutive,
        required_none_consecutive=required_none,
    )


@pytest.fixture()
def event_log(tmp_path: Path) -> state.EventLog:
    return state.EventLog(tmp_path / "events.log")


def test_record_detection_and_reload(event_log: state.EventLog) -> None:
    manager = _manager(event_log)
    assert manager.record_detection(DetectionResult("victory", 0.8)).event is not None
    assert manager.record_detection(DetectionResult("defeat", 0.9)).event is not None
    manager.record_adjustment("draw", 1, note="tie")

    summary = manager.summary
    assert summary.victories == 1
    assert summary.defeats == 1
    assert summary.draws == 1
    assert summary.total == 3

    reloaded = manager.reload()
    assert reloaded.victories == 1
    assert reloaded.defeats == 1
    assert reloaded.draws == 1


def test_record_adjustment(event_log: state.EventLog) -> None:
    manager = _manager(event_log)
    manager.record_detection(DetectionResult("victory", 0.75))
    manager.record_adjustment("defeat", 1, note="manual fix")
    manager.record_adjustment("draw", 2)

    assert manager.summary.victories == 1
    assert manager.summary.defeats == 1
    assert manager.summary.draws == 2
    assert manager.summary.adjustments[0].note == "manual fix"


def test_event_log_tail(event_log: state.EventLog) -> None:
    manager = _manager(event_log)
    for _ in range(3):
        manager.record_detection(DetectionResult("victory", 0.7))
    tail = event_log.tail(2)
    assert len(tail) == 2
    assert tail[0].type == "result"


def test_record_detection_accepts_draw(event_log: state.EventLog) -> None:
    manager = _manager(event_log)
    response = manager.record_detection(DetectionResult("draw", 0.65))
    assert response.event is not None
    assert manager.summary.draws == 1


def test_requires_none_clearance_before_recount(event_log: state.EventLog) -> None:
    manager = _manager(event_log, required_none=2)
    first = manager.record_detection(DetectionResult("victory", 0.9))
    assert first.event is not None

    # クールダウン0なので即座に解除されるが、none連続判定が必要
    second = manager.record_detection(DetectionResult("victory", 0.85))
    assert second.event is None
    assert manager.summary.victories == 1

    # noneを2回連続検知するまで解除されない
    manager.record_detection(
        DetectionResult("unknown", 0.2, predicted_class="none")
    )
    third = manager.record_detection(
        DetectionResult("unknown", 0.1, predicted_class="none")
    )
    assert third.event is None  # none自体はカウントしない

    # none連続判定が完了したので再びカウント可能
    final = manager.record_detection(DetectionResult("defeat", 0.95))
    assert final.event is not None
    assert manager.summary.defeats == 1


def test_none_clearance_resets_when_non_none_detected(event_log: state.EventLog) -> None:
    manager = _manager(event_log, required_none=2)
    manager.record_detection(DetectionResult("victory", 0.92))

    manager.record_detection(DetectionResult("unknown", 0.2, predicted_class="none"))
    # 勝利画面が続いていると none 連続カウントはリセットされる
    manager.record_detection(DetectionResult("victory", 0.88))
    manager.record_detection(DetectionResult("unknown", 0.2, predicted_class="none"))
    manager.record_detection(DetectionResult("unknown", 0.2, predicted_class="none"))
    assert manager.record_detection(DetectionResult("defeat", 0.9)).event is not None
    assert manager.summary.defeats == 1
