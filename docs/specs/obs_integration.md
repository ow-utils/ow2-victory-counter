# OBS 連携手順

Victory Detector を OBS Studio に組み込み、配信中に勝敗カウントを表示・調整するための手順をまとめています。

## 1. 前提条件

- Python 3.12（OBS が利用する Python 実行環境に合わせる）。
  - 3.13 以降はOBSが対応していません
- Node.js 18 以上（オーバーレイ開発サーバに使用）。
- 本リポジトリをローカルにクローン済みで、`uv` が利用可能。

> OBS の Python バージョンはインストール先によって異なるため、必要に応じて `uv python install <version>` で OBS と同じバージョンを用意してください。OBS Scripts Manager 側で参照する Python パスを合わせることが重要です。

## 2. Victory Detector の準備

1. 依存のロックファイルがない場合は `uv lock` を実行します。
2. OBS から読み込めるよう、`victory-detector/scripts/obs_victory_detector.py` を使用します（後述）。
3. イベントログを初期化する場合は CLI でモック判定を流せます。

```bash
cd packages/obs-victory-counter/victory-detector
PYTHONPATH=src UV_NO_SYNC=1 uv run python -m victory_detector.cli tests/fixtures/snapshots_simple.json --event-log logs/detections.jsonl
```

CLI を実行すると `logs/detections.jsonl` に初期イベントが保存されます。OBS から同じログを参照することで、配信開始時点の勝敗カウントが再現されます。

## 3. OBS Scripts Manager への登録

1. OBS を起動し、メニューの **ツール > スクリプト** を選択します。
2. **Python スクリプト** タブで「+」ボタンを押し、`packages/obs-victory-counter/victory-detector/scripts/obs_victory_detector.py` を追加します。
3. 右側の設定で以下を指定できます。
   - **Event Log Path**: 勝敗ログの JSON Lines ファイル。既定は `logs/detections.jsonl`。
   - **Host**: HTTP サーバのバインドアドレス（既定 `127.0.0.1`）。
   - **Port**: HTTP ポート（既定 `8912`）。
   - **Reload Interval (sec)**: EventLog の再読み込み間隔（秒、既定 5）。
4. スクリプトを有効にすると、バックグラウンドで HTTP サーバが起動し `/state` `/history` `/adjust` が利用可能になります。
5. スクリプトを無効化／削除するとサーバは自動で停止します。

`obs_victory_detector.py` は OBS のライフサイクルに合わせて StateManager を生成・保存し、設定変更時にサーバを再起動します。OBS のログには `Victory Detector server started` の出力が記録されるため、動作確認の参考にしてください。

## 4. CNN 推論プロセスの起動

OBS スクリプトとは別に、CNN を使った自動勝敗判定を行う外部プロセス `run_capture_monitor_ws.py` を起動します。

### 4.1 学習済みモデルの準備

1. データセットを準備します（`data/samples/` または `samples/<label>/*.png` 形式）。
2. データセットをビルドします。

   ```bash
   cd packages/obs-victory-counter/victory-detector
   uv run python scripts/build_dataset.py --data data/samples --output dataset --crop 460,378,995,550 --size 128
   ```

3. CNN モデルを訓練します。

   ```bash
   uv run python scripts/train_classifier.py --data dataset --epochs 30 --batch-size 32
   ```

4. 学習済みモデルが `artifacts/models/victory_classifier.pth` に保存されます。このファイルには label_map と idx_to_label が含まれています。

### 4.2 CNN 推論プロセスの起動

1. OBS で obs-websocket を有効化します（ツール > WebSocket サーバ設定）。ポート `4455` とパスワードを確認します。
2. 別ターミナルで CNN 推論プロセスを起動します。

   ```bash
   cd packages/obs-victory-counter/victory-detector
   uv run python scripts/run_capture_monitor_ws.py \
     --host 127.0.0.1 \
     --port 4455 \
     --password "<obs-websocketのパスワード>" \
     --source "<ゲームキャプチャソース名>" \
     --model artifacts/models/victory_classifier.pth \
     --event-log logs/detections.jsonl \
     --cooldown 180 \
     --interval 2.0
   ```

   - `--source`: OBS のソース名（例: "ゲームキャプチャ"、"ウィンドウキャプチャ (Overwatch 2)"）
   - `--model`: 学習済みモデルのパス
   - `--event-log`: イベントログファイル（OBS スクリプトと同じパスを指定）
   - `--cooldown`: クールダウン時間（秒、デフォルト 180）
   - `--interval`: キャプチャ間隔（秒、デフォルト 2.0）

3. 推論結果は標準出力に JSON 形式で出力されます。

   ```jsonl
   {"outcome": "victory", "confidence": 0.9987, "counted": true, "timestamp": 1731148320.5, "counter": {"victories": 1, "defeats": 0, "draws": 0}}
   {"outcome": "victory", "confidence": 0.9923, "counted": false, "timestamp": 1731148322.5, "counter": {"victories": 1, "defeats": 0, "draws": 0}, "cooldown_note": "[cooldown: 178s remaining]"}
   ```

   - `counted: true` はカウントに反映された検知
   - `counted: false` はクールダウン中の検知（`cooldown_note` に残り時間が記録される）

### 4.3 二重起動の注意

- **OBS スクリプト** (`obs_victory_detector.py`): HTTP API サーバとして起動（`/state`, `/history`, `/adjust` エンドポイントを提供）
- **CNN 推論プロセス** (`run_capture_monitor_ws.py`): 外部プロセスとして起動（obs-websocket 経由でスクリーンショット取得・CNN 推論・イベントログ記録）

両プロセスは同一の `logs/detections.jsonl` を参照することで状態を同期します。OBS スクリプト側の設定で Event Log Path を `logs/detections.jsonl` に設定し、CNN 推論プロセスの `--event-log` と一致させてください。

