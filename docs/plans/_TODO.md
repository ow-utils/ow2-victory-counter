# フェーズ7 TODO 総覧

## 完了済みマイルストーン

- [x] Git 履歴から画像ファイル（.png）を削除
  - git-filter-repo で全履歴から .png を削除
  - git lfs prune でローカル LFS キャッシュをクリーンアップ
  - 履歴から完全に削除されたことを検証済み

- [x] Victory/Defeat/Draw データモデル拡張と API/UI の更新
- [x] 配信用 `/overlay` エンドポイントとオーバーレイ UI の整備
- [x] テンプレートマッチング PoC（スコア分布の把握と閾値策定）
- [x] `scripts/check_templates.py` によるテンプレート整合性チェック
- [x] obs-websocket(5.x) 経由でのスクリーンショット取得 PoC
- [x] `scripts/build_dataset.py` を用いた `victory/defeat/draw/none` データセットの整備（6クラス、230枚で完了）
- [x] `scripts/train_classifier.py` で軽量 CNN を学習し、精度・推論時間を評価（検証精度91.30%達成）
- [x] CNN推論モジュールの実装（`victory_detector.inference.VictoryPredictor`）
  - モデルチェックポイント読み込み、クラス数自動検出、CPU/GPU デバイス管理
  - アスペクト比維持リサイズ、正規化、テンソル変換の前処理パイプライン
  - Softmax/argmax によるクラス判定と信頼度処理
  - 6クラス分類結果から勝敗・ドローへのマッピング（victory_text/victory_progressbar → victory 等）
- [x] 重複カウント防止（クールダウン）機能の実装
  - StateManager に最終検知時刻記録機能、デフォルト180秒のクールダウン
  - クールダウン中の検知をログに記録（delta=0、カウントしない）
- [x] `run_capture_monitor_ws.py` のCNN化完了
  - テンプレートマッチングから CNN への完全切り替え
  - StateManager への直接統合
  - パフォーマンステスト完了（推論時間・精度評価済み）
- [x] 誤検知改善プラン（2025-11-09）
  - DetectionResult に `predicted_class` フィールド追加（6クラス詳細名を保持）
  - 検知時スクリーンショット自動保存機能（`--save-detections` オプション）
  - 学習画像サイズをオリジナル（995×550）に変更
  - オリジナルサイズでモデル再訓練（精度向上、約10分/エポック）
- [x] 連続検知機能の実装（2025-11-10）
  - 連続N回（デフォルト3回）同じ結果が出た場合のみカウント
  - キャプチャ間隔を0.25秒に短縮（0.75秒で判定確定）
  - 異なる結果が出たら連続カウントをリセット
  - スクリーンショット保存は連続検知の最初の1回のみ
  - DetectionResponse データクラスで連続検知状態を返す

## 進行中タスク

### draw判定の除外と5クラスモデルへの移行（2025-11-16）

**背景**:
- draw_textクラス（19枚）の誤判定が多発
- 教師データが少なく学習データ拡充が困難
- draw判定を除外し、5クラス（none, victory_text, victory_progressbar, defeat_text, defeat_progressbar）分類に移行

**実施タスク**:
- [ ] dataset/draw_text ディレクトリを削除（dataset_backup/ に移動してバックアップ）
- [ ] predictor.py の CLASS_TO_OUTCOME 定数から "draw_text": "draw" エントリを削除
- [ ] 型ヒント Literal["victory", "defeat", "draw", "unknown"] から "draw" を削除
- [ ] 5クラスでモデル再学習（train_classifier.py --batch-size 16 --epochs 30）
- [ ] 推論テストと動作確認（draw_text が出力されないことを確認）
- [ ] 実運用での精度評価

**クラス構成の変更**:
- 変更前: 6クラス（victory_text, victory_progressbar, defeat_text, defeat_progressbar, draw_text, none）
- 変更後: 5クラス（victory_text, victory_progressbar, defeat_text, defeat_progressbar, none）

### 連続検知機能（2025-11-10）

実運用テストとモデル再訓練を踏まえ、誤検知をさらに削減するための連続検知機能を実装：

- [ ] 実運用テストと継続的改善
  - [ ] 連続検知機能を有効にして実際のゲームプレイでテスト
  - [ ] 保存されたスクリーンショットから誤検知パターンを分析
  - [ ] 必要に応じて `required_consecutive` パラメータを調整（2回 or 4回）
  - [ ] 誤検知画像を学習データに追加して再訓練

