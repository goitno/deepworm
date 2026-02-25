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

from .config import Config
from .exceptions import APIKeyError, ModelNotFoundError, ProviderError, RateLimitError

logger = logging.getLogger("deepworm")

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


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
    else:
        raise ProviderError(
            f"Unknown provider: {provider}",
            hint="Supported providers: openai, anthropic, google, ollama",
        )


class LLMClient:
    """Base class for LLM clients."""

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
    """Client for OpenAI and Ollama (OpenAI-compatible API)."""

    def __init__(self, api_key: str, base_url: str, model: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.3) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
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
    """Client for Google Gemini."""

    def __init__(self, api_key: str, model: str):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.genai = genai
        self.model_name = model

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.3) -> str:
        model = self.genai.GenerativeModel(self.model_name)

        # Convert messages to Gemini format
        parts = []
        for m in messages:
            parts.append(m["content"])

        resp = model.generate_content(
            "\n\n".join(parts),
            generation_config={"temperature": temperature},
        )
        return resp.text