## 5. ブラウザソースの設定

### 5.1 管理 UI（開発サーバ）を表示する場合

1. 別ターミナルでオーバーレイ用開発サーバを起動します。

```bash
cd packages/obs-victory-counter/victory-counter-overlay-ui
npm run dev
```

2. OBS のシーンに「ブラウザ」を追加し、URL を `http://127.0.0.1:5173` に設定します（必要に応じてポート番号を変更）。
3. 表示サイズを配信レイアウトに合わせて調整します。背景は透過気味のダークカラーに設定しているため、必要に応じて CSS をカスタマイズしてください。

> 本番運用では静的ビルド + 任意の HTTP サーバを利用する想定です。現状はモック段階のため、開発サーバを利用しています。

### 5.2 Victory Detector `/overlay` を表示する場合

- 配信用には `victory-detector` の `http://127.0.0.1:8912/overlay` をブラウザソースに設定することで、コンパクトな UI を直接表示できます。
- クエリパラメータ例: `http://127.0.0.1:8912/overlay?theme=transparent&scale=1.1&history=5`
- Draw の表示を省きたい場合は `showDraw=false` を指定してください。
- 更新間隔を調整したい場合は `poll=3` のように指定すると 3 秒ごとに自動更新されます。
- さらにデザインを細かく調整したい場合は、OBS の「カスタム CSS」で `overlay-card` や `overlay-history__item` などのクラスを上書きできます。
- 静的ファイルで利用したい場合は `victory-counter-overlay-ui` で `npm run build` を実行し、生成された `dist/overlay.html` を OBS ブラウザソースで `file:///.../dist/overlay.html` として読み込むことも可能です。

### 5.3 静的ビルドの利用手順

1. `victory-counter-overlay-ui` でビルドを実行します。

   ```bash
   cd packages/obs-victory-counter/victory-counter-overlay-ui
   npm run build
   ```

2. 生成された `dist` ディレクトリを利用し、以下のいずれかの方法で OBS に読み込ませます。
   - **ローカルファイルとして読み込む**: OBS ブラウザソースの URL を `file:///.../dist/overlay.html` に設定する。ファイル更新時は OBS のプロパティ画面で「リロード」ボタンを押して反映させる。
   - **軽量サーバで配信する**: `dist` をルートとして簡易サーバを起動し、`http://127.0.0.1:4173/overlay.html` のような URL を指定する。例: `npm run preview`, `python -m http.server --directory dist 4173`。
3. `dist` 以下には `assets/` ディレクトリも生成されるため、OBS の参照先がこれらのファイルを読み込めるパスであることを確認してください。
4. Python パッケージ側から配布したい場合は `npm run package-overlay` を実行すると、`victory-detector/static/overlay/` にファイルをコピーできます（リポジトリにはコミットされません）。
5. カスタム CSS を適用する際は、`.overlay-card`, `.overlay-history__item`, `.overlay-result__label` などのクラスを上書きすると配信者がレイアウトを調整しやすくなります。

## 6. 手動補正とリアルタイム更新の確認

1. ブラウザソース内の右下フォームから Outcome/Delta/Note を入力し「Apply」を押す。
2. `victory-detector` 側の `/adjust` API が呼び出され、イベントログに追記されます。
3. UI は 5 秒間隔で `/state` をポーリングし、勝敗カウントと Recent Events が更新されます。
4. 成功時／失敗時のメッセージはステータスバーに表示されるため、配信前の接続確認に活用してください。

## 7. トラブルシュート

### 7.1 API 接続の問題

- **CORS エラー**: UI 側が `Access-Control-Allow-Origin` を要求するため、v0.0.2 以降のサーバコードを使用してください。旧版では CORS ヘッダーが不足している可能性があります。
- **ポート競合**: ポート `8912` が埋まっている場合は、OBS スクリプトの設定で別ポートを指定し、UI 側の `body data-poll-interval` または `src/apiClient.js` の `baseUrl` を調整します。
- **OBS の Python パス**: OBS が使用する Python DLL が見つからない場合、OBS の「スクリプト」ダイアログ右下の「Python 設定」で正しいパスをセットしてください。

### 7.2 CNN 推論プロセスの問題

- **obs-websocket 接続エラー**: OBS の「ツール > WebSocket サーバ設定」でサーバが有効になっているか、ポート番号とパスワードが正しいか確認してください。
- **ソース名が見つからない**: `--source` に指定した名前が OBS のソース一覧と完全一致しているか確認してください（大文字小文字、スペースに注意）。
- **GPU が利用されない**: PyTorch が CUDA を認識しているか確認してください（`python -c "import torch; print(torch.cuda.is_available())"`）。
- **推論精度が低い**: 学習データが不足している可能性があります。`data/samples/` にサンプルを追加し、再訓練してください。
- **クールダウンが効かない**: イベントログファイルが OBS スクリプトと CNN プロセスで一致しているか確認してください。

## 8. 今後の展望

- **静的配信用ビルド**: `npm run dev` 依存を解消し、任意の HTTP サーバや OBS のローカルファイルモードでも動作するよう調整する予定です。
- **認証**: 現状はローカル用途に限定しており認証は不要ですが、将来的に外部アクセスを許可する場合に備え、API トークン等の導入を検討してください。
- **モデル配布**: 学習済みモデルファイルを GitHub Releases や外部ストレージで配布し、初期セットアップを簡素化する。
- **リアルタイム通知**: WebSocket を使って管理 UI へのプッシュ通知を実装し、ポーリング間隔を削減する。

上記手順に従うことで、OBS 上で勝敗カウントが自動更新され、手動補正も反映されます。トラブル発生時は `obs_log.txt` と Victory Detector の標準出力を併せて確認してください。
