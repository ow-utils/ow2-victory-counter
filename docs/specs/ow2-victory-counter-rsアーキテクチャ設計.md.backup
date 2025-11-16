# ow2-victory-counter-rs アーキテクチャ設計

## 概要

Overwatch 2 の勝敗判定を自動で行い、カウントを配信画面にオーバーレイ表示するシステムの Rustでの正式実装版。Python PoC から正式版への移行として、性能向上、配布の簡便さ、カスタマイズ性を重視した設計。

### 主要な設計方針

- **単一バイナリ配布**: エンドユーザーは Python 環境不要
- **段階的カスタマイズ**: CSS 編集から完全な独自 UI 実装まで対応
- **リッチな UI**: PoC より視覚的に洗練されたアニメーション効果
- **ステートレスサーバー**: 永続化はブラウザー側で管理

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
│ Victory Detector (Rust)                                     │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ HTTP サーバー (axum)                                 │  │
│  │  ├─ GET  /              (標準UI: Svelte)            │  │
│  │  ├─ GET  /custom.css    (カスタマイズ用CSS)         │  │
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
│  │  ├─ イベントログ保存 (JSONL)                        │  │
│  │  └─ tokio::sync::broadcast (SSE配信)                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ イベントログ │
                  │ (JSONL)      │
                  └──────────────┘
```

### ブラウザー側（フロントエンド）

```
┌─────────────────────────────────────────────────────────────┐
│ ブラウザー (OBS ブラウザーソース: Chromium)                 │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ UI (Svelte)                                          │  │
│  │  ├─ カウンター表示 (Victory/Defeat/Draw)            │  │
│  │  ├─ カウントアップアニメーション (tweened)          │  │
│  │  ├─ 勝利時エフェクト (transition)                    │  │
│  │  └─ CSS変数によるカスタマイズ対応                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                        │                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ EventSource API (SSE クライアント)                   │  │
│  │  ├─ /events に接続                                   │  │
│  │  ├─ counter-update イベント受信                      │  │
│  │  └─ 自動再接続                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                        │                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ localStorage                                         │  │
│  │  ├─ counter_state 保存                               │  │
│  │  └─ 起動時に /api/initialize へ送信                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## コンポーネント詳細

### 1. 画像取得・前処理モジュール

**責務**: OBS から画像を取得し、CNN 推論用に前処理

**技術スタック**:

- `obws`: OBS WebSocket クライアント
- `opencv-rust`: 画像処理
- `base64`: Base64 デコード

**処理フロー**:

```rust
// 0.25秒間隔でキャプチャ
loop {
    // 1. OBS WebSocket経由でスクリーンショット取得
    let response = obs_client.get_source_screenshot(
        source_name,
        "png",
        1920,
        1080
    ).await?;

    // 2. Base64デコード
    let png_bytes = base64::decode(response.image_data)?;

    // 3. PNGデコード
    let image = opencv::imdecode(&png_bytes, opencv::IMREAD_COLOR)?;

    // 4. クロップ (460, 378, 995, 550)
    let cropped = image.roi(Rect::new(460, 378, 995 - 460, 550 - 378))?;

    // 5. リサイズ（オプション）
    let resized = if let Some(size) = image_size {
        opencv::resize(&cropped, size, INTER_LINEAR)?
    } else {
        cropped
    };

    // 6. マスク適用（オプション）
    let masked = apply_mask(resized, mask_regions)?;

    // 7. CNN推論へ
    let detection = predictor.predict(masked).await?;

    tokio::time::sleep(Duration::from_secs_f32(0.25)).await;
}
```

### 2. CNN 推論モジュール (ONNX Runtime)

**責務**: 画像から勝敗を判定

**技術スタック**:

- `ort`: ONNX Runtime の Rust バインディング
- `ndarray`: テンソル操作

**モデル**:

- 入力: `(1, 3, 550, 995)` または リサイズ後のサイズ
- 出力: `(1, num_classes)` - クラスごとの確率
- クラス: `victory`, `defeat`, `draw`, `none`, その他

**処理フロー**:

```rust
pub struct VictoryPredictor {
    session: Session,
    label_map: HashMap<usize, String>,
}

impl VictoryPredictor {
    pub fn predict(&self, image: Mat) -> Result<Detection> {
        // 1. 画像をテンソルに変換 (HWC → CHW, BGR → RGB, 正規化)
        let tensor = self.image_to_tensor(image)?;

        // 2. ONNX Runtime推論
        let outputs = self.session.run(vec![tensor])?;

        // 3. 出力から最大確率のクラスを取得
        let probs = outputs[0].extract_tensor::<f32>()?;
        let (class_idx, confidence) = probs
            .iter()
            .enumerate()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap())
            .unwrap();

        // 4. クラスIDをラベルに変換
        let predicted_class = self.label_map.get(&class_idx)?;
        let outcome = self.class_to_outcome(predicted_class);

        Ok(Detection {
            outcome,
            confidence: *confidence,
            predicted_class: predicted_class.clone(),
        })
    }
}
```

