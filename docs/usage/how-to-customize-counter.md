# OBS カウンターのカスタマイズ

このドキュメントでは、`ow2-victory-counter-rs` の OBS 表示を、ビルド環境なしでカスタマイズする方法を説明します。

編集するファイルは次の 4 つです。

- `assets/counter.html`
- `assets/counter.css`
- `assets/counter.js`
- `assets/preview.html`（ブラウザだけで表示確認するためのファイル）

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
- `assets/preview.html`
  - ブラウザだけで表示確認するためのファイルです（アプリや OBS を起動しなくても見た目を確認できます）
  - 内部に `COUNTER_HTML` という JavaScript の定数で **`counter.html` と同じ DOM 構造をコピー保持** しています
  - そのため `counter.html` の構造（タグや属性）を変更したときは、この定数も同じ構造に書き換えないとプレビューに反映されません
  - 色や余白を変えただけ（`counter.css` だけ編集）の場合は、`preview.html` を編集する必要はありません

アプリケーション本体は `http://localhost:3000/` にアクセスされたとき、`assets/counter.html`、`assets/counter.css`、`assets/counter.js` を読み込みます。`assets/preview.html` はアプリ本体からは使われず、ブラウザで直接開いたときだけ使われます。  
ファイルを編集したあとは、OBS のブラウザーソースを再読込すると反映されます。

## 基本手順

