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
- `latest_plan_name()` and `next_plan_name()` find existing and next local
  `Sprint Review N` names. `create_next_plan_dir()` creates the next local plan
  directory.
- `import_plan(plan_name)` copies `ACTIVE_AUDIO_PLAN` into `plans/`;
  `export_plan(plan_name)` deploys a local plan package to `ACTIVE_AUDIO_PLAN`.
  These tools replace the removed repository-root `plan_sync.py` script.
- `transcribe_annotation(audio_path)` creates the adjacent `.stt.txt` and
  `.stt.wav` files for an annotation recording.
- `ask_llm(prompt, model)` sends a text prompt to OpenAI and returns the model's
  text response. It uses `OPENAI_MODEL` when `model` is omitted (default
  `gpt-4o-mini`) and requires `OPENAI_API_KEY` in the MCP server environment.

The speech implementation and its local dependencies live in
`outdoor-speech-mcp/src/outdoor_speech_mcp`, including the local Sprint Review
plan synchronization helpers.

## Outdoor Ticket System MCP

`outdoor-ticket-system-mcp` manages repository-local tickets in `tickets/`.
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
`create_ticket`, `update_ticket`, and `transition_ticket`. Use
`list_tickets(state="ready", output_mode="full")` to select implementation
work. Its `file-format="markdown"` mode returns the Sprint Review Plan from
all non-closed tickets by default. Save it as `plan.md` in a new local Sprint
Review directory, then use `synthesize_audio_plan` and `export_plan` from
`outdoor-speech-mcp` to generate and deploy the audio package.

The speech MCP owns plan synchronization through `next_plan_name`,
`create_next_plan_dir`, `import_plan`, and `export_plan`. These tools replace
the former `plan_sync.py` command-line helpers. Import/export use
`ACTIVE_AUDIO_PLAN` and local `plans/` directories. The speech MCP requires
`AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, and `OPENAI_API_KEY`;
`.vscode/mcp.json` references environment variables rather than storing
credentials.
