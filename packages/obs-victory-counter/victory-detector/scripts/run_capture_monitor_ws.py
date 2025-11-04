"""obs-websocket を利用した勝敗判定 PoC モニター。

OBS 5.x の websocket API を使用し、指定ソースのスクリーンショットを
一定間隔で取得してテンプレートと照合、判定結果を標準出力へログ出力する。
"""

from __future__ import annotations

import argparse
import base64
import json
import time
from pathlib import Path

import cv2  # type: ignore
import numpy as np  # type: ignore
from obsws_python import ReqClient

DEFAULT_THRESHOLD = 0.9
DEFAULT_INTERVAL = 2.0


def preprocess(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def load_templates(template_root: Path, variant: str) -> dict[str, list[np.ndarray]]:
    mapping: dict[str, list[np.ndarray]] = {}
    for label_dir in template_root.iterdir():
        if not label_dir.is_dir():
            continue
        variant_dir = label_dir / variant
        if not variant_dir.exists():
            continue
        templates: list[np.ndarray] = []
        for path in variant_dir.glob("*.png"):
            img = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if img is not None:
                templates.append(preprocess(img))
        if templates:
            mapping[label_dir.name] = templates
    return mapping


def match_score(image: np.ndarray, templates: list[np.ndarray]) -> float:
    scores = []
    for tmpl in templates:
        resized = cv2.resize(image, (tmpl.shape[1], tmpl.shape[0]))
        res = cv2.matchTemplate(resized, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        scores.append(max_val)
    return max(scores) if scores else 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OBS websocket capture monitor")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4455)
    parser.add_argument("--password", default="")
    parser.add_argument("--source", required=True, help="スクリーンショット対象のソース名")
    parser.add_argument("--variant", default="default_unranked")
    parser.add_argument("--templates", type=Path, default=Path("data/templates"))
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--screenshot-width", type=int, default=1920)
    parser.add_argument("--screenshot-height", type=int, default=1080)
    parser.add_argument("--template-bbox", type=str, help="x,y,w,h を指定した場合はこの範囲で判定")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.templates.is_dir():
        print(f"[ERROR] テンプレートディレクトリが見つかりません: {args.templates}")
        return 1

    templates = load_templates(args.templates, args.variant)
    if not templates:
        print(f"[ERROR] variant {args.variant} のテンプレートがありません。")
        return 1

    bbox = None
    if args.template_bbox:
        try:
            bbox = tuple(int(part) for part in args.template_bbox.split(","))
            if len(bbox) != 4:
                raise ValueError
        except ValueError:
            print("[ERROR] template-bbox は x,y,width,height 形式で指定してください。")
            return 1

    client = ReqClient(host=args.host, port=args.port, password=args.password)
    print("[INFO] obs-websocket (5.x) に接続しました。Ctrl+C で終了します。")

    try:
        while True:
            resp = client.get_source_screenshot(
                args.source,
                "png",
                args.screenshot_width,
                args.screenshot_height,
                -1,
            )
            image_data = getattr(resp, "image_data", None)
            if not image_data:
                print("[WARN] 画像データが取得できませんでした。")
            else:
                if image_data.startswith("data:"):
                    _, base64_data = image_data.split(",", 1)
                else:
                    base64_data = image_data
                try:
                    png_bytes = base64.b64decode(base64_data)
                except Exception as exc:  # noqa: BLE001
                    print(f"[WARN] base64 デコードに失敗しました: {exc}")
                    png_bytes = b""

                if png_bytes:
                    np_data = np.frombuffer(png_bytes, np.uint8)
                    image = cv2.imdecode(np_data, cv2.IMREAD_COLOR)
                    if image is not None:
                        crop = image
                        if bbox:
                            x, y, w, h = bbox
                            crop = image[y : y + h, x : x + w]
                        processed = preprocess(crop)
                        best_label = "unknown"
                        best_score = 0.0
                        for label, tmpl_list in templates.items():
                            score = match_score(processed, tmpl_list)
                            if score > best_score:
                                best_label = label
                                best_score = score
                        result = best_label if best_score >= args.threshold else "unknown"
                        print(
                            json.dumps(
                                {
                                    "result": result,
                                    "score": round(best_score, 6),
                                    "timestamp": time.time(),
                                },
                                ensure_ascii=False,
                            )
                        )
                    else:
                        print("[WARN] PNG データのデコードに失敗しました。")

            time.sleep(max(args.interval, 0.5))
    except KeyboardInterrupt:
        print("[INFO] 監視を終了します。")
    finally:
        client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
