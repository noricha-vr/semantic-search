"""テキストファイルプロセッサ。

.txt、.md、.pyなどのプレーンテキストファイルを処理する。
"""

from dataclasses import dataclass
from pathlib import Path

from src.config.logging import get_logger

logger = get_logger()

# サポートする拡張子
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".rst",
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".yaml",
    ".yml",
    ".json",
    ".xml",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".sql",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".gitignore",
    ".dockerfile",
    ".makefile",
    ".cmake",
    ".gradle",
    ".properties",
    ".csv",
    ".log",
}


@dataclass
class TextResult:
    """テキスト処理結果。"""

    text: str
    encoding: str
    line_count: int


class TextProcessor:
    """テキストファイルプロセッサ。"""

    def __init__(self, encodings: list[str] | None = None):
        """初期化。

        Args:
            encodings: 試行するエンコーディングのリスト
        """
        self.encodings = encodings or ["utf-8", "utf-16", "shift_jis", "euc-jp", "cp932"]

    def extract_text(self, file_path: Path | str) -> TextResult:
        """テキストファイルからテキストを抽出。

        Args:
            file_path: ファイルパス

        Returns:
            テキストと情報

        Raises:
            FileNotFoundError: ファイルが見つからない
            ValueError: エンコーディングの検出に失敗
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        text = None
        used_encoding = None

        for encoding in self.encodings:
            try:
                text = file_path.read_text(encoding=encoding)
                used_encoding = encoding
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if text is None:
            raise ValueError(f"Failed to decode file: {file_path}")

        line_count = text.count("\n") + 1 if text else 0

        logger.info(
            f"Extracted text from: {file_path}, "
            f"encoding: {used_encoding}, lines: {line_count}"
        )

        return TextResult(
            text=text,
            encoding=used_encoding,
            line_count=line_count,
        )

    def is_supported(self, file_path: Path | str) -> bool:
        """ファイルがサポートされているかを判定。

        Args:
            file_path: ファイルパス

        Returns:
            サポートされていればTrue
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        # 拡張子がない場合、ファイル名自体をチェック
        if not suffix:
            name_lower = file_path.name.lower()
            return name_lower in {"makefile", "dockerfile", "rakefile", "gemfile"}

        return suffix in TEXT_EXTENSIONS
