from win_detector.core import vision


def test_evaluate_snapshot_win():
    snapshot = vision.VisionSnapshot(True, 0.8, 0.2, 0.0)
    result = vision.evaluate_snapshot(snapshot)
    assert result.outcome == "victory"
    assert result.confidence == 0.8


def test_evaluate_snapshot_uses_payload_advantage():
    snapshot = vision.VisionSnapshot(True, 0.55, 0.5, -0.3)
    result = vision.evaluate_snapshot(snapshot)
    assert result.outcome == "defeat"
    assert result.confidence > 0.5


def test_choose_outcome_prefers_confident_secondary():
    primary = vision.DetectionResult("unknown", 0.2)
    secondary = vision.DetectionResult("victory", 0.9)
    chosen = vision.choose_outcome(primary, secondary)
    assert chosen is secondary
