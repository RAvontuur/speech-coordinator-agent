import os
import re
import tempfile
import threading
from datetime import date
from pathlib import Path
from typing import Literal

import yaml


STATES = {"new", "refined", "ready", "in_progress", "review", "blocked", "closed"}
REQUIRED_FRONTMATTER = {
    "id",
    "title",
    "state",
    "type",
    "created",
    "updated",
    "priority",
    "dependencies",
    "related",
    "affected_area",
}
REQUIRED_SECTIONS = (
    "Objective",
    "Acceptance Criteria",
    "Validation Approach",
    "Change Record",
    "Review Documentation",
    "History",
    "Blockers and Questions",
)
EDITABLE_METADATA = {"title", "type", "priority", "dependencies", "related", "affected_area"}
EDITABLE_SECTIONS = set(REQUIRED_SECTIONS) - {"History"}
TRANSITIONS = {
    "new": {"refined", "ready"},
    "refined": {"ready"},
    "ready": {"in_progress"},
    "in_progress": {"review"},
    "review": {"in_progress", "closed"},
    "blocked": {"ready", "in_progress"},
    "closed": set(),
}
DECISION_STATES = {"refined", "ready", "closed"}
_ID_PATTERN = re.compile(r"^OC-(\d{3,})$")
_HISTORY_PATTERN = re.compile(r"^- (\d{4}-\d{2}-\d{2}), `([^`]+)`: (.+)$")