1. `templates/` 配下のファイルを `assets/` にコピーする（`counter.html` / `counter.css` / `counter.js` / `preview.html` の 4 つすべて）
2. `assets/counter.html`、`assets/counter.css`、または `assets/counter.js` を開く
3. 見た目や配置を編集する
4. `counter.html` の構造を変えた場合は、`assets/preview.html` の `COUNTER_HTML` 定数も同じ構造に書き換える（[counter.html を変更したとき](#counterhtml-を変更したとき) 参照）
5. プレビューで確認する（次のセクション参照）
6. OBS でブラウザーソースを再読込する

OBS では次のどちらかで再読込できます。

- ブラウザーソースのプロパティを開いて OK を押す
- 「ソースが表示されたときにブラウザーの表示を更新する」を有効にして、表示を入れ直す

## ブラウザーだけで動作確認する

`assets/preview.html` をブラウザーで直接開くと、アプリケーションや OBS を起動しなくてもカウンターの表示を確認できます。

### できること

- **+ Victory / + Defeat** ボタンでカウンターを増減できます。数値変更時のアニメーションも動作します
- **Reset** ボタンでカウンターを 0 に戻せます
- **背景色の切り替え**（4 種）で、暗い背景・寒色・暖色・明るい背景それぞれでの視認性を確認できます

### 使い方

1. `assets/preview.html` をブラウザーで開く
2. ボタンを押してカウンターの見た目やアニメーションを確認する
3. `assets/counter.css` などを編集し、ブラウザーをリロードする
4. 納得できたら OBS で最終確認する

## `counter.html` を変更したとき

`preview.html` はブラウザだけで動かす都合上、`counter.html` のファイル内容を読み込めません。代わりに **`preview.html` の中に同じ DOM 構造を JavaScript の文字列定数（`COUNTER_HTML`）としてコピー保持** しています。

そのため、`counter.html` のタグ構成や `data-*` 属性、クラス名などを変更したときは、`preview.html` 内 `COUNTER_HTML` も同じ内容に揃えてください。揃えないとプレビューだけ旧構造のまま表示され、本番（OBS）と食い違います。

### 編集箇所

`assets/preview.html` を開くと、`<script>` ブロックの先頭付近に次のような箇所があります。

```javascript
const COUNTER_HTML = `
  <div class="counter-container">
    <div class="scoreboard">
      ...
    </div>
  </div>
`;
```

このバッククォート（`` ` ``）で囲まれた範囲を、`counter.html` の本文と同じ内容に書き換えます。

### 守るべきこと

- バッククォート（`` ` ``）と `const COUNTER_HTML = ` および末尾の `;` は **削除しないでください**
- HTML 内に `` ` `` や `${` を含めるとエスケープが必要になります。通常のカウンター用 HTML であれば気にしなくて構いません
- `data-counter` や `data-meta`、`data-style` などの属性は `counter.html` と同じものを必ず付けてください（プレビューで値が反映されなくなります）
- 編集対象は `<script>` 内の `COUNTER_HTML` 定数だけです。`preview.html` のそれ以外（プレビュー用 UI、ボタン、iframe ロジックなど）は触らないでください

### 編集が不要なケース

次の場合は `preview.html` を編集する必要はありません。

- `counter.css` だけ編集して色・余白・サイズなどを変えた
- `counter.js` のアニメーションだけ調整した
- `counter.html` の **構造は変えず**、テキスト（例: `Victory` → `WIN`）だけ変えた場合も、構造が一致していれば必須ではありません（ただし揃えておくとプレビューの見た目が本番に近くなります）

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

## AI に編集してもらう場合

HTML / CSS / JavaScript に詳しくない場合でも、Claude Desktop や ChatGPT などの AI に依頼してカスタマイズできます。

Claude Desktop や Claude Code Desktop など、ローカルファイルを直接編集できる AI ツールを使う場合は、配布フォルダーをワークスペースとして開き、`assets/` 内のファイルだけを編集対象にしてください。無料プランで使える範囲やローカルファイル編集の可否はサービス側で変わることがあるため、使っている AI ツールの画面や公式案内で確認してください。

ローカルファイルを直接編集できない AI ツールを使う場合は、このセクションの依頼文にファイル内容を貼り付け、AI が出した内容を自分で `assets/` のファイルへ反映してください。

### 先にやること

まず、ひな形を `assets/` にコピーします。

- `templates/counter.html` → `assets/counter.html`
- `templates/counter.css` → `assets/counter.css`
- `templates/counter.js` → `assets/counter.js`
- `templates/preview.html` → `assets/preview.html`

AI には、基本的に `assets/` 側のファイルを編集してもらいます。

ローカルファイルを直接編集できる AI ツールに依頼する場合は、次の点を伝えてください。

- 配布フォルダーをワークスペースとして開いていること
- 編集してよいのは `assets/counter.html`、`assets/counter.css`、`assets/counter.js`、`assets/preview.html` の 4 つだけであること
- `templates/` は復旧用のひな形なので編集しないこと
- `counter.html` の構造（タグ・クラス・`data-*` 属性）を変更した場合は、`preview.html` 内の `COUNTER_HTML` 定数も同じ構造に揃えること

### AI に伝える内容

AI に依頼するときは、次の情報を渡すと意図が伝わりやすくなります。

- どういう見た目にしたいか
- 画面のどこに表示したいか
- 色、サイズ、余白、フォントの希望
- アニメーションを変えたいか
- 変更してよいファイル
- 現在の `counter.html` / `counter.css` / 必要なら `counter.js` の内容

### 依頼文の例

```text
OBS のブラウザーソースで表示する勝敗カウンターをカスタマイズしたいです。

変更してよいファイルは次の 4 つです。
- assets/counter.html
- assets/counter.css
- assets/counter.js
- assets/preview.html

条件:
- ビルド環境は使いません
- assets/ 以外のファイルは変更しないでください
- templates/ は復旧用のひな形なので編集しないでください
- counter.html は body の中身だけです。html/head/body タグは書かないでください
- data-counter="victories" と data-counter="defeats" は残してください
- data-meta="winrate" は勝率表示に使います
- data-style="winrate-width" は勝率バーの幅更新に使います
- JavaScript を変更する場合も /api/status と /events の取得処理は壊さないでください
- counter.html の構造を変更した場合は、preview.html 内の COUNTER_HTML 定数も同じ構造に書き換えてください
  - 場所: preview.html の <script> ブロック内、`const COUNTER_HTML = \`...\`;` という箇所
  - 書き換えるのはバッククォート（`）で囲まれた中身だけです
  - `const COUNTER_HTML = ` の宣言部分、末尾の `;`、preview.html のそれ以外（ボタン UI や iframe 制御スクリプト）は触らないでください

やりたいこと:
- ここに希望を書く
- 例: カウンターを画面左下に小さく表示したい
- 例: 数値が増えたときに一瞬光るようにしたい

以下が現在のファイル内容です。

--- counter.html ---
ここに assets/counter.html の内容を貼る

--- counter.css ---
ここに assets/counter.css の内容を貼る

--- counter.js ---
動きを変えたい場合だけ、ここに assets/counter.js の内容を貼る

--- preview.html ---
counter.html の構造を変える場合だけ、ここに assets/preview.html の内容を貼る
```

ローカルファイルを直接編集できない AI ツールに依頼する場合は、必ず「変更後のファイル全体を出してください」と伝えてください。  
一部分だけの差分だと、貼り付ける場所を間違えやすくなります。

おすすめの依頼:

```text
変更後の counter.html、counter.css、必要なら counter.js を、それぞれファイル全体で出してください。
counter.html の構造を変えた場合は、preview.html の COUNTER_HTML 定数を更新したものもファイル全体で出してください。
説明は短くてよいです。
```

### 反映手順

1. AI が出した内容を `assets/counter.html`、`assets/counter.css`、`assets/counter.js`、（必要なら）`assets/preview.html` に反映する
2. `assets/preview.html` をブラウザで開いて、見た目とアニメーションを確認する
3. OBS のブラウザーソースを再読込する
4. 表示が崩れていないか確認する
5. 管理画面でカウントを増減して、値更新やアニメーションを確認する

### 壊れた場合

表示されない、値が更新されない、画面が真っ白になる場合は、`templates/` のひな形を `assets/` にコピーし直してください（`preview.html` も含めて 4 ファイルすべて）。

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
- `counter.html` と `preview.html` 内 `COUNTER_HTML` 定数は **手作業で同期** する必要があります
  - 同期が崩れていても OBS 表示には影響しません（OBS は `counter.html` だけを読みます）
  - プレビュー画面だけが旧構造のまま表示されるため、見た目と実物が食い違って混乱の元になります
- カスタマイズによってカウンターの表示寸法が変わった場合は、OBS のブラウザーソースの **幅・高さ設定** も合わせて見直してください
  - デフォルトレイアウトの推奨サイズは `640x400` です
  - パネルが大きくなるカスタマイズ（フォント拡大・要素追加・余白拡大など）をした場合は、内容が収まるサイズに広げる必要があります
  - 逆にコンパクトにした場合は、無駄な透明領域を減らすためサイズを縮めると OBS の合成負荷を抑えられます
  - 確認方法: OBS のブラウザーソース設定で **「現在のページを再読み込み」** を押し、プレビュー上で内容が見切れたり余白が広すぎたりしないかを目視チェック

## 壊したときの戻し方

- `assets/counter.html`
- `assets/counter.css`
- `assets/counter.js`
- `assets/preview.html`

を配布時の内容に戻してください。  
元に戻したいときは、`templates/` にあるひな形を再度 `assets/` にコピーしてください。一部だけ壊しても、残ったファイルがあればアプリ自体は動作します（`preview.html` を消した・壊した場合はブラウザでのプレビューだけが使えなくなり、OBS 表示には影響しません）。
