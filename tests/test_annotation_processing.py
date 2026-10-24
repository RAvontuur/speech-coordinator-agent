import json

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
            "text": "First recording. Second recording.",
            "context": {
                "sentence_id": "s0004",
                "sentence": "The source sentence.",
                "source_file": "https://example.com/repo/blob/main/plan.md#oc-004",
            },
        }
    ]
    assert (audio_dir / "annotation-new.stt.txt").read_text(encoding="utf-8") == "Second recording.\n"