"""エラー定義。

アプリケーション全体で使用するカスタムエラーを定義する。
"""

from fastapi import HTTPException, status


class LocalDocSearchError(Exception):
    """基底エラークラス。"""

    def __init__(self, message: str, details: dict | None = None):
        """初期化。

        Args:
            message: エラーメッセージ
            details: 詳細情報
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class FileNotFoundError(LocalDocSearchError):
    """ファイルが見つからないエラー。"""

    pass


class UnsupportedFileTypeError(LocalDocSearchError):
    """サポートされていないファイルタイプ。"""

    pass


class IndexingError(LocalDocSearchError):
    """インデックス化エラー。"""

    pass


class SearchError(LocalDocSearchError):
    """検索エラー。"""

    pass


class OllamaConnectionError(LocalDocSearchError):
    """Ollamaへの接続エラー。"""

    pass


class EmbeddingError(LocalDocSearchError):
    """Embedding生成エラー。"""

    pass


class TranscriptionError(LocalDocSearchError):
    """文字起こしエラー。"""

    pass


def to_http_exception(error: LocalDocSearchError) -> HTTPException:
    """カスタムエラーをHTTPExceptionに変換。

    Args:
        error: カスタムエラー

    Returns:
        HTTPException
    """
    if isinstance(error, FileNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": error.message, **error.details},
        )
    elif isinstance(error, UnsupportedFileTypeError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": error.message, **error.details},
        )
    elif isinstance(error, OllamaConnectionError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": error.message, **error.details},
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": error.message, **error.details},
        )
