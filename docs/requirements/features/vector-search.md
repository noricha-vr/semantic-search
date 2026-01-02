# ベクトル検索

## 概要

BGE-M3 Embeddingを使用したセマンティック検索。

## 使用モデル

| 項目 | 値 |
|------|-----|
| モデル | BGE-M3 |
| プロバイダ | Ollama |
| 次元数 | 1024 |
| 最大トークン | 8192 |
| サイズ | 1.34GB |

## 選定理由

- **Multi-Functionality**: Dense/Sparse/Multi-vector検索を1モデルで実行
- **Multi-Linguality**: 100言語以上対応（日本語・英語両方で検索可能）
- **Multi-Granularity**: 短文から8192トークンの長文まで対応
- **ベンチマーク最高精度**: Retrieval精度72%

## 設定

```yaml
embedding:
  model: bge-m3
  provider: ollama
  dimensions: 1024

  ollama:
    host: http://localhost:11434
    timeout: 30

  batch_size: 32

  cache:
    enabled: true
    max_size_mb: 1000
```

## ベクトルDB

| 項目 | 値 |
|------|-----|
| DB | LanceDB |
| 特徴 | 組み込み型、サーバー不要 |
| 性能 | 10億ベクトルを100ms以下で検索 |

### 選定理由

- Rustベースで高速・省メモリ
- マルチモーダルデータ対応
- トランザクション保証
