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
CooldownState = Literal["COOLDOWN", "WAITING_FOR_NONE", "READY"]


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
        none_required_consecutive: int = 50,
    ) -> None:
        self._log = event_log
        self._cooldown_seconds = cooldown_seconds
        self._required_consecutive = required_consecutive
        self._none_required_consecutive = none_required_consecutive
        self._state = CounterState()
        for event in self._log.read_events():
            self._state.apply(event)
        self._last_detection_time = self._find_last_detection_time()
        # 連続検知追跡用（勝敗判定用）
        self._consecutive_outcome: Optional[Outcome] = None
        self._consecutive_count: int = 0
        # 2段階クールダウン用
        self._cooldown_state: CooldownState = "READY"
        self._none_consecutive_count: int = 0
        # 初期状態の設定
        if self._last_detection_time is not None:
            self._cooldown_state = "COOLDOWN"

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
        """判定結果を2段階クールダウンと連続検知で処理する。

        2段階クールダウン:
        1. COOLDOWN: すべての検知を無視（0〜cooldown_seconds）
        2. WAITING_FOR_NONE: none をカウント、victory/defeat は無視
        3. READY: 次の勝敗判定が可能（none が規定回数検知後）

        連続検知:
        - 同じ結果が required_consecutive 回検知されたらカウント
        - 異なる結果が出たら連続カウントをリセット
        """

        now = datetime.now(timezone.utc)

        # 状態1: COOLDOWN（時間経過待ち）
        if self._cooldown_state == "COOLDOWN":
            if self._last_detection_time is not None:
                elapsed = (now - self._last_detection_time).total_seconds()
                if elapsed < self._cooldown_seconds:
                    # クールダウン中はすべての検知を無視
                    return DetectionResponse(
                        event=None,
                        consecutive_count=0,
                        is_first_detection=False,
                    )
                else:
                    # 時間経過 → WAITING_FOR_NONE へ遷移
                    self._cooldown_state = "WAITING_FOR_NONE"
                    self._none_consecutive_count = 0

        # 状態2: WAITING_FOR_NONE（none 連続検知待ち）
        if self._cooldown_state == "WAITING_FOR_NONE":
            if detection.outcome not in ("victory", "defeat", "draw"):
                # unknown/none を検知
                self._none_consecutive_count += 1
                if self._none_consecutive_count >= self._none_required_consecutive:
                    # none が規定回数 → READY へ遷移
                    self._cooldown_state = "READY"
                    self._none_consecutive_count = 0
                    # 勝敗判定用カウントもリセット
                    self._consecutive_outcome = None
                    self._consecutive_count = 0
                return DetectionResponse(
                    event=None,
                    consecutive_count=0,
                    is_first_detection=False,
                )
            else:
                # victory/defeat/draw を検知 → カウントリセット（まだ判定不可）
                self._none_consecutive_count = 0
                return DetectionResponse(
                    event=None,
                    consecutive_count=0,
                    is_first_detection=False,
                )

        # 状態3: READY（通常の勝敗判定）
        if detection.outcome not in ("victory", "defeat", "draw"):
            # unknown の場合は連続カウントをリセット
            self._consecutive_outcome = None
            self._consecutive_count = 0
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
            self._last_detection_time = now
            # COOLDOWN 状態へ遷移
            self._cooldown_state = "COOLDOWN"
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
