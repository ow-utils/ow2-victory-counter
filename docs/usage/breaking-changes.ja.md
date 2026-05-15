# Breaking Changes

本ツールのバージョンアップに伴い、利用者の作業（設定変更・ファイル移行など）が必要となる変更を記録します。

リリースノート（[GitHub Releases](https://github.com/ow-utils/ow2-victory-counter/releases)）と併せて参照してください。新しいバージョンが上にあります。

## 未リリース

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
