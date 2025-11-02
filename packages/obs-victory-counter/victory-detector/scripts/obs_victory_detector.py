"""OBS integration script for Victory Detector.

This script can be loaded from OBS Scripts Manager to expose the HTTP
state API (`/state`, `/history`, `/adjust`) while OBS is running.  It
wraps `victory_detector.server` to follow OBS's lifecycle callbacks.

Usage:
  1. Tools > Scripts > Python Scripts > + > select this file.
  2. Adjust the event log path / host / port as needed.

The server runs in a background thread and shuts down automatically
when the script is unloaded or settings change.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Optional

import obspython as obs

# OBS 読み込み時に victory_detector パッケージへパスが通るように調整する。
HERE = Path(__file__).resolve()
SRC_DIR = HERE.parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from victory_detector import server  # noqa: E402  (import after sys.path tweak)
from victory_detector.core import state  # noqa: E402

DEFAULT_EVENT_LOG = HERE.parent / "events_cli.log"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8912

_server_instance: Optional[server.StateServer] = None
_server_thread: Optional[threading.Thread] = None
_server_manager: Optional[state.StateManager] = None


# ---------------------------------------------------------------------------
# OBS スクリプトのライフサイクルフック
# ---------------------------------------------------------------------------


def script_description() -> str:
    return (
        "Expose the Victory Detector HTTP API while OBS is running.\n"
        "Provides /state, /history, and /adjust endpoints backed by the "
        "configured event log."
    )


def script_properties() -> obs.obs_properties_t:
    props = obs.obs_properties_create()

    obs.obs_properties_add_path(
        props,
        "event_log",
        "Event Log Path",
        obs.OBS_PATH_FILE,
        "JSON Lines (*.log *.jsonl)",
        str(DEFAULT_EVENT_LOG),
    )

    obs.obs_properties_add_text(props, "host", "Bind Host", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_int(props, "port", "Port", 1024, 65535, 1)
    obs.obs_properties_add_int(
        props, "poll_interval", "Reload Interval (sec)", 1, 60, 1
    )

    return props


def script_defaults(settings: obs.obs_data_t) -> None:
    obs.obs_data_set_default_string(settings, "event_log", str(DEFAULT_EVENT_LOG))
    obs.obs_data_set_default_string(settings, "host", DEFAULT_HOST)
    obs.obs_data_set_default_int(settings, "port", DEFAULT_PORT)
    obs.obs_data_set_default_int(settings, "poll_interval", 5)


def script_load(settings: obs.obs_data_t) -> None:
    _start_server(settings)
    _start_refresh_timer(settings)


def script_update(settings: obs.obs_data_t) -> None:
    _restart_server(settings)
    _start_refresh_timer(settings)


def script_unload() -> None:
    obs.timer_remove(_refresh_state)
    _stop_server()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _restart_server(settings: obs.obs_data_t) -> None:
    _stop_server()
    _start_server(settings)


def _start_server(settings: obs.obs_data_t) -> None:
    global _server_instance, _server_thread, _server_manager

    if _server_thread and _server_thread.is_alive():
        # すでにサーバが起動中
        return

    event_log_path = Path(
        obs.obs_data_get_string(settings, "event_log") or str(DEFAULT_EVENT_LOG)
    )
    host = obs.obs_data_get_string(settings, "host") or DEFAULT_HOST
    port = obs.obs_data_get_int(settings, "port") or DEFAULT_PORT

    event_log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        _server_manager = state.StateManager(state.EventLog(event_log_path))
    except Exception as exc:  # pragma: no cover - OBS 環境専用処理
        obs.script_log(
            obs.LOG_ERROR, f"Failed to initialise Victory Detector state: {exc}"
        )
        return

    try:
        _server_instance = server.create_server(host, port, _server_manager)
    except OSError as exc:  # pragma: no cover - OBS 環境専用処理
        obs.script_log(obs.LOG_ERROR, f"Failed to bind Victory Detector server: {exc}")
        _server_manager = None
        return

    obs.script_log(
        obs.LOG_INFO, f"Victory Detector server started on http://{host}:{port}"
    )

    def run_server() -> None:  # pragma: no cover - OBS 環境専用処理
        assert _server_instance is not None
        try:
            _server_instance.serve_forever(poll_interval=0.5)
        except Exception as exc:  # noqa: BLE001
            obs.script_log(
                obs.LOG_ERROR, f"Victory Detector server stopped unexpectedly: {exc}"
            )
        finally:
            obs.script_log(obs.LOG_INFO, "Victory Detector server thread exiting")

    _server_thread = threading.Thread(
        target=run_server, name="victory-detector-server", daemon=True
    )
    _server_thread.start()


def _stop_server() -> None:
    global _server_instance, _server_thread, _server_manager

    if _server_instance:
        obs.script_log(obs.LOG_INFO, "Shutting down Victory Detector server")
        try:
            _server_instance.shutdown()
            _server_instance.server_close()
        except Exception as exc:  # pragma: no cover - OBS 環境専用処理
            obs.script_log(obs.LOG_WARNING, f"Error while stopping server: {exc}")
        _server_instance = None

    if _server_thread:
        _server_thread.join(timeout=1)
        _server_thread = None

    _server_manager = None


# ---------------------------------------------------------------------------
# 状態を定期的に同期させるためのタイマー
# ---------------------------------------------------------------------------


def _start_refresh_timer(settings: obs.obs_data_t) -> None:
    interval = obs.obs_data_get_int(settings, "poll_interval") or 5
    interval_ms = max(1, interval) * 1000
    obs.timer_remove(_refresh_state)
    obs.timer_add(_refresh_state, interval_ms)


def _refresh_state() -> None:
    # イベントログを読み直し、手動編集後も StateManager の内容を整合させる。
    if _server_manager:
        _server_manager.reload()
