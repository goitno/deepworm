"""Logging configuration for deepworm.

Provides structured logging with configurable levels and outputs.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional


_configured = False


def setup_logging(
    level: str = "WARNING",
    log_file: Optional[str] = None,
    structured: bool = False,
) -> logging.Logger:
    """Configure deepworm logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional file path for log output.
        structured: Use JSON structured logging format.

    Returns:
        The configured deepworm logger.
    """
    global _configured
    logger = logging.getLogger("deepworm")

    if _configured:
        logger.setLevel(getattr(logging, level.upper(), logging.WARNING))
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.WARNING))

    if structured:
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","module":"%(name)s","message":"%(message)s"}'
    else:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _configured = True
    return logger


def get_logger(name: str = "deepworm") -> logging.Logger:
    """Get a child logger.

    Args:
        name: Logger name, will be prefixed with 'deepworm.'.

    Returns:
        Logger instance.
    """
    if name == "deepworm" or name.startswith("deepworm."):
        return logging.getLogger(name)
    return logging.getLogger(f"deepworm.{name}")
