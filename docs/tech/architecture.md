# アーキテクチャ

## システム構成図

```mermaid
graph TB
    subgraph "フロントエンド"
        UI[SvelteKit UI]
    end

    subgraph "バックエンド"
        API[FastAPI]
        Indexer[Indexer Service]
        Watcher[File Watcher]
        Queue[Processing Queue]
    end

    subgraph "AI処理"
        Ollama[Ollama]
        BGE[BGE-M3 Embedding]
        VLM[Qwen2.5-VL]
        Reranker[BGE Reranker]
        Whisper[mlx-whisper]
    end

    subgraph "ストレージ"
        LanceDB[(LanceDB)]
        SQLite[(SQLite FTS5)]
        Config[config.yaml]
    end

    subgraph "外部ツール"
        FFmpeg[FFmpeg]
        Vision[Apple Vision]
    end

    UI -->|REST API| API
    API -->|検索| LanceDB
    API -->|BM25| SQLite
    API -->|リランク| Reranker

    Watcher -->|ファイル変更| Queue
    Queue -->|処理| Indexer

    Indexer -->|テキスト抽出| FFmpeg
    Indexer -->|OCR| Vision
    Indexer -->|画像理解| VLM
    Indexer -->|文字起こし| Whisper
    Indexer -->|Embedding| BGE
    Indexer -->|保存| LanceDB
    Indexer -->|保存| SQLite

    Ollama -->|推論| BGE
    Ollama -->|推論| VLM
    Ollama -->|推論| Reranker
```

## コンポーネント

### フロントエンド

| コンポーネント | 技術 | 役割 |
|--------------|------|------|
| Web UI | SvelteKit | 検索インターフェース |

### バックエンド

| コンポーネント | 技術 | 役割 |
|--------------|------|------|
| API | FastAPI | REST API提供 |
| Watcher | watchdog | ファイル監視 |
| Queue | 独自実装 | 処理キュー管理 |
| Indexer | 独自実装 | インデックス処理 |

### AI処理

| コンポーネント | モデル | 役割 |
|--------------|--------|------|
| Embedding | BGE-M3 | ベクトル生成 |
| VLM | Qwen2.5-VL:7B | 画像理解 |
| Reranker | bge-reranker-v2-m3 | 検索精度向上 |
| 音声認識 | whisper-large-v3-turbo | 文字起こし |

### ストレージ

| コンポーネント | 技術 | 役割 |
|--------------|------|------|
| ベクトルDB | LanceDB | ベクトル検索 |
| 全文検索 | SQLite FTS5 | BM25検索 |

## 処理フロー

### インデックス処理

```mermaid
sequenceDiagram
    participant W as File Watcher
    participant Q as Queue
    participant I as Indexer
    participant P as Processor
    participant E as Embedding
    participant DB as Storage

    W->>Q: ファイル変更検出
    Q->>I: 処理依頼
    I->>P: ファイルタイプ判定

    alt ドキュメント
        P->>P: テキスト抽出
    else 画像
        P->>P: VLM処理
    else 動画/音声
        P->>P: FFmpeg音声抽出
        P->>P: Whisper文字起こし
    end

    P->>P: チャンキング
    P->>E: Embedding生成
    E->>DB: 保存
```

### 検索処理

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant V as Vector Search
    participant B as BM25 Search
    participant R as Reranker

    U->>API: 検索クエリ
    API->>V: ベクトル検索
    API->>B: BM25検索

    V-->>API: 結果
    B-->>API: 結果

    API->>API: RRF統合
    API->>R: リランキング
    R-->>API: 最終結果
    API-->>U: 検索結果
```

## ディレクトリ構成

```
local-doc-search/
├── src/
│   ├── config/          # 設定管理
│   ├── indexer/         # インデックス処理
│   ├── processors/      # ファイル処理
│   ├── transcription/   # 音声認識
│   ├── ocr/             # OCR
│   ├── embeddings/      # Embedding
│   ├── storage/         # DB操作
│   ├── search/          # 検索
│   ├── api/             # REST API
│   └── cli/             # CLI
├── ui/                  # SvelteKit
├── data/                # データ
├── scripts/             # スクリプト
├── tests/               # テスト
└── docs/                # ドキュメント
```

## セキュリティ

- **完全ローカル処理**: 外部通信なし
- **API認証**: localhost限定
- **ファイルアクセス**: 設定された監視ディレクトリのみ
