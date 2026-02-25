"""CLI helper utilities for deepworm.

Provides argument parsing helpers, output formatting, color support,
progress indicators, and interactive prompt utilities.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class Color(Enum):
    """Terminal colors (ANSI)."""

    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"


class OutputFormat(Enum):
    """Output format preferences."""

    PLAIN = "plain"
    COLORED = "colored"
    JSON = "json"
    MARKDOWN = "markdown"
    QUIET = "quiet"


class Verbosity(Enum):
    """Verbosity levels."""

    SILENT = 0
    QUIET = 1
    NORMAL = 2
    VERBOSE = 3
    DEBUG = 4


# ---------------------------------------------------------------------------
# Color support
# ---------------------------------------------------------------------------


def supports_color() -> bool:
    """Check if the terminal supports ANSI colors."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


def colorize(text: str, color: Color) -> str:
    """Apply color to text if terminal supports it."""
    if not supports_color():
        return text
    return f"{color.value}{text}{Color.RESET.value}"


def red(text: str) -> str:
    return colorize(text, Color.RED)


def green(text: str) -> str:
    return colorize(text, Color.GREEN)


def yellow(text: str) -> str:
    return colorize(text, Color.YELLOW)


def blue(text: str) -> str:
    return colorize(text, Color.BLUE)


def cyan(text: str) -> str:
    return colorize(text, Color.CYAN)


def bold(text: str) -> str:
    return colorize(text, Color.BOLD)


def dim(text: str) -> str:
    return colorize(text, Color.DIM)


# ---------------------------------------------------------------------------
# Text formatting
# ---------------------------------------------------------------------------


def truncate(text: str, max_length: int = 80, suffix: str = "...") -> str:
    """Truncate text to max_length."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def pad_right(text: str, width: int, char: str = " ") -> str:
    """Pad text to the right."""
    if len(text) >= width:
        return text
    return text + char * (width - len(text))


def pad_left(text: str, width: int, char: str = " ") -> str:
    """Pad text to the left."""
    if len(text) >= width:
        return text
    return char * (width - len(text)) + text


def indent_text(text: str, spaces: int = 2) -> str:
    """Indent each line of text."""
    prefix = " " * spaces
    return "\n".join(prefix + line for line in text.split("\n"))


def format_table_simple(
    headers: List[str],
    rows: List[List[str]],
    *,
    padding: int = 1,
    separator: str = "|",
) -> str:
    """Format data as a simple text table."""
    if not headers:
        return ""

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    pad = " " * padding

    # Header
    header_line = separator.join(
        pad + pad_right(h, widths[i]) + pad
        for i, h in enumerate(headers)
    )
    divider = separator.join(
        pad + "-" * widths[i] + pad
        for i in range(len(headers))
    )

    lines = [header_line, divider]
    for row in rows:
        line = separator.join(
            pad + pad_right(str(row[i]) if i < len(row) else "", widths[i]) + pad
            for i in range(len(headers))
        )
        lines.append(line)

    return "\n".join(lines)


def format_key_value(
    data: Dict[str, Any],
    *,
    separator: str = ": ",
    indent: int = 0,
) -> str:
    """Format dict as key-value pairs."""
    prefix = " " * indent
    max_key = max(len(str(k)) for k in data) if data else 0
    lines = []
    for key, value in data.items():
        padded_key = pad_right(str(key), max_key)
        lines.append(f"{prefix}{padded_key}{separator}{value}")
    return "\n".join(lines)


def format_list(
    items: List[str],
    *,
    bullet: str = "•",
    indent: int = 0,
) -> str:
    """Format a list with bullets."""
    prefix = " " * indent
    return "\n".join(f"{prefix}{bullet} {item}" for item in items)


def format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"


def format_duration(ms: float) -> str:
    """Format milliseconds to a human-readable duration."""
    if ms < 1:
        return f"{ms * 1000:.0f}µs"
    elif ms < 1000:
        return f"{ms:.1f}ms"
    elif ms < 60000:
        return f"{ms / 1000:.1f}s"
    elif ms < 3600000:
        minutes = int(ms / 60000)
        seconds = (ms % 60000) / 1000
        return f"{minutes}m{seconds:.0f}s"
    else:
        hours = int(ms / 3600000)
        minutes = int((ms % 3600000) / 60000)
        return f"{hours}h{minutes}m"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a ratio (0-1) as percentage."""
    return f"{value * 100:.{decimals}f}%"


# ---------------------------------------------------------------------------
# Progress indicators
# ---------------------------------------------------------------------------


@dataclass
class ProgressBar:
    """Simple text-based progress bar."""

    total: int
    current: int = 0
    width: int = 40
    fill_char: str = "█"
    empty_char: str = "░"
    prefix: str = ""
    suffix: str = ""

    def advance(self, amount: int = 1) -> None:
        self.current = min(self.current + amount, self.total)

    def set(self, value: int) -> None:
        self.current = min(max(0, value), self.total)

    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return self.current / self.total

    def render(self) -> str:
        filled = int(self.width * self.percentage)
        bar = self.fill_char * filled + self.empty_char * (self.width - filled)
        pct = format_percentage(self.percentage, 0)
        parts = []
        if self.prefix:
            parts.append(self.prefix)
        parts.append(f"[{bar}]")
        parts.append(pct)
        parts.append(f"({self.current}/{self.total})")
        if self.suffix:
            parts.append(self.suffix)
        return " ".join(parts)

    def __str__(self) -> str:
        return self.render()


