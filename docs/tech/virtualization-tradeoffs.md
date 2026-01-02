# OrbStack仮想化のトレードオフ

## 結論

**LocalDocSearchではOrbStack/Docker仮想化は非推奨**

理由: mlx-whisper、Ollamaなど本プロジェクトのコア技術がGPU/Metal/Neural Engineアクセスを必要とするが、macOSのコンテナ仮想化ではこれらにアクセスできない。

## 技術的制約

### Apple Hypervisor.frameworkの制限

macOS上のすべての仮想化ソリューション（OrbStack、Docker Desktop、Parallels、Podman等）はAppleの`Hypervisor.framework`を使用する。このフレームワークは**仮想GPU機能を提供していない**。

| リソース | ホストアクセス | コンテナアクセス |
|---------|---------------|-----------------|
| CPU | Yes | Yes（仮想化） |
| メモリ | Yes | Yes（制限付き） |
| GPU (Metal) | Yes | **No** |
| Neural Engine | Yes | **No** |
| ファイルシステム | Yes | Yes（VirtioFS） |

### 影響を受けるコンポーネント

| コンポーネント | GPU必要 | 影響 |
|--------------|---------|------|
| Ollama (BGE-M3, Qwen2.5-VL) | Yes | Metal加速不可、CPU推論のみ |
| mlx-whisper | Yes | 動作不可（MLXはMetal必須） |
| Apple Vision OCR | Yes | 動作不可（macOS専用API） |

### パフォーマンス比較

| 処理 | ネイティブ (Metal) | コンテナ (CPUのみ) |
|-----|-------------------|-------------------|
| 画像VLM処理 | ~3秒 | 推定10-20秒 |
| 1時間動画の文字起こし | ~5分 | 推定30-60分 |
| Embedding生成 | 高速 | 推定5-10倍遅い |

## OrbStackのメリット

それでもOrbStackを使う場合のメリット:

| メリット | 詳細 |
|---------|------|
| 開発環境の分離 | ホスト環境を汚さない |
| 再現性 | Dockerfileで環境を再現可能 |
| リソース効率 | Docker Desktopより3-4倍少ないRAM使用 |
| ファイルI/O | Docker Desktopより2-10倍高速 |
| 消費電力 | Docker Desktopの1/4 |

## 推奨アーキテクチャ

### 方式1: 完全ネイティブ（推奨）

```
[macOS ホスト]
├── Python環境（uv）
├── Ollama（ネイティブ）
├── mlx-whisper
├── Apple Vision Framework
├── LanceDB
└── SvelteKit開発サーバー
```

**メリット**: 最高性能、全機能利用可能
**デメリット**: ホスト環境にツールをインストール

### 方式2: ハイブリッド（代替案）

```
[macOS ホスト]
├── Ollama（ネイティブ、GPU使用）
└── mlx-whisper（ネイティブ）

[OrbStack / Docker]
├── FastAPI バックエンド
├── LanceDB
└── SvelteKit（ビルド用）
```

**メリット**: AI処理はGPU使用、他は分離
**デメリット**: 構成が複雑、ホスト↔コンテナ通信オーバーヘッド

### 方式3: コンテナ内CPU推論（非推奨）

```
[OrbStack / Docker]
├── すべてのコンポーネント
└── Ollama（CPUのみ）
```

**メリット**: 完全分離
**デメリット**: 極端に遅い、mlx-whisper使用不可

## Ollamaの公式推奨

Ollamaは公式にmacOSでのDocker使用を非推奨としている:

> "Ollama recommends running Ollama alongside Docker Desktop for MacOS in order for Ollama to enable GPU acceleration."

つまり、Ollamaをコンテナ内で実行せず、**ホストでネイティブ実行**することを推奨。

## 今後の展望

- **Podman + libkrun**: 実験的なVulkanパススルーがあるが、安定性に課題
- **Apple Containers**: Apple純正のコンテナ技術だがGPUサポートは未実装
- **Hypervisor.framework更新**: Appleが仮想GPUサポートを追加する可能性（未定）

## 参考資料

- [Apple Silicon GPUs, Docker and Ollama: Pick two](https://chariotsolutions.com/blog/post/apple-silicon-gpus-docker-and-ollama-pick-two/)
- [A path to GPU support for Ollama in a VM/container on Apple Silicon](https://github.com/ollama/ollama/issues/5652)
- [GPU acceleration / libkrun - OrbStack Discussion](https://github.com/orgs/orbstack/discussions/1408)
- [Local AI with MLX on the Mac](https://www.markus-schall.de/en/2025/09/mlx-on-apple-silicon-as-local-ki-compared-with-ollama-co/)
- [Docker on MacOS is still slow? (2025)](https://www.paolomainardi.com/posts/docker-performance-macos-2025/)
