import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import uuid
import wave
from pathlib import Path
from urllib.parse import quote, urlsplit

from .path_utils import normalize_path

logger = logging.getLogger(__name__)
_MARKDOWN_ANCHOR_PATTERN = re.compile(
    r"<a\s+(?:id|name)=[\"']([^\"']+)[\"']\s*>\s*</a\s*>", re.IGNORECASE
)


def sentence_records(
    text: str,
    source_filename: str,
    index_offset: int = 0,
    char_offset: int = 0,
):
    records = []
    for local_index, match in enumerate(re.finditer(r".*?(?:[.!?](?=\s|$)|$)", text, re.DOTALL)):
        value = match.group(0)
        stripped = value.strip()
        if stripped:
            index = index_offset + len(records)
            start = char_offset + match.start() + len(value) - len(value.lstrip())
            records.append({"sentence_id": f"s{index:04d}", "index": index, "text": stripped, "start_char": start, "end_char": start + len(stripped), "source_filename": source_filename})
    return records


def markdown_anchor_segments(content: str) -> list[tuple[str | None, str]]:
    anchors = list(_MARKDOWN_ANCHOR_PATTERN.finditer(content))
    if not anchors:
        return [(None, content)]

    segments = []
    previous_end = 0
    current_anchor = None
    for match in anchors:
        text = content[previous_end : match.start()]
        if text.strip():
            segments.append((current_anchor, text))
        current_anchor = match.group(1)
        previous_end = match.end()
    trailing_text = content[previous_end:]
    if trailing_text.strip():
        segments.append((current_anchor, trailing_text))
    return segments


