"""自動インデクサー。

ファイル監視とインデクサーを統合して自動インデックスを実行する。
"""

import asyncio
from pathlib import Path
from typing import Any

from src.config.logging import get_logger
from src.indexer.document_indexer import DocumentIndexer
from src.indexer.file_watcher import AsyncFileWatcher
from src.indexer.task_queue import Task, TaskQueue, TaskType

logger = get_logger()


class AutoIndexer:
    """自動インデクサー。"""

    def __init__(self):
        """初期化。"""
        self._indexer = DocumentIndexer()
        self._watcher = AsyncFileWatcher()
        self._queue = TaskQueue()
        self._queue.set_handler(self._handle_task)
        self._running = False
        self._event_task: asyncio.Task | None = None

    async def _handle_task(self, task: Task) -> dict[str, Any] | None:
        """タスクを処理。

        Args:
            task: タスク

        Returns:
            処理結果
        """
        if task.task_type == TaskType.INDEX:
            # ファイルが存在することを確認
            if not task.path.exists():
                logger.warning(f"File no longer exists: {task.path}")
                return None

            # インデックス化を実行（同期処理を非同期で実行）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._indexer.index_file,
                task.path,
            )
            return result

        elif task.task_type == TaskType.DELETE:
            # 削除処理（まだ実装していない）
            logger.info(f"Delete task for: {task.path}")
            return None

        elif task.task_type == TaskType.UPDATE:
            # 更新 = 削除 + インデックス
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._indexer.index_file,
                task.path,
            )
            return result

        return None

    async def _event_loop(self) -> None:
        """イベントループ。"""
        while self._running:
            try:
                event_type, path = await self._watcher.get_event()

                if event_type == "created":
                    await self._queue.add_task(TaskType.INDEX, path)
                elif event_type == "modified":
                    await self._queue.add_task(TaskType.UPDATE, path)
                elif event_type == "deleted":
                    await self._queue.add_task(TaskType.DELETE, path)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event loop error: {e}")

    async def start(self, watch_paths: list[Path | str]) -> None:
        """自動インデックスを開始。

        Args:
            watch_paths: 監視するディレクトリパスのリスト
        """
        self._running = True

        # ファイル監視を開始
        await self._watcher.start(watch_paths)

        # タスクキューを開始
        await self._queue.start()

        # イベントループを開始
        self._event_task = asyncio.create_task(self._event_loop())

        logger.info(f"Auto indexer started, watching: {watch_paths}")

    async def stop(self) -> None:
        """自動インデックスを停止。"""
        self._running = False

        if self._event_task:
            self._event_task.cancel()
            try:
                await self._event_task
            except asyncio.CancelledError:
                pass

        await self._queue.stop()
        await self._watcher.stop()

        logger.info("Auto indexer stopped")

    def get_stats(self) -> dict[str, Any]:
        """統計情報を取得。

        Returns:
            統計情報の辞書
        """
        return self._queue.get_stats()


async def run_auto_indexer(watch_paths: list[Path | str]) -> None:
    """自動インデクサーを実行。

    Args:
        watch_paths: 監視するディレクトリパスのリスト
    """
    indexer = AutoIndexer()
    await indexer.start(watch_paths)

    try:
        # Ctrl+Cで終了するまで待機
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await indexer.stop()
