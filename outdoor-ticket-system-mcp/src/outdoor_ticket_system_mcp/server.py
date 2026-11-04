import inspect
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .repository_store import RepositoryStore
from .ticket_store import ticket_store_from_environment


mcp = FastMCP("outdoor-ticket-system-mcp")
ticket_store = ticket_store_from_environment()
repository_store = RepositoryStore(ticket_store.ticket_root)
ticket_store.repository_store = repository_store


@mcp.tool()
def list_repositories() -> list[dict]:
    """List registered repositories available to the ticket service."""
    return repository_store.list_repositories()


@mcp.tool()
def get_repository(name: str) -> dict:
    """Return one registered repository by name."""
    return repository_store.get_repository(name)


@mcp.tool()
def create_repository(
    name: str,
    get_url: str,
    local_directory: str,
    default_target_branch: str | None = None,
) -> dict:
    """Register a repository's name, Git GET URL, and local clone directory."""
    return repository_store.create_repository(
        name, get_url, local_directory, default_target_branch
    )


@mcp.tool()
def update_repository(name: str, updates: dict) -> dict:
    """Update fields on a registered repository, including its name."""
    return repository_store.update_repository(name, updates)


@mcp.tool()
def delete_repository(name: str) -> dict:
    """Remove a repository registration by name."""
    return repository_store.delete_repository(name)


@mcp.tool()
def select_ticket_repository(
    ticket_id: str,
    repository_name: str,
    working_branch: str,
    target_branch: str | None = None,
) -> dict:
    """Record the registered repository and resolved branch names for a ticket."""
    return ticket_store.select_ticket_repository(
        ticket_id, repository_name, working_branch, target_branch
    )


@mcp.tool()
def create_working_branch(ticket_id: str) -> dict:
    """Create the selected ticket branch from its target immediately before coding."""
    return ticket_store.create_working_branch(ticket_id)


@mcp.tool()
def finish_working_branch(ticket_id: str) -> dict:
    """Commit ticket changes and switch back to its selected target after coding."""
    return ticket_store.finish_working_branch(ticket_id)


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
    plan_number: int,
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