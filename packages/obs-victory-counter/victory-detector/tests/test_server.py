import http.client
import json
import threading
import time
from typing import Tuple

import pytest

from victory_detector.core import state
from victory_detector.core.vision import DetectionResult
from victory_detector import server


def test_serialize_summary_includes_events() -> None:
    counter = state.CounterState()
    result_event = state.Event(
        type="result",
        value="victory",
        delta=1,
        timestamp="2024-01-01T00:00:00Z",
        confidence=0.9,
        note="auto",
    )
    adjust_event = state.Event(
        type="adjustment",
        value="defeat",
        delta=2,
        timestamp="2024-01-02T00:00:00Z",
        note="manual fix",
    )
    draw_event = state.Event(
        type="result",
        value="draw",
        delta=1,
        timestamp="2024-01-03T00:00:00Z",
    )
    counter.apply(result_event)
    counter.apply(adjust_event)
    counter.apply(draw_event)

    payload = server.serialize_summary(counter)
    assert payload["victories"] == 1
    assert payload["defeats"] == 2
    assert payload["draws"] == 1
    assert payload["total"] == 4
    assert payload["results"][0]["note"] == "auto"
    assert payload["adjustments"][0]["note"] == "manual fix"


@pytest.fixture()
def running_server(tmp_path):
    log_dir = tmp_path / "log"
    log_dir.mkdir()
    event_log = state.EventLog(log_dir / "events.log")
    manager = state.StateManager(event_log)
    manager.record_detection(DetectionResult("victory", 0.8))
    manager.record_adjustment("defeat", 1, note="manual")
    manager.record_adjustment("draw", 1, note="tie")

    httpd = server.create_server("127.0.0.1", 0, manager)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    # サーバがポートを確保するまで短時間待機
    time.sleep(0.05)

    yield httpd, manager

    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=1)


def _request_json(
    address: Tuple[str, int], method: str, path: str, body: dict | None = None
) -> tuple[int, dict, dict]:
    connection = http.client.HTTPConnection(address[0], address[1], timeout=2)
    try:
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        body = response.read()
        payload = json.loads(body.decode("utf-8")) if body else {}
        return (
            response.status,
            payload,
            {key: value for key, value in response.getheaders()},
        )
    finally:
        connection.close()


def test_state_endpoint_returns_summary(running_server) -> None:
    httpd, _ = running_server
    status, payload, headers = _request_json(httpd.server_address, "GET", "/state")
    assert status == 200
    assert payload["victories"] == 1
    assert payload["defeats"] == 1
    assert payload["draws"] == 1
    assert payload["total"] == 3
    assert payload["adjustments"][0]["note"] == "manual"
    assert headers["Access-Control-Allow-Origin"] == "*"


def test_state_endpoint_handles_unknown_route(running_server) -> None:
    httpd, _ = running_server
    status, payload, _ = _request_json(httpd.server_address, "GET", "/unknown")
    assert status == 404
    assert payload["error"] == "not_found"


def test_state_endpoint_handles_internal_error() -> None:
    class BrokenManager:
        @property
        def summary(
            self,
        ) -> state.CounterState:  # pragma: no cover - エラー経路テスト用
            raise RuntimeError("boom")

    httpd = server.create_server("127.0.0.1", 0, BrokenManager())  # type: ignore[arg-type]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)

    try:
        status, payload, _ = _request_json(httpd.server_address, "GET", "/state")
        assert status == 500
        assert payload["error"] == "internal_server_error"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1)


def test_history_endpoint_returns_recent_events(running_server) -> None:
    httpd, _ = running_server
    status, payload, _ = _request_json(httpd.server_address, "GET", "/history?limit=1")
    assert status == 200
    assert len(payload["events"]) == 1
    assert payload["events"][0]["type"] in {"adjustment", "result"}


def test_history_endpoint_rejects_invalid_limit(running_server) -> None:
    httpd, _ = running_server
    status, payload, _ = _request_json(
        httpd.server_address, "GET", "/history?limit=abc"
    )
    assert status == 400
    assert payload["error"] == "invalid_limit"


def test_adjust_endpoint_records_event(running_server) -> None:
    httpd, manager = running_server
    status, payload, headers = _request_json(
        httpd.server_address,
        "POST",
        "/adjust",
        {"value": "victory", "delta": 2, "note": "manual bump"},
    )
    assert status == 202
    assert payload["event"]["value"] == "victory"
    assert manager.summary.victories == 3  # 初期値1に補正+2が加算される
    assert headers["Access-Control-Allow-Methods"] == "GET, POST, OPTIONS"


def test_adjust_endpoint_rejects_invalid_payload(running_server) -> None:
    httpd, _ = running_server
    status, payload, _ = _request_json(
        httpd.server_address,
        "POST",
        "/adjust",
        {"value": "oops"},
    )
    assert status == 400
    assert payload["error"] == "invalid_payload"


def test_adjust_endpoint_accepts_draw(running_server) -> None:
    httpd, manager = running_server
    status, payload, _ = _request_json(
        httpd.server_address,
        "POST",
        "/adjust",
        {"value": "draw", "delta": 1},
    )
    assert status == 202
    assert payload["event"]["value"] == "draw"
    assert manager.summary.draws >= 1


def test_options_preflight_returns_cors_headers(running_server) -> None:
    httpd, _ = running_server
    connection = http.client.HTTPConnection(
        httpd.server_address[0], httpd.server_address[1], timeout=2
    )
    try:
        connection.request("OPTIONS", "/adjust")
        response = connection.getresponse()
        assert response.status == 204
        headers = {key: value for key, value in response.getheaders()}
        assert headers["Access-Control-Allow-Origin"] == "*"
        assert "POST" in headers["Access-Control-Allow-Methods"]
    finally:
        connection.close()


def _get_raw(address: Tuple[str, int], path: str) -> tuple[int, dict, str]:
    connection = http.client.HTTPConnection(address[0], address[1], timeout=2)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        headers = {key: value for key, value in response.getheaders()}
        body = response.read().decode("utf-8")
        return response.status, headers, body
    finally:
        connection.close()


def test_overlay_endpoint_returns_html(running_server) -> None:
    httpd, _ = running_server
    status, headers, body = _get_raw(httpd.server_address, "/overlay")
    assert status == 200
    assert headers["Content-Type"].startswith("text/html")
    assert "Victory" in body


def test_overlay_endpoint_respects_query(running_server) -> None:
    httpd, _ = running_server
    status, headers, body = _get_raw(
        httpd.server_address, "/overlay?theme=transparent&history=2&scale=1.5"
    )
    assert status == 200
    assert "scale(1.5)" in body
    assert "rgba(15,23,42,0.7)" not in body  # transparent テーマで背景が変わる
    assert headers["Content-Type"].startswith("text/html")
