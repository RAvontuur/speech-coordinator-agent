import asyncio
from pathlib import Path

import pytest

from outdoor_ticket_system_mcp.ticket_store import TicketStore


def _store(tmp_path: Path) -> TicketStore:
    root = tmp_path / "tickets"
    root.mkdir()
    (root / "README.md").write_text(
        "# Local Ticket System\n\n## Ticket Format\n\n## States\n", encoding="utf-8"
    )
    return TicketStore(root)


def _write_ticket(
    store: TicketStore,
    state: str = "new",
    ticket_id: str = "OC-001",
    title: str = "Example ticket",
) -> Path:
    directory_name = f"{ticket_id}-{title.lower().replace(' ', '-')}"
    directory = store.ticket_root / directory_name
    directory.mkdir()
    path = directory / f"{directory_name}.md"
    path.write_text(_ticket_content(ticket_id, title, state), encoding="utf-8")
    return path


def _ticket_content(ticket_id: str, title: str, state: str) -> str:
    return f"""---
id: {ticket_id}
title: {title}
state: {state}
type: feature
created: 2026-10-14
updated: 2026-10-14
priority: normal
dependencies: []
related: []
affected_area:
  - src/example.py
---

# {title}

## Objective

Deliver the example behavior.

## Acceptance Criteria

- The behavior is observable.

## Validation Approach

Run the focused test.

## Change Record

Not implemented yet.

## Review Documentation

Not applicable until implementation is complete.

## History

- 2026-10-14, `new`: Created for testing.

## Blockers and Questions

None
"""


def test_validates_repository_ticket_and_reports_schema_errors(tmp_path):
    store = _store(tmp_path)
    path = _write_ticket(store)
    (path.parent / "related-notes.md").write_text("Ticket artifact.", encoding="utf-8")

    result = store.validate_tickets()

    assert result["valid"] is True
    assert result["checked"] == 1
    assert store.get_ticket("OC-001")["path"] == str(path)
    assert store.list_tickets()[0]["created"] == "2026-10-14"

    path.write_text("---\nid: [invalid\n---\n", encoding="utf-8")
    result = store.validate_tickets()
    assert result["valid"] is False
    assert "invalid YAML frontmatter" in result["tickets"][0]["errors"][0]

    path.write_text(
        _ticket_content("OC-001", "Example ticket", "[new]"), encoding="utf-8"
    )
    result = store.validate_tickets()
    assert any("state must be one of" in error for error in result["tickets"][0]["errors"])


def test_list_tickets_filters_by_state_and_selects_output(tmp_path):
    store = _store(tmp_path)
    path = _write_ticket(store)
    _write_ticket(store, "review", "OC-002", "Review ticket")

    assert store.list_tickets(state="new", output_mode="ids") == ["OC-001"]
    assert store.list_tickets(state="blocked", output_mode="ids") == []

    headers = store.list_tickets(state="new", output_mode="headers")
    assert len(headers) == 1
    assert headers[0]["id"] == "OC-001"
    assert "body" not in headers[0]

    full = store.list_tickets(state="new", output_mode="full")
    assert full[0]["path"] == str(path)
    assert full[0]["title"] == "Example ticket"
    assert "## Objective" in full[0]["body"]

    with pytest.raises(ValueError, match="invalid state"):
        store.list_tickets(state="unknown")


def test_ids_only_mode_does_not_hide_invalid_ticket_records(tmp_path):
    store = _store(tmp_path)
    path = _write_ticket(store)
    path.write_text("malformed ticket", encoding="utf-8")

    with pytest.raises(ValueError, match="ticket records are invalid"):
        store.list_tickets(output_mode="ids")

    listed = store.list_tickets(output_mode="headers")
    assert listed[0]["errors"]


def test_mcp_list_tickets_accepts_hyphenated_file_format(tmp_path, monkeypatch):
    from outdoor_ticket_system_mcp import server

    store = _store(tmp_path)
    _write_ticket(store)
    monkeypatch.setattr(server, "ticket_store", store)
    tool = next(
        tool for tool in server.mcp._tool_manager.list_tools() if tool.name == "list_tickets"
    )

    result = asyncio.run(tool.run({"file-format": "markdown"}))

    assert result.startswith("# Sprint Review Plan")
    assert "OC-001: Example ticket" in result


