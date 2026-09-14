import argparse
import os
import shutil
from pathlib import Path


def normalize_plan_name(plan_name: str) -> str:
    value = str(plan_name).strip()
    if not value:
        raise ValueError("plan name must not be empty")
    return value


def next_plan_name(plans_dir: str | Path | None = None) -> str:
    base_dir = Path(plans_dir) if plans_dir is not None else Path(__file__).resolve().parent / "plans"
    base_dir.mkdir(parents=True, exist_ok=True)

    highest = 0
    for child in sorted(base_dir.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        match = child.name.strip()
        if not match.startswith("Sprint Review "):
            continue
        suffix = match[len("Sprint Review ") :]
        if suffix.isdigit():
            highest = max(highest, int(suffix))

    return f"Sprint Review {highest + 1}"


def create_next_plan_dir(repo_root: str | Path | None = None) -> Path:
    root = Path(repo_root) if repo_root is not None else _repo_root()
    plans_dir = _plans_dir(root)
    next_name = next_plan_name(plans_dir)
    new_dir = plans_dir / next_name
    new_dir.mkdir(parents=True, exist_ok=True)
    return new_dir


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _plans_dir(repo_root: str | Path | None = None) -> Path:
    root = Path(repo_root) if repo_root is not None else _repo_root()
    plans_dir = root / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    return plans_dir


def _active_audio_plan() -> Path:
    value = os.getenv("ACTIVE_AUDIO_PLAN")
    if not value:
        raise RuntimeError("ACTIVE_AUDIO_PLAN is not set")
    return Path(value).expanduser()


def export_plan(plan_name: str, repo_root: str | Path | None = None) -> Path:
    name = normalize_plan_name(plan_name)
    source = _plans_dir(repo_root) / name
    if not source.exists():
        raise FileNotFoundError(f"Plan directory not found: {source}")

    destination = _active_audio_plan()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.is_dir():
            shutil.rmtree(destination)
        else:
            destination.unlink()
    shutil.copytree(source, destination)
    return destination


def import_plan(plan_name: str, repo_root: str | Path | None = None) -> Path:
    name = normalize_plan_name(plan_name)
    source = _active_audio_plan()
    if not source.exists():
        raise FileNotFoundError(f"ACTIVE_AUDIO_PLAN does not exist: {source}")

    destination = _plans_dir(repo_root) / name
    if destination.exists():
        if destination.is_dir():
            shutil.rmtree(destination)
        else:
            destination.unlink()
    shutil.copytree(source, destination)
    return destination


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync a local Sprint Review plan with ACTIVE_AUDIO_PLAN.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--export", dest="export_name", metavar="PLAN_NAME", help="Copy a local plan from plans/ into ACTIVE_AUDIO_PLAN.")
    mode.add_argument("--import", dest="import_name", metavar="PLAN_NAME", help="Copy the active iCloud plan back into plans/.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.export_name:
        destination = export_plan(args.export_name)
        print(f"Exported {args.export_name} to {destination}")
        return 0

    destination = import_plan(args.import_name)
    print(f"Imported {args.import_name} from {_active_audio_plan()} to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
