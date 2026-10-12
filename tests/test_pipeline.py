import json

from test_adapters_run import Tone
from test_metrics import case

from rarespeech.io import write_jsonl


def test_one_command_workflow_keeps_evidence_and_unverified_label(tmp_path, monkeypatch):
    import rarespeech.pipeline as pipeline
    import rarespeech.run as run

    monkeypatch.setattr(pipeline.importlib.util, "find_spec", lambda name: True)
    monkeypatch.setattr(run, "load_adapter", lambda config: Tone())
    c = case()

    def transcript_fixture(root, out, *args):
        samples = json.loads((root / "samples.json").read_text())
        write_jsonl(
            out,
            [
                {
                    "id": s["id"],
                    "text": c["text"],
                    "audio_hash": s["audio_hash"],
                    "engine": "unit-test-fixture",
                }
                for s in samples
            ],
        )

    monkeypatch.setattr(pipeline, "transcribe", transcript_fixture)
    report = pipeline.benchmark([c], {"type": "python", "factory": "test:factory"}, tmp_path, "fixture")
    assert report["summary"]["complete"]
    assert report["review_summary"]["verified_accuracy"] is None
    assert (tmp_path / "report/index.html").exists()
    assert (tmp_path / "report/audio/sample--r1.wav").exists()
    assert (tmp_path / "report/badge.svg").exists()
