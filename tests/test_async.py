"""Tests for deepworm.async_api."""

import asyncio

import pytest

from deepworm.async_api import AsyncResearcher, async_research
from deepworm.config import Config


def test_async_researcher_init():
    """Should initialize without errors."""
    config = Config(provider="ollama", api_key="ollama")
    researcher = AsyncResearcher(config=config)
    assert researcher.config.provider == "ollama"


def test_async_research_function_exists():
    """async_research should be importable."""
    assert callable(async_research)


def test_async_researcher_has_methods():
    """Should have research and research_stream methods."""
    researcher = AsyncResearcher()
    assert hasattr(researcher, "research")
    assert hasattr(researcher, "research_stream")
    assert asyncio.iscoroutinefunction(researcher.research)
