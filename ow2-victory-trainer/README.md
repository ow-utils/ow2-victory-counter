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
│   ├── retrain.py                # データセット構築・学習・ONNX変換の一括実行
│   ├── retrain_all.py            # 全言語一括再学習
│   ├── build_dataset.py          # データセット構築
│   ├── train_classifier.py       # 学習実行
│   ├── convert_to_onnx.py        # ONNX変換
│   ├── inference_pytorch.py      # PyTorchモデルでの推論テスト
│   └── inference_onnx.py         # ONNXモデルでの推論テスト
├── artifacts/
│   └── models/                   # 学習済みモデル（言語別）
│       ├── ja/
│       │   └── victory_classifier.pth
│       └── en/
│           └── victory_classifier.pth
├── pyproject.toml
└── README.md
```

## セットアップ

### 必要要件

- Python 3.11 以上
- [uv](https://github.com/astral-sh/uv) (Python パッケージマネージャー)

### インストール

```bash
cd ow2-victory-trainer
uv sync
```

## 使い方

### 一括再学習

データセット構築、モデル学習、ONNX 変換、`victory` / `defeat` / `none` 各クラスの推論確認をまとめて実行します。

```bash
uv run python scripts/retrain.py
```

既存の `dataset` を削除して作り直す場合は `--clean-dataset` を指定します。

```bash
uv run python scripts/retrain.py --clean-dataset
```

言語別に再学習する場合は `--lang` を指定します（推奨）。

```bash
# 言語別に再学習（推奨）
uv run python scripts/retrain.py --lang ja --clean-dataset --mask
uv run python scripts/retrain.py --lang en --clean-dataset --mask
```

**主なオプション:**

- `--lang`: 学習対象の言語コード (例: ja, en)。指定時に samples/dataset/checkpoint/onnx-output パスを `{lang}/` 配下に自動切替し、`data/samples/shared/` を共通サンプルとして併用する
- `--samples`: サンプル画像のディレクトリ（デフォルト: `data/samples`）
- `--dataset`: データセットの出力先・学習元ディレクトリ（デフォルト: `dataset`）
- `--checkpoint`: PyTorch モデル保存先（デフォルト: `artifacts/models/victory_classifier.pth`）
- `--onnx-output`: ONNX モデル保存先（デフォルト: `../ow2-victory-counter-rs/models/victory_classifier.onnx`）
- `--clean-dataset`: データセット構築前に `--dataset` のディレクトリを削除する
- `--skip-build`: データセット構築をスキップする
- `--skip-convert`: ONNX 変換をスキップする
- `--skip-verify`: ONNX 変換後の推論確認をスキップする
- `--verify-samples`: 推論確認に使うサンプル画像ディレクトリ（デフォルト: `--samples` と同じ）
- `--verify-count-per-class`: 推論確認で各クラスから使用する画像数（デフォルト: 1）
- `--epochs`: エポック数（デフォルト: 30）
- `--batch-size`: バッチサイズ（デフォルト: 32）
- `--crop`: クロップ領域（デフォルト: `42,156,245,108`）
- `--height`: ONNX 入力画像の高さ（デフォルト: 108）
- `--width`: ONNX 入力画像の幅（デフォルト: 245）
- `--opset`: ONNX オペレーターセットのバージョン（デフォルト: 22）

### 全言語一括再学習

`data/samples/` 配下の言語ディレクトリーを自動検出し、各言語に対して `retrain.py --lang {lang}` を順次実行します。

```bash
uv run python scripts/retrain_all.py --clean-dataset --mask
```

`retrain.py` で受け付けるオプションはそのまま透過されます (例: `--epochs`, `--batch-size`, `--lr`, `--mask`, `--clean-dataset` 等)。
途中のいずれかの言語で失敗した場合はそこで停止します。

### 1. データセット構築

学習用データセットを構築します。元のサンプル画像から、クロップ・リサイズ・マスク処理を行います。

```bash
uv run python scripts/build_dataset.py
```

**オプション:**

- `--samples`: サンプル画像のディレクトリ（デフォルト: `data/samples`）
- `--output`: 出力先ディレクトリ（デフォルト: `dataset`）
- `--size`: リサイズ後の画像サイズ（長辺、省略時はリサイズしない）
- `--crop`: クロップ領域 `x,y,width,height`（省略時は推奨値 `42,156,245,108`）
- `--mask`: マスク領域（省略時はマスクなし、値を省略すると `0,534,1920,295`）
- `--shared`: 言語共通サンプルディレクトリ (例: `data/samples/shared`)。指定時に各ラベルの画像を `--output` の対応ラベルへマージする

### 2. モデル学習

データセットを使ってモデルを学習します。

```bash
uv run python scripts/train_classifier.py
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
  "predicted_class": "victory",
  "probabilities": [
    { "class": "defeat", "probability": 0.0034 },
    { "class": "none", "probability": 0.0078 },
    { "class": "victory", "probability": 0.9876 }
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
  --model ../ow2-victory-counter-rs/models/victory_classifier.onnx \
  --height 108 \
  --width 245
```

### 4. ONNX変換

PyTorchモデルをONNX形式に変換します。変換後のモデルは Rust 実装で使用できます。

```bash
uv run python scripts/convert_to_onnx.py \
  --input artifacts/models/victory_classifier.pth \
  --output ../ow2-victory-counter-rs/models/victory_classifier.onnx \
  --height 108 \
  --width 245 \
  --opset 22
```

**オプション:**

- `--input`: PyTorchモデルのパス
- `--output`: 出力先ONNXファイルのパス
- `--height`: 入力画像の高さ（デフォルト: 108）
- `--width`: 入力画像の幅（デフォルト: 245）
- `--opset`: ONNXオペレーターセットのバージョン（デフォルト: 22）

変換時に以下のファイルが生成されます：

- `victory_classifier.onnx`: ONNXモデル
- `victory_classifier.label_map.json`: クラスラベルマップ

## モデルの詳細

### アーキテクチャ

- **モデルタイプ**: CNN（畳み込みニューラルネットワーク）
- **クラス数**: 3クラス
  - `victory`: 勝利
  - `defeat`: 敗北
  - `none`: 検知なし

### 前処理

1. マスク適用（オプション）
2. クロップ（推奨: 42, 156, 245, 108）
3. アスペクト比維持リサイズ（オプション）
4. BGR → RGB 変換
5. 0-1 正規化

## データについて

- 学習データは `data/samples/{lang}/` 配下に言語別に配置します (例: `data/samples/ja/victory/`, `data/samples/en/defeat/`)
- 言語に依存しないサンプル (ゲーム中画面・ロビーなど none クラス) は `data/samples/shared/none/` に配置します
- データセットは `dataset/{lang}/` に生成されます (build 時に shared の画像が各言語にマージされます)
- これらは大容量のため `.gitignore` で除外されています

## ow2-victory-counter-rs との連携

学習したモデルを Rust 実装の推論エンジンで使用するには：

1. ONNX変換を実行 (言語別)

   ```bash
   uv run python scripts/retrain.py --lang ja --skip-build --skip-verify
   ```

2. 生成されたファイルを確認
   - `../ow2-victory-counter-rs/models/{lang}/victory_classifier.onnx`
   - `../ow2-victory-counter-rs/models/{lang}/victory_classifier.label_map.json`

3. Rust プロジェクト側で `config.toml` の `[model]` セクションに対応するパスを指定

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
