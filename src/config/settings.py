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
    api_host: str = Field(default="127.0.0.1", description="APIサーバーのホスト")
    api_port: int = Field(default=8765, description="APIサーバーのポート")

    # Data
    data_dir: Path = Field(
        default=Path("~/.local/share/local-doc-search"),
        description="データディレクトリ",
    )

    # Logging
    log_level: str = Field(default="INFO", description="ログレベル")

    # Models
    embedding_model: str = Field(default="bge-m3", description="Embeddingモデル名")
    vlm_model: str = Field(default="qwen2.5-vl:7b", description="VLMモデル名")
    reranker_model: str = Field(
        default="bge-reranker-v2-m3", description="リランカーモデル名"
    )

    # Chunking
    chunk_size: int = Field(default=800, description="チャンクサイズ（文字数）")
    chunk_overlap: int = Field(default=200, description="チャンクのオーバーラップ（文字数）")

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
