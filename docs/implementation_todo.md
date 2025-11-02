# 実装フェーズ TODO 一覧

## フェーズ1: 骨組み整備

- [x] `packages/obs-win-counter/` ディレクトリーを作成し、親 `README.md` を配置する
- [x] `packages/obs-win-counter/README.md` にモノレポ構造と各プロジェクトの役割をまとめる
- [x] `packages/obs-win-counter/win-detector/` を作成し、以下の雛形を追加する
  - [x] `pyproject.toml`（`uv` ワークスペース設定、依存プレースホルダー）
  - [x] `src/win_detector/__init__.py`
  - [x] `tests/__init__.py` と `tests/conftest.py`
- [x] `uv lock` を生成し、`uv run python -V` が成功することを確認する
- [x] `packages/obs-win-counter/win-counter-overlay-ui/` を作成し、以下の雛形を追加する
  - [x] `package.json`（`lint`・`test` スクリプトのプレースホルダー）
  - [x] `src/index.tsx` もしくは `src/index.ts`／`index.html` の最小構成
- [x] 選定したパッケージマネージャで依存を初期化し、`npm run lint` が成功することを確認する
- [x] ルート `.gitignore` を更新し、`uv.lock`・`node_modules/` 等を除外する

## フェーズ2: 判定ロジックのスタンドアロン実装

- [x] `win-detector/src/win_detector/core/vision.py` にテンプレートマッチング処理を実装する
- [x] `win-detector/src/win_detector/core/state.py` に勝敗集計とイベントログ管理を実装する
- [x] `tests/fixtures/` にサンプルフレームを追加し、`pytest` で判定精度を検証する（テスト実行は要ネットワーク）
- [x] JSON Lines 形式のイベントログ追記と再起動時の復元処理を実装・テストする
- [x] `uv run python -m win_detector.cli ...` を用意し、CLI 経由でデバッグ出力を確認する（`PYTHONPATH=src` で実行）

## フェーズ3: HTTPサーバ層の追加

- [ ] `win_detector/server.py` に `ThreadingHTTPServer` での `/state` 提供機能を実装する
- [ ] `curl 127.0.0.1:8912/state` で最新カウントが取得できることを確認する
- [ ] API シリアライズの単体テストと異常系（サーバ停止時など）のログ確認を行う

## フェーズ3.5: 履歴APIと手動補正準備

- [ ] `/history` エンドポイントを追加し、直近N件のイベントログを返す
- [ ] `POST /adjust` のスケルトンを実装し、補正イベントをログに追記できるようにする
- [ ] `docs/api.md` に `/state`・`/history`・`/adjust` の仕様と認証方針を記述する

## フェーズ4: オーバーレイUIのモック実装

- [ ] `win-counter-overlay-ui` にダミーデータで動作するモックUIを実装する
- [ ] `npm start`（または `npm run dev`）でモック画面を表示し、表示崩れがないか確認する
- [ ] `vitest` や Testing Library でコンポーネントの描画テストを追加する

## フェーズ5: 実データ接続

- [ ] `fetch('/state')` のポーリング処理とタイムアウト/リトライを実装する
- [ ] ローカルの HTTP サーバと接続し、リアルタイムでカウントが反映されることを確認する
- [ ] 管理用 UI もしくはツールから `POST /adjust` を実行し、補正が反映されることを検証する
- [ ] ネットワーク障害を想定したエラーハンドリングと表示を実装する

## フェーズ6: OBS 連携

- [ ] OBS Scripts Manager に `win-detector` を読み込ませ、ゲーム配信で勝敗が更新されるか確認する
- [ ] OBS ブラウザソースにオーバーレイを適用し、リアルタイム連携を検証する
- [ ] 観戦中に手動補正を実施し、`/history` と UI 表示が同期するか確認する
- [ ] 検証結果・スクリーンショット・課題を `docs/` 配下に記録する

## フェーズ7: 最終調整と CI 整備

- [ ] `pytest --cov` と `npm run test -- --coverage` を実行し、カバレッジ目標を達成する
- [ ] GitHub Actions（`ci.yml`）で `uv run pytest` と `npm test` を並列実行するワークフローを構築する
- [ ] `docs/usage.md` や 親 `README.md` にセットアップ手順・トラブルシュートを記載する
- [ ] リリース手順（バージョニング、配布方法）を整理し、必要であれば `CHANGELOG.md` を準備する
