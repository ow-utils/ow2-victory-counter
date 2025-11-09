# Victory Counter アーキテクチャ概要

## コンポーネント構成

```
┌──────────────────────────────┐
│  OBS + Victory Detector（Python） │
│  ├─ victory_detector.core.*       │
│  ├─ HTTP サーバ                  │
│  │   ├─ GET /state               │
│  │   ├─ GET /history             │
│  │   ├─ POST /adjust             │
│  │   └─ GET /overlay             │
│  └─ OBS スクリプト (obs_victory_detector.py) │
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

1. OBS が `obs_victory_detector.py` を介して HTTP サーバを起動。
2. 管理 UI (`5173`) が `/state`・`/history` の API を定期ポーリングし、勝敗カウントと履歴を表示。`POST /adjust` で補正を行う。
3. `/overlay` エンドポイントは配信用。クエリでテーマやスケール、履歴数、更新間隔などを指定でき、埋め込みスクリプトが `/state` `/history` を一定間隔で再取得して画面を更新する。

## サンプルデータ保管

- 画像解析 PoC 用のスクリーンショットは `/data/samples` 以下に保存する。サブディレクトリ名は `YYYYMMDD_runXX` とし、同名の JSON に解像度・UI 言語・アクセシビリティ設定・各サンプルのラベルを記録する。
- 例: `data/samples/20251103_run01/20251103_run01.json` には draw バナーの PNG とメタデータを格納している。
- ラベリング手順や命名規則は `docs/plans/2025-11-03-08全体TODO.md` を参照。データ追加時は同ドキュメントの TODO／参考メモを更新し、必要に応じてテンプレート座標（`template_bbox`）などのメタ情報を追記する。
- 明度しきい値を使って候補領域を抽出する補助ツールとして `scripts/list_overlay_components.py` を用意している。ImageMagick が必要で、テンプレート矩形を決める際のヒントにする。
- `scripts/export_templates.py` を実行すると、`template_bbox` を基に `data/templates/<label>/<variant>/` に切り出されたテンプレート PNG が生成される。`variant` にはサンプルの `accessibility`・`mode` を小文字スラッグ化したものを連結して保存する（例: `umiinu_competitive`）。PoC やテンプレートマッチング実装ではここを参照する。
- `scripts/check_templates.py` はサンプル JSON とテンプレートを突き合わせ、variant ごとに PNG が揃っているかを検証する。CI で実行することでテンプレート不足を早期検知できる。
- `scripts/build_dataset.py` は学習用データセットを生成し、`dataset/<label>/` に配置する。画像はアスペクト比を維持したまま長辺を指定サイズ（デフォルト128px）にリサイズされる。従来の JSON ベースのサンプルに加え、`samples/<label>/*.png` という簡易なフォルダ構造にも対応し、JSON なしで手軽にデータセットを構築できる。CNN 学習用の生データ扱いのため Git では無視する。
- **推奨クロップ領域**: `460,378,995,550` (x, y, width, height)。この領域は画面中央の勝敗テキストバナーと画面下部のプログレスバーの両方を含む統一領域として設定されており、`victory_text`/`defeat_text` と `victory_progress`/`defeat_progress` の両方のクラスを一度の推論で判定できる。データセット構築時には `--crop 460,378,995,550` オプションで指定する。
- `scripts/train_classifier.py` を用いて軽量 CNN を訓練し、モデルを `artifacts/models/` に保存する。データセットのパスのみ指定すれば良く、variant パラメータは不要。推論は `run_capture_monitor_ws.py` などから呼び出す予定。
- `scripts/poc_detect.py --report` によりスコア分布を JSON 出力できる。現状の最小スコアは 0.99999976 であり、実運用の推奨閾値は 0.90、警戒ライン（unknown 判定への切り替え）は 0.85 を目安とする。

## CNN モデルアーキテクチャ

- `VictoryClassifier` は可変サイズ入力に対応した軽量 CNN で、以下の特徴を持つ：
  - **3層の畳み込み層**：Conv2d + BatchNorm + ReLU + MaxPool2d の組み合わせで特徴抽出
  - **適応型プーリング**：`AdaptiveAvgPool2d(4, 4)` により、任意のサイズの入力を 4×4 の固定サイズに変換
  - **全結合層**：128チャンネル × 4 × 4 = 2048次元のベクトルを分類ラベル数の出力に変換
  - この設計により、アスペクト比や解像度の異なる入力画像でも学習・推論が可能

- ラベルクラス数はデータセットから自動検出される：
  - `dataset/` 配下のディレクトリ構造（`victory/`, `defeat/`, `draw/`, `none/` など）から自動認識
  - 4クラス固定ではなく、任意のクラス数に対応（6クラス、8クラスなど）
  - 学習スクリプト実行時に `VictoryDataset` が label_map を自動生成し、`num_classes` が自動設定される
  - 例：`victory_text`, `victory_progress`, `defeat_text`, `defeat_progress`, `draw`, `none` の 6クラス分類にも対応

## 今後の方針

- 配信オーバーレイは Python `/overlay` と静的ビルドの二本立てを維持しつつ、React コンポーネントの共有やビルド成果物の配布フローを整備する。
- draw を含む自動判定（画像解析）を導入し、Victory Detector 側でスナップショットから勝敗を判定できるようにする。
- CI パイプラインで Python/Node のテストを統合し、配信前の品質を担保する。