def git_source_url(source_file: str | Path, bookmark: str | None = None) -> str:
    source = Path(source_file).expanduser().resolve()
    git_root = _git_root(source)
    if git_root is None:
        repo_name = source.parent.name or "repository"
        relative_path = source.name
        base_url = f"git://{quote(repo_name, safe='')}/{quote(relative_path, safe='/')}"
    else:
        relative_path = source.relative_to(git_root).as_posix()
        remote = subprocess.run(
            ["git", "-C", str(git_root), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
        )
        if remote.returncode != 0 or not remote.stdout.strip():
            base_url = f"git://{quote(git_root.name, safe='')}/{quote(relative_path, safe='/')}"
        else:
            remote_url = _remote_web_url(remote.stdout.strip())
            branch = subprocess.run(
                ["git", "-C", str(git_root), "symbolic-ref", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )
            revision = branch.stdout.strip() if branch.returncode == 0 else "HEAD"
            host = urlsplit(remote_url).hostname or ""
            encoded_revision = quote(revision, safe="/")
            encoded_path = quote(relative_path, safe="/")
            if "gitlab" in host.lower():
                route = "-/blob"
            elif "bitbucket" in host.lower():
                route = "src"
            else:
                route = "blob"
            base_url = f"{remote_url}/{route}/{encoded_revision}/{encoded_path}"

    if bookmark:
        return f"{base_url}#{quote(bookmark, safe='-._~')}"
    return base_url


def _remote_web_url(remote: str) -> str:
    if remote.startswith("git@"):
        host, path = remote[4:].split(":", maxsplit=1)
    else:
        parsed = urlsplit(remote)
        host = parsed.hostname or ""
        path = parsed.path.lstrip("/")
    path = path.removesuffix(".git").strip("/")
    return f"https://{host}/{path}"


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _append_wav(output, segment):
    with wave.open(str(segment), "rb") as source:
        params = source.getparams()
        frames = source.readframes(source.getnframes())
    if output.getnframes() == 0:
        output.setnchannels(params.nchannels)
        output.setsampwidth(params.sampwidth)
        output.setframerate(params.framerate)
        output.setcomptype(params.comptype, params.compname)
    elif (output.getnchannels(), output.getsampwidth(), output.getframerate()) != (params.nchannels, params.sampwidth, params.framerate):
        raise ValueError("TTS segments have incompatible WAV formats")
    start_sample = output.getnframes()
    output.writeframes(frames)
    return start_sample, output.getnframes(), params.framerate, params.nchannels


def _git_root(path):
    working_dir = path if path.is_dir() else path.parent
    result = subprocess.run(
        ["git", "-C", str(working_dir), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else None


def _ignored_paths(paths, git_root):
    if not git_root or not paths:
        return set()
    inputs = {}
    for path in paths:
        relative = path.relative_to(git_root).as_posix()
        inputs[relative.rstrip("/")] = path
    result = subprocess.run(
        ["git", "-C", str(git_root), "check-ignore", "--no-index", "-z", "--stdin"],
        input="\0".join(
            f"{path.relative_to(git_root).as_posix()}{'/' if path.is_dir() else ''}"
            for path in paths
        )
        + "\0",
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        return set()
    return {
        inputs[name.rstrip("/")]
        for name in result.stdout.split("\0")
        if name.rstrip("/") in inputs
    }


def _source_files(source):
    if source.is_file():
        ignored = _ignored_paths([source], _git_root(source))
        candidates = [] if source in ignored else [source]
    elif source.is_dir():
        candidates = []
        git_root = _git_root(source)
        for current_dir, directory_names, filenames in os.walk(source, topdown=True):
            current_path = Path(current_dir)
            directory_names[:] = sorted(name for name in directory_names if name != ".git")
            directories = [current_path / name for name in directory_names]
            files = [current_path / name for name in filenames]
            ignored = _ignored_paths(directories + files, git_root)
            directory_names[:] = [name for name in directory_names if current_path / name not in ignored]
            candidates.extend(path for path in files if path not in ignored)
    else:
        raise FileNotFoundError(f"file or directory not found: {source}")
    return sorted(candidates, key=lambda path: path.as_posix().lower())


def create_audio_plan(source_path, speech_service, text_transformer, output_dir=None):
    source = normalize_path(source_path)
    source_files = _source_files(source)
    if not source_files:
        raise ValueError("source contains no files after applying .gitignore rules")
    transformed_sources = []
    for source_file in source_files:
        logger.info("Transforming source file: %s", source_file)
        source_content = source_file.read_text(encoding="utf-8")
        segments = markdown_anchor_segments(source_content) if source_file.suffix.lower() == ".md" else [(None, source_content)]
        for bookmark, segment in segments:
            transformed = (
                text_transformer.transform_file_to_tts_text(source_file, segment)
                if segment.strip()
                else "This file is empty."
            )
            transformed_sources.append((transformed.strip(), git_source_url(source_file, bookmark)))
    tts_text = "\n\n\n".join(text for text, _ in transformed_sources) + "\n"
    if not tts_text.strip():
        raise ValueError("file has no speakable text")
    plan_id = source.stem[:-7] if source.stem.endswith(".prompt") else source.stem
    package = normalize_path(output_dir) if output_dir else source.parent / plan_id
    logger.info("Creating audio plan package: %s", package)
    package.mkdir(parents=True, exist_ok=True)
    (package / "audio").mkdir(exist_ok=True)
    text_path, audio_path = package / "plan.tts.txt", package / "plan.wav"
    manifest_path, annotations_path = package / "plan.timing.json", package / "annotations.json"
    text_path.write_text(tts_text, encoding="utf-8")
    records = []
    char_offset = 0
    for section_index, (text, source_filename) in enumerate(transformed_sources):
        if section_index:
            char_offset += 3
        records.extend(
            sentence_records(
                text,
                source_filename,
                index_offset=len(records),
                char_offset=char_offset,
            )
        )
        char_offset += len(text)
    generation = uuid.uuid4().hex
    with tempfile.TemporaryDirectory(dir=str(package)) as temp_dir:
        temp_audio, segment_dir = Path(temp_dir) / "plan.wav", Path(temp_dir) / "segments"
        segment_dir.mkdir()
        with wave.open(str(temp_audio), "wb") as output:
            for record in records:
                logger.info("Synthesizing TTS for sentence %s: %s", record["sentence_id"], record["text"])
                segment_path = segment_dir / f"{record['index']:04d}.wav"
                speech_service.text_to_speech_file(record["text"], str(segment_path))
                start, end, sample_rate, channels = _append_wav(output, segment_path)
                record.update(start_sample=start, end_sample=end, start_seconds=start / sample_rate, end_seconds=end / sample_rate)
        shutil.copyfile(temp_audio, audio_path)
    manifest = {"schema_version": 1, "plan_id": plan_id, "audio_generation": generation, "source_file": str(source), "text_file": "plan.tts.txt", "audio_file": "plan.wav", "text_sha256": _sha256(text_path), "audio_sha256": _sha256(audio_path), "sample_rate_hz": sample_rate, "channels": channels, "duration_seconds": records[-1]["end_seconds"], "sentences": records}
    annotations = {"schema_version": 1, "plan_id": plan_id, "audio_generation": generation, "manifest_file": "plan.timing.json", "annotations": []}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    annotations_path.write_text(json.dumps(annotations, indent=2) + "\n", encoding="utf-8")
    return {"package_dir": str(package), "source_file": str(source), "text_file": str(text_path), "audio_file": str(audio_path), "manifest_file": str(manifest_path), "annotations_file": str(annotations_path), "manifest": manifest}