# Outdoor Speech MCP

`outdoor-speech-mcp` is a local MCP server for Azure Speech recognition and
synthesis. It uses MCP stdio transport, so an MCP client launches it as a
local process rather than connecting to an HTTP server.

## Requirements

- Python 3.10+
- Azure Cognitive Services Speech credentials
- `ffmpeg` on `PATH` for M4A transcription

## Install

```bash
cd outdoor-speech-mcp
python -m pip install -e .
```

Create a `.env` file in the repository root or export these variables:

```env
AZURE_SPEECH_KEY=your_speech_key_here
AZURE_SPEECH_REGION=your_region_here
ACTIVE_AUDIO_PLAN=/path/to/audio-plan
AUDIO_PLAN_INTERVAL_SECONDS=10
```

## Configure an MCP client

Use the installed console script as the local MCP command:

```json
{
  "mcpServers": {
    "outdoor-speech": {
      "command": "/absolute/path/to/.venv/bin/outdoor-speech-mcp",
      "env": {
        "AZURE_SPEECH_KEY": "your_speech_key_here",
        "AZURE_SPEECH_REGION": "your_region_here"
      }
    }
  }
}
```

The repository wrapper also starts the same server:

```bash
.venv/bin/python run.py
```

## MCP tools

- `run_speech_coordinator(message)` speaks a prompt, listens until the user
  says `submit`, and returns the collected transcript.
- `synthesize_audio_plan(filename, output_dir)` converts Markdown into the
  iOS-compatible plan package used by AudioAnnotation.
- `transcribe_annotation(audio_path)` creates the adjacent `.stt.txt` and
  `.stt.wav` files for an annotation recording.

The speech implementation and its local dependencies live in
`outdoor-speech-mcp/src/outdoor_speech_mcp`. Repository plan synchronization
utilities remain at the project root.
