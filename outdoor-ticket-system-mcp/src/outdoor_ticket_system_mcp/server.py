import logging
from typing import Literal

from mcp.server.fastmcp import FastMCP

from .queue_store import queue_from_environment
from .ticket_store import ticket_store_from_environment


logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)
mcp = FastMCP("outdoor-ticket-system-mcp")
queue = queue_from_environment()
ticket_store = ticket_store_from_environment()


@mcp.tool()
def claim_next_prompt() -> dict | None:
    """Atomically claim the oldest Markdown coding prompt in the queue."""
    prompt = queue.claim_next()
    logger.info("Claimed queued prompt: %s", prompt["filename"] if prompt else "none")
    return prompt


@mcp.tool()
def complete_prompt(claim_id: str) -> dict:
    """Move a successfully handled prompt out of processing and into completed."""
    return queue.complete(claim_id)


@mcp.tool()
def requeue_prompt(claim_id: str) -> dict:
    """Return an unprocessed or interrupted prompt to the pending queue."""
    return queue.requeue(claim_id)


@mcp.tool()
def list_tickets(
    state: str | None = None,
    output_mode: Literal["ids", "headers", "full"] = "headers",
) -> list[str] | list[dict]:
    """List tickets by state and return IDs, frontmatter headers, or full records."""
    return ticket_store.list_tickets(state, output_mode)


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


@mcp.tool()
def prepare_ticket_plan() -> dict:
    """Write Markdown for every non-closed ticket for synthesis by outdoor-speech-mcp."""
    return ticket_store.prepare_ticket_plan()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()