"""Core research engine.

Orchestrates the research loop:
  1. Generate search queries from the topic
  2. Search the web for each query
  3. Fetch and extract content from top results
  4. Analyze sources with LLM
  5. Identify knowledge gaps
  6. Generate follow-up queries
  7. Repeat for configured depth
  8. Synthesize final report
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .config import Config
from .llm import LLMClient, TokenTracker, get_client
from .cache import Cache, get_cache
from .events import Event, EventEmitter, EventType
from .history import add_entry as _add_history
from .languages import get_language_instruction
from .metrics import MetricsCollector
from .plugins import PluginManager
from .search import SearchResult, fetch_page_text, search_web
from .session import save_session
from .utils import ContentDeduplicator, RateLimiter

logger = logging.getLogger(__name__)

console = Console()


@dataclass
class Source:
    """A research source with extracted information."""
    url: str
    title: str
    content: str
    findings: str = ""
    relevance: float = 0.0  # 0-1 relevance score


@dataclass
class ResearchState:
    """Tracks the state of an ongoing research session."""
    topic: str
    queries: list[str] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    iterations_done: int = 0


QUERY_GENERATION_PROMPT = """Given a research topic, generate {breadth} search queries that would help build a comprehensive understanding. Each query should target a different angle or aspect.

Topic: {topic}

{context}

Return a JSON array of search query strings. Queries should be specific enough to find relevant results but diverse enough to cover the topic broadly. Example format: ["query 1", "query 2"]"""

FOLLOWUP_QUERY_PROMPT = """Based on research findings so far, identify what's still unknown or unclear and generate {breadth} targeted follow-up queries.

Original topic: {topic}

Current findings:
{findings_summary}

Focus on: gaps in understanding, conflicting claims that need verification, specific details missing from the overview, and emerging sub-topics worth exploring. Return a JSON array of search query strings."""

ANALYSIS_PROMPT = """Extract key findings from this source that are relevant to the research topic.

Topic: {topic}

Source: {title}
URL: {url}
Content:
{content}

Provide a concise analysis with:
- Key facts, statistics, and data points
- Notable claims or arguments
- Unique perspectives not commonly found elsewhere
- Any caveats or limitations mentioned

Use bullet points. Be precise and factual."""

SYNTHESIS_PROMPT = """Write a comprehensive research report based on the following findings.

Research topic: {topic}

Sources and analysis:
{all_findings}

