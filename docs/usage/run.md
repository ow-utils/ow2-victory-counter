# 実行手順（Windows 環境）

このドキュメントでは、Windows 環境で ow2-victory-counter-rs を実行する手順を説明します。

---

## 前提条件

- [ビルド手順](./build.md) を完了していること
- OBS Studio 28.0 以上がインストールされていること
- `config.toml` が作成されていること

---

## 1. OBS Studio の設定

### 1.1 OBS WebSocket プラグインの有効化

1. OBS Studio を起動
2. メニューバーから **ツール** → **WebSocket サーバー設定** を選択
3. 以下の設定を行う：
   - ✅ **「WebSocket サーバーを有効にする」** にチェック
   - **サーバーポート**: `4455` （デフォルト）
   - **サーバーパスワード**: （オプション）パスワードを設定した場合は `config.toml` にも記載

4. **OK** をクリック

**確認方法**:
- OBS 下部のステータスバーに「WebSocket サーバー実行中」と表示されます

---

### 1.2 ゲーム画面ソースの追加

1. OBS の **ソース** パネルで **+** ボタンをクリック
2. **ゲームキャプチャ** または **ウィンドウキャプチャ** を選択
3. ソース名を入力（例: 「Overwatch 2」「ゲーム画面」）
   - **重要**: このソース名を `config.toml` の `source_name` に設定します
4. キャプチャ設定を行い、Overwatch 2 の画面が表示されることを確認

---

## 2. 設定ファイルの確認・編集

### 2.1 config.toml の確認

`packages/ow2-victory-counter-rs/config.toml` を開き、以下を確認：

```toml
[obs]
host = "localhost"
port = 4455
# password = "your-password"  # OBS WebSocket にパスワードを設定した場合は記載
source_name = "Overwatch 2"  # ← OBS で設定したソース名と一致させる

[model]
model_path = "models/victory_classifier.onnx"
label_map_path = "models/victory_classifier.label_map.json"

[preprocessing]
crop_rect = [465, 530, 512, 283]  # 勝敗表示の領域（1920x1080 の場合）

[state]
cooldown_seconds = 10  # 勝敗判定後のクールダウン時間（秒）
required_consecutive = 3  # 連続検知が必要な回数

[server]
host = "127.0.0.1"
port = 3000

[detection]
interval_ms = 1000  # 検知間隔（ミリ秒）
```

### 2.2 重要な設定項目

#### source_name
- **OBS のソース名と完全に一致**させる必要があります
- 大文字・小文字、スペースも区別されます

#### crop_rect
- 勝敗表示の領域を指定します（`[x, y, width, height]`）
- **デフォルト**: `[465, 530, 512, 283]` （1920x1080 の画面用）
- 画面解像度が異なる場合は調整が必要です（後述）

---

## 3. アプリケーションの起動

### 3.1 PowerShell で起動

**プロジェクトディレクトリに移動**:
```powershell
cd path\to\ow2\packages\ow2-victory-counter-rs
```

**開発ビルドで起動** （デバッグ用）:
```powershell
cargo run
```

または、**リリースビルドで起動** （本番用）:
```powershell
.\target\release\ow2-victory-detector.exe
```

**カスタム設定ファイルを指定**:
```powershell
cargo run -- --config my-config.toml
```

---

### 3.2 起動ログの確認

正常に起動すると、以下のようなログが表示されます：

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

**重要なメッセージ**:
- ✅ `OBS WebSocket connected successfully` - OBS との接続成功
- ✅ `ONNX model loaded successfully` - モデル読み込み成功
- ✅ `HTTP server listening on...` - Web サーバー起動成功

---

## 4. ブラウザーで UI を確認

### 4.1 OBS 用 UI（カウンター表示）

ブラウザーで以下の URL を開く：

```
http://127.0.0.1:3000/
```

**表示内容**:
- 勝利カウント（緑色）
- 敗北カウント（赤色）
- 最終更新時刻

---

### 4.2 管理画面 UI

ブラウザーで以下の URL を開く：

```
http://127.0.0.1:3000/admin
```

**機能**:
- 現在のカウント表示
- **+** / **-** ボタンで手動調整
- **リセット** ボタンで全カウントをゼロに

---

## 5. OBS にブラウザーソースを追加

### 5.1 ブラウザーソースの追加

1. OBS の **ソース** パネルで **+** ボタンをクリック
2. **ブラウザー** を選択
3. 以下の設定を入力：
   - **URL**: `http://127.0.0.1:3000/`
   - **幅**: `1920`
   - **高さ**: `1080`
   - ☑ **「ローカルファイル」のチェックを外す**
   - ☑ **「ソースが表示されたときにブラウザーの表示を更新する」** にチェック

4. **OK** をクリック

---

### 5.2 カウンターの配置調整

1. OBS プレビューでブラウザーソースを選択
2. 赤い枠をドラッグして、表示位置・サイズを調整
3. カウンターが見やすい位置に配置

---

## 6. 勝敗検知のテスト

### 6.1 テスト方法

1. Overwatch 2 でゲームをプレイ
2. 試合終了後、勝敗画面が表示される
3. カウンターが自動的に増加することを確認

**確認ポイント**:
- 勝利時: 緑色のカウントが +1
- 敗北時: 赤色のカウントが +1
- アプリケーションのログに `Event triggered: victory` や `Event triggered: defeat` が表示される

