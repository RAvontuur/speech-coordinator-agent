from outdoor_speech_mcp import speech_service
from outdoor_speech_mcp.speech_service import SpeechService


def test_speech_config_uses_region_when_endpoint_is_unset(monkeypatch):
    calls = {}

    def fake_speech_config(**kwargs):
        calls.update(kwargs)
        return object()

    monkeypatch.setattr(speech_service.speechsdk, "SpeechConfig", fake_speech_config)
    monkeypatch.setenv("AZURE_SPEECH_KEY", "test-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "westus")
    monkeypatch.delenv("AZURE_SPEECH_ENDPOINT", raising=False)

    SpeechService()

    assert calls == {"subscription": "test-key", "region": "westus"}


def test_speech_config_uses_endpoint_when_configured(monkeypatch):
    calls = {}

    def fake_speech_config(**kwargs):
        calls.update(kwargs)
        return object()

    monkeypatch.setattr(speech_service.speechsdk, "SpeechConfig", fake_speech_config)
    monkeypatch.setenv("AZURE_SPEECH_KEY", "test-key")
    monkeypatch.setenv(
        "AZURE_SPEECH_ENDPOINT",
        "https://custom-name.cognitiveservices.azure.com/",
    )
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)

    SpeechService()

    assert calls == {
        "subscription": "test-key",
        "endpoint": "https://custom-name.cognitiveservices.azure.com/",
    }
