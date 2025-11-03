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
- ラベリング手順や命名規則は `docs/plans/2025-11-03-07画像サンプル収集手順.md` を参照。データ追加時は同ドキュメントの TODO を更新し、必要に応じてテンプレート座標などのメタ情報を追記する。

## 今後の方針

- 配信オーバーレイは Python `/overlay` と静的ビルドの二本立てを維持しつつ、React コンポーネントの共有やビルド成果物の配布フローを整備する。
- draw を含む自動判定（画像解析）を導入し、Victory Detector 側でスナップショットから勝敗を判定できるようにする。
- CI パイプラインで Python/Node のテストを統合し、配信前の品質を担保する。
