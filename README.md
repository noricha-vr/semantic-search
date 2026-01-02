# LocalDocSearch

Mac上の画像・PDF・動画・音声を自然言語で検索できるローカルAI検索システム。

## セットアップ

```bash
# 依存関係インストール
uv sync

# 開発サーバー起動
uv run uvicorn src.api.main:app --reload
```

## 機能

- ファイル監視・自動インデックス
- ベクトル検索 + BM25ハイブリッド検索
- 画像理解（VLM）
- 動画・音声文字起こし
- Web UI
