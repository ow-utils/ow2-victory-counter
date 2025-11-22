"""obs-websocket 経由でソース一覧を取得するユーティリティ。"""
from __future__ import annotations

import argparse
from obsws_python import ReqClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List OBS sources via websocket")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4455)
    parser.add_argument("--password", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = ReqClient(host=args.host, port=args.port, password=args.password)
    resp = client.get_input_list()
    inputs = resp.get("inputs", []) if isinstance(resp, dict) else getattr(resp, "inputs", [])
    print("Inputs:")
    for src in inputs:
        if isinstance(src, dict):
            name = src.get("inputName")
            kind = src.get("inputKind")
        else:
            name = getattr(src, "input_name", None)
            kind = getattr(src, "input_kind", None)
        print(f"  - {name} ({kind})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
