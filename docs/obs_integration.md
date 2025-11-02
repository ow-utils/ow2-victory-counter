# OBS 連携手順

Victory Detector を OBS Studio に組み込み、配信中に勝敗カウントを表示・調整するための手順をまとめています。

## 1. 前提条件

- Python 3.11 以上（OBS が利用する Python 実行環境に合わせる）。
- Node.js 18 以上（オーバーレイ開発サーバに使用）。
- 本リポジトリをローカルにクローン済みで、`uv` が利用可能。

> OBS の Python バージョンはインストール先によって異なるため、必要に応じて `uv python install <version>` で OBS と同じバージョンを用意してください。OBS Scripts Manager 側で参照する Python パスを合わせることが重要です。

## 2. Victory Detector の準備

1. 依存のロックファイルがない場合は `uv lock` を実行します。
2. OBS から読み込めるよう、`victory-detector/scripts/obs_victory_detector.py` を使用します（後述）。
3. イベントログを初期化する場合は CLI でモック判定を流せます。

```bash
cd packages/obs-victory-counter/victory-detector
PYTHONPATH=src UV_NO_SYNC=1 uv run python -m victory_detector.cli tests/fixtures/snapshots_simple.json --event-log events_cli.log
```

CLI を実行すると `events_cli.log` に初期イベントが保存されます。OBS から同じログを参照することで、配信開始時点の勝敗カウントが再現されます。

## 3. OBS Scripts Manager への登録

1. OBS を起動し、メニューの **ツール > スクリプト** を選択します。
2. **Python スクリプト** タブで「+」ボタンを押し、`packages/obs-victory-counter/victory-detector/scripts/obs_victory_detector.py` を追加します。
3. 右側の設定で以下を指定できます。
   - **Event Log Path**: 勝敗ログの JSON Lines ファイル。既定は `events_cli.log`。
   - **Host**: HTTP サーバのバインドアドレス（既定 `127.0.0.1`）。
   - **Port**: HTTP ポート（既定 `8912`）。
4. スクリプトを有効にすると、バックグラウンドで HTTP サーバが起動し `/state` `/history` `/adjust` が利用可能になります。
5. スクリプトを無効化／削除するとサーバは自動で停止します。

`obs_victory_detector.py` は OBS のライフサイクルに合わせて StateManager を生成・保存し、設定変更時にサーバを再起動します。OBS のログには `Victory Detector server started` の出力が記録されるため、動作確認の参考にしてください。

## 4. ブラウザソースの設定

1. 別ターミナルでオーバーレイ用開発サーバを起動します。

```bash
cd packages/obs-victory-counter/victory-counter-overlay-ui
npm run dev
```

2. OBS のシーンに「ブラウザ」を追加し、URL を `http://127.0.0.1:5173` に設定します（必要に応じてポート番号を変更）。
3. 表示サイズを配信レイアウトに合わせて調整します。背景は透過気味のダークカラーに設定しているため、必要に応じて CSS をカスタマイズしてください。

> 本番運用では静的ビルド + 任意の HTTP サーバを利用する想定です。現状はモック段階のため、開発サーバを利用しています。

## 5. 手動補正とリアルタイム更新の確認

1. ブラウザソース内の右下フォームから Outcome/Delta/Note を入力し「Apply」を押す。
2. `victory-detector` 側の `/adjust` API が呼び出され、イベントログに追記されます。
3. UI は 5 秒間隔で `/state` をポーリングし、勝敗カウントと Recent Events が更新されます。
4. 成功時／失敗時のメッセージはステータスバーに表示されるため、配信前の接続確認に活用してください。

## 6. トラブルシュート

- **CORS エラー**: UI 側が `Access-Control-Allow-Origin` を要求するため、v0.0.2 以降のサーバコードを使用してください。旧版では CORS ヘッダーが不足している可能性があります。
- **ポート競合**: ポート `8912` が埋まっている場合は、OBS スクリプトの設定で別ポートを指定し、UI 側の `body data-poll-interval` または `src/apiClient.js` の `baseUrl` を調整します。
- **OBS の Python パス**: OBS が使用する Python DLL が見つからない場合、OBS の「スクリプト」ダイアログ右下の「Python 設定」で正しいパスをセットしてください。

## 7. 今後の展望

- **Draw（引き分け）対応**: バックログに記載したとおり、勝敗に加えて draw を扱うための拡張が必要です。
- **静的配信用ビルド**: `npm run dev` 依存を解消し、任意の HTTP サーバや OBS のローカルファイルモードでも動作するよう調整する予定です。
- **認証**: 現状はローカル用途に限定しており認証は不要ですが、将来的に外部アクセスを許可する場合に備え、API トークン等の導入を検討してください。

上記手順に従うことで、OBS 上で勝敗カウントが自動更新され、手動補正も反映されます。トラブル発生時は `obs_log.txt` と Victory Detector の標準出力を併せて確認してください。
