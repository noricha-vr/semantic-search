"""メディア処理の基底クラス。"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseMediaProcessor(ABC):
    """メディア処理の基底クラス。"""

    @abstractmethod
    def can_process(self, file_path: Path) -> bool:
        """このプロセッサで処理可能か判定。

        Args:
            file_path: ファイルパス

        Returns:
            処理可能ならTrue
        """
        pass

    @abstractmethod
    def process(self, file_path: Path, content_hash: str) -> dict[str, Any] | None:
        """ファイルを処理してドキュメントレコードを返す。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントレコードまたはNone
        """
        pass
