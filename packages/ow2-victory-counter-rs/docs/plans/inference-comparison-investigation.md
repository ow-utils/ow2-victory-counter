# 推論結果差異調査・解決計画

## 概要

### 問題の説明

Rust版（ONNX）での推論で、none クラスの confidence が頻繁に 1.00 になる現象が観察されています。

```
Prediction: [defeat_progressbar=0.00, defeat_text=0.00, none=1.00, victory_progressbar=0.00, victory_text=0.00] -> outcome=none (confidence=1.00)
```

これはPoCのPyTorch推論と比較して、推論結果に差異がある可能性を示唆しています。

### 調査の目的

1. PoCとRust版の前処理の違いを特定する
2. 同じ画像で両方の推論結果を比較する
3. 必要に応じて前処理を修正し、推論精度を向上させる

### 既知の差異

調査により以下の差異が判明しています：

| 項目 | PoC (Python) | Rust版 | 一致 |
|------|-------------|--------|------|
| 正規化 | 0-1 (/ 255.0) | 0-1 (/ 255.0) | ✅ |
| 色空間 | RGB | RGB | ✅ |
| テンソル形式 | NCHW | NCHW | ✅ |
| リサイズ | アスペクト比維持 or なし | **固定サイズ強制** | ❌ |
| フィルター | cv2.INTER_LINEAR | FilterType::Triangle | △ |

**主な問題**: リサイズ方法が異なる可能性があります。

---

## フェーズ1: PoCの処理方法を確認（調査）

### 1.1 PoCの実行設定を確認

**確認項目**:
- `packages/obs-victory-counter/victory-detector/start.ps1`
- `--image-size` パラメータが指定されているか
- 指定されている場合、そのサイズ（例: 512, 283など）

**確認方法**:
```bash
# start.ps1 を確認
cat packages/obs-victory-counter/victory-detector/start.ps1 | grep image-size

# または実行ログを確認
```

**判定基準**:
- `--image-size` が**指定されている** → リサイズあり
- `--image-size` が**指定されていない** → リサイズなし（995x550のまま）

### 1.2 学習時の画像サイズを確認

**確認項目**:
- 学習データセットのドキュメント
- モデルトレーニング時の設定

**確認方法**:
```bash
# データセット作成スクリプトを確認
cat packages/obs-victory-counter/victory-detector/scripts/create_dataset.py

# 学習スクリプトを確認
cat packages/obs-victory-counter/victory-detector/scripts/train.py
```

**期待される情報**:
- 学習データの解像度
- モデルが期待する入力サイズ

---

## フェーズ2: デバッグ用画像保存機能の追加

### 2.1 設定ファイルの拡張

`config.example.toml` に以下のセクションを追加:

```toml
[debug]
# デバッグ機能（開発・検証用）
enabled = false
save_dir = "debug"
save_cropped = true        # クロップ後の元画像を保存
save_preprocessed = true   # 前処理後（リサイズ後）の画像を保存
save_results = true        # 推論結果JSONを保存
```

### 2.2 実装内容

#### src/config.rs

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DebugConfig {
    #[serde(default = "default_debug_enabled")]
    pub enabled: bool,
    #[serde(default = "default_debug_save_dir")]
    pub save_dir: PathBuf,
    #[serde(default = "default_debug_save_cropped")]
    pub save_cropped: bool,
    #[serde(default = "default_debug_save_preprocessed")]
    pub save_preprocessed: bool,
    #[serde(default = "default_debug_save_results")]
    pub save_results: bool,
}

fn default_debug_enabled() -> bool { false }
fn default_debug_save_dir() -> PathBuf { PathBuf::from("debug") }
fn default_debug_save_cropped() -> bool { true }
fn default_debug_save_preprocessed() -> bool { true }
fn default_debug_save_results() -> bool { true }
```

#### src/main.rs（検知ループ）

```rust
// デバッグディレクトリ作成
if config.debug.enabled {
    tokio::fs::create_dir_all(&config.debug.save_dir).await?;
    info!("Debug mode enabled: {}", config.debug.save_dir.display());
}

