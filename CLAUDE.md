# LocalDocSearch

Mac上の画像・PDF・動画・音声を自然言語で検索できるローカルAI検索システム。
すべての処理をローカルで完結し、外部サービスへのデータ送信を行わない。

<quick_reference>

| 項目 | 値 |
|------|-----|
| ローカルAPI | http://localhost:2602 |
| Swagger UI | http://localhost:2602/docs |
| フロントエンド(dev) | http://localhost:5173 |
| Ollamaモデル | bge-m3, llava:7b |
| Python | 3.11+ |
| データ保存先 | ~/.local/share/local-doc-search |

</quick_reference>

<tech_stack>

| カテゴリ | 技術 |
|---------|------|
| バックエンド | FastAPI, uv |
| フロントエンド | SvelteKit, Tailwind CSS, Bun |
| ベクトルDB | LanceDB |
| 全文検索 | SQLite FTS5 (BM25) |
| Embedding | Ollama (BGE-M3) |
| 画像理解 | Ollama (llava:7b) |
| 音声認識 | mlx-whisper |
| PDF処理 | PyMuPDF4LLM |

</tech_stack>

<directory_structure>

| ディレクトリ | 役割 |
|-------------|------|
| src/api/ | FastAPI REST API |
| src/cli/ | Typer CLI |
| src/config/ | 設定管理（Pydantic Settings） |
| src/constants/ | 定数定義（メディアタイプ等） |
| src/embeddings/ | BGE-M3 Embedding |
| src/indexer/ | インデックス処理 |
| src/processors/ | ファイル処理（PDF, VLM等） |
| src/search/ | 検索エンジン（ハイブリッド検索） |
| src/storage/ | ストレージ層（リポジトリパターン） |
| src/transcription/ | 音声認識（mlx-whisper） |
| ui/ | SvelteKit フロントエンド |
| tests/ | テストコード（177件） |
| scripts/ | スクリプト・デーモン設定 |

</directory_structure>

<commands>

```bash
# APIサーバー起動
./scripts/start.sh

# フロントエンド開発サーバー
cd ui && bun run dev

# テスト実行
uv run pytest tests/ -v

# ファイルインデックス
uv run python -m src.cli.main index ~/Documents

# 検索
uv run python -m src.cli.main search "検索クエリ"

# ファイル監視
uv run python -m src.cli.main watch ~/Documents

# デーモンインストール（ログイン時自動起動）
./scripts/install-daemon.sh

# デーモン状態確認
launchctl list | grep localdocsearch
```

</commands>

<environment_variables>

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| OLLAMA_HOST | http://localhost:11434 | Ollamaサーバー |
| DATA_DIR | ~/.local/share/local-doc-search | データ保存先 |
| LOG_LEVEL | INFO | ログレベル |
| EMBEDDING_MODEL | bge-m3 | Embeddingモデル |
| VLM_MODEL | llava:7b | 画像理解モデル |
| PDF_VLM_MODEL | minicpm-v | PDF VLM処理用 |
| PDF_VLM_TIMEOUT | 60 | VLMタイムアウト(秒) |

</environment_variables>

<supported_formats>

- ドキュメント: .pdf, .txt, .md, .docx, .xlsx, .pptx
- 画像: .jpg, .jpeg, .png, .gif, .bmp, .webp
- 動画: .mp4, .mov, .avi, .mkv, .wmv, .webm
- 音声: .mp3, .wav, .m4a, .flac, .aac, .ogg

</supported_formats>

<code_investigation>

コードを編集・提案する前に、必ず関連ファイルを読んで理解する。
推測でコードを提案しない。ユーザーが特定のファイルに言及した場合、そのファイルを開いて確認してから回答する。
既存のスタイル、規約、抽象化を確認してから新機能を実装する。

</code_investigation>

<avoid_overengineering>

直接要求された変更、または明らかに必要な変更のみ行う。
要求されていない機能追加、リファクタリング、「改善」は行わない。
バグ修正時に周辺コードのクリーンアップは不要。
シンプルな機能に追加の設定可能性は不要。
発生し得ないシナリオに対するエラーハンドリング、フォールバック、バリデーションは追加しない。
一度きりの操作にヘルパー、ユーティリティ、抽象化を作成しない。
既存の抽象化を再利用し、DRY原則に従う。

</avoid_overengineering>

<testing>

テスト実行後、失敗したテストがあれば原因を調査して修正する。
テストを削除・編集して通すことは禁止。機能の欠落やバグにつながる。
テストはロジックの正しさを検証するためにあり、テストに合わせて実装を歪めない。

</testing>

<dependencies>

Ollamaが起動していることを確認してからAPIサーバーを起動する。
初回インデックスは時間がかかる（特にVLM処理）。
PDF VLM処理は1ページあたり最大60秒のタイムアウトあり。

</dependencies>
