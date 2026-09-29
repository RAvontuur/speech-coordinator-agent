import wave
from pathlib import Path

from outdoor_speech_mcp.audio_plan import create_audio_plan
from plan_sync import create_next_plan_dir, export_plan, next_plan_name


def test_next_plan_name_increments_from_existing_dirs(tmp_path):
    plans_dir = tmp_path / "plans"
    plans_dir.mkdir()
    (plans_dir / "Sprint Review 1").mkdir()
    (plans_dir / "Sprint Review 2").mkdir()

    assert next_plan_name(plans_dir) == "Sprint Review 3"


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
        def transform_markdown_to_tts_text(self, markdown):
            assert markdown == "# Sample plan\n\nThis is a test sentence."
            return "A transformed, listenable sentence.\n"

    speech = DummySpeechService()
    result = create_audio_plan(
        str(source), speech, DummyTextTransformer(), output_dir=str(plan_dir)
    )

    assert result["package_dir"] == str(plan_dir)
    assert (plan_dir / "plan.wav").exists()
    assert (plan_dir / "plan.tts.txt").exists()
    assert (plan_dir / "plan.tts.txt").read_text(encoding="utf-8") == "A transformed, listenable sentence.\n"
    assert speech.synthesized_text == ["A transformed, listenable sentence."]
