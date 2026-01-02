# ファイル監視・インデックス

## 概要

watchdogを使用したファイルシステム監視と、ファイル追跡システム。

## ユーザーストーリー

> 開発者として、ファイルの変更を自動検出してインデックスを更新してほしい。
> なぜなら、手動で再インデックスするのは面倒だから。

## 機能詳細

### 監視ディレクトリ

```yaml
include:
  - ~/Documents
  - ~/Downloads
  - ~/Pictures
  - ~/Desktop
  - ~/project
  - ~/Movies

exclude:
  - ~/Library
  - ~/.*
  - "**/node_modules"
  - "**/.git"
  - "**/.venv"
  - "**/__pycache__"
```

### ファイル識別方式

```python
class FileIdentity:
    content_hash: str      # SHA-256（先頭64KB + 末尾64KB + サイズ）
    inode: int            # macOSのinode番号
    path: str             # 現在のパス
    size: int             # ファイルサイズ
    mtime: float          # 最終更新日時
    ctime: float          # 作成日時
    media_type: str       # document | image | video | audio
```

### ファイル状態の検出

| イベント | 検出方法 | アクション |
|---------|---------|-----------|
| 新規作成 | watchdog CREATE | インデックス追加 |
| 更新 | mtime変更 + hash変更 | 再インデックス |
| 移動 | 同一hash + 異なるpath | パス更新のみ |
| リネーム | 同一inode + 異なるpath | パス更新のみ |
| 削除 | watchdog DELETE | 論理削除フラグ |
| 復元 | 削除済みhashと一致 | 削除フラグ解除 |

### サイズ制限

| 項目 | 制限値 |
|------|--------|
| 最大ファイルサイズ | 500MB |
| 最小ファイルサイズ | 1KB |
| 最大画像サイズ | 4096px |
| 最大動画長 | 180分 |

## 処理キュー

- 最大キューサイズ: 10,000
- バッチサイズ: 50
- 最大ワーカー数: 4