// 検知ループ内
loop {
    // 画像キャプチャ
    let image = obs_capture.capture().await?;

    // デバッグ: 元画像を保存
    if config.debug.enabled && config.debug.save_cropped {
        let timestamp = Local::now().format("%Y%m%d-%H%M%S-%3f");
        let path = config.debug.save_dir.join(format!("cropped-{}.png", timestamp));
        image.save(&path)?;
    }

    // 前処理
    let processed = obs_capture.preprocess(image.clone(), crop_rect)?;

    // デバッグ: 前処理後の画像を保存
    if config.debug.enabled && config.debug.save_preprocessed {
        let timestamp = Local::now().format("%Y%m%d-%H%M%S-%3f");
        let path = config.debug.save_dir.join(format!("preprocessed-{}.png", timestamp));
        processed.save(&path)?;
    }

    // 推論
    let detection = predictor.predict(&processed)?;

    // デバッグ: 推論結果を保存
    if config.debug.enabled && config.debug.save_results {
        let timestamp = Local::now().format("%Y%m%d-%H%M%S-%3f");
        let result_json = serde_json::json!({
            "timestamp": timestamp.to_string(),
            "outcome": detection.outcome,
            "confidence": detection.confidence,
            "predicted_class": detection.predicted_class,
            "probabilities": detection.probabilities,
        });
        let path = config.debug.save_dir.join(format!("result-{}.json", timestamp));
        tokio::fs::write(&path, serde_json::to_string_pretty(&result_json)?).await?;
    }

    // ... 以降は既存の処理
}
```

### 2.3 目的

この機能により以下が可能になります:

1. **クロップ領域の検証**: クロップ後の画像を目視確認し、勝敗表示が正しく含まれているか確認
2. **前処理の検証**: リサイズ後の画像を確認し、歪みや劣化を確認
3. **PoC比較用データ**: 保存した画像をPoCで推論し、結果を比較
4. **推論結果の記録**: タイムスタンプ付きで推論結果を記録

### 2.4 変更ファイル一覧

1. `config.example.toml`: [debug] セクション追加
2. `src/config.rs`: DebugConfig 構造体追加
3. `src/main.rs`: デバッグ画像・結果保存処理追加

---

## フェーズ3: 比較テスト

### 3.1 Rust版で画像を保存

**手順**:

1. `config.toml` でデバッグモードを有効化:
   ```toml
   [debug]
   enabled = true
   save_dir = "debug"
   save_cropped = true
   save_preprocessed = true
   save_results = true
   ```

2. Rust版を実行:
   ```bash
   cargo run --release
   ```

3. none 検知時の画像を収集（数枚）
4. victory/defeat 検知時の画像も収集（参考用）

### 3.2 PoCで同じ画像を推論

**手順**:

1. 保存したクロップ後の画像をPoCで推論:
   ```bash
   cd packages/obs-victory-counter/victory-detector

   # 単一画像推論スクリプトを作成（必要に応じて）
   uv run python scripts/inference_single_image.py \
     --image ../../ow2-victory-counter-rs/debug/cropped-20251121-143025-123.png \
     --model artifacts/models/victory_classifier.pth
   ```

2. 推論結果（確率分布）を記録

### 3.3 結果の比較分析

**比較項目**:

| 画像ファイル | Rust版 confidence | PoC confidence | 差分 | 判定 |
|------------|------------------|----------------|------|------|
| cropped-001.png | none=1.00 | none=0.95 | 0.05 | 小 |
| cropped-002.png | none=1.00 | victory=0.85 | - | **大** |

**判定基準**:

- **差が小さい（< 0.1）**: 前処理はほぼ同じ → モデルの問題、またはクロップ位置の問題
- **差が大きい（≥ 0.1）**: **前処理の違いが原因** → フェーズ4へ

**可視化**（オプション）:
```python
import matplotlib.pyplot as plt

# 確率分布の比較グラフ
classes = ['defeat_pb', 'defeat_text', 'none', 'victory_pb', 'victory_text']
rust_probs = [0.00, 0.00, 1.00, 0.00, 0.00]
poc_probs = [0.05, 0.10, 0.70, 0.10, 0.05]

