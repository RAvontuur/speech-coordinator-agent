import wave
from pathlib import Path

import pytest

from outdoor_speech_mcp.audio_plan import create_audio_plan
from outdoor_speech_mcp.plan_sync import (
    create_next_plan_dir,
    export_plan,
    import_plan,
    latest_plan_name,
    next_plan_name,
)


def test_next_plan_name_increments_from_existing_dirs(tmp_path):
    plans_dir = tmp_path / "plans"
    plans_dir.mkdir()
    (plans_dir / "Sprint Review 1").mkdir()
    (plans_dir / "Sprint Review 2").mkdir()

    assert next_plan_name(plans_dir) == "Sprint Review 3"


def test_latest_plan_name_returns_highest_existing_number(tmp_path):
    plans_dir = tmp_path / "plans"
    plans_dir.mkdir()
    (plans_dir / "Sprint Review 2").mkdir()
    (plans_dir / "Sprint Review 11").mkdir()
    (plans_dir / "Sprint Review notes").mkdir()

    assert latest_plan_name(plans_dir) == "Sprint Review 11"
    assert latest_plan_name(tmp_path / "empty") is None


def test_create_next_plan_dir_creates_the_next_numbered_directory(tmp_path):
    repo_root = tmp_path
    plans_dir = repo_root / "plans"
    (plans_dir / "Sprint Review 1").mkdir(parents=True)

    next_dir = create_next_plan_dir(repo_root)

    assert next_dir == plans_dir / "Sprint Review 2"
    assert next_dir.is_dir()


def test_export_plan_copies_local_dir_to_active_audio_plan(tmp_path, monkeypatch):
    repo_root = tmp_path
    plans_dir = repo_root / "plans"
    source_dir = plans_dir / "Sprint Review 1"
    source_dir.mkdir(parents=True)
    (source_dir / "plan.tts.txt").write_text("example", encoding="utf-8")

    destination = repo_root / "icloud-plan"
    monkeypatch.setenv("ACTIVE_AUDIO_PLAN", str(destination))

    exported = export_plan("Sprint Review 1", repo_root=repo_root)

    assert exported == destination
    assert destination.exists()
    assert (destination / "plan.tts.txt").read_text(encoding="utf-8") == "example"


