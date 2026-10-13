import logging

from mcp.server.fastmcp import FastMCP

from .queue_store import queue_from_environment


logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)
mcp = FastMCP("outdoor-ticket-system-mcp")
queue = queue_from_environment()


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


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()