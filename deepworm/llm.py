"""LLM provider abstraction layer.

Supports OpenAI, Anthropic, Google, and Ollama (local).
Uses the OpenAI client for OpenAI and Ollama (compatible API).
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from .config import Config


def get_client(config: Config) -> "LLMClient":
    """Create an LLM client based on config."""
    provider = config.provider

    if provider == "ollama":
        return OpenAICompatibleClient(
            api_key="ollama",
            base_url=config.ollama_base_url,
            model=config.model,
        )
    elif provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        return OpenAICompatibleClient(
            api_key=api_key,
            base_url="https://api.openai.com/v1",
            model=config.model,
        )
    elif provider == "anthropic":
        return AnthropicClient(
            api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            model=config.model,
        )
    elif provider == "google":
        return GoogleClient(
            api_key=os.environ.get("GOOGLE_API_KEY", ""),
            model=config.model,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


class LLMClient:
    """Base class for LLM clients."""

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.3) -> str:
        raise NotImplementedError

    def chat_json(self, messages: list[dict[str, str]], temperature: float = 0.1) -> Any:
        """Chat and parse the response as JSON."""
        response = self.chat(messages, temperature=temperature)
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
