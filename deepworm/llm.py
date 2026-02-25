"""LLM provider abstraction layer.

Supports OpenAI, Anthropic, Google, and Ollama (local).
Uses the OpenAI client for OpenAI and Ollama (compatible API).
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Optional

from dataclasses import dataclass, field

from .config import Config
from .exceptions import APIKeyError, ModelNotFoundError, ProviderError, RateLimitError

logger = logging.getLogger("deepworm")

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds

# Approximate cost per million tokens (USD) — updated 2025
_MODEL_COSTS: dict[str, tuple[float, float]] = {
    # (input_cost_per_M, output_cost_per_M)
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-haiku-20240307": (0.25, 1.25),
    "claude-3-opus-20240229": (15.00, 75.00),
    "gemini-2.5-flash": (0.00, 0.00),  # free tier
    "gemini-2.5-pro": (0.00, 0.00),
    "gemini-2.0-flash": (0.00, 0.00),
    "gemini-2.0-flash-lite": (0.00, 0.00),
    "gemini-3-flash-preview": (0.00, 0.00),
}


@dataclass
class TokenUsage:
    """Token usage for a single LLM call."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    estimated_cost_usd: float = 0.0


@dataclass
class TokenTracker:
    """Accumulates token usage across multiple LLM calls."""
    calls: list[TokenUsage] = field(default_factory=list)
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    def record(self, usage: TokenUsage) -> None:
        self.calls.append(usage)
        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens
        self.total_tokens += usage.total_tokens
        self.total_cost_usd += usage.estimated_cost_usd

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def summary(self) -> str:
        parts = [f"{self.total_tokens:,} tokens ({self.call_count} calls)"]
        if self.total_cost_usd > 0:
            parts.append(f"~${self.total_cost_usd:.4f}")
        return " · ".join(parts)


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost in USD for a given model and token counts."""
    for model_key, (inp_cost, out_cost) in _MODEL_COSTS.items():
        if model_key in model:
            return (prompt_tokens * inp_cost + completion_tokens * out_cost) / 1_000_000
    return 0.0


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def get_client(config: Config) -> "LLMClient":
    """Create an LLM client based on config.

    Raises :class:`APIKeyError` if the required API key env var is not set.
    Raises :class:`ProviderError` for unknown providers.
    """
    provider = config.provider

    if provider == "ollama":
        return OpenAICompatibleClient(
            api_key="ollama",
            base_url=config.ollama_base_url,
            model=config.model,
        )
    elif provider == "openai":
        api_key = config.api_key or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise APIKeyError(
                "OpenAI API key not found",
                hint="Set OPENAI_API_KEY environment variable or add api_key to config file",
            )
        return OpenAICompatibleClient(
            api_key=api_key,
            base_url=config.base_url or "https://api.openai.com/v1",
            model=config.model,
        )
    elif provider == "anthropic":
        api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise APIKeyError(
                "Anthropic API key not found",
                hint="Set ANTHROPIC_API_KEY environment variable or add api_key to config file",
            )
        return AnthropicClient(api_key=api_key, model=config.model)
    elif provider == "google":
        api_key = config.api_key or os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            raise APIKeyError(
                "Google API key not found",
                hint="Set GOOGLE_API_KEY environment variable or add api_key to config file",
            )
        return GoogleClient(api_key=api_key, model=config.model)
    elif provider == "openrouter":
        api_key = config.api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            raise APIKeyError(
                "OpenRouter API key not found",
                hint="Set OPENROUTER_API_KEY environment variable or add api_key to config file",
            )
        return OpenAICompatibleClient(
            api_key=api_key,
            base_url=config.base_url or "https://openrouter.ai/api/v1",
            model=config.model,
            extra_headers={
                "HTTP-Referer": "https://github.com/bysiber/deepworm",
                "X-Title": "deepworm",
            },
        )
    else:
        raise ProviderError(
            f"Unknown provider: {provider}",
            hint="Supported providers: openai, anthropic, google, openrouter, ollama",
        )


class LLMClient:
    """Base class for LLM clients."""

    def __init__(self):
        self.token_tracker = TokenTracker()
        self.last_usage: Optional[TokenUsage] = None

    def _record_usage(self, prompt_tokens: int, completion_tokens: int, model: str = "") -> TokenUsage:
        """Record token usage from an API call."""
        total = prompt_tokens + completion_tokens
        cost = _estimate_cost(model or getattr(self, 'model', ''), prompt_tokens, completion_tokens)
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            model=model or getattr(self, 'model', ''),
            estimated_cost_usd=cost,
        )
        self.token_tracker.record(usage)
        self.last_usage = usage
        return usage

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.3) -> str:
        raise NotImplementedError

    def stream(self, messages: list[dict[str, str]], temperature: float = 0.3):
        """Stream chat response. Yields string chunks.

        Default implementation falls back to non-streaming.
        """
        yield self.chat(messages, temperature=temperature)

    def chat_with_retry(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_retries: int = MAX_RETRIES,
    ) -> str:
        """Chat with automatic retry on transient failures.

        Detects rate-limit responses and wraps them as :class:`RateLimitError`.
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                return self.chat(messages, temperature=temperature)
            except Exception as e:
                last_error = e
                # Detect rate-limit errors from any provider
                err_str = str(e).lower()
                if "rate" in err_str and "limit" in err_str:
                    raise RateLimitError(provider=getattr(self, "model", "unknown")) from e
                if attempt < max_retries - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.debug(f"LLM call failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    time.sleep(delay)
        raise last_error  # type: ignore[misc]

    def chat_json(self, messages: list[dict[str, str]], temperature: float = 0.1) -> Any:
        """Chat and parse the response as JSON."""
        response = self.chat_with_retry(messages, temperature=temperature)
        # Try to extract JSON from the response
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            lines = lines[1:]  # skip ```json
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)
        return json.loads(response)


