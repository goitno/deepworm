"""Custom exceptions for deepworm.

Provides user-friendly error messages for common failure scenarios.
"""

from __future__ import annotations


class DeepWormError(Exception):
    """Base exception for all deepworm errors."""

    def __init__(self, message: str, hint: str = ""):
        self.hint = hint
        super().__init__(message)

    def friendly(self) -> str:
        """Return a user-friendly error message with optional hint."""
        msg = str(self)
        if self.hint:
            msg += f"\n  Hint: {self.hint}"
        return msg


class ConfigError(DeepWormError):
    """Invalid or missing configuration."""


class ProviderError(DeepWormError):
    """LLM provider is unavailable or misconfigured."""


class APIKeyError(ProviderError):
    """API key is missing or invalid."""


class ModelNotFoundError(ProviderError):
    """Requested model not found on the provider."""


class RateLimitError(ProviderError):
    """Provider rate limit exceeded."""

    def __init__(self, provider: str, retry_after: float | None = None):
        self.retry_after = retry_after
        hint = "Wait a moment and retry, or use a different model/provider."
        if retry_after:
            hint = f"Retry after {retry_after:.0f}s, or use a different model/provider."
        super().__init__(
            f"Rate limit exceeded for {provider}",
            hint=hint,
        )


class SearchError(DeepWormError):
    """Web search failed."""


class NetworkError(DeepWormError):
    """Network connectivity issue."""


class ContentExtractionError(DeepWormError):
    """Failed to extract content from a web page."""


class SessionError(DeepWormError):
    """Error loading or saving a research session."""
