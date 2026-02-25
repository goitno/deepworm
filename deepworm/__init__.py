"""DeepWorm - AI-powered deep research agent."""

import logging

__version__ = "0.3.0"

from .async_api import AsyncResearcher, async_research
from .chain import research_chain
from .events import Event, EventEmitter, EventType
from .exceptions import (
    APIKeyError,
    ConfigError,
    ContentExtractionError,
    DeepWormError,
    ModelNotFoundError,
    NetworkError,
    ProviderError,
    RateLimitError,
    SearchError,
    SessionError,
)
from .history import HistoryEntry
from .languages import Language, get_language, list_languages
from .researcher import DeepResearcher

__all__ = [
    "APIKeyError",
    "AsyncResearcher",
    "ConfigError",
    "ContentExtractionError",
    "DeepResearcher",
    "DeepWormError",
    "Event",
    "EventEmitter",
    "EventType",
    "HistoryEntry",
    "Language",
    "ModelNotFoundError",
    "NetworkError",
    "ProviderError",
    "RateLimitError",
    "SearchError",
    "SessionError",
    "__version__",
    "async_research",
    "get_language",
    "list_languages",
    "research",
    "research_chain",
]

# Set up default logging (NullHandler to avoid "No handlers" warnings)
logging.getLogger("deepworm").addHandler(logging.NullHandler())


def research(topic: str, **kwargs) -> str:
    """Quick research function. Returns a markdown report.

    Usage:
        from deepworm import research
        report = research("quantum computing advances in 2024")
    """
    researcher = DeepResearcher(**kwargs)
    return researcher.research(topic)
