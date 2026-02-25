"""HTTP middleware and request/response processing for deepworm.

Provides middleware pipeline for HTTP requests, response caching,
request logging, retry logic, and rate limiting at the HTTP layer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class MiddlewarePhase(Enum):
    """Phase of middleware execution."""

    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"


class RequestMethod(Enum):
    """HTTP request methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class Request:
    """HTTP request representation."""

    method: RequestMethod
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    params: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def has_body(self) -> bool:
        return self.body is not None and len(self.body) > 0

    def set_header(self, key: str, value: str) -> None:
        self.headers[key] = value

    def get_header(self, key: str, default: str = "") -> str:
        return self.headers.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method.value,
            "url": self.url,
            "headers": dict(self.headers),
            "body": self.body,
            "params": dict(self.params),
            "timestamp": self.timestamp,
        }


@dataclass
class Response:
    """HTTP response representation."""

    status_code: int
    body: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_redirect(self) -> bool:
        return 300 <= self.status_code < 400

    @property
    def is_client_error(self) -> bool:
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        return 500 <= self.status_code < 600

    @property
    def is_error(self) -> bool:
        return self.status_code >= 400

    def set_header(self, key: str, value: str) -> None:
        self.headers[key] = value

    def get_header(self, key: str, default: str = "") -> str:
        return self.headers.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "body": self.body,
            "headers": dict(self.headers),
            "elapsed_ms": round(self.elapsed_ms, 2),
        }


# ---------------------------------------------------------------------------
# Middleware types
# ---------------------------------------------------------------------------

# Middleware function signature:
#   (request, next_handler) -> response
MiddlewareFunc = Callable[[Request, Callable[[Request], Response]], Response]


@dataclass
class MiddlewareEntry:
    """A registered middleware with priority and metadata."""

    name: str
    handler: MiddlewareFunc
    priority: int = 0
    enabled: bool = True
    phase: MiddlewarePhase = MiddlewarePhase.REQUEST

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Middleware name cannot be empty")


class MiddlewareStack:
    """Stack of middleware handlers applied to requests/responses."""

    def __init__(self) -> None:
        self._entries: List[MiddlewareEntry] = []
        self._request_count: int = 0
        self._error_count: int = 0

    def use(
        self,
        handler: MiddlewareFunc,
        *,
        name: Optional[str] = None,
        priority: int = 0,
        phase: MiddlewarePhase = MiddlewarePhase.REQUEST,
    ) -> None:
        """Add middleware to the stack."""
        mw_name = name or getattr(handler, "__name__", f"mw_{len(self._entries)}")
        entry = MiddlewareEntry(
            name=mw_name, handler=handler, priority=priority, phase=phase,
        )
        self._entries.append(entry)

    def remove(self, name: str) -> bool:
        """Remove middleware by name. Returns True if found."""
        for i, entry in enumerate(self._entries):
            if entry.name == name:
                self._entries.pop(i)
                return True
        return False

    def enable(self, name: str) -> bool:
        for entry in self._entries:
            if entry.name == name:
                entry.enabled = True
                return True
        return False

    def disable(self, name: str) -> bool:
        for entry in self._entries:
            if entry.name == name:
                entry.enabled = False
                return True
        return False

    @property
    def middlewares(self) -> List[MiddlewareEntry]:
        return list(self._entries)

    @property
    def request_count(self) -> int:
        return self._request_count

    @property
    def error_count(self) -> int:
        return self._error_count

    def _sorted_entries(self, phase: MiddlewarePhase) -> List[MiddlewareEntry]:
        """Get enabled entries for a given phase sorted by priority (higher first)."""
        return sorted(
            [e for e in self._entries if e.enabled and e.phase == phase],
            key=lambda e: e.priority,
            reverse=True,
        )

    def execute(
        self,
        request: Request,
        final_handler: Callable[[Request], Response],
    ) -> Response:
        """Execute the middleware chain for a request."""
        self._request_count += 1

        # Build chain from sorted request-phase middleware
        entries = self._sorted_entries(MiddlewarePhase.REQUEST)

        def build_chain(
            remaining: List[MiddlewareEntry],
        ) -> Callable[[Request], Response]:
            if not remaining:
                return final_handler

            current = remaining[0]
            rest = remaining[1:]

            def handler(req: Request) -> Response:
                next_handler = build_chain(rest)
                return current.handler(req, next_handler)

            return handler

        chain = build_chain(entries)

        try:
            response = chain(request)
        except Exception as e:
            self._error_count += 1
            # Run error middleware
            for entry in self._sorted_entries(MiddlewarePhase.ERROR):
                try:
                    error_req = Request(
                        method=request.method,
                        url=request.url,
                        headers=request.headers,
                        metadata={"error": str(e), **request.metadata},
                    )
                    response = entry.handler(error_req, final_handler)
                    return response
                except Exception:
                    continue
            raise

        # Run response-phase middleware
        for entry in self._sorted_entries(MiddlewarePhase.RESPONSE):
            try:
                resp_req = Request(
                    method=request.method,
                    url=request.url,
                    headers=request.headers,
                    metadata={"response": response, **request.metadata},
                )
                entry.handler(resp_req, lambda _r: response)
            except Exception:
                pass

        return response

    def reset_stats(self) -> None:
        self._request_count = 0
        self._error_count = 0


