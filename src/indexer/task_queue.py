"""処理キュー。

ファイル処理タスクをキューイングして順次処理する。
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine

from src.config.logging import get_logger

logger = get_logger()


class TaskStatus(str, Enum):
    """タスクステータス。"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(str, Enum):
    """タスクタイプ。"""

    INDEX = "index"
    DELETE = "delete"
    UPDATE = "update"


@dataclass
class Task:
    """タスク。"""

    id: str
    task_type: TaskType
    path: Path
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result: dict[str, Any] | None = None
    retry_count: int = 0
    max_retries: int = 3


class TaskQueue:
    """タスクキュー。"""

    def __init__(self, max_size: int = 10000):
        """初期化。

        Args:
            max_size: キューの最大サイズ
        """
        self._queue: asyncio.Queue[Task] = asyncio.Queue(maxsize=max_size)
        self._processing: dict[str, Task] = {}
        self._completed: list[Task] = []
        self._failed: list[Task] = []
        self._running = False
        self._worker_task: asyncio.Task | None = None
        self._handler: Callable[[Task], Coroutine[Any, Any, dict[str, Any] | None]] | None = None

    def set_handler(
        self,
        handler: Callable[[Task], Coroutine[Any, Any, dict[str, Any] | None]],
    ) -> None:
        """タスクハンドラを設定。

        Args:
            handler: タスク処理関数
        """
        self._handler = handler

    async def add_task(
        self,
        task_type: TaskType,
        path: Path,
        task_id: str | None = None,
    ) -> Task:
        """タスクを追加。

        Args:
            task_type: タスクタイプ
            path: ファイルパス
            task_id: タスクID（指定しない場合は自動生成）

        Returns:
            作成されたタスク
        """
        import uuid

        task = Task(
            id=task_id or str(uuid.uuid4()),
            task_type=task_type,
            path=path,
        )
        await self._queue.put(task)
        logger.info(f"Task added: {task.id} ({task.task_type.value}) - {task.path}")
        return task

    async def _process_task(self, task: Task) -> None:
        """タスクを処理。

        Args:
            task: タスク
        """
        if self._handler is None:
            logger.error("No handler set for task queue")
            return

        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.now()
        self._processing[task.id] = task

        try:
            result = await self._handler(task)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            self._completed.append(task)
            logger.info(f"Task completed: {task.id}")
        except Exception as e:
            task.error = str(e)
            task.retry_count += 1

            if task.retry_count < task.max_retries:
                # リトライ
                task.status = TaskStatus.PENDING
                await self._queue.put(task)
                logger.warning(
                    f"Task failed, retrying ({task.retry_count}/{task.max_retries}): {task.id}"
                )
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                self._failed.append(task)
                logger.error(f"Task failed permanently: {task.id} - {e}")
        finally:
            self._processing.pop(task.id, None)

    async def _worker(self) -> None:
        """ワーカーループ。"""
        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._process_task(task)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")

    async def start(self) -> None:
        """キュー処理を開始。"""
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("Task queue started")

    async def stop(self) -> None:
        """キュー処理を停止。"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Task queue stopped")

    def get_stats(self) -> dict[str, int]:
        """統計情報を取得。

        Returns:
            統計情報の辞書
        """
        return {
            "pending": self._queue.qsize(),
            "processing": len(self._processing),
            "completed": len(self._completed),
            "failed": len(self._failed),
        }
