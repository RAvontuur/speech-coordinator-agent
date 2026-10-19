import os
import re
import shutil
from pathlib import Path


_PLAN_NAME_PATTERN = re.compile(r"^Sprint Review \d+$")


def normalize_plan_name(plan_name: str) -> str:
    value = str(plan_name).strip()
    if not _PLAN_NAME_PATTERN.fullmatch(value):
        raise ValueError("plan name must match 'Sprint Review N'")
    return value


def next_plan_name(plans_dir: str | Path | None = None) -> str:
    base_dir = Path(plans_dir) if plans_dir is not None else _plans_dir()
    base_dir.mkdir(parents=True, exist_ok=True)

    highest = 0
    for child in base_dir.iterdir():
        if not child.is_dir():
            continue
        match = _PLAN_NAME_PATTERN.fullmatch(child.name.strip())
        if match:
            highest = max(highest, int(child.name.strip().removeprefix("Sprint Review ")))

    return f"Sprint Review {highest + 1}"


def latest_plan_name(plans_dir: str | Path | None = None) -> str | None:
    base_dir = Path(plans_dir) if plans_dir is not None else _plans_dir()
    if not base_dir.is_dir():
        return None
    names = [
        child.name.strip()
        for child in base_dir.iterdir()
        if child.is_dir() and _PLAN_NAME_PATTERN.fullmatch(child.name.strip())
    ]
    if not names:
        return None
    return max(names, key=lambda name: int(name.removeprefix("Sprint Review ")))


def create_next_plan_dir(repo_root: str | Path | None = None) -> Path:
    plans_dir = _plans_dir(repo_root)
    new_dir = plans_dir / next_plan_name(plans_dir)
    new_dir.mkdir()
    return new_dir


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root is not None:
        return Path(repo_root).expanduser().resolve()
    configured_root = os.getenv("OUTDOOR_SPEECH_WORKSPACE_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    return Path(__file__).resolve().parents[3]


def _plans_dir(repo_root: str | Path | None = None) -> Path:
    plans_dir = _repo_root(repo_root) / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    return plans_dir


def _active_audio_plan() -> Path:
    value = os.getenv("ACTIVE_AUDIO_PLAN")
    if not value:
        raise RuntimeError("ACTIVE_AUDIO_PLAN is not set")
    return Path(value).expanduser().resolve()


def _plan_path(plan_name: str, repo_root: str | Path | None = None) -> Path:
    name = normalize_plan_name(plan_name)
    plans_dir = _plans_dir(repo_root)
    path = (plans_dir / name).resolve()
    if path.parent != plans_dir.resolve():
        raise ValueError("plan path must remain within the local plans directory")
    return path


def export_plan(plan_name: str, repo_root: str | Path | None = None) -> Path:
    source = _plan_path(plan_name, repo_root)
    if not source.is_dir():
        raise FileNotFoundError(f"Plan directory not found: {source}")

    destination = _active_audio_plan()
    _require_disjoint_paths(source, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _remove_destination(destination)
    shutil.copytree(source, destination)
    return destination


def import_plan(plan_name: str, repo_root: str | Path | None = None) -> Path:
    source = _active_audio_plan()
    if not source.is_dir():
        raise FileNotFoundError(f"ACTIVE_AUDIO_PLAN does not exist: {source}")

    destination = _plan_path(plan_name, repo_root)
    _require_disjoint_paths(source, destination)
    _remove_destination(destination)
    shutil.copytree(source, destination)
    return destination


def _require_disjoint_paths(source: Path, destination: Path) -> None:
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError("ACTIVE_AUDIO_PLAN must not overlap a local Sprint Review plan path")


def _remove_destination(destination: Path) -> None:
    if destination.is_dir():
        shutil.rmtree(destination)
    elif destination.exists():
        destination.unlink()