class OpenAICompatibleClient(LLMClient):
    """Client for OpenAI, Ollama, and OpenRouter (OpenAI-compatible API)."""

    def __init__(self, api_key: str, base_url: str, model: str, extra_headers: dict | None = None):
        super().__init__()
        from openai import OpenAI
        kwargs: dict = {"api_key": api_key, "base_url": base_url}
        if extra_headers:
            kwargs["default_headers"] = extra_headers
        self.client = OpenAI(**kwargs)
        self.model = model

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.3) -> str:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
        except Exception as e:
            err = str(e)
            # Some models don't support system instructions — retry with system→user
            if "developer instruction" in err.lower() or "system" in err.lower() and "not" in err.lower():
                fixed = []
                for m in messages:
                    if m.get("role") == "system":
                        fixed.append({"role": "user", "content": f"[Instructions] {m['content']}"})
                    else:
                        fixed.append(m)
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=fixed,
                    temperature=temperature,
                )
            elif "429" in err or "rate" in err.lower():
                from .exceptions import DeepWormError
                raise DeepWormError(
                    f"Rate limited on {self.model}",
                    hint="Try a different model: /set model google/gemini-2.0-flash-001",
                )
            else:
                raise
        # Track token usage from API response
        if resp.usage:
            self._record_usage(
                prompt_tokens=resp.usage.prompt_tokens or 0,
                completion_tokens=resp.usage.completion_tokens or 0,
                model=self.model,
            )
        else:
            # Estimate tokens if API doesn't report
            prompt_text = " ".join(m.get("content", "") for m in messages)
            result_text = resp.choices[0].message.content or ""
            self._record_usage(
                prompt_tokens=_estimate_tokens(prompt_text),
                completion_tokens=_estimate_tokens(result_text),
                model=self.model,
            )
        return resp.choices[0].message.content or ""

    def stream(self, messages: list[dict[str, str]], temperature: float = 0.3):
        """Stream chat response from OpenAI/Ollama."""
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        for chunk in resp:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicClient(LLMClient):
    """Client for Anthropic Claude."""

    def __init__(self, api_key: str, model: str):
        super().__init__()
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.3) -> str:
        # Anthropic expects system message separately
        system_msg = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                chat_messages.append(m)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": chat_messages,
            "temperature": temperature,
        }
        if system_msg:
            kwargs["system"] = system_msg

        resp = self.client.messages.create(**kwargs)
        # Track token usage from Anthropic response
        if hasattr(resp, 'usage') and resp.usage:
            self._record_usage(
                prompt_tokens=getattr(resp.usage, 'input_tokens', 0),
                completion_tokens=getattr(resp.usage, 'output_tokens', 0),
                model=self.model,
            )
        return resp.content[0].text

    def stream(self, messages: list[dict[str, str]], temperature: float = 0.3):
        """Stream chat response from Anthropic."""
        system_msg = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                chat_messages.append(m)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": chat_messages,
            "temperature": temperature,
        }
        if system_msg:
            kwargs["system"] = system_msg

        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text


class GoogleClient(LLMClient):
    """Client for Google Gemini (new google-genai SDK)."""

    def __init__(self, api_key: str, model: str):
        super().__init__()
        import warnings
        warnings.filterwarnings("ignore", category=FutureWarning, module=r"google")
        warnings.filterwarnings("ignore", message=r".*non-text parts.*")
        warnings.filterwarnings("ignore", message=r".*thought_signature.*")
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self.model_name = model
        self.model = model  # for base class access

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.3) -> str:
        import warnings
        warnings.filterwarnings("ignore", message=r".*non-text parts.*")
        from google.genai import types

        # Convert messages to prompt text
        parts = []
        for m in messages:
            parts.append(m["content"])
        prompt_text = "\n\n".join(parts)

        try:
            resp = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt_text,
                config=types.GenerateContentConfig(temperature=temperature),
            )
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                # Extract retry delay if available
                import re
                retry_match = re.search(r"retry in (\d+)", err_str, re.IGNORECASE)
                wait_str = f" (retry in {retry_match.group(1)}s)" if retry_match else ""
                from .exceptions import DeepWormError
                raise DeepWormError(
                    f"Rate limit exceeded for {self.model_name}{wait_str}",
                    hint="Free tier: 20 requests/day per model. Wait or switch model with /set model <name>",
                ) from e
            raise

        result_text = resp.text or ""

        # Track token usage
        if resp.usage_metadata:
            um = resp.usage_metadata
            self._record_usage(
                prompt_tokens=getattr(um, 'prompt_token_count', 0) or 0,
                completion_tokens=getattr(um, 'candidates_token_count', 0) or 0,
                model=self.model_name,
            )
        else:
            self._record_usage(
                prompt_tokens=_estimate_tokens(prompt_text),
                completion_tokens=_estimate_tokens(result_text),
                model=self.model_name,
            )
        return result_text
