"""Async research API.

Provides an asyncio-compatible interface for integrating deepworm
into async web frameworks (FastAPI, Starlette, aiohttp, etc.).
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, Optional

from .cache import Cache, get_cache
from .config import Config
from .events import Event, EventEmitter, EventType
from .researcher import DeepResearcher

logger = logging.getLogger(__name__)


class AsyncResearcher:
    """Async wrapper around DeepResearcher.

    Runs the synchronous research engine in a thread pool executor
    so it doesn't block the event loop.

    Usage:
        researcher = AsyncResearcher()
        report = await researcher.research("quantum computing")

        # With streaming
        async for chunk in researcher.research_stream("AI safety"):
            print(chunk, end="")
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        cache: Optional[Cache] = None,
        events: Optional[EventEmitter] = None,
    ):
        self.config = config or Config.auto()
        self.cache = cache if cache is not None else get_cache()
        self.events = events or EventEmitter()

    async def research(
        self,
        topic: str,
        verbose: bool = False,
        persona: str | None = None,
    ) -> str:
        """Run deep research asynchronously.

        Args:
            topic: Research topic or question.
            verbose: Show progress output.
            persona: Optional research perspective.

        Returns:
            Markdown research report.
        """
        loop = asyncio.get_event_loop()
        researcher = DeepResearcher(
            config=self.config,
            cache=self.cache,
            events=self.events,
        )

        return await loop.run_in_executor(
            None,
            lambda: researcher.research(topic, verbose=verbose, persona=persona),
        )

    async def research_stream(
        self,
        topic: str,
        verbose: bool = False,
        persona: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream research progress events asynchronously.

        Yields event messages as they occur during research.
        The final yield is the complete report.
        """
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        events = EventEmitter()

        def on_event(event: Event) -> None:
            asyncio.get_event_loop().call_soon_threadsafe(
                queue.put_nowait, f"[{event.type.value}] {event.message}\n"
            )

        events.on_all(on_event)

        # Also forward to user's event emitter
        if self.events:
            events.on_all(lambda e: self.events.emit(e))

        researcher = DeepResearcher(
            config=self.config,
            cache=self.cache,
            events=events,
        )

        loop = asyncio.get_event_loop()

        async def _run() -> str:
            return await loop.run_in_executor(
                None,
                lambda: researcher.research(topic, verbose=verbose, persona=persona),
            )

        task = asyncio.create_task(_run())

        # Yield events as they come
        while not task.done():
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=0.1)
                if msg is not None:
                    yield msg
            except asyncio.TimeoutError:
                continue

        # Drain remaining messages
        while not queue.empty():
            msg = queue.get_nowait()
            if msg is not None:
                yield msg

        # Yield final report
        report = await task
        yield report


async def async_research(topic: str, **kwargs) -> str:
    """Quick async research function.

    Usage:
        import asyncio
        from deepworm.async_api import async_research
        report = asyncio.run(async_research("topic"))
    """
    researcher = AsyncResearcher(**kwargs)
    return await researcher.research(topic)
