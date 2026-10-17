# Outdoor Speech MCP

`outdoor-speech-mcp` is a local MCP server for Azure Speech recognition and
synthesis. It uses MCP stdio transport, so an MCP client launches it as a
local process rather than connecting to an HTTP server.

## Requirements

- Python 3.10+
- Azure Cognitive Services Speech credentials
- An OpenAI API key to use `ask_llm` and synthesize audio plans
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
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
LOG_FILE=/path/to/outdoor-speech-mcp.log
ACTIVE_AUDIO_PLAN=/path/to/audio-plan
AUDIO_PLAN_INTERVAL_SECONDS=10
```

Server logs are written to `~/.outdoor-speech-mcp.log` by default, with a
date/time stamp on each entry. The previous log is rotated at startup, keeping
the ten most recent backups. Set `LOG_FILE` to choose a different path and
`LOG_LEVEL` to adjust the verbosity.

## Configure an MCP client

Use the installed console script as the local MCP command:

```json
{
  "mcpServers": {
    "outdoor-speech": {
      "command": "/absolute/path/to/.venv/bin/outdoor-speech-mcp",
      "env": {
        "AZURE_SPEECH_KEY": "your_speech_key_here",
        "AZURE_SPEECH_REGION": "your_region_here",
        "OPENAI_API_KEY": "your_openai_api_key_here",
        "OPENAI_MODEL": "gpt-4o-mini"
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
- `synthesize_audio_plan(filename, output_dir)` supports `.md` and `.py` files.
  Markdown uses the packaged markdown-to-TTS skill; Python source uses the
  python-to-TTS skill to explain code behavior in listenable prose. An OpenAI
  model transforms the source before the iOS-compatible plan is generated.
- `transcribe_annotation(audio_path)` creates the adjacent `.stt.txt` and
  `.stt.wav` files for an annotation recording.
- `ask_llm(prompt, model)` sends a text prompt to OpenAI and returns the model's
  text response. It uses `OPENAI_MODEL` when `model` is omitted (default
  `gpt-4o-mini`) and requires `OPENAI_API_KEY` in the MCP server environment.

The speech implementation and its local dependencies live in
`outdoor-speech-mcp/src/outdoor_speech_mcp`. Repository plan synchronization
utilities remain at the project root.

## Outdoor Ticket System MCP

`outdoor-ticket-system-mcp` manages repository-local tickets in `tickets/` and
also provides a Markdown prompt queue for the Copilot agents in `.github/agents`.
Install it into the workspace virtual environment:

```bash
cd outdoor-ticket-system-mcp
../.venv/bin/python -m pip install -e .
```

VS Code discovers both MCP servers through `.vscode/mcp.json`. Ticket records
remain under `tickets/`; set `OUTDOOR_TICKET_ROOT` to override that location.
The service requires the schema in `tickets/README.md` and never creates a
parallel ticket store. Ticket mutations preserve append-only history and use
the documented state graph. Transitions to `refined`, `ready`, or `closed`
require `decision_evidence`; every transition requires `evidence`. MCP records
caller-supplied evidence but cannot authenticate who supplied it.

The ticket tools are `list_tickets`, `get_ticket`, `validate_tickets`,
`create_ticket`, `update_ticket`, `transition_ticket`, and
`prepare_ticket_plan`. The latter writes Markdown to a temporary source file
and returns its path and included ticket IDs. Pass that file to
`outdoor-speech-mcp.synthesize_audio_plan` to create the audio-plan artifacts.
The speech MCP requires `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, and
`OPENAI_API_KEY` in the environment; `.vscode/mcp.json` references those
environment variables rather than storing credentials.

The separate prompt-queue tools remain `claim_next_prompt`, `complete_prompt`,
and `requeue_prompt`. Add one `.md` file per coding prompt to `ticket-queue/`;
the server claims prompts by oldest modification time, with filename as the
tie-breaker. Claimed prompts move into `ticket-queue/.processing/` and are
completed into `.completed/` or returned with `requeue_prompt`.
