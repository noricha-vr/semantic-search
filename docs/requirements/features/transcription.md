# 動画・音声文字起こし

## 概要

Whisper large-v3-turboを使用した音声認識とタイムスタンプ付きチャンキング。

## 対応形式

### 動画

| 拡張子 | 処理方法 |
|--------|----------|
| .mp4, .mov, .avi, .mkv, .webm, .m4v | FFmpeg音声抽出 → Whisper |

### 音声

| 拡張子 | 処理方法 |
|--------|----------|
| .mp3, .m4a, .wav, .flac, .ogg, .aac | Whisper直接処理 |

## 使用モデル

| 項目 | 値 |
|------|-----|
| モデル | whisper-large-v3-turbo |
| プロバイダ | mlx-whisper |
| サイズ | 1.6GB |
| 言語 | 日本語（自動検出可） |

### 選定理由

- デコーダ層32→4に削減で6倍高速化
- 精度はlarge-v2相当を維持
- mlx-whisperでApple Silicon最適化

## 設定

```yaml
transcription:
  model: mlx-community/whisper-large-v3-turbo
  model_engine: mlx-whisper

  language: ja

  word_timestamps: false
  segment_timestamps: true

  batch_size: 12
  max_concurrent: 1

  audio_extraction:
    sample_rate: 16000
    channels: 1
    format: wav

  cache:
    enabled: true
    keep_extracted_audio: false
    cache_transcripts: true
```

## チャンキング

```yaml
transcript:
  min_segment_chars: 50
  max_segment_chars: 1000
  max_time_gap: 2.0
```

## タイムスタンプ付き再生

検索結果から動画・音声の特定箇所に直接ジャンプ可能。

```python
def get_playback_url(self) -> str | None:
    if self.media_type in ("video", "audio") and self.timestamp_start:
        return f"file://{self.path}#t={int(self.timestamp_start)}"
    return None
```

## パフォーマンス

| 長さ | 処理時間 |
|------|----------|
| 10分 | ~1分 |
| 1時間 | ~5分 |
| 3時間 | ~15分 |

## 制限

| 項目 | 値 |
|------|-----|
| 最大動画/音声長 | 180分 |
