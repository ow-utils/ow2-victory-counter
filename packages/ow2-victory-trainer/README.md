# ow2-victory-trainer

Overwatch 2 の勝敗判定モデルを学習するためのプロジェクトです。

## 概要

このプロジェクトは、Overwatch 2 のゲーム画面から勝敗を判定する CNN（畳み込みニューラルネットワーク）モデルを学習します。学習したモデルは PyTorch 形式（.pth）で保存され、ONNX 形式に変換することで Rust 実装の推論エンジン（`ow2-victory-counter-rs`）で使用できます。

## プロジェクト構成

```
ow2-victory-trainer/
├── src/
│   └── victory_trainer/          # 再利用可能なライブラリコード
│       ├── model.py              # CNNモデル定義
│       ├── dataset.py            # データセット処理
│       └── inference/            # 推論エンジン（検証用）
│           ├── __init__.py
│           └── predictor.py
├── scripts/                       # 実行可能なスクリプト
│   ├── build_dataset.py          # データセット構築
│   ├── train_classifier.py       # 学習実行
│   ├── convert_to_onnx.py        # ONNX変換
│   ├── inference_pytorch.py      # PyTorchモデルでの推論テスト
│   └── inference_onnx.py         # ONNXモデルでの推論テスト
├── artifacts/
│   └── models/                   # 学習済みモデル（Gitにコミット）
│       └── victory_classifier.pth
├── pyproject.toml
└── README.md
```

## セットアップ

### 必要要件

- Python 3.11 以上
- [uv](https://github.com/astral-sh/uv) (Python パッケージマネージャー)

### インストール

```bash
cd packages/ow2-victory-trainer
uv sync
```

## 使い方

### 1. データセット構築

学習用データセットを構築します。元のサンプル画像から、クロップ・リサイズ・マスク処理を行います。

```bash
uv run python scripts/build_dataset.py --size 512 --mask
```

**オプション:**
- `--samples`: サンプル画像のディレクトリ（デフォルト: `data/samples`）
- `--output`: 出力先ディレクトリ（デフォルト: `dataset`）
- `--size`: リサイズ後の画像サイズ（長辺、省略時はリサイズしない）
- `--crop`: クロップ領域 `x,y,width,height`（省略時は推奨値 `460,378,995,550`）
- `--mask`: マスク領域（省略時はマスクなし、値を省略すると `0,534,1920,295`）

### 2. モデル学習

データセットを使ってモデルを学習します。

```bash
uv run python scripts/train_classifier.py --epochs 30 --batch-size 32
```

**オプション:**
- `--data`: データセットのディレクトリ（デフォルト: `dataset`）
- `--epochs`: エポック数（デフォルト: 30）
- `--batch-size`: バッチサイズ（デフォルト: 32）
- `--lr`: 学習率（デフォルト: 1e-3）
- `--checkpoint`: モデル保存先（デフォルト: `artifacts/models/victory_classifier.pth`）

学習済みモデルには以下が含まれます：
- `model_state_dict`: モデルの重み
- `label_map`: ラベル名→インデックスのマッピング
- `idx_to_label`: インデックス→ラベル名のマッピング

### 3. モデル検証

#### PyTorchモデルでの推論

学習直後の素早い検証に使用します。

```bash
uv run python scripts/inference_pytorch.py \
  --image path/to/test_image.png \
  --model artifacts/models/victory_classifier.pth \
  --size 512
```

**出力例:**
```json
{
  "image": "path/to/test_image.png",
  "outcome": "victory",
  "confidence": 0.9876,
  "predicted_class": "victory_text",
  "probabilities": [
    {"class": "defeat_progressbar", "probability": 0.0012},
    {"class": "defeat_text", "probability": 0.0034},
    {"class": "none", "probability": 0.0078},
    {"class": "victory_progressbar", "probability": 0.0123},
    {"class": "victory_text", "probability": 0.9876}
  ]
}
```

#### ONNXモデルでの推論

本番環境（Rust）と同じ形式での動作確認に使用します。まず ONNX 変換が必要です。

```bash
# ONNX変換
uv run python scripts/convert_to_onnx.py \
  --input artifacts/models/victory_classifier.pth \
  --output ../ow2-victory-counter-rs/models/victory_classifier.onnx

# ONNX推論
uv run python scripts/inference_onnx.py \
  --image path/to/test_image.png \
  --model ../ow2-victory-counter-rs/models/victory_classifier.onnx
```

### 4. ONNX変換

PyTorchモデルをONNX形式に変換します。変換後のモデルは Rust 実装で使用できます。

```bash
uv run python scripts/convert_to_onnx.py \
  --input artifacts/models/victory_classifier.pth \
  --output ../ow2-victory-counter-rs/models/victory_classifier.onnx \
  --height 550 \
  --width 995
```

**オプション:**
- `--input`: PyTorchモデルのパス
- `--output`: 出力先ONNXファイルのパス
- `--height`: 入力画像の高さ（デフォルト: 550）
- `--width`: 入力画像の幅（デフォルト: 995）
- `--opset`: ONNXオペレーターセットのバージョン（デフォルト: 17）

変換時に以下のファイルが生成されます：
- `victory_classifier.onnx`: ONNXモデル
- `victory_classifier.label_map.json`: クラスラベルマップ

## モデルの詳細

### アーキテクチャ

- **モデルタイプ**: CNN（畳み込みニューラルネットワーク）
- **クラス数**: 5クラス
  - `victory_text`: 勝利テキスト
  - `victory_progressbar`: 勝利プログレスバー
  - `defeat_text`: 敗北テキスト
  - `defeat_progressbar`: 敗北プログレスバー
  - `none`: 検知なし

### 前処理

1. マスク適用（オプション）
2. クロップ（推奨: 460, 378, 995, 550）
3. アスペクト比維持リサイズ（オプション）
4. BGR → RGB 変換
5. 0-1 正規化

## データについて

- 学習データは `data/samples/` に配置されています
- データセットは `dataset/` に生成されます
- これらは大容量のため `.gitignore` で除外されています

## ow2-victory-counter-rs との連携

学習したモデルを Rust 実装の推論エンジンで使用するには：

1. ONNX変換を実行
   ```bash
   uv run python scripts/convert_to_onnx.py
   ```

2. 生成されたファイルを確認
   - `../ow2-victory-counter-rs/models/victory_classifier.onnx`
   - `../ow2-victory-counter-rs/models/victory_classifier.label_map.json`

3. Rust プロジェクトでモデルを使用

## トラブルシューティング

### データセットが見つからない

```
[ERROR] dataset ... が見つかりません。先に build_dataset.py を実行してください。
```

→ `scripts/build_dataset.py` を実行してデータセットを構築してください。

### CUDA out of memory

→ `--batch-size` を小さくしてください（例: `--batch-size 16`）

### 推論時のエラー

→ モデルファイルのパスが正しいか確認してください。また、画像ファイルが存在し、読み込み可能か確認してください。

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。
