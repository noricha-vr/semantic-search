# 機能要件

## 機能一覧

| # | 機能 | 優先度 | フェーズ |
|---|------|--------|----------|
| 1 | [ファイル監視・インデックス](features/file-indexing.md) | Must | Phase 1 |
| 2 | [ドキュメント処理](features/document-processing.md) | Must | Phase 1 |
| 3 | [ベクトル検索](features/vector-search.md) | Must | Phase 1 |
| 4 | [ハイブリッド検索](features/hybrid-search.md) | Must | Phase 2 |
| 5 | [画像理解（VLM）](features/vlm-processing.md) | Must | Phase 2 |
| 6 | [動画・音声文字起こし](features/transcription.md) | Must | Phase 3 |
| 7 | [Web UI](features/web-ui.md) | Must | Phase 4 |
| 8 | [CLI](features/cli.md) | Should | Phase 5 |
| 9 | リランキング | Should | Phase 2 |
| 10 | バックアップ・リストア | Should | Phase 5 |

## ユーザーストーリー

### ファイル検索

> 開発者として、自然言語でファイルを検索したい。
> なぜなら、ファイル名を覚えていなくても内容で探せるから。

### 画像検索

> 開発者として、画像の内容で検索したい。
> なぜなら、スクリーンショットやダイアグラムを探すのに便利だから。

### 動画内検索

> 開発者として、動画内の発言を検索してその箇所にジャンプしたい。
> なぜなら、長時間の動画から特定の情報を探すのが大変だから。

### 常時監視

> 開発者として、ファイルの変更を自動検出してインデックスを更新してほしい。
> なぜなら、手動で再インデックスするのは面倒だから。

## MVP機能

Phase 1-2で実装する最小限の機能:

1. PDF・テキストファイルのインデックス
2. ベクトル検索 + BM25ハイブリッド検索
3. ファイル監視・自動インデックス更新
4. 基本的なWeb検索UI

## 将来の拡張機能

- Cloudflare Tunnel連携（外出先からの検索）
- MCP統合（Claude Desktopからの直接検索）
- 類似ドキュメント推薦
- タグ自動付与（LLMによる自動分類）
- 重複ファイル検出
- 話者分離（pyannote-audio）
- リアルタイム文字起こし