### OBS 連携・運用
- [ ] websocket 監視スクリプトの設定ファイル化（variant ごとの `template_bbox` / モデル指定）
- [ ] キャプチャ間隔を 0.3s 前後に設定した長時間テストと負荷計測
- [ ] 誤判定時のリトライ／エラーログ整理

### 静的ビルド・CI
- [ ] `victory-counter-overlay-ui` の静的ビルドと管理 UI のコンポーネント共有計画
- [ ] Python/Node の lint/test/build を GitHub Actions で自動化
- [ ] モデル学習・テンプレート生成の CI 手順（少なくともフォーマットチェック、テンプレート整合性チェック）

### ドキュメント整備
- [ ] CNN 学習・推論手順を `docs/specs/architecture.md` などに追記
- [ ] ユーザー向けセットアップ手順（obs-websocket 設定 / キャプチャソース選択 / CNN 導入手順）の整備

## バックログ

- [ ] 勝敗判定の放置対策（2025-11-15）
  - [ ] クールダウン明け再開条件として `none` の連続検知（規定回数）を導入し、victory/defeat progressbar 画面放置時の誤カウントを防止
  - [ ] `required_none_consecutive`（仮）パラメータを `StateManager` へ追加し、クールダウン解除と連続検知ロジックの整合性を担保する
  - [ ] 仕様を `docs/specs/architecture.md` に追記し、運用手順へ `none` 連続判定の役割を説明
- [ ] ライバル以外のモード・他言語 UI のスクリーンショット収集と `template_bbox` 整備
- [ ] 勝敗判定が不確実な場合のフォールバック（テンプレート照合とのハイブリッド等）
- [ ] 学習データの共有方法（LFS or 外部ストレージ）とバージョン管理方針
- [ ] 推論モデルの軽量化・最適化（ONNX、量子化など）

---

このファイルを単一の TODO とし、タスクの状態更新や追記は本ドキュメントに反映する。

## 参考メモ（データ収集・ラベリング）

※以下のパスは victory-detector プロジェクト (`packages/obs-victory-counter/victory-detector/`) 内の相対パスです。

- スクリーンショットは OBS で勝敗画面が表示されたタイミングを保存し、`data/samples/YYYYMMDD_runXX/` に配置する。JSON メタデータには `label`, `variant`（アクセシビリティ／モード、テンプレート生成に使用），`template_bbox`（`[x, y, width, height]`）を記録する。なお、CNN データセット構築では `variant` は不要で、`samples/<label>/*.png` という簡易構造にも対応している。
- ラベルは `victory`, `defeat`, `draw`, `none`（勝敗バナーが出ていないシーン）を基本とし、品質が低い場合は `"quality": "low"` などのフラグを付け、PoC 学習から除外できるようにする。
- 追加で収集したサンプルは `scripts/export_templates.py` → `scripts/build_dataset.py` の順でテンプレート／学習データに反映し、必要に応じて `scripts/train_classifier.py` でモデルを再学習する。簡易なデータセット構築には、`samples/victory/`, `samples/defeat/` などのフォルダに直接 PNG を配置する方法も利用できる。
- データセット構築時は `_resize_keep_aspect_ratio()` により画像のアスペクト比を維持したまま長辺を基準にリサイズするため、出力画像は必ずしも正方形ではない（例: 128×96、100×128 など）。モデルは `AdaptiveAvgPool2d(4, 4)` により可変サイズ入力に対応しているため、異なるアスペクト比の画像でも学習・推論が可能。
- クラス数はデータセットのディレクトリ構造から自動検出される（4クラス、6クラスなど任意の数に対応）。例えば `victory_text`, `victory_progress`, `defeat_text`, `defeat_progress`, `draw`, `none` の6つのフォルダを配置すれば、自動的に6クラス分類器として学習される。
- **推奨クロップ領域**: `460,378,995,550` (x, y, width, height)
  - データセット構築時に `build_dataset.py --crop 460,378,995,550` で使用
  - この領域は画面中央の勝敗テキストバナーと画面下部のプログレスバーの両方を含む統一領域として設定されており、`victory_text`/`defeat_text` と `victory_progress`/`defeat_progress` の両方のクラスを一度の推論で判定できる
- **学習画像サイズ**: デフォルトはオリジナルサイズ（クロップ後995×550）を使用
  - `build_dataset.py` は `--size` 未指定時はリサイズせずオリジナルサイズを維持
  - `--size 512` などを指定することで任意のサイズにリサイズ可能
  - モデルは `AdaptiveAvgPool2d(4, 4)` により可変サイズ入力に対応
  - オリジナルサイズ使用により情報損失を最小化し、精度向上を目指す
  - RTX 3070での推論時間: 約5-8ms（250-500ms間隔で十分な余裕）
