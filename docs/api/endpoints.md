# API仕様

## 概要

| 項目 | 値 |
|------|-----|
| ベースURL | http://127.0.0.1:8765/api |
| 形式 | REST JSON |
| 認証 | なし（localhost限定） |

## エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| POST | /search | 検索 |
| GET | /documents/{id} | ドキュメント詳細 |
| POST | /documents/{id}/open | ファイルを開く |
| GET | /status | インデックス状態 |
| POST | /index | 手動インデックス |
| GET | /config | 設定取得 |
| PUT | /config | 設定更新 |

## 検索

### POST /search

検索クエリを実行し、結果を返す。

**リクエスト**

```json
{
  "query": "検索クエリ",
  "limit": 10,
  "filters": {
    "media_type": ["document", "image"],
    "extension": [".pdf", ".png"],
    "path_prefix": "~/Documents",
    "date_from": "2024-01-01",
    "date_to": "2024-12-31"
  }
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| query | string | Yes | 検索クエリ |
| limit | int | No | 結果件数（デフォルト: 10） |
| filters | object | No | フィルター条件 |

**レスポンス**

```json
{
  "results": [
    {
      "document_id": "uuid",
      "chunk_id": "uuid",
      "path": "/path/to/file.pdf",
      "filename": "file.pdf",
      "media_type": "document",
      "text_snippet": "...マッチしたテキスト...",
      "score": 0.85,
      "vector_score": 0.9,
      "bm25_score": 0.75,
      "timestamp_start": null,
      "timestamp_end": null,
      "metadata": {}
    }
  ],
  "total": 42,
  "took_ms": 23
}
```

## ドキュメント詳細

### GET /documents/{id}

ドキュメントの詳細情報を取得。

**レスポンス**

```json
{
  "document": {
    "id": "uuid",
    "path": "/path/to/file.pdf",
    "filename": "file.pdf",
    "extension": ".pdf",
    "media_type": "document",
    "size": 1024000,
    "created_at": "2024-01-01T00:00:00Z",
    "modified_at": "2024-01-02T00:00:00Z",
    "indexed_at": "2024-01-02T12:00:00Z"
  },
  "chunks": [
    {
      "id": "uuid",
      "chunk_index": 0,
      "text": "...",
      "start_time": null,
      "end_time": null
    }
  ],
  "transcript": null
}
```

## ファイルを開く

### POST /documents/{id}/open

ファイルをデフォルトアプリケーションで開く。

**リクエスト**

```json
{
  "timestamp": 120
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| timestamp | float | No | 再生開始位置（秒） |

**レスポンス**

```json
{
  "success": true
}
```

## インデックス状態

### GET /status

インデックスの状態を取得。

**レスポンス**

```json
{
  "total_documents": 10000,
  "by_media_type": {
    "document": 5000,
    "image": 3000,
    "video": 1500,
    "audio": 500
  },
  "total_chunks": 50000,
  "last_indexed_at": "2024-01-02T12:00:00Z",
  "pending_count": 10,
  "processing_count": 2
}
```

## 手動インデックス

### POST /index

指定パスを手動でインデックス。

**リクエスト**

```json
{
  "paths": [
    "/path/to/dir1",
    "/path/to/file.pdf"
  ]
}
```

**レスポンス**

```json
{
  "success": true,
  "queued_count": 150
}
```

## 設定

### GET /config

現在の設定を取得。

### PUT /config

設定を更新。

**リクエスト**

```json
{
  "watch": {
    "include": ["~/Documents", "~/Downloads"]
  }
}
```
