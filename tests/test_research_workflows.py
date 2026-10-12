import json
from collections import Counter

import pytest

from rarespeech.corpus import load_cases
from rarespeech.datasets import dataset_path, track_identity
from rarespeech.evaluate import evaluate
from rarespeech.io import file_hash
from rarespeech.report import build_report
from rarespeech.study import build_study, unblind
from rarespeech.submission import submission


def test_packaged_core_and_stress_design():
    core = load_cases(dataset_path("core"))
    stress = load_cases(dataset_path("stress"))
    assert len(core) == 128 and len(stress) == 192
    assert len({c["family_id"] for c in core}) == 64
    assert len({c["cluster_id"] for c in core}) == 63
    assert Counter(c["variant"] for c in core) == {"isolated": 64, "dense": 64}
    assert Counter(c["variant"] for c in stress) == {"confusable": 64, "extended": 64, "control": 64}
    assert all(len(c["targets"]) == 1 for c in core)
    assert sum(c["variant"] == "control" for c in stress) == 64
    assert all(len(c["targets"]) == 1 for c in stress if c["variant"] == "control")
    assert all(len(c["targets"]) == 3 for c in stress if c["variant"] in {"confusable", "extended"})
    assert track_identity(core)["canonical"]
    assert not track_identity(core[:8])["canonical"]


def test_study_hides_model_and_asr_and_preserves_audio_binding(tmp_path):
    import wave

    root = tmp_path / "report"
    root.mkdir()
    (root / "audio").mkdir()
    path = root / "audio/sample.wav"
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(b"\x01\x00" * 16000)
    c = load_cases(dataset_path())[0]
    h = file_hash(path)
    sample = {"id": "sample", "case_id": c["id"], "status": "ok", "audio": "audio/sample.wav", "audio_hash": h}
    transcript = {"id": "sample", "audio_hash": h, "engine": "private-recognizer", "text": c["text"]}
    r = evaluate([c], [sample], [transcript], {"identity": {"model_label": "private-model"}})
    build_report(r, root, root)
    out = tmp_path / "study"
    value = build_study([root / "report.json"], out)
    assert value["trials"] == 1
    raw = (out / "data.js").read_text(encoding="utf-8")
    assert "private-model" not in raw and "private-recognizer" not in raw and '"metrics"' not in raw
    packet = json.loads((out / "study.json").read_text(encoding="utf-8"))
    trial = packet["trials"][0]
    assert file_hash(out / trial["audio"]) == h
    assert trial["report_id"] != r["report_id"]
    assert trial["sample_id"] != sample["id"]
    decisions = [{"report_id": trial["report_id"], "sample_id": trial["sample_id"], "audio_hash": h,
                  "target_id": "t1", "rater": "reviewer-a", "verdict": "uncertain"}]
    restored = tmp_path / "decisions"
    unblind(tmp_path / "study.key.json", decisions, restored)
    saved = json.loads((restored / f"{r['report_id']}.jsonl").read_text(encoding="utf-8"))
    assert saved["report_id"] == r["report_id"] and saved["sample_id"] == sample["id"]
    assert not (out / "study.key.json").exists()
    with pytest.raises(ValueError, match="empty"):
        build_study([root / "report.json"], out)


def test_submission_rejects_partial_track_and_missing_model_revision(tmp_path):
    c = load_cases(dataset_path())[0]
    r = evaluate([c], [], [])
    result = submission(r, tmp_path)
    assert not result["eligible_for_automatic_track_table"]
    assert len(result["blockers"]) >= 3
    assert (tmp_path / "model-card.md").exists()