---

### 6.2 検知されない場合

#### 原因 1: クロップ領域が正しくない

**症状**: ログに `Detection: outcome=none` ばかり表示される

**解決策**: `crop_rect` を調整する（後述）

---

#### 原因 2: ソース名が一致していない

**症状**: `Failed to capture image` エラーが表示される

**解決策**:
1. OBS でソース名を確認
2. `config.toml` の `source_name` を一致させる
3. アプリケーションを再起動

---

#### 原因 3: 連続検知回数が多すぎる

**症状**: 勝敗画面が表示されるが、カウントが増えない

**解決策**: `config.toml` の `required_consecutive` を減らす
```toml
[state]
required_consecutive = 2  # デフォルトは 3
```

---

## 7. crop_rect の調整

勝敗判定が正しく動作しない場合、`crop_rect` の調整が必要です。

### 7.1 調整方法

1. Overwatch 2 の勝敗画面のスクリーンショットを撮る
2. 画像編集ソフト（ペイント、GIMP など）で開く
3. **「VICTORY」** または **「DEFEAT」** のテキスト領域を選択
4. 選択範囲の座標とサイズを確認：
   - **x**: 左上の X 座標
   - **y**: 左上の Y 座標
   - **width**: 幅
   - **height**: 高さ

5. `config.toml` の `crop_rect` を更新：
   ```toml
   [preprocessing]
   crop_rect = [x, y, width, height]
   ```

6. アプリケーションを再起動

---

### 7.2 デフォルト値

**1920x1080 の場合**:
```toml
crop_rect = [465, 530, 512, 283]
```

**2560x1440 の場合** （参考値、要調整）:
```toml
crop_rect = [620, 707, 683, 377]
```

---

## 8. カスタマイズ

### 8.1 CSS のカスタマイズ

`templates/custom.css` を編集して、カウンターの見た目を変更できます。

**例: 色を変更**:
```css
.counter-grid {
  --victory-color: #00ff00;  /* 勝利の色 */
  --defeat-color: #ff0000;   /* 敗北の色 */
  --font-size: 96px;         /* フォントサイズ */
}
```

**例: グロー効果を追加**:
```css
.value {
  text-shadow: 0 0 20px currentColor,
               0 0 40px currentColor,
               0 0 60px currentColor;
}
```

変更後、ブラウザーを更新（F5）すると反映されます。

---

### 8.2 OBS ブラウザーソースでカスタム CSS を適用

1. OBS でブラウザーソースを右クリック → **プロパティ**
2. **カスタム CSS** に以下を追加：
   ```css
   @import url("http://127.0.0.1:3000/custom.css");
   ```
3. **OK** をクリック

---

## 9. ログレベルの変更

詳細なログを表示したい場合、環境変数を設定します。

**PowerShell**:
```powershell
$env:RUST_LOG="debug"
cargo run
```

**コマンドプロンプト**:
```cmd
set RUST_LOG=debug
cargo run
```

**ログレベル**:
- `error`: エラーのみ
- `warn`: 警告以上
- `info`: 情報以上（デフォルト）
- `debug`: デバッグ情報
- `trace`: 最も詳細

---

## 10. トラブルシューティング

### エラー: "failed to connect to the obs-websocket plugin"

**原因**: OBS が起動していない、または WebSocket が無効

**解決策**:
1. OBS Studio を起動
2. **ツール** → **WebSocket サーバー設定** で有効化
3. ポート番号が `4455` であることを確認
4. Windows Firewall で接続がブロックされていないか確認

---

### エラー: "Failed to capture image"

**原因**: ソース名が一致していない

**解決策**:
1. OBS でソース名を確認（大文字・小文字、スペースも正確に）
2. `config.toml` の `source_name` を修正
3. アプリケーションを再起動

---

### エラー: "No such file or directory: models/victory_classifier.onnx"

**原因**: ONNX モデルファイルが存在しない

**解決策**:
1. `models/` ディレクトリを確認：
   ```powershell
   dir models
   ```
2. ファイルが存在しない場合は、[ビルド手順](./build.md#4-onnxモデルの配置確認) を参照

---

### カウントが増えすぎる

**原因**: クールダウン時間が短すぎる、または連続検知回数が少なすぎる

**解決策**: `config.toml` を調整
```toml
[state]
cooldown_seconds = 15  # クールダウンを延長
required_consecutive = 5  # 連続検知回数を増やす
```

---

### カウントが増えない

**原因 1**: クロップ領域が正しくない

**解決策**: [crop_rect の調整](#7-crop_rect-の調整) を参照

**原因 2**: 検知信頼度が低い

**解決策**: ログで `confidence` の値を確認（0.8 以上が望ましい）

---

## 11. アプリケーションの終了

### 11.1 正常終了

PowerShell で **Ctrl + C** を押すと、アプリケーションが終了します。

---

### 11.2 強制終了

応答しない場合は、タスクマネージャーで `ow2-victory-detector.exe` を終了します。

---

## 次のステップ

- [README](../../packages/ow2-victory-counter-rs/README.md) でさらに詳しい情報を確認
- [カスタマイズ方法](../../packages/ow2-victory-counter-rs/README.md#カスタマイズ) で UI をカスタマイズ
- 問題が発生した場合は、[GitHub Issues](https://github.com/your-repo/issues) で報告
