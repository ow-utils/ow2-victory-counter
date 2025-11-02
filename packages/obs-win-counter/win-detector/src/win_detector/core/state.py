"""勝敗カウンタおよびイベントログの管理モジュール。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Literal, Optional, Sequence, TypedDict

from .vision import DetectionResult

EventType = Literal["result", "adjustment"]
Outcome = Literal["win", "loss"]


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
class CounterState:
    """勝敗カウンタの集計結果。"""

    wins: int = 0
    losses: int = 0
    adjustments: list[Event] = field(default_factory=list)
    results: list[Event] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.wins + self.losses

    def apply(self, event: Event) -> None:
        if event.value == "win":
            self.wins += event.delta
        else:
            self.losses += event.delta

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

    def __init__(self, event_log: EventLog) -> None:
        self._log = event_log
        self._state = CounterState()
        for event in self._log.read_events():
            self._state.apply(event)

    @property
    def summary(self) -> CounterState:
        return self._state

    def record_detection(self, detection: DetectionResult, note: str = "") -> Optional[Event]:
        """判定結果をイベントとして保存する。"""

        if detection.outcome not in ("win", "loss"):
            return None

        event = Event(
            type="result",
            value=detection.outcome,
            delta=1,
            timestamp=utcnow_iso(),
            confidence=detection.confidence,
            note=note,
        )
        self._persist(event)
        return event

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
