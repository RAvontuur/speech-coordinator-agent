import os
from pathlib import Path

from outdoor_ticket_system_mcp.queue_store import TicketPromptQueue


def test_claim_next_uses_oldest_markdown_and_complete_moves_it(tmp_path):
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    older = queue_dir / "older.md"
    newer = queue_dir / "newer.md"
    older.write_text("Fix the parser.", encoding="utf-8")
    newer.write_text("Add a test.", encoding="utf-8")
    os.utime(older, ns=(1_000_000_000, 1_000_000_000))
    os.utime(newer, ns=(2_000_000_000, 2_000_000_000))
    queue = TicketPromptQueue(queue_dir)

    claimed = queue.claim_next()

    assert claimed is not None
    assert claimed["filename"] == "older.md"
    assert claimed["prompt"] == "Fix the parser."
    assert not older.exists()
    assert newer.exists()
    assert queue.complete(claimed["claim_id"]) == {
        "status": "completed",
        "claim_id": claimed["claim_id"],
    }
    assert (queue.completed_dir / claimed["claim_id"]).read_text(encoding="utf-8") == (
        "Fix the parser."
    )


def test_requeue_returns_claimed_prompt_to_pending_queue(tmp_path):
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    (queue_dir / "task.md").write_text("Implement the feature.", encoding="utf-8")
    queue = TicketPromptQueue(queue_dir)

    claimed = queue.claim_next()
    requeued = queue.requeue(claimed["claim_id"])

    assert requeued["status"] == "queued"
    assert (queue_dir / requeued["filename"]).read_text(encoding="utf-8") == (
        "Implement the feature."
    )
    assert not (queue.processing_dir / claimed["claim_id"]).exists()


def test_claim_next_ignores_non_markdown_files(tmp_path):
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    (queue_dir / "notes.txt").write_text("not a prompt", encoding="utf-8")
    queue = TicketPromptQueue(queue_dir)

    assert queue.claim_next() is None