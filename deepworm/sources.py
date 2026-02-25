"""Source export and import.

Export discovered sources as JSON, CSV, or BibTeX for external use.
Import previously exported sources to seed a new research session.

Usage:
    deepworm "topic" --export-sources sources.json
    deepworm "topic" --export-sources sources.csv
    deepworm "topic" --export-sources sources.bib
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from .citations import Citation, format_bibtex


def export_sources(
    sources: list[dict[str, Any]],
    path: str,
    fmt: Optional[str] = None,
) -> str:
    """Export sources to a file.

    Args:
        sources: List of source dicts with url, title, findings, relevance.
        path: Output file path.
        fmt: Format override ('json', 'csv', 'bibtex'). Auto-detected from extension.

    Returns:
        Absolute path of the written file.
    """
    p = Path(path)

    if fmt is None:
        ext_map = {".json": "json", ".csv": "csv", ".bib": "bibtex", ".bibtex": "bibtex"}
        fmt = ext_map.get(p.suffix.lower(), "json")

    p.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "csv":
        _export_csv(sources, p)
    elif fmt == "bibtex":
        _export_bibtex(sources, p)
    else:
        _export_json(sources, p)

    return str(p.resolve())


def _export_json(sources: list[dict[str, Any]], path: Path) -> None:
    """Export as JSON array."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=2, ensure_ascii=False)


def _export_csv(sources: list[dict[str, Any]], path: Path) -> None:
    """Export as CSV."""
    if not sources:
        path.write_text("url,title,findings,relevance\n")
        return

    fieldnames = ["url", "title", "findings", "relevance"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sources)


def _export_bibtex(sources: list[dict[str, Any]], path: Path) -> None:
    """Export as BibTeX entries."""
    entries = []
    for i, src in enumerate(sources, 1):
        citation = Citation(
            title=src.get("title", "Untitled"),
            url=src.get("url", ""),
        )
        entries.append(format_bibtex(citation))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(entries))


def import_sources(path: str) -> list[dict[str, Any]]:
    """Import sources from a JSON or CSV file.

    Args:
        path: Path to source file.

    Returns:
        List of source dicts.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Source file not found: {path}")

    if p.suffix.lower() == ".csv":
        return _import_csv(p)
    return _import_json(p)


def _import_json(path: Path) -> list[dict[str, Any]]:
    """Import from JSON."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return []


def _import_csv(path: Path) -> list[dict[str, Any]]:
    """Import from CSV."""
    sources = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert relevance to float if present
            if "relevance" in row:
                try:
                    row["relevance"] = float(row["relevance"])
                except (ValueError, TypeError):
                    row["relevance"] = 0.0
            sources.append(dict(row))
    return sources


def sources_to_dicts(sources: list) -> list[dict[str, Any]]:
    """Convert Source objects to serializable dicts."""
    result = []
    for s in sources:
        if hasattr(s, "__dict__"):
            d = {
                "url": getattr(s, "url", ""),
                "title": getattr(s, "title", ""),
                "findings": getattr(s, "findings", ""),
                "relevance": getattr(s, "relevance", 0.0),
            }
        elif isinstance(s, dict):
            d = s
        else:
            continue
        result.append(d)
    return result