### 3. StateManager

**責務**: 検知の連続性判定、クールダウン管理、イベント記録

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

**実装**:

```rust
pub struct StateManager {
    event_log: EventLog,
    state: State,
    cooldown_seconds: u64,
    required_consecutive: usize,
    consecutive_detections: Vec<Detection>,
    last_event_time: Option<Instant>,
    broadcast_tx: broadcast::Sender<CounterUpdate>,
}

impl StateManager {
    pub fn record_detection(&mut self, detection: Detection) -> RecordResponse {
        match self.state {
            State::Ready => {
                if detection.outcome != "none" {
                    self.consecutive_detections.push(detection);

                    if self.consecutive_detections.len() >= self.required_consecutive {
                        // カウント確定
                        self.increment_counter(detection.outcome);
                        self.state = State::Cooldown;
                        self.last_event_time = Some(Instant::now());
                        self.consecutive_detections.clear();

                        // SSE配信
                        let update = self.create_counter_update();
                        let _ = self.broadcast_tx.send(update);

                        return RecordResponse::new_event(/* ... */);
                    }
                } else {
                    self.consecutive_detections.clear();
                }
            }
            State::Cooldown => {
                if self.last_event_time.unwrap().elapsed().as_secs() >= self.cooldown_seconds {
                    if detection.outcome != "none" {
                        self.state = State::WaitingForNone;
                    }
                }
            }
            State::WaitingForNone => {
                if detection.outcome == "none" {
                    self.state = State::Ready;
                }
            }
        }

        RecordResponse::no_event()
    }
}
```

### 4. HTTP サーバー (axum)

**責務**: REST API と SSE エンドポイント提供

**エンドポイント実装**:

```rust
use axum::{
    Router,
    routing::{get, post},
    response::{Html, sse::{Event, Sse}},
    extract::State,
    Json,
};

async fn serve_ui() -> Html<String> {
    // 外部ファイル優先、なければバイナリー組み込み
    if let Ok(html) = tokio::fs::read_to_string("templates/counter.html").await {
        return Html(html);
    }
    Html(include_str!("../dist/index.html").to_string())
}

async fn sse_handler(
    State(state): State<AppState>,
) -> Sse<impl Stream<Item = Result<Event, Infallible>>> {
    let rx = state.subscribe();

    let stream = BroadcastStream::new(rx).map(|result| {
        result.map(|update| {
            Event::default()
                .event("counter-update")
                .json_data(update)
                .unwrap()
        })
    });

    Sse::new(stream).keep_alive(Duration::from_secs(15))
}

async fn get_status(State(state): State<AppState>) -> Json<StatusResponse> {
    let summary = state.state_manager.summary();
    Json(StatusResponse {
        victories: summary.victories,
        defeats: summary.defeats,
        draws: summary.draws,
        status: state.state_manager.status().to_string(),
    })
}

async fn initialize(
    State(state): State<AppState>,
    Json(data): Json<InitializeRequest>,
) -> Json<StatusResponse> {
    state.state_manager.initialize(data.victories, data.defeats, data.draws);
    get_status(State(state)).await
}

async fn adjust(
    State(state): State<AppState>,
    Json(data): Json<AdjustRequest>,
) -> Json<StatusResponse> {
    state.state_manager.adjust(data.outcome, data.delta);
    get_status(State(state)).await
}

fn app() -> Router {
    Router::new()
        .route("/", get(serve_ui))
        .route("/custom.css", get(serve_custom_css))
        .route("/events", get(sse_handler))
        .route("/api/status", get(get_status))
        .route("/api/initialize", post(initialize))
        .route("/api/adjust", post(adjust))
        .with_state(app_state)
}
```

### 5. フロントエンド (Svelte)

**責務**: カウンター表示、アニメーション、永続化

**実装**:

