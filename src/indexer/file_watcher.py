"""ファイル監視サービス。

watchdogを使用してファイル変更を検出する。
"""

import asyncio
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from src.config.logging import get_logger

logger = get_logger()


class FileEventHandler(FileSystemEventHandler):
    """ファイルイベントハンドラ。"""

    def __init__(self, callback: Callable[[str, Path], None]):
        """初期化。

        Args:
            callback: イベント発生時に呼び出すコールバック関数
        """
        self.callback = callback
        self._ignore_patterns = {
            ".DS_Store",
            ".git",
            "__pycache__",
            ".pyc",
            ".venv",
            "node_modules",
        }

    def _should_ignore(self, path: str) -> bool:
        """無視すべきパスかどうかを判定。"""
        for pattern in self._ignore_patterns:
            if pattern in path:
                return True
        return False

    def on_created(self, event: FileSystemEvent) -> None:
        """ファイル作成イベント。"""
        if event.is_directory or self._should_ignore(event.src_path):
            return
        logger.info(f"File created: {event.src_path}")
        self.callback("created", Path(event.src_path))

    def on_modified(self, event: FileSystemEvent) -> None:
        """ファイル変更イベント。"""
        if event.is_directory or self._should_ignore(event.src_path):
            return
        logger.info(f"File modified: {event.src_path}")
        self.callback("modified", Path(event.src_path))

    def on_deleted(self, event: FileSystemEvent) -> None:
        """ファイル削除イベント。"""
        if event.is_directory or self._should_ignore(event.src_path):
            return
        logger.info(f"File deleted: {event.src_path}")
        self.callback("deleted", Path(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        """ファイル移動イベント。"""
        if event.is_directory or self._should_ignore(event.src_path):
            return
        logger.info(f"File moved: {event.src_path} -> {event.dest_path}")
        self.callback("deleted", Path(event.src_path))
        self.callback("created", Path(event.dest_path))


class FileWatcher:
    """ファイル監視クラス。"""

    def __init__(self, callback: Callable[[str, Path], None]):
        """初期化。

        Args:
            callback: イベント発生時に呼び出すコールバック関数
        """
        self.callback = callback
        self.observer = Observer()
        self.event_handler = FileEventHandler(callback)
        self._watched_paths: list[str] = []

    def add_watch(self, path: Path | str, recursive: bool = True) -> None:
        """監視対象を追加。

        Args:
            path: 監視するディレクトリパス
            recursive: サブディレクトリも監視するか
        """
        path = Path(path).expanduser()
        if not path.exists():
            logger.warning(f"Path does not exist: {path}")
            return

        self.observer.schedule(self.event_handler, str(path), recursive=recursive)
        self._watched_paths.append(str(path))
        logger.info(f"Watching: {path}")

    def start(self) -> None:
        """監視を開始。"""
        self.observer.start()
        logger.info("File watcher started")

    def stop(self) -> None:
        """監視を停止。"""
        self.observer.stop()
        self.observer.join()
        logger.info("File watcher stopped")

    def is_running(self) -> bool:
        """監視中かどうか。"""
        return self.observer.is_alive()


class AsyncFileWatcher:
    """非同期ファイル監視クラス。"""

    def __init__(self):
        """初期化。"""
        self._queue: asyncio.Queue | None = None
        self._watcher: FileWatcher | None = None

    def _on_event(self, event_type: str, path: Path) -> None:
        """イベントハンドラ。"""
        if self._queue:
            try:
                self._queue.put_nowait((event_type, path))
            except asyncio.QueueFull:
                logger.warning("Event queue is full, dropping event")

    async def start(self, paths: list[Path | str]) -> None:
        """監視を開始。

        Args:
            paths: 監視するディレクトリパスのリスト
        """
        self._queue = asyncio.Queue(maxsize=1000)
        self._watcher = FileWatcher(self._on_event)

        for path in paths:
            self._watcher.add_watch(path)

        self._watcher.start()

    async def stop(self) -> None:
        """監視を停止。"""
        if self._watcher:
            self._watcher.stop()

    async def get_event(self) -> tuple[str, Path]:
        """イベントを取得。

        Returns:
            (イベントタイプ, パス)のタプル
        """
        if self._queue is None:
            raise RuntimeError("Watcher not started")
        return await self._queue.get()
