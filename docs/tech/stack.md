# 技術選定

## サマリー

| レイヤー | 技術 | バージョン |
|---------|------|-----------|
| バックエンド | Python | 3.11+ |
| フロントエンド | SvelteKit | 最新 |
| パッケージ管理 | uv | 0.7+ |
| API | FastAPI | 0.115+ |
| ベクトルDB | LanceDB | 0.15+ |
| 全文検索 | SQLite FTS5 | - |
| LLM推論 | Ollama | 最新 |

## バックエンド

### Python 3.11+

**選定理由**:
- 豊富なML/AIライブラリ
- 型ヒント完全サポート
- asyncio対応

### FastAPI

**選定理由**:
- 高速（Starlette + Pydantic）
- 自動OpenAPI生成
- 型安全

## フロントエンド

### SvelteKit + Tailwind CSS

**選定理由**:
- 軽量・高速
- シンプルな構文
- TypeScript対応

## データベース

### LanceDB

| 項目 | 値 |
|------|-----|
| 用途 | ベクトル検索 |
| 特徴 | 組み込み型、サーバー不要 |
| 性能 | 10億ベクトル/100ms以下 |

**選定理由**:
- Rustベースで高速・省メモリ
- マルチモーダルデータ対応
- トランザクション保証

### SQLite FTS5

| 項目 | 値 |
|------|-----|
| 用途 | BM25全文検索 |
| 特徴 | 組み込み型 |

## AIモデル

### Embedding: BGE-M3

| 項目 | 値 |
|------|-----|
| サイズ | 1.34GB |
| 次元数 | 1024 |
| 対応言語 | 100+ |

**選定理由**:
- Dense/Sparse/Multi-vector対応
- 日本語・英語両方で高精度

### VLM: Qwen2.5-VL:7B

| 項目 | 値 |
|------|-----|
| サイズ | 4.7GB |
| 用途 | 画像理解・OCR |

**選定理由**:
- 日本語ドキュメント理解に優れる
- OCR・構造化出力に最適化

### 音声認識: Whisper large-v3-turbo

| 項目 | 値 |
|------|-----|
| サイズ | 1.6GB |
| エンジン | mlx-whisper |

**選定理由**:
- large-v3の6倍高速
- Apple Silicon最適化

### OCR: Apple Vision Framework

| 項目 | 値 |
|------|-----|
| 用途 | OCR補助 |
| 対応言語 | 日本語、英語 |

**選定理由**:
- macOS標準で追加インストール不要
- 高速・高精度

### リランカー: bge-reranker-v2-m3

| 項目 | 値 |
|------|-----|
| サイズ | 1.1GB |
| 用途 | 検索精度向上 |

## その他ツール

| ツール | 用途 |
|-------|------|
| FFmpeg | 動画から音声抽出 |
| watchdog | ファイル監視 |
| Typer | CLI構築 |
| Rich | リッチコンソール出力 |

## 依存関係

```toml
[project]
dependencies = [
    # Web Framework
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",

    # Database
    "lancedb>=0.15.0",

    # Document Processing
    "pymupdf>=1.24.0",
    "python-docx>=1.1.0",
    "openpyxl>=3.1.0",
    "python-pptx>=1.0.0",

    # Image Processing
    "pillow>=10.0.0",

    # Audio/Video
    "mlx-whisper>=0.4.0",

    # ML/Embedding
    "ollama>=0.3.0",
    "numpy>=1.26.0",

    # File Watching
    "watchdog>=4.0.0",

    # OCR (Apple Vision wrapper)
    "pyobjc-framework-Vision>=10.0",

    # Utilities
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "pyyaml>=6.0.0",
    "rich>=13.0.0",
    "typer>=0.12.0",
]
```
