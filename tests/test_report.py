"""Tests for deepworm.report."""

import os
import tempfile

from deepworm.report import _slugify, save_report


def test_slugify():
    assert _slugify("Hello World!") == "hello-world"
    assert _slugify("AI & Machine Learning") == "ai-machine-learning"
    assert _slugify("  spaces  ") == "spaces"


def test_slugify_long():
    long_text = "a" * 100
    assert len(_slugify(long_text)) <= 60


def test_save_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_report("# Test Report\n\nContent here.", os.path.join(tmpdir, "test.md"))
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "# Test Report" in content


def test_save_report_auto_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_report(
            "# Report",
            os.path.join(tmpdir, "auto.md"),
            topic="quantum computing",
        )
        assert os.path.exists(path)
