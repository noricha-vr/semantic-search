# CLI

## 概要

Typerベースのコマンドラインインターフェース。

## コマンド一覧

```bash
# 検索
local-doc-search search "検索クエリ"

# インデックス状態
local-doc-search status

# 手動インデックス
local-doc-search index /path/to/dir

# サーバー起動
local-doc-search serve

# 設定表示
local-doc-search config show

# バックアップ
local-doc-search backup create
local-doc-search backup restore <backup-file>
```

## オプション

### search

```bash
local-doc-search search "クエリ" \
  --limit 20 \
  --type document \
  --type image \
  --path-prefix ~/Documents \
  --json
```

| オプション | 説明 |
|-----------|------|
| --limit | 結果件数（デフォルト: 10） |
| --type | メディアタイプフィルター |
| --path-prefix | パスプレフィックス |
| --json | JSON出力 |

### serve

```bash
local-doc-search serve \
  --host 127.0.0.1 \
  --port 8765 \
  --reload
```

## 依存ライブラリ

- typer: CLI構築
- rich: リッチ出力
