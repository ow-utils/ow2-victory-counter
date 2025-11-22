# ow2-victory-counter-rs アーキテクチャ設計

## 概要

Overwatch 2 の勝敗判定を自動で行い、カウントを配信画面にオーバーレイ表示するシステムの Rust での正式実装版。Python PoC から正式版への移行として、性能向上、配布の簡便さ、カスタマイズ性を重視した設計。

### 主要な設計方針

- **単一バイナリ配布**: エンドユーザーは Python 環境不要
- **段階的カスタマイズ**: CSS 編集から完全な独自 UI 実装まで対応
- **リッチな UI**: PoC より視覚的に洗練されたアニメーション効果
- **ステートレスサーバー**: 永続化はブラウザー側（管理画面）で管理

## システムアーキテクチャ

### 全体構成

```
┌─────────────────────────────────────────────────────────────┐
│ OBS Studio                                                  │
│  ┌──────────────────┐          ┌────────────────────────┐  │
│  │ ゲーム画面       │          │ ブラウザーソース       │  │
│  │ (Overwatch 2)    │          │ http://localhost:3000/ │  │
│  └──────────────────┘          └────────────────────────┘  │
│         │                                │                  │
│         │ (obs-websocket)                │ (SSE)            │
└─────────┼────────────────────────────────┼──────────────────┘
          │                                │
          ▼                                ▼
┌─────────────────────────────────────────────────────────────┐
│ ow2-victory-detector (Rust)                                 │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ HTTP サーバー (axum)                                 │  │
│  │  ├─ GET  /              (OBS用UI: 読み取り専用)     │  │
│  │  ├─ GET  /admin         (管理画面UI)                │  │
│  │  ├─ GET  /custom.css    (カスタムCSS)               │  │
│  │  ├─ GET  /events        (SSE: リアルタイム通知)     │  │
│  │  ├─ GET  /api/status    (REST: 状態取得)            │  │
│  │  ├─ POST /api/initialize (初期化)                   │  │
│  │  └─ POST /api/adjust     (手動調整)                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                        │                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 画像取得・前処理                                     │  │
│  │  ├─ OBS WebSocket クライアント (obws)               │  │
│  │  ├─ Base64 デコード                                  │  │
│  │  ├─ PNG デコード (opencv-rust)                       │  │
│  │  └─ 画像クロップ・リサイズ                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                        │                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ CNN 推論 (ONNX Runtime)                              │  │
│  │  ├─ ONNX モデル読み込み                              │  │
│  │  ├─ 画像テンソル化                                   │  │
│  │  ├─ 推論実行                                         │  │
│  │  └─ 勝敗判定 (victory/defeat/draw/none)             │  │
│  └──────────────────────────────────────────────────────┘  │
│                        │                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ StateManager                                         │  │
│  │  ├─ 連続検知判定 (required_consecutive)             │  │
│  │  ├─ 2段階クールダウン制御                           │  │
│  │  └─ tokio::sync::broadcast (SSE配信)                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 管理画面 (通常のブラウザー)                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ http://localhost:3000/admin                          │  │
│  │  ├─ カウンター表示                                   │  │
│  │  ├─ 調整ボタン (+/-)                                 │  │
│  │  ├─ 初期化ボタン                                     │  │
│  │  └─ localStorage (永続化)                            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### UI の役割分担

#### OBS 用 UI (GET /)

- **用途**: 配信画面へのオーバーレイ表示
- **機能**: カウンター表示のみ（読み取り専用）
- **永続化**: なし（SSE 受信時に UI 更新のみ）
- **カスタマイズ**: custom.css、ui-config.json

#### 管理画面 (GET /admin)

- **用途**: 勝敗数の管理・調整
- **機能**:
  - カウンター表示
  - 手動調整（+/- ボタン）
  - 初期化（リセットボタン）
- **永続化**: localStorage で勝敗数を保存
- **起動時**: localStorage から読み込み → POST /api/initialize

## コンポーネント詳細

### 1. 画像取得・前処理モジュール

**責務**: OBS から画像を取得し、CNN 推論用に前処理

**技術スタック**:

- `obws`: OBS WebSocket クライアント
- `opencv-rust`: 画像処理
- `base64`: Base64 デコード

**処理概要**:

1. OBS WebSocket 経由でスクリーンショット取得（0.25 秒間隔）
2. Base64 デコード
3. PNG デコード
4. クロップ (460, 378, 995, 550)
5. リサイズ（オプション）
6. マスク適用（オプション）
7. CNN 推論モジュールへ渡す

### 2. CNN 推論モジュール (ONNX Runtime)

**責務**: 画像から勝敗を判定

**技術スタック**:

- `ort`: ONNX Runtime の Rust バインディング
- `ndarray`: テンソル操作

**モデル仕様**:

- 入力: `(1, 3, 550, 995)` または リサイズ後のサイズ
- 出力: `(1, num_classes)` - クラスごとの確率
- クラス: `victory`, `defeat`, `draw`, `none`, その他

**処理概要**:

1. 画像をテンソルに変換 (HWC → CHW, BGR → RGB, 正規化)
2. ONNX Runtime 推論
3. 出力から最大確率のクラスを取得
4. クラス ID をラベルに変換
5. Detection 構造体を返す

### 3. StateManager

**責務**: 検知の連続性判定、クールダウン管理、SSE 配信

**状態遷移**:

```
READY
  │
  │ 勝敗検知 × required_consecutive回
  ▼
