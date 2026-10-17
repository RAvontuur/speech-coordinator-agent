# Manual Testing

## Ticket System MCP

`mcp-ticket-system-test.py` starts the workspace's
`outdoor-ticket-system-mcp`, initializes an MCP stdio session, and either lists
registered tools or calls one tool with JSON arguments. Run commands from the
repository root:

```bash
./.venv/bin/python manual-testing/mcp-ticket-system-test.py --list-tools
./.venv/bin/python manual-testing/mcp-ticket-system-test.py --tool list_tickets
./.venv/bin/python manual-testing/mcp-ticket-system-test.py \
  --tool list_tickets --arguments '{"state":"ready","output_mode":"ids"}'
./.venv/bin/python manual-testing/mcp-ticket-system-test.py \
  --tool list_tickets --arguments '{"output_mode":"full"}'
./.venv/bin/python manual-testing/mcp-ticket-system-test.py \
  --tool get_ticket --arguments '{"ticket_id":"OC-005"}'
./.venv/bin/python manual-testing/mcp-ticket-system-test.py \
  --tool validate_tickets --arguments '{"ticket_id":"OC-005"}'
./.venv/bin/python manual-testing/mcp-ticket-system-test.py --tool prepare_ticket_plan
```

Use `--arguments` for any tool's JSON object. For example, `create_ticket`
accepts fields such as `title`, `ticket_type`, `objective`,
`acceptance_criteria` (an array of strings), `validation_approach`,
`affected_area` (an array of paths), and `creation_evidence`:

```bash
./.venv/bin/python manual-testing/mcp-ticket-system-test.py \
  --tool create_ticket \
  --arguments '{"title":"Try a sample ticket","ticket_type":"feature","objective":"Exercise ticket creation.","acceptance_criteria":["The sample can be validated."],"validation_approach":"Call validate_tickets.","affected_area":["manual-testing/"],"creation_evidence":"Created for manual MCP testing."}'
```

Ticket mutations write to the configured `OUTDOOR_TICKET_ROOT`, which defaults
to the repository's `tickets/` directory. Use an isolated ticket root for
`create_ticket`, `update_ticket`, and `transition_ticket` so manual checks do
not alter real tickets. The isolated root must contain a `README.md` with
`## Ticket Format` and `## States` headings. Transition calls require
`evidence`; transitions to `refined`, `ready`, or `closed` also require
`decision_evidence`. Pass `--ticket-root /path/to/test-tickets` to override the
root for that invocation. For example, initialize a temporary root and inspect
it without changing repository tickets:

```bash
mkdir -p /tmp/ticket-mcp-test
printf '# Local Ticket System\n\n## Ticket Format\n\n## States\n' \
  > /tmp/ticket-mcp-test/README.md
./.venv/bin/python manual-testing/mcp-ticket-system-test.py \
  --ticket-root /tmp/ticket-mcp-test --tool list_tickets
```

## Synthesize an Audio Plan

`mcp-synthesize-audio-plan-test.py` starts the workspace's
`outdoor-speech-mcp` executable, initializes an MCP stdio session, and calls
`synthesize_audio_plan` with the source and output directory supplied on the
command line. Run it from the repository root so relative source and output
paths resolve as expected:

```bash
./.venv/bin/python manual-testing/mcp-synthesize-audio-plan-test.py \
  --filename mcp-synthesize-audio-plan-test.py \
  --output-dir test/plan2
```

Both options are required:

- `--filename`: a source file or directory supported by the speech MCP.
- `--output-dir`: the directory where `plan.tts.txt`, `plan.wav`, timing data,
  annotations data, and audio segments are generated.

For an absolute source path, quote the value if it contains spaces:

```bash
./.venv/bin/python manual-testing/mcp-synthesize-audio-plan-test.py \
  --filename "/path/to/my source.md" \
  --output-dir test/custom-plan
```

The script locates `.venv/bin/outdoor-speech-mcp` relative to the repository.
The virtual environment and the speech MCP's Azure Speech and OpenAI
credentials must be configured before running it. Audio synthesis writes files
to the requested output directory and may incur provider usage charges.