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
from datetime import datetime
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
DEFAULT_CAPTURE_DIR = HERE.parent / "captures"
DEFAULT_CAPTURE_SOURCE = ""

_server_instance: Optional[server.StateServer] = None
_server_thread: Optional[threading.Thread] = None
_server_manager: Optional[state.StateManager] = None
_capture_enabled: bool = False
_capture_dir: Path = DEFAULT_CAPTURE_DIR
_capture_source_name: str = ""


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

    obs.obs_properties_add_bool(props, "capture_enabled", "Enable Screenshot Capture")
    obs.obs_properties_add_path(
        props,
        "capture_dir",
        "Screenshot Directory",
        obs.OBS_PATH_DIRECTORY,
        None,
        str(DEFAULT_CAPTURE_DIR),
    )
    obs.obs_properties_add_int(
        props, "capture_interval", "Screenshot Interval (sec)", 1, 60, 1
    )

    source_list = obs.obs_properties_add_list(
        props,
        "capture_source",
        "Screenshot Source",
        obs.OBS_COMBO_TYPE_EDITABLE,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    _populate_source_list(source_list)

    return props


def script_defaults(settings: obs.obs_data_t) -> None:
    obs.obs_data_set_default_string(settings, "event_log", str(DEFAULT_EVENT_LOG))
    obs.obs_data_set_default_string(settings, "host", DEFAULT_HOST)
    obs.obs_data_set_default_int(settings, "port", DEFAULT_PORT)
    obs.obs_data_set_default_int(settings, "poll_interval", 5)
    obs.obs_data_set_default_bool(settings, "capture_enabled", False)
    obs.obs_data_set_default_string(settings, "capture_dir", str(DEFAULT_CAPTURE_DIR))
    obs.obs_data_set_default_int(settings, "capture_interval", 10)
    obs.obs_data_set_default_string(settings, "capture_source", DEFAULT_CAPTURE_SOURCE)


def script_load(settings: obs.obs_data_t) -> None:
    _start_server(settings)
    _start_refresh_timer(settings)
    _start_capture_timer(settings)


def script_update(settings: obs.obs_data_t) -> None:
    _restart_server(settings)
    _start_refresh_timer(settings)
    _start_capture_timer(settings)


def script_unload() -> None:
    obs.timer_remove(_refresh_state)
    obs.timer_remove(_capture_frame)
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


def _start_capture_timer(settings: obs.obs_data_t) -> None:
    global _capture_enabled, _capture_dir, _capture_source_name

    obs.timer_remove(_capture_frame)

    enabled = obs.obs_data_get_bool(settings, "capture_enabled")
    if not enabled:
        _capture_enabled = False
        return

    path_str = obs.obs_data_get_string(settings, "capture_dir") or str(DEFAULT_CAPTURE_DIR)
    interval = obs.obs_data_get_int(settings, "capture_interval") or 10
    source_name = obs.obs_data_get_string(settings, "capture_source") or DEFAULT_CAPTURE_SOURCE
    if not source_name:
        obs.script_log(obs.LOG_WARNING, "Screenshot capture is enabled but no source is specified.")
        _capture_enabled = False
        return

    _capture_enabled = True
    _capture_dir = Path(path_str)
    _capture_source_name = source_name
    _capture_dir.mkdir(parents=True, exist_ok=True)

    interval_ms = max(1, interval) * 1000
    obs.timer_add(_capture_frame, interval_ms)


def _capture_frame() -> None:  # pragma: no cover - OBS runtime
    global _capture_enabled

    if not _capture_enabled:
        return

    source = obs.obs_get_source_by_name(_capture_source_name)
    if source is None:
        obs.script_log(
            obs.LOG_WARNING,
            f"Screenshot source '{_capture_source_name}' not found.",
        )
        _capture_enabled = False
        return

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    file_path = _capture_dir / f"capture-{timestamp}.png"

    try:
        obs.obs_source_save_screenshot(source, "png", str(file_path))
    except Exception as exc:  # noqa: BLE001
        obs.script_log(obs.LOG_WARNING, f"Failed to capture screenshot: {exc}")
    finally:
        obs.obs_source_release(source)


def _populate_source_list(prop: obs.obs_property_t) -> None:
    sources = obs.obs_enum_sources()
    try:
        for source in sources or []:
            name = obs.obs_source_get_name(source)
            if name:
                obs.obs_property_list_add_string(prop, name, name)
    finally:
        obs.source_list_release(sources)
