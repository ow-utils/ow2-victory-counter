# obs-win-counter

このディレクトリーには Overwatch 2 の勝敗カウンター関連プロジェクトをまとめています。

## プロジェクト構成

- `win-detector/`  
  OBS Studio の Python スクリプトとして動作する勝敗判定ロジックと、HTTP API を提供するバックエンドコンポーネント。

- `win-counter-overlay-ui/`  
  ブラウザソースで勝敗カウントや履歴を表示するためのフロントエンド資産。開発中はローカルサーバで動作確認します。

共通のドキュメントやサンプルデータはこのディレクトリー内、または必要に応じて `shared/` を追加して管理してください。

## 開発の流れ（概要）

1. `win-detector` の `uv` ワークスペースをセットアップし、画像処理ロジックを実装。
2. `win-counter-overlay-ui` でモックデータを使った UI を構築。
3. HTTP API 経由で両者を接続し、OBS との連携検証を実施。

詳細なタスクは `docs/implementation_todo.md` を参照してください。
