---
name: "ticket-management"
description: "Discover, validate, refine, and narrate repository-local tickets stored in per-ticket directories under tickets/."
argument-hint: "Describe a ticket, a state transition, or the ticket schema you need to review."
---

# Local Ticket Management Skill

Use `outdoor-ticket-system-mcp` for deterministic ticket discovery, validation,
creation, edits, state transitions, and Sprint Review Markdown generation. The MCP server
uses the schema in `tickets/README.md`; do not create a separate ticket store.

## Workflow

1. Call `validate_tickets` before ticket updates and use `get_ticket` to inspect
    the existing record before changing it.
2. Use `create_ticket` for new work, `update_ticket` for metadata or body
    sections, and `transition_ticket` for state changes. Preserve the user's
    intent and provide accurate evidence; decision evidence is required when
    moving to `refined`, `ready`, or `closed`.
3. Use `list_tickets` to review the current set. Only `ready` tickets are
    eligible for implementation. Do not treat test success alone as acceptance
    or close a ticket without explicit user decision evidence.
4. Call `list_tickets` with `file-format="markdown"` after ticket updates to
    generate the Sprint Review Plan from every non-closed ticket. Save that
    Markdown as `plan.md` in the next local Sprint Review directory, then use
    the `outdoor-speech-mcp` `synthesize_audio_plan` and `export_plan` tools to
    generate and deploy the audio plan. Review tickets use their Review
    Documentation; other open tickets use a concise structured summary.
