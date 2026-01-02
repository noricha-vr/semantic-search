# 画像理解（VLM）

## 概要

Vision Language Modelを使用した画像の説明文生成とOCR。

## 対応形式

| 拡張子 | 処理方法 |
|--------|----------|
| .png, .jpg, .jpeg, .webp | VLM (Qwen2.5-VL) |
| .heic, .gif, .bmp, .tiff | VLM (Qwen2.5-VL) |

## 使用モデル

| 項目 | 値 |
|------|-----|
| モデル | Qwen2.5-VL:7B |
| プロバイダ | Ollama |
| サイズ | 4.7GB |
| タイムアウト | 120秒 |
| 同時処理数 | 2 |

### 選定理由

- 前世代(Qwen2-VL)から文書解析・OCR・構造化出力が大幅強化
- 日本語ドキュメントの理解に優れる
- M3 Ultraで快適に動作

## 設定

```yaml
vlm:
  model: qwen2.5-vl:7b
  provider: ollama
  timeout_seconds: 120
  max_concurrent: 2
  retry_count: 3

  prompt: |
    この画像の内容を詳細に説明してください。
    - 文字が含まれていれば全て書き起こしてください
    - 図表があれば内容を説明してください
    - 写真なら何が写っているか説明してください
    日本語で回答してください。
```

## OCR補助

| 項目 | 値 |
|------|-----|
| エンジン | Apple Vision Framework |
| 対応言語 | 日本語、英語 |
| 用途 | VLMで不十分な場合のフォールバック |

```yaml
ocr:
  enabled: true
  engine: apple_vision
  languages:
    - ja
    - en
  fallback_for_vlm: true
```

## パフォーマンス

| 処理 | 時間 |
|------|------|
| 画像1枚 | ~3秒 |

## 画像サイズ制限

| 項目 | 値 |
|------|-----|
| 最小幅 | 200px |
| 最小高さ | 200px |
| 最大サイズ | 4096px |
