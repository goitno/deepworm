"""DeepWorm - AI-powered deep research agent."""

import logging

__version__ = "0.7.0"

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
from .export import ExportFormat, ExportOptions, ExportResult, batch_export, export_report
from .footnotes import FootnoteResult, add_footnotes, merge_footnotes, renumber_footnotes, strip_footnotes
from .history import HistoryEntry
from .keywords import Keyword, KeywordResult, extract_keywords, extract_tags
from .languages import Language, get_language, list_languages
from .notion import NotionBlock, NotionPage, export_notion_json, markdown_to_notion
from .outline import OutlineSection, ReportOutline, generate_outline, outline_from_report
from .planner import ResearchPlan, generate_plan, estimate_complexity
from .progress import ProgressSnapshot, ProgressTracker, ResearchStage
from .readability import ReadabilityResult, analyze_readability
from .researcher import DeepResearcher
from .scoring import QualityScore, score_report
from .summary import Summary, extract_key_findings, extract_topics, summarize
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
    "ExportFormat",
    "ExportOptions",
    "ExportResult",
    "FootnoteResult",
    "HistoryEntry",
    "Keyword",
    "KeywordResult",
    "Language",
    "ModelNotFoundError",
    "NetworkError",
    "NotionBlock",
    "NotionPage",
    "OutlineSection",
    "ProgressSnapshot",
    "ProgressTracker",
    "ProviderError",
    "QualityScore",
    "RateLimitError",
    "ReadabilityResult",
    "ReportOutline",
    "ResearchPlan",
    "ResearchStage",
    "SearchError",
    "SessionError",
    "Summary",
    "ValidationResult",
    "__version__",
    "add_footnotes",
    "analyze_readability",
    "async_research",
    "batch_export",
    "estimate_complexity",
    "export_notion_json",
    "export_report",
    "extract_key_findings",
    "extract_keywords",
    "extract_tags",
    "extract_topics",
    "generate_outline",
    "generate_plan",
    "get_language",
    "list_languages",
    "markdown_to_notion",
    "merge_footnotes",
    "outline_from_report",
    "renumber_footnotes",
    "research",
    "research_chain",
    "score_report",
    "score_source",
    "score_sources",
    "strip_footnotes",
    "summarize",
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
