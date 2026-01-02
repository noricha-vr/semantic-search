"""Whisper文字起こしクライアント。

mlx-whisperを使用して音声をテキストに変換する。
"""

from dataclasses import dataclass
from pathlib import Path

from src.config.logging import get_logger

logger = get_logger()


@dataclass
class TranscriptSegment:
    """文字起こしセグメント。"""

    text: str
    start: float
    end: float


@dataclass
class TranscriptResult:
    """文字起こし結果。"""

    text: str
    segments: list[TranscriptSegment]
    language: str
    duration: float


class WhisperClient:
    """Whisperクライアント。"""

    def __init__(self, model: str = "large-v3-turbo"):
        """初期化。

        Args:
            model: モデル名
        """
        self.model = model
        self._model_loaded = False

    def _load_model(self):
        """モデルをロード。"""
        if self._model_loaded:
            return

        try:
            import mlx_whisper

            self._mlx_whisper = mlx_whisper
            self._model_loaded = True
            logger.info(f"Loaded Whisper model: {self.model}")
        except ImportError as e:
            logger.error(f"Failed to import mlx_whisper: {e}")
            raise

    def transcribe(
        self,
        audio_path: Path | str,
        language: str | None = None,
    ) -> TranscriptResult:
        """音声ファイルを文字起こし。

        Args:
            audio_path: 音声ファイルのパス
            language: 言語コード（Noneの場合は自動検出）

        Returns:
            文字起こし結果
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self._load_model()

        try:
            # mlx-whisperで文字起こし
            result = self._mlx_whisper.transcribe(
                str(audio_path),
                path_or_hf_repo=f"mlx-community/whisper-{self.model}",
                word_timestamps=True,
            )

            # セグメントを変換
            segments = []
            for seg in result.get("segments", []):
                segments.append(
                    TranscriptSegment(
                        text=seg.get("text", "").strip(),
                        start=seg.get("start", 0),
                        end=seg.get("end", 0),
                    )
                )

            # 全文テキストを構築
            full_text = result.get("text", "").strip()
            if not full_text and segments:
                full_text = " ".join(s.text for s in segments)

            # 言語を取得
            detected_language = result.get("language", language or "unknown")

            # 長さを計算
            duration = 0.0
            if segments:
                duration = segments[-1].end

            logger.info(
                f"Transcribed: {audio_path}, "
                f"language: {detected_language}, "
                f"duration: {duration:.1f}s, "
                f"segments: {len(segments)}"
            )

            return TranscriptResult(
                text=full_text,
                segments=segments,
                language=detected_language,
                duration=duration,
            )

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def transcribe_to_dict(
        self,
        audio_path: Path | str,
        language: str | None = None,
    ) -> dict:
        """音声ファイルを文字起こしして辞書で返す。

        Args:
            audio_path: 音声ファイルのパス
            language: 言語コード

        Returns:
            文字起こし結果の辞書
        """
        result = self.transcribe(audio_path, language)
        return {
            "text": result.text,
            "segments": [
                {
                    "text": s.text,
                    "start": s.start,
                    "end": s.end,
                }
                for s in result.segments
            ],
            "language": result.language,
            "duration": result.duration,
        }
