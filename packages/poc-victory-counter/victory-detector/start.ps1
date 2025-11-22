uv run python scripts/run_capture_monitor_ws.py `
--host 127.0.0.1 `
--port 4455 `
--source "ゲームキャプチャ" `
--model artifacts/models/victory_classifier.pth `
--event-log logs/detections.jsonl `
--cooldown 5 `
--save-detections save-detections `
--size 512
