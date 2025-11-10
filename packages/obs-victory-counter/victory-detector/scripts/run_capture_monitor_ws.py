"""obs-websocket を利用したCNN勝敗判定モニター。

OBS 5.x の websocket API を使用し、指定ソースのスクリーンショットを
一定間隔で取得してCNNで勝敗判定、結果とカウント状態を標準出力へログ出力する。
"""

from __future__ import annotations

import argparse
import base64
import json
import time
from datetime import datetime
from pathlib import Path

import cv2  # type: ignore
import numpy as np  # type: ignore
from obsws_python import ReqClient

from victory_detector.core.state import EventLog, StateManager
from victory_detector.inference import VictoryPredictor

DEFAULT_INTERVAL = 0.25
DEFAULT_COOLDOWN = 180
DEFAULT_REQUIRED_CONSECUTIVE = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OBS websocket CNN victory detector")
    parser.add_argument("--host", default="127.0.0.1", help="OBS WebSocket host")
    parser.add_argument("--port", type=int, default=4455, help="OBS WebSocket port")
    parser.add_argument("--password", default="", help="OBS WebSocket password")
    parser.add_argument("--source", required=True, help="スクリーンショット対象のソース名")
    parser.add_argument("--model", type=Path, default=Path("artifacts/models/victory_classifier.pth"), help="学習済みモデルのパス")
    parser.add_argument("--event-log", type=Path, default=Path("logs/detections.jsonl"), help="イベントログの保存先")
    parser.add_argument("--cooldown", type=int, default=DEFAULT_COOLDOWN, help="クールダウン時間（秒）")
    parser.add_argument("--required-consecutive", type=int, default=DEFAULT_REQUIRED_CONSECUTIVE, help="カウントに必要な連続検知回数")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="キャプチャ間隔（秒）")
    parser.add_argument("--screenshot-width", type=int, default=1920, help="スクリーンショットの幅")
    parser.add_argument("--screenshot-height", type=int, default=1080, help="スクリーンショットの高さ")
    parser.add_argument("--save-detections", type=Path, default=None, help="検知時のスクリーンショット保存先ディレクトリ（オプション）")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # モデルファイルの存在確認
    if not args.model.exists():
        print(f"[ERROR] モデルファイルが見つかりません: {args.model}")
        return 1

    # VictoryPredictorの初期化
    print("[INFO] CNN推論モジュールを初期化中...")
    predictor = VictoryPredictor(
        model_path=args.model,
        crop_region=(460, 378, 995, 550),
    )
    print(f"[INFO] Device: {predictor.device}")
    print(f"[INFO] Classes: {list(predictor.label_map.keys())}")

    # StateManagerの初期化
    event_log = EventLog(args.event_log)
    state_manager = StateManager(event_log, cooldown_seconds=args.cooldown, required_consecutive=args.required_consecutive)
    print(f"[INFO] クールダウン: {args.cooldown}秒")
    print(f"[INFO] 連続検知回数: {args.required_consecutive}回")
    print(f"[INFO] イベントログ: {args.event_log}")
    print(
        f"[INFO] 現在のカウント: "
        f"Victory={state_manager.summary.victories}, "
        f"Defeat={state_manager.summary.defeats}, "
        f"Draw={state_manager.summary.draws}"
    )

    # スクリーンショット保存ディレクトリの作成
    if args.save_detections:
        args.save_detections.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] 検知時スクリーンショット保存: {args.save_detections}")

    # OBS接続
    client = ReqClient(host=args.host, port=args.port, password=args.password)
    print("[INFO] obs-websocket (5.x) に接続しました。Ctrl+C で終了します。")

    try:
        while True:
            # スクリーンショット取得
            resp = client.get_source_screenshot(
                args.source,
                "png",
                args.screenshot_width,
                args.screenshot_height,
                -1,
            )

            # レスポンスからimage_dataを取得
            if isinstance(resp, dict):
                image_data = resp.get("imageData") or resp.get("imageDataBase64")
            else:
                image_data = getattr(resp, "image_data", None)

            if not image_data:
                print("[WARN] 画像データが取得できませんでした。")
            else:
                # Base64デコード
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
                    # 画像デコード
                    np_data = np.frombuffer(png_bytes, np.uint8)
                    image = cv2.imdecode(np_data, cv2.IMREAD_COLOR)

                    if image is not None:
                        # CNN推論
                        detection = predictor.predict(image)

                        # StateManagerに記録（連続検知対応）
                        response = state_manager.record_detection(detection)

                        # 検知時スクリーンショット保存（最初の検知のみ）
                        if args.save_detections and response.is_first_detection and detection.outcome in ("victory", "defeat", "draw"):
                            timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]  # ミリ秒まで
                            predicted_class = detection.predicted_class or "unknown"
                            filename = f"{timestamp_str}-{predicted_class}-first.png"
                            filepath = args.save_detections / filename
                            cv2.imwrite(str(filepath), image)
                            print(f"[INFO] スクリーンショット保存: {filename}")

                        # 結果出力
                        output: dict = {
                            "outcome": detection.outcome,
                            "confidence": round(detection.confidence, 4),
                            "counted": response.event is not None,
                            "consecutive_count": response.consecutive_count,
                            "consecutive_required": args.required_consecutive,
                            "timestamp": time.time(),
                            "counter": {
                                "victories": state_manager.summary.victories,
                                "defeats": state_manager.summary.defeats,
                                "draws": state_manager.summary.draws,
                            },
                        }

                        # カウントされた場合
                        if response.event:
                            output["predicted_class"] = detection.predicted_class

                        print(json.dumps(output, ensure_ascii=False))
                    else:
                        print("[WARN] PNG データのデコードに失敗しました。")

            time.sleep(max(args.interval, 0.5))

    except KeyboardInterrupt:
        print("\n[INFO] 監視を終了します。")
    finally:
        client.disconnect()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
