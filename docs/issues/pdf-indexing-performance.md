# PDF インデックス パフォーマンス問題

## 最終更新: 2026-01-03

## ステータス: 解決済み

---

## 問題の概要

大きなPDFファイル（特に画像が多いPDF）のインデックス処理中に、CPU使用率が100%に達し、メモリ使用量が継続的に増加する。処理は完了せずハングする。

## 解決策

### 実装した変更

| ファイル | 変更内容 |
|---------|---------|
| `pyproject.toml` | `pymupdf4llm>=0.0.17` 依存関係追加 |
| `src/config/settings.py` | PDF処理設定7項目追加 |
| `src/processors/pdf_processor.py` | PyMuPDF4LLM統合、VLM用画像変換メソッド追加 |
| `src/indexer/document_indexer.py` | VLMフォールバック、タイムアウト、進捗ログ追加 |

### 新しいPDF処理設定

```python
# src/config/settings.py
pdf_use_markdown: bool = True           # Markdown形式で抽出
pdf_min_chars_per_page: int = 100       # VLM閾値（1ページあたり）
pdf_vlm_fallback: bool = True           # VLMフォールバック有効
pdf_vlm_dpi: int = 150                  # 画像変換DPI
pdf_vlm_model: str = "minicpm-v"        # VLMモデル
pdf_vlm_timeout: int = 60               # 1ページあたりのタイムアウト（秒）
pdf_vlm_max_pages: int = 20             # VLM処理する最大ページ数
```

### 処理フロー

```
PDF入力
  ↓
PyMuPDF4LLM でテキスト抽出（Markdown形式）
  ↓
ページ単位でテキスト量チェック（閾値: 100文字/ページ）
  ↓
閾値以下のページあり？
  ├─ No → 通常処理（チャンキング→Embedding）
  └─ Yes → VLMフォールバック
              ↓
           最大ページ数制限チェック（デフォルト20ページ）
              ↓
           該当ページを画像変換（DPI 150）
              ↓
           VLM（minicpm-v）で各ページを処理
           （タイムアウト: 60秒/ページ、進捗ログ出力）
              ↓
           テキスト結果を統合
              ↓
           チャンキング→Embedding
```

### テスト結果

| テスト | 結果 |
|--------|------|
| VRC-UI2.pdf (20MB, 59ページ) テキスト抽出 | ✅ 4.19秒で完了 |
| VLM処理 (3ページ制限) | ✅ 25.8秒で完了 |
| API経由インデックス | ✅ 正常動作 |
| 進捗ログ出力 | ✅ `[1/3] Processing page 1 with VLM...` |
| タイムアウト機能 | ✅ 実装済み |

---

## 問題の詳細（アーカイブ）

### 発見事項

#### 1. 小さいPDFは正常に動作

| ファイル | サイズ | テキスト量 | 結果 |
|---------|--------|-----------|------|
| 20240404konnai-kabushikigaisha-san-sama-goseikyuusho.pdf | 54KB | 370文字 | ✅ 正常（0.05秒） |

#### 2. 大きいPDFでハング（修正前）

| ファイル | サイズ | ページ数 | テキスト量 | 結果 |
|---------|--------|---------|-----------|------|
| VRC-UI2.pdf | 20MB | 59ページ | 1068文字 | ❌ ハング（CPU 100%, メモリ 40%+） |

### 原因

1. **画像ベースPDF**: 59ページ中57ページがテキストなし（画像のみ）
2. **VLMフォールバックなし**: テキストが抽出できない場合の代替処理がなかった
3. **タイムアウトなし**: 処理が無限に続く可能性があった

### Claude Code シェル環境の問題（別件）

一部のハングはClaude Codeのシェル環境に起因していた可能性がある。直接ターミナルでの実行では問題が再現しないケースがあった。

## 関連ファイル

- `src/indexer/document_indexer.py` - VLMフォールバック処理
- `src/processors/pdf_processor.py` - PyMuPDF4LLM統合
- `src/config/settings.py` - PDF処理設定

## 正常に動作している機能

- 画像ファイルのインデックス（VLM経由）
- 小さいPDFのインデックス
- 大きいPDF（画像ベース）のインデックス ← **新規追加**
- 音声ファイルのインデックス
- 検索機能
- Web UI
- API経由でのインデックス
