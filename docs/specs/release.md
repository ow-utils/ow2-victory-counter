# リリース手順

GitHub Actions によるタグベースの自動リリースで配布物を作成する。

## バージョニング規則

| 対象   | タグパターン                     | 例             | ワークフロー        |
| ------ | -------------------------------- | -------------- | ------------------- |
| アプリ | `v<major>.<minor>.<patch>`       | `v0.4.0`       | `package.yml`       |
| モデル | `model-v<major>.<minor>.<patch>` | `model-v1.0.0` | `model-release.yml` |

アプリとモデルは独立したリリースサイクルを持つ。アプリリリースには、その時点の最新モデルがデフォルトとして同梱される。

## アプリリリース

### 前提条件

- リリース対象の変更が main ブランチにマージ済み
- ローカルで動作確認済み

### 手順

```bash
git checkout main
git pull
git tag v0.4.0
git push origin v0.4.0
```

タグの push をトリガーに `package.yml` が自動実行される。

### 配布物の内容

| ファイル                      | 説明                                          |
| ----------------------------- | --------------------------------------------- |
| `ow2-victory-detector.exe`    | アプリ本体                                    |
| `*.dll`                       | 依存ライブラリ                                |
| `models/`                     | デフォルトの判定モデル（ONNX + ラベルマップ） |
| `templates/`                  | OBS表示テンプレート                           |
| `frontend/dist/`              | 管理画面フロントエンド                        |
| `config.example.toml`         | 設定ファイルのサンプル                        |
| `debug.bat`                   | デバッグ起動用バッチ                          |
| `利用方法.html`               | エンドユーザー向けドキュメント                |
| `how-to-customize-counter.md` | カスタマイズガイド                            |

### 確認

GitHub Releases ページに `ow2-victory-counter-rs.zip` が添付されたリリースが作成される。

## モデルリリース

### 前提条件

- 再学習が完了し、ONNX に変換済み
- `packages/ow2-victory-counter-rs/models/` にモデルファイルを配置済み
- 変更をコミット・push 済み

### 手順

```bash
git tag model-v1.0.0
git push origin model-v1.0.0
```

タグの push をトリガーに `model-release.yml` が自動実行される。

### 配布物の内容

| ファイル                                   | 説明         |
| ------------------------------------------ | ------------ |
| `models/victory_classifier.onnx`           | 判定モデル   |
| `models/victory_classifier.label_map.json` | ラベルマップ |

### 確認

GitHub Releases ページに `[モデル] victory_classifier model-vX.Y.Z` という名前で `victory-classifier-models.zip` が添付されたリリースが作成される。

## 手動実行（workflow_dispatch）

タグを打たずに GitHub Actions の画面から手動で実行することもできる。

1. GitHub リポジトリの Actions タブを開く
2. 左のワークフロー一覧から「配布パッケージ生成」または「モデル配布」を選択
3. 「Run workflow」ボタンからブランチを選んで実行

手動実行の場合、アーティファクトのみ生成される（GitHub Release は作成されない）。
