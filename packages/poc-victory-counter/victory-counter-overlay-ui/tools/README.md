# tools ディレクトリーについて

このディレクトリーは、`victory-counter-overlay-ui` の開発・配布を補助するスクリプトを配置するための場所です。現在の構成は以下の通りです。

- `copy-overlay.mjs`  
  `npm run package-overlay` から呼び出され、`npm run build` で生成された `dist/` ディレクトリーを Victory Detector 側（`packages/obs-victory-counter/victory-detector/static/overlay/`）へコピーします。OBS から Python スクリプト経由で静的ファイルを配布する際に利用します。

## 使用方法

```bash
npm run package-overlay
```

1. `npm run build` を実行して `dist/` を生成します。
2. `tools/copy-overlay.mjs` が `dist/` の内容を削除→再作成された `victory-detector/static/overlay/` にコピーします。

`dist/` が存在しない場合はエラーが表示されるため、先に `npm run build` を実行してください。

## 今後の追加について

配信者向け配布パッケージの作成や自動配布に関する補助スクリプトも、このディレクトリーに追加する方針です。新しいスクリプトを追加する場合は、この README を更新し、目的と使い方を追記してください。