class Spinner:
    """Simple text spinner for long-running operations."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Working") -> None:
        self.message = message
        self._frame_index = 0

    def render(self) -> str:
        frame = self.FRAMES[self._frame_index % len(self.FRAMES)]
        self._frame_index += 1
        return f"{frame} {self.message}"

    def __str__(self) -> str:
        return self.render()


# ---------------------------------------------------------------------------
# Argument parsing helpers
# ---------------------------------------------------------------------------


@dataclass
class CLIArg:
    """CLI argument definition."""

    name: str
    short: Optional[str] = None
    description: str = ""
    default: Any = None
    arg_type: str = "string"  # string, int, float, bool, list
    required: bool = False
    choices: Optional[List[str]] = None


@dataclass
class CLICommand:
    """CLI command definition."""

    name: str
    description: str = ""
    args: List[CLIArg] = field(default_factory=list)
    handler: Optional[Callable] = None


def parse_args(
    args: List[str],
    definitions: List[CLIArg],
) -> Dict[str, Any]:
    """Simple argument parser.

    Supports --key value, --key=value, -k value, and --flag (bool).
    """
    result: Dict[str, Any] = {}

    # Set defaults
    for defn in definitions:
        result[defn.name] = defn.default

    # Build lookup tables
    long_map: Dict[str, CLIArg] = {}
    short_map: Dict[str, CLIArg] = {}
    for defn in definitions:
        long_map[f"--{defn.name}"] = defn
        if defn.short:
            short_map[f"-{defn.short}"] = defn

    i = 0
    positional = []
    while i < len(args):
        arg = args[i]

        # --key=value
        if "=" in arg and arg.startswith("--"):
            key, value = arg.split("=", 1)
            if key in long_map:
                defn = long_map[key]
                result[defn.name] = _coerce_value(value, defn.arg_type)
            i += 1
            continue

        # --key value or -k value
        defn = long_map.get(arg) or short_map.get(arg)
        if defn:
            if defn.arg_type == "bool":
                result[defn.name] = True
                i += 1
            else:
                if i + 1 < len(args):
                    result[defn.name] = _coerce_value(args[i + 1], defn.arg_type)
                    i += 2
                else:
                    i += 1
            continue

        # Positional
        positional.append(arg)
        i += 1

    result["_positional"] = positional
    return result


def _coerce_value(value: str, arg_type: str) -> Any:
    """Coerce string value to the specified type."""
    if arg_type == "int":
        return int(value)
    elif arg_type == "float":
        return float(value)
    elif arg_type == "bool":
        return value.lower() in ("true", "1", "yes", "on")
    elif arg_type == "list":
        return value.split(",")
    return value


def format_help(
    command_name: str,
    description: str,
    args: List[CLIArg],
) -> str:
    """Generate help text for a CLI command."""
    lines = [f"Usage: {command_name} [options]", ""]
    if description:
        lines.append(description)
        lines.append("")

    if args:
        lines.append("Options:")
        for arg in args:
            flags = f"  --{arg.name}"
            if arg.short:
                flags += f", -{arg.short}"
            desc = arg.description
            if arg.default is not None:
                desc += f" (default: {arg.default})"
            if arg.required:
                desc += " [required]"
            if arg.choices:
                desc += f" [{', '.join(arg.choices)}]"
            lines.append(f"{pad_right(flags, 30)}{desc}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Box drawing
# ---------------------------------------------------------------------------


def draw_box(
    text: str,
    *,
    title: str = "",
    padding: int = 1,
    border_char: str = "─",
    corner_tl: str = "╭",
    corner_tr: str = "╮",
    corner_bl: str = "╰",
    corner_br: str = "╯",
    side: str = "│",
) -> str:
    """Draw a box around text."""
    lines = text.split("\n")
    max_width = max(len(line) for line in lines) if lines else 0
    if title:
        max_width = max(max_width, len(title) + 2)

    inner_width = max_width + padding * 2

    result = []
    if title:
        title_bar = f"{corner_tl}{border_char} {title} {border_char * (inner_width - len(title) - 3)}{corner_tr}"
    else:
        title_bar = f"{corner_tl}{border_char * inner_width}{corner_tr}"
    result.append(title_bar)

    pad = " " * padding
    for line in lines:
        padded = pad + pad_right(line, max_width) + pad
        result.append(f"{side}{padded}{side}")

    result.append(f"{corner_bl}{border_char * inner_width}{corner_br}")
    return "\n".join(result)


# ---------------------------------------------------------------------------
# Factory / helpers
# ---------------------------------------------------------------------------


def create_progress_bar(
    total: int,
    *,
    width: int = 40,
    prefix: str = "",
) -> ProgressBar:
    """Create a progress bar."""
    return ProgressBar(total=total, width=width, prefix=prefix)


def create_spinner(message: str = "Working") -> Spinner:
    """Create a spinner."""
    return Spinner(message=message)