plt.bar(classes, rust_probs, alpha=0.5, label='Rust')
plt.bar(classes, poc_probs, alpha=0.5, label='PoC')
plt.legend()
plt.show()
```

---

## フェーズ4: 必要に応じて修正

### 4.1 パターンA: PoCがリサイズしていない場合

**前提**: PoCで `--image-size` が指定されておらず、クロップ後の995x550画像をそのまま使用

**対応**: Rust版も**リサイズを削除**

#### 修正内容

**src/predictor/onnx.rs**:

```rust
fn image_to_tensor(&self, image: &DynamicImage) -> Result<Array4<f32>, PredictionError> {
    // リサイズせず、そのままテンソル化
    let rgb_image = image.to_rgb8();
    let (width, height) = (image.width(), image.height());

    debug!(
        "Converting image to tensor: {}x{} RGB (no resize)",
        width, height
    );

    // NCHW 形式のテンソルを作成（可変サイズ）
    let mut tensor = Array4::<f32>::zeros((1, 3, height as usize, width as usize));

    // HWC (image) → CHW (tensor) 変換 + 正規化
    for y in 0..height {
        for x in 0..width {
            let pixel = rgb_image.get_pixel(x, y);
            tensor[[0, 0, y as usize, x as usize]] = pixel[0] as f32 / 255.0;
            tensor[[0, 1, y as usize, x as usize]] = pixel[1] as f32 / 255.0;
            tensor[[0, 2, y as usize, x as usize]] = pixel[2] as f32 / 255.0;
        }
    }

    Ok(tensor)
}
```

**注意**: ONNXモデルが可変サイズ入力を受け付けるか事前確認が必要

### 4.2 パターンB: PoCが512x283にリサイズしていた場合

**前提**: PoCで `--image-size 512` などが指定されており、アスペクト比維持リサイズを実施

**対応1**: アスペクト比維持リサイズに変更

```rust
fn image_to_tensor(&self, image: &DynamicImage) -> Result<Array4<f32>, PredictionError> {
    const TARGET_WIDTH: u32 = 512;
    const TARGET_HEIGHT: u32 = 283;

    // アスペクト比維持リサイズ
    let resized = image.resize(
        TARGET_WIDTH,
        TARGET_HEIGHT,
        image::imageops::FilterType::Triangle,
    );

    // 足りない部分を黒でパディング（必要に応じて）
    // ...
}
```

**対応2**: 現在の固定サイズリサイズのまま維持（リサイズアルゴリズムのみ確認）

```rust
// 既存のコードと同じ（変更なし）
let resized = image.resize_exact(
    TARGET_WIDTH,
    TARGET_HEIGHT,
    image::imageops::FilterType::Triangle,
);
```

### 4.3 ONNXモデルの入力形状を確認

**確認方法**:

```bash
# ONNXモデルの情報を表示
python -c "
import onnx
model = onnx.load('models/victory_classifier.onnx')
print(model.graph.input[0])
"
```

**期待される出力例**:
```
name: "input"
type {
  tensor_type {
    elem_type: 1  # FLOAT
    shape {
      dim { dim_value: 1 }      # batch
      dim { dim_value: 3 }      # channels
      dim { dim_value: 283 }    # height（固定）
      dim { dim_value: 512 }    # width（固定）
    }
  }
}
```

または:
```
dim { dim_param: "height" }  # 可変
dim { dim_param: "width" }   # 可変
```

**判定**:
- `dim_value` が指定 → **固定サイズ入力のみ** → リサイズ必須
- `dim_param` が指定 → **可変サイズ入力可能** → リサイズ不要

### 4.4 最適な前処理を決定

比較テスト結果に基づいて最終判断:

| 比較結果 | 判断 | 対応 |
|---------|------|------|
| 確率分布がほぼ一致 | 前処理は問題なし | クロップ位置を調整、またはモデル再学習を検討 |
| 確率分布が大きく異なる | 前処理に問題あり | PoCの処理方法に完全一致させる |
| Rust版の方が精度が高い | Rust版の前処理が優れている | 現在の実装を維持 |

---

## 実装の優先順位

### 優先度: 最高 ⭐⭐⭐

**フェーズ1: PoCの処理方法を確認**
- すぐに実行可能
- 実装不要、調査のみ
- 所要時間: 30分

### 優先度: 高 ⭐⭐

**フェーズ2: デバッグ用画像保存機能の追加**
- 実装が必要
- 比較テストの前提条件
- 所要時間: 2-3時間

### 優先度: 中 ⭐

**フェーズ3: 比較テスト**
- フェーズ2完了後に実施
- 手動での確認作業
- 所要時間: 1-2時間

### 優先度: 低（条件付き）

**フェーズ4: 必要に応じて修正**
- 比較結果次第で実施
- 所要時間: 1-4時間（修正内容による）

---

## 期待される成果

### 短期的成果（フェーズ1-3）

1. **原因の特定**: PoCとRust版の推論結果の差異の原因を特定
2. **データの蓄積**: デバッグ画像・結果の収集により、後続の改善作業の基礎データを確保
3. **可視化**: クロップ領域や前処理結果を目視確認可能に

### 長期的成果（フェーズ4）

1. **推論精度の向上**: 適切な前処理により、none の過剰検知を削減
2. **PoC互換性の確保**: PoCと同等の推論結果を実現
3. **保守性の向上**: デバッグ機能により、将来的な問題の早期発見が可能

---

## 参考情報

### 関連ファイル

- **PoC前処理**: `packages/obs-victory-counter/victory-detector/src/victory_detector/inference/predictor.py`
- **Rust前処理**: `packages/ow2-victory-counter-rs/src/predictor/onnx.rs`
- **学習データ**: `packages/obs-victory-counter/victory-detector/scripts/dataset.py`

### 関連ドキュメント

- ONNX変換: `packages/obs-victory-counter/victory-detector/scripts/convert_to_onnx.py`
- モデル仕様: `packages/ow2-victory-counter-rs/models/victory_classifier.label_map.json`

---

**作成日**: 2025-01-21
**ステータス**: 計画中
**次のアクション**: フェーズ1の調査を開始