COOLDOWN (180秒)
  │
  │ 180秒経過 + 勝敗検知
  ▼
WAITING_FOR_NONE
  │
  │ none検知
  ▼
READY
```

**主要機能**:

- 連続検知判定（required_consecutive 回連続で検知したらカウント）
- 2 段階クールダウン制御（誤カウント防止）
- tokio::sync::broadcast でイベント配信（SSE へ）

### 4. HTTP サーバー (axum)

**責務**: REST API と SSE エンドポイント提供、UI 配信

**エンドポイント**:

- GET /: OBS 用 UI 配信
- GET /admin: 管理画面 UI 配信
- GET /custom.css: カスタム CSS 配信
- GET /events: SSE ストリーム
- GET /api/status: 現在の状態取得
- POST /api/initialize: 勝敗数初期化
- POST /api/adjust: 勝敗数調整

**UI 配信方式**:

- Svelte でビルドした HTML/JS/CSS をバイナリーに組み込み
- `include_str!` マクロで埋め込み

### 5. フロントエンド

#### OBS 用 UI (Svelte)

**責務**: カウンター表示、アニメーション

**主要機能**:

- SSE で勝敗数受信
- tweened ストアでカウントアップアニメーション
- ui-config.json に基づいてコンポーネント表示制御

#### 管理画面 UI (Svelte)

**責務**: カウンター管理、永続化

**主要機能**:

- SSE で勝敗数受信
- localStorage で永続化
- 調整ボタン（POST /api/adjust）
- 初期化ボタン（POST /api/initialize）

## エンドポイント仕様

### GET /

OBS 用カウンター表示 UI を提供。

**レスポンス**:

- Content-Type: `text/html`
- Body: HTML ファイル（Svelte コンパイル済み、バイナリー組み込み）

### GET /admin

管理画面 UI を提供。

**レスポンス**:

- Content-Type: `text/html`
- Body: HTML ファイル（Svelte コンパイル済み、バイナリー組み込み）

### GET /custom.css

カスタマイズ用 CSS を提供。

**レスポンス**:

- Content-Type: `text/css`
- Body: CSS ファイル

**動作**:

1. `templates/custom.css` が存在すればそれを返す
2. なければ空の CSS を返す

### GET /events

SSE でリアルタイム通知。

**レスポンス**:

- Content-Type: `text/event-stream`
- イベント名: `counter-update`
- データ形式: JSON

**イベントデータ**:

```json
{
  "victories": 5,
  "defeats": 3,
  "draws": 1,
  "last_outcome": "victory",
  "timestamp": 1234567890.123
}
```

**Keep-Alive**: 15 秒間隔

### GET /api/status

現在の勝敗数を取得（REST API）。

**レスポンス**:

```json
{
  "victories": 5,
  "defeats": 3,
  "draws": 1,
  "status": "ready"
}
```

**用途**:

- デバッグ: `curl http://localhost:3000/api/status`
- 独自 UI 実装時の初期値取得
- 他ツール連携

### POST /api/initialize

勝敗数を初期化。

**リクエスト**:

```json
{
  "victories": 5,
  "defeats": 3,
  "draws": 1
}
```

**レスポンス**:

```json
{
  "victories": 5,
  "defeats": 3,
  "draws": 1,
  "status": "ready"
}
```

**用途**: 管理画面起動時に localStorage から復元したデータをサーバーに送信

### POST /api/adjust

勝敗数を手動調整。

**リクエスト**:

```json
{
  "outcome": "victory",
  "delta": 1
}
```

- `outcome`: `"victory"`, `"defeat"`, `"draw"`
- `delta`: 増減量（正負の整数）

**レスポンス**:

```json
{
  "victories": 6,
  "defeats": 3,
  "draws": 1,
  "status": "ready"
}
```

**用途**: 誤カウント修正、手動カウント調整

## データフロー

### 管理画面起動時

