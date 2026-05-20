# 学習パラメーター(学習作業ログ) 2025-11-28

英語も認識できるようにする。
パラメーターは前回と完全に一緒で良さそう。

## 学習

プログレスバー画面の左上に表示されている「勝利！」「敗北」で勝敗を判断できるだろう、という想定で学習させてみる。

```bash
cd packages/ow2-victory-trainer
```

```bash
uv sync
rm -r dataset
uv run python scripts/build_dataset.py --crop 36,123,248,92
uv run python scripts/train_classifier.py
uv run python scripts/convert_to_onnx.py \
  --input artifacts/models/victory_classifier.pth \
  --output ../ow2-victory-counter-rs/models/victory_classifier.onnx \
  --opset 18 \
  --width 248 \
  --height 92
```

## 推論検証

```bash
cd ../ow2-victory-counter-rs
```

```bash
uv run cargo run --bin ow2-victory-detector -- predict \
    --image ../ow2-victory-trainer/data/samples/defeat/defeat_progressbar/20251110-220009-923-defeat_progressbar-first.png
uv run cargo run --bin ow2-victory-detector -- predict \
    --image ../ow2-victory-trainer/data/samples/victory/victory_progressbar/20251110-225420-329-victory_progressbar-first.png
uv run cargo run --bin ow2-victory-detector -- predict \
    --image ../ow2-victory-trainer/data/samples/none/20251110-233346-009-defeat_text-first.png
uv run cargo run --bin ow2-victory-detector -- predict \
    --image ../ow2-victory-trainer/data/samples/defeat/defeat_progressbar_en/スクリーンショット\ 2025-11-28\ 231431.png
uv run cargo run --bin ow2-victory-detector -- predict \
    --image ../ow2-victory-trainer/data/samples/victory/victory_progressbar_en/スクリーンショット\ 2025-11-28\ 231303.png
```
