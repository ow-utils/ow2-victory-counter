# Repository Guidelines

## 原則・共通ルール

- 応答やドキュメント、コミットメッセージ、ソースコード中のコメント、要求や仕様を記述したファイル名など、自然言語を用いる箇所では、特に指定が無い限り日本語を使用する

## ディレクトリー構成

リポジトリーは以下の 2 つのサブプロジェクトと、共通ドキュメント類で構成されます。

- `ow2-victory-counter-rs/` : 本体（Rust + フロントエンド）。詳細は同ディレクトリーの `README.md` を参照。
- `ow2-victory-trainer/` : 勝敗判定モデルの学習プロジェクト（Python）。詳細は同ディレクトリーの `README.md` を参照。

`docs/` には全体に関係するドキュメントを置きます。

- `docs/usage/` : エンドユーザー向けドキュメント。リリースZIPに同梱される(`.github/workflows/package.yml` 参照)。
- `docs/assets/pandoc/` : リリース時にMarkdown→HTML変換で利用するテンプレート。
- `docs/architecture.md` : 実装されている動作・設計を記述。実装変更時に追従する。
- `docs/release.md` : リリース手順。
- `docs/roadmap.md` : 将来構想・未着手項目。着手したものはここから外し、確定仕様は `architecture.md` に反映する。
- `docs/*.md` のその他 : 技術ノート(ONNX関連など)。

`logs/` には、学習作業など時系列で残したい手動の作業ログを置きます。普遍的なナレッジは `docs/` 側に置いてください。

## コミットとプルリクエスト指針

コミットメッセージは`type: summary`形式（例: `feat: add hero roster importer`）で要約し、1コミット1責務を意識します。PR本文には目的、主要変更点、テスト結果、関連Issueのリンクを箇条書きで記載し、UI変更がある場合はスクリーンショットやGIFを添付してください。レビューを円滑にするため、ドラフト状態で早期に共有し、説明が必要な箇所には該当コードへのインラインコメントを追加してください。ただし、コードを読めば自明なコメントを書くのは避けてください。

## セキュリティと設定メモ

APIキーなど機密情報はコードにハードコードせず、`.env.example`にダミー値のみを記載します。実値はローカル`.env`（`.gitignore`対象とし、`.env.example`以外の`.env*`をコミットしない）または CI のシークレットストアで管理してください。GitHub の Secret Scanning と Push Protection を有効化し、漏えい時の検知と push ブロックを担保します。CI からクラウドサービスへアクセスする場合は、長期APIキーよりも OIDC による短期トークン（GitHub Actions の OIDC + クラウド側 STS など）を優先し、本番稼働コードは可能な限り Secrets Manager / Vault などのシークレットストア経由で取得します。鍵は有効期限とローテーション手順を明確にしてください。依存更新時は各サブプロジェクトの慣習に従って脆弱性スキャンを実施します（Rust: `cargo audit`、Python: `pip-audit` または `uv pip list --outdated`、Node: `pnpm audit`）。ネットワークに依存するテストにはモックを使って再現性を確保してください。

## プログラミング言語(等)ごとの指針

### Markdownファイル

- ファイル編集後は `prettier` で整形します

### Python

- `uv` を用いてパッケージ管理を行います
- `black` を用いて整形します

### Rust (`ow2-victory-counter-rs/`)

- edition は `2024` を使用します
- `cargo fmt` で整形し、`cargo clippy -- -D warnings` で警告ゼロを維持します
- 設定ファイル（`rustfmt.toml`, `clippy.toml`）は置かず、ツールチェインのデフォルトに従います

### フロントエンド (`ow2-victory-counter-rs/frontend/`)

- パッケージマネージャは pnpm を使用します（`pnpm-lock.yaml` をコミット）
- ビルド・開発サーバーは Vite (`pnpm dev` / `pnpm build`)
- TypeScript + Svelte 5 構成です