```
1. ブラウザー（管理画面）起動
   ↓
2. localStorage から counter_state 読み込み
   ↓
3. POST /api/initialize（サーバーに状態復元）
   ↓
4. GET /events（SSE接続開始）
   ↓
5. 初回イベント受信（現在の状態）
   ↓
6. UI更新
```

### OBS UI 起動時

```
1. ブラウザー（OBS）起動
   ↓
2. GET /events（SSE接続開始）
   ↓
3. 初回イベント受信（現在の状態）
   ↓
4. UI更新
```

### 勝敗判定時

```
1. OBS から画像取得（0.25秒間隔）
   ↓
2. CNN推論 → 勝敗判定
   ↓
3. StateManager.record_detection()
   ↓
4. 連続検知判定（required_consecutive回）
   ↓
5. カウント確定
   ↓
6. tokio::sync::broadcast でイベント配信
   ↓
7. SSE経由で全接続クライアントに通知
   ↓
8. 管理画面: UI更新 + localStorage保存
   OBS UI: UI更新のみ
```

### 手動調整時

```
1. 管理画面で調整ボタンクリック
   ↓
2. POST /api/adjust
   ↓
3. StateManager.adjust()
   ↓
4. カウント増減
   ↓
5. tokio::sync::broadcast でイベント配信
   ↓
6. SSE経由で全接続クライアントに通知
   ↓
7. 管理画面: UI更新 + localStorage保存
   OBS UI: UI更新のみ
```

## 永続化戦略

### サーバー側（Rust）

- **現在の状態**: メモリ内のみ（再起動で失われる）
- **設計思想**: ステートレス

### ブラウザー側（管理画面）

- **localStorage**: `counter_state` キーで状態を保存
- **形式**:
  ```json
  {
    "victories": 5,
    "defeats": 3,
    "draws": 1
  }
  ```
- **タイミング**: SSE でイベント受信時に毎回保存
- **容量**: 約 50 バイト（5-10MB 制限内で十分）

### 復元フロー

```
1. サーバー起動
   ↓
   StateManager は初期状態（0,0,0）

2. 管理画面起動
   ↓
   localStorage から前回の状態を読み込み
   ↓
   POST /api/initialize で状態をサーバーに送信
   ↓
   サーバー側 StateManager を復元
```

**メリット**:

- サーバー再起動の影響を最小化
- 管理画面ごとに異なるカウンターを持てる
- サーバー側の実装がシンプル

## カスタマイズ方法

### レベル 0: デフォルト

何もしない。バイナリー単体で動作。

### レベル 1: CSS 編集

`templates/custom.css` を作成して配置:

```css
/* 色を変更 */
.counter-grid {
  --victory-color: #00ff00;
  --defeat-color: #ff0000;
  --font-size: 96px;
}

/* 背景を追加 */
body {
  background: linear-gradient(45deg, #000, #333);
}

/* グロー効果 */
.value {
  text-shadow: 0 0 20px currentColor;
  animation: glow 2s infinite;
}

@keyframes glow {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}
```

**必要スキル**: CSS

### レベル 2: 設定ファイル編集

`config/ui-config.json` を編集:

```json
{
  "components": {
    "victory": true,
    "defeat": true,
    "draw": false
  },
  "layout": {
    "orientation": "horizontal",
    "fontSize": 96,
    "gap": 40
  }
}
```

**必要スキル**: JSON 編集

### レベル 3: 独自 UI 実装

`/events` API を使って完全に独自の UI を実装:

```html
<!DOCTYPE html>
<html>
  <head>
    <title>My Custom Counter</title>
  </head>
  <body>
    <h1>Victories: <span id="victories">0</span></h1>

    <script>
      const eventSource = new EventSource("http://localhost:3000/events");
      eventSource.addEventListener("counter-update", (e) => {
        const data = JSON.parse(e.data);
        document.getElementById("victories").textContent = data.victories;
      });
    </script>
  </body>
</html>
```

**必要スキル**: HTML, JavaScript, CSS
**環境**: 独自の Web サーバーを立てる

## 技術選定理由

### OBS プラグイン vs obs-websocket

**決定**: obs-websocket 採用

**理由**:

- 実証済みの安定性（PoC で確認済み）
- 開発コスト削減（3-4 週間短縮）
- OBS プロセスから独立して動作（クラッシュリスク回避）
- Base64 オーバーヘッドは許容範囲（1-2ms、全体の 5-10%）

### PyTorch .pth vs ONNX vs Rust ネイティブ

**決定**: ONNX 採用

**理由**:

- 開発コスト最小（1-2 日 vs 4-6 日 vs 9-14 日）
- 学習環境は引き続き PyTorch（成熟したエコシステム）
- ONNX Runtime は高性能で安定
- モデル構造変更時も再変換のみで対応

### WebSocket vs SSE vs ポーリング

