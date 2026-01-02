"""音声プロセッサ。

音声ファイルを文字起こししてインデックス化する。
"""

import uuid
from dataclasses import dataclass
from pathlib import Path

from src.config.logging import get_logger
from src.embeddings.ollama_embedding import OllamaEmbeddingClient
from src.processors.chunker import Chunker
from src.storage.lancedb_client import LanceDBClient
from src.storage.sqlite_client import SQLiteClient
from src.transcription.whisper_client import WhisperClient

logger = get_logger()


@dataclass
class AudioResult:
    """音声処理結果。"""

    text: str
    language: str
    duration: float
    word_count: int
    segments: list[dict]


class AudioProcessor:
    """音声プロセッサ。"""

    SUPPORTED_EXTENSIONS = {
        ".mp3",
        ".wav",
        ".m4a",
        ".flac",
        ".aac",
        ".ogg",
        ".wma",
    }

    def __init__(self):
        """初期化。"""
        self.whisper_client = WhisperClient()
        self.chunker = Chunker()
        self.embedding_client = OllamaEmbeddingClient()
        self.lancedb_client = LanceDBClient()
        self.sqlite_client = SQLiteClient()

    def process_audio(self, audio_path: Path | str) -> AudioResult | None:
        """音声を処理。

        Args:
            audio_path: 音声ファイルのパス

        Returns:
            処理結果またはNone
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            logger.warning(f"Audio file not found: {audio_path}")
            return None

        try:
            # 文字起こし
            result = self.whisper_client.transcribe(audio_path)

            logger.info(
                f"Processed audio: {audio_path}, "
                f"duration: {result.duration:.1f}s"
            )

            return AudioResult(
                text=result.text,
                language=result.language,
                duration=result.duration,
                word_count=len(result.text.split()),
                segments=[
                    {
                        "text": s.text,
                        "start": s.start,
                        "end": s.end,
                    }
                    for s in result.segments
                ],
            )

        except Exception as e:
            logger.error(f"Failed to process audio {audio_path}: {e}")
            return None

    def index_audio(
        self,
        audio_path: Path | str,
        document_id: str,
    ) -> dict | None:
        """音声をインデックス化。

        Args:
            audio_path: 音声ファイルのパス
            document_id: ドキュメントID

        Returns:
            Transcriptレコードまたはなし
        """
        result = self.process_audio(audio_path)
        if not result:
            return None

        audio_path = Path(audio_path)

        # Transcriptレコードを作成
        transcript = {
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "full_text": result.text,
            "language": result.language,
            "duration_seconds": result.duration,
            "word_count": result.word_count,
        }

        # セグメントをタイムスタンプ付きチャンクに変換
        chunks = self.chunker.chunk_with_timestamps(result.segments)

        if not chunks:
            # セグメントがない場合はテキスト全体をチャンク化
            text_chunks = self.chunker.chunk_text(result.text)
            chunks = [
                {
                    "text": c.text,
                    "start_time": None,
                    "end_time": None,
                    "chunk_index": c.chunk_index,
                }
                for c in text_chunks
            ]

        # Embedding生成
        chunk_texts = [c["text"] for c in chunks]
        if chunk_texts:
            embeddings = self.embedding_client.embed_batch(chunk_texts)
        else:
            embeddings = []

        # チャンクレコード作成
        chunk_records = []
        fts_records = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_id = str(uuid.uuid4())
            chunk_record = {
                "id": chunk_id,
                "document_id": document_id,
                "chunk_index": chunk.get("chunk_index", 0),
                "text": chunk["text"],
                "vector": embedding,
                "start_time": chunk.get("start_time"),
                "end_time": chunk.get("end_time"),
                "path": str(audio_path.absolute()),
                "filename": audio_path.name,
                "media_type": "audio",
            }
            chunk_records.append(chunk_record)
            fts_records.append({
                "id": chunk_id,
                "document_id": document_id,
                "text": chunk["text"],
                "path": str(audio_path.absolute()),
                "filename": audio_path.name,
            })

        # データベースに保存
        if chunk_records:
            self.lancedb_client.add_chunks(chunk_records)
            self.sqlite_client.add_chunks_fts(fts_records)

        logger.info(
            f"Indexed audio: {audio_path}, "
            f"chunks: {len(chunk_records)}"
        )

        return transcript

    def is_supported(self, file_path: Path | str) -> bool:
        """ファイルがサポートされているかを判定。

        Args:
            file_path: ファイルパス

        Returns:
            サポートされていればTrue
        """
        file_path = Path(file_path)
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
