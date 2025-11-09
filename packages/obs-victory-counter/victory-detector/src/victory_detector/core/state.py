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

    def __init__(self, event_log: EventLog, cooldown_seconds: int = 180) -> None:
        self._log = event_log
        self._cooldown_seconds = cooldown_seconds
        self._state = CounterState()
        for event in self._log.read_events():
            self._state.apply(event)
        self._last_detection_time = self._find_last_detection_time()

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
    ) -> Optional[Event]:
        """判定結果をイベントとして保存する。

        クールダウン期間内の検知はログに記録されるが、カウントには反映されない（delta=0）。
        """

        if detection.outcome not in ("victory", "defeat", "draw"):
            return None

        now = datetime.now(timezone.utc)
        in_cooldown = False
        elapsed = 0.0

        # クールダウンチェック
        if self._last_detection_time is not None:
            elapsed = (now - self._last_detection_time).total_seconds()
            in_cooldown = elapsed < self._cooldown_seconds

        # クールダウン中の処理
        if in_cooldown:
            remaining = self._cooldown_seconds - elapsed
            cooldown_note = f"[cooldown: {remaining:.0f}s remaining] {note}".strip()
            event = Event(
                type="result",
                value=detection.outcome,
                delta=0,  # カウントしない
                timestamp=now.isoformat(),
                confidence=detection.confidence,
                note=cooldown_note,
            )
            self._log.append(event)  # ログには残す
            # _state.apply()は呼ばない（delta=0なのでカウント増えない）
            return event

        # 通常処理
        event = Event(
            type="result",
            value=detection.outcome,
            delta=1,
            timestamp=now.isoformat(),
            confidence=detection.confidence,
            note=note,
        )
        self._persist(event)
        self._last_detection_time = now  # 最後の検知時刻を更新
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
