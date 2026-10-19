import inspect
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .ticket_store import ticket_store_from_environment


mcp = FastMCP("outdoor-ticket-system-mcp")
ticket_store = ticket_store_from_environment()


def _list_tickets_signature(
    state: str | None = None,
    output_mode: Literal["ids", "headers", "full"] = "headers",
    file_format: Annotated[Literal["json", "markdown"], Field(alias="file-format")] = "json",
) -> str | list[str] | list[dict]:
    """List tickets as JSON projections or a Markdown Sprint Review Plan."""
    return ticket_store.list_tickets(state, output_mode, file_format)


def list_tickets(**kwargs: Any) -> str | list[str] | list[dict]:
    """List tickets as JSON projections or a Markdown Sprint Review Plan."""
    return ticket_store.list_tickets(
        kwargs.get("state"),
        kwargs.get("output_mode", "headers"),
        kwargs.get("file-format", "json"),
    )


list_tickets.__signature__ = inspect.signature(_list_tickets_signature)
mcp.tool()(list_tickets)


@mcp.tool()
def get_ticket(ticket_id: str) -> dict:
    """Return one validated local ticket by ID, including its Markdown body."""
    return ticket_store.get_ticket(ticket_id)


@mcp.tool()
def validate_tickets(ticket_id: str | None = None) -> dict:
    """Validate one ticket by ID, or all ticket records when no ID is supplied."""
    return ticket_store.validate_tickets(ticket_id)


@mcp.tool()
def create_ticket(
    title: str,
    ticket_type: str,
    objective: str,
    acceptance_criteria: list[str],
    validation_approach: str,
    affected_area: list[str],
    creation_evidence: str,
    priority: str = "normal",
    dependencies: list[str] | None = None,
    related: list[str] | None = None,
) -> dict:
    """Create a schema-valid ticket in new state with an initial history entry."""
    return ticket_store.create_ticket(
        title,
        ticket_type,
        objective,
        acceptance_criteria,
        validation_approach,
        affected_area,
        creation_evidence,
        priority,
        dependencies,
        related,
    )


@mcp.tool()
def update_ticket(ticket_id: str, updates: dict) -> dict:
    """Update ticket metadata or named body sections; History and state are protected."""
    return ticket_store.update_ticket(ticket_id, updates)


@mcp.tool()
def transition_ticket(
    ticket_id: str,
    new_state: str,
    evidence: str,
    decision_evidence: str | None = None,
) -> dict:
    """Transition a ticket and append evidence; selected states require decision evidence."""
    return ticket_store.transition_ticket(ticket_id, new_state, evidence, decision_evidence)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()