import pytest

from outdoor_speech_mcp import llm_service
from outdoor_speech_mcp.llm_service import LLMService


def test_ask_uses_configured_model_and_returns_response_text(monkeypatch):
    calls = {}

    class FakeResponses:
        def create(self, **kwargs):
            calls.update(kwargs)
            return type("Response", (), {"output_text": "Hello from the model."})()

    class FakeOpenAI:
        def __init__(self, api_key):
            calls["api_key"] = api_key
            self.responses = FakeResponses()

    monkeypatch.setattr(llm_service, "OpenAI", FakeOpenAI)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")

    answer = LLMService().ask("Say hello")

    assert answer == "Hello from the model."
    assert calls == {"api_key": "test-key", "model": "gpt-test", "input": "Say hello"}


def test_ask_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
        LLMService().ask("Say hello")


def test_ask_rejects_empty_prompt():
    with pytest.raises(ValueError, match="prompt must not be empty"):
        LLMService().ask("  ")


def test_transform_uses_packaged_skill_instructions(monkeypatch):
    calls = {}

    class FakeResponses:
        def create(self, **kwargs):
            calls.update(kwargs)
            return type("Response", (), {"output_text": "Listen to this sentence."})()

    class FakeOpenAI:
        def __init__(self, api_key):
            calls["api_key"] = api_key
            self.responses = FakeResponses()

    monkeypatch.setattr(llm_service, "OpenAI", FakeOpenAI)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")

    text = LLMService().transform_markdown_to_tts_text("# Heading\n\n- A list item")

    assert text == "Listen to this sentence.\n"
    assert calls["model"] == "gpt-test"
    assert calls["input"] == "# Heading\n\n- A list item"
    assert "Transform markdown documents" in calls["instructions"] or "listenable text" in calls["instructions"].lower()
    assert "Return only the transformed text" in calls["instructions"]