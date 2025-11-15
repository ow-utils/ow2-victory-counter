# Victory Counter アーキテクチャ概要

## コンポーネント構成

```
┌──────────────────────────────┐
│  OBS + Victory Detector（Python） │
│  ├─ victory_detector.core.*       │
│  │   ├─ StateManager（状態管理・クールダウン） │
│  │   └─ EventLog（イベント永続化）    │
│  ├─ victory_detector.inference.*   │
│  │   └─ VictoryPredictor（CNN推論）  │
│  ├─ HTTP サーバ                  │
│  │   ├─ GET /state               │
│  │   ├─ GET /history             │
│  │   ├─ POST /adjust             │
│  │   └─ GET /overlay             │
│  ├─ OBS スクリプト (obs_victory_detector.py) │
│  └─ CNN推論プロセス (run_capture_monitor_ws.py) │
│      └─ obs-websocket経由でリアルタイム判定 │
└──────────────────────────────┘
                 ↑ JSON API
                 ↓
┌──────────────────────────────┐
│ victory-counter-overlay-ui (Node/TS) │
│  ├─ 管理 UI (http://127.0.0.1:5173/) │
│  │   ├─ 勝敗表示＋手動補正フォーム       │
│  │   └─ Victory Detector API をポーリング │
│  └─ 配信用オーバーレイ (静的ビルド dist/overlay.html) │
└──────────────────────────────┘
```

- 勝敗判定のロジック・イベントログ管理は Victory Detector 側で担当し、OBS で StateManager を起動して HTTP API を提供します。
- 管理 UI は `victory-counter-overlay-ui` 側で提供され、API を通じて勝敗カウント／履歴を取得し、手動補正を送信します。
- `/overlay` は Python 側で提供する軽量な HTML で、配信画面に簡易オーバーレイを載せたい場合の最低限の機能を担います。並行して `npm run build` / `npm run package-overlay` で生成した静的ファイルを OBS のブラウザソースへ直接読み込む運用もサポートしています。

## データフロー

1. **OBS HTTP API サーバ**：OBS が `obs_victory_detector.py` を介して HTTP サーバを起動。
2. **CNN 推論プロセス**：`run_capture_monitor_ws.py` を外部プロセスとして起動し、obs-websocket 経由でスクリーンショットを取得。VictoryPredictor で CNN 推論を行い、StateManager でイベントログに記録。
3. **イベントログ共有**：OBS スクリプトと CNN 推論プロセスは同一の `logs/detections.jsonl` を参照し、状態を同期。
4. **管理 UI**：`victory-counter-overlay-ui` (`5173`) が `/state`・`/history` の API を定期ポーリングし、勝敗カウントと履歴を表示。`POST /adjust` で補正を行う。
5. **配信オーバーレイ**：`/overlay` エンドポイントは配信用。クエリでテーマやスケール、履歴数、更新間隔などを指定でき、埋め込みスクリプトが `/state` `/history` を一定間隔で再取得して画面を更新する。

## サンプルデータ保管

※以下のパスは victory-detector プロジェクト (`packages/obs-victory-counter/victory-detector/`) 内の相対パスです。

### サンプル画像とラベリング

- 画像解析用のスクリーンショットは `data/samples` 以下に保存する。サブディレクトリ名は `YYYYMMDD_runXX` とし、同名の JSON に解像度・UI 言語・アクセシビリティ設定・各サンプルのラベルを記録する。
- ラベリング手順や命名規則は `docs/plans/2025-11-03-08全体TODO.md` を参照。データ追加時は同ドキュメントの TODO／参考メモを更新する。

### CNN 学習ワークフロー（現行）

- **推奨クロップ領域**: `460,378,995,550` (x, y, width, height)。この領域は画面中央の勝敗テキストバナーと画面下部のプログレスバーの両方を含む統一領域として設定されており、`victory_text`/`defeat_text` と `victory_progress`/`defeat_progress` の両方のクラスを一度の推論で判定できる。
- `scripts/build_dataset.py` は学習用データセットを生成し、`dataset/<label>/` に配置する。画像はアスペクト比を維持したまま長辺を指定サイズ（デフォルト128px）にリサイズされる。従来の JSON ベースのサンプルに加え、`samples/<label>/*.png` という簡易なフォルダ構造にも対応し、JSON なしで手軽にデータセットを構築できる。CNN 学習用の生データ扱いのため Git では無視する。データセット構築時には `--crop 460,378,995,550` オプションで指定する。
- `scripts/train_classifier.py` を用いて軽量 CNN を訓練し、モデルを `artifacts/models/` に保存する。データセットのパスのみ指定すれば良い。学習時に label_map と idx_to_label がモデルファイル (.pth) に保存されるため、推論時は dataset ディレクトリ不要。

