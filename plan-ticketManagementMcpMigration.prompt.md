## Plan: Move Ticket Workflow Into MCP

Move deterministic ticket-management behavior into `outdoor-ticket-system-mcp`. Keep a short skill for conversational guidance, and use `outdoor-speech-mcp` for audio synthesis.

**Steps**
1. Add a ticket repository service that reads the configured ticket root, defaulting to the workspace’s `tickets/`. Require the canonical `tickets/README.md`; validate frontmatter, required sections, states, directory and filename consistency, and readiness criteria. Use a YAML parser and keep ticket paths confined to the configured root.
2. Add MCP tools to list and retrieve tickets, validate one or all tickets, create tickets, update ticket content, and transition states. Preserve existing prompt-queue tools. Mutations should update `updated`, append dated history entries, and reject transitions without required evidence. Require decision evidence for `refined`, `ready`, and `closed`, and validation evidence before `review`.
3. Add a tool that prepares Markdown from every non-closed ticket. Use concise structured summaries for non-review tickets and the ticket’s Review Documentation for review tickets. Return the source path and included IDs; the agent then passes that source to the existing `synthesize_audio_plan` tool.
4. Register `outdoor-speech-mcp` in [`.vscode/mcp.json`](.vscode/mcp.json), sourcing Azure and OpenAI credentials from the environment. Update [README.md](README.md) with the ticket root setting, tools, transition evidence, and synthesis workflow. Reduce [SKILL.md](skills/ticket-management/SKILL.md) to tool-routing and conversational guidance.
5. Add focused ticket-service tests while preserving the existing prompt-queue tests. Test real ticket validation, transition guards and history, path containment, and plan-source inclusion. Manually pass a generated source path to the speech MCP and verify its output when credentials are available.

**Relevant files**
- [server.py](outdoor-ticket-system-mcp/src/outdoor_ticket_system_mcp/server.py) — register ticket tools alongside current queue tools.
- [queue_store.py](outdoor-ticket-system-mcp/src/outdoor_ticket_system_mcp/queue_store.py) — preserve existing queue behavior and use its environment-root convention.
- `outdoor-ticket-system-mcp/src/outdoor_ticket_system_mcp/ticket_store.py` — new ticket persistence, validation, transitions, and plan-source assembly.
- [pyproject.toml](outdoor-ticket-system-mcp/pyproject.toml) — declare the YAML parsing dependency.
- `outdoor-ticket-system-mcp/tests/test_ticket_store.py` — new focused tests.
- [tickets/README.md](tickets/README.md) — keep the documented schema aligned with what code enforces.

**Decisions**
- Prompt queue files and durable ticket records remain separate; existing queue endpoints stay intact.
- Ticket MCP prepares plan source; it does not duplicate speech synthesis or directly launch another MCP server.
- Decision evidence is recorded, but MCP cannot verify that it came from a human.
- This workspace currently registers only the ticket MCP. Audio synthesis requires configuring the speech MCP and its Azure/OpenAI credentials.
