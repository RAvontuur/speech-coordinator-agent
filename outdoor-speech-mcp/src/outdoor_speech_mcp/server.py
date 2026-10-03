import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .audio_plan import create_audio_plan
from .coordinator import Coordinator
from .llm_service import LLMService
from .speech_service import SpeechService


log_file = Path(os.getenv("LOG_FILE", str(Path.home() / ".outdoor-speech-mcp.log"))).expanduser()
log_file.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(log_file),
    level=os.getenv("LOG_LEVEL", "INFO"),
)
logger = logging.getLogger(__name__)
mcp = FastMCP("outdoor-speech")
speech = SpeechService()
llm = LLMService()


@mcp.tool()
def run_speech_coordinator(message: str) -> str:
    """Speak a prompt, collect microphone input until the user says submit, and return the transcript."""
    logger.info("Tool request run_speech_coordinator: %r", {"message": message})
    if not message.strip():
        raise ValueError("message must be a non-empty string")
    response = Coordinator(speech).run(message)
    logger.info("Tool response run_speech_coordinator: %r", response)
    return response


@mcp.tool()
def synthesize_audio_plan(filename: str, output_dir: str | None = None) -> dict:
    """Convert a Markdown or Python source file into an iOS-compatible audio plan."""
    logger.info(
        "Tool request synthesize_audio_plan: %r",
        {"filename": filename, "output_dir": output_dir},
    )
    source = Path(filename).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"file not found: {filename}")
    response = create_audio_plan(str(source), speech, llm, output_dir)
    logger.info("Tool response synthesize_audio_plan: %r", response)
    return response


@mcp.tool()
def transcribe_annotation(audio_path: str) -> dict:
    """Transcribe an audio annotation and create its adjacent replay WAV file."""
    logger.info("Tool request transcribe_annotation: %r", {"audio_path": audio_path})
    text_path, wav_path = speech.process_annotation_file(audio_path)
    response = {
        "text_file": str(text_path),
        "audio_file": str(wav_path),
        "text": text_path.read_text(encoding="utf-8"),
    }
    logger.info("Tool response transcribe_annotation: %r", response)
    return response


@mcp.tool()
def ask_llm(prompt: str, model: str | None = None) -> str:
    """Ask an OpenAI model a text prompt; set OPENAI_API_KEY in the server environment."""
    logger.info("Tool request ask_llm: %r", {"prompt": prompt, "model": model})
    response = llm.ask(prompt, model)
    logger.info("Tool response ask_llm: %r", response)
    return response


def main():
    stop_event = None
    if os.getenv("ACTIVE_AUDIO_PLAN"):
        _, stop_event = speech.start_audio_plan_task()
    try:
        mcp.run(transport="stdio")
    finally:
        if stop_event:
            stop_event.set()