Structure the report as:
1. Title (# heading)
2. Executive Summary (2-3 paragraph overview)
3. Main sections organized by theme (## headings)
4. Key Takeaways (bulleted list)
5. Sources (numbered list of URLs)

Guidelines:
- Lead with the most important findings
- Include specific numbers, dates, and facts when available
- Note disagreements between sources
- Distinguish between established facts and emerging trends
- Write in clear, professional prose

Output the report in Markdown format."""

FOLLOWUP_QUESTIONS_PROMPT = """Based on the research report below, suggest 5 follow-up questions that someone interested in this topic would likely want to explore next.

Topic: {topic}

Report summary: {summary}

Return a JSON array of 5 question strings. Questions should:
- Explore adjacent or deeper aspects of the topic
- Be specific and researchable
- Cover different angles (technical, practical, future, historical, comparative)

Example: ["What are the long-term implications of X?", "How does X compare to Y in practice?"]"""


class DeepResearcher:
    """Main research engine."""

    def __init__(
        self,
        config: Optional[Config] = None,
        on_progress: Optional[Callable[[str], None]] = None,
        cache: Optional[Cache] = None,
        events: Optional[EventEmitter] = None,
        plugins: Optional[PluginManager] = None,
    ):
        self.config = config or Config.auto()
        self.client: Optional[LLMClient] = None
        self._on_progress = on_progress
        self.cache = cache if cache is not None else get_cache()
        self.events = events or EventEmitter()
        self.plugins = plugins or PluginManager()
        self._dedup = ContentDeduplicator(threshold=0.7)
        self._rate_limiter = RateLimiter(
            max_calls=self.config.max_requests_per_minute,
            period=60.0,
        )
        self._metrics = MetricsCollector()

    def _progress(self, msg: str) -> None:
        if self._on_progress:
            self._on_progress(msg)

    def _save_state(self, state: ResearchState) -> None:
        """Auto-save research state for resume capability."""
        try:
            state_data = {
                "topic": state.topic,
                "queries": state.queries,
                "sources": [
                    {"url": s.url, "title": s.title, "findings": s.findings, "relevance": s.relevance}
                    for s in state.sources
                ],
                "findings": state.findings,
                "gaps": state.gaps,
                "iterations_done": state.iterations_done,
                "created_at": getattr(self, "_session_start", time.time()),
            }
            save_session(state.topic, state_data, status="in_progress")
        except Exception as e:
            logger.debug("Failed to save session: %s", e)

    def _get_client(self) -> LLMClient:
        if self.client is None:
            self.client = get_client(self.config)
        return self.client

    def _llm_call(self, llm: LLMClient, method: str, *args, **kwargs):
        """Rate-limited LLM call with retry."""
        self._rate_limiter.acquire()
        if method == "chat":
            return llm.chat_with_retry(*args, **kwargs)
        elif method == "chat_json":
            return llm.chat_json(*args, **kwargs)
        fn = getattr(llm, method)
        return fn(*args, **kwargs)

    def _check_timeout(self) -> bool:
        """Check if research has exceeded the time budget.

        Returns True if timed out.
        """
        if self.config.timeout_seconds <= 0:
            return False
        elapsed = time.time() - getattr(self, "_session_start", time.time())
        return elapsed >= self.config.timeout_seconds

    def research(self, topic: str, verbose: bool = True, persona: str | None = None, stream: bool = False, followup: bool = True, lang: str | None = None) -> str:
        """Run deep research on a topic and return a markdown report.

        Args:
            topic: Research topic or question.
            verbose: Show progress output.
            persona: Optional perspective for the research (e.g. "startup founder").
            stream: Stream the final report to terminal as it generates.
            followup: Whether to generate follow-up questions (appended to report).
            lang: ISO 639-1 language code for report output (e.g. 'tr', 'de', 'fr').
        """
        state = ResearchState(topic=topic)
        llm = self._get_client()

        # Build system context for persona
        persona_context = ""
        if persona:
            persona_context = f"Write from the perspective of a {persona}. Focus on aspects most relevant to this audience."

        # Apply language instruction
        if lang:
            lang_instruction = get_language_instruction(lang)
            if lang_instruction:
                persona_context = f"{persona_context}\n\n{lang_instruction}" if persona_context else lang_instruction

        if verbose:
            info = (
                f"[bold]{topic}[/bold]\n\n"
                f"Provider: {self.config.provider} | Model: {self.config.model}\n"
                f"Depth: {self.config.depth} | Breadth: {self.config.breadth}"
            )
            if persona:
                info += f"\nPersona: {persona}"
            console.print(Panel(info, title="[bold]deepworm[/bold] research", border_style="blue"))
            console.print()

        t_start = time.time()
        self._session_start = t_start

        self.events.emit(Event(
            type=EventType.RESEARCH_START,
            data={"topic": topic, "depth": self.config.depth, "breadth": self.config.breadth},
            message=f"Starting research: {topic}",
        ))

        for i in range(self.config.depth):
            state.iterations_done = i + 1
            t_iter = time.time()

            # Check timeout
            if self._check_timeout():
                if verbose:
                    console.print("[yellow]Time budget exceeded, moving to synthesis...[/yellow]")
                break

            if verbose:
                console.print(f"\n[bold cyan]--- Iteration {i + 1}/{self.config.depth} ---[/bold cyan]")

            self.events.emit(Event(
                type=EventType.ITERATION_START,
                data={"iteration": i + 1, "total": self.config.depth},
                message=f"Starting iteration {i + 1}/{self.config.depth}",
            ))

            # Generate search queries
            if i == 0:
                queries = self._generate_initial_queries(llm, topic)
            else:
                queries = self._generate_followup_queries(llm, state)

            state.queries.extend(queries)
            self._metrics.increment("search_queries", len(queries))

            # Apply plugin hooks
            queries = self.plugins.apply_transform_queries(topic, queries)

            self.events.emit(Event(
                type=EventType.QUERIES_GENERATED,
                data={"queries": queries, "count": len(queries)},
                message=f"Generated {len(queries)} search queries",
            ))

            if verbose:
                console.print(f"[dim]Generated {len(queries)} search queries[/dim]")
                for q in queries:
                    console.print(f"  [dim]• {q}[/dim]")
                # Show token usage after query generation
                tracker = llm.token_tracker
                console.print(
                    f"  [blue]⟡ Tokens: {tracker.total_tokens:,} "
                    f"(in:{tracker.total_prompt_tokens:,} out:{tracker.total_completion_tokens:,}) "
                    f"| {tracker.call_count} API calls[/blue]"
                )

            # Search and fetch
            with self._metrics.time("search"):
                new_sources = self._search_and_fetch(queries, verbose=verbose)
            state.sources.extend(new_sources)

            if verbose:
                console.print(f"[dim]Fetched {len(new_sources)} sources[/dim]")

            # Analyze each source
            if verbose:
                console.print("[dim]Analyzing sources...[/dim]")

            for source in new_sources:
                if not source.content:
                    continue
                # Skip near-duplicate content
                if self._dedup.is_duplicate(source.content):
                    logger.debug("Skipping duplicate: %s", source.url)
                    self._metrics.increment("duplicates_skipped")
                    continue
                # Apply filter hook
                if not self.plugins.apply_filter_source(source.url, source.title, source.content):
                    continue
                findings = self._analyze_source(llm, topic, source)
                # Apply post_analysis hook
                findings = self.plugins.apply_post_analysis(topic, source.content, findings)
                source.findings = findings
                source.relevance = self._score_source(source, topic)
                state.findings.append(findings)
                self._metrics.increment("sources_analyzed")

            elapsed = time.time() - t_iter
            self._progress(f"Completed iteration {i + 1}")

            self.events.emit(Event(
                type=EventType.ITERATION_END,
                data={"iteration": i + 1, "elapsed": elapsed, "sources": len(new_sources)},
                message=f"Iteration {i + 1} completed in {elapsed:.1f}s",
            ))

            if verbose:
                total_elapsed = time.time() - t_start
                remaining = self.config.depth - (i + 1)
                tracker = llm.token_tracker
                token_info = (
                    f"[blue]⟡ Tokens: {tracker.total_tokens:,} "
                    f"(in:{tracker.total_prompt_tokens:,} out:{tracker.total_completion_tokens:,}) "
                    f"| {tracker.call_count} API calls[/blue]"
                )
                if remaining > 0 and (i + 1) > 0:
                    avg_iter = total_elapsed / (i + 1)
                    eta = avg_iter * remaining + avg_iter * 0.5  # +synthesis estimate
                    console.print(
                        f"[dim]Iteration completed in {elapsed:.1f}s · "
                        f"ETA: ~{eta:.0f}s remaining[/dim]"
                    )
                else:
                    console.print(f"[dim]Iteration completed in {elapsed:.1f}s[/dim]")
                console.print(f"  {token_info}")

            # Auto-save session state after each iteration
            self._save_state(state)

        # Synthesize
        if verbose:
            console.print("\n[bold green]Synthesizing report...[/bold green]")

        self.events.emit(Event(
            type=EventType.SYNTHESIS_START,
            data={"total_sources": len(state.sources)},
            message="Starting synthesis",
        ))

        report = self._synthesize(llm, state, persona_context, stream=stream and verbose)

        # Apply post_report hook
        report = self.plugins.apply_post_report(topic, report)

        # Generate follow-up questions
        if followup:
            followup_questions = self._generate_followup_questions_list(llm, topic, report)
        else:
            followup_questions = []
        if followup_questions:
            followup_section = "\n\n## Follow-up Questions\n\n"
            for idx, q in enumerate(followup_questions, 1):
                followup_section += f"{idx}. {q}\n"
            report += followup_section
            self.events.emit(Event(
                type=EventType.SYNTHESIS_COMPLETE,
                data={"followup_questions": followup_questions},
                message=f"Generated {len(followup_questions)} follow-up questions",
            ))

        # Mark session as completed
        try:
            state_data = {
                "topic": state.topic,
                "queries": state.queries,
                "sources": [
                    {"url": s.url, "title": s.title, "findings": s.findings, "relevance": s.relevance}
                    for s in state.sources
                ],
                "findings": state.findings,
                "iterations_done": state.iterations_done,
            }
            save_session(state.topic, state_data, status="completed")
        except Exception:
            pass

        total_time = time.time() - t_start

        # Record in persistent history
        try:
            _add_history(
                topic=topic,
                elapsed=total_time,
                model=self.config.model,
                provider=self.config.provider,
                depth=self.config.depth,
                breadth=self.config.breadth,
                total_sources=len(state.sources),
                report_length=len(report),
                persona=persona,
                output_file=self.config.output_file,
            )
        except Exception:
            logger.debug("Failed to record history entry")

        self.events.emit(Event(
            type=EventType.RESEARCH_COMPLETE,
            data={"elapsed": total_time, "sources": len(state.sources), "iterations": state.iterations_done},
            message=f"Research completed in {total_time:.1f}s",
        ))

        if verbose:
            tracker = llm.token_tracker
            console.print()
            # Final summary table
            summary_table = Table(show_header=False, box=None, padding=(0, 2))
            summary_table.add_column(style="bold")
            summary_table.add_column()
            summary_table.add_row("Time", f"{total_time:.1f}s")
            summary_table.add_row("Sources", f"{len(state.sources)}")
            summary_table.add_row("API Calls", f"{tracker.call_count}")
            summary_table.add_row("Tokens", f"{tracker.total_tokens:,}")
            summary_table.add_row("  Input", f"{tracker.total_prompt_tokens:,}")
            summary_table.add_row("  Output", f"{tracker.total_completion_tokens:,}")
            if tracker.total_cost_usd > 0:
                summary_table.add_row("Est. Cost", f"${tracker.total_cost_usd:.4f}")
            console.print(Panel(summary_table, title="[bold green]✓ Research Complete[/bold green]", border_style="green"))
            console.print()

        # Store sources for post-research access (e.g., source export)
        self.last_sources = state.sources
        self.last_token_tracker = llm.token_tracker

        # Finalize metrics
        self.last_metrics = self._metrics.finalize()
        if state.sources:
            relevances = [s.relevance for s in state.sources if s.relevance > 0]
            if relevances:
                self.last_metrics.avg_source_relevance = sum(relevances) / len(relevances)

        return report

    def _generate_initial_queries(self, llm: LLMClient, topic: str) -> list[str]:
        """Generate initial search queries from the topic."""
        prompt = QUERY_GENERATION_PROMPT.format(
            breadth=self.config.breadth,
            topic=topic,
            context="Generate diverse queries covering different aspects of this topic.",
        )
        try:
            result = llm.chat_json([
                {"role": "system", "content": "You return only valid JSON arrays."},
                {"role": "user", "content": prompt},
            ])
            if isinstance(result, list):
                return [str(q) for q in result[:self.config.breadth]]
        except Exception:
            pass
        # Fallback: use the topic itself
        return [topic]

    def _generate_followup_queries(self, llm: LLMClient, state: ResearchState) -> list[str]:
        """Generate follow-up queries based on current findings."""
        findings_summary = "\n".join(f"- {f[:200]}" for f in state.findings[-6:])
        prompt = FOLLOWUP_QUERY_PROMPT.format(
            breadth=self.config.breadth,
            topic=state.topic,
            findings_summary=findings_summary,
        )
        try:
            result = llm.chat_json([
                {"role": "system", "content": "You return only valid JSON arrays."},
                {"role": "user", "content": prompt},
            ])
            if isinstance(result, list):
                return [str(q) for q in result[:self.config.breadth]]
        except Exception:
            pass
        return [state.topic]

    def _generate_followup_questions_list(self, llm: LLMClient, topic: str, report: str) -> list[str]:
        """Generate follow-up questions based on the completed report."""
        # Use first ~2000 chars of report as summary to stay within limits
        summary = report[:2000]
        prompt = FOLLOWUP_QUESTIONS_PROMPT.format(
            topic=topic,
            summary=summary,
        )
        try:
            result = llm.chat_json([
                {"role": "system", "content": "You return only valid JSON arrays."},
                {"role": "user", "content": prompt},
            ])
            if isinstance(result, list):
                return [str(q) for q in result[:5]]
        except Exception:
            logger.debug("Failed to generate follow-up questions")
        return []

    def _search_and_fetch(
        self,
        queries: list[str],
        verbose: bool = False,
    ) -> list[Source]:
        """Search web and fetch content for each query (concurrent)."""
        seen_urls: set[str] = set()
        sources: list[Source] = []
        urls_to_fetch: list[SearchResult] = []

        # Search queries concurrently
        def _search_query(query: str) -> list[SearchResult]:
            return search_web(
                query,
                max_results=self.config.max_sources,
                cache=self.cache,
                provider=self.config.search_provider,
            )

        search_workers = min(4, len(queries))
        if search_workers > 0:
            with ThreadPoolExecutor(max_workers=search_workers) as executor:
                futures = {executor.submit(_search_query, q): q for q in queries}
                for future in as_completed(futures):
                    try:
                        results = future.result()
                        for r in results:
                            if r.url not in seen_urls:
                                seen_urls.add(r.url)
                                urls_to_fetch.append(r)
                    except Exception:
                        pass

        # Fetch pages concurrently
        def _fetch(result: SearchResult) -> Source:
            body = fetch_page_text(result.url, cache=self.cache)
            return Source(
                url=result.url,
                title=result.title,
                content=body or result.snippet,
            )

        max_workers = min(8, len(urls_to_fetch))
        if max_workers == 0:
            return sources

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_fetch, r): r for r in urls_to_fetch}
            for future in as_completed(futures):
                try:
                    source = future.result()
                    sources.append(source)
                    if verbose:
                        console.print(f"  [dim]Fetched: {source.title[:60]}...[/dim]")
                except Exception:
                    pass

        return sources

    def _analyze_source(self, llm: LLMClient, topic: str, source: Source) -> str:
        """Analyze a single source for relevant findings."""
        # Truncate content to avoid token limits
        content = source.content[:4000]
        prompt = ANALYSIS_PROMPT.format(
            topic=topic,
            title=source.title,
            url=source.url,
            content=content,
        )
        try:
            return llm.chat([
                {"role": "system", "content": "You are a precise research analyst."},
                {"role": "user", "content": prompt},
            ])
        except Exception as e:
            return f"Could not analyze: {e}"

    @staticmethod
    def _score_source(source: Source, topic: str) -> float:
        """Score source quality (0.0-1.0) based on heuristics.

        Factors: content length, findings length, domain authority signals,
        keyword overlap with topic.
        """
        score = 0.0

        # Content length (longer = likely more substantive)
        content_len = len(source.content)
        if content_len > 3000:
            score += 0.25
        elif content_len > 1000:
            score += 0.15
        elif content_len > 300:
            score += 0.05

        # Findings length (more analysis = more relevant)
        findings_len = len(source.findings)
        if findings_len > 500:
            score += 0.25
        elif findings_len > 200:
            score += 0.15
        elif findings_len > 50:
            score += 0.05

        # Domain authority heuristics
        url = source.url.lower()
        high_quality_domains = [
            '.edu', '.gov', '.org', 'arxiv.org', 'nature.com', 'science.org',
            'ieee.org', 'acm.org', 'springer.com', 'wiley.com',
            'wikipedia.org', 'github.com', 'stackoverflow.com',
        ]
        if any(d in url for d in high_quality_domains):
            score += 0.25

        # Keyword overlap
        topic_words = set(topic.lower().split())
        content_lower = source.content.lower()
        matches = sum(1 for w in topic_words if w in content_lower and len(w) > 3)
        if topic_words:
            overlap = matches / len(topic_words)
            score += min(0.25, overlap * 0.25)

        return min(1.0, score)

    def _synthesize(self, llm: LLMClient, state: ResearchState, persona_context: str = "", stream: bool = False) -> str:
        """Synthesize all findings into a final report."""
        # Build findings with source attribution, sorted by relevance
        scored_sources = sorted(
            [s for s in state.sources if s.findings],
            key=lambda s: s.relevance,
            reverse=True,
        )
        parts = []
        for source in scored_sources:
            parts.append(f"### {source.title}\nURL: {source.url}\nRelevance: {source.relevance:.2f}\n{source.findings}")

        all_findings = "\n\n".join(parts) if parts else "No detailed findings available."

        prompt = SYNTHESIS_PROMPT.format(
            topic=state.topic,
            all_findings=all_findings,
        )
        if persona_context:
            prompt += f"\n\nAdditional context: {persona_context}"

        messages = [
            {"role": "system", "content": "You are an expert research report writer."},
            {"role": "user", "content": prompt},
        ]

        if stream:
            # Stream to terminal and collect
            collected = []
            import sys
            console.print()  # newline before stream
            for chunk in llm.stream(messages, temperature=0.4):
                sys.stdout.write(chunk)
                sys.stdout.flush()
                collected.append(chunk)
            sys.stdout.write("\n")
            sys.stdout.flush()
            return "".join(collected)

        try:
            return llm.chat(messages, temperature=0.4)
        except Exception as e:
            return f"# Research: {state.topic}\n\nError synthesizing report: {e}\n\n## Raw Findings\n\n" + all_findings
