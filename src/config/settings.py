"""設定管理モジュール。

Pydantic Settingsを使用して環境変数と設定ファイルを統合管理する。
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション設定。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Ollama
    ollama_host: str = Field(
        default="http://localhost:11434",
        description="OllamaサーバーのURL",
    )

    # API
    api_host: str = Field(default="0.0.0.0", description="APIサーバーのホスト")
    api_port: int = Field(default=2602, description="APIサーバーのポート")

    # Data
    data_dir: Path = Field(
        default=Path("~/.local/share/local-doc-search"),
        description="データディレクトリ",
    )

    # Logging
    log_level: str = Field(default="INFO", description="ログレベル")

    # Models
    embedding_model: str = Field(default="bge-m3", description="Embeddingモデル名")
    vlm_model: str = Field(default="llava:7b", description="VLMモデル名")
    reranker_model: str = Field(
        default="bge-reranker-v2-m3", description="リランカーモデル名"
    )

    # Chunking
    chunk_size: int = Field(default=800, description="チャンクサイズ（文字数）")
    chunk_overlap: int = Field(default=200, description="チャンクのオーバーラップ（文字数）")

    # PDF Processing
    pdf_use_markdown: bool = Field(
        default=True, description="PyMuPDF4LLMでMarkdown抽出を使用"
    )
    pdf_min_chars_per_page: int = Field(
        default=100, description="VLMフォールバック閾値（1ページあたりの最小文字数）"
    )
    pdf_vlm_fallback: bool = Field(
        default=True, description="テキスト少量時にVLMフォールバックを有効化"
    )
    pdf_vlm_dpi: int = Field(default=150, description="VLM処理時のPDF→画像変換DPI")
    pdf_vlm_model: str = Field(
        default="minicpm-v", description="PDF VLM処理用モデル"
    )
    pdf_vlm_timeout: int = Field(
        default=60, description="VLM処理の1ページあたりのタイムアウト（秒）"
    )
    pdf_vlm_max_pages: int = Field(
        default=20, description="VLM処理する最大ページ数（0で無制限）"
    )
    pdf_vlm_workers: int = Field(
        default=2, description="VLM並列処理のワーカー数（1で順次処理）"
    )

    @field_validator("data_dir", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path) -> Path:
        """パスを展開する。"""
        return Path(v).expanduser()

    @property
    def lancedb_path(self) -> Path:
        """LanceDBのパス。"""
        return self.data_dir / "lancedb"

    @property
    def sqlite_path(self) -> Path:
        """SQLiteのパス。"""
        return self.data_dir / "fts.sqlite"

    @property
    def logs_dir(self) -> Path:
        """ログディレクトリ。"""
        return Path("logs")


@lru_cache
def get_settings() -> Settings:
    """設定を取得する（シングルトン）。

    Returns:
        設定インスタンス
    """
    return Settings()
