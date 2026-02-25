"""Tests for deepworm.cli_helpers module."""

import os

import pytest

from deepworm.cli_helpers import (
    CLIArg,
    CLICommand,
    Color,
    OutputFormat,
    ProgressBar,
    Spinner,
    Verbosity,
    bold,
    blue,
    colorize,
    create_progress_bar,
    create_spinner,
    cyan,
    dim,
    draw_box,
    format_duration,
    format_help,
    format_key_value,
    format_list,
    format_percentage,
    format_size,
    format_table_simple,
    green,
    indent_text,
    pad_left,
    pad_right,
    parse_args,
    red,
    truncate,
    yellow,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:
    def test_color_values(self):
        assert Color.RED.value == "\033[31m"
        assert Color.RESET.value == "\033[0m"
        assert Color.BOLD.value == "\033[1m"

    def test_output_format(self):
        assert OutputFormat.PLAIN.value == "plain"
        assert OutputFormat.COLORED.value == "colored"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.MARKDOWN.value == "markdown"

    def test_verbosity(self):
        assert Verbosity.SILENT.value == 0
        assert Verbosity.NORMAL.value == 2
        assert Verbosity.DEBUG.value == 4


# ---------------------------------------------------------------------------
# Color functions
# ---------------------------------------------------------------------------


class TestColors:
    def test_colorize_no_color(self):
        os.environ["NO_COLOR"] = "1"
        try:
            result = colorize("hello", Color.RED)
            assert result == "hello"
        finally:
            del os.environ["NO_COLOR"]

    def test_color_helpers(self):
        # Just check they return strings (terminal may or may not support color)
        assert isinstance(red("test"), str)
        assert isinstance(green("test"), str)
        assert isinstance(yellow("test"), str)
        assert isinstance(blue("test"), str)
        assert isinstance(cyan("test"), str)
        assert isinstance(bold("test"), str)
        assert isinstance(dim("test"), str)


# ---------------------------------------------------------------------------
# Text formatting
# ---------------------------------------------------------------------------


class TestTextFormatting:
    def test_truncate(self):
        assert truncate("hello", 10) == "hello"
        assert truncate("hello world this is long", 10) == "hello w..."
        assert truncate("hello world", 10, "…") == "hello wor…"

    def test_pad_right(self):
        assert pad_right("hi", 5) == "hi   "
        assert pad_right("hello", 3) == "hello"

    def test_pad_left(self):
        assert pad_left("42", 5) == "   42"
        assert pad_left("hello", 3) == "hello"

    def test_indent_text(self):
        result = indent_text("line1\nline2", spaces=4)
        assert result == "    line1\n    line2"

    def test_format_size(self):
        assert format_size(500) == "500B"
        assert format_size(1500) == "1.5KB"
        assert format_size(1500000) == "1.4MB"
        assert format_size(1500000000) == "1.4GB"

    def test_format_duration(self):
        assert "µs" in format_duration(0.5)
        assert "ms" in format_duration(50)
        assert "s" in format_duration(5000)
        assert "m" in format_duration(120000)
        assert "h" in format_duration(7200000)

    def test_format_percentage(self):
        assert format_percentage(0.75) == "75.0%"
        assert format_percentage(0.333, 2) == "33.30%"

    def test_format_table_simple(self):
        table = format_table_simple(
            ["Name", "Age"],
            [["Alice", "30"], ["Bob", "25"]],
        )
        assert "Name" in table
        assert "Alice" in table
        assert "Bob" in table
        assert "---" in table

    def test_format_table_empty(self):
        assert format_table_simple([], []) == ""

    def test_format_key_value(self):
        result = format_key_value({"name": "test", "size": 42})
        assert "name" in result
        assert "42" in result

    def test_format_list(self):
        result = format_list(["one", "two", "three"])
        assert "• one" in result
        assert "• two" in result

    def test_format_list_custom_bullet(self):
        result = format_list(["a", "b"], bullet="-", indent=2)
        assert "  - a" in result


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------


class TestProgressBar:
    def test_basic(self):
        bar = create_progress_bar(100)
        assert bar.percentage == 0.0
        bar.advance(50)
        assert bar.percentage == 0.5
        bar.set(100)
        assert bar.percentage == 1.0

    def test_render(self):
        bar = create_progress_bar(10, prefix="Loading")
        bar.advance(5)
        text = bar.render()
        assert "Loading" in text
        assert "50" in text  # 50.0%
        assert "5/10" in text

    def test_str(self):
        bar = create_progress_bar(10)
        bar.advance(3)
        assert "3/10" in str(bar)

    def test_overflow(self):
        bar = create_progress_bar(10)
        bar.advance(20)
        assert bar.current == 10

    def test_zero_total(self):
        bar = create_progress_bar(0)
        assert bar.percentage == 0.0


# ---------------------------------------------------------------------------
# Spinner
# ---------------------------------------------------------------------------


class TestSpinner:
    def test_render(self):
        spinner = create_spinner("Processing")
        text1 = spinner.render()
        text2 = spinner.render()
        assert "Processing" in text1
        assert "Processing" in text2
        # Frames should differ
        assert text1 != text2

    def test_str(self):
        spinner = create_spinner("Test")
        assert "Test" in str(spinner)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


class TestParseArgs:
    def test_long_flag(self):
        defs = [CLIArg(name="verbose", arg_type="bool")]
        result = parse_args(["--verbose"], defs)
        assert result["verbose"] is True

    def test_long_value(self):
        defs = [CLIArg(name="output", default="out.md")]
        result = parse_args(["--output", "report.md"], defs)
        assert result["output"] == "report.md"

    def test_long_equals(self):
        defs = [CLIArg(name="depth", arg_type="int", default=2)]
        result = parse_args(["--depth=5"], defs)
        assert result["depth"] == 5

    def test_short_flag(self):
        defs = [CLIArg(name="verbose", short="v", arg_type="bool")]
        result = parse_args(["-v"], defs)
        assert result["verbose"] is True

    def test_short_value(self):
        defs = [CLIArg(name="output", short="o")]
        result = parse_args(["-o", "file.md"], defs)
        assert result["output"] == "file.md"

    def test_default_values(self):
        defs = [
            CLIArg(name="depth", arg_type="int", default=2),
            CLIArg(name="output", default="report.md"),
        ]
        result = parse_args([], defs)
        assert result["depth"] == 2
        assert result["output"] == "report.md"

    def test_positional(self):
        defs = [CLIArg(name="verbose", short="v", arg_type="bool")]
        result = parse_args(["topic1", "-v", "topic2"], defs)
        assert result["_positional"] == ["topic1", "topic2"]

    def test_int_coercion(self):
        defs = [CLIArg(name="count", arg_type="int")]
        result = parse_args(["--count", "42"], defs)
        assert result["count"] == 42

    def test_float_coercion(self):
        defs = [CLIArg(name="temp", arg_type="float")]
        result = parse_args(["--temp", "0.7"], defs)
        assert result["temp"] == 0.7

    def test_list_coercion(self):
        defs = [CLIArg(name="tags", arg_type="list")]
        result = parse_args(["--tags", "a,b,c"], defs)
        assert result["tags"] == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# Help formatting
# ---------------------------------------------------------------------------


class TestFormatHelp:
    def test_basic(self):
        args = [
            CLIArg(name="output", short="o", description="Output file", default="report.md"),
            CLIArg(name="depth", short="d", description="Search depth", arg_type="int", default=2),
        ]
        help_text = format_help("deepworm", "AI research agent", args)
        assert "deepworm" in help_text
        assert "AI research agent" in help_text
        assert "--output" in help_text
        assert "-o" in help_text
        assert "report.md" in help_text

    def test_required_flag(self):
        args = [CLIArg(name="topic", description="Research topic", required=True)]
        help_text = format_help("deepworm", "", args)
        assert "[required]" in help_text

    def test_choices(self):
        args = [CLIArg(name="format", description="Output format", choices=["md", "html", "json"])]
        help_text = format_help("deepworm", "", args)
        assert "md, html, json" in help_text


# ---------------------------------------------------------------------------
# Box drawing
# ---------------------------------------------------------------------------


class TestDrawBox:
    def test_basic(self):
        box = draw_box("Hello World")
        assert "╭" in box
        assert "╰" in box
        assert "Hello World" in box

    def test_with_title(self):
        box = draw_box("Content", title="My Box")
        assert "My Box" in box
        assert "Content" in box

    def test_multiline(self):
        box = draw_box("Line 1\nLine 2\nLine 3")
        assert "Line 1" in box
        assert "Line 2" in box
        assert "Line 3" in box


# ---------------------------------------------------------------------------
# CLI structures
# ---------------------------------------------------------------------------


class TestCLIStructures:
    def test_cli_arg(self):
        arg = CLIArg(name="output", short="o", description="Output file")
        assert arg.name == "output"
        assert arg.short == "o"

    def test_cli_command(self):
        cmd = CLICommand(name="research", description="Run research")
        assert cmd.name == "research"
        assert cmd.args == []
