"""ファイルオープナー。

ファイルを開く機能を提供する。タイムスタンプ指定による動画・音声の位置再生をサポート。
"""

import subprocess
from pathlib import Path

from src.config.logging import get_logger
from src.constants.media_types import is_media_file

logger = get_logger()


class FileOpener:
    """ファイルオープナー。"""

    def open_file(
        self,
        file_path: Path | str,
        start_time: float | None = None,
    ) -> bool:
        """ファイルを開く。

        音声・動画ファイルの場合、start_timeを指定すると該当位置から再生する。

        Args:
            file_path: ファイルパス
            start_time: 開始時間（秒）

        Returns:
            成功したらTrue
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False

        is_media = is_media_file(file_path)

        try:
            if is_media and start_time is not None:
                return self._open_media_with_timestamp(file_path, start_time)
            else:
                return self._open_with_default_app(file_path)
        except Exception as e:
            logger.error(f"Failed to open file {file_path}: {e}")
            return False

    def _open_with_default_app(self, file_path: Path) -> bool:
        """デフォルトアプリで開く。

        Args:
            file_path: ファイルパス

        Returns:
            成功したらTrue
        """
        result = subprocess.run(
            ["open", str(file_path)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logger.info(f"Opened file: {file_path}")
            return True
        else:
            logger.error(f"Failed to open file: {result.stderr}")
            return False

    def _open_media_with_timestamp(self, file_path: Path, start_time: float) -> bool:
        """メディアファイルを指定位置から開く。

        VLCまたはIINAを使用してタイムスタンプ指定で開く。

        Args:
            file_path: ファイルパス
            start_time: 開始時間（秒）

        Returns:
            成功したらTrue
        """
        # VLCを試す
        if self._try_open_with_vlc(file_path, start_time):
            return True

        # IINAを試す
        if self._try_open_with_iina(file_path, start_time):
            return True

        # どちらもない場合は通常のオープン
        logger.warning(
            "VLC or IINA not found. Opening without timestamp. "
            "Install VLC or IINA for timestamp support."
        )
        return self._open_with_default_app(file_path)

    def _try_open_with_vlc(self, file_path: Path, start_time: float) -> bool:
        """VLCでタイムスタンプ指定で開く。

        Args:
            file_path: ファイルパス
            start_time: 開始時間（秒）

        Returns:
            成功したらTrue
        """
        vlc_paths = [
            "/Applications/VLC.app/Contents/MacOS/VLC",
            "/opt/homebrew/bin/vlc",
            "/usr/local/bin/vlc",
        ]

        vlc_path = None
        for path in vlc_paths:
            if Path(path).exists():
                vlc_path = path
                break

        if not vlc_path:
            return False

        try:
            subprocess.Popen(
                [
                    vlc_path,
                    f"--start-time={start_time}",
                    str(file_path),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"Opened with VLC at {start_time}s: {file_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to open with VLC: {e}")
            return False

    def _try_open_with_iina(self, file_path: Path, start_time: float) -> bool:
        """IINAでタイムスタンプ指定で開く。

        Args:
            file_path: ファイルパス
            start_time: 開始時間（秒）

        Returns:
            成功したらTrue
        """
        iina_paths = [
            "/Applications/IINA.app/Contents/MacOS/iina-cli",
            "/opt/homebrew/bin/iina",
            "/usr/local/bin/iina",
        ]

        iina_path = None
        for path in iina_paths:
            if Path(path).exists():
                iina_path = path
                break

        if not iina_path:
            return False

        try:
            subprocess.Popen(
                [
                    iina_path,
                    f"--mpv-start={start_time}",
                    str(file_path),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"Opened with IINA at {start_time}s: {file_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to open with IINA: {e}")
            return False

    def reveal_in_finder(self, file_path: Path | str) -> bool:
        """Finderでファイルの場所を表示。

        Args:
            file_path: ファイルパス

        Returns:
            成功したらTrue
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False

        try:
            result = subprocess.run(
                ["open", "-R", str(file_path)],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.info(f"Revealed in Finder: {file_path}")
                return True
            else:
                logger.error(f"Failed to reveal in Finder: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Failed to reveal in Finder {file_path}: {e}")
            return False

    def format_timestamp(self, seconds: float) -> str:
        """秒をタイムスタンプ形式に変換。

        Args:
            seconds: 秒数

        Returns:
            "HH:MM:SS" or "MM:SS" 形式
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
