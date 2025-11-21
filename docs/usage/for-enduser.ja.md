# OW2 Victory Counter

Overwatch 2 の勝敗を自動カウントして OBS に表示するツールです。CNN（深層学習）で勝敗画面を検知し、リアルタイムでカウントを更新します。

CSSの知識があればある程度デザインをカスタマイズすることが可能です。

## リンク

つぎのURLをブックマークしておくと便利です:

- [README](https://github.com/ow-utils/ow-utils/blob/main/packages/ow2-victory-counter-rs/README.md): 本ファイルをWebで見られます
- [adminページ](http://localhost:3000/admin): このプログラムの管理画面です
  - 開けるのはプログラム実行中のみです
  - 設定でポートを変更した場合はこのページのポート番号も変わります

## セットアップ

### 1. 実行ファイルのダウンロード

[Releases](https://github.com/ow-utils/ow-utils/releases) から最新版のをダウンロードし、適当なディレクトリーに展開します。

### 2. 設定ファイルの準備

`config.example.toml` を `config.toml` にコピーして編集します。

**必須設定項目**:

```toml
[obs]
source_name = "ゲームキャプチャ" # OW2をキャプチャしているOBSのソース名
```

**"ゲームキャプチャ"** の部分を、あなたのOBS設定に合わせて更新してください。
なお、ソースは1920x1080など16:9のアスペクト比であることを前提としています。

### 3. OBS WebSocket の有効化

1. OBS Studio を起動
2. `ツール` → `WebSocket サーバー設定` を開く
3. `WebSocket サーバーを有効にする` にチェック
4. ポート番号を確認（デフォルト: 4455）
5. パスワードを設定した場合は `config.toml` に記載

```toml
[obs]
password = "your-password"  # パスワード設定時のみ
```

## 使い方

### 1. サーバーモード（通常使用）

#### 1.1 ツールの起動

`ow2-victory-detector.exe` をダブルクリックして起動してください。

#### 1.2 OBS にブラウザーソースを追加

1. OBS で `ソース` → `+` → `ブラウザー` を選択
2. 以下の設定を入力:

   - **URL**: `http://127.0.0.1:3000/`
   - **幅**: 1920
   - **高さ**: 1080
   - ☑ **ローカルファイル** のチェックを外す
   - ☑ **ソースが表示されたときにブラウザーの表示を更新する**

3. OKをクリック

カウンターが表示されます！

#### 1.3 管理画面でカウントを確認

ブラウザーで `http://127.0.0.1:3000/admin` を開くと、管理画面が表示されます。

機能:

- 現在のカウント表示
- `+` / `-` ボタンで手動調整
- `リセット` ボタンで全カウントをゼロに

### 2. 予測モード（比較テスト・デバッグ用）

単一の画像ファイルに対して推論を実行するモードです。PoCとの比較テストやデバッグに活用できます。

#### 2.1 基本的な使い方

```bash
# Windows
ow2-victory-detector.exe predict ^
  --image path/to/image.png ^
  --model models/victory_classifier.onnx ^
  --label-map models/victory_classifier.label_map.json

# macOS / Linux
./ow2-victory-detector predict \
  --image path/to/image.png \
  --model models/victory_classifier.onnx \
  --label-map models/victory_classifier.label_map.json
```

#### 2.2 オプション

| オプション    | 短縮形 | 必須 | 説明                                                 |
| ------------- | ------ | ---- | ---------------------------------------------------- |
| `--image`     | `-i`   | ✅   | 入力画像のパス                                       |
| `--model`     | `-m`   | ✅   | ONNXモデルファイルのパス                             |
| `--label-map` | `-l`   | ✅   | ラベルマップJSONファイルのパス                       |
| `--output`    | `-o`   | ❌   | 結果を保存するJSONファイルのパス（省略時は標準出力） |
| `--no-crop`   | -      | ❌   | クロップをスキップ（デバッグ用）                     |

#### 2.3 出力例

```json
{
  "image": "path/to/image.png",
  "outcome": "victory",
  "confidence": 0.95,
  "predicted_class": "victory_text",
  "probabilities": [
    { "class": "defeat_progressbar", "probability": 0.01 },
    { "class": "defeat_text", "probability": 0.02 },
    { "class": "none", "probability": 0.02 },
    { "class": "victory_progressbar", "probability": 0.0 },
    { "class": "victory_text", "probability": 0.95 }
  ]
}
```

#### 2.4 使用例: デバッグ画像で推論

デバッグモードで保存した画像を使って推論を実行：

```bash
# デバッグモードで保存された画像を推論
./ow2-victory-detector predict \
  --image debug/cropped-20251121-143025-123.png \
  --model models/victory_classifier.onnx \
  --label-map models/victory_classifier.label_map.json \
  --no-crop \
  --output result.json
```

`--no-crop` オプションを使うと、デバッグモードですでにクロップされた画像をそのまま推論できます。

#### 2.5 使用例: PoCとの比較テスト

同じ画像をPoCとRustで推論して結果を比較：

```bash
# Rust版で推論
./ow2-victory-detector predict \
  --image screenshot.png \
  --model models/victory_classifier.onnx \
  --label-map models/victory_classifier.label_map.json \
  --output rust_result.json

# PoC版で推論（別のディレクトリで実行）
cd ../obs-victory-counter/victory-detector
uv run python scripts/inference_single_image.py \
  --image ../../ow2-victory-counter-rs/screenshot.png \
  --model artifacts/models/victory_classifier.pth \
  --output ../../ow2-victory-counter-rs/poc_result.json

# 結果を比較
cd ../../ow2-victory-counter-rs
diff rust_result.json poc_result.json
```

## カスタマイズ

### CSS でスタイル変更

`templates/custom.css` を編集して見た目をカスタマイズできます：

```css
/* 色を変更 */
.counter-grid {
  --victory-color: #00ff00;
  --defeat-color: #ff0000;
  --font-size: 96px;
}

/* グロー効果 */
.value {
  text-shadow: 0 0 20px currentColor;
}
```

OBS のブラウザーソースで `カスタムCSS` に以下を追加:

```css
@import url("http://127.0.0.1:3000/custom.css");
```

### スクリーンショット保存機能

勝敗判定時のスクリーンショットを自動保存できます。誤検知の分析やモデル改善に活用できます。

**有効化方法**:

`config.toml` で以下のように設定:

```toml
[screenshot]
enabled = true
save_dir = "screenshots"  # 保存先ディレクトリ
```

**保存タイミング**:

- 連続検知の**最初の1回のみ**保存（ストレージ節約）
- victory, defeat のみ保存（none は保存しない）

**ファイル名形式**:

```
20251121-143025-123-victory_text-first.png
```

- タイムスタンプ（ミリ秒まで）
- 詳細クラス名（victory_text, defeat_progressbar など）
- `-first` サフィックス（連続検知の最初の1回を示す）

**保存される画像**:

- OBSから取得した元画像（前処理前）
- 解像度: OBS の出力サイズ（通常1920×1080）

### クロップ領域の調整

勝敗画面が正しく検知されない場合、`config.toml` の `crop_rect` を調整します：

```toml
[preprocessing]
# [x, y, width, height]
# 1920x1080 での標準的な位置
crop_rect = [460, 378, 995, 550]
```

調整方法:

1. OBS でゲーム画面のスクリーンショットを撮る
2. 画像編集ソフトで勝敗表示の位置・サイズを測定
3. `crop_rect` を更新

## トラブルシューティング

### OBS WebSocket に接続できない

**エラー**: `Failed to connect to OBS WebSocket`

**解決策**:

1. OBS Studio が起動しているか確認
2. WebSocket サーバーが有効になっているか確認（ツール → WebSocket サーバー設定）
3. ポート番号が一致しているか確認（デフォルト: 4455）
4. ファイアウォールで接続がブロックされていないか確認

### モデルファイルが見つからない

**エラー**: `Failed to read config file 'models/victory_classifier.onnx'`

**解決策**:

1. `models/` ディレクトリに ONNX モデルファイルがあるか確認
2. `config.toml` の `model_path` が正しいか確認

### 勝敗が検知されない

**原因**:

- クロップ領域が正しくない
- 画質が低い
- 勝敗表示が見切れている

**解決策**:

1. `crop_rect` を調整して勝敗表示全体が含まれるようにする
2. OBS の出力解像度を 1920x1080 にする
3. ログで `confidence` スコアを確認（0.8以上が望ましい）

### カウントが増えすぎる

**原因**:

- クールダウン時間が短すぎる
- 連続検知回数が少なすぎる

**解決策**:

`config.toml` を調整:

```toml
[state]
cooldown_seconds = 15  # クールダウンを延長
required_consecutive = 5  # 連続検知回数を増やす
```

## 開発者向け情報

### ビルド方法

```bash
# フロントエンドビルド
cd frontend
pnpm install
pnpm build

# Rustビルド
cd ..
cargo build --release
```

### 開発ワークフロー

フロントエンドの変更を開発しながらテストする場合:

**1. Vite 開発サーバーを起動** （別のターミナルで）:

```bash
cd frontend
pnpm dev
```

Vite が `http://localhost:5173` で起動します。

**2. Rust アプリケーションをデバッグモードで起動**:

```bash
cargo run
```

デバッグモード（`cargo run`）では、ブラウザーが自動的に Vite 開発サーバーへリダイレクトされ、フロントエンドの変更がホットリロードされます。

**注意**:

- `cargo run` （デバッグ）= Vite 開発サーバー（localhost:5173）へリダイレクト
- `cargo run --release` （リリース）= ビルド済みファイル（frontend/dist/）を配信

通常の使用では **`cargo run --release`** を推奨します。

### ログレベルの変更

環境変数で設定:

```bash
# Windows (PowerShell)
$env:RUST_LOG="debug"; .\ow2-victory-detector.exe

# macOS / Linux
RUST_LOG=debug ./ow2-victory-detector
```

## ライセンス

MIT License

## クレジット

- ONNX Runtime: https://onnxruntime.ai/
- OBS WebSocket: https://github.com/obsproject/obs-websocket
- Svelte: https://svelte.dev/
