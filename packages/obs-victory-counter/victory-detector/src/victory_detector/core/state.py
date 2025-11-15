"""勝敗カウンタおよびイベントログの管理モジュール。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Literal, Optional, Sequence, TypedDict

from .vision import DetectionResult

EventType = Literal["result", "adjustment"]
Outcome = Literal["victory", "defeat", "draw"]


def utcnow_iso() -> str:
    """UTCのISO8601文字列を返す。"""

    return datetime.now(timezone.utc).isoformat()


class EventDict(TypedDict, total=False):
    """イベントの永続化フォーマット。"""

    type: EventType
    value: Outcome
    delta: int
    confidence: float
    timestamp: str
    note: str


@dataclass(slots=True)
class Event:
    """勝敗結果または手動補正イベント。"""

    type: EventType
    value: Outcome
    delta: int
    timestamp: str
    confidence: float = 1.0
    note: str = ""

    def to_dict(self) -> EventDict:
        data: EventDict = {
            "type": self.type,
            "value": self.value,
            "delta": self.delta,
            "timestamp": self.timestamp,
        }
        if self.type == "result":
            data["confidence"] = self.confidence
        if self.note:
            data["note"] = self.note
        return data

    @classmethod
    def from_dict(cls, payload: EventDict) -> "Event":
        """シリアライズされたデータからイベントを復元する。"""

        return cls(
            type=payload["type"],
            value=payload["value"],
            delta=payload.get("delta", 1),
            timestamp=payload.get("timestamp", utcnow_iso()),
            confidence=payload.get("confidence", 1.0),
            note=payload.get("note", ""),
        )


@dataclass(slots=True)
class DetectionResponse:
    """検知結果のレスポンス（連続検知対応）。"""

    event: Optional[Event]
    consecutive_count: int
    is_first_detection: bool


@dataclass(slots=True)
class CounterState:
    """勝敗カウンタの集計結果。"""

    victories: int = 0
    defeats: int = 0
    draws: int = 0
    adjustments: list[Event] = field(default_factory=list)
    results: list[Event] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.victories + self.defeats + self.draws

    def apply(self, event: Event) -> None:
        # delta > 0の場合のみカウントを更新
        if event.delta > 0:
            if event.value == "victory":
                self.victories += event.delta
            elif event.value == "defeat":
                self.defeats += event.delta
            else:
                self.draws += event.delta

        # delta=0でもイベントリストには追加（ログとして保持）
        if event.type == "result":
            self.results.append(event)
        else:
            self.adjustments.append(event)


class EventLog:
    """JSON Lines形式でイベントを永続化するロガー。"""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, event: Event) -> None:
        with self._path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(event.to_dict(), ensure_ascii=False))
            fp.write("\n")

    def read_events(self) -> Iterator[Event]:
        if not self._path.exists():
            return iter(())

        def _iter() -> Iterator[Event]:
            with self._path.open("r", encoding="utf-8") as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    payload = json.loads(line)
                    yield Event.from_dict(payload)

        return _iter()

    def tail(self, limit: int) -> list[Event]:
        return list(self.read_events())[-limit:]


class StateManager:
    """勝敗判定と手動補正を管理するユーティリティ。"""

    def __init__(
        self,
        event_log: EventLog,
        cooldown_seconds: int = 180,
        required_consecutive: int = 3,
        required_none_consecutive: int = 30,
    ) -> None:
        self._log = event_log
        self._cooldown_seconds = cooldown_seconds
        self._required_consecutive = required_consecutive
        self._required_none_consecutive = max(0, required_none_consecutive)
        self._state = CounterState()
        for event in self._log.read_events():
            self._state.apply(event)
        self._last_detection_time = self._find_last_detection_time()
        # 連続検知追跡用
        self._consecutive_outcome: Optional[Outcome] = None
        self._consecutive_count: int = 0
        # クールダウン解除後の none 連続検知追跡
        self._needs_none_clearance = (
            self._required_none_consecutive > 0 and self._last_detection_time is not None
        )
        self._none_consecutive_count = 0

    @property
    def summary(self) -> CounterState:
        return self._state

    def _find_last_detection_time(self) -> Optional[datetime]:
        """イベントログから最後の検知時刻（delta > 0のresult）を取得。"""
        events = list(self._log.read_events())
        for event in reversed(events):
            if event.type == "result" and event.delta > 0:
                return datetime.fromisoformat(event.timestamp)
        return None

    def record_detection(
        self, detection: DetectionResult, note: str = ""
    ) -> DetectionResponse:
        """判定結果を連続検知として処理する。

        連続で同じ結果が required_consecutive 回検知されたらカウント。
        異なる結果が出たら連続カウントをリセット。
        """

        if detection.outcome not in ("victory", "defeat", "draw"):
            # unknown の場合は連続カウントをリセットし、none連続判定を進める
            self._consecutive_outcome = None
            self._consecutive_count = 0
            self._update_none_clearance(detection.predicted_class)
            return DetectionResponse(
                event=None,
                consecutive_count=0,
                is_first_detection=False,
            )

        now = datetime.now(timezone.utc)

        # クールダウン中の処理
        if self._last_detection_time is not None:
            elapsed = (now - self._last_detection_time).total_seconds()
            if elapsed < self._cooldown_seconds:
                # クールダウン中は連続カウントしない
                remaining = self._cooldown_seconds - elapsed
                return DetectionResponse(
                    event=None,
                    consecutive_count=0,
                    is_first_detection=False,
                )

        if self._needs_none_clearance:
            # none連続判定が完了するまで勝敗カウントを停止
            self._consecutive_outcome = None
            self._consecutive_count = 0
            if detection.predicted_class != "none":
                self._none_consecutive_count = 0
            return DetectionResponse(
                event=None,
                consecutive_count=0,
                is_first_detection=False,
            )

        # 連続検知の判定
        is_first = False
        if self._consecutive_outcome == detection.outcome:
            # 同じ結果が続いている
            self._consecutive_count += 1
        else:
            # 異なる結果が出た → リセット
            self._consecutive_outcome = detection.outcome
            self._consecutive_count = 1
            is_first = True

        # 必要回数に達したかチェック
        if self._consecutive_count >= self._required_consecutive:
            # カウント確定
            event = Event(
                type="result",
                value=detection.outcome,
                delta=1,
                timestamp=now.isoformat(),
                confidence=detection.confidence,
                note=note,
            )
            self._persist(event)
            self._last_detection_time = now  # クールダウン開始
            self._needs_none_clearance = self._required_none_consecutive > 0
            self._none_consecutive_count = 0
            # 連続カウントをリセット
            self._consecutive_outcome = None
            self._consecutive_count = 0
            return DetectionResponse(
                event=event,
                consecutive_count=self._required_consecutive,
                is_first_detection=is_first,
            )

        # まだ確定していない
        return DetectionResponse(
            event=None,
            consecutive_count=self._consecutive_count,
            is_first_detection=is_first,
        )

    def record_adjustment(self, value: Outcome, delta: int, note: str = "") -> Event:
        event = Event(
            type="adjustment",
            value=value,
            delta=delta,
            timestamp=utcnow_iso(),
            confidence=1.0,
            note=note,
        )
        self._persist(event)
        return event

    def _persist(self, event: Event) -> None:
        self._log.append(event)
        self._state.apply(event)

    def _update_none_clearance(self, predicted_class: Optional[str]) -> None:
        """クールダウン明けに必要な none 連続検知の状態を更新する。"""

        if not self._needs_none_clearance or self._required_none_consecutive <= 0:
            if self._required_none_consecutive <= 0:
                self._needs_none_clearance = False
            return

        if predicted_class == "none":
            self._none_consecutive_count += 1
            if self._none_consecutive_count >= self._required_none_consecutive:
                self._needs_none_clearance = False
                self._none_consecutive_count = 0
        else:
            self._none_consecutive_count = 0

    def history(self, limit: int) -> list[Event]:
        """直近のイベントを取得する。"""

        if limit <= 0:
            return []
        return self._log.tail(limit)

    def reload(self) -> CounterState:
        self._state = CounterState()
        for event in self._log.read_events():
            self._state.apply(event)
        return self._state


def aggregate(events: Sequence[Event]) -> CounterState:
    """イベント列を集計し CounterState を返す。"""

    state = CounterState()
    for event in events:
        state.apply(event)
    return state
