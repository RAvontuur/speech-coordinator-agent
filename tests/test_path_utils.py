from pathlib import Path

from outdoor_speech_mcp.path_utils import normalize_path


def test_normalize_path_replaces_escaped_spaces():
    raw = "/Users/ravontuur/Library/Mobile\\ Documents/com~apple~CloudDocs/audio/outdoor-coding-audio-plan"

    normalized = normalize_path(raw)

    assert str(normalized) == "/Users/ravontuur/Library/Mobile Documents/com~apple~CloudDocs/audio/outdoor-coding-audio-plan"


def test_normalize_path_keeps_existing_real_path():
    raw = "/Users/ravontuur/Library/Mobile Documents/com~apple~CloudDocs/audio/example-audio-plan"

    normalized = normalize_path(raw)

    assert str(normalized) == raw
