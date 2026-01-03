"""メディアタイプ定数と判定ユーティリティ。"""

from pathlib import Path

from src.storage.schema import MediaType

# 画像拡張子
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".svg"}

# 動画拡張子
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".wmv", ".flv"}

# 音声拡張子
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma"}

# PDF拡張子
PDF_EXTENSIONS = {".pdf"}

# Office拡張子
OFFICE_EXTENSIONS = {".docx", ".xlsx", ".pptx"}

# テキスト拡張子
TEXT_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".xml", ".html"}

# メディア拡張子（動画 + 音声）
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS


def get_media_type(path: Path | str) -> MediaType:
    """ファイルパスからメディアタイプを判定。

    Args:
        path: ファイルパス

    Returns:
        メディアタイプ
    """
    if isinstance(path, str):
        path = Path(path)

    suffix = path.suffix.lower()

    if suffix in IMAGE_EXTENSIONS:
        return MediaType.IMAGE
    elif suffix in VIDEO_EXTENSIONS:
        return MediaType.VIDEO
    elif suffix in AUDIO_EXTENSIONS:
        return MediaType.AUDIO
    else:
        return MediaType.DOCUMENT


def is_media_file(path: Path | str) -> bool:
    """ファイルがメディアファイル（動画・音声）かどうかを判定。

    Args:
        path: ファイルパス

    Returns:
        メディアファイルならTrue
    """
    if isinstance(path, str):
        path = Path(path)

    suffix = path.suffix.lower()
    return suffix in MEDIA_EXTENSIONS
