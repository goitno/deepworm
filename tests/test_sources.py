"""Tests for deepworm.sources."""

import csv
import json

import pytest

from deepworm.sources import (
    export_sources,
    import_sources,
    sources_to_dicts,
)


@pytest.fixture
def sample_sources():
    return [
        {"url": "https://example.com/a", "title": "Source A", "findings": "Finding A", "relevance": 0.85},
        {"url": "https://example.com/b", "title": "Source B", "findings": "Finding B", "relevance": 0.72},
    ]


def test_export_json(tmp_path, sample_sources):
    path = str(tmp_path / "sources.json")
    result = export_sources(sample_sources, path)
    assert result.endswith("sources.json")
    with open(result) as f:
        data = json.load(f)
    assert len(data) == 2
    assert data[0]["url"] == "https://example.com/a"


def test_export_csv(tmp_path, sample_sources):
    path = str(tmp_path / "sources.csv")
    result = export_sources(sample_sources, path)
    with open(result) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 2
    assert rows[0]["title"] == "Source A"


def test_export_bibtex(tmp_path, sample_sources):
    path = str(tmp_path / "sources.bib")
    result = export_sources(sample_sources, path)
    content = open(result).read()
    assert "@online" in content
    assert "Source A" in content


def test_import_json(tmp_path, sample_sources):
    path = str(tmp_path / "sources.json")
    export_sources(sample_sources, path)
    imported = import_sources(path)
    assert len(imported) == 2
    assert imported[0]["url"] == "https://example.com/a"


def test_import_csv(tmp_path, sample_sources):
    path = str(tmp_path / "sources.csv")
    export_sources(sample_sources, path, fmt="csv")
    imported = import_sources(path)
    assert len(imported) == 2
    assert imported[0]["title"] == "Source A"
    assert float(imported[0]["relevance"]) == 0.85


def test_import_missing_file():
    with pytest.raises(FileNotFoundError):
        import_sources("/nonexistent/file.json")


def test_export_empty_csv(tmp_path):
    path = str(tmp_path / "empty.csv")
    export_sources([], path)
    content = open(path).read()
    assert "url" in content  # Headers still present


def test_sources_to_dicts():
    class FakeSource:
        def __init__(self):
            self.url = "https://example.com"
            self.title = "Test"
            self.findings = "Some findings"
            self.relevance = 0.9

    result = sources_to_dicts([FakeSource()])
    assert len(result) == 1
    assert result[0]["url"] == "https://example.com"
    assert result[0]["relevance"] == 0.9


def test_sources_to_dicts_from_dicts():
    result = sources_to_dicts([{"url": "https://a.com", "title": "A"}])
    assert len(result) == 1
    assert result[0]["url"] == "https://a.com"


def test_export_format_override(tmp_path, sample_sources):
    path = str(tmp_path / "data.txt")
    export_sources(sample_sources, path, fmt="json")
    with open(path) as f:
        data = json.load(f)
    assert len(data) == 2
