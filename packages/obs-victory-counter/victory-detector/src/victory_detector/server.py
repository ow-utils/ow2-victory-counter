"""HTTPサーバ層。`/state` エンドポイントで現在の勝敗カウントを返す。"""

from __future__ import annotations

import argparse
import html
import json
import logging
from datetime import datetime
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
        "draws": counter.draws,
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
        if parsed.path == "/overlay":
            self._handle_overlay(parsed)
            return

        self._send_json(404, {"error": "not_found"})

    def do_OPTIONS(self) -> None:  # noqa: N802 - プリフライト要求への対応
        parsed = urlparse(self.path)
        if parsed.path in {"/state", "/history", "/overlay"}:
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
            if value not in ("victory", "defeat", "draw"):
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

    def _handle_overlay(self, parsed_url) -> None:
        query = parse_qs(parsed_url.query)
        theme = (query.get("theme", ["dark"])[0]).lower()
        if theme not in {"dark", "light", "transparent"}:
            theme = "dark"
        try:
            scale = float(query.get("scale", ["1.0"])[0])
        except ValueError:
            scale = 1.0
        try:
            history_limit = int(query.get("history", ["3"])[0])
        except ValueError:
            history_limit = 3
        show_draw = (query.get("showDraw", ["true"])[0]).lower() != "false"

        try:
            summary = serialize_summary(self.server.manager.summary)
            events = self.server.manager.history(max(1, history_limit))
        except Exception:  # pragma: no cover - 想定外の例外はログで確認
            logger.exception("Failed to prepare overlay payload")
            self._send_json(500, {"error": "internal_server_error"})
            return

        html_body = self._render_overlay(summary, events, theme, scale, show_draw)
        self._send_html(200, html_body)

    def _render_overlay(self, summary, events, theme, scale, show_draw):
        palette = {
            "dark": {
                "bg": "rgba(15,23,42,0.7)",
                "text": "#f8fafc",
                "card": "rgba(30,41,59,0.7)",
                "accent_victory": "#38bdf8",
                "accent_defeat": "#f87171",
                "accent_draw": "#94a3b8",
            },
            "light": {
                "bg": "rgba(255,255,255,0.85)",
                "text": "#1f2937",
                "card": "rgba(241,245,249,0.9)",
                "accent_victory": "#3b82f6",
                "accent_defeat": "#ef4444",
                "accent_draw": "#64748b",
            },
            "transparent": {
                "bg": "transparent",
                "text": "#f8fafc",
                "card": "rgba(15,23,42,0.45)",
                "accent_victory": "#38bdf8",
                "accent_defeat": "#f87171",
                "accent_draw": "#94a3b8",
            },
        }[theme]

        history_items = []
        for event in reversed(events):
            raw_value = event.value
            value_class = f"overlay-history__item overlay-history__item--{raw_value}"
            value_label = html.escape(raw_value.upper())
            delta = f"+{event.delta}" if event.delta > 0 else str(event.delta)
            note = html.escape(event.note)
            timestamp_raw = event.timestamp.replace("Z", "+00:00")
            try:
                parsed_time = datetime.fromisoformat(timestamp_raw)
                display_time = parsed_time.astimezone().strftime("%H:%M:%S")
            except ValueError:
                display_time = event.timestamp[-8:]
            display_time = html.escape(display_time)
            history_items.append(
                f"<li class='{value_class}'>"
                f"<span class='overlay-history__time'>{display_time}</span>"
                f"<span class='overlay-history__value'>{value_label}</span>"
                f"<span class='overlay-history__delta'>{delta}</span>"
                + (f"<span class='overlay-history__note'>{note}</span>" if note else "")
                + "</li>"
            )

        draws_card = (
            f"<div class='overlay-card overlay-card--draw'><span class='overlay-card__label'>Draw</span><span class='overlay-card__value'>{summary['draws']}</span></div>"
            if show_draw
            else ""
        )

        scale_clamped = max(0.5, min(scale, 2.0))
        cols = 3 if show_draw else 2

        history_html = "".join(history_items)
        if not history_html:
            history_html = "<li class='overlay-history__item overlay-history__item--draw'><span class='overlay-history__value'>NO DATA</span></li>"

        return f"""
<!DOCTYPE html>
<html lang=\"ja\">
  <head>
    <meta charset=\"utf-8\" />
    <title>Victory Counter Overlay</title>
    <style>
      :root {{
        color-scheme: { 'dark' if theme != 'light' else 'light' };
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      }}
      body.overlay-body {{
        margin: 0;
        padding: 12px;
        color: {palette['text']};
        background: {palette['bg']};
        transform: scale({scale_clamped});
        transform-origin: top left;
      }}
      .overlay-root {{
        display: grid;
        gap: 12px;
        min-width: 240px;
      }}
      .overlay-summary {{
        display: grid;
        grid-template-columns: repeat({cols}, minmax(0, 1fr));
        gap: 8px;
      }}
      .overlay-card {{
        padding: 10px;
        border-radius: 10px;
        background: {palette['card']};
        text-align: center;
      }}
      .overlay-card__label {{
        display: block;
        font-size: 0.7rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        opacity: 0.75;
      }}
      .overlay-card__value {{
        display: block;
        font-size: 1.6rem;
        font-weight: 700;
      }}
      .overlay-card--victory {{ border-left: 4px solid {palette['accent_victory']}; }}
      .overlay-card--defeat {{ border-left: 4px solid {palette['accent_defeat']}; }}
      .overlay-card--draw {{ border-left: 4px solid {palette['accent_draw']}; }}
      .overlay-history {{
        list-style: none;
        margin: 0;
        padding: 0;
        display: grid;
        gap: 6px;
      }}
      .overlay-history__item {{
        display: grid;
        grid-template-columns: 60px 1fr auto;
        gap: 8px;
        align-items: center;
        padding: 6px 8px;
        border-radius: 8px;
        background: {palette['card']};
      }}
      .overlay-history__item--victory {{ border-left: 4px solid {palette['accent_victory']}; }}
      .overlay-history__item--defeat {{ border-left: 4px solid {palette['accent_defeat']}; }}
      .overlay-history__item--draw {{ border-left: 4px solid {palette['accent_draw']}; }}
      .overlay-history__time {{ font-variant-numeric: tabular-nums; opacity: 0.6; }}
      .overlay-history__value {{ letter-spacing: 0.04em; }}
      .overlay-history__delta {{ font-weight: 600; }}
      .overlay-history__note {{ grid-column: 2 / span 2; font-size: 0.7rem; opacity: 0.65; }}
    </style>
  </head>
  <body class=\"overlay-body overlay-theme--{theme}\">
    <div class=\"overlay-root\">
      <div class=\"overlay-summary\">
        <div class='overlay-card overlay-card--victory'><span class='overlay-card__label'>Victory</span><span class='overlay-card__value'>{summary['victories']}</span></div>
        <div class='overlay-card overlay-card--defeat'><span class='overlay-card__label'>Defeat</span><span class='overlay-card__value'>{summary['defeats']}</span></div>
        {draws_card}
      </div>
      <ul class=\"overlay-history\">
        {history_html}
      </ul>
    </div>
  </body>
</html>
"""

    def log_message(
        self, format: str, *args: Any
    ) -> None:  # noqa: A003 - ベースクラス準拠
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

    def _send_html(self, status: int, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class StateServer(ThreadingHTTPServer):
    """StateManager を共有する ThreadingHTTPServer。"""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self, server_address: Tuple[str, int], manager: state.StateManager
    ) -> None:
        super().__init__(server_address, StateRequestHandler)
        self.manager = manager


def create_server(host: str, port: int, manager: state.StateManager) -> StateServer:
    """StateServer を生成するヘルパー。"""

    return StateServer((host, port), manager)


def serve(
    manager: state.StateManager, host: str = "127.0.0.1", port: int = 8912
) -> None:
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
    parser = argparse.ArgumentParser(
        description="Serve victory-detector state over HTTP."
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8912, help="Port to listen on (default: 8912)"
    )
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
