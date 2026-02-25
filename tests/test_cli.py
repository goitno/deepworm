"""Tests for deepworm CLI."""

from deepworm.__main__ import build_parser


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
