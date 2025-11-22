# obs-victory-counter

このディレクトリーには Overwatch 2 の勝敗カウンター関連プロジェクトをまとめています。

PoCとしてPythonで実装を行ったものです。
正式なものとしては [ow2-victory-trainer](../ow2-victory-trainer/README.md), [ow2-victory-counter-rs](../ow2-victory-counter-rs/README.md) に引き継いでおり、このプロジェクトはもはや更新されません。

## プロジェクト構成

- `victory-detector/`  
  OBS Studio の Python スクリプトとして動作する勝敗判定ロジックと、HTTP API を提供するバックエンドコンポーネント。`scripts/obs_victory_detector.py` を OBS Scripts Manager に追加すると、配信中に HTTP API が自動起動します（手順は `docs/obs_integration.md` を参照）。

- `victory-counter-overlay-ui/`  
  ブラウザソースで勝敗カウントや履歴を表示するためのフロントエンド資産。開発中はローカルサーバで動作確認します。

共通のドキュメントやサンプルデータはこのディレクトリー内、または必要に応じて `shared/` を追加して管理してください。

## 開発の流れ（概要）

1. `victory-detector` の `uv` ワークスペースをセットアップし、画像処理ロジックを実装。
2. `victory-counter-overlay-ui` でモックデータを使った UI を構築。
3. HTTP API 経由で両者を接続し、OBS との連携検証を実施。

詳細なタスクは `docs/implementation_todo.md` を参照してください。
