import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .audio_plan import create_audio_plan
from .coordinator import Coordinator
from .llm_service import LLMService
from .speech_service import SpeechService


log_file = Path(os.getenv("LOG_FILE", str(Path.home() / ".outdoor-speech-mcp.log"))).expanduser()
log_file.parent.mkdir(parents=True, exist_ok=True)
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=0,
    backupCount=10,
    encoding="utf-8",
)
if log_file.exists() and log_file.stat().st_size > 0:
    file_handler.doRollover()
logging.basicConfig(
    handlers=[file_handler],
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger(__name__)
mcp = FastMCP("outdoor-speech")
speech = SpeechService()
llm = LLMService()


@mcp.tool()
def run_speech_coordinator(message: str) -> str:
    """Speak a prompt, collect microphone input until the user says submit, and return the transcript."""
    logger.info("Tool request run_speech_coordinator: %r", {"message": message})
    try:
        if not message.strip():
            raise ValueError("message must be a non-empty string")
        response = Coordinator(speech).run(message)
        logger.info("Tool response run_speech_coordinator: %r", response)
        return response
    except Exception:
        logger.exception("Tool run_speech_coordinator failed")
        raise


@mcp.tool()
def synthesize_audio_plan(filename: str, output_dir: str | None = None) -> dict:
    """Convert a source file or directory into an iOS-compatible audio plan."""
    logger.info(
        "Tool request synthesize_audio_plan: %r",
        {"filename": filename, "output_dir": output_dir},
    )
    try:
        source = Path(filename).expanduser()
        if not source.exists():
            raise FileNotFoundError(f"file or directory not found: {filename}")
        response = create_audio_plan(str(source), speech, llm, output_dir)
        logger.info("Tool response synthesize_audio_plan: %r", response)
        return response
    except Exception:
        logger.exception("Tool synthesize_audio_plan failed")
        raise


@mcp.tool()
def transcribe_annotation(audio_path: str) -> dict:
    """Transcribe an audio annotation and create its adjacent replay WAV file."""
    logger.info("Tool request transcribe_annotation: %r", {"audio_path": audio_path})
    try:
        text_path, wav_path = speech.process_annotation_file(audio_path)
        response = {
            "text_file": str(text_path),
            "audio_file": str(wav_path),
            "text": text_path.read_text(encoding="utf-8"),
        }
        logger.info("Tool response transcribe_annotation: %r", response)
        return response
    except Exception:
        logger.exception("Tool transcribe_annotation failed")
        raise


@mcp.tool()
def ask_llm(prompt: str, model: str | None = None) -> str:
    """Ask an OpenAI model a text prompt; set OPENAI_API_KEY in the server environment."""
    logger.info("Tool request ask_llm: %r", {"prompt": prompt, "model": model})
    try:
        response = llm.ask(prompt, model)
        logger.info("Tool response ask_llm: %r", response)
        return response
    except Exception:
        logger.exception("Tool ask_llm failed")
        raise


def main():
    stop_event = None
    if os.getenv("ACTIVE_AUDIO_PLAN"):
        _, stop_event = speech.start_audio_plan_task()
    try:
        mcp.run(transport="stdio")
    finally:
        if stop_event:
            stop_event.set()