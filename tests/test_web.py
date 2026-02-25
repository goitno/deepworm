"""Tests for deepworm.web module."""

import json
import threading
import time
from http.server import HTTPServer
from urllib.request import urlopen

import pytest

from deepworm.web import INDEX_HTML, ResearchHandler


@pytest.fixture
def server():
    """Start a test server on a random port."""
    srv = HTTPServer(("127.0.0.1", 0), ResearchHandler)
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    srv.shutdown()


def test_index_page(server):
    """Index page should return the web UI HTML."""
    resp = urlopen(f"{server}/")
    html = resp.read().decode()
    assert "deepworm" in html
    assert "<!DOCTYPE html>" in html


def test_history_api(server):
    """History API should return JSON array."""
    resp = urlopen(f"{server}/api/history")
    data = json.loads(resp.read().decode())
    assert isinstance(data, list)


def test_404(server):
    """Unknown routes should return 404."""
    try:
        urlopen(f"{server}/nonexistent")
        assert False, "Should have raised"
    except Exception as e:
        assert "404" in str(e)


def test_index_html_content():
    """The HTML template should contain key elements."""
    assert "Research" in INDEX_HTML
    assert "startResearch" in INDEX_HTML
    assert "api/research" in INDEX_HTML
