"""FFmpeg音声抽出ユーティリティ。

動画ファイルから音声を抽出する。
"""

import subprocess
import tempfile
from pathlib import Path

from src.config.logging import get_logger

logger = get_logger()


class FFmpegError(Exception):
    """FFmpegエラー。"""

    pass


def check_ffmpeg_available() -> bool:
    """FFmpegが利用可能かチェック。

    Returns:
        利用可能ならTrue
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def extract_audio(
    input_path: Path | str,
    output_path: Path | str | None = None,
    output_format: str = "wav",
    sample_rate: int = 16000,
) -> Path:
    """動画/音声ファイルから音声を抽出。

    Args:
        input_path: 入力ファイルパス
        output_path: 出力ファイルパス（Noneの場合は一時ファイル）
        output_format: 出力形式（wav, mp3など）
        sample_rate: サンプルレート

    Returns:
        出力ファイルのパス

    Raises:
        FFmpegError: FFmpegでのエラー
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_path is None:
        # 一時ファイルを作成
        temp_dir = tempfile.mkdtemp()
        output_path = Path(temp_dir) / f"audio.{output_format}"
    else:
        output_path = Path(output_path)

    # 出力ディレクトリを作成
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # FFmpegコマンドを構築
    cmd = [
        "ffmpeg",
        "-i",
        str(input_path),
        "-vn",  # ビデオを無効化
        "-acodec",
        "pcm_s16le" if output_format == "wav" else "libmp3lame",
        "-ar",
        str(sample_rate),
        "-ac",
        "1",  # モノラル
        "-y",  # 上書き確認なし
        str(output_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1時間タイムアウト
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise FFmpegError(f"FFmpeg failed: {result.stderr}")

        logger.info(f"Extracted audio: {input_path} -> {output_path}")
        return output_path

    except subprocess.TimeoutExpired:
        raise FFmpegError("FFmpeg timeout")


def get_media_duration(file_path: Path | str) -> float | None:
    """メディアファイルの長さを取得。

    Args:
        file_path: ファイルパス

    Returns:
        長さ（秒）またはNone
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return None

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(file_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            duration = float(result.stdout.strip())
            return duration
        return None

    except (subprocess.TimeoutExpired, ValueError):
        return None


def get_media_info(file_path: Path | str) -> dict | None:
    """メディアファイルの情報を取得。

    Args:
        file_path: ファイルパス

    Returns:
        メディア情報またはNone
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return None

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=width,height,duration,codec_name,codec_type",
        "-show_entries",
        "format=duration,size,format_name",
        "-of",
        "json",
        str(file_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            import json

            data = json.loads(result.stdout)
            info = {
                "duration": None,
                "width": None,
                "height": None,
                "format": None,
            }

            if "format" in data:
                fmt = data["format"]
                info["duration"] = float(fmt.get("duration", 0))
                info["format"] = fmt.get("format_name")

            if "streams" in data:
                for stream in data["streams"]:
                    if stream.get("codec_type") == "video":
                        info["width"] = stream.get("width")
                        info["height"] = stream.get("height")
                        break

            return info
        return None

    except (subprocess.TimeoutExpired, ValueError):
        return None
