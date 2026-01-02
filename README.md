# LocalDocSearch

Mac上の画像・PDF・動画・音声を自然言語で検索できるローカルAI検索システム。

## 必要環境

- macOS (Apple Silicon推奨)
- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- [Ollama](https://ollama.ai/) (BGE-M3, llava:7b)
- FFmpeg (音声・動画処理用)
- Bun (フロントエンド開発用)

## セットアップ

```bash
# 1. 依存関係インストール
uv sync

# 2. Ollamaモデルをプル
ollama pull bge-m3
ollama pull llava:7b

# 3. FFmpegインストール（未インストールの場合）
brew install ffmpeg

# 4. フロントエンド依存関係
cd ui && bun install
```

## 使い方

### CLIコマンド

```bash
# ファイル/ディレクトリをインデックス化
uv run local-doc-search index ~/Documents

# 検索
uv run local-doc-search search "会議の議事録"

# ディレクトリ監視（自動インデックス）
uv run local-doc-search watch ~/Documents ~/Downloads

# APIサーバー起動
uv run local-doc-search serve

# インデックス状態確認
uv run local-doc-search status
```

### Web UI

```bash
# ターミナル1: APIサーバー
uv run local-doc-search serve

# ターミナル2: フロントエンド開発サーバー
cd ui && bun run dev
```

ブラウザで http://localhost:5173 を開く

## 機能

- ハイブリッド検索（ベクトル検索 + BM25 + RRF）
- 画像理解（VLM: llava:7b）
- 動画・音声文字起こし（mlx-whisper）
- タイムスタンプジャンプ（VLC/IINA対応）
- ファイル監視・自動インデックス
- Web UI（SvelteKit + Tailwind CSS）

## 対応ファイル形式

| カテゴリ | 拡張子 |
|----------|--------|
| ドキュメント | .pdf, .txt, .md, .docx, .xlsx, .pptx |
| 画像 | .jpg, .jpeg, .png, .gif, .bmp, .webp |
| 動画 | .mp4, .mov, .avi, .mkv, .wmv, .webm |
| 音声 | .mp3, .wav, .m4a, .flac, .aac, .ogg |

## アーキテクチャ

```
src/
├── api/          # FastAPI REST API
├── cli/          # Typer CLI
├── config/       # 設定管理
├── embeddings/   # BGE-M3 Embedding
├── indexer/      # インデックス処理
├── ocr/          # VLM画像理解
├── processors/   # ファイル処理
├── search/       # 検索エンジン
├── storage/      # LanceDB + SQLite
├── transcription/# 音声認識
└── utils/        # ユーティリティ

ui/               # SvelteKit フロントエンド
```
