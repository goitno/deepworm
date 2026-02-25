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
