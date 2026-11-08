import json
from pathlib import Path

from outdoor_speech_mcp.annotation_processing import process_plan_annotations


def test_process_plan_annotations_combines_transcripts_with_sentence_context(tmp_path):
    plan_dir = tmp_path / "plan"
    audio_dir = plan_dir / "audio"
    audio_dir.mkdir(parents=True)
    cached_audio = audio_dir / "annotation-cached.m4a"
    new_audio = audio_dir / "annotation-new.m4a"
    cached_audio.write_bytes(b"cached")
    new_audio.write_bytes(b"new")
    (audio_dir / "annotation-cached.stt.txt").write_text("First recording.\n", encoding="utf-8")

    (plan_dir / "annotations.json").write_text(
        json.dumps(
            {
                "annotations": [
                    {
                        "annotation_id": "a-1",
                        "sentence_id": "s0004",
                        "audio_files": [
                            {"audio_file": "audio/annotation-cached.m4a"},
                            {"audio_file": "audio/annotation-new.m4a"},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (plan_dir / "plan.timing.json").write_text(
        json.dumps(
            {
                "sentences": [
                    {
                        "sentence_id": "s0004",
                        "text": "The source sentence.",
                        "source_filename": "https://example.com/repo/blob/main/plan.md#oc-004",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    class SpeechService:
        def speech_to_text_file(self, audio_path):
            assert audio_path == new_audio.resolve()
            return "Second recording."

    assert process_plan_annotations(plan_dir, SpeechService()) == [
        {
            "annotation_id": "a-1",
            "annotation_number": 1,
            "anchor": "plan-1",
            "annotation_url": "audioannotation://annotation#plan-1",
            "text": "First recording. Second recording.",
            "context": {
                "sentence_id": "s0004",
                "sentence": "The source sentence.",
                "source_file": "https://example.com/repo/blob/main/plan.md#oc-004",
            },
        }
    ]
    assert (audio_dir / "annotation-new.stt.txt").read_text(encoding="utf-8") == "Second recording.\n"
    saved = json.loads((plan_dir / "annotations.json").read_text(encoding="utf-8"))
    assert saved["annotations"][0]["annotation_number"] == 1
    assert saved["annotations"][0]["anchor"] == "plan-1"


def test_process_plan_annotations_preserves_numbers_and_allocates_next_per_plan(tmp_path):
    results = []
    for plan_name, numbers in (("Sprint Review 15", [8, 2]), ("Sprint Review 16", [1])):
        plan_dir = tmp_path / plan_name
        audio_dir = plan_dir / "audio"
        audio_dir.mkdir(parents=True)
        annotations = []
        for index, number in enumerate(numbers):
            audio_name = f"annotation-{index}.m4a"
            (audio_dir / audio_name).write_bytes(b"audio")
            annotations.append(
                {
                    "annotation_id": f"{plan_name}-{index}",
                    "annotation_number": number,
                    "audio_files": [{"audio_file": f"audio/{audio_name}"}],
                }
            )
        annotations.append(
            {
                "annotation_id": f"{plan_name}-new",
                "audio_files": [],
            }
        )
        (plan_dir / "annotations.json").write_text(
            json.dumps({"plan_id": plan_name, "annotations": annotations}), encoding="utf-8"
        )
        (plan_dir / "plan.timing.json").write_text('{"sentences": []}', encoding="utf-8")
        for annotation in annotations[:-1]:
            (audio_dir / f"{Path(annotation['audio_files'][0]['audio_file']).stem}.stt.txt").write_text(
                "Transcript", encoding="utf-8"
            )

        results.append(process_plan_annotations(plan_dir, object()))

    assert [item["anchor"] for item in results[0]] == [
        "Sprint Review 15-8",
        "Sprint Review 15-2",
        "Sprint Review 15-9",
    ]
    assert [item["anchor"] for item in results[1]] == ["Sprint Review 16-1", "Sprint Review 16-2"]
    assert results[0][0]["annotation_url"] == "audioannotation://annotation#Sprint%20Review%2015-8"