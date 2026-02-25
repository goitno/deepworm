"""Tests for deepworm.llm."""

import json

from deepworm.llm import LLMClient


class MockLLMClient(LLMClient):
    """Mock client for testing."""

    def __init__(self, response: str):
        self._response = response

    def chat(self, messages, temperature=0.3):
        return self._response


class FailThenSucceedClient(LLMClient):
    """Mock client that fails N times then succeeds."""

    def __init__(self, fail_times: int, response: str):
        self._fail_times = fail_times
        self._response = response
        self._attempts = 0

    def chat(self, messages, temperature=0.3):
        self._attempts += 1
        if self._attempts <= self._fail_times:
            raise ConnectionError("mock connection error")
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


def test_retry_succeeds_after_failures():
    client = FailThenSucceedClient(fail_times=2, response="success")
    result = client.chat_with_retry(
        [{"role": "user", "content": "test"}],
        max_retries=3,
    )
    assert result == "success"
    assert client._attempts == 3


def test_retry_immediate_success():
    client = FailThenSucceedClient(fail_times=0, response="ok")
    result = client.chat_with_retry(
        [{"role": "user", "content": "test"}],
        max_retries=3,
    )
    assert result == "ok"
    assert client._attempts == 1