### レガシーツール（テンプレートマッチング PoC）

以下のツールは初期の PoC で使用したテンプレートマッチング方式のもので、現在は CNN 推論に置き換えられています。歴史的参考資料として保持しています。

- `scripts/list_overlay_components.py` - 明度しきい値で候補領域を抽出（ImageMagick 必要）
- `scripts/export_templates.py` - `template_bbox` から `data/templates/<label>/<variant>/` にテンプレート PNG を生成
- `scripts/check_templates.py` - サンプル JSON とテンプレートの整合性検証
- `scripts/poc_detect.py` - テンプレートマッチング PoC。`--report` でスコア分布を JSON 出力

## CNN モデルアーキテクチャ

- `VictoryClassifier` は可変サイズ入力に対応した軽量 CNN で、以下の特徴を持つ：
  - **3層の畳み込み層**：Conv2d + BatchNorm + ReLU + MaxPool2d の組み合わせで特徴抽出
  - **適応型プーリング**：`AdaptiveAvgPool2d(4, 4)` により、任意のサイズの入力を 4×4 の固定サイズに変換
  - **全結合層**：128チャンネル × 4 × 4 = 2048次元のベクトルを分類ラベル数の出力に変換
  - この設計により、アスペクト比や解像度の異なる入力画像でも学習・推論が可能

- ラベルクラス数はデータセットから自動検出される：
  - `dataset/` 配下のディレクトリ構造（`victory/`, `defeat/`, `none/` など）から自動認識
  - 4クラス固定ではなく、任意のクラス数に対応（5クラス、8クラスなど）
  - 学習スクリプト実行時に `VictoryDataset` が label_map を自動生成し、`num_classes` が自動設定される
  - 例：`victory_text`, `victory_progress`, `defeat_text`, `defeat_progress`, `none` の 5クラス分類に対応

## VictoryPredictor 推論モジュール

`victory_detector.inference.VictoryPredictor` は学習済みCNNモデルを使った勝敗判定を行うクラスです。

### 主な機能

- **5クラス分類から勝敗へマッピング**：
  - `victory_text` / `victory_progressbar` → `victory`
  - `defeat_text` / `defeat_progressbar` → `defeat`
  - `none` → `unknown`（検知なし）
  - ※ 過去には `draw_text` クラスが存在したが、教師データ不足による誤判定のため除外
  - `DetectionResult` には `outcome` に加えて、元の詳細クラス名を保持する `predicted_class` フィールドも含まれる（誤検知分析に活用）

- **モデルファイルに label_map を内包**：
  - `train_classifier.py` で学習時に label_map と idx_to_label をモデルファイル (.pth) に保存
  - 推論時は dataset ディレクトリ不要、モデルファイルのみで動作
  - クラス数は自動検出されるため、4クラス・5クラスなど任意のクラス数に対応

- **前処理パイプライン**：
  1. 画像クロップ（デフォルト: `460,378,995,550`）
  2. アスペクト比を維持したままリサイズ（`image_size` パラメータ指定時のみ。未指定時はオリジナルサイズを維持）
  3. BGR → RGB 変換
  4. 0-1 正規化
  5. テンソル変換とバッチ次元追加

- **デバイス自動選択**：
  - `device="auto"` で CUDA が利用可能なら GPU、なければ CPU を自動選択
  - RTX 3070 / CUDA 12.8 環境で動作確認済み

### 使用例

```python
from victory_detector.inference import VictoryPredictor

# オリジナルサイズで推論（デフォルト）
predictor = VictoryPredictor(
    model_path=Path("artifacts/models/victory_classifier.pth"),
    crop_region=(460, 378, 995, 550),
)

# 画像から推論
detection = predictor.predict(image)  # DetectionResult(outcome, confidence, predicted_class)
print(f"{detection.outcome}: {detection.confidence:.4f} ({detection.predicted_class})")

# リサイズを指定する場合
predictor_resized = VictoryPredictor(
    model_path=Path("artifacts/models/victory_classifier.pth"),
    crop_region=(460, 378, 995, 550),
    image_size=512,  # 長辺を512pxにリサイズ
)
```

## クールダウン機能

`StateManager` は重複カウント防止のため、クールダウン機能を実装しています。

### 仕様

- **デフォルト180秒のクールダウン期間**：
  - 前回の検知（`delta > 0` のイベント）から指定秒数以内の検知はカウントしない
  - クールダウン中の検知は `delta=0` でイベントログに記録されるが、カウントには反映されない
  - これにより、同一試合の繰り返し検知を防止

