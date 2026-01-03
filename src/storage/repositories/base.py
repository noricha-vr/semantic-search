"""リポジトリ基底クラス。"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


class BaseRepository:
    """リポジトリの基底クラス。

    データベース接続の共通処理を提供する。
    """

    def __init__(self, db_path: Path):
        """初期化。

        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = db_path

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """データベース接続を取得。

        Yields:
            SQLite接続オブジェクト
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
