# ドキュメント処理

## 概要

PDF、Office文書、テキストファイルからテキストを抽出する機能。

## 対応形式

### ドキュメント

| 拡張子 | 処理方法 |
|--------|----------|
| .pdf | pymupdf テキスト抽出 → 画像のみならVLM |
| .docx | python-docx |
| .xlsx | openpyxl |
| .pptx | python-pptx |
| .md, .txt, .rtf | 直接読み込み |
| .csv, .json, .yaml | 直接読み込み |

## 処理パイプライン

```
[ファイル検出]
      |
      v
[ファイルタイプ判定]
      |
      +-- PDF --> pymupdf テキスト抽出
      |              └── 画像のみ → VLM
      +-- Office --> python-docx 等
      +-- テキスト --> 直接読み込み
      |
      v
[テキストチャンキング]
      |
      v
[Embedding生成 (BGE-M3)]
      |
      v
[LanceDB + SQLite FTS5 保存]
```

## チャンキング設定

```yaml
chunking:
  strategy: semantic

  semantic:
    max_chunk_size: 1000
    min_chunk_size: 100
    overlap: 100
```

## パフォーマンス目標

| ファイルタイプ | サイズ | 処理時間 |
|--------------|--------|----------|
| PDF (テキスト) | 100ページ | ~5秒 |
| PDF (スキャン) | 100ページ | ~3分 |
