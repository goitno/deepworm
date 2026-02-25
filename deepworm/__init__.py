"""DeepWorm - AI-powered deep research agent."""

import logging

__version__ = "0.5.0"

from .async_api import AsyncResearcher, async_research
from .chain import research_chain
from .credibility import CredibilityReport, CredibilityScore, score_source, score_sources
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
from .notion import NotionBlock, NotionPage, export_notion_json, markdown_to_notion
from .outline import OutlineSection, ReportOutline, generate_outline, outline_from_report
from .planner import ResearchPlan, generate_plan, estimate_complexity
from .researcher import DeepResearcher
from .scoring import QualityScore, score_report
from .validator import ValidationResult, validate_topic

__all__ = [
    "APIKeyError",
    "AsyncResearcher",
    "ConfigError",
    "ContentExtractionError",
    "CredibilityReport",
    "CredibilityScore",
    "DeepResearcher",
    "DeepWormError",
    "Event",
    "EventEmitter",
    "EventType",
    "HistoryEntry",
    "Language",
    "ModelNotFoundError",
    "NetworkError",
    "NotionBlock",
    "NotionPage",
    "OutlineSection",
    "ProviderError",
    "QualityScore",
    "RateLimitError",
    "ReportOutline",
    "ResearchPlan",
    "SearchError",
    "SessionError",
    "ValidationResult",
    "__version__",
    "async_research",
    "estimate_complexity",
    "export_notion_json",
    "generate_outline",
    "generate_plan",
    "get_language",
    "list_languages",
    "markdown_to_notion",
    "outline_from_report",
    "research",
    "research_chain",
    "score_report",
    "score_source",
    "score_sources",
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
