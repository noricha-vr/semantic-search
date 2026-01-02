"""ログ設定モジュール。

構造化ログ（JSON形式）の設定を提供する。
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JSONFormatter(logging.Formatter):
    """JSON形式でログを出力するフォーマッタ。"""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": record.levelname.lower(),
            "source": record.name,
            "summary": record.getMessage(),
        }

        if record.exc_info:
            log_data["stack_trace"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data"):
            log_data["detail"] = record.extra_data

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    log_level: str = "INFO",
    log_dir: Path | None = None,
    app_name: str = "local-doc-search",
) -> logging.Logger:
    """ロガーを設定して返す。

    Args:
        log_level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_dir: ログファイルの保存ディレクトリ
        app_name: アプリケーション名

    Returns:
        設定済みのロガー
    """
    logger = logging.getLogger(app_name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    json_formatter = JSONFormatter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{app_name}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "local-doc-search") -> logging.Logger:
    """既存のロガーを取得する。

    Args:
        name: ロガー名

    Returns:
        ロガーインスタンス
    """
    return logging.getLogger(name)
