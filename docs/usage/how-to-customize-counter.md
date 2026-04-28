# OBS カウンターのカスタマイズ

このドキュメントでは、`ow2-victory-counter-rs` の OBS 表示を、ビルド環境なしでカスタマイズする方法を説明します。

編集するファイルは次の 3 つです。

- `assets/counter.html`
- `assets/counter.css`
- `assets/counter.js`

いずれもテキストエディターで編集できます。Node.js やフロントエンドのビルドは不要です。

編集前に、ひな形ファイルを `templates/` から `assets/` へコピーしてください。

## 仕組み

- `assets/counter.html`
  - OBS に表示する HTML の本文です
  - レイアウトや要素の並びを変更できます
- `assets/counter.css`
  - `assets/counter.html` に対して適用されるスタイルです
  - 色、余白、フォント、サイズ、配置などを変更できます
- `assets/counter.js`
  - カウンター値の反映やアニメーションなど、動きを変更できます

アプリケーション本体は `http://localhost:3000/` にアクセスされたとき、`assets/` 配下のこれらのファイルを読み込みます。  
ファイルを編集したあとは、OBS のブラウザーソースを再読込すると反映されます。

## 基本手順

1. `templates/counter.html`、`templates/counter.css`、`templates/counter.js` を `assets/` にコピーする
2. `assets/counter.html`、`assets/counter.css`、または `assets/counter.js` を開く
3. 見た目や配置を編集する
4. OBS でブラウザーソースを再読込する

OBS では次のどちらかで再読込できます。

- ブラウザーソースのプロパティを開いて OK を押す
- 「ソースが表示されたときにブラウザーの表示を更新する」を有効にして、表示を入れ直す

## `counter.html` で使える属性

値を表示したい要素には、次の `data-*` 属性を付けます。

### カウンター値

- `data-counter="victories"`
- `data-counter="defeats"`
- `data-counter="draws"`

### 補助情報

- `data-meta="winrate"`
- `data-meta="last-updated"`
- `data-meta="last-outcome"`

同じ属性を複数の要素に付けても構いません。すべて同じ値で更新されます。

## 最小サンプル

```html
<main>
  <div>
    <span>Victory</span>
    <strong data-counter="victories">0</strong>
  </div>
  <div>
    <span>Defeat</span>
    <strong data-counter="defeats">0</strong>
  </div>
  <div>
    <span>Winrate</span>
    <strong data-meta="winrate">0%</strong>
  </div>
</main>
```

この HTML に対して `counter.css` を好きなように書けば、シンプルなカウンターから装飾の強い表示まで自由に調整できます。動きを変えたい場合は `counter.js` を編集します。

## 動きを変更する場合

`counter.js` では、サーバーから受け取った勝敗数を HTML に反映しています。

- `/api/status` で初期値を取得します
- `/events` で更新を受け取ります
- `data-counter` や `data-meta` が付いた要素へ値を反映します
- 数値が変わったときは `playBump` でアニメーションします

アニメーションだけ変えたい場合は、まず `playBump` の中身を調整してください。

## レイアウト変更例

縦並びにしたい場合の例です。

```html
<main class="stacked-counter">
  <section class="stacked-counter__item">
    <span class="stacked-counter__label">Victory</span>
    <strong class="stacked-counter__value" data-counter="victories">0</strong>
  </section>
  <section class="stacked-counter__item">
    <span class="stacked-counter__label">Defeat</span>
    <strong class="stacked-counter__value" data-counter="defeats">0</strong>
  </section>
</main>
```

```css
body {
  margin: 0;
  background: transparent;
}

.stacked-counter {
  display: grid;
  gap: 16px;
  justify-items: start;
  padding: 40px;
  color: white;
}

.stacked-counter__item {
  padding: 12px 20px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.55);
}

.stacked-counter__value {
  font-size: 72px;
}
```

## 注意点

- JavaScript はユーザーが編集する前提ではありません
- `counter.html` は HTML 全体ではなく本文として読み込まれます
  - `<!DOCTYPE html>` や `<html>`、`<head>`、`<body>` は書かないでください
- `data-counter` や `data-meta` が無い要素は自動更新されません
- 知らない属性値は無視されます
- `counter.js` を壊すとカウンター値が更新されなくなることがあります

## 壊したときの戻し方

- `assets/counter.html`
- `assets/counter.css`
- `assets/counter.js`

を配布時の内容に戻してください。  
元に戻したいときは、`templates/` にあるひな形を再度 `assets/` にコピーしてください。どちらか片方だけ壊しても、もう片方が残っていればアプリ自体は動作します。
