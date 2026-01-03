"""file_watcherのテスト。"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.indexer.file_watcher import AsyncFileWatcher, FileEventHandler, FileWatcher


class TestFileEventHandler:
    """FileEventHandlerのテスト。"""

    @pytest.fixture
    def callback(self):
        """モックコールバック。"""
        return MagicMock()

    @pytest.fixture
    def handler(self, callback):
        """FileEventHandler。"""
        return FileEventHandler(callback)

    def test_init(self, handler, callback):
        """初期化が正しく行われる。"""
        assert handler.callback == callback
        assert ".DS_Store" in handler._ignore_patterns
        assert ".git" in handler._ignore_patterns

    def test_should_ignore_ds_store(self, handler):
        """DS_Storeを無視する。"""
        assert handler._should_ignore("/path/.DS_Store") is True

    def test_should_ignore_git(self, handler):
        """gitディレクトリを無視する。"""
        assert handler._should_ignore("/path/.git/config") is True

    def test_should_ignore_pycache(self, handler):
        """__pycache__を無視する。"""
        assert handler._should_ignore("/path/__pycache__/file.pyc") is True

    def test_should_ignore_node_modules(self, handler):
        """node_modulesを無視する。"""
        assert handler._should_ignore("/path/node_modules/package") is True

    def test_should_not_ignore_normal_file(self, handler):
        """通常ファイルは無視しない。"""
        assert handler._should_ignore("/path/document.txt") is False

    def test_on_created_calls_callback(self, handler, callback):
        """ファイル作成イベントでコールバックが呼ばれる。"""
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/file.txt"

        handler.on_created(event)

        callback.assert_called_once_with("created", Path("/path/to/file.txt"))

    def test_on_created_ignores_directory(self, handler, callback):
        """ディレクトリ作成イベントは無視する。"""
        event = MagicMock()
        event.is_directory = True
        event.src_path = "/path/to/dir"

        handler.on_created(event)

        callback.assert_not_called()

    def test_on_created_ignores_ds_store(self, handler, callback):
        """DS_Storeファイルは無視する。"""
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/.DS_Store"

        handler.on_created(event)

        callback.assert_not_called()

    def test_on_modified_calls_callback(self, handler, callback):
        """ファイル変更イベントでコールバックが呼ばれる。"""
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/file.txt"

        handler.on_modified(event)

        callback.assert_called_once_with("modified", Path("/path/to/file.txt"))

    def test_on_deleted_calls_callback(self, handler, callback):
        """ファイル削除イベントでコールバックが呼ばれる。"""
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/file.txt"

        handler.on_deleted(event)

        callback.assert_called_once_with("deleted", Path("/path/to/file.txt"))

    def test_on_moved_calls_callback_twice(self, handler, callback):
        """ファイル移動イベントで削除と作成コールバックが呼ばれる。"""
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/old.txt"
        event.dest_path = "/path/new.txt"

        handler.on_moved(event)

        assert callback.call_count == 2
        callback.assert_any_call("deleted", Path("/path/old.txt"))
        callback.assert_any_call("created", Path("/path/new.txt"))


class TestFileWatcher:
    """FileWatcherのテスト。"""

    @pytest.fixture
    def callback(self):
        """モックコールバック。"""
        return MagicMock()

    @pytest.fixture
    def watcher(self, callback):
        """FileWatcher。"""
        return FileWatcher(callback)

    def test_init(self, watcher, callback):
        """初期化が正しく行われる。"""
        assert watcher.callback == callback
        assert watcher.observer is not None
        assert watcher.event_handler is not None
        assert watcher._watched_paths == []

    def test_add_watch_existing_path(self, watcher, tmp_path):
        """存在するパスを監視対象に追加できる。"""
        watcher.add_watch(tmp_path)

        assert str(tmp_path) in watcher._watched_paths

    def test_add_watch_nonexistent_path(self, watcher, tmp_path):
        """存在しないパスは追加されない。"""
        nonexistent = tmp_path / "nonexistent"

        watcher.add_watch(nonexistent)

        assert watcher._watched_paths == []

    def test_add_watch_string_path(self, watcher, tmp_path):
        """文字列パスを受け入れる。"""
        watcher.add_watch(str(tmp_path))

        assert str(tmp_path) in watcher._watched_paths

    def test_add_watch_expands_user(self, watcher):
        """チルダをユーザーディレクトリに展開する。"""
        with patch.object(Path, "exists", return_value=True):
            with patch.object(watcher.observer, "schedule"):
                watcher.add_watch("~/test")

                expanded = Path("~/test").expanduser()
                assert str(expanded) in watcher._watched_paths

    @patch("src.indexer.file_watcher.Observer")
    def test_start(self, mock_observer_class, callback):
        """監視を開始できる。"""
        mock_observer = MagicMock()
        mock_observer_class.return_value = mock_observer

        watcher = FileWatcher(callback)
        watcher.start()

        mock_observer.start.assert_called_once()

    @patch("src.indexer.file_watcher.Observer")
    def test_stop(self, mock_observer_class, callback):
        """監視を停止できる。"""
        mock_observer = MagicMock()
        mock_observer_class.return_value = mock_observer

        watcher = FileWatcher(callback)
        watcher.stop()

        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()

    @patch("src.indexer.file_watcher.Observer")
    def test_is_running(self, mock_observer_class, callback):
        """監視中かどうかを確認できる。"""
        mock_observer = MagicMock()
        mock_observer.is_alive.return_value = True
        mock_observer_class.return_value = mock_observer

        watcher = FileWatcher(callback)

        assert watcher.is_running() is True


class TestAsyncFileWatcher:
    """AsyncFileWatcherのテスト。"""

    def test_init(self):
        """初期化が正しく行われる。"""
        watcher = AsyncFileWatcher()

        assert watcher._queue is None
        assert watcher._watcher is None

    @pytest.mark.asyncio
    async def test_start(self, tmp_path):
        """監視を開始できる。"""
        watcher = AsyncFileWatcher()

        await watcher.start([tmp_path])

        assert watcher._queue is not None
        assert watcher._watcher is not None
        assert watcher._watcher.is_running()

        await watcher.stop()

    @pytest.mark.asyncio
    async def test_stop(self, tmp_path):
        """監視を停止できる。"""
        watcher = AsyncFileWatcher()
        await watcher.start([tmp_path])

        await watcher.stop()

        assert watcher._watcher is not None
        assert not watcher._watcher.is_running()

    @pytest.mark.asyncio
    async def test_get_event_raises_without_start(self):
        """開始前にget_eventを呼ぶとエラー。"""
        watcher = AsyncFileWatcher()

        with pytest.raises(RuntimeError, match="Watcher not started"):
            await watcher.get_event()

    @pytest.mark.asyncio
    async def test_on_event_queues_event(self, tmp_path):
        """イベントがキューに追加される。"""
        watcher = AsyncFileWatcher()
        await watcher.start([tmp_path])

        # 直接イベントを発生させる
        watcher._on_event("created", Path("/test/file.txt"))

        event = await asyncio.wait_for(watcher.get_event(), timeout=1.0)
        assert event == ("created", Path("/test/file.txt"))

        await watcher.stop()

    @pytest.mark.asyncio
    async def test_on_event_handles_full_queue(self, tmp_path):
        """キューが満杯でもエラーにならない。"""
        watcher = AsyncFileWatcher()
        watcher._queue = asyncio.Queue(maxsize=1)

        # キューを満杯にする
        await watcher._queue.put(("test", Path("/test")))

        # これはエラーにならずに警告ログを出す
        watcher._on_event("created", Path("/test/file.txt"))

        # キューにはまだ1つだけ
        assert watcher._queue.qsize() == 1
