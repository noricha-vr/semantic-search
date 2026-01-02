# ハイブリッド検索

## 概要

ベクトル検索とBM25検索を組み合わせた検索機能。

## 検索方式

```
[クエリ]
    |
    +---------------------+
    |                     |
    v                     v
[ベクトル検索]       [BM25検索]
(LanceDB)           (SQLite FTS5)
    |                     |
    +---------------------+
              |
              v
    [Reciprocal Rank Fusion]
              |
              v
    [リランキング (オプション)]
              |
              v
         [検索結果]
```

## 設定

```yaml
search:
  default_limit: 10
  max_limit: 100

  weights:
    vector: 0.7
    bm25: 0.3

  rrf_k: 60
  min_similarity: 0.3

  reranker:
    enabled: true
    model: bge-reranker-v2-m3
    top_k: 50
```

## API

```python
def hybrid_search(
    query: str,
    k: int = 10,
    vector_weight: float = 0.7,
    bm25_weight: float = 0.3,
    filters: dict | None = None
) -> list[SearchResult]:
```

### フィルター

| フィルター | 説明 |
|-----------|------|
| media_type | document, image, video, audio |
| extension | .pdf, .png など |
| path_prefix | パスのプレフィックス |
| date_from | 開始日 |
| date_to | 終了日 |
| min_duration | 最小長（秒） |
| max_duration | 最大長（秒） |

## リランカー

| 項目 | 値 |
|------|-----|
| モデル | bge-reranker-v2-m3 |
| サイズ | 1.1GB |
| 対象数 | 上位50件 |