```svelte
<script>
  import { tweened } from 'svelte/motion';
  import { cubicOut } from 'svelte/easing';
  import { onMount } from 'svelte';

  let victories = tweened(0, { duration: 1000, easing: cubicOut });
  let defeats = tweened(0, { duration: 1000, easing: cubicOut });
  let draws = tweened(0, { duration: 1000, easing: cubicOut });

  onMount(async () => {
    // localStorage から復元
    const saved = localStorage.getItem('counter_state');
    if (saved) {
      const data = JSON.parse(saved);
      victories.set(data.victories, { duration: 0 });
      defeats.set(data.defeats, { duration: 0 });
      draws.set(data.draws, { duration: 0 });

      // サーバーに初期化
      await fetch('/api/initialize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
    }

    // SSE接続
    const eventSource = new EventSource('/events');
    eventSource.addEventListener('counter-update', (e) => {
      const data = JSON.parse(e.data);
      victories.set(data.victories);
      defeats.set(data.defeats);
      draws.set(data.draws);
      localStorage.setItem('counter_state', JSON.stringify(data));
    });
  });
</script>

<div class="counter-grid">
  <div class="victory">
    <div class="label">Victory</div>
    <div class="value">{Math.floor($victories)}</div>
  </div>
  <div class="defeat">
    <div class="label">Defeat</div>
    <div class="value">{Math.floor($defeats)}</div>
  </div>
  <div class="draw">
    <div class="label">Draw</div>
    <div class="value">{Math.floor($draws)}</div>
  </div>
</div>

<style>
  .counter-grid {
    --victory-color: #4caf50;
    --defeat-color: #f44336;
    --draw-color: #ff9800;
    --font-size: 64px;
    --gap: 20px;

    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--gap);
    padding: 40px;
    font-family: Arial, sans-serif;
  }

  .victory { color: var(--victory-color); }
  .defeat { color: var(--defeat-color); }
  .draw { color: var(--draw-color); }

  .label {
    font-size: calc(var(--font-size) * 0.5);
    opacity: 0.8;
  }

  .value {
    font-size: var(--font-size);
    font-weight: bold;
    text-shadow: 3px 3px 6px rgba(0, 0, 0, 0.9);
  }
</style>
```

## エンドポイント仕様

### GET /

標準 UI（Svelte）を提供。

**レスポンス**:

- Content-Type: `text/html`
- Body: HTML ファイル（Svelte コンパイル済み）

**動作**:

1. `templates/counter.html` が存在すればそれを返す（カスタマイズ版）
2. なければバイナリー組み込みの標準 UI を返す

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

**用途**: ブラウザー起動時に localStorage から復元したデータをサーバーに送信

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

### 起動時

```
1. ブラウザー起動
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
8. ブラウザーでイベント受信
   ↓
9. Svelte tweened でアニメーション
   ↓
10. localStorage に保存
```

### 手動調整時

```
1. 外部ツール（例: curl）から POST /api/adjust
   ↓
2. StateManager.adjust()
   ↓
3. カウント増減
   ↓
4. tokio::sync::broadcast でイベント配信
   ↓
5. SSE経由で全接続クライアントに通知
   ↓
6. ブラウザーでUI更新 + localStorage保存
```

## 永続化戦略

### サーバー側（Rust）

- **イベントログ**: JSONL 形式で全イベントを記録
- **現在の状態**: メモリ内のみ（再起動で失われる）
- **設計思想**: ステートレス、イベントソーシング

### ブラウザー側

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

### 復元フロー

```
1. サーバー起動
   ↓
   StateManager は初期状態（0,0,0）

2. ブラウザー起動
   ↓
   localStorage から前回の状態を読み込み
   ↓
   POST /api/initialize で状態をサーバーに送信
   ↓
   サーバー側 StateManager を復元
```

**メリット**:

- サーバー再起動の影響を最小化
- ブラウザーごとに異なるカウンターを持てる
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

### レベル 2: 独自 UI 実装

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

### レベル 3: Svelte ソース編集

`src-templates/Counter.svelte` を編集して再ビルド:

```bash
cd src-templates
npm install
npm run dev    # 開発モード
npm run build  # ビルド（templates/counter.html に出力）
```

**必要スキル**: Svelte, Node.js, JavaScript

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

### 最小構成（デフォルト）

```
packages/ow2-victory-detector-rs/
└── ow2-victory-detector.exe    # 単一バイナリ（標準UI組み込み）
```

### 完全構成

```
packages/ow2-victory-detector-rs/
├── ow2-victory-detector.exe              # Rustバイナリ
├── models/
│   ├── victory_classifier.onnx       # ONNXモデル
│   └── victory_classifier.label_map.json
├── templates/                        # カスタマイズ用（オプション）
│   ├── counter.html                  # 完全カスタマイズ版UI
│   └── custom.css                    # CSS変数上書き
├── src-templates/                    # Svelteソース（開発者向け）
│   ├── Counter.svelte
│   ├── package.json
│   └── README.md
├── logs/                             # 実行時生成
│   └── detections.jsonl
└── README.md
```

## セキュリティ考慮事項

### ローカルホスト限定

- バインドアドレス: `127.0.0.1:3000`（外部からアクセス不可）
- HTTPS 不要（ローカル通信のみ）
- CORS 不要（同一オリジン）

### ファイルアクセス

- 読み取り専用: `templates/`, `models/`
- 書き込み: `logs/` のみ
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