def test_create_update_and_transition_append_history(tmp_path):
    store = _store(tmp_path)
    created = store.create_ticket(
        title="Add a ticket API",
        ticket_type="feature",
        objective="Expose ticket operations.",
        acceptance_criteria=["Users can list tickets."],
        validation_approach="Run ticket service tests.",
        affected_area=["outdoor-ticket-system-mcp/"],
        creation_evidence="Requested directly by the user.",
    )
    assert created["id"] == "OC-001"

    store.update_ticket("OC-001", {"Objective": "Expose local ticket operations."})
    with pytest.raises(ValueError, match="decision_evidence"):
        store.transition_ticket("OC-001", "ready", "Criteria are complete.")

    store.transition_ticket(
        "OC-001", "ready", "Required fields are concrete.", "User approved readiness."
    )
    store.transition_ticket("OC-001", "in_progress", "Implementation started.")
    store.transition_ticket("OC-001", "review", "Focused tests passed.")
    ticket = store.get_ticket("OC-001")
    assert ticket["state"] == "review"
    assert "Created through the ticket MCP" in ticket["body"]
    assert "User approved readiness." in ticket["body"]
    assert "Focused tests passed." in ticket["body"]
    with pytest.raises(ValueError, match="decision_evidence"):
        store.transition_ticket("OC-001", "closed", "Tests passed.")
    store.transition_ticket("OC-001", "closed", "User accepted.", "Accepted in review.")

    with pytest.raises(ValueError, match="non-editable fields: History"):
        store.update_ticket("OC-001", {"History": "rewritten"})


def test_annotation_driven_ready_transition_keeps_history_and_rejects_invalid_close(tmp_path):
    store = _store(tmp_path)
    ticket = store.create_ticket(
        title="Add annotation state transitions",
        ticket_type="feature",
        objective="Allow explicit annotation-driven transitions.",
        acceptance_criteria=["Users can move tickets to ready or closed via annotation intent."],
        validation_approach="Run the focused ticket transition tests.",
        affected_area=["tickets/"],
        creation_evidence="Requested by users during annotation review.",
    )
    assert ticket["id"] == "OC-001"

    store.transition_ticket(
        "OC-001",
        "ready",
        "Annotation requested state change to ready.",
        "User explicitly approved the ready state.",
    )
    updated = store.get_ticket("OC-001")
    assert updated["state"] == "ready"
    assert "Annotation requested state change to ready." in updated["body"]
    assert "User explicitly approved the ready state." in updated["body"]
    assert "Created through the ticket MCP" in updated["body"]

    with pytest.raises(ValueError, match="not allowed"):
        store.transition_ticket("OC-001", "closed", "Close as requested.", "User requested closure.")


def test_ready_transition_requires_concrete_fields(tmp_path):
    store = _store(tmp_path)
    path = _write_ticket(store)
    content = path.read_text(encoding="utf-8").replace("Deliver the example behavior.", "TBD")
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="Objective must be concrete"):
        store.transition_ticket(
            "OC-001", "ready", "Ready to start.", "User approved readiness."
        )


def test_blocked_transition_records_blocker_in_ticket_body(tmp_path):
    store = _store(tmp_path)
    _write_ticket(store)

    store.transition_ticket("OC-001", "blocked", "Waiting for API credentials.")

    ticket = store.get_ticket("OC-001")
    assert ticket["state"] == "blocked"
    assert "Waiting for API credentials." in ticket["body"]


def test_plan_includes_open_tickets_and_excludes_closed_tickets(tmp_path):
    store = _store(tmp_path)
    _write_ticket(store)
    _write_ticket(store, "review", "OC-002", "Review ticket")
    _write_ticket(store, "closed", "OC-003", "Closed ticket")

    plan = store.list_tickets(file_format="markdown")
    assert "OC-001: Example ticket" in plan
    assert '<a id="oc-001"></a>' in plan
    assert "OC-002: Review ticket" in plan
    assert '<a id="oc-002"></a>' in plan
    assert "Sprint Review Plan" in plan
    assert "State: review" in plan
    assert "Not applicable until implementation is complete." in plan
    assert "OC-003" not in plan

    ready_plan = store.list_tickets(state="new", file_format="markdown")
    assert "OC-001: Example ticket" in ready_plan
    assert "OC-002" not in ready_plan


def test_missing_schema_and_symlink_ticket_are_not_followed(tmp_path):
    missing = TicketStore(tmp_path / "missing")
    with pytest.raises(FileNotFoundError, match="refusing to create another ticket store"):
        missing.list_tickets()

    store = _store(tmp_path)
    target = tmp_path / "outside"
    target.mkdir()
    (target / "ticket.md").write_text("not a ticket", encoding="utf-8")
    (store.ticket_root / "OC-003-linked").symlink_to(target, target_is_directory=True)
    assert store.validate_tickets()["checked"] == 0