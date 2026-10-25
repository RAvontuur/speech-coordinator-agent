import json
import os
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlsplit


class RepositoryStore:
    _FIELDS = {"name", "get_url", "local_directory"}

    def __init__(self, storage_directory: str | Path):
        self.storage_directory = Path(storage_directory).expanduser().resolve()
        self.registry_path = self.storage_directory / "repositories.json"
        self._lock = threading.RLock()

    def list_repositories(self) -> list[dict]:
        with self._lock:
            return list(self._read().values())

    def get_repository(self, name: str) -> dict:
        name = self._required_text(name, "name")
        with self._lock:
            try:
                return self._read()[name]
            except KeyError:
                raise KeyError(f"repository not found: {name}") from None

    def create_repository(self, name: str, get_url: str, local_directory: str) -> dict:
        repository = self._validated_repository({
            "name": name,
            "get_url": get_url,
            "local_directory": local_directory,
        })
        with self._lock:
            repositories = self._read()
            if repository["name"] in repositories:
                raise ValueError(f"repository already exists: {repository['name']}")
            repositories[repository["name"]] = repository
            self._write(repositories)
        return repository

    def update_repository(self, name: str, updates: dict) -> dict:
        name = self._required_text(name, "name")
        if not isinstance(updates, dict) or not updates:
            raise ValueError("updates must be a non-empty object")
        unknown_fields = set(updates) - self._FIELDS
        if unknown_fields:
            raise ValueError(f"unknown repository fields: {', '.join(sorted(unknown_fields))}")

        with self._lock:
            repositories = self._read()
            if name not in repositories:
                raise KeyError(f"repository not found: {name}")
            repository = self._validated_repository({**repositories[name], **updates})
            new_name = repository["name"]
            if new_name != name and new_name in repositories:
                raise ValueError(f"repository already exists: {new_name}")
            del repositories[name]
            repositories[new_name] = repository
            self._write(repositories)
        return repository

    def delete_repository(self, name: str) -> dict:
        name = self._required_text(name, "name")
        with self._lock:
            repositories = self._read()
            try:
                repository = repositories.pop(name)
            except KeyError:
                raise KeyError(f"repository not found: {name}") from None
            self._write(repositories)
        return repository

    def _read(self) -> dict[str, dict]:
        if not self.registry_path.exists():
            return {}
        if self.registry_path.is_symlink():
            raise ValueError("repository registry must not be a symbolic link")
        try:
            records = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"repository registry could not be read: {error}") from error
        if not isinstance(records, list):
            raise ValueError("repository registry must contain a list")

        repositories = {}
        for record in records:
            repository = self._validated_repository(record)
            if repository["name"] in repositories:
                raise ValueError(f"duplicate repository in registry: {repository['name']}")
            repositories[repository["name"]] = repository
        return repositories

    def _write(self, repositories: dict[str, dict]) -> None:
        self.storage_directory.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.storage_directory,
                prefix=".repositories.",
                delete=False,
            ) as stream:
                temporary_path = Path(stream.name)
                json.dump(list(repositories.values()), stream, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self.registry_path)
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

    @classmethod
    def _validated_repository(cls, repository) -> dict:
        if not isinstance(repository, dict):
            raise ValueError("repository registration must be an object")
        missing = cls._FIELDS - repository.keys()
        if missing:
            raise ValueError(f"missing required repository fields: {', '.join(sorted(missing))}")
        name = cls._required_text(repository["name"], "name")
        get_url = cls._required_text(repository["get_url"], "get_url")
        local_directory = cls._required_text(repository["local_directory"], "local_directory")
        parsed_url = urlsplit(get_url)
        if parsed_url.scheme not in {"http", "https", "ssh", "git"} or not parsed_url.netloc:
            raise ValueError("get_url must be an absolute HTTP(S), SSH, or Git URL")
        return {"name": name, "get_url": get_url, "local_directory": local_directory}

    @staticmethod
    def _required_text(value, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
        return value.strip()