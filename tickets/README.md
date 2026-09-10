# Local Ticket System

Tickets are Markdown files stored in this directory. The filename is the stable ticket identifier followed by a short title, for example `OC-001-outdoor-coding-agent.md`.

## Ticket Format

Each ticket starts with YAML frontmatter:

```yaml
---
id: OC-001
title: Short imperative title
state: ready
type: feature
created: 2026-09-08
updated: 2026-09-08
priority: normal
dependencies: []
related: []
affected_area:
  - path/to/file
---
```

The body must contain these sections:

- Objective: the outcome the ticket must create.
- Acceptance criteria: observable conditions for completion.
- Validation approach: focused checks to run and record.
- Change record: files changed, behavior, and decisions made during implementation.
- Review documentation: detailed narration for tickets in `review`, including problem, approach, code changes, control-flow or data effects, validation results, compatibility concerns, and reviewer checks.
- History: append-only state changes with date, state, and evidence.
- Blockers and questions: unresolved issues, or `None`.

## States

Use these states exactly:

- `new`: captured but not yet refined.
- `ready`: objective, acceptance criteria, affected area, and validation approach are concrete.
- `in_progress`: actively being implemented.
- `review`: implementation and validation are complete; awaiting user review.
- `blocked`: work cannot proceed; record the blocker and next action.
- `closed`: accepted and excluded from future audio plans.

Only `ready` tickets may enter implementation. An implementation moves to `in_progress` before code changes, then to `review` after validation. Keep a ticket in `review` until the user or the repository workflow closes it. State changes append an entry to `History`; do not erase prior entries.

## Plan Inclusion

The audio plan includes every ticket except tickets with `state: closed`. Review tickets receive detailed review documentation. Other tickets receive a concise spoken summary of their objective, state, dependencies, blockers, and next action.
