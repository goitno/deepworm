"""Opt-in anonymous Parallel Search MCP backend (Python 3.10+)."""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import httpx

from . import __version__
from .search import SearchResult

_ENDPOINT = "https://search.parallel.ai/mcp"
_USER_AGENT = f"deepworm/{__version__}"
_TIMEOUT = 30.0
# Reuse an identity across concurrent queries and retries, rather than rotating
# free-tier accounting with each connection. No credentials are read or sent.
_SESSION_ID = uuid4().hex


def search_parallel(query: str, max_results: int) -> list[SearchResult]:
    """Search anonymously through MCP's Streamable HTTP transport.

    Requires the ``parallel`` extra. Errors propagate to search_web's existing
    DuckDuckGo fallback; cancellation is not swallowed.
    """
    return asyncio.run(_search_parallel(query, max_results))


async def _search_parallel(query: str, max_results: int) -> list[SearchResult]:
    # Lazy imports keep the core install and other search providers independent
    # of the MCP SDK, which requires Python 3.10 or later.
    import anyio
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    with anyio.fail_after(_TIMEOUT):
        async with httpx.AsyncClient(
            headers={"User-Agent": _USER_AGENT}, timeout=_TIMEOUT,
        ) as client:
            async with streamable_http_client(
                _ENDPOINT, http_client=client,
            ) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    response = await session.call_tool("web_search", {
                        "objective": query,
                        "search_queries": [query],
                        "session_id": _SESSION_ID,
                    })

    if response.isError:
        raise RuntimeError("Parallel Search MCP returned a tool error")
    data = response.structuredContent
    if data is None:
        # Older MCP servers may return the same JSON as text content.
        data = json.loads("\n".join(
            block.text for block in response.content if block.type == "text"
        ))
    results = []
    for item in data["results"][:max_results]:
        results.append(SearchResult(
            title=item.get("title") or item["url"],
            url=item["url"],
            snippet="\n\n".join(item["excerpts"]),
        ))
    return results
