# ビルド手順（Windows 環境）

このドキュメントでは、Windows 環境で ow2-victory-counter-rs をビルドする手順を説明します。

---

## 前提条件

### 必須ソフトウェア

#### 1. Rust（1.70 以上）

**インストール方法**:

1. [https://rustup.rs/](https://rustup.rs/) にアクセス
2. `rustup-init.exe` をダウンロードして実行
3. デフォルト設定でインストール

**確認コマンド**:
```powershell
rustc --version
cargo --version
```

**期待される出力例**:
```
rustc 1.83.0 (90b35a623 2024-11-26)
cargo 1.83.0 (5ffbef321 2024-10-29)
```

---

#### 2. Node.js（18.x 以上）

**インストール方法**:

1. [https://nodejs.org/](https://nodejs.org/) にアクセス
2. LTS 版（推奨）をダウンロードしてインストール

**確認コマンド**:
```powershell
node --version
```

**期待される出力例**:
```
v20.18.1
```

---

#### 3. pnpm（8.x 以上）

**インストール方法**:

Node.js インストール後、PowerShell で以下を実行：

```powershell
npm install -g pnpm
```

**確認コマンド**:
```powershell
pnpm --version
```

**期待される出力例**:
```
9.15.1
```

---

## ビルド手順

### 1. リポジトリのクローン

```powershell
git clone https://github.com/your-repo/ow2.git
cd ow2/packages/ow2-victory-counter-rs
```

---

### 2. フロントエンドのビルド

#### 2.1 依存関係のインストール

```powershell
cd frontend
pnpm install
```

**期待される出力**:
```
Packages: +XXX
++++++++++++++++++++++++++++++++++++++++++++++++++++++
Progress: resolved XXX, reused XXX, downloaded 0, added XXX, done
```

#### 2.2 ビルド実行

```powershell
pnpm build
```

**期待される出力**:
```
vite v7.0.0 building for production...
✓ XXX modules transformed.
dist/obs.html               X.XX kB
dist/admin.html             X.XX kB
dist/assets/obs-XXX.js      XX.XX kB │ gzip: XX.XX kB
dist/assets/admin-XXX.js    XX.XX kB │ gzip: XX.XX kB
✓ built in XXXms
```

#### 2.3 ビルド成果物の確認

```powershell
dir dist
```

以下のファイルが生成されていることを確認：
- `obs.html`
- `admin.html`
- `assets/` ディレクトリ（JS/CSS ファイル）

---

### 3. Rust のビルド

#### 3.1 プロジェクトルートに戻る

```powershell
cd ..  # packages/ow2-victory-counter-rs に戻る
```

#### 3.2 開発ビルド（デバッグ用、高速）

```powershell
cargo build
```

**期待される出力**:
```
   Compiling ow2-victory-detector v0.1.0
    Finished `dev` profile [unoptimized + debuginfo] target(s) in XXs
```

**成果物**: `target/debug/ow2-victory-detector.exe`

---

#### 3.3 リリースビルド（本番用、最適化）

```powershell
cargo build --release
```

**期待される出力**:
```
   Compiling ow2-victory-detector v0.1.0
    Finished `release` profile [optimized] target(s) in XXs
```

**成果物**: `target/release/ow2-victory-detector.exe`

---

### 4. ONNXモデルの配置確認

以下のファイルが存在することを確認：

```powershell
dir models
```

**必要なファイル**:
- `models/victory_classifier.onnx` (約 407KB)
- `models/victory_classifier.label_map.json`

**注意**: これらのファイルはリポジトリに含まれています。もし存在しない場合は、[モデル変換手順](../plans/_TODO.md#7-モデル変換) を参照してください。

---

### 5. 設定ファイルの準備

#### 5.1 config.toml の作成

```powershell
copy config.example.toml config.toml
```

#### 5.2 config.toml の編集

エディターで `config.toml` を開き、以下を設定：

```toml
[obs]
host = "localhost"  # Windows 環境では localhost でOK
port = 4455
# password = "your-password"  # OBS WebSocket にパスワードを設定した場合
source_name = "ゲーム画面"  # OBS のソース名に変更

[model]
model_path = "models/victory_classifier.onnx"
label_map_path = "models/victory_classifier.label_map.json"

[preprocessing]
crop_rect = [465, 530, 990, 550]  # 勝敗表示の領域（要調整）

[state]
cooldown_seconds = 10
required_consecutive = 3

[server]
host = "127.0.0.1"
port = 3000

[detection]
interval_ms = 1000
```

---

## ビルド成果物の確認

すべてのビルドが完了したら、以下のファイルが存在することを確認してください：

```
ow2-victory-counter-rs/
├── target/
│   └── release/
│       └── ow2-victory-detector.exe  ← 実行ファイル（リリースビルド）
├── frontend/
│   └── dist/
│       ├── obs.html
│       ├── admin.html
│       └── assets/
├── models/
│   ├── victory_classifier.onnx
│   └── victory_classifier.label_map.json
├── templates/
│   └── custom.css
└── config.toml  ← 設定ファイル（自分で作成）
```

---

## トラブルシューティング

### Rust コンパイルエラー

#### エラー: "error: linker `link.exe` not found"

**原因**: Visual Studio Build Tools がインストールされていない

**解決策**:
1. [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/) をダウンロード
2. 「C++ によるデスクトップ開発」をインストール
3. PC を再起動
4. `cargo build` を再実行

---

#### エラー: "error: could not find `Cargo.toml`"

**原因**: 間違ったディレクトリで実行している

**解決策**:
```powershell
cd packages/ow2-victory-counter-rs
```

---

### フロントエンドビルドエラー

#### エラー: "pnpm: command not found"

**原因**: pnpm がインストールされていない、またはPATHが通っていない

**解決策**:
```powershell
npm install -g pnpm
```

PowerShell を再起動して再実行

---

#### エラー: "vite: command not found"

**原因**: node_modules がインストールされていない

**解決策**:
```powershell
cd frontend
pnpm install
pnpm build
```

---

### ONNX モデルが見つからない

#### エラー: "No such file or directory: models/victory_classifier.onnx"

**原因**: ONNX モデルファイルが存在しない、またはパスが間違っている

**解決策**:

1. ファイルが存在するか確認：
   ```powershell
   dir models
   ```

2. 存在しない場合は、PyTorch モデルから変換：
   ```bash
   # WSL2 または Linux 環境で実行
   cd packages/obs-victory-counter/victory-detector
   uv run python scripts/convert_to_onnx.py \
     --input artifacts/models/victory_classifier.pth \
     --output ../ow2-victory-counter-rs/models/victory_classifier.onnx
   ```

3. 生成されたファイルを Windows 側にコピー

---

## 次のステップ

ビルドが完了したら、[実行手順](./run.md) に進んでください。
