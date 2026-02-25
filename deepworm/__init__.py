"""DeepWorm - AI-powered deep research agent."""

import logging

__version__ = "0.5.0"

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
from .planner import ResearchPlan, generate_plan, estimate_complexity
from .researcher import DeepResearcher
from .scoring import QualityScore, score_report
from .validator import ValidationResult, validate_topic

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
    "QualityScore",
    "RateLimitError",
    "ResearchPlan",
    "SearchError",
    "SessionError",
    "ValidationResult",
    "__version__",
    "async_research",
    "estimate_complexity",
    "generate_plan",
    "get_language",
    "list_languages",
    "research",
    "research_chain",
    "score_report",
    "validate_topic",
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
