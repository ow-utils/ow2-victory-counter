"""Lightweight heuristics for classifying match outcomes from vision signals.

本実装は最終的なOpenCVロジックを置き換えるためのスタブであり、
プロトタイピング段階ではテレメトリ値から勝敗を推定する。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

Outcome = Literal["win", "loss", "unknown"]


@dataclass(slots=True)
class VisionSnapshot:
    """抽出済みのメトリクスを保持するスナップショット。

    Attributes:
        match_complete: ラウンドが終了していると推定できるか。
        victory_banner_confidence: 勝利バナーが検出された信頼度（0.0-1.0）。
        defeat_banner_confidence: 敗北バナーが検出された信頼度（0.0-1.0）。
        payload_advantage: チームの優勢度（-1.0-1.0）。正の値で優勢。
    """

    match_complete: bool
    victory_banner_confidence: float
    defeat_banner_confidence: float
    payload_advantage: float = 0.0


@dataclass(slots=True)
class DetectionResult:
    """勝敗の推定結果。"""

    outcome: Outcome
    confidence: float

    def is_confident(self, threshold: float = 0.7) -> bool:
        """指定した閾値以上の信頼度があるかを判定する。"""

        return self.outcome != "unknown" and self.confidence >= threshold


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    """補助関数。信頼度を0-1の範囲に収める。"""

    return max(min(value, max_value), min_value)


def evaluate_snapshot(snapshot: VisionSnapshot) -> DetectionResult:
    """スナップショットから勝敗を推定する。

    現段階では以下の簡易ルールで推定する。
        1. 試合が未終了なら`unknown`
        2. 勝利バナーの信頼度が敗北バナーより0.2以上高い場合は`win`
        3. 逆の場合は`loss`
        4. 信頼度が拮抗している場合はpayload_advantageを元に勝敗を推定
    """

    if not snapshot.match_complete:
        return DetectionResult(outcome="unknown", confidence=0.0)

    victory = clamp(snapshot.victory_banner_confidence)
    defeat = clamp(snapshot.defeat_banner_confidence)
    banner_gap = victory - defeat

    if banner_gap >= 0.2:
        return DetectionResult(outcome="win", confidence=float(victory))

    if banner_gap <= -0.2:
        return DetectionResult(outcome="loss", confidence=float(defeat))

    if snapshot.payload_advantage >= 0.1:
        return DetectionResult(outcome="win", confidence=clamp(0.5 + snapshot.payload_advantage / 2))

    if snapshot.payload_advantage <= -0.1:
        return DetectionResult(outcome="loss", confidence=clamp(0.5 + abs(snapshot.payload_advantage) / 2))

    return DetectionResult(outcome="unknown", confidence=abs(banner_gap))


def choose_outcome(
    primary: DetectionResult, secondary: Optional[DetectionResult] = None, threshold: float = 0.7
) -> DetectionResult:
    """複数の判定結果から最も信頼できる結果を選ぶ。

    Args:
        primary: メインの判定結果。
        secondary: 補助的な判定結果。
        threshold: 信頼度の閾値。
    """

    if primary.is_confident(threshold):
        return primary

    if secondary:
        if secondary.is_confident(threshold):
            return secondary
        return primary if primary.confidence >= secondary.confidence else secondary

    return primary
