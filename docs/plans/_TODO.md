# フェーズ7 TODO 総覧

## 完了済みマイルストーン

- [x] Victory/Defeat/Draw データモデル拡張と API/UI の更新
- [x] 配信用 `/overlay` エンドポイントとオーバーレイ UI の整備
- [x] テンプレートマッチング PoC（スコア分布の把握と閾値策定）
- [x] `scripts/check_templates.py` によるテンプレート整合性チェック
- [x] obs-websocket(5.x) 経由でのスクリーンショット取得 PoC

## 進行中タスク

### 画像解析 (CNN 化)
- [ ] `scripts/build_dataset.py` を用いた `victory/defeat/draw/none` データセットの整備（none クラスの収集含む）。アスペクト比保持リサイズ・可変クラス数対応済み。従来の JSON ベースに加え、`samples/<label>/` フォルダに直接 PNG を配置する簡易構造にも対応
- [ ] `scripts/train_classifier.py` で軽量 CNN を学習し、精度・推論時間を評価
- [ ] CNN推論モジュールの実装
  - [ ] `victory_detector/inference/predictor.py` にVictoryPredictorクラスを作成
  - [ ] モデルチェックポイント(.pth)の読み込み処理
  - [ ] クラス数の自動検出とモデル初期化
  - [ ] CPU/GPU デバイス管理
- [ ] CNN用の前処理パイプライン実装
  - [ ] アスペクト比維持リサイズ処理
  - [ ] 正規化処理（0-1スケール）
  - [ ] テンソル変換
- [ ] 推論結果の解釈と信頼度処理
  - [ ] Softmax/argmaxによるクラス判定
  - [ ] 信頼度しきい値の設定
  - [ ] ラベルマッピング
- [ ] `run_capture_monitor_ws.py` への統合
  - [ ] テンプレートマッチングからCNNへの切り替え
  - [ ] パフォーマンステスト（推論時間測定）
  - [ ] 精度評価
- [ ] Victory Detector への自動反映（`/adjust` POST）の実装とログ検証

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

- [ ] ライバル以外のモード・他言語 UI のスクリーンショット収集と `template_bbox` 整備
- [ ] 勝敗判定が不確実な場合のフォールバック（テンプレート照合とのハイブリッド等）
- [ ] 学習データの共有方法（LFS or 外部ストレージ）とバージョン管理方針
- [ ] 推論モデルの軽量化・最適化（ONNX、量子化など）

---

このファイルを単一の TODO とし、タスクの状態更新や追記は本ドキュメントに反映する。

## 参考メモ（データ収集・ラベリング）

- スクリーンショットは OBS で勝敗画面が表示されたタイミングを保存し、`data/samples/YYYYMMDD_runXX/` に配置する。JSON メタデータには `label`, `variant`（アクセシビリティ／モード、テンプレート生成に使用），`template_bbox`（`[x, y, width, height]`）を記録する。なお、CNN データセット構築では `variant` は不要で、`samples/<label>/*.png` という簡易構造にも対応している。
- ラベルは `victory`, `defeat`, `draw`, `none`（勝敗バナーが出ていないシーン）を基本とし、品質が低い場合は `"quality": "low"` などのフラグを付け、PoC 学習から除外できるようにする。
- 追加で収集したサンプルは `scripts/export_templates.py` → `scripts/build_dataset.py` の順でテンプレート／学習データに反映し、必要に応じて `scripts/train_classifier.py` でモデルを再学習する。簡易なデータセット構築には、`samples/victory/`, `samples/defeat/` などのフォルダに直接 PNG を配置する方法も利用できる。
- データセット構築時は `_resize_keep_aspect_ratio()` により画像のアスペクト比を維持したまま長辺を基準にリサイズするため、出力画像は必ずしも正方形ではない（例: 128×96、100×128 など）。モデルは `AdaptiveAvgPool2d(4, 4)` により可変サイズ入力に対応しているため、異なるアスペクト比の画像でも学習・推論が可能。
- クラス数はデータセットのディレクトリ構造から自動検出される（4クラス、6クラスなど任意の数に対応）。例えば `victory_text`, `victory_progress`, `defeat_text`, `defeat_progress`, `draw`, `none` の6つのフォルダを配置すれば、自動的に6クラス分類器として学習される。
