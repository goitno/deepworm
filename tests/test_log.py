"""Tests for deepworm.log — logging configuration."""

import logging
import tempfile
import os

from deepworm.log import get_logger, setup_logging


def test_get_logger():
    logger = get_logger("test")
    assert logger.name == "deepworm.test"


def test_get_logger_root():
    logger = get_logger("deepworm")
    assert logger.name == "deepworm"


def test_get_logger_prefixed():
    logger = get_logger("deepworm.sub")
    assert logger.name == "deepworm.sub"


def test_setup_logging_level():
    import deepworm.log as log_module
    log_module._configured = False
    logger = setup_logging(level="DEBUG")
    assert logger.level == logging.DEBUG
    log_module._configured = False  # reset for other tests


def test_setup_logging_file():
    import deepworm.log as log_module
    log_module._configured = False
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        path = f.name
    try:
        logger = setup_logging(level="INFO", log_file=path)
        logger.info("test message")
        # Should have written to file
        with open(path) as fh:
            content = fh.read()
        assert "test message" in content
    finally:
        os.unlink(path)
        log_module._configured = False
