"""動画プロセッサ。

動画ファイルから音声を抽出して文字起こしする。
"""

import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from src.config.logging import get_logger
from src.embeddings.ollama_embedding import OllamaEmbeddingClient
from src.processors.chunker import Chunker
from src.storage.lancedb_client import LanceDBClient
from src.storage.sqlite_client import SQLiteClient
from src.transcription.ffmpeg_utils import extract_audio, get_media_info
from src.transcription.whisper_client import WhisperClient

logger = get_logger()


@dataclass
class VideoResult:
    """動画処理結果。"""

    text: str
    language: str
    duration: float
    word_count: int
    segments: list[dict]
    width: int | None
    height: int | None


class VideoProcessor:
    """動画プロセッサ。"""

    SUPPORTED_EXTENSIONS = {
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".wmv",
        ".flv",
        ".webm",
    }

    def __init__(self):
        """初期化。"""
        self.whisper_client = WhisperClient()
        self.chunker = Chunker()
        self.embedding_client = OllamaEmbeddingClient()
        self.lancedb_client = LanceDBClient()
        self.sqlite_client = SQLiteClient()

    def process_video(self, video_path: Path | str) -> VideoResult | None:
        """動画を処理。

        Args:
            video_path: 動画ファイルのパス

        Returns:
            処理結果またはNone
        """
        video_path = Path(video_path)
        if not video_path.exists():
            logger.warning(f"Video file not found: {video_path}")
            return None

        temp_dir = None
        try:
            # メディア情報を取得
            info = get_media_info(video_path)
            width = info.get("width") if info else None
            height = info.get("height") if info else None

            # 音声を抽出
            temp_dir = tempfile.mkdtemp()
            audio_path = extract_audio(video_path, output_path=Path(temp_dir) / "audio.wav")

            # 文字起こし
            result = self.whisper_client.transcribe(audio_path)

            logger.info(
                f"Processed video: {video_path}, "
                f"duration: {result.duration:.1f}s"
            )

            return VideoResult(
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
                width=width,
                height=height,
            )

        except Exception as e:
            logger.error(f"Failed to process video {video_path}: {e}")
            return None

        finally:
            # 一時ファイルを削除
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def index_video(
        self,
        video_path: Path | str,
        document_id: str,
    ) -> dict | None:
        """動画をインデックス化。

        Args:
            video_path: 動画ファイルのパス
            document_id: ドキュメントID

        Returns:
            Transcriptレコードまたはなし
        """
        result = self.process_video(video_path)
        if not result:
            return None

        video_path = Path(video_path)

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
                "path": str(video_path.absolute()),
                "filename": video_path.name,
                "media_type": "video",
            }
            chunk_records.append(chunk_record)
            fts_records.append({
                "id": chunk_id,
                "document_id": document_id,
                "text": chunk["text"],
                "path": str(video_path.absolute()),
                "filename": video_path.name,
            })

        # データベースに保存
        if chunk_records:
            self.lancedb_client.add_chunks(chunk_records)
            self.sqlite_client.add_chunks_fts(fts_records)

        logger.info(
            f"Indexed video: {video_path}, "
            f"chunks: {len(chunk_records)}"
        )

        return {
            "transcript": transcript,
            "width": result.width,
            "height": result.height,
        }

    def is_supported(self, file_path: Path | str) -> bool:
        """ファイルがサポートされているかを判定。

        Args:
            file_path: ファイルパス

        Returns:
            サポートされていればTrue
        """
        file_path = Path(file_path)
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
