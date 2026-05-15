# Breaking Changes

本ツールのバージョンアップに伴い、利用者の作業（設定変更・ファイル移行など）が必要となる変更を記録します。

リリースノート（[GitHub Releases](https://github.com/ow-utils/ow2-victory-counter/releases)）と併せて参照してください。新しいバージョンが上にあります。

## v0.4.0

### モデルディレクトリー構造の言語別化

- **変更内容**: モデルファイルの配置を `models/victory_classifier.onnx` から `models/<lang>/victory_classifier.onnx` へ変更しました（`ja` / `en` の言語別配置）。
- **影響**: 既存の `config.toml` の `[model]` セクションの設定値（`model_path` / `label_map_path`）がそのままでは動作しません。
- **対応**: 配布ZIPに含まれる `config.example.toml` を参考に、`models/ja/...` または `models/en/...` の形式に書き換えてください。
  - 日本語版の場合:
    ```toml
    [model]
    model_path = "models/ja/victory_classifier.onnx"
    label_map_path = "models/ja/victory_classifier.label_map.json"
    ```
  - 英語版の場合:
    ```toml
    [model]
    model_path = "models/en/victory_classifier.onnx"
    label_map_path = "models/en/victory_classifier.label_map.json"
    ```
- **背景**: ゲームの表示言語に応じて最適なモデルを選択できるようにするための変更です。

## v0.1.0

### 画像前処理パラメーターの変更

- **変更内容**: オーバーウォッチの仕様変更に伴い、学習対象が変わったため `config.toml` の `[preprocessing]` セクションの値が変更になりました。
- **影響**: 旧バージョンの `config.toml` をそのまま使用すると、勝敗判定が正しく動作しません。
- **対応**: `config.toml` の `[preprocessing]` セクションを以下の値に更新してください。
  ```toml
  [preprocessing]
  # 画像前処理設定
  # クロップ領域: [x, y, width, height]
  # 1920x1080 解像度での勝敗表示の標準的な位置
  crop_rect = [42, 156, 245, 108]
  # モデル入力サイズ（ONNXエクスポート時の height/width と一致させる）
  resize_width = 245
  resize_height = 108
  ```
