"""obs-websocket 経由でソース一覧を取得するユーティリティ。"""
from __future__ import annotations

import argparse
from obswebsocket import obsws, requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List OBS sources via websocket")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4455)
    parser.add_argument("--password", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ws = obsws(args.host, args.port, args.password)
    ws.connect()
    try:
        resp = ws.call(requests.GetSourceList())
        if not resp.status:
            print(f"[ERROR] GetSourceList failed: {resp.datain}")
            return 1
        sources = resp.datain.get("sources", [])
        print("Sources:")
        for src in sources:
            name = src.get("name")
            stype = src.get("type") or src.get("sourceKind")
            print(f"  - {name} ({stype})")
    finally:
        ws.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