- **残り時間の通知**：
  - クールダウン中のイベントには `note` フィールドに残り時間を記録
  - 例: `[cooldown: 120s remaining]`

- **イベントソーシングパターン**：
  - すべての検知イベント（`delta=0` を含む）は JSONL ファイルに永続化
  - `StateManager` 起動時に過去のイベントログから最後の検知時刻を復元
  - プロセス再起動後もクールダウン状態を維持

### イベントログ例

```jsonl
{"type": "result", "value": "victory", "delta": 1, "timestamp": "2025-11-09T10:00:00Z", "confidence": 0.9998}
{"type": "result", "value": "victory", "delta": 0, "timestamp": "2025-11-09T10:01:30Z", "confidence": 0.9995, "note": "[cooldown: 90s remaining]"}
{"type": "result", "value": "defeat", "delta": 1, "timestamp": "2025-11-09T10:05:00Z", "confidence": 0.9992}
```

1行目は通常カウント、2行目はクールダウン中のため `delta=0` でカウントされず、3行目は再びカウントされています。

## 連続検知機能

`StateManager` は誤検知を削減するため、連続検知機能を実装しています。

### 仕様

- **連続N回の検知でカウント**（デフォルト3回）:
  - 同じ結果（victory/defeat）が連続で検知された場合のみカウント
  - 異なる結果が出た場合は連続カウントをリセット
  - 一時的なノイズや画面切り替え時の誤検知を防止

- **高速判定**:
  - キャプチャ間隔: 0.25秒（デフォルト）
  - 3回連続検知: 0.25秒 × 3回 = 0.75秒で確定
  - 従来のクールダウン（180秒）より大幅に高速

- **スクリーンショット保存の最適化**:
  - 連続検知の最初の1回のみスクリーンショットを保存
  - ストレージ使用量を削減

- **DetectionResponse**:
  - `event`: カウントされた場合のイベント（未確定の場合はNone）
  - `consecutive_count`: 現在の連続回数
  - `is_first_detection`: 連続検知の最初の1回か

### 動作例

```
0.00秒: victory検知 (1/3) → ログなし、スクリーンショット保存
0.25秒: victory検知 (2/3) → ログなし
0.50秒: victory検知 (3/3) → カウント確定、イベントログ記録
0.75秒: victory検知 (cooldown) → クールダウン中、カウントしない
```

```
0.00秒: victory検知 (1/3) → ログなし、スクリーンショット保存
0.25秒: defeat検知 (1/3) → リセット、スクリーンショット保存
0.50秒: defeat検知 (2/3) → ログなし
0.75秒: defeat検知 (3/3) → カウント確定
```

### パラメータ

- `required_consecutive` (デフォルト: 3): カウントに必要な連続検知回数
- `interval` (デフォルト: 0.25秒): キャプチャ間隔

## 検知時スクリーンショット保存（誤検知分析）

`run_capture_monitor_ws.py` は `--save-detections` オプションにより、検知時のスクリーンショットを自動保存できます。

### 機能

- **保存対象**：victory/defeat を検知した場合のみ保存（unknown は保存しない）
- **保存タイミング**：カウントされた検知（`delta > 0`）とクールダウン中の検知（`delta = 0`）の両方を保存
- **ファイル名形式**：`{timestamp}-{predicted_class}-{status}.png`
  - `timestamp`: `YYYYMMDD-HHMMSS-mmm` 形式（ミリ秒まで）
  - `predicted_class`: 詳細クラス名（`victory_text`, `victory_progressbar`, `defeat_text`, `defeat_progressbar` など）
  - `status`: `counted`（カウント済み）または `cooldown`（クールダウン中）

### 使用例

```bash
python scripts/run_capture_monitor_ws.py \
  --source "ゲームキャプチャ" \
  --model artifacts/models/victory_classifier.pth \
  --save-detections data/detections/session01
```

保存されたスクリーンショットは誤検知分析に活用し、誤検知パターンを学習データに追加することでモデルを継続的に改善できます。

## 今後の方針

- 配信オーバーレイは Python `/overlay` と静的ビルドの二本立てを維持しつつ、React コンポーネントの共有やビルド成果物の配布フローを整備する。
- CI パイプラインで Python/Node のテストを統合し、配信前の品質を担保する。
- モデル精度の継続的改善：新しいサンプルデータの追加、データ拡張（Data Augmentation）の検討、モデルアーキテクチャの最適化。
- 推論信頼度の閾値調整：実運用でのログ分析に基づいて、`unknown` 判定への切り替え閾値を最適化する。
