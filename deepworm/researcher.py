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

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import Config
from .llm import LLMClient, get_client
from .search import SearchResult, fetch_page_text, search_web

console = Console()


@dataclass
class Source:
    """A research source with extracted information."""
    url: str
    title: str
    content: str
    findings: str = ""


@dataclass
class ResearchState:
    """Tracks the state of an ongoing research session."""
    topic: str
    queries: list[str] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    iterations_done: int = 0


QUERY_GENERATION_PROMPT = """You are a research assistant. Given a research topic, generate {breadth} diverse search queries that would help thoroughly research this topic from different angles.

Topic: {topic}

{context}

Return a JSON array of strings, nothing else. Example: ["query 1", "query 2", "query 3"]"""

FOLLOWUP_QUERY_PROMPT = """You are a research assistant. Based on the research so far, identify knowledge gaps and generate {breadth} follow-up search queries.

Original topic: {topic}

What we know so far:
{findings_summary}

What gaps remain or what aspects need deeper investigation? Return a JSON array of search query strings, nothing else."""

ANALYSIS_PROMPT = """You are a research analyst. Analyze the following source material and extract key findings relevant to the research topic.

Research topic: {topic}

Source: {title} ({url})
Content:
{content}

Provide a concise analysis (3-5 bullet points) of the key findings from this source that are relevant to the research topic. Focus on facts, data, and unique insights."""

SYNTHESIS_PROMPT = """You are an expert research analyst. Synthesize the following research findings into a comprehensive, well-structured report.

Research topic: {topic}

Sources and findings:
{all_findings}

Write a detailed research report in Markdown format. The report should:
1. Start with a clear title and executive summary
2. Organize findings into logical sections with headers
3. Include specific facts, data points, and insights
4. Note any conflicting information or areas of uncertainty
5. End with key takeaways and conclusions
6. Include a Sources section at the end listing all URLs

Write the report directly, no preamble. Make it thorough but readable."""


class DeepResearcher:
    """Main research engine."""

    def __init__(
        self,
        config: Optional[Config] = None,
        on_progress: Optional[Callable[[str], None]] = None,
    ):
        self.config = config or Config.auto()
        self.client: Optional[LLMClient] = None
        self._on_progress = on_progress

    def _progress(self, msg: str) -> None:
        if self._on_progress:
            self._on_progress(msg)

    def _get_client(self) -> LLMClient:
        if self.client is None:
            self.client = get_client(self.config)
        return self.client

    def research(self, topic: str, verbose: bool = True) -> str:
        """Run deep research on a topic and return a markdown report."""
        state = ResearchState(topic=topic)
        llm = self._get_client()

        if verbose:
            console.print(Panel(
                f"[bold]{topic}[/bold]\n\n"
                f"Provider: {self.config.provider} | Model: {self.config.model}\n"
                f"Depth: {self.config.depth} | Breadth: {self.config.breadth}",
                title="deepworm research",
                border_style="blue",
            ))

        for i in range(self.config.depth):
            state.iterations_done = i + 1

            if verbose:
                console.print(f"\n[bold cyan]--- Iteration {i + 1}/{self.config.depth} ---[/bold cyan]")

            # Generate search queries
            if i == 0:
                queries = self._generate_initial_queries(llm, topic)
            else:
                queries = self._generate_followup_queries(llm, state)

            state.queries.extend(queries)

            if verbose:
                console.print(f"[dim]Generated {len(queries)} search queries[/dim]")
                for q in queries:
                    console.print(f"  [dim]• {q}[/dim]")

            # Search and fetch
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
                findings = self._analyze_source(llm, topic, source)
                source.findings = findings
                state.findings.append(findings)

            self._progress(f"Completed iteration {i + 1}")

        # Synthesize
        if verbose:
            console.print("\n[bold green]Synthesizing report...[/bold green]")

        report = self._synthesize(llm, state)

        if verbose:
            console.print("[bold green]Done![/bold green]\n")

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

    def _search_and_fetch(
        self,
        queries: list[str],
        verbose: bool = False,
    ) -> list[Source]:
        """Search web and fetch content for each query (concurrent)."""
        seen_urls: set[str] = set()
        sources: list[Source] = []
        urls_to_fetch: list[SearchResult] = []

        # Collect unique URLs from all queries
        for query in queries:
            results = search_web(query, max_results=self.config.max_sources)
            for r in results:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    urls_to_fetch.append(r)

        # Fetch pages concurrently
        def _fetch(result: SearchResult) -> Source:
            body = fetch_page_text(result.url)
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

    def _synthesize(self, llm: LLMClient, state: ResearchState) -> str:
        """Synthesize all findings into a final report."""
        # Build findings with source attribution
        parts = []
        for source in state.sources:
            if source.findings:
                parts.append(f"### {source.title}\nURL: {source.url}\n{source.findings}")

        all_findings = "\n\n".join(parts) if parts else "No detailed findings available."

        prompt = SYNTHESIS_PROMPT.format(
            topic=state.topic,
            all_findings=all_findings,
        )
        try:
            return llm.chat([
                {"role": "system", "content": "You are an expert research report writer."},
                {"role": "user", "content": prompt},
            ], temperature=0.4)
        except Exception as e:
            return f"# Research: {state.topic}\n\nError synthesizing report: {e}\n\n## Raw Findings\n\n" + all_findings
