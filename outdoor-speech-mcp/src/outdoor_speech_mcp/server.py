import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .audio_plan import create_audio_plan
from .coordinator import Coordinator
from .speech_service import SpeechService


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
mcp = FastMCP("outdoor-speech")
speech = SpeechService()


@mcp.tool()
def run_speech_coordinator(message: str) -> str:
    """Speak a prompt, collect microphone input until the user says submit, and return the transcript."""
    if not message.strip():
        raise ValueError("message must be a non-empty string")
    return Coordinator(speech).run(message)


@mcp.tool()
def synthesize_audio_plan(filename: str, output_dir: str | None = None) -> dict:
    """Convert a Markdown file into an iOS-compatible audio plan package."""
    source = Path(filename).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"file not found: {filename}")
    return create_audio_plan(str(source), speech, output_dir)


@mcp.tool()
def transcribe_annotation(audio_path: str) -> dict:
    """Transcribe an audio annotation and create its adjacent replay WAV file."""
    text_path, wav_path = speech.process_annotation_file(audio_path)
    return {"text_file": str(text_path), "audio_file": str(wav_path), "text": text_path.read_text(encoding="utf-8")}


def main():
    stop_event = None
    if os.getenv("ACTIVE_AUDIO_PLAN"):
        _, stop_event = speech.start_audio_plan_task()
    try:
        mcp.run(transport="stdio")
    finally:
        if stop_event:
            stop_event.set()