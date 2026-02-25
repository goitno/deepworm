"""Tests for deepworm CLI."""

import subprocess
import sys

import pytest

from deepworm.__main__ import build_parser, _copy_to_clipboard


def test_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["test topic"])
    assert args.topic == "test topic"
    assert args.depth is None
    assert args.breadth is None
    assert args.model is None
    assert args.provider is None
    assert args.output is None
    assert args.quiet is False
    assert args.json_output is False
    assert args.interactive is False
    assert args.copy is False
    assert args.no_followup is False


def test_parser_all_flags():
    parser = build_parser()
    args = parser.parse_args([
        "my topic",
        "-d", "3",
        "-b", "6",
        "-m", "gpt-4o",
        "-p", "openai",
        "-o", "report.md",
        "-q",
        "--json",
    ])
    assert args.topic == "my topic"
    assert args.depth == 3
    assert args.breadth == 6
    assert args.model == "gpt-4o"
    assert args.provider == "openai"
    assert args.output == "report.md"
    assert args.quiet is True
    assert args.json_output is True


def test_parser_interactive_flag():
    parser = build_parser()
    args = parser.parse_args(["topic", "-i"])
    assert args.interactive is True


def test_parser_interactive_long_flag():
    parser = build_parser()
    args = parser.parse_args(["topic", "--interactive"])
    assert args.interactive is True


def test_parser_copy_flag():
    parser = build_parser()
    args = parser.parse_args(["topic", "--copy"])
    assert args.copy is True


def test_parser_no_followup_flag():
    parser = build_parser()
    args = parser.parse_args(["topic", "--no-followup"])
    assert args.no_followup is True


def test_parser_template_flag():
    parser = build_parser()
    args = parser.parse_args(["topic", "-t", "academic"])
    assert args.template == "academic"


def test_parser_combined_new_flags():
    parser = build_parser()
    args = parser.parse_args(["topic", "-i", "--copy", "--no-followup", "-t", "quick"])
    assert args.interactive is True
    assert args.copy is True
    assert args.no_followup is True
    assert args.template == "quick"


def test_copy_to_clipboard_runs(monkeypatch):
    """Clipboard function runs without error on supported platforms."""
    calls = []

    class FakeProc:
        def communicate(self, data):
            calls.append(data)

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: FakeProc())
    _copy_to_clipboard("test report")
    assert len(calls) == 1
    assert b"test report" in calls[0]


def test_parser_score_flag():
    parser = build_parser()
    args = parser.parse_args(["topic", "--score"])
    assert args.score is True


def test_parser_sections_flag():
    parser = build_parser()
    args = parser.parse_args(["topic", "--sections", "Summary|Findings"])
    assert args.sections == "Summary|Findings"


def test_parser_timeout_flag():
    parser = build_parser()
    args = parser.parse_args(["topic", "--timeout", "120"])
    assert args.timeout == 120


def test_parser_diff_flag():
    parser = build_parser()
    args = parser.parse_args(["--diff", "old.md", "new.md"])
    assert args.diff == ["old.md", "new.md"]


def test_parser_toc_and_stats():
    parser = build_parser()
    args = parser.parse_args(["topic", "--toc", "--stats"])
    assert args.toc is True
    assert args.stats is True


def test_parser_polish_flag():
    parser = build_parser()
    args = parser.parse_args(["topic", "--polish"])
    assert args.polish is True


def test_parser_polish_default():
    parser = build_parser()
    args = parser.parse_args(["topic"])
    assert args.polish is False


def test_parser_graph_flag_default():
    parser = build_parser()
    args = parser.parse_args(["topic", "--graph"])
    assert args.graph == "mermaid"


def test_parser_graph_flag_dot():
    parser = build_parser()
    args = parser.parse_args(["topic", "--graph", "dot"])
    assert args.graph == "dot"


def test_parser_graph_flag_stats():
    parser = build_parser()
    args = parser.parse_args(["topic", "--graph", "stats"])
    assert args.graph == "stats"


def test_parser_graph_flag_json():
    parser = build_parser()
    args = parser.parse_args(["topic", "--graph", "json"])
    assert args.graph == "json"


def test_parser_graph_no_flag():
    parser = build_parser()
    args = parser.parse_args(["topic"])
    assert args.graph is None


def test_parser_polish_and_graph_combined():
    parser = build_parser()
    args = parser.parse_args(["topic", "--polish", "--graph", "stats"])
    assert args.polish is True
    assert args.graph == "stats"


def test_interactive_shell_help_function():
    """Test that _show_help runs without error."""
    from deepworm.__main__ import _show_help
    _show_help()  # Should not raise


def test_interactive_shell_config_function():
    """Test that _show_config runs without error."""
    from deepworm.__main__ import _show_config
    from deepworm.config import Config
    config = Config.auto()
    _show_config(config)  # Should not raise


def test_interactive_shell_models_function():
    """Test that _show_models runs without error."""
    from deepworm.__main__ import _show_models
    from deepworm.config import Config
    config = Config.auto()
    _show_models(config)  # Should not raise


def test_interactive_polish_inline():
    """Test that _run_polish_inline runs without error."""
    from deepworm.__main__ import _run_polish_inline
    sample = "# Title\n\n## Intro\n\nSome text here.\n\n## Sources\n\n1. [x](http://x.com)\n"
    _run_polish_inline(sample)  # Should not raise


def test_interactive_graph_inline():
    """Test that _run_graph_inline runs without error."""
    from deepworm.__main__ import _run_graph_inline
    sample = "# Title\n\n## Intro\n\nSome text here.\n\n## Sources\n\n1. [x](http://x.com)\n"
    _run_graph_inline(sample)  # Should not raise
