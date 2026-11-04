import json
import os
import tempfile
import threading
import subprocess
from pathlib import Path
from urllib.parse import urlsplit


class RepositoryStore:
    _FIELDS = {"name", "get_url", "local_directory", "default_target_branch"}
    _REQUIRED_FIELDS = {"name", "get_url", "local_directory"}

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

    def create_repository(
        self,
        name: str,
        get_url: str,
        local_directory: str,
        default_target_branch: str | None = None,
    ) -> dict:
        repository = self._validated_repository({
            "name": name,
            "get_url": get_url,
            "local_directory": local_directory,
            "default_target_branch": default_target_branch,
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
        missing = cls._REQUIRED_FIELDS - repository.keys()
        if missing:
            raise ValueError(f"missing required repository fields: {', '.join(sorted(missing))}")
        name = cls._required_text(repository["name"], "name")
        get_url = cls._required_text(repository["get_url"], "get_url")
        local_directory = cls._required_text(repository["local_directory"], "local_directory")
        parsed_url = urlsplit(get_url)
        if parsed_url.scheme not in {"http", "https", "ssh", "git"} or not parsed_url.netloc:
            raise ValueError("get_url must be an absolute HTTP(S), SSH, or Git URL")
        default_target_branch = repository.get("default_target_branch")
        if default_target_branch is not None:
            default_target_branch = cls._required_text(default_target_branch, "default_target_branch")
        result = {"name": name, "get_url": get_url, "local_directory": local_directory}
        if default_target_branch is not None:
            result["default_target_branch"] = default_target_branch
        return result

    def create_working_branch(
        self, repository: dict, working_branch: str, target_branch: str
    ) -> dict:
        directory = self._git_directory(repository)
        working_branch = self._validate_branch(directory, working_branch)
        target_branch = self._validate_branch(directory, target_branch)
        if working_branch == target_branch:
            raise ValueError("working branch and target branch must be different")
        self._require_clean_worktree(directory)
        if not self._branch_exists(directory, target_branch):
            raise ValueError(f"target branch does not exist: {target_branch}")
        created = not self._branch_exists(directory, working_branch)
        if not created:
            self._run_git(
                directory, "switch", working_branch, action="switch to existing working branch"
            )
            self._run_git(
                directory, "merge", "--ff-only", target_branch,
                action=f"update {working_branch} from {target_branch}",
            )
        else:
            self._run_git(
                directory, "switch", "--create", working_branch, target_branch,
                action="create working branch",
            )
        return {
            "repository": repository["name"],
            "working_branch": working_branch,
            "target_branch": target_branch,
            "local_directory": str(directory),
            "created": created,
        }

    def finish_working_branch(
        self, repository: dict, working_branch: str, target_branch: str
    ) -> dict:
        directory = self._git_directory(repository)
        working_branch = self._validate_branch(directory, working_branch)
        target_branch = self._validate_branch(directory, target_branch)
        if working_branch == target_branch:
            raise ValueError("working branch and target branch must be different")

        current_branch = self._run_git(
            directory, "branch", "--show-current", action="inspect current branch"
        ).stdout.strip()
        if not self._branch_exists(directory, target_branch):
            raise ValueError(f"target branch does not exist: {target_branch}")

        if current_branch == target_branch:
            status = self._run_git(
                directory, "status", "--porcelain", action="inspect worktree"
            )
            if status.stdout.strip():
                raise ValueError(f"Git worktree is not clean on target branch: {directory}")
            return {
                "repository": repository["name"],
                "working_branch": working_branch,
                "target_branch": target_branch,
                "local_directory": str(directory),
                "committed": False,
                "commit": None,
                "already_finished": True,
            }
        if current_branch != working_branch:
            raise ValueError(
                f"cannot finish ticket branch {working_branch}: "
                f"expected it to be checked out, found {current_branch or 'detached HEAD'}"
            )

        status = self._run_git(
            directory, "status", "--porcelain", action="inspect worktree"
        )
        commit_hash = None
        if status.stdout.strip():
            self._run_git(directory, "add", "--all", action="stage worktree changes")
            staged = subprocess.run(
                ["git", "-C", str(directory), "diff", "--cached", "--quiet"],
                capture_output=True,
                text=True,
                check=False,
            )
            if staged.returncode not in {0, 1}:
                detail = staged.stderr.strip() or staged.stdout.strip() or "unknown Git error"
                raise ValueError(f"could not inspect staged changes: {detail}")
            if staged.returncode == 1:
                self._run_git(
                    directory,
                    "commit",
                    "-m",
                    f"Save changes on {working_branch} after ticket implementation",
                    action=f"commit changes on working branch {working_branch}",
                )
                commit_hash = self._run_git(
                    directory, "rev-parse", "HEAD", action="record commit"
                ).stdout.strip()

        self._run_git(directory, "switch", target_branch, action="switch to target branch")
        return {
            "repository": repository["name"],
            "working_branch": working_branch,
            "target_branch": target_branch,
            "local_directory": str(directory),
            "committed": commit_hash is not None,
            "commit": commit_hash,
        }

    def merge_working_branch(
        self, repository: dict, working_branch: str, target_branch: str
    ) -> dict:
        directory = self._git_directory(repository)
        working_branch = self._validate_branch(directory, working_branch)
        target_branch = self._validate_branch(directory, target_branch)
        if working_branch == target_branch:
            raise ValueError("working branch and target branch must be different")
        self._require_clean_worktree(directory)
        if not self._branch_exists(directory, working_branch):
            raise ValueError(f"working branch does not exist: {working_branch}")
        if not self._branch_exists(directory, target_branch):
            raise ValueError(f"target branch does not exist: {target_branch}")
        self._run_git(directory, "switch", target_branch, action="switch to target branch")
        try:
            self._run_git(
                directory, "merge", "--no-edit", working_branch,
                action=f"merge {working_branch} into {target_branch}",
            )
        except ValueError as error:
            # Leave the selected repository out of a conflicted merge state.
            subprocess.run(
                ["git", "-C", str(directory), "merge", "--abort"],
                capture_output=True,
                text=True,
                check=False,
            )
            raise ValueError(
                f"merge failed for repository {repository['name']} "
                f"({working_branch} -> {target_branch}): {error}"
            ) from error
        return {
            "repository": repository["name"],
            "working_branch": working_branch,
            "target_branch": target_branch,
            "local_directory": str(directory),
        }

    @staticmethod
    def _git_directory(repository: dict) -> Path:
        directory = Path(repository["local_directory"]).expanduser().resolve()
        if not directory.is_dir():
            raise ValueError(f"registered repository directory does not exist: {directory}")
        result = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise ValueError(
                f"registered directory is not a Git repository ({repository['name']}): "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        return Path(result.stdout.strip()).resolve()

    @classmethod
    def _validate_branch(cls, directory: Path, branch: str) -> str:
        branch = cls._required_text(branch, "branch")
        result = subprocess.run(
            ["git", "-C", str(directory), "check-ref-format", "--branch", branch],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise ValueError(f"invalid Git branch name: {branch}")
        return branch

    @classmethod
    def _branch_exists(cls, directory: Path, branch: str) -> bool:
        result = subprocess.run(
            ["git", "-C", str(directory), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    @classmethod
    def _require_clean_worktree(cls, directory: Path) -> None:
        result = cls._run_git(directory, "status", "--porcelain", action="inspect worktree")
        if result.stdout.strip():
            raise ValueError(f"Git worktree is not clean: {directory}")

    @staticmethod
    def _run_git(directory: Path, *arguments: str, action: str) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["git", "-C", str(directory), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
            raise ValueError(f"could not {action}: {detail}")
        return result

    @staticmethod
    def _required_text(value, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
        return value.strip()