**決定**: SSE 採用

**理由**:

- 単方向通信で十分（サーバー→ブラウザー）
- 自動再接続機能
- WebSocket より軽量でシンプル
- OBS ブラウザーソース（Chromium）で完全サポート
- axum で標準サポート

### Vue vs Svelte vs バニラ JS

**決定**: Svelte 採用

**理由**:

- リッチなアニメーション実装が容易（tweened, transition）
- コンパイル後は軽量（15KB、gzip 後 5KB）
- ランタイムなし、純粋な JavaScript
- バニラ JS ではアニメーション実装が手間
- Vue は CDN 依存またはサイズ大（300KB）

### localStorage vs IndexedDB

**決定**: localStorage 採用

**理由**:

- データサイズが非常に小さい（約 50 バイト）
- 実装がシンプル（3 行で完結）
- パフォーマンスが十分（同期 API でも問題なし）
- IndexedDB は過剰スペック

## パフォーマンス特性

### 処理時間内訳（推定）

| 処理            | 時間        | 備考                        |
| --------------- | ----------- | --------------------------- |
| Base64 デコード | 0.5-1ms     | Rust 実装                   |
| PNG デコード    | 10-20ms     | OpenCV（C++ライブラリ）     |
| 画像前処理      | 1-2ms       | クロップ、リサイズ          |
| CNN 推論        | 5-15ms      | ONNX Runtime（CPU/GPU）     |
| StateManager    | 0.1-0.3ms   | Rust 実装                   |
| SSE 配信        | 0.5-1ms     | tokio broadcast             |
| **合計**        | **17-39ms** | **0.25 秒間隔なので 7-16%** |

### Rust 化による改善（Python PoC 比）

| コンポーネント  | Python        | Rust          | 改善             |
| --------------- | ------------- | ------------- | ---------------- |
| Base64 デコード | 1-2ms         | 0.5-1ms       | 50%削減          |
| PNG デコード    | 10-20ms       | 10-20ms       | 同等             |
| StateManager    | 1-2ms         | 0.1-0.3ms     | 80-90%削減       |
| HTTP サーバー   | 5-10ms        | 0.5-1ms       | 90%削減          |
| メモリ使用量    | 200-300MB     | 50-100MB      | 60-75%削減       |
| 起動時間        | 2-5秒         | 0.1-0.5秒     | 90%削減          |
| **全体**        | **平均 30ms** | **平均 26ms** | **13-15%高速化** |

## 配布構成

### エンドユーザー向け配布物

```
ow2-victory-counter-rs/          # 配布物ルート（任意のディレクトリー名）
├── ow2-victory-detector.exe     # 単一バイナリ（UI組み込み済み）
├── models/
│   ├── victory_classifier.onnx
│   └── victory_classifier.label_map.json
├── config/
│   └── ui-config.json           # UI設定（表示/非表示、レイアウト等）
├── templates/
│   └── custom.css               # カスタムCSS（サンプル）
└── README.md
```

**配布形式**: ZIP アーカイブ

**必要環境**: Windows 10/11（Rust バイナリー）

**起動方法**:

1. ZIP を解凍
2. `ow2-victory-detector.exe` を実行
3. ブラウザーで `http://localhost:3000/admin` を開く（管理画面）
4. OBS で `http://localhost:3000/` をブラウザーソースとして追加

## セキュリティ考慮事項

### ローカルホスト限定

- バインドアドレス: `127.0.0.1:3000`（外部からアクセス不可）
- HTTPS 不要（ローカル通信のみ）
- CORS 不要（同一オリジン）

### ファイルアクセス

- 読み取り専用: `templates/`, `models/`, `config/`
- パストラバーサル対策

### API 認証

- 現時点では未実装（ローカルホスト限定のため）
- 将来的に外部公開する場合は API キーまたは JWT 検討

## 今後の拡張性

### 短期（1-2 ヶ月）

- Svelte UI の完成度向上（エフェクト追加）
- カスタマイズドキュメント整備
- エラーハンドリング強化

### 中期（3-6 ヶ月）

- 学習スクリプトの整理・リファクタリング
- データセット構築の Rust 化（オプション）
- パフォーマンス最適化（JPEG 形式、解像度削減）

### 長期（1 年以上）

- burn v1.0 リリース後に学習の Rust 化を再検討
- OBS プラグイン実装（レイテンシー改善が必要な場合）
- 他ゲームへの対応

## 参考資料

- [ONNX Runtime](https://onnxruntime.ai/)
- [axum](https://github.com/tokio-rs/axum)
- [Svelte](https://svelte.dev/)
- [obs-websocket](https://github.com/obsproject/obs-websocket)
- [burn](https://github.com/tracel-ai/burn)
