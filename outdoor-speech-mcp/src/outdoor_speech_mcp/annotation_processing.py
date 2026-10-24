import json
from pathlib import Path

from .path_utils import normalize_path


def process_plan_annotations(plan_path, speech_service):
    """Transcribe a plan's recordings and return each annotation with sentence context."""
    plan_dir = normalize_path(plan_path)
    if not plan_dir.is_dir():
        raise FileNotFoundError(f"Plan directory not found: {plan_dir}")

    annotations_path = plan_dir / "annotations.json"
    manifest_path = plan_dir / "plan.timing.json"
    if not annotations_path.is_file():
        raise FileNotFoundError(f"Annotation file not found: {annotations_path}")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Timing manifest not found: {manifest_path}")

    annotation_document = json.loads(annotations_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sentences = {
        sentence["sentence_id"]: sentence
        for sentence in manifest.get("sentences", [])
        if sentence.get("sentence_id")
    }

    processed = []
    for annotation in annotation_document.get("annotations", []):
        transcripts = []
        for recording in annotation.get("audio_files", []):
            audio_path = _recording_path(plan_dir, recording["audio_file"])
            transcript_path = audio_path.with_name(f"{audio_path.stem}.stt.txt")
            if transcript_path.is_file():
                transcript = transcript_path.read_text(encoding="utf-8").strip()
            else:
                transcript = speech_service.speech_to_text_file(audio_path).strip()
                transcript_path.write_text(transcript + "\n", encoding="utf-8")
            if transcript:
                transcripts.append(transcript)

        sentence_id = annotation.get("sentence_id")
        sentence = sentences.get(sentence_id)
        processed.append(
            {
                "annotation_id": annotation.get("annotation_id"),
                "text": " ".join(transcripts),
                "context": {
                    "sentence_id": sentence_id,
                    "sentence": sentence.get("text") if sentence else None,
                    "source_file": sentence.get("source_filename") if sentence else None,
                },
            }
        )
    return processed


def _recording_path(plan_dir: Path, audio_file: str) -> Path:
    audio_path = Path(audio_file).expanduser()
    if not audio_path.is_absolute():
        audio_path = plan_dir / audio_path
    audio_path = audio_path.resolve()
    if audio_path != plan_dir and plan_dir not in audio_path.parents:
        raise ValueError(f"Annotation audio path must remain within the plan directory: {audio_file}")
    if not audio_path.is_file():
        raise FileNotFoundError(f"Annotation audio file not found: {audio_path}")
    return audio_path