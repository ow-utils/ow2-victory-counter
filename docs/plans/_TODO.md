# ow2-victory-counter-rs 実装TODO

このドキュメントは、Rust版Overwatch 2勝敗カウンターの実装タスクリストです。

**参照ドキュメント**:

- [アーキテクチャ設計](../specs/ow2-victory-counter-rsアーキテクチャ設計.md)
- [実装詳細](./2025-11-16-04実装詳細.md)

## タスク凡例

- 🔴 優先度: 高（必須、他タスクの依存元）
- 🟡 優先度: 中（重要だが依存関係は少ない）
- 🟢 優先度: 低（後回し可能）
- ✅ 完了
- 🚧 進行中
- ⏳ 未着手

---

## 1. 環境セットアップ

### 🔴 1.1 Rust環境構築

- ✅ Rust 1.70以上のインストール
  ```bash
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
  rustc --version  # 1.70以上を確認
  ```
- **依存関係**: なし
- **参照**: [実装詳細#開発環境](./2025-11-16-04実装詳細.md#開発環境)

### 🔴 1.2 JavaScript環境構築

- ✅ Node.js 18.x以上のインストール
  ```bash
  nvm install 18
  nvm use 18
  node --version  # v18.x以上を確認
  ```
- ✅ pnpm 8.x以上のインストール
  ```bash
  npm install -g pnpm
  pnpm --version  # 8.x以上を確認
  ```
- **依存関係**: なし
- **参照**: [実装詳細#開発環境](./2025-11-16-04実装詳細.md#開発環境)

---

## 2. リポジトリー構造作成

### 🔴 2.1 ディレクトリー構造作成

- ✅ `packages/ow2-victory-counter-rs/` ディレクトリー作成
  ```bash
  mkdir -p packages/ow2-victory-counter-rs/{src/{server,state,predictor,capture},frontend/{obs-ui,admin-ui},models,config,templates}
  ```
- **依存関係**: 1.1, 1.2
- **参照**: [実装詳細#リポジトリー構造](./2025-11-16-04実装詳細.md#リポジトリー構造)

### 🔴 2.2 Cargo.toml設定

- ✅ `Cargo.toml` 作成
  ```toml
  [package]
  name = "ow2-victory-detector"
  version = "0.1.0"
  edition = "2021"

  [dependencies]
  axum = "0.7"
  tokio = { version = "1", features = ["full"] }
  tokio-stream = "0.1"
  serde = { version = "1", features = ["derive"] }
  serde_json = "1"
  ort = { version = "2", features = ["download-binaries"] }
  ndarray = "0.15"
  opencv = "0.91"
  obws = "0.11"
  base64 = "0.21"
  tracing = "0.1"
  tracing-subscriber = "0.3"
  ```
- **依存関係**: 2.1
- **参照**: [実装詳細#開発環境](./2025-11-16-04実装詳細.md#開発環境)

### 🔴 2.3 フロントエンドpackage.json設定

- ✅ `frontend/package.json` 作成（単一プロジェクト）
  ```json
  {
    "name": "ow2-victory-counter-ui",
    "version": "0.1.0",
    "type": "module",
    "scripts": {
      "dev": "vite",
      "build": "vite build",
      "preview": "vite preview"
    },
    "devDependencies": {
      "@sveltejs/vite-plugin-svelte": "^6.0.0",
      "svelte": "^5.0.0",
      "typescript": "^5.0.0",
      "vite": "^7.0.0"
    }
  }
  ```
- **依存関係**: 2.1
- **参照**: [実装詳細#開発環境](./2025-11-16-04実装詳細.md#開発環境)
- **備考**: マルチページアプリケーション方式（obs.html, admin.html）

---

## 3. Vite開発環境設定

### 🔴 3.1 Vite設定ファイル作成

- ✅ `frontend/vite.config.ts` 作成（マルチページアプリ設定）
  ```typescript
  import { defineConfig } from "vite";
  import { svelte } from "@sveltejs/vite-plugin-svelte";
  import { resolve } from "path";

  export default defineConfig({
    plugins: [svelte()],
    build: {
      rollupOptions: {
        input: {
          obs: resolve(__dirname, "obs.html"),
          admin: resolve(__dirname, "admin.html"),
        },
      },
    },
    server: {
      port: 5173,
      proxy: {
        "/events": { target: "http://localhost:3000", changeOrigin: true },
        "/api": { target: "http://localhost:3000", changeOrigin: true },
        "/custom.css": { target: "http://localhost:3000", changeOrigin: true },
      },
    },
  });
  ```
- **依存関係**: 2.3
- **目的**: マルチページアプリ（obs.html, admin.html）+ Rustサーバーへのプロキシ

### 🔴 3.2 TypeScript設定

- ✅ `frontend/tsconfig.json` 作成
  ```json
  {
    "extends": "@tsconfig/svelte/tsconfig.json",
    "compilerOptions": {
      "target": "ES2020",
      "module": "ESNext",
      "moduleResolution": "bundler",
      "resolveJsonModule": true,
      "allowJs": true,
      "checkJs": true,
      "isolatedModules": true,
      "baseUrl": ".",
      "paths": {
        "$lib/*": ["src/lib/*"]
      }
    },
    "include": ["src/**/*.ts", "src/**/*.svelte"],
    "exclude": ["node_modules"]
  }
  ```
- **依存関係**: 2.3
- **備考**: `$lib/*` エイリアスで共通コンポーネントをインポート可能

### 🟡 3.3 開発フロードキュメント

- ⏳ 開発フローの README セクション追加
  - **開発モード**: Vite dev server（`pnpm dev`）+ Rustサーバー（`cargo run`）並行起動
  - **本番モード**: フロントエンドビルド（`pnpm build`）→ Rustバイナリーに組み込み
- **依存関係**: 3.1, 3.2

---

## 4. Rust実装

### 🔴 4.1 画像取得・前処理モジュール

- ✅ `src/capture/mod.rs` 作成
- ✅ `src/capture/obs.rs` 作成
  - `OBSCapture` 構造体
  - `new()` メソッド（OBS WebSocket接続）
  - `capture()` メソッド（OBS WebSocket経由で画像取得、Base64デコード、PNGデコード）
  - `preprocess()` メソッド（クロップ）
  - `to_rgb8()` メソッド（RGB8バッファ変換）
  - `CaptureError` エラー型
- **依存関係**: 2.2
- **参照**: [実装詳細#画像取得・前処理モジュール](./2025-11-16-04実装詳細.md#1-画像取得前処理モジュール)
- **備考**: opencv の代わりに image クレート (pure Rust) を使用。obws 0.14, base64 0.22 で実装。

### 🔴 4.2 CNN推論モジュール

- ✅ `src/predictor/mod.rs` 作成
- ✅ `src/predictor/onnx.rs` 作成
  - `VictoryPredictor` 構造体
  - `new()` メソッド（ONNX Runtime初期化、label_map読み込み）
  - `predict()` メソッド（画像→テンソル変換→推論→ラベル変換）
  - `Detection` 構造体
- **依存関係**: 2.2, 7.1（ONNXモデル）
- **参照**: [実装詳細#CNN推論モジュール](./2025-11-16-04実装詳細.md#2-cnn-推論モジュール)
- **備考**: ort 2.0.0-rc.10 対応。ndarray 0.16 使用（0.17 は未対応）。

### 🔴 4.3 StateManager

- ✅ `src/state/mod.rs` 作成
- ✅ `src/state/manager.rs` 作成
  - `State` enum（Ready, Cooldown, WaitingForNone）
  - `StateManager` 構造体
  - `record_detection()` メソッド（連続検知判定、状態遷移）
  - `initialize()` / `adjust()` メソッド（REST API用）
  - `broadcast_update()` メソッド（SSE配信）
- **依存関係**: 2.2
- **参照**: [実装詳細#StateManager](./2025-11-16-04実装詳細.md#3-statemanager)

### 🔴 4.4 HTTPサーバー

- ✅ `src/server/mod.rs` 作成
- ✅ `src/server/routes.rs` 作成
  - `app()` 関数（axum Router設定）
  - `serve_obs_ui()` ハンドラー（GET /）
  - `serve_admin_ui()` ハンドラー（GET /admin）
  - `serve_custom_css()` ハンドラー（GET /custom.css）
  - `sse_handler()` ハンドラー（GET /events）
  - `get_status()` ハンドラー（GET /api/status）
  - `initialize()` ハンドラー（POST /api/initialize）
  - `adjust()` ハンドラー（POST /api/adjust）
- **依存関係**: 2.2, 4.3, 5.1, 5.2（フロントエンドビルド成果物）
- **参照**: [実装詳細#HTTPサーバー](./2025-11-16-04実装詳細.md#4-http-サーバー)
- **備考**: 開発モードはVite dev serverへリダイレクト、本番モードはビルド成果物を組み込み

### 🟡 4.5 設定管理

- ✅ `src/config.rs` 作成
  - `Config` 構造体（OBS接続情報、モデルパス、クールダウン設定等）
  - TOML設定ファイル読み込み
  - デフォルト値サポート
- ✅ `config.example.toml` 作成（コメント付き設定テンプレート）
- **依存関係**: 2.2
- **備考**: TOML形式を採用（JSONではなく）。toml 0.8 使用。

### 🔴 4.6 メインエントリーポイント

- ✅ `src/main.rs` 更新
  - トレースログ初期化
  - clap によるコマンドライン引数パース (`--config`)
  - TOML設定ファイル読み込み
  - OBSCapture初期化
  - VictoryPredictor初期化
  - StateManager初期化
  - HTTPサーバー起動（axum）
  - 検知ループ（設定可能な間隔で画像取得→前処理→推論→記録）
- **依存関係**: 4.1, 4.2, 4.3, 4.4, 4.5
- **参照**: [実装詳細#リポジトリー構造](./2025-11-16-04実装詳細.md#リポジトリー構造)
- **備考**: 検知ループとHTTPサーバーを並行実行。エラーハンドリング実装済み。

---

## 5. フロントエンド実装（Svelte + TypeScript）

### 🔴 5.1 OBS用UI

- ✅ `frontend/src/obs/main.ts` 作成
- ✅ `frontend/src/obs/App.svelte` 作成
  - Svelte 5 ルーン方式（$state, $effect, $derived）
  - `tweened` ストアでカウントアップアニメーション
  - SSE接続（EventSource）で `/events` に接続
  - `counter-update` イベント受信→UI更新
  - Victory / Defeat のみ表示（drawは非表示）
  - 最終更新時刻 + 勝敗を表示
  - スタイリング（透明背景、CSS変数、テキストシャドウ）
- **依存関係**: 2.3, 3.1, 3.2
- **参照**: [実装詳細#OBS用UI](./2025-11-16-04実装詳細.md#5-obs-用-ui-svelte)

### 🔴 5.2 管理画面UI

- ✅ `frontend/src/admin/main.ts` 作成
- ✅ `frontend/src/admin/App.svelte` 作成
  - Svelte 5 ルーン方式（$state, $effect, $derived）
  - `tweened` ストアでカウントアップアニメーション
  - SSE接続（EventSource）で `/events` に接続
  - Victory / Defeat のみ表示（drawは非表示）
  - 最終更新時刻 + 勝敗を表示
  - 調整ボタン（+/-）→ POST /api/adjust
  - 初期化ボタン → POST /api/initialize
- **依存関係**: 2.3, 3.1, 3.2
- **参照**: [実装詳細#管理画面UI](./2025-11-16-04実装詳細.md#6-管理画面-ui-svelte)
- **備考**: localStorage永続化は将来追加予定

### 🟡 5.3 ui-config.json対応

- ⏳ OBS用UIでui-config.json読み込み
  - コンポーネント表示/非表示制御
  - レイアウト設定（orientation, fontSize, gap）
  - カラー設定
- **依存関係**: 5.1, 6.1
- **参照**: [実装詳細#ui-config.json仕様](./2025-11-16-04実装詳細.md#ui-configjson-仕様)

---

## 6. 設定ファイル・テンプレート

### 🟡 6.1 ui-config.json

- ⏳ `config/ui-config.json` 作成
  ```json
  {
    "components": {
      "victory": true,
      "defeat": true,
      "draw": true
    },
    "layout": {
      "orientation": "horizontal",
      "fontSize": 64,
      "gap": 20
    },
    "colors": {
      "victory": "#4caf50",
      "defeat": "#f44336",
      "draw": "#ff9800"
    }
  }
  ```
- **依存関係**: 2.1
- **参照**: [実装詳細#ui-config.json仕様](./2025-11-16-04実装詳細.md#ui-configjson-仕様)

### 🟡 6.2 custom.css

- ✅ `templates/custom.css` 作成（サンプルCSS）
  - 基本カラー設定
  - グロー効果サンプル
  - アニメーション効果サンプル
  - レイアウト変更サンプル
  - コメント付きで各種カスタマイズ例を記載
- **依存関係**: 2.1
- **参照**: [アーキテクチャ設計#カスタマイズ方法](../specs/ow2-victory-counter-rsアーキテクチャ設計.md#カスタマイズ方法)

### 🟡 6.3 エンドユーザー向けREADME

- ✅ `packages/ow2-victory-counter-rs/README.md` 作成
  - 必要環境（Windows 10/11、OBS Studio）
  - インストール手順
  - 起動方法
  - OBS設定（ブラウザーソース追加）
  - カスタマイズ方法（CSS、設定ファイル）
  - トラブルシューティング
  - 開発者向け情報
- **依存関係**: なし

---

## 7. モデル変換

### 🔴 7.1 ONNX変換スクリプト

- ✅ `packages/obs-victory-counter/victory-detector/scripts/convert_to_onnx.py` 作成
  - PyTorchモデル読み込み
  - ダミー入力作成（1, 3, 550, 995）
  - torch.onnx.export実行
  - label_map.json保存
  - 精度検証（PyTorch vs ONNX Runtime）
- **依存関係**: なし
- **参照**: [実装詳細#ONNX変換スクリプト](./2025-11-16-04実装詳細.md#onnx-変換スクリプト)
- **備考**: onnx, onnxruntime, onnxscript を依存関係に追加。PyTorchとONNXの出力が完全一致（差分0.000000）を確認。

### 🔴 7.2 ONNX変換実行

- ✅ PyTorchモデル→ONNX変換
  ```bash
  uv run python scripts/convert_to_onnx.py \
    --input artifacts/models/victory_classifier.pth \
    --output ../ow2-victory-counter-rs/models/victory_classifier.onnx
  ```
- ✅ `models/victory_classifier.label_map.json` 生成確認
- **依存関係**: 7.1
- **備考**: 5クラス分類モデル（defeat_progressbar, defeat_text, none, victory_progressbar, victory_text）。ONNX opset 18で変換。単一ファイル形式（.onnx のみ、407KB）で保存。

---

## 8. ビルド・パッケージング

### 🔴 8.1 フロントエンドビルド

- ⏳ OBS用UIビルド
  ```bash
  cd frontend/obs-ui
  pnpm install
  pnpm build  # dist/にHTML/JS/CSS生成
  ```
- ⏳ 管理画面UIビルド
  ```bash
  cd frontend/admin-ui
  pnpm install
  pnpm build  # dist/にHTML/JS/CSS生成
  ```
- **依存関係**: 5.1, 5.2
- **参照**: [実装詳細#ビルドプロセス](./2025-11-16-04実装詳細.md#ビルドプロセス)

### 🔴 8.2 Rust開発ビルド

- ⏳ 開発ビルド実行
  ```bash
  cd packages/ow2-victory-counter-rs
  cargo build
  ```
- **依存関係**: 4.1-4.6, 8.1

### 🔴 8.3 Rustリリースビルド

- ⏳ リリースビルド実行
  ```bash
  cargo build --release
  # target/release/ow2-victory-detector.exe生成
  ```
- **依存関係**: 8.1, 8.2
- **参照**: [実装詳細#ビルドプロセス](./2025-11-16-04実装詳細.md#ビルドプロセス)

### 🟡 8.4 配布物ZIP作成

- ⏳ 配布ディレクトリー構成作成
  ```
  ow2-victory-counter-rs/
  ├── ow2-victory-detector.exe
  ├── models/
  │   ├── victory_classifier.onnx
  │   └── victory_classifier.label_map.json
  ├── config/
  │   └── ui-config.json
  ├── templates/
  │   └── custom.css
  └── README.md
  ```
- ⏳ ZIP圧縮
- **依存関係**: 8.3, 6.1, 6.2, 6.3, 7.2
- **参照**: [アーキテクチャ設計#配布構成](../specs/ow2-victory-counter-rsアーキテクチャ設計.md#配布構成)

---

## 9. テスト・検証

### 🟡 9.1 単体テスト

- ⏳ StateManagerテスト（連続検知判定、状態遷移）
- ⏳ VictoryPredictorテスト（ダミー画像での推論）
- ⏳ OBSCaptureテスト（モック使用）
- **依存関係**: 4.1, 4.2, 4.3

### 🟡 9.2 結合テスト

- ⏳ OBS連携テスト（実際のOBSと接続）
- ⏳ SSE通信テスト（ブラウザーで受信確認）
- ⏳ REST APIテスト（curl使用）
- **依存関係**: 8.2

### 🟡 9.3 パフォーマンス測定

- ⏳ 処理時間計測（Base64デコード、CNN推論、SSE配信）
- ⏳ メモリ使用量計測
- ⏳ CPU使用率計測
- **依存関係**: 8.2
- **参照**: [アーキテクチャ設計#パフォーマンス特性](../specs/ow2-victory-counter-rsアーキテクチャ設計.md#パフォーマンス特性)

### 🟡 9.4 エンドツーエンドテスト

- ⏳ 実際のゲームプレイでのテスト
- ⏳ 勝敗判定精度確認
- ⏳ クールダウン機能確認
- ⏳ 永続化機能確認（管理画面でlocalStorage動作確認）
- **依存関係**: 8.3

---

## 10. ドキュメント整備

### 🟡 10.1 トラブルシューティングガイド

- ⏳ ONNX Runtimeエラー対処法
- ⏳ OBS WebSocket接続エラー対処法
- ⏳ フロントエンドビルドエラー対処法
- **依存関係**: 9.2, 9.4
- **参照**: [実装詳細#トラブルシューティング](./2025-11-16-04実装詳細.md#トラブルシューティング)

### 🟡 10.2 カスタマイズガイド

- ⏳ CSS編集方法（custom.css）
- ⏳ ui-config.json編集方法
- ⏳ 独自UI実装方法（/events API使用）
- **依存関係**: 6.1, 6.2
- **参照**: [アーキテクチャ設計#カスタマイズ方法](../specs/ow2-victory-counter-rsアーキテクチャ設計.md#カスタマイズ方法)

### 🟢 10.3 開発者向けドキュメント

- ⏳ コントリビューションガイド
- ⏳ コーディング規約
- ⏳ デバッグ方法まとめ
- **依存関係**: なし
- **参照**: [実装詳細#デバッグ方法](./2025-11-16-04実装詳細.md#デバッグ方法)

---

## 実装の推奨順序

1. **環境構築** (1.1, 1.2)
2. **リポジトリー構造** (2.1, 2.2, 2.3)
3. **Vite設定** (3.1, 3.2) ← 開発効率のため早期に
4. **Rust基盤実装** (4.3 StateManager → 4.4 HTTPサーバー)
5. **フロントエンド実装** (5.1, 5.2) ← ここまでで開発環境完成
6. **画像処理・推論** (7.1, 7.2, 4.1, 4.2)
7. **統合** (4.6 main.rs)
8. **テスト** (9.1, 9.2, 9.3, 9.4)
9. **ビルド・配布** (8.1, 8.2, 8.3, 8.4)
10. **ドキュメント** (6.3, 10.1, 10.2)

---

## 進捗管理

各タスク完了時に、この欄に完了日時と担当者を記載してください。

| タスクID | 完了日時 | 担当者 | 備考 |
| -------- | -------- | ------ | ---- |
| -        | -        | -      | -    |
