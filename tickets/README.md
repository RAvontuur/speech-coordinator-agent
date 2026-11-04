# Local Ticket System

Tickets are Markdown files stored in its ticket directory. The name of the ticket directory is the same as the file (without extension). The directory should be used to store artifacts related to the ticket. When a ticket is closed, the user may choose to archive the ticket and its artifacts together. This keeps the system clean without deleting the ticket itself.

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
# Optional implementation routing, populated during refinement:
repository: registered-repository-name
working_branch: oc-001-short-description
target_branch: main
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
- `refined`: a user has reviewed and clarified the ticket, but it is intentionally delayed and is not yet ready for implementation.
- `ready`: objective, acceptance criteria, affected area, and validation approach are concrete.
- `in_progress`: actively being implemented.
- `review`: implementation and validation are complete; awaiting user review.
- `test`: the reviewed working branch has been merged into its target and is awaiting user-controlled testing.
- `blocked`: work cannot proceed; record the blocker and next action.
- `closed`: accepted and excluded from future audio plans.

Only tickets in `ready` state are ready for implementation. A user may request a valid state change by annotation or review feedback, and the agent should honor explicit instructions when they match the repository's allowed state graph. The agent does not invent state changes from vague notes; it uses `transition_ticket` with evidence and the required `decision_evidence` for `refined`, `ready`, or `closed`. An implementation moves to `in_progress` before code changes, then to `review` after validation. Keep a ticket in `review` until the user requests closure/testing. On an explicit request to close a reviewed implementation, transition it to `test`; the ticket service first merges its working branch into its target and records the merge in History. A merge error leaves the ticket in `review`. Never move a ticket into `test` without explicit user intent. Close it only after the user accepts testing. State changes and repository/branch operations append entries to `History`; do not erase prior entries.

Ticket routing fields are optional until refinement: `repository` names a registered repository, and `working_branch` and `target_branch` identify its branches. The refinement worker records the selection using `select_ticket_repository`; if no ticket target branch is specified, the repository's `default_target_branch` is resolved and saved on the ticket. Repository registrations continue to require `name`, `get_url`, and `local_directory`; `default_target_branch` is optional at registration but must be supplied by either the registration or the ticket before implementation can start. The dispatcher calls `create_working_branch` after moving a selected ticket to `in_progress` and immediately before sending it to the coder.

The `outdoor-ticket-system-mcp` validates this schema before ticket operations. It requires dated history entries with a state and evidence, protects `History` from ordinary updates, and records transition evidence. Any non-closed ticket may move to `blocked`; the transition evidence is copied into `Blockers and Questions`. A blocked ticket may return to `ready` or `in_progress` once its blocker is resolved. Readiness validation checks that the objective, acceptance criteria, validation approach, and affected area are present and not obvious placeholders; it cannot judge whether their meaning is sufficiently precise. The MCP requires caller-supplied decision evidence for `refined`, `ready`, and `closed`, but does not authenticate the caller's identity.

After successful coding and before moving a ticket to `review`, the dispatcher calls `finish_working_branch`. This operation commits pending tracked, staged, and untracked non-ignored changes on the ticket's recorded working branch, then checks out the recorded target branch without merging. It requires the recorded working branch to be checked out; it never commits changes on another branch. If cleanup fails, the ticket must not advance to `review`.

Examples of valid state values include `state: refined`, `state: ready`, `state: review`, `state: test`, and `state: closed`.

## Plan Inclusion

The audio plan includes every ticket except tickets with `state: closed`. Review tickets receive detailed review documentation. Other tickets receive a concise spoken summary of their objective, state, dependencies, blockers, and next action.
