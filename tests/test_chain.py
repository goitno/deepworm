"""Tests for deepworm.chain."""

from deepworm.chain import CHAIN_PROMPT, _generate_next_topic


class FakeLLM:
    """Mock LLM for chain tests."""

    def __init__(self, response="{}"):
        self._response = response

    def chat(self, messages, temperature=0.3):
        return self._response

    def chat_json(self, messages, temperature=0.3):
        import json
        text = self._response
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)


def test_chain_prompt_format():
    """CHAIN_PROMPT can be formatted with required keys."""
    formatted = CHAIN_PROMPT.format(topic="AI", excerpt="Some findings")
    assert "AI" in formatted
    assert "Some findings" in formatted


def test_generate_next_topic_valid():
    """_generate_next_topic returns topic from valid JSON."""
    import json
    llm = FakeLLM(json.dumps({"topic": "Next question?", "reason": "Important"}))
    result = _generate_next_topic(llm, "AI", "# Report\n\nFindings about AI.")
    assert result == "Next question?"


def test_generate_next_topic_invalid_json():
    """Returns None on invalid JSON."""
    llm = FakeLLM("not json")
    result = _generate_next_topic(llm, "AI", "report")
    assert result is None


def test_generate_next_topic_missing_key():
    """Returns None when JSON lacks 'topic' key."""
    import json
    llm = FakeLLM(json.dumps({"reason": "something"}))
    result = _generate_next_topic(llm, "AI", "report")
    assert result is None
