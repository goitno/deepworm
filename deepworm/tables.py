"""Markdown table generation utilities.

Create well-formatted markdown tables from data:
- Auto-aligned columns
- Header separators
- Support for lists of dicts, lists of lists, and key-value pairs
- CSV import/export
"""

from __future__ import annotations

import csv
import io
from typing import Any, Sequence


def make_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    alignment: str | Sequence[str] | None = None,
) -> str:
    """Create a markdown table from headers and rows.

    Args:
        headers: Column header strings.
        rows: List of row data (each row is a sequence of values).
        alignment: Column alignment - "left", "right", "center", or
            a sequence of these for per-column alignment. Default: "left".

    Returns:
        Formatted markdown table string.
    """
    if not headers:
        return ""

    ncols = len(headers)

    # Normalize alignment
    if alignment is None:
        aligns = ["left"] * ncols
    elif isinstance(alignment, str):
        aligns = [alignment] * ncols
    else:
        aligns = list(alignment)
        while len(aligns) < ncols:
            aligns.append("left")

    # Convert all cells to strings
    str_headers = [str(h) for h in headers]
    str_rows = [[str(c) for c in row] for row in rows]

    # Pad rows to match header count
    for row in str_rows:
        while len(row) < ncols:
            row.append("")

    # Calculate column widths
    widths = [len(h) for h in str_headers]
    for row in str_rows:
        for i, cell in enumerate(row[:ncols]):
            widths[i] = max(widths[i], len(cell))

    # Minimum width of 3 for separator
    widths = [max(w, 3) for w in widths]

    # Build header line
    header_line = "| " + " | ".join(
        h.ljust(widths[i]) for i, h in enumerate(str_headers)
    ) + " |"

    # Build separator
    sep_parts = []
    for i, align in enumerate(aligns):
        w = widths[i]
        if align == "center":
            sep_parts.append(":" + "-" * (w - 2) + ":")
        elif align == "right":
            sep_parts.append("-" * (w - 1) + ":")
        else:  # left
            sep_parts.append("-" * w)
    sep_line = "| " + " | ".join(sep_parts) + " |"

    # Build data rows
    data_lines = []
    for row in str_rows:
        cells = []
        for i in range(ncols):
            cell = row[i] if i < len(row) else ""
            if aligns[i] == "right":
                cells.append(cell.rjust(widths[i]))
            elif aligns[i] == "center":
                cells.append(cell.center(widths[i]))
            else:
                cells.append(cell.ljust(widths[i]))
        data_lines.append("| " + " | ".join(cells) + " |")

    return "\n".join([header_line, sep_line] + data_lines)


def from_dicts(
    data: Sequence[dict[str, Any]],
    columns: Sequence[str] | None = None,
    alignment: str | Sequence[str] | None = None,
) -> str:
    """Create a markdown table from a list of dictionaries.

    Args:
        data: List of dicts with consistent keys.
        columns: Optional subset/ordering of columns. If None, uses
            all keys from the first dict.
        alignment: Column alignment.

    Returns:
        Formatted markdown table string.
    """
    if not data:
        return ""

    if columns is None:
        columns = list(data[0].keys())

    rows = [[d.get(col, "") for col in columns] for d in data]
    return make_table(columns, rows, alignment)


def from_pairs(
    pairs: Sequence[tuple[str, Any]],
    headers: tuple[str, str] = ("Key", "Value"),
    alignment: str | Sequence[str] | None = None,
) -> str:
    """Create a two-column key-value table.

    Args:
        pairs: Sequence of (key, value) tuples.
        headers: Column headers for the key and value columns.
        alignment: Column alignment.

    Returns:
        Formatted markdown table string.
    """
    return make_table(list(headers), [[k, v] for k, v in pairs], alignment)


def to_csv(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
) -> str:
    """Convert table data to CSV string.

    Args:
        headers: Column headers.
        rows: Row data.

    Returns:
        CSV formatted string.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([str(c) for c in row])
    return output.getvalue()


def from_csv(text: str, alignment: str | None = None) -> str:
    """Convert CSV text to a markdown table.

    Args:
        text: CSV formatted text.
        alignment: Column alignment.

    Returns:
        Formatted markdown table string.
    """
    reader = csv.reader(io.StringIO(text))
    rows_list = list(reader)
    if not rows_list:
        return ""
    headers = rows_list[0]
    rows = rows_list[1:]
    return make_table(headers, rows, alignment)


def transpose(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    row_header: str = "",
) -> str:
    """Create a transposed table (rows become columns).

    Useful for comparing a small number of items across many attributes.

    Args:
        headers: Original column headers (become first column values).
        rows: Original row data.
        row_header: Header for the first column in transposed table.

    Returns:
        Transposed markdown table.
    """
    if not headers or not rows:
        return ""

    new_headers = [row_header] + [str(row[0]) if row else "" for row in rows]
    new_rows = []
    for i, header in enumerate(headers):
        new_row = [header]
        for row in rows:
            new_row.append(str(row[i]) if i < len(row) else "")
        new_rows.append(new_row)

    return make_table(new_headers, new_rows)
