# OW2 Victory Counter (Rust版)

Overwatch 2 の勝敗を自動カウントして OBS に表示するツールです。CNN（深層学習）で勝敗画面を検知し、リアルタイムでカウントを更新します。

## 特徴

- ✅ **自動検知**: 勝敗画面を CNN で自動認識
- ✅ **OBS統合**: OBS Studio のブラウザーソースで表示
- ✅ **誤検知防止**: 連続検知 + クールダウンで精度向上
- ✅ **カスタマイズ**: CSS で見た目を自由に変更可能
- ✅ **管理画面**: ブラウザーで手動調整・リセット可能

## 必要環境

- **OS**: Windows 10/11, macOS, Linux
- **OBS Studio**: 28.0 以上
  - OBS WebSocket プラグイン有効化（Tools → WebSocket Server Settings）
- **モデルファイル**: victory_classifier.onnx

## インストール

### 1. 実行ファイルのダウンロード

[Releases](https://github.com/your-repo/releases) から最新版の実行ファイルをダウンロードします。

- Windows: `ow2-victory-detector.exe`
- macOS: `ow2-victory-detector`
- Linux: `ow2-victory-detector`

### 2. 設定ファイルの準備

`config.example.toml` を `config.toml` にコピーして編集します：

```bash
cp config.example.toml config.toml
```

**必須設定項目**:

```toml
[obs]
source_name = "OBS ソース名"  # OBSで表示しているゲーム画面のソース名

[model]
model_path = "models/victory_classifier.onnx"
label_map_path = "models/victory_classifier.label_map.json"

[preprocessing]
crop_rect = [465, 530, 512, 283]  # 勝敗表示の領域（要調整）
```

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

### 1. ツールの起動

```bash
# Windows
ow2-victory-detector.exe

# macOS / Linux
./ow2-victory-detector
```

起動時のログ:
```
INFO  Starting ow2-victory-detector...
INFO  Loading config from: config.toml
INFO  Connecting to OBS WebSocket at localhost:4455...
INFO  OBS WebSocket connected successfully
INFO  Loading ONNX model...
INFO  ONNX model loaded successfully
INFO  HTTP server listening on http://127.0.0.1:3000
INFO    - OBS UI: http://127.0.0.1:3000/
INFO    - Admin UI: http://127.0.0.1:3000/admin
INFO    - SSE endpoint: http://127.0.0.1:3000/events
INFO  Starting detection loop (interval: 1000ms, crop: (465, 530, 512, 283))
```

### 2. OBS にブラウザーソースを追加

1. OBS で `ソース` → `+` → `ブラウザー` を選択
2. 以下の設定を入力:
   - **URL**: `http://127.0.0.1:3000/`
   - **幅**: 1920
   - **高さ**: 1080
   - ☑ **ローカルファイル** のチェックを外す
   - ☑ **ソースが表示されたときにブラウザーの表示を更新する**

3. OKをクリック

カウンターが表示されます！

### 3. 管理画面でカウントを確認

ブラウザーで `http://127.0.0.1:3000/admin` を開くと、管理画面が表示されます。

機能:
- 現在のカウント表示
- `+` / `-` ボタンで手動調整
- `リセット` ボタンで全カウントをゼロに

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

### クロップ領域の調整

勝敗画面が正しく検知されない場合、`config.toml` の `crop_rect` を調整します：

```toml
[preprocessing]
# [x, y, width, height]
crop_rect = [465, 530, 512, 283]
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