class TicketStore:
    def __init__(self, ticket_root: str | Path, plan_source_dir: str | Path | None = None):
        self.ticket_root = Path(ticket_root).expanduser().resolve()
        self.plan_source_dir = (
            Path(plan_source_dir).expanduser().resolve()
            if plan_source_dir
            else Path(tempfile.gettempdir()) / "outdoor-ticket-system-mcp"
        )
        self._lock = threading.RLock()

    def list_tickets(
        self,
        state: str | None = None,
        output_mode: Literal["ids", "headers", "full"] = "headers",
    ) -> list[str] | list[dict]:
        self._require_schema()
        if state is not None and state not in STATES:
            raise ValueError(f"invalid state {state!r}; expected one of {', '.join(sorted(STATES))}")
        if output_mode not in {"ids", "headers", "full"}:
            raise ValueError("output_mode must be one of: ids, headers, full")

        tickets = []
        errors = []
        for directory in self._ticket_directories():
            path = self._ticket_markdown_file(directory)
            if path is None:
                if state is None:
                    errors.append(f"{directory}: {self._markdown_count_error(directory)}")
                    if output_mode != "ids":
                        tickets.append({
                            "path": str(directory),
                            "errors": [self._markdown_count_error(directory)],
                        })
                continue
            ticket_errors, metadata, body = self._validate_file(path)
            if state is not None and metadata.get("state") != state:
                continue
            if ticket_errors:
                errors.extend(ticket_errors)
                if output_mode != "ids":
                    tickets.append({"path": str(path), "id": metadata.get("id"), "errors": ticket_errors})
            else:
                ticket = {"path": str(path), **self._json_metadata(metadata)}
                if output_mode == "ids":
                    tickets.append(metadata["id"])
                else:
                    if output_mode == "full":
                        ticket["body"] = body
                    tickets.append(ticket)
        if output_mode == "ids" and errors:
            raise ValueError("cannot list IDs because ticket records are invalid: " + "; ".join(errors))
        return tickets

    def get_ticket(self, ticket_id: str) -> dict:
        path = self._find_ticket_path(ticket_id)
        errors, metadata, body = self._validate_file(path)
        if errors:
            raise ValueError("; ".join(errors))
        return {"path": str(path), **self._json_metadata(metadata), "body": body}

    def validate_tickets(self, ticket_id: str | None = None) -> dict:
        self._require_schema()
        if ticket_id:
            paths = [self._find_ticket_path(ticket_id)]
        else:
            paths = []
            for directory in self._ticket_directories():
                path = self._ticket_markdown_file(directory)
                if path is None:
                    paths.append(directory)
                else:
                    paths.append(path)

        results = []
        for path in paths:
            if path.is_dir():
                errors = [self._markdown_count_error(path)]
            else:
                errors, _, _ = self._validate_file(path)
            results.append({"path": str(path), "valid": not errors, "errors": errors})
        return {
            "valid": all(result["valid"] for result in results),
            "checked": len(results),
            "tickets": results,
        }

    def create_ticket(
        self,
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
        self._require_schema()
        title = self._required_text(title, "title")
        creation_evidence = self._required_text(creation_evidence, "creation_evidence")
        ticket_type = self._required_text(ticket_type, "type")
        objective = self._required_text(objective, "objective")
        validation_approach = self._required_text(validation_approach, "validation_approach")
        affected_area = self._string_list(affected_area, "affected_area")
        acceptance_criteria = self._string_list(acceptance_criteria, "acceptance_criteria")
        priority = self._required_text(priority, "priority")

        with self._lock:
            sequence = self._next_sequence()
            ticket_id = f"OC-{sequence:03d}"
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "ticket"
            directory_name = f"{ticket_id}-{slug}"
            directory = self.ticket_root / directory_name
            if directory.exists():
                raise FileExistsError(f"ticket already exists: {directory}")
            today = date.today().isoformat()
            metadata = {
                "id": ticket_id,
                "title": title,
                "state": "new",
                "type": ticket_type,
                "created": today,
                "updated": today,
                "priority": priority,
                "dependencies": self._string_list(dependencies or [], "dependencies"),
                "related": self._string_list(related or [], "related"),
                "affected_area": affected_area,
            }
            sections = {
                "Objective": objective,
                "Acceptance Criteria": "\n".join(f"- {item}" for item in acceptance_criteria),
                "Validation Approach": validation_approach,
                "Change Record": "Not implemented yet.",
                "Review Documentation": "Not applicable until implementation is complete.",
                "History": f"- {today}, `new`: Created through the ticket MCP. {self._single_line(creation_evidence)}",
                "Blockers and Questions": "None",
            }
            content = self._serialize(metadata, self._render_sections(title, sections))
            errors, _, _ = self._validate_content(content, directory, directory / f"{directory_name}.md")
            if errors:
                raise ValueError("ticket would be invalid: " + "; ".join(errors))
            directory.mkdir()
            path = directory / f"{directory_name}.md"
            try:
                self._atomic_write(path, content)
            except Exception:
                path.unlink(missing_ok=True)
                directory.rmdir()
                raise
        return {"id": ticket_id, "path": str(path), "state": "new"}

    def update_ticket(self, ticket_id: str, updates: dict) -> dict:
        if not isinstance(updates, dict) or not updates:
            raise ValueError("updates must be a non-empty object")
        unknown = set(updates) - EDITABLE_METADATA - EDITABLE_SECTIONS
        if unknown:
            raise ValueError(f"updates contain non-editable fields: {', '.join(sorted(unknown))}")

        with self._lock:
            path = self._find_ticket_path(ticket_id)
            errors, metadata, body = self._validate_file(path)
            if errors:
                raise ValueError("cannot update invalid ticket: " + "; ".join(errors))
            for key in EDITABLE_METADATA.intersection(updates):
                value = updates[key]
                metadata[key] = self._string_list(value, key) if key in {"dependencies", "related", "affected_area"} else self._required_text(value, key)
            for section in EDITABLE_SECTIONS.intersection(updates):
                value = updates[section]
                if isinstance(value, list):
                    value = "\n".join(f"- {self._required_text(item, section)}" for item in value)
                body = self._replace_section(body, section, self._required_text(value, section))
            metadata["updated"] = date.today().isoformat()
            content = self._serialize(metadata, body)
            errors, _, _ = self._validate_content(content, path.parent, path)
            if errors:
                raise ValueError("updated ticket would be invalid: " + "; ".join(errors))
            self._atomic_write(path, content)
        return {"id": metadata["id"], "path": str(path), "updated": metadata["updated"]}

    def transition_ticket(
        self,
        ticket_id: str,
        new_state: str,
        evidence: str,
        decision_evidence: str | None = None,
    ) -> dict:
        if new_state not in STATES:
            raise ValueError(f"invalid state {new_state!r}; expected one of {', '.join(sorted(STATES))}")
        evidence = self._single_line(self._required_text(evidence, "evidence"))
        if new_state in DECISION_STATES:
            decision_evidence = self._single_line(self._required_text(decision_evidence, "decision_evidence"))

        with self._lock:
            path = self._find_ticket_path(ticket_id)
            errors, metadata, body = self._validate_file(path)
            if errors:
                raise ValueError("cannot transition invalid ticket: " + "; ".join(errors))
            old_state = metadata["state"]
            allowed = set(TRANSITIONS[old_state])
            if old_state != "closed":
                allowed.add("blocked")
            if new_state not in allowed:
                raise ValueError(f"transition {old_state!r} -> {new_state!r} is not allowed")
            if new_state == "ready":
                readiness_errors = self._readiness_errors(metadata, body, path)
                if readiness_errors:
                    raise ValueError("ticket is not ready: " + "; ".join(readiness_errors))
            history = self._section_body(body, "History")
            entry = f"- {date.today().isoformat()}, `{new_state}`: {evidence}"
            if decision_evidence:
                entry += f" Decision evidence: {decision_evidence}"
            body = self._replace_section(body, "History", f"{history.rstrip()}\n{entry}")
            if new_state == "blocked":
                body = self._replace_section(body, "Blockers and Questions", evidence)
            metadata["state"] = new_state
            metadata["updated"] = date.today().isoformat()
            content = self._serialize(metadata, body)
            errors, _, _ = self._validate_content(content, path.parent, path)
            if errors:
                raise ValueError("transition would make ticket invalid: " + "; ".join(errors))
            self._atomic_write(path, content)
        return {"id": metadata["id"], "from": old_state, "state": new_state, "path": str(path)}

    def prepare_ticket_plan(self) -> dict:
        self._require_schema()
        tickets = []
        for item in self.list_tickets():
            if item.get("errors"):
                raise ValueError(f"cannot prepare plan: {item['path']}: {'; '.join(item['errors'])}")
            if item["state"] != "closed":
                tickets.append(self.get_ticket(item["id"]))
        tickets.sort(key=lambda ticket: ticket["id"])
        lines = ["# Local Ticket Plan", ""]
        if not tickets:
            lines.append("There are no open tickets.")
        for ticket in tickets:
            lines.extend([f"## {ticket['id']}: {ticket['title']}", ""])
            sections = self._sections(ticket["body"])
            if ticket["state"] == "review":
                lines.extend([
                    "State: review",
                    "",
                    "### Review Documentation",
                    "",
                    sections["Review Documentation"],
                    "",
                ])
                continue
            lines.extend([
                f"State: {ticket['state']}",
                "",
                "Objective:",
                sections["Objective"],
                "",
                "Dependencies: " + (", ".join(ticket["dependencies"]) or "None"),
                "",
                "Blockers:",
                sections["Blockers and Questions"],
                "",
                "Next action: " + self._next_action(ticket["state"]),
                "",
            ])
        self.plan_source_dir.mkdir(parents=True, exist_ok=True)
        path = self.plan_source_dir / "ticket-plan-source.md"
        with self._lock:
            self._atomic_write(path, "\n".join(lines).rstrip() + "\n")
        return {"source_file": str(path), "ticket_ids": [ticket["id"] for ticket in tickets]}

    def _require_schema(self) -> None:
        readme = self.ticket_root / "README.md"
        if not self.ticket_root.is_dir() or not readme.is_file() or readme.is_symlink():
            raise FileNotFoundError(
                f"ticket schema not found: expected {readme}; refusing to create another ticket store"
            )
        text = readme.read_text(encoding="utf-8")
        for heading in ("## Ticket Format", "## States"):
            if heading not in text:
                raise ValueError(f"{readme} is not a recognized ticket schema; missing {heading}")

    def _ticket_directories(self) -> list[Path]:
        return sorted(
            (path for path in self.ticket_root.iterdir() if path.is_dir() and not path.is_symlink()),
            key=lambda path: path.name.lower(),
        )

    @staticmethod
    def _markdown_files(directory: Path) -> list[Path]:
        return sorted(
            (path for path in directory.glob("*.md") if path.is_file() and not path.is_symlink()),
            key=lambda path: path.name.lower(),
        )

    @staticmethod
    def _ticket_markdown_file(directory: Path) -> Path | None:
        path = directory / f"{directory.name}.md"
        return path if path.is_file() and not path.is_symlink() else None

    @classmethod
    def _markdown_count_error(cls, directory: Path) -> str:
        count = len(cls._markdown_files(directory))
        return f"{directory}: expected non-symlink ticket file {directory.name}.md; found {count} Markdown files"

    def _find_ticket_path(self, ticket_id: str) -> Path:
        self._require_schema()
        if not isinstance(ticket_id, str) or not _ID_PATTERN.fullmatch(ticket_id):
            raise ValueError("ticket_id must use the format OC-###")
        matches = []
        for directory in self._ticket_directories():
            path = self._ticket_markdown_file(directory)
            if path:
                _, metadata, _ = self._validate_file(path)
                if metadata.get("id") == ticket_id:
                    matches.append(path)
        if not matches:
            raise FileNotFoundError(f"ticket not found: {ticket_id}")
        if len(matches) > 1:
            raise ValueError(f"ticket ID is not unique: {ticket_id}")
        return matches[0]

    @staticmethod
    def _json_metadata(metadata: dict) -> dict:
        return {
            key: value.isoformat() if isinstance(value, date) else value
            for key, value in metadata.items()
        }

    def _validate_file(self, path: Path) -> tuple[list[str], dict, str]:
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            return [f"{path}: unable to read ticket: {error}"], {}, ""
        return self._validate_content(content, path.parent, path)

    def _validate_content(self, content: str, directory: Path, path: Path) -> tuple[list[str], dict, str]:
        if path.is_symlink() or directory.is_symlink():
            return [f"{path}: symlink ticket paths are not allowed"], {}, ""
        try:
            path.resolve().relative_to(self.ticket_root)
        except ValueError:
            return [f"{path}: ticket path is outside {self.ticket_root}"], {}, ""
        metadata, body, parse_error = self._parse(content, path)
        if parse_error:
            return [parse_error], {}, ""
        errors = []
        missing = REQUIRED_FRONTMATTER - metadata.keys()
        errors.extend(f"{path}: missing frontmatter field {key!r}" for key in sorted(missing))
        ticket_id = metadata.get("id")
        if not isinstance(ticket_id, str) or not _ID_PATTERN.fullmatch(ticket_id or ""):
            errors.append(f"{path}: id must use the format OC-###")
        elif not directory.name.startswith(ticket_id + "-"):
            errors.append(f"{path}: directory name must begin with {ticket_id}-")
        if path.name != f"{directory.name}.md":
            errors.append(f"{path}: Markdown filename must match its ticket directory name")
        state = metadata.get("state")
        if not isinstance(state, str) or state not in STATES:
            errors.append(f"{path}: state must be one of {', '.join(sorted(STATES))}")
        for key in ("title", "type", "priority"):
            if key in metadata and (not isinstance(metadata[key], str) or not metadata[key].strip()):
                errors.append(f"{path}: {key} must be a non-empty string")
        for key in ("created", "updated"):
            if key in metadata and not isinstance(metadata[key], date):
                try:
                    date.fromisoformat(metadata[key])
                except (TypeError, ValueError):
                    errors.append(f"{path}: {key} must be an ISO date")
        for key in ("dependencies", "related", "affected_area"):
            if key in metadata and (
                not isinstance(metadata[key], list)
                or any(not isinstance(value, str) or not value.strip() for value in metadata[key])
            ):
                errors.append(f"{path}: {key} must be a list of non-empty strings")
        sections = self._sections(body)
        for section in REQUIRED_SECTIONS:
            if section not in sections:
                errors.append(f"{path}: missing required section '## {section}'")
        if "History" in sections:
            history_entries = [line.strip() for line in sections["History"].splitlines() if line.strip()]
            if not history_entries:
                errors.append(f"{path}: History must contain dated state entries with evidence")
            for entry in history_entries:
                match = _HISTORY_PATTERN.fullmatch(entry)
                if not match or match.group(2) not in STATES or not match.group(3).strip():
                    errors.append(f"{path}: invalid History entry {entry!r}; expected '- YYYY-MM-DD, `state`: evidence'")
                else:
                    try:
                        date.fromisoformat(match.group(1))
                    except ValueError:
                        errors.append(f"{path}: History entry has an invalid date: {entry!r}")
        if metadata.get("state") == "ready":
            errors.extend(self._readiness_errors(metadata, body, path))
        return errors, metadata, body

    @staticmethod
    def _parse(content: str, path: Path) -> tuple[dict, str, str | None]:
        if not content.startswith("---\n"):
            return {}, "", f"{path}: missing YAML frontmatter starting with ---"
        marker = content.find("\n---\n", 4)
        if marker == -1:
            return {}, "", f"{path}: missing closing YAML frontmatter delimiter"
        try:
            metadata = yaml.safe_load(content[4:marker])
        except yaml.YAMLError as error:
            return {}, "", f"{path}: invalid YAML frontmatter: {error}"
        if not isinstance(metadata, dict):
            return {}, "", f"{path}: YAML frontmatter must be an object"
        return metadata, content[marker + 5 :], None

    @staticmethod
    def _sections(body: str) -> dict[str, str]:
        lines = body.splitlines()
        headings = []
        for index, line in enumerate(lines):
            match = re.fullmatch(r"##\s+(.+?)\s*", line)
            if match:
                headings.append((index, match.group(1).strip()))
        sections = {}
        for position, (start, title) in enumerate(headings):
            end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
            canonical_title = next(
                (required for required in REQUIRED_SECTIONS if required.casefold() == title.casefold()),
                title,
            )
            sections[canonical_title] = "\n".join(lines[start + 1 : end]).strip()
        return sections

    @classmethod
    def _section_body(cls, body: str, section: str) -> str:
        for title, value in cls._sections(body).items():
            if title.casefold() == section.casefold():
                return value
        raise ValueError(f"missing section: {section}")

    @classmethod
    def _replace_section(cls, body: str, section: str, replacement: str) -> str:
        lines = body.splitlines()
        headings = []
        for index, line in enumerate(lines):
            match = re.fullmatch(r"##\s+(.+?)\s*", line)
            if match:
                headings.append((index, match.group(1).strip()))
        for position, (start, title) in enumerate(headings):
            if title.casefold() != section.casefold():
                continue
            end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
            lines[start + 1 : end] = ["", *replacement.strip().splitlines(), ""]
            return "\n".join(lines).strip() + "\n"
        raise ValueError(f"missing section: {section}")

    @staticmethod
    def _serialize(metadata: dict, body: str) -> str:
        frontmatter = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True).rstrip()
        return f"---\n{frontmatter}\n---\n\n{body.lstrip()}"

    @staticmethod
    def _render_sections(title: str, sections: dict[str, str]) -> str:
        chunks = [f"# {title}"]
        for section in REQUIRED_SECTIONS:
            chunks.extend(["", f"## {section}", "", sections[section]])
        return "\n".join(chunks) + "\n"

    @staticmethod
    def _readiness_errors(metadata: dict, body: str, path: Path) -> list[str]:
        errors = []
        sections = TicketStore._sections(body)
        for section in ("Objective", "Acceptance Criteria", "Validation Approach"):
            value = sections.get(section, "").strip()
            normalized = re.sub(r"(?m)^\s*[-*+]\s*", "", value).strip().casefold()
            if not normalized or normalized in {"none", "tbd", "todo", "not applicable"}:
                errors.append(f"{path}: {section} must be concrete before state can be ready")
        if not metadata.get("affected_area"):
            errors.append(f"{path}: affected_area must be non-empty before state can be ready")
        return errors

    def _next_sequence(self) -> int:
        highest = 0
        for directory in self._ticket_directories():
            match = re.match(r"^OC-(\d+)-", directory.name)
            if match:
                highest = max(highest, int(match.group(1)))
        return highest + 1

    @staticmethod
    def _required_text(value, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value.strip()

    @classmethod
    def _string_list(cls, values, name: str) -> list[str]:
        if not isinstance(values, list):
            raise ValueError(f"{name} must be a list of non-empty strings")
        return [cls._required_text(value, name) for value in values]

    @staticmethod
    def _single_line(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _next_action(state: str) -> str:
        return {
            "new": "clarify and refine the ticket, then request user review",
            "refined": "wait for explicit user approval before implementation",
            "ready": "begin implementation",
            "in_progress": "continue implementation and focused validation",
            "blocked": "resolve the recorded blocker and document the next action",
        }.get(state, "review the ticket and choose the next action")

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
            ) as stream:
                temporary_path = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()


def ticket_store_from_environment() -> TicketStore:
    workspace_root = Path(__file__).resolve().parents[3]
    ticket_root = os.getenv("OUTDOOR_TICKET_ROOT", str(workspace_root / "tickets"))
    plan_source_dir = os.getenv("OUTDOOR_TICKET_PLAN_SOURCE_DIR")
    return TicketStore(ticket_root, plan_source_dir)