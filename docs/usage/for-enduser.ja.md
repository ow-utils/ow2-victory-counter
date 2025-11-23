# OW2 Victory Counter

Overwatch 2 の勝敗を自動カウントして OBS に表示するツールです。CNN（深層学習）で勝敗画面を検知し、リアルタイムでカウントを更新します。

CSSの知識があればある程度デザインをカスタマイズすることが可能です。

## リンク

つぎのURLをブックマークしておくと便利です:

- [エンドユーザー向けドキュメント](https://github.com/ow-utils/ow2-victory-counter/blob/main/docs/usage/for-enduser.ja.md): 本ファイルをWebで見られます
- [adminページ](http://localhost:3000/admin): このプログラムの管理画面です
  - 開けるのはプログラム実行中のみです
  - 設定でポートを変更した場合はこのページのポート番号も変わります

## セットアップ

### 実行ファイルのダウンロード

[Releases](https://github.com/ow-utils/ow2-victory-counter/releases) から最新版のをダウンロードし、適当なディレクトリーに展開します。

### 設定ファイルの準備

`config.example.toml` を `config.toml` にリネーム(あるいはコピー)して編集します。

**必須設定項目**:

```toml
[obs]
source_name = "ゲームキャプチャ" # OW2をキャプチャしているOBSのソース名
```

**"ゲームキャプチャ"** の部分を、あなたのOBS設定に合わせて更新してください。
なお、ソースは1920x1080など16:9のアスペクト比であることを前提としています。

### OBS WebSocketの有効化

1. OBS Studio を起動
2. `ツール` → `WebSocket サーバー設定` を開く
3. `WebSocket サーバーを有効にする` にチェック
4. ポート番号を確認（デフォルト: 4455）
5. パスワードを設定した場合は `config.toml` の `obs > port` 設定値も合わせて変更します

```toml
[obs]
password = "your-password"  # パスワード設定時のみ
```

## 使い方

#### ツールの起動

`ow2-victory-detector.exe` をダブルクリックして起動してください。

画面がすぐに閉じてしまう場合は設定に誤りがあります。
後述の「トラブルシューティング」を参照してください。

#### OBS にブラウザーソースを追加

1. OBS で `ソース` → `+` → `ブラウザ` を選択
2. 以下の設定を入力:
   - **URL**: `http://localhost:3000/`
   - (幅、高さは適当に調整してください)
   - ☑ **シーンがアクティブになったときにブラウザの表示を更新する**

3. OKをクリック

カウンターが表示されます！

`ow2-victory-detector.exe` をあとから起動した場合などカウンターが表示されない場合は目玉アイコン(表示/非表示切り替えアイコン)を押して表示を更新してみて下さい。

#### 管理画面でカウントを確認

ブラウザーで `http://localhost:3000/admin` を開くと、管理画面が表示されます。

機能:

- 現在のカウント表示
- `+` / `-` ボタンで手動調整
- `リセット` ボタンで全カウントをゼロに

## カスタマイズ

※ 本機能は開発中であり、未テストです。また、仕様も今後大きく変わる可能性があります。

### CSS でスタイル変更

`templates/custom.css` を編集して見た目をカスタマイズできます：

```css
/* 色を変更 */
.counter-grid {
  --victory-color: #00ff00;
  --defeat-color: #ff0000;
  --font-size: 96px;
}

/* グロー効果 */
.value {
  text-shadow: 0 0 20px currentColor;
}
```

OBS のブラウザーソースで `カスタムCSS` に以下を追加:

```css
@import url("http://localhost:3000/custom.css");
```

## トラブルシューティング

### `ow2-victory-detector.exe` をダブルクリックして起動してもすぐに閉じてしまう

同じディレクトリーにある `debug.bat` をダブルクリックして起動してください。
エラー情報が表示されると思います。

### Error: FileRead("config.toml", "指定されたファイルが見つかりません。 (os error 2)")

**設定ファイルの準備** セクションを参照してください。
`config.template.toml` をリネームして `config.toml` ファイルを作成する必要があります。

### Error: ObsConnection("failed to connect to the obs-websocket plugin")

OBS Studio が起動していないか、起動していたとしてもWebSocketサーバーが有効化されていません。

**OBS WebSocketの有効化** セクションを参照してください。

### Failed to capture image: OBS capture error: API error: ResourceNotFound

オーバーウォッチ2をキャプチャーしているソース名の設定が間違っています。

**設定ファイルの準備** セクションを参照してください。
`config.toml` ファイル `source_name` の値を、あなたの環境に合わせて編集する必要があります。
