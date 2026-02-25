"""DeepWorm - AI-powered deep research agent."""

import logging

__version__ = "0.9.0"

from .annotations import AnnotationSet, AnnotationType, annotate_report, auto_annotate, extract_annotations
from .async_api import AsyncResearcher, async_research
from .batch import BatchConfig, BatchResult, BatchStatus, BatchTask, create_batch, run_batch
from .chain import research_chain
from .credibility import CredibilityReport, CredibilityScore, score_source, score_sources
from .crossref import CrossRefIndex, CrossRefTarget, build_crossref_index, inject_crossrefs, generate_list_of_figures, generate_list_of_tables
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
from .glossary import Glossary, GlossaryEntry, extract_glossary, inject_glossary
from .history import HistoryEntry
from .keywords import Keyword, KeywordResult, extract_keywords, extract_tags
from .languages import Language, get_language, list_languages
from .notion import NotionBlock, NotionPage, export_notion_json, markdown_to_notion
from .outline import OutlineSection, ReportOutline, generate_outline, outline_from_report
from .planner import ResearchPlan, generate_plan, estimate_complexity
from .progress import ProgressSnapshot, ProgressTracker, ResearchStage
from .readability import ReadabilityResult, analyze_readability
from .references import Reference, Bibliography, extract_references, create_reference, inject_bibliography, merge_bibliographies
from .researcher import DeepResearcher
from .scoring import QualityScore, score_report
from .sentiment import SentimentScore, SentimentReport, ToneAnalysis, analyze_sentiment, analyze_tone, analyze_report_sentiment, sentiment_diff
from .similarity import SimilarityResult, compare_texts, cosine_similarity, detect_plagiarism, find_similar
from .summary import Summary, extract_key_findings, extract_topics, summarize
from .timeline import Timeline, TimelineEvent, extract_timeline, create_timeline, compare_timelines
from .validator import ValidationResult, validate_topic

__all__ = [
    "APIKeyError",
    "AnnotationSet",
    "AnnotationType",
    "AsyncResearcher",
    "BatchConfig",
    "BatchResult",
    "BatchStatus",
    "BatchTask",
    "Bibliography",
    "ConfigError",
    "ContentExtractionError",
    "CredibilityReport",
    "CredibilityScore",
    "CrossRefIndex",
    "CrossRefTarget",
    "DeepResearcher",
    "DeepWormError",
    "Event",
    "EventEmitter",
    "EventType",
    "ExportFormat",
    "ExportOptions",
    "ExportResult",
    "FootnoteResult",
    "Glossary",
    "GlossaryEntry",
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
    "Reference",
    "ReportOutline",
    "ResearchPlan",
    "ResearchStage",
    "SearchError",
    "SentimentReport",
    "SentimentScore",
    "SessionError",
    "SimilarityResult",
    "Summary",
    "Timeline",
    "TimelineEvent",
    "ToneAnalysis",
    "ValidationResult",
    "__version__",
    "add_footnotes",
    "analyze_readability",
    "analyze_report_sentiment",
    "analyze_sentiment",
    "analyze_tone",
    "annotate_report",
    "async_research",
    "auto_annotate",
    "batch_export",
    "build_crossref_index",
    "compare_texts",
    "compare_timelines",
    "cosine_similarity",
    "create_batch",
    "create_reference",
    "create_timeline",
    "detect_plagiarism",
    "estimate_complexity",
    "export_notion_json",
    "export_report",
    "extract_annotations",
    "extract_glossary",
    "extract_key_findings",
    "extract_keywords",
    "extract_references",
    "extract_tags",
    "extract_timeline",
    "extract_topics",
    "find_similar",
    "generate_list_of_figures",
    "generate_list_of_tables",
    "generate_outline",
    "generate_plan",
    "get_language",
    "inject_bibliography",
    "inject_crossrefs",
    "inject_glossary",
    "list_languages",
    "markdown_to_notion",
    "merge_bibliographies",
    "merge_footnotes",
    "outline_from_report",
    "renumber_footnotes",
    "research",
    "research_chain",
    "run_batch",
    "score_report",
    "score_source",
    "score_sources",
    "sentiment_diff",
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
