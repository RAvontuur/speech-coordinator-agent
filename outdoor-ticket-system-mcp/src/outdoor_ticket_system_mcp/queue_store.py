import os
import uuid
from pathlib import Path


class TicketPromptQueue:
    def __init__(self, queue_dir: str | Path):
        self.queue_dir = Path(queue_dir).expanduser().resolve()
        self.processing_dir = self.queue_dir / ".processing"
        self.completed_dir = self.queue_dir / ".completed"

    def claim_next(self) -> dict | None:
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.processing_dir.mkdir(exist_ok=True)
        pending = []
        for path in self.queue_dir.iterdir():
            if path.suffix.lower() != ".md" or path.is_symlink() or not path.is_file():
                continue
            try:
                pending.append((path.stat().st_mtime_ns, path.name, path))
            except FileNotFoundError:
                continue

        for _, _, source in sorted(pending):
            claim_id = f"{uuid.uuid4().hex}--{source.name}"
            claimed = self.processing_dir / claim_id
            try:
                source.rename(claimed)
            except FileNotFoundError:
                continue
            return {
                "claim_id": claim_id,
                "filename": source.name,
                "prompt": claimed.read_text(encoding="utf-8"),
            }
        return None

    def complete(self, claim_id: str) -> dict:
        claimed = self._claimed_path(claim_id)
        self.completed_dir.mkdir(exist_ok=True)
        destination = self.completed_dir / claim_id
        claimed.rename(destination)
        return {"status": "completed", "claim_id": claim_id}

    def requeue(self, claim_id: str) -> dict:
        claimed = self._claimed_path(claim_id)
        original_name = self._original_filename(claim_id)
        destination_name = f"{uuid.uuid4().hex}--{original_name}"
        claimed.rename(self.queue_dir / destination_name)
        return {"status": "queued", "filename": destination_name}

    def _claimed_path(self, claim_id: str) -> Path:
        original_name = self._original_filename(claim_id)
        prefix = claim_id.split("--", maxsplit=1)[0]
        try:
            uuid.UUID(hex=prefix)
        except ValueError as error:
            raise ValueError("claim_id is invalid") from error
        claimed = self.processing_dir / claim_id
        if not claimed.is_file():
            raise FileNotFoundError(f"claimed prompt not found: {claim_id}")
        return claimed

    @staticmethod
    def _original_filename(claim_id: str) -> str:
        prefix, separator, filename = claim_id.partition("--")
        if (
            not separator
            or not prefix
            or not filename
            or Path(filename).name != filename
            or Path(filename).suffix.lower() != ".md"
        ):
            raise ValueError("claim_id is invalid")
        return filename


def queue_from_environment() -> TicketPromptQueue:
    workspace_root = Path(__file__).resolve().parents[3]
    queue_dir = os.getenv("OUTDOOR_TICKET_QUEUE_DIR", str(workspace_root / "ticket-queue"))
    return TicketPromptQueue(queue_dir)