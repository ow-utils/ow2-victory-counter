# ONNX ファイル形式について

## 概要

ONNX (Open Neural Network Exchange) モデルには、2つの保存形式があります：

1. **単一ファイル形式**: すべてのデータを1つの `.onnx` ファイルに保存
2. **外部データ形式**: モデル構造を `.onnx` ファイルに、重みを `.onnx.data` ファイルに分離

このドキュメントでは、それぞれの特徴と使い分けについて説明します。

---

## 1. 単一ファイル形式（.onnx のみ）

### 特徴

- **ファイル構成**: `.onnx` ファイル1つのみ
- **データ保存**: モデル構造と重みをすべて Protocol Buffers 形式で1つのファイルに保存
- **サイズ制限**: Protocol Buffers の制限により、**2GB以下**のモデルに適用

### メリット

✅ **デプロイが簡単**: 1ファイルのみ配布すればよい
✅ **管理が容易**: ファイル紛失のリスクがない
✅ **シンプル**: パスの指定や依存関係の心配が不要

### デメリット

❌ **サイズ制限**: 2GB を超えるモデルは保存できない
❌ **メモリ効率**: 大きなモデルの場合、すべてをメモリに読み込む必要がある

### 使用例

```python
import torch

# 単一ファイル形式で保存
torch.onnx.export(
    model,
    dummy_input,
    "model.onnx",
    export_params=True,
    external_data=False,  # 👈 これを指定
    # ... その他のパラメータ
)
```

---

## 2. 外部データ形式（.onnx + .onnx.data）

### 特徴

- **ファイル構成**:
  - `.onnx`: モデル構造と外部データへの参照（メタデータ）
  - `.onnx.data`: 実際のモデルの重み
- **データ保存**: 重みは `.onnx.data` に保存され、`.onnx` ファイルには参照情報（ファイルパス、オフセット、長さ）のみ
- **サイズ制限**: **2GB以上**のモデルに対応可能

### メリット

✅ **大規模モデル対応**: 2GB を超えるモデルを保存可能
✅ **メモリ効率**: 必要な部分のみ読み込むことが可能（実装による）
✅ **重みの共有**: 複数のモデルで同じ重みファイルを参照できる（高度な用途）

### デメリット

❌ **デプロイが複雑**: 2ファイルを正しく配置する必要がある
❌ **ファイル紛失リスク**: `.onnx.data` を忘れるとモデルが動作しない
❌ **パス依存**: `.onnx.data` は `.onnx` と同じディレクトリに配置する必要がある

### 使用例

```python
import torch

# 外部データ形式で保存
torch.onnx.export(
    model,
    dummy_input,
    "model.onnx",
    export_params=True,
    external_data=True,  # 👈 これを指定（または省略）
    # ... その他のパラメータ
)
```

**重要**: `.onnx.data` ファイルは `.onnx` ファイルと**同じディレクトリ**に配置する必要があります。

---

## 3. PyTorch でのデフォルト動作

### PyTorch のバージョンによる違い

| PyTorch バージョン | デフォルト動作 | 備考 |
|-------------------|---------------|------|
| < 2.1 | 単一ファイル形式 | `use_external_data_format=False` |
| ≥ 2.1 (dynamo exporter) | **外部データ形式** | `external_data=True` がデフォルト |
| ≥ 2.1 (legacy exporter) | 単一ファイル形式 | `dynamo=False` で使用可能 |

### 注意点

- **PyTorch 2.1 以降**では、新しい dynamo ベースのエクスポーターが使われる場合があります
- パラメータを明示的に指定しないと、**意図しない形式**で保存される可能性があります
- **推奨**: `external_data` パラメータを**明示的に指定する**

```python
# ✅ 推奨: 明示的に指定
torch.onnx.export(
    model,
    dummy_input,
    "model.onnx",
    external_data=False,  # 👈 明示的に指定
    # ...
)
```

---

## 4. Rust ort クレートでの対応

### 対応状況

Rust の `ort` クレート（ONNX Runtime のラッパー）は、**両方の形式をサポート**しています。

### 読み込み方法

```rust
use ort::{Session, SessionBuilder};

// ファイルパスから読み込み（両方の形式に対応）
let session = SessionBuilder::new()?
    .commit_from_file("model.onnx")?;
```

### 動作

- **単一ファイル形式**: `model.onnx` のみを読み込む
- **外部データ形式**: `model.onnx` を読み込む際、ONNX Runtime が自動的に同じディレクトリの `model.onnx.data` を検出して読み込む

### 注意点

- 外部データ形式の場合、`.onnx.data` ファイルが**同じディレクトリ**に存在する必要があります
- ファイルパスベースの読み込み（`commit_from_file`）を使用する場合、ONNX Runtime が自動的に処理します
- メモリから読み込む場合（`commit_from_memory`）は、外部データ形式は使用できません

---

## 5. どちらを選ぶべきか？

### 選択基準

| モデルサイズ | 推奨形式 | 理由 |
|-------------|---------|------|
| **< 2GB** | **単一ファイル形式** | デプロイが簡単、管理が容易 |
| **≥ 2GB** | **外部データ形式** | Protocol Buffers の制限により必須 |

### このプロジェクトでの判断

**ow2-victory-counter-rs プロジェクト**では、以下の理由で**単一ファイル形式**を採用しました：

- モデルサイズ: 約 408KB（非常に小さい）
- デプロイ先: エンドユーザーの環境（ファイル管理を簡単に）
- 配布方法: ZIP ファイルによる配布（1ファイルの方が扱いやすい）

```python
# convert_to_onnx.py での設定
torch.onnx.export(
    model,
    dummy_input,
    output_path,
    export_params=True,
    opset_version=opset_version,
    do_constant_folding=True,
    input_names=["input"],
    output_names=["output"],
    dynamic_axes={
        "input": {0: "batch_size"},
        "output": {0: "batch_size"},
    },
    external_data=False,  # 👈 単一ファイル形式を明示的に指定
)
```

---

## 6. トラブルシューティング

### 問題: モデルが2ファイルに分かれてしまった

**症状**: `.onnx` と `.onnx.data` の2つのファイルが生成された

**原因**: `external_data` パラメータが指定されていない、または `True` になっている

**解決策**:
```python
# external_data=False を追加
torch.onnx.export(
    model,
    dummy_input,
    "model.onnx",
    external_data=False,  # 👈 追加
    # ...
)
```

### 問題: Rust で「外部データファイルが見つからない」エラー

**症状**: ONNX モデルの読み込み時にエラーが発生

**原因**: `.onnx.data` ファイルが `.onnx` ファイルと同じディレクトリにない

**解決策**:
1. `.onnx.data` ファイルを `.onnx` ファイルと同じディレクトリに配置
2. または、単一ファイル形式でモデルを再変換

---

## 7. 参考資料

- [ONNX 公式ドキュメント](https://onnx.ai/)
- [PyTorch ONNX Export ドキュメント](https://pytorch.org/docs/stable/onnx.html)
- [ONNX Runtime ドキュメント](https://onnxruntime.ai/)
- [ort クレート（Rust）](https://docs.rs/ort/)

---

## 更新履歴

- 2025-11-19: 初版作成（Task 7 ONNX変換時の調査結果をまとめ）