# ---------------------------------------------------------------------------
# Built-in middleware factories
# ---------------------------------------------------------------------------

@dataclass
class RequestLog:
    """Log entry for a request."""

    method: str
    url: str
    status_code: int
    elapsed_ms: float
    timestamp: float
    error: str = ""


class RequestLogger:
    """Middleware that logs all requests."""

    def __init__(self, max_entries: int = 1000) -> None:
        self._logs: List[RequestLog] = []
        self._max_entries = max_entries

    @property
    def logs(self) -> List[RequestLog]:
        return list(self._logs)

    @property
    def total_requests(self) -> int:
        return len(self._logs)

    def clear(self) -> None:
        self._logs.clear()

    def middleware(self, request: Request, next_handler: Callable) -> Response:
        """The middleware function."""
        start = time.perf_counter()
        try:
            response = next_handler(request)
            elapsed = (time.perf_counter() - start) * 1000
            log = RequestLog(
                method=request.method.value,
                url=request.url,
                status_code=response.status_code,
                elapsed_ms=elapsed,
                timestamp=request.timestamp,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            log = RequestLog(
                method=request.method.value,
                url=request.url,
                status_code=0,
                elapsed_ms=elapsed,
                timestamp=request.timestamp,
                error=str(e),
            )
            self._add_log(log)
            raise

        self._add_log(log)
        return response

    def _add_log(self, log: RequestLog) -> None:
        self._logs.append(log)
        if len(self._logs) > self._max_entries:
            self._logs = self._logs[-self._max_entries:]

    def summary(self) -> Dict[str, Any]:
        if not self._logs:
            return {"total": 0}
        times = [l.elapsed_ms for l in self._logs]
        errors = sum(1 for l in self._logs if l.error)
        return {
            "total": len(self._logs),
            "errors": errors,
            "avg_ms": round(sum(times) / len(times), 2),
            "min_ms": round(min(times), 2),
            "max_ms": round(max(times), 2),
        }


def header_injection(headers: Dict[str, str]) -> MiddlewareFunc:
    """Create middleware that injects headers into every request."""
    def middleware(request: Request, next_handler: Callable) -> Response:
        for key, value in headers.items():
            request.set_header(key, value)
        return next_handler(request)
    return middleware


def timeout_middleware(timeout_ms: float) -> MiddlewareFunc:
    """Create middleware that adds timeout metadata to requests."""
    def middleware(request: Request, next_handler: Callable) -> Response:
        request.metadata["timeout_ms"] = timeout_ms
        return next_handler(request)
    return middleware


def retry_middleware(
    max_retries: int = 3,
    retry_on: Optional[List[int]] = None,
    backoff_ms: float = 100,
) -> MiddlewareFunc:
    """Create middleware that retries failed requests."""
    retry_codes = retry_on or [429, 500, 502, 503, 504]

    def middleware(request: Request, next_handler: Callable) -> Response:
        last_response = None
        for attempt in range(max_retries + 1):
            try:
                response = next_handler(request)
                if response.status_code not in retry_codes:
                    return response
                last_response = response
            except Exception:
                if attempt == max_retries:
                    raise
                last_response = None

            if attempt < max_retries:
                wait = backoff_ms * (2 ** attempt) / 1000
                time.sleep(wait)

        return last_response or Response(status_code=500, body="Max retries exceeded")

    return middleware


def auth_middleware(token: str, scheme: str = "Bearer") -> MiddlewareFunc:
    """Create middleware that adds authorization headers."""
    def middleware(request: Request, next_handler: Callable) -> Response:
        request.set_header("Authorization", f"{scheme} {token}")
        return next_handler(request)
    return middleware


def content_type_middleware(content_type: str = "application/json") -> MiddlewareFunc:
    """Create middleware that sets content-type header."""
    def middleware(request: Request, next_handler: Callable) -> Response:
        request.set_header("Content-Type", content_type)
        return next_handler(request)
    return middleware


def user_agent_middleware(user_agent: str = "deepworm/1.0") -> MiddlewareFunc:
    """Create middleware that sets user-agent header."""
    def middleware(request: Request, next_handler: Callable) -> Response:
        request.set_header("User-Agent", user_agent)
        return next_handler(request)
    return middleware


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def create_response(
    status_code: int = 200,
    body: str = "",
    headers: Optional[Dict[str, str]] = None,
) -> Response:
    """Create a response."""
    return Response(
        status_code=status_code,
        body=body,
        headers=headers or {},
    )


def create_request(
    method: str = "GET",
    url: str = "",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[str] = None,
    params: Optional[Dict[str, str]] = None,
) -> Request:
    """Create a request."""
    method_enum = RequestMethod(method.upper())
    return Request(
        method=method_enum,
        url=url,
        headers=headers or {},
        body=body,
        params=params or {},
    )


def create_middleware_stack() -> MiddlewareStack:
    """Create a new middleware stack."""
    return MiddlewareStack()


def create_logger(max_entries: int = 1000) -> RequestLogger:
    """Create a new request logger."""
    return RequestLogger(max_entries=max_entries)
