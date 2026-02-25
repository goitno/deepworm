"""Tests for deepworm.llm."""

import json

from deepworm.llm import LLMClient, TokenTracker, TokenUsage, _estimate_tokens


class MockLLMClient(LLMClient):
    """Mock client for testing."""

    def __init__(self, response: str):
        super().__init__()
        self._response = response

    def chat(self, messages, temperature=0.3):
        return self._response


class FailThenSucceedClient(LLMClient):
    """Mock client that fails N times then succeeds."""

    def __init__(self, fail_times: int, response: str):
        super().__init__()
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


# --- Token tracking tests ---

def test_token_usage_dataclass():
    usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150, model="test")
    assert usage.prompt_tokens == 100
    assert usage.completion_tokens == 50
    assert usage.total_tokens == 150


def test_token_tracker_record():
    tracker = TokenTracker()
    assert tracker.call_count == 0
    assert tracker.total_tokens == 0

    tracker.record(TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150, model="m1"))
    assert tracker.call_count == 1
    assert tracker.total_tokens == 150
    assert tracker.total_prompt_tokens == 100
    assert tracker.total_completion_tokens == 50

    tracker.record(TokenUsage(prompt_tokens=200, completion_tokens=80, total_tokens=280, model="m1"))
    assert tracker.call_count == 2
    assert tracker.total_tokens == 430
    assert tracker.total_prompt_tokens == 300
    assert tracker.total_completion_tokens == 130


def test_token_tracker_summary():
    tracker = TokenTracker()
    tracker.record(TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500, model="test"))
    s = tracker.summary()
    assert "1,500 tokens" in s
    assert "1 calls" in s


def test_estimate_tokens():
    assert _estimate_tokens("hello world") >= 1
    assert _estimate_tokens("x" * 400) == 100  # ~4 chars per token
    assert _estimate_tokens("") == 1  # min 1


def test_client_has_token_tracker():
    client = MockLLMClient("test")
    assert hasattr(client, "token_tracker")
    assert isinstance(client.token_tracker, TokenTracker)
    assert client.token_tracker.call_count == 0


def test_record_usage_on_client():
    client = MockLLMClient("test")
    usage = client._record_usage(prompt_tokens=50, completion_tokens=25, model="test-model")
    assert usage.total_tokens == 75
    assert client.token_tracker.call_count == 1
    assert client.last_usage is not None
    assert client.last_usage.total_tokens == 75
