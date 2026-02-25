"""Tests for deepworm.http_middleware module."""

import time

import pytest

from deepworm.http_middleware import (
    MiddlewareEntry,
    MiddlewareFunc,
    MiddlewarePhase,
    MiddlewareStack,
    Request,
    RequestLog,
    RequestLogger,
    RequestMethod,
    Response,
    auth_middleware,
    content_type_middleware,
    create_logger,
    create_middleware_stack,
    create_request,
    create_response,
    header_injection,
    retry_middleware,
    timeout_middleware,
    user_agent_middleware,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok_handler(request: Request) -> Response:
    """Final handler that returns 200 OK."""
    return Response(status_code=200, body="ok")


def _echo_handler(request: Request) -> Response:
    """Final handler that echoes request info."""
    return Response(
        status_code=200,
        body=f"{request.method.value} {request.url}",
        headers=dict(request.headers),
    )


def _error_handler(request: Request) -> Response:
    """Final handler that raises an error."""
    raise RuntimeError("handler error")


def _server_error_handler(request: Request) -> Response:
    """Final handler that returns 500."""
    return Response(status_code=500, body="server error")


# ---------------------------------------------------------------------------
# RequestMethod enum
# ---------------------------------------------------------------------------


class TestRequestMethod:
    def test_values(self):
        assert RequestMethod.GET.value == "GET"
        assert RequestMethod.POST.value == "POST"
        assert RequestMethod.DELETE.value == "DELETE"

    def test_count(self):
        assert len(RequestMethod) == 7


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class TestRequest:
    def test_creation(self):
        req = Request(method=RequestMethod.GET, url="https://example.com")
        assert req.method == RequestMethod.GET
        assert req.url == "https://example.com"

    def test_has_body(self):
        req = Request(method=RequestMethod.POST, url="/api", body="data")
        assert req.has_body
        req2 = Request(method=RequestMethod.GET, url="/api")
        assert not req2.has_body
        req3 = Request(method=RequestMethod.GET, url="/api", body="")
        assert not req3.has_body

    def test_headers(self):
        req = Request(method=RequestMethod.GET, url="/")
        req.set_header("X-Custom", "value")
        assert req.get_header("X-Custom") == "value"
        assert req.get_header("Missing", "default") == "default"

    def test_to_dict(self):
        req = Request(method=RequestMethod.POST, url="/api", body="test")
        d = req.to_dict()
        assert d["method"] == "POST"
        assert d["url"] == "/api"
        assert d["body"] == "test"

    def test_params(self):
        req = Request(method=RequestMethod.GET, url="/", params={"q": "test"})
        assert req.params["q"] == "test"


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class TestResponse:
    def test_success(self):
        r = Response(status_code=200)
        assert r.is_success
        assert not r.is_error

    def test_redirect(self):
        r = Response(status_code=301)
        assert r.is_redirect
        assert not r.is_success

    def test_client_error(self):
        r = Response(status_code=404)
        assert r.is_client_error
        assert r.is_error

    def test_server_error(self):
        r = Response(status_code=500)
        assert r.is_server_error
        assert r.is_error

    def test_headers(self):
        r = Response(status_code=200)
        r.set_header("Content-Type", "text/plain")
        assert r.get_header("Content-Type") == "text/plain"

    def test_to_dict(self):
        r = Response(status_code=200, body="ok", elapsed_ms=1.234)
        d = r.to_dict()
        assert d["status_code"] == 200
        assert d["elapsed_ms"] == 1.23


# ---------------------------------------------------------------------------
# MiddlewareEntry
# ---------------------------------------------------------------------------


class TestMiddlewareEntry:
    def test_creation(self):
        entry = MiddlewareEntry(name="test", handler=lambda r, n: n(r))
        assert entry.name == "test"
        assert entry.enabled
        assert entry.priority == 0
        assert entry.phase == MiddlewarePhase.REQUEST

    def test_empty_name_raises(self):
        with pytest.raises(ValueError):
            MiddlewareEntry(name="", handler=lambda r, n: n(r))


# ---------------------------------------------------------------------------
# MiddlewareStack
# ---------------------------------------------------------------------------


class TestMiddlewareStack:
    def test_empty_stack(self):
        stack = MiddlewareStack()
        req = Request(method=RequestMethod.GET, url="/")
        resp = stack.execute(req, _ok_handler)
        assert resp.status_code == 200
        assert stack.request_count == 1

    def test_single_middleware(self):
        stack = MiddlewareStack()

        def add_header(request, next_handler):
            request.set_header("X-MW", "applied")
            return next_handler(request)

        stack.use(add_header, name="add_header")
        req = Request(method=RequestMethod.GET, url="/")
        resp = stack.execute(req, _echo_handler)
        assert resp.headers.get("X-MW") == "applied"

    def test_middleware_chain_order(self):
        stack = MiddlewareStack()
        order = []

        def mw1(request, next_handler):
            order.append("mw1_before")
            resp = next_handler(request)
            order.append("mw1_after")
            return resp

        def mw2(request, next_handler):
            order.append("mw2_before")
            resp = next_handler(request)
            order.append("mw2_after")
            return resp

        stack.use(mw1, name="mw1", priority=10)
        stack.use(mw2, name="mw2", priority=5)

        req = Request(method=RequestMethod.GET, url="/")
        stack.execute(req, _ok_handler)
        assert order == ["mw1_before", "mw2_before", "mw2_after", "mw1_after"]

    def test_remove_middleware(self):
        stack = MiddlewareStack()
        stack.use(lambda r, n: n(r), name="removable")
        assert len(stack.middlewares) == 1
        assert stack.remove("removable")
        assert len(stack.middlewares) == 0
        assert not stack.remove("nonexistent")

    def test_enable_disable(self):
        stack = MiddlewareStack()
        called = []

        def tracked(request, next_handler):
            called.append(True)
            return next_handler(request)

        stack.use(tracked, name="tracked")
        req = Request(method=RequestMethod.GET, url="/")

        stack.execute(req, _ok_handler)
        assert len(called) == 1

        stack.disable("tracked")
        stack.execute(req, _ok_handler)
        assert len(called) == 1  # not called again

        stack.enable("tracked")
        stack.execute(req, _ok_handler)
        assert len(called) == 2

    def test_error_handling(self):
        stack = MiddlewareStack()
        stack.use(lambda r, n: n(r), name="passthrough")

        error_handled = []

        def error_mw(request, next_handler):
            error_handled.append(request.metadata.get("error", ""))
            return Response(status_code=500, body="error handled")

        stack.use(error_mw, name="error_handler", phase=MiddlewarePhase.ERROR)

        req = Request(method=RequestMethod.GET, url="/")
        resp = stack.execute(req, _error_handler)
        assert resp.status_code == 500
        assert "error handled" in resp.body
        assert stack.error_count == 1

    def test_error_without_handler(self):
        stack = MiddlewareStack()
        req = Request(method=RequestMethod.GET, url="/")
        with pytest.raises(RuntimeError):
            stack.execute(req, _error_handler)

    def test_reset_stats(self):
        stack = MiddlewareStack()
        req = Request(method=RequestMethod.GET, url="/")
        stack.execute(req, _ok_handler)
        assert stack.request_count == 1
        stack.reset_stats()
        assert stack.request_count == 0


# ---------------------------------------------------------------------------
# RequestLogger
# ---------------------------------------------------------------------------


class TestRequestLogger:
    def test_logs_requests(self):
        logger = RequestLogger()
        stack = MiddlewareStack()
        stack.use(logger.middleware, name="logger")

        req = Request(method=RequestMethod.GET, url="/test")
        stack.execute(req, _ok_handler)

        assert logger.total_requests == 1
        assert logger.logs[0].method == "GET"
        assert logger.logs[0].url == "/test"
        assert logger.logs[0].status_code == 200

    def test_logs_multiple(self):
        logger = RequestLogger()
        stack = MiddlewareStack()
        stack.use(logger.middleware, name="logger")

        for i in range(5):
            req = Request(method=RequestMethod.GET, url=f"/test/{i}")
            stack.execute(req, _ok_handler)

        assert logger.total_requests == 5

    def test_max_entries(self):
        logger = RequestLogger(max_entries=3)
        stack = MiddlewareStack()
        stack.use(logger.middleware, name="logger")

        for i in range(10):
            req = Request(method=RequestMethod.GET, url=f"/test/{i}")
            stack.execute(req, _ok_handler)

        assert logger.total_requests == 3
        assert logger.logs[0].url == "/test/7"

    def test_summary(self):
        logger = RequestLogger()
        stack = MiddlewareStack()
        stack.use(logger.middleware, name="logger")

        req = Request(method=RequestMethod.GET, url="/test")
        stack.execute(req, _ok_handler)

        summary = logger.summary()
        assert summary["total"] == 1
        assert summary["errors"] == 0
        assert "avg_ms" in summary

    def test_empty_summary(self):
        logger = RequestLogger()
        assert logger.summary() == {"total": 0}

    def test_clear(self):
        logger = RequestLogger()
        stack = MiddlewareStack()
        stack.use(logger.middleware, name="logger")
        req = Request(method=RequestMethod.GET, url="/")
        stack.execute(req, _ok_handler)
        assert logger.total_requests == 1
        logger.clear()
        assert logger.total_requests == 0


# ---------------------------------------------------------------------------
# Built-in middleware factories
# ---------------------------------------------------------------------------


class TestHeaderInjection:
    def test_injects_headers(self):
        stack = MiddlewareStack()
        stack.use(header_injection({"X-API-Key": "abc123"}), name="headers")

        req = Request(method=RequestMethod.GET, url="/")
        stack.execute(req, _echo_handler)
        assert req.get_header("X-API-Key") == "abc123"

    def test_multiple_headers(self):
        stack = MiddlewareStack()
        stack.use(
            header_injection({"X-A": "1", "X-B": "2"}),
            name="headers",
        )

        req = Request(method=RequestMethod.GET, url="/")
        stack.execute(req, _echo_handler)
        assert req.get_header("X-A") == "1"
        assert req.get_header("X-B") == "2"


class TestTimeoutMiddleware:
    def test_sets_timeout(self):
        stack = MiddlewareStack()
        stack.use(timeout_middleware(5000), name="timeout")

        req = Request(method=RequestMethod.GET, url="/")
        stack.execute(req, _ok_handler)
        assert req.metadata["timeout_ms"] == 5000


class TestAuthMiddleware:
    def test_bearer_auth(self):
        stack = MiddlewareStack()
        stack.use(auth_middleware("mytoken"), name="auth")

        req = Request(method=RequestMethod.GET, url="/")
        stack.execute(req, _echo_handler)
        assert req.get_header("Authorization") == "Bearer mytoken"

    def test_custom_scheme(self):
        stack = MiddlewareStack()
        stack.use(auth_middleware("key123", scheme="Basic"), name="auth")

        req = Request(method=RequestMethod.GET, url="/")
        stack.execute(req, _echo_handler)
        assert req.get_header("Authorization") == "Basic key123"


class TestContentTypeMiddleware:
    def test_default(self):
        stack = MiddlewareStack()
        stack.use(content_type_middleware(), name="ct")

        req = Request(method=RequestMethod.GET, url="/")
        stack.execute(req, _echo_handler)
        assert req.get_header("Content-Type") == "application/json"

    def test_custom(self):
        stack = MiddlewareStack()
        stack.use(content_type_middleware("text/xml"), name="ct")

        req = Request(method=RequestMethod.GET, url="/")
        stack.execute(req, _echo_handler)
        assert req.get_header("Content-Type") == "text/xml"


class TestUserAgentMiddleware:
    def test_default(self):
        stack = MiddlewareStack()
        stack.use(user_agent_middleware(), name="ua")

        req = Request(method=RequestMethod.GET, url="/")
        stack.execute(req, _echo_handler)
        assert req.get_header("User-Agent") == "deepworm/1.0"


class TestRetryMiddleware:
    def test_no_retry_on_success(self):
        call_count = [0]

        def counting_handler(request):
            call_count[0] += 1
            return Response(status_code=200, body="ok")

        stack = MiddlewareStack()
        stack.use(retry_middleware(max_retries=3, backoff_ms=1), name="retry")

        req = Request(method=RequestMethod.GET, url="/")
        resp = stack.execute(req, counting_handler)
        assert resp.status_code == 200
        assert call_count[0] == 1

    def test_retries_on_server_error(self):
        call_count = [0]

        def failing_then_ok(request):
            call_count[0] += 1
            if call_count[0] < 3:
                return Response(status_code=500, body="error")
            return Response(status_code=200, body="ok")

        stack = MiddlewareStack()
        stack.use(retry_middleware(max_retries=3, backoff_ms=1), name="retry")

        req = Request(method=RequestMethod.GET, url="/")
        resp = stack.execute(req, failing_then_ok)
        assert resp.status_code == 200
        assert call_count[0] == 3


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


class TestFactories:
    def test_create_response(self):
        r = create_response(404, "not found")
        assert r.status_code == 404
        assert r.body == "not found"

    def test_create_request(self):
        r = create_request("POST", "/api", body="data")
        assert r.method == RequestMethod.POST
        assert r.body == "data"

    def test_create_middleware_stack(self):
        stack = create_middleware_stack()
        assert isinstance(stack, MiddlewareStack)
        assert len(stack.middlewares) == 0

    def test_create_logger(self):
        logger = create_logger(500)
        assert isinstance(logger, RequestLogger)
