"""Exercise opt-in Parallel selection through the real MCP HTTP client."""

import asyncio
import json

import httpx
import pytest

pytest.importorskip("mcp")

from deepworm import parallel
from deepworm.cache import Cache
from deepworm.config import Config
from deepworm.researcher import DeepResearcher
from deepworm.search import SearchResult, search_web


@pytest.fixture
def mcp_http(monkeypatch):
    """Replace only the network boundary; run MCP negotiation and dispatch."""
    requests = []
    clients = []
    data = {"results": [{
        "url": "https://example.org/batteries", "title": "Battery research",
        "excerpts": ["A new solid-state design.", "Results from a recent study."],
    }]}
    state = {"data": data, "error": False, "text_only": False, "block": False}

    async def handler(request):
        requests.append(request)
        assert str(request.url) == "https://search.parallel.ai/mcp"
        assert request.headers["user-agent"] == parallel._USER_AGENT
        assert "authorization" not in request.headers
        message = json.loads(request.content)
        method = message["method"]
        if "id" not in message:
            return httpx.Response(202)
        if method == "initialize":
            result = {
                "protocolVersion": message["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "parallel-fixture", "version": "1"},
            }
        elif method == "tools/list":
            result = {"tools": [{"name": "web_search", "inputSchema": {"type": "object"}}]}
        else:
            assert method == "tools/call"
            if state["block"]:
                state["started"].set()
                await asyncio.Event().wait()
            if state.get("http_error"):
                return httpx.Response(503)
            result = {
                "isError": state["error"],
                "content": [{"type": "text", "text": json.dumps(state["data"])}],
            }
            if not state["text_only"]:
                result["structuredContent"] = state["data"]
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": message["id"], "result": result})

    real_client = httpx.AsyncClient

    def client_factory(**kwargs):
        client = real_client(transport=httpx.MockTransport(handler), **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(parallel.httpx, "AsyncClient", client_factory)
    state.update(requests=requests, clients=clients)
    return state


def test_research_selection_and_result_consumption(mcp_http, monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPWORM_SEARCH_PROVIDER", "parallel")
    monkeypatch.setenv("PARALLEL_API_KEY", "unused-fixture-key")
    config = Config.from_env(api_key="local-fixture", provider="ollama")
    assert config.search_provider == "parallel"
    monkeypatch.setattr("deepworm.researcher.fetch_page_text", lambda *a, **kw: "")
    monkeypatch.setattr("deepworm.search._search_ddgs", lambda *a: pytest.fail("Unexpected fallback"))
    researcher = DeepResearcher(config, cache=Cache(tmp_path))
    sources = researcher._search_and_fetch(["solid state battery research"])
    assert len(sources) == 1
    assert sources[0].url == "https://example.org/batteries"
    assert sources[0].title == "Battery research"
    assert sources[0].content == "A new solid-state design.\n\nResults from a recent study."
    calls = [json.loads(r.content)["params"] for r in mcp_http["requests"]
             if json.loads(r.content)["method"] == "tools/call"]
    assert calls == [{"name": "web_search", "arguments": {
        "objective": "solid state battery research",
        "search_queries": ["solid state battery research"],
        "session_id": parallel._SESSION_ID,
    }}]
    assert all(c.is_closed for c in mcp_http["clients"])


def test_cache_isolated_and_session_reused(mcp_http, tmp_path):
    cache = Cache(tmp_path)
    cache.set("search", "query", [{"title": "Old default", "url": "https://old.org", "snippet": "old"}])
    assert search_web("query", provider="parallel", cache=cache)[0].title == "Battery research"
    count = len(mcp_http["requests"])
    assert search_web("query", provider="parallel", cache=cache)[0].title == "Battery research"
    assert len(mcp_http["requests"]) == count
    assert search_web("query", cache=cache)[0].title == "Old default"
    search_web("another query", provider="parallel")
    sessions = [json.loads(r.content)["params"]["arguments"]["session_id"]
                for r in mcp_http["requests"] if json.loads(r.content)["method"] == "tools/call"]
    assert sessions == [parallel._SESSION_ID, parallel._SESSION_ID]


def test_text_response_and_result_limit(mcp_http):
    mcp_http["text_only"] = True
    mcp_http["data"]["results"] *= 3
    mcp_http["data"]["results"][0]["title"] = None
    results = search_web("query", provider="parallel", max_results=2)
    assert len(results) == 2
    assert results[0].title == "https://example.org/batteries"


@pytest.mark.parametrize("failure", ["tool", "http", "malformed", "empty", "timeout"])
def test_failure_falls_back_and_closes_client(mcp_http, monkeypatch, failure):
    if failure == "tool":
        mcp_http["error"] = True
    elif failure == "http":
        mcp_http["http_error"] = True
    elif failure == "malformed":
        mcp_http["data"] = {"unexpected": []}
    elif failure == "empty":
        mcp_http["data"] = {"results": []}
    else:
        mcp_http["block"] = True
        mcp_http["started"] = asyncio.Event()
        monkeypatch.setattr(parallel, "_TIMEOUT", 0.05)
    fallback = [SearchResult("Fallback", "https://fallback.org", "DDG result")]
    monkeypatch.setattr("deepworm.search._search_ddgs", lambda *a: fallback)
    assert search_web("query", provider="parallel") == fallback
    assert all(c.is_closed for c in mcp_http["clients"])


def test_cancellation_propagates_and_closes_client(mcp_http):
    async def run():
        mcp_http["block"] = True
        mcp_http["started"] = asyncio.Event()
        task = asyncio.create_task(parallel._search_parallel("query", 1))
        await asyncio.wait_for(mcp_http["started"].wait(), timeout=2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(run())
    assert all(c.is_closed for c in mcp_http["clients"])


def test_default_does_not_load_parallel(monkeypatch):
    assert Config(api_key="local-fixture").search_provider == "duckduckgo"
    monkeypatch.setattr(parallel, "search_parallel", lambda *a: pytest.fail("Parallel was not selected"))
    default = [SearchResult("Default", "https://default.org", "default")]
    monkeypatch.setattr("deepworm.search._search_ddgs", lambda *a: default)
    assert search_web("query") == default


def test_missing_optional_sdk_falls_back(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def without_mcp(name, *args, **kwargs):
        if name == "mcp" or name.startswith("mcp."):
            raise ModuleNotFoundError("MCP extra not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_mcp)
    fallback = [SearchResult("Fallback", "https://fallback.org", "DDG result")]
    monkeypatch.setattr("deepworm.search._search_ddgs", lambda *a: fallback)
    assert search_web("query", provider="parallel") == fallback
