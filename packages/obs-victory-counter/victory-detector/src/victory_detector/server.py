"""HTTPサーバ層。`/state` エンドポイントで現在の勝敗カウントを返す。"""

from __future__ import annotations

import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Tuple, cast
from urllib.parse import parse_qs, urlparse

from .core import state

logger = logging.getLogger(__name__)


def serialize_summary(counter: state.CounterState) -> dict[str, Any]:
    """CounterState を JSON 変換可能な辞書へシリアライズする。"""

    return {
        "victories": counter.victories,
        "defeats": counter.defeats,
        "total": counter.total,
        "results": [event.to_dict() for event in counter.results],
        "adjustments": [event.to_dict() for event in counter.adjustments],
    }


class StateRequestHandler(BaseHTTPRequestHandler):
    """`/state` リソースを返却するリクエストハンドラー。"""

    server: "StateServer"  # 型ヒント用

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler 命名準拠)
        parsed = urlparse(self.path)
        if parsed.path == "/state":
            self._handle_state()
            return
        if parsed.path == "/history":
            self._handle_history(parsed)
            return

        self._send_json(404, {"error": "not_found"})

    def do_OPTIONS(self) -> None:  # noqa: N802 - preflight support
        parsed = urlparse(self.path)
        if parsed.path in {"/state", "/history"}:
            self._send_empty(204, allow_methods="GET, OPTIONS")
            return
        if parsed.path == "/adjust":
            self._send_empty(204, allow_methods="POST, OPTIONS")
            return
        self._send_empty(404, allow_methods="OPTIONS")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/adjust":
            self._handle_adjust()
            return
        self._send_json(404, {"error": "not_found"})

    def _handle_state(self) -> None:
        try:
            summary = self.server.manager.summary
            payload = serialize_summary(summary)
        except Exception:  # pragma: no cover - 例外メッセージはログで確認
            logger.exception("Failed to serialize state response")
            self._send_json(500, {"error": "internal_server_error"})
            return

        self._send_json(200, payload)

    def _handle_history(self, parsed_url) -> None:
        try:
            query = parse_qs(parsed_url.query)
            limit = int(query.get("limit", ["10"])[0])
        except (ValueError, TypeError):
            self._send_json(400, {"error": "invalid_limit"})
            return

        try:
            events = self.server.manager.history(limit)
            payload = [event.to_dict() for event in events]
        except Exception:  # pragma: no cover
            logger.exception("Failed to read history response")
            self._send_json(500, {"error": "internal_server_error"})
            return

        self._send_json(200, {"events": payload})

    def _handle_adjust(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
            value = payload.get("value")
            if value not in ("victory", "defeat"):
                raise ValueError("invalid value")
            delta = int(payload.get("delta", 1))
            note = payload.get("note", "")
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning("Invalid adjust payload: %s", exc)
            self._send_json(400, {"error": "invalid_payload"})
            return

        try:
            event = self.server.manager.record_adjustment(value, delta, note=note)
        except Exception:  # pragma: no cover
            logger.exception("Failed to record adjustment")
            self._send_json(500, {"error": "internal_server_error"})
            return

        self._send_json(202, {"event": event.to_dict()})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003 - ベースクラス準拠
        logger.info("%s - %s", self.address_string(), format % args)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _send_empty(self, status: int, allow_methods: str) -> None:
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", allow_methods)
        self.end_headers()


class StateServer(ThreadingHTTPServer):
    """StateManager を共有する ThreadingHTTPServer。"""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: Tuple[str, int], manager: state.StateManager) -> None:
        super().__init__(server_address, StateRequestHandler)
        self.manager = manager


def create_server(host: str, port: int, manager: state.StateManager) -> StateServer:
    """StateServer を生成するヘルパー。"""

    return StateServer((host, port), manager)


def serve(manager: state.StateManager, host: str = "127.0.0.1", port: int = 8912) -> None:
    """StateServer を起動し、Ctrl+C まで待機する。"""

    httpd = create_server(host, port, manager)
    actual_host, actual_port = cast(Tuple[str, int], httpd.server_address)
    logger.info("Serving /state on http://%s:%s", actual_host, actual_port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - 手動停止時
        logger.info("Shutting down server")
    finally:
        httpd.shutdown()
        httpd.server_close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve victory-detector state over HTTP.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8912, help="Port to listen on (default: 8912)")
    parser.add_argument(
        "--event-log",
        type=Path,
        default=Path("events.log"),
        help="Path to JSONL event log (default: ./events.log)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    event_log = state.EventLog(args.event_log)
    manager = state.StateManager(event_log)

    logging.basicConfig(level=logging.INFO)
    serve(manager, host=args.host, port=args.port)


if __name__ == "__main__":  # pragma: no cover
    main()
