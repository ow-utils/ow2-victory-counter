# Victory Detector API

このドキュメントは `victory-detector` が提供するローカル HTTP API の仕様をまとめたものです。  
すべてのエンドポイントは `http://127.0.0.1:8912` を基点に提供されます。開発・配信用にローカルでのみ動作させる想定のため、認証は実装しません。

## 共通事項

- `Content-Type` はリクエスト／レスポンスともに `application/json` を利用します。
- エラー時は `{"error": "<reason>"}` 形式の JSON を返し、HTTP ステータスで詳細を示します。
- オーバーレイ UI からアクセスできるよう、すべてのレスポンスに `Access-Control-Allow-Origin: *` を付与しています。

## `GET /state`

最新の勝敗カウントとイベント情報を返します。

### レスポンス

```jsonc
{
  "victories": 12,
  "defeats": 8,
  "total": 20,
  "results": [
    {
      "type": "result",
      "value": "victory",
      "delta": 1,
      "confidence": 0.92,
      "timestamp": "2025-01-01T12:34:56Z",
    },
  ],
  "adjustments": [
    {
      "type": "adjustment",
      "value": "defeat",
      "delta": 1,
      "timestamp": "2025-01-01T13:00:00Z",
      "note": "manual fix",
    },
  ],
}
```

- `results` と `adjustments` は最新イベントを時系列順に格納します。
- 信頼度 (`confidence`) は自動判定イベントにのみ含まれます。

## `GET /history`

イベントログの直近 N 件を返します。クエリ `limit` で件数を指定できます（既定値 10、最大値は実装に依存）。

### リクエスト例

```
GET /history?limit=5
```

### レスポンス

```jsonc
{
  "events": [
    {
      "type": "result",
      "value": "victory",
      "delta": 1,
      "timestamp": "2025-01-01T12:30:00Z",
      "confidence": 0.88,
    },
    {
      "type": "adjustment",
      "value": "defeat",
      "delta": 1,
      "timestamp": "2025-01-01T12:35:00Z",
      "note": "manual correction",
    },
  ],
}
```

### エラー

- `limit` が数値に変換できない、または負数の場合は `400 Bad Request` と `{"error": "invalid_limit"}` を返します。

## `POST /adjust`

勝敗カウントを手動で調整するエンドポイントです。イベントログにも補正イベントが追記されます。

### リクエスト

```json
{
  "value": "victory", // "victory" または "defeat"
  "delta": 2, // 省略時は 1
  "note": "manual fix" // 任意
}
```

### レスポンス

- 成功時: `202 Accepted` と補正イベントの内容を返します。

```jsonc
{
  "event": {
    "type": "adjustment",
    "value": "victory",
    "delta": 2,
    "timestamp": "2025-01-01T14:00:00Z",
    "note": "manual fix",
  },
}
```

### エラー

- `value` が `"victory"` / `"defeat"` 以外、または JSON が不正な場合は `400 Bad Request` と `{"error": "invalid_payload"}` を返します。
- 内部エラー時は `500 Internal Server Error` を返します（エラーログはサーバ側に記録されます）。

---

今後、履歴を範囲指定で取得する、あるいは UI の更新通知を WebSocket で配信するといった拡張を検討する場合、本ドキュメントを更新して周知してください。
