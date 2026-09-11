---
name: "Local Ticket Management"
description: "Discover, validate, refine, and narrate repository-local tickets stored in per-ticket directories under tickets/."
argument-hint: "Describe a ticket, a state transition, or the ticket schema you need to review."
---

# Local Ticket Management Skill

This skill manages the repository's Markdown ticket system. It is intentionally local-first: it reads the schema in `tickets/README.md`, presumes no hosted tracker exists, and refuses to invent a second ticket system when the repository does not contain a recognizable `tickets/` directory or schema. Each ticket lives in its own subdirectory under `tickets/`, with the directory name matching the markdown file name without the extension. Keep related artifacts in that directory; when a ticket is closed, the user may archive the ticket and its artifacts together to keep the working tree clean without deleting the ticket record.

## Purpose

Use this skill to:

- discover local tickets and understand the schema contract
- validate frontmatter, required sections, and state transitions
- move tickets through `new`, `ready`, `in_progress`, `review`, `blocked`, and `closed`
- create concise spoken summaries for non-review tickets
- create detailed review documentation for tickets in `review`
- keep history append-only and preserve evidence across state changes

## Required Source of Truth

Before changing or creating tickets, read:

1. `tickets/README.md` for the canonical schema and state rules.
2. The relevant existing ticket file for the same identifier if one exists.
3. The active audio plan only as an input to update or create tickets; do not treat the plan as a second source of truth.

If `tickets/README.md` is missing or the repository has no recognized ticket directory, stop and report the missing artifact instead of creating a parallel ticket store.

## Ticket Schema Contract

The canonical ticket schema lives in `tickets/README.md`. Use it directly and do not define a second format.

The required frontmatter keys are:

- `id`
- `title`
- `state`
- `type`
- `created`
- `updated`
- `priority`
- `dependencies`
- `related`
- `affected_area`

The required body sections are:

- Objective
- Acceptance Criteria
- Validation Approach
- Change Record
- Review Documentation
- History
- Blockers and Questions

The supported states are exactly:

- `new`
- `ready`
- `in_progress`
- `review`
- `blocked`
- `closed`

Only tickets in `ready` state may start implementation. A ticket moves to `in_progress` before code changes, then to `review` after validation. Keep a ticket in `review` until the user or the repository workflow closes it. Never overwrite older history entries.

## Discovery Workflow

1. Confirm the repository contains a `tickets/` directory and `tickets/README.md`.
2. Read the schema and state rules before making any ticket edits.
3. Enumerate each ticket directory under `tickets/`, find the markdown file within it, and identify each ticket's ID and state.
4. For each ticket, validate the frontmatter, required sections, and state rules.
5. Treat unrelated working-tree changes and generated assets as user-owned unless they are part of this ticket update.

## Validation Rules

A ticket is valid only when all of the following are true:

- the ticket is stored in its own subdirectory under the recognized tickets directory
- the directory name matches the markdown file name without the `.md` extension
- the ticket file is a Markdown file within that directory
- YAML frontmatter is present and parseable
- all required frontmatter keys exist
- the `state` value is one of the allowed states
- the content contains the required sections
- `History` is append-only and includes date, state, and evidence
- `Objective`, `Acceptance Criteria`, `Affected Area`, and `Validation Approach` are concrete before a ticket becomes `ready`
- non-closed tickets are eligible for plan inclusion while `closed` tickets are excluded
- closed tickets may be archived with their artifact directories when the user chooses to archive them, without deleting the ticket record itself

When validation fails, return an actionable error that names the file, the missing or invalid field, and the expected contract.

## Ticket Creation and Update Rules

When creating a ticket:

- use the stable ID format `OC-###` followed by a short slug
- include a meaningful imperative title
- set `state` to `new` until the objective, criteria, affected area, and validation approach are concrete
- add an initial `History` entry describing creation and evidence

When updating a ticket:

- append to `History` rather than rewriting earlier entries
- update `updated` to the current date
- keep identifiers stable
- preserve `related` links and dependency information when present
- do not invent missing state transitions or skip required documentation

## Transition Logic

- `new` -> `ready`: only when objective, acceptance criteria, affected area, and validation approach are concrete
- `ready` -> `in_progress`: begins implementation and records evidence
- `in_progress` -> `review`: after implementation and focused validation are complete
- `review` -> `closed`: only by explicit user acceptance or repository workflow, not by test success alone
- `review` -> `in_progress`: only for explicit rework or corrections
- `blocked` -> `ready` or `in_progress`: only after the blocker is resolved and documented

## Narration Rules

For non-review tickets:

- provide a concise spoken summary
- include objective, current state, dependencies, blockers, and next action
- keep the summary short enough to be listenable in an audio plan

For review tickets:

- provide detailed local review documentation
- cover problem, approach, code changes, control-flow or data effects, validation results, compatibility concerns, and reviewer checks
- include explicit evidence from the repository, ticket history, and relevant diffs or generated docs

## Audio Plan Inclusion Rules

- every non-closed ticket is eligible for the audio plan
- closed tickets are excluded
- non-review tickets get concise summaries
- review tickets get detailed review documentation
- do not generate a second ticket store when there is no recognized local schema

## Validation Command

The repository does not need a broad suite for this skill. Use a focused validation that checks the real local ticket files and the schema contract, for example:

```bash
cd /Users/ravontuur/speech-coordinator-agent && .venv/bin/python - <<'PY'
from pathlib import Path

tickets = Path('tickets')
readme = tickets / 'README.md'
assert readme.exists(), 'tickets/README.md is missing'
text = readme.read_text(encoding='utf-8')
assert 'state: ready' in text, 'ready state not documented'
assert 'state: review' in text, 'review state not documented'
assert 'state: closed' in text, 'closed state not documented'

ticket_dirs = sorted(p for p in tickets.iterdir() if p.is_dir())
assert ticket_dirs, 'no ticket directories were found under tickets/'
for directory in ticket_dirs:
    md_files = sorted(directory.glob('*.md'))
    assert len(md_files) == 1, f'{directory} should contain exactly one ticket markdown file'
    path = md_files[0]
    assert path.name == f'{directory.name}.md', f'{directory} name does not match the ticket file name'
    content = path.read_text(encoding='utf-8')
    assert content.startswith('---\n'), f'{path} is missing YAML frontmatter'
    assert '## Objective' in content, f'{path} is missing Objective section'
    assert '## Acceptance Criteria' in content, f'{path} is missing Acceptance Criteria section'
    assert '## Validation Approach' in content, f'{path} is missing Validation Approach section'
    assert '## History' in content, f'{path} is missing History section'
    assert '## Blockers and Questions' in content, f'{path} is missing Blockers and Questions section'
print('ticket schema validation passed')
PY
```

This check is intentionally narrow and repository-specific; it validates the local ticket contract rather than inventing a generic ticket system.
