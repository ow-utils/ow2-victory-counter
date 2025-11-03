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
│  └─ 配信用オーバーレイ (作成中)         │
└──────────────────────────────┘
```

- 勝敗判定のロジック・イベントログ管理は Victory Detector 側で担当し、OBS で StateManager を起動して HTTP API を提供します。
- 管理 UI は `victory-counter-overlay-ui` 側で提供され、API を通じて勝敗カウント／履歴を取得し、手動補正を送信します。
- `/overlay` は Python 側で提供する軽量な HTML で、配信画面に簡易オーバーレイを載せたい場合の最低限の機能を担う位置付けです。将来的には `victory-counter-overlay-ui` に静的ビルド機能を実装し、ブラウザソースに静的ファイルを読み込ませる構成も検討中です。

## データフロー

1. OBS が `obs_victory_detector.py` を介して HTTP サーバを起動。
2. 管理 UI (`5173`) が `/state`・`/history` の API を定期ポーリングし、勝敗カウントと履歴を表示。`POST /adjust` で補正を行う。
3. `/overlay` エンドポイントは配信用。クエリでテーマやスケール、履歴数、更新間隔などを指定でき、埋め込みスクリプトが `/state` `/history` を一定間隔で再取得して画面を更新する。

## 今後の方針

- 配信オーバーレイを `victory-counter-overlay-ui` 側で静的ビルドできるようにし、OBS のブラウザソースにビルド済みファイルを読み込ませる構成へ発展させる。
- draw を含む自動判定（画像解析）を導入し、Victory Detector 側でスナップショットから勝敗を判定できるようにする。
- CI パイプラインで Python/Node のテストを統合し、配信前の品質を担保する。
