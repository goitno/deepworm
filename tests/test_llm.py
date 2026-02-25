"""Tests for deepworm.llm."""

import json

from deepworm.llm import LLMClient


class MockLLMClient(LLMClient):
    """Mock client for testing."""

    def __init__(self, response: str):
        self._response = response

    def chat(self, messages, temperature=0.3):
        return self._response


def test_chat_json_plain():
    client = MockLLMClient('["query 1", "query 2"]')
    result = client.chat_json([{"role": "user", "content": "test"}])
    assert result == ["query 1", "query 2"]


def test_chat_json_with_markdown():
    client = MockLLMClient('```json\n["a", "b"]\n```')
    result = client.chat_json([{"role": "user", "content": "test"}])
    assert result == ["a", "b"]


def test_chat_json_object():
    client = MockLLMClient('{"key": "value"}')
    result = client.chat_json([{"role": "user", "content": "test"}])
    assert result == {"key": "value"}
