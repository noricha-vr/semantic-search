# Web UI

## 概要

SvelteKitベースの検索インターフェース。

## 技術スタック

| 項目 | 技術 |
|------|------|
| フレームワーク | SvelteKit |
| CSS | Tailwind CSS |
| ランタイム | Node.js 22+ |

## 画面構成

### 検索画面（メイン）

- 検索バー
- フィルターパネル（メディアタイプ、拡張子、日付範囲）
- 検索結果一覧
- メディアプレビュー

### 設定画面

- 監視ディレクトリ設定
- インデックス状態表示
- 手動インデックス実行

## コンポーネント

| コンポーネント | 役割 |
|---------------|------|
| SearchBar | 検索入力 |
| ResultCard | 検索結果カード |
| FilterPanel | フィルター設定 |
| MediaPreview | メディアプレビュー |
| TimestampPlayer | タイムスタンプ付き再生 |

## API連携

```typescript
// lib/api.ts
const API_BASE = 'http://127.0.0.1:8765/api';

export async function search(query: string, filters?: SearchFilters) {
  const res = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, ...filters })
  });
  return res.json();
}
```

## 機能

- 検索結果のハイライト表示
- メディアタイプ別アイコン表示
- 動画・音声のタイムスタンプ付き再生
- ファイルを開く（Finderで表示）