def test_import_plan_copies_active_audio_plan_to_local_dir(tmp_path, monkeypatch):
    repo_root = tmp_path / "repository"
    source = tmp_path / "active-plan"
    source.mkdir()
    (source / "annotations.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("ACTIVE_AUDIO_PLAN", str(source))

    imported = import_plan("Sprint Review 4", repo_root=repo_root)

    assert imported == repo_root / "plans" / "Sprint Review 4"
    assert (imported / "annotations.json").read_text(encoding="utf-8") == "{}"


def test_plan_name_rejects_path_traversal(tmp_path):
    from outdoor_speech_mcp.plan_sync import export_plan

    with pytest.raises(ValueError, match="Sprint Review N"):
        export_plan("../outside", repo_root=tmp_path)


def test_export_rejects_destination_that_contains_local_plans(tmp_path, monkeypatch):
    source = tmp_path / "plans" / "Sprint Review 1"
    source.mkdir(parents=True)
    (source / "plan.md").write_text("keep this source", encoding="utf-8")
    monkeypatch.setenv("ACTIVE_AUDIO_PLAN", str(tmp_path / "plans"))

    with pytest.raises(ValueError, match="must not overlap"):
        export_plan("Sprint Review 1", repo_root=tmp_path)

    assert (source / "plan.md").read_text(encoding="utf-8") == "keep this source"


def test_import_rejects_destination_inside_active_plan(tmp_path, monkeypatch):
    source = tmp_path / "active-plan"
    source.mkdir()
    (source / "annotations.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("ACTIVE_AUDIO_PLAN", str(source))

    with pytest.raises(ValueError, match="must not overlap"):
        import_plan("Sprint Review 1", repo_root=source)

    assert (source / "annotations.json").read_text(encoding="utf-8") == "{}"


def test_create_audio_plan_handles_source_in_output_dir(tmp_path):
    plan_dir = tmp_path / "plans" / "Sprint Review 2"
    plan_dir.mkdir(parents=True)
    source = plan_dir / "plan.md"
    source.write_text("# Sample plan\n\nThis is a test sentence.", encoding="utf-8")

    class DummySpeechService:
        synthesized_text = []

        def text_to_speech_file(self, text, output_path):
            self.synthesized_text.append(text)
            with wave.open(output_path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(8000)
                wav.writeframes(b"\x00\x00" * 4)

    class DummyTextTransformer:
        def transform_file_to_tts_text(self, filename, content):
            assert Path(filename) == source
            assert content == "# Sample plan\n\nThis is a test sentence."
            return "A transformed, listenable sentence.\n"

    speech = DummySpeechService()
    result = create_audio_plan(
        str(source), speech, DummyTextTransformer(), output_dir=str(plan_dir)
    )

    assert result["package_dir"] == str(plan_dir)
    assert result["source_file"] == str(source)
    assert (plan_dir / "plan.wav").exists()
    assert (plan_dir / "plan.tts.txt").exists()
    assert (plan_dir / "plan.tts.txt").read_text(encoding="utf-8") == (
        f"source file : {source}\n\nA transformed, listenable sentence.\n"
    )
    assert speech.synthesized_text == [
        f"source file : {source}\n\nA transformed, listenable sentence."
    ]


def test_create_audio_plan_transforms_directory_and_skips_ignored_files(tmp_path):
    repository = tmp_path / "repository"
    source_dir = repository / "sources"
    (source_dir / "nested").mkdir(parents=True)
    (source_dir / "nested" / "first.md").write_text("First content", encoding="utf-8")
    (source_dir / "second.txt").write_text("Second content", encoding="utf-8")
    (source_dir / "ignored.md").write_text("Ignore this", encoding="utf-8")
    (repository / ".gitignore").write_text("sources/ignored.md\n", encoding="utf-8")
    import subprocess

    subprocess.run(["git", "init", "-q", str(repository)], check=True)

    class DummySpeechService:
        synthesized_text = []

        def text_to_speech_file(self, text, output_path):
            self.synthesized_text.append(text)
            with wave.open(output_path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(8000)
                wav.writeframes(b"\x00\x00" * 4)

    class DummyTextTransformer:
        def __init__(self):
            self.files = []

        def transform_file_to_tts_text(self, filename, content):
            self.files.append((Path(filename), content))
            return f"Transformed {content}\n"

    speech = DummySpeechService()
    transformer = DummyTextTransformer()
    result = create_audio_plan(str(source_dir), speech, transformer)

    first = source_dir / "nested" / "first.md"
    second = source_dir / "second.txt"
    assert [file for file, _ in transformer.files] == [first, second]
    expected = (
        f"source file : {first}\n\nTransformed First content\n\n\n"
        f"source file : {second}\n\nTransformed Second content\n"
    )
    assert Path(result["text_file"]).read_text(encoding="utf-8") == expected


def test_create_audio_plan_includes_message_for_empty_file(tmp_path):
    source = tmp_path / "empty.md"
    source.touch()

    class DummySpeechService:
        synthesized_text = []

        def text_to_speech_file(self, text, output_path):
            self.synthesized_text.append(text)
            with wave.open(output_path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(8000)
                wav.writeframes(b"\x00\x00" * 4)

    class DummyTextTransformer:
        def transform_file_to_tts_text(self, filename, content):
            raise AssertionError("empty files should not be transformed")

    speech = DummySpeechService()
    result = create_audio_plan(str(source), speech, DummyTextTransformer())
    expected = f"source file : {source.resolve()}\n\nThis file is empty."

    assert Path(result["text_file"]).read_text(encoding="utf-8") == expected + "\n"
    assert speech.synthesized_text == [expected]
