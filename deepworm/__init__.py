"""DeepWorm - AI-powered deep research agent."""

import logging

__version__ = "1.1.0"

from .annotations import AnnotationSet, AnnotationType, annotate_report, auto_annotate, extract_annotations
from .async_api import AsyncResearcher, async_research
from .batch import BatchConfig, BatchResult, BatchStatus, BatchTask, create_batch, run_batch
from .chain import research_chain
from .compliance import ComplianceIssue, ComplianceReport, IssueCategory, Severity, StyleGuide, check_compliance, create_style_guide, academic_style_guide, technical_style_guide
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
from .hooks import HookContext, HookEntry, HookRegistry, HookResult, HookStage, Pipeline, PipelineResult, create_middleware, create_pipeline, get_global_registry, hook
from .i18n import TranslationEntry, TranslationCatalog, LanguageDetection, detect_language, extract_translatable, create_catalog, merge_catalogs
from .keywords import Keyword, KeywordResult, extract_keywords, extract_tags
from .languages import Language, get_language, list_languages
from .notion import NotionBlock, NotionPage, export_notion_json, markdown_to_notion
from .outline import OutlineSection, ReportOutline, generate_outline, outline_from_report
from .planner import ResearchPlan, generate_plan, estimate_complexity
from .progress import ProgressSnapshot, ProgressTracker, ResearchStage
from .readability import ReadabilityResult, analyze_readability
from .references import Reference, Bibliography, extract_references, create_reference, inject_bibliography, merge_bibliographies
from .researcher import DeepResearcher
from .revisions import Revision, Change, RevisionDiff, RevisionHistory, compute_diff, create_revision, create_history, track_changes, merge_revisions
from .schema import DocumentSchema, FieldType, SchemaField, SectionRule, ValidationError as SchemaValidationError, ValidationResult as SchemaValidationResult, create_schema, report_schema, article_schema
from .scoring import QualityScore, score_report
from .sentiment import SentimentScore, SentimentReport, ToneAnalysis, analyze_sentiment, analyze_tone, analyze_report_sentiment, sentiment_diff
from .similarity import SimilarityResult, compare_texts, cosine_similarity, detect_plagiarism, find_similar
from .statistics import TextStatistics, ComparisonResult, compute_statistics, compare_statistics, vocabulary_analysis, section_statistics, reading_level
from .summary import Summary, extract_key_findings, extract_topics, summarize
from .timeline import Timeline, TimelineEvent, extract_timeline, create_timeline, compare_timelines
from .toc import TocEntry, TableOfContents, extract_toc, generate_toc, inject_toc, merge_tocs
from .validator import ValidationResult, validate_topic
from .wordcloud import WordFrequency, WordCloudData, generate_word_cloud, compare_word_clouds, tfidf_cloud

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
    "Change",
    "ComparisonResult",
    "ComplianceIssue",
    "ComplianceReport",
    "ConfigError",
    "ContentExtractionError",
    "CredibilityReport",
    "CredibilityScore",
    "CrossRefIndex",
    "CrossRefTarget",
    "DeepResearcher",
    "DeepWormError",
    "DocumentSchema",
    "Event",
    "EventEmitter",
    "EventType",
    "ExportFormat",
    "ExportOptions",
    "ExportResult",
    "FieldType",
    "FootnoteResult",
    "Glossary",
    "GlossaryEntry",
    "HistoryEntry",
    "HookContext",
    "HookEntry",
    "HookRegistry",
    "HookResult",
    "HookStage",
    "IssueCategory",
    "Keyword",
    "KeywordResult",
    "Language",
    "LanguageDetection",
    "ModelNotFoundError",
    "NetworkError",
    "NotionBlock",
    "NotionPage",
    "OutlineSection",
    "Pipeline",
    "PipelineResult",
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
    "Revision",
    "RevisionDiff",
    "RevisionHistory",
    "SchemaField",
    "SchemaValidationError",
    "SchemaValidationResult",
    "SearchError",
    "SectionRule",
    "SentimentReport",
    "SentimentScore",
    "SessionError",
    "Severity",
    "SimilarityResult",
    "StyleGuide",
    "Summary",
    "TableOfContents",
    "TextStatistics",
    "Timeline",
    "TimelineEvent",
    "TocEntry",
    "ToneAnalysis",
    "TranslationCatalog",
    "TranslationEntry",
    "ValidationResult",
    "WordCloudData",
    "WordFrequency",
    "__version__",
    "academic_style_guide",
    "add_footnotes",
    "analyze_readability",
    "analyze_report_sentiment",
    "analyze_sentiment",
    "analyze_tone",
    "annotate_report",
    "article_schema",
    "async_research",
    "auto_annotate",
    "batch_export",
    "build_crossref_index",
    "check_compliance",
    "compare_statistics",
    "compare_texts",
    "compare_timelines",
    "compare_word_clouds",
    "compute_diff",
    "compute_statistics",
    "cosine_similarity",
    "create_batch",
    "create_catalog",
    "create_history",
    "create_middleware",
    "create_pipeline",
    "create_reference",
    "create_revision",
    "create_schema",
    "create_style_guide",
    "create_timeline",
    "detect_language",
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
    "extract_toc",
    "extract_topics",
    "extract_translatable",
    "find_similar",
    "generate_list_of_figures",
    "generate_list_of_tables",
    "generate_outline",
    "generate_plan",
    "generate_toc",
    "generate_word_cloud",
    "get_global_registry",
    "get_language",
    "hook",
    "inject_bibliography",
    "inject_crossrefs",
    "inject_glossary",
    "inject_toc",
    "list_languages",
    "markdown_to_notion",
    "merge_bibliographies",
    "merge_catalogs",
    "merge_footnotes",
    "merge_revisions",
    "merge_tocs",
    "outline_from_report",
    "reading_level",
    "renumber_footnotes",
    "report_schema",
    "research",
    "research_chain",
    "run_batch",
    "score_report",
    "score_source",
    "score_sources",
    "section_statistics",
    "sentiment_diff",
    "strip_footnotes",
    "summarize",
    "technical_style_guide",
    "tfidf_cloud",
    "track_changes",
    "validate_topic",
    "vocabulary_analysis",
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
