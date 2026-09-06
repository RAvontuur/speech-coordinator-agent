import hashlib
import json
import re
import shutil
import tempfile
import uuid
import wave
from pathlib import Path


def markdown_to_tts_text(markdown: str) -> str:
    footnotes = {
        match.group(1): match.group(2).strip()
        for match in re.finditer(r"^\[\^([^\]]+)\]:\s*(.+)$", markdown, re.MULTILINE)
    }
    text = re.sub(r"^\[\^[^\]]+\]:.*(?:\n|$)", "", markdown, flags=re.MULTILINE)
    text = re.sub(r"```[^\n]*\n.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(
        r"\[\^([^\]]+)\]",
        lambda match: f"Specifically, {footnotes.get(match.group(1), '')}",
        text,
    )
    text = re.sub(r"[*_`]+", "", text)
    text = re.sub(r"^\s*(?:---+|\*\*\*+|___+)\s*$", "Moving on.", text, flags=re.MULTILINE)
    text = re.sub(r"\n{2,}", "\n\n", text)

    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = re.sub(r"\s+", " ", paragraph).strip()
        if not paragraph:
            continue
        if paragraph[-1] not in ".!?":
            paragraph += "."
        paragraphs.append(paragraph)
    return "\n\n".join(paragraphs) + ("\n" if paragraphs else "")


def sentence_records(text: str, source_filename: str):
    records = []
    index = 0
    for match in re.finditer(r".*?(?:[.!?](?=\s|$)|$)", text, re.DOTALL):
        value = match.group(0)
        stripped = value.strip()
        if not stripped:
            continue
        start = match.start() + len(value) - len(value.lstrip())
        end = start + len(stripped)
        records.append({
            "sentence_id": f"s{index:04d}",
            "index": index,
            "text": stripped,
            "start_char": start,
            "end_char": end,
            "source_filename": source_filename,
        })
        index += 1
    return records


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _append_wav(output: wave.Wave_write, segment: Path):
    with wave.open(str(segment), "rb") as source:
        params = source.getparams()
        frames = source.readframes(source.getnframes())
    if output.getnframes() == 0:
        output.setnchannels(params.nchannels)
        output.setsampwidth(params.sampwidth)
        output.setframerate(params.framerate)
        output.setcomptype(params.comptype, params.compname)
    elif (output.getnchannels(), output.getsampwidth(), output.getframerate()) != (
        params.nchannels,
        params.sampwidth,
        params.framerate,
    ):
        raise ValueError("TTS segments have incompatible WAV formats")
    start_sample = output.getnframes()
    output.writeframes(frames)
    return start_sample, output.getnframes(), params.framerate, params.nchannels


def create_audio_plan(source_path: str, speech_service, output_dir: str | None = None) -> dict:
    source = Path(source_path).expanduser().resolve()
    source_text = source.read_text(encoding="utf-8")
    tts_text = markdown_to_tts_text(source_text)
    if not tts_text.strip():
        raise ValueError("file has no speakable text")

    plan_id = source.stem[:-7] if source.stem.endswith(".prompt") else source.stem
    package = Path(output_dir).expanduser().resolve() if output_dir else source.parent / plan_id
    package.mkdir(parents=True, exist_ok=True)
    audio_dir = package / "audio"
    audio_dir.mkdir(exist_ok=True)
    text_path = package / "plan.tts.txt"
    audio_path = package / "plan.wav"
    manifest_path = package / "plan.timing.json"
    annotations_path = package / "annotations.json"
    text_path.write_text(tts_text, encoding="utf-8")
    records = sentence_records(tts_text, source.name)
    generation = uuid.uuid4().hex

    with tempfile.TemporaryDirectory(dir=str(package)) as temp_dir:
        temp_audio = Path(temp_dir) / "plan.wav"
        segment_dir = Path(temp_dir) / "segments"
        segment_dir.mkdir()
        with wave.open(str(temp_audio), "wb") as output:
            sample_rate = channels = 0
            for record in records:
                segment_path = segment_dir / f"{record['index']:04d}.wav"
                speech_service.text_to_speech_file(record["text"], str(segment_path))
                start, end, sample_rate, channels = _append_wav(output, segment_path)
                record["start_sample"] = start
                record["end_sample"] = end
                record["start_seconds"] = start / sample_rate
                record["end_seconds"] = end / sample_rate
        shutil.copyfile(temp_audio, audio_path)

    manifest = {
        "schema_version": 1,
        "plan_id": plan_id,
        "audio_generation": generation,
        "source_file": source.name,
        "text_file": "plan.tts.txt",
        "audio_file": "plan.wav",
        "text_sha256": _sha256(text_path),
        "audio_sha256": _sha256(audio_path),
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "duration_seconds": records[-1]["end_seconds"],
        "sentences": records,
    }
    annotations = {
        "schema_version": 1,
        "plan_id": plan_id,
        "audio_generation": generation,
        "manifest_file": "plan.timing.json",
        "annotations": [],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    annotations_path.write_text(json.dumps(annotations, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(source, package / source.name)
    return {
        "package_dir": str(package),
        "source_file": str(package / source.name),
        "text_file": str(text_path),
        "audio_file": str(audio_path),
        "manifest_file": str(manifest_path),
        "annotations_file": str(annotations_path),
        "manifest": manifest,
    }