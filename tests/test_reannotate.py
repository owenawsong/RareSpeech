"""Annotation migration uses synthetic audio and never invokes a model."""

import json
import wave
from copy import deepcopy
from pathlib import Path

import pytest
from test_metrics import case

from rarespeech.corpus import corpus_hash
from rarespeech.io import digest, file_hash, write_json
from rarespeech.reannotate import reannotate


def fixture(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "audio").mkdir()
    first, second = case(), case("I read omphacite twice.")
    first.update(id="term.bare", family_id="term", track="core-v1")
    second.update(id="term.short", family_id="term", variant="isolated", track="core-v1")
    cases = [first, second]
    corrected = deepcopy(cases)
    corrected[1]["variant"] = "dense"
    samples, transcripts = [], []
    for c in cases:
        sid = c["id"] + "--r1"
        rel = "audio/" + sid + ".wav"
        with wave.open(str(source / rel), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(b"\x01\x00" * 320)
        sample = {
            "id": sid,
            "case_id": c["id"],
            "audio": rel,
            "audio_hash": file_hash(source / rel),
            "status": "ok",
            "repeat": 1,
            "seed": 17,
            "wall_seconds": 0.25,
        }
        samples.append(sample)
        transcripts.append(
            {
                "id": sid,
                "audio_hash": sample["audio_hash"],
                "text": c["text"],
                "engine": "synthetic-test-engine",
                "settings": {"beam_size": 5},
            }
        )
    metadata = {
        "schema": "rarespeech.run.v1",
        "version": "0.2.0",
        "identity": {
            "corpus_hash": corpus_hash(cases),
            "repeats": 1,
            "base_seed": 17,
            "adapter": {"config_hash": "a" * 64, "revision": "weights-sha256:" + "b" * 64},
            "model_label": "Synthetic migration fixture",
        },
        "created_utc": "2026-10-12T00:00:00+00:00",
        "environment": {"python": "fixture", "os": "fixture"},
        "adapter_load_seconds": 0.125,
        "timing_scope": "adapter-call wall time",
    }
    for name, value in (("run.json", metadata), ("samples.json", samples), ("cases.json", cases)):
        write_json(source / name, value)
    transcript_bytes = (
        "\r\n".join(json.dumps(t, separators=(", ", ": ")) for t in transcripts) + "\r\n"
    ).encode()
    (source / "asr-test.jsonl").write_bytes(transcript_bytes)
    (source / "report.json").write_text('{"obsolete":true}', encoding="utf-8")
    return source, cases, corrected, samples, metadata


def test_migration_preserves_every_audio_sample_transcript_byte_and_original_capture(tmp_path):
    source, cases, corrected, samples, metadata = fixture(tmp_path)
    originals = {p.relative_to(source): p.read_bytes() for p in source.rglob("*") if p.is_file()}
    out = tmp_path / "corrected"
    result = reannotate(source, corrected, out, "Correct inherited isolated label on short-context cases.")
    assert result["changed_cases"] == 1 and result["audio_files"] == 2
    assert result["corrected_corpus_hash"] == corpus_hash(corrected)
    assert result["source_corpus_hash"] == corpus_hash(cases)
    assert json.loads((out / "cases.json").read_text()) == corrected
    assert (out / "samples.json").read_bytes() == originals[Path("samples.json")]
    assert (out / "asr-test.jsonl").read_bytes() == originals[Path("asr-test.jsonl")]
    assert (out / "provenance/original-cases.json").read_bytes() == originals[Path("cases.json")]
    assert (out / "provenance/original-run.json").read_bytes() == originals[Path("run.json")]
    migrated = json.loads((out / "run.json").read_text())
    changed = deepcopy(metadata)
    changed["identity"]["corpus_hash"] = corpus_hash(corrected)
    assert {k: v for k, v in migrated.items() if k != "annotation_correction"} == changed
    correction = migrated["annotation_correction"]
    assert correction["source_cases_sha256"] == file_hash(source / "cases.json")
    assert correction["source_run_sha256"] == file_hash(source / "run.json")
    assert correction["source_identity_hash"] == digest(metadata["identity"])
    assert correction["changes"][0]["before"] == {"variant": "isolated"}
    assert correction["changes"][0]["after"] == {"variant": "dense"}
    assert not (out / "report.json").exists()
    for sample in samples:
        assert file_hash(out / sample["audio"]) == sample["audio_hash"]
    assert {p.relative_to(source): p.read_bytes() for p in source.rglob("*") if p.is_file()} == originals


@pytest.mark.parametrize(
    "field,value",
    [
        ("text", "different synthesis text"),
        ("targets", []),
        ("family_id", "other"),
        ("category", "other"),
        ("language", "fr"),
        ("rarity", {"zipf": 9}),
        ("authorship", "replacement"),
    ],
)
def test_protected_content_mutations_are_rejected_before_output(tmp_path, field, value):
    source, _, corrected, _, _ = fixture(tmp_path)
    corrected[0][field] = value
    out = tmp_path / "corrected"
    with pytest.raises(ValueError, match="protected field"):
        reannotate(source, corrected, out, "Incorrect mutation")
    assert not out.exists()


def test_target_type_mutation_cannot_hide_behind_python_numeric_equality(tmp_path):
    source, _, corrected, _, _ = fixture(tmp_path)
    corrected[0]["targets"][0]["start"] = float(corrected[0]["targets"][0]["start"])
    with pytest.raises(ValueError, match="protected field"):
        reannotate(source, corrected, tmp_path / "corrected", "Type change is not annotation metadata")


def test_case_order_and_ids_must_remain_identical(tmp_path):
    source, _, corrected, _, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match="IDs and order"):
        reannotate(source, corrected[::-1], tmp_path / "corrected", "Order change")
    corrected[0]["id"] = "different"
    with pytest.raises(ValueError, match="IDs and order"):
        reannotate(source, corrected, tmp_path / "corrected", "ID change")


def test_source_corpus_tampering_is_detected(tmp_path):
    source, cases, corrected, _, _ = fixture(tmp_path)
    cases[0]["text"] += " Tampered."
    write_json(source / "cases.json", cases)
    with pytest.raises(ValueError, match="source corpus hash"):
        reannotate(source, corrected, tmp_path / "corrected", "Correction")


def test_audio_hash_mismatch_is_detected_before_output(tmp_path):
    source, _, corrected, samples, _ = fixture(tmp_path)
    (source / samples[0]["audio"]).write_bytes(b"tampered")
    out = tmp_path / "corrected"
    with pytest.raises(ValueError, match="audio hash mismatch"):
        reannotate(source, corrected, out, "Correction")
    assert not out.exists()


@pytest.mark.parametrize(
    "field,value", [("id", "unknown"), ("audio_hash", "invalid"), ("text", None), ("engine", "")]
)
def test_transcript_identity_and_types_are_verified(tmp_path, field, value):
    source, _, corrected, _, _ = fixture(tmp_path)
    rows = [json.loads(line) for line in (source / "asr-test.jsonl").read_text().splitlines()]
    rows[0][field] = value
    (source / "asr-test.jsonl").write_text("\n".join(json.dumps(t) for t in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="transcript"):
        reannotate(source, corrected, tmp_path / "corrected", "Correction")


def test_existing_nonempty_out_is_preserved_and_empty_out_is_supported(tmp_path):
    source, _, corrected, _, _ = fixture(tmp_path)
    out = tmp_path / "corrected"
    out.mkdir()
    (out / "keep.txt").write_text("preserve", encoding="utf-8")
    with pytest.raises(ValueError, match="empty directory"):
        reannotate(source, corrected, out, "Correction")
    assert (out / "keep.txt").read_text() == "preserve"
    (out / "keep.txt").unlink()
    reannotate(source, corrected, out, "Correction")
    assert (out / "run.json").exists()


def test_source_overlap_and_empty_reason_are_rejected(tmp_path):
    source, _, corrected, _, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match="overlap"):
        reannotate(source, corrected, source / "nested", "Correction")
    with pytest.raises(ValueError, match="overlap"):
        reannotate(source, corrected, source, "Correction")
    with pytest.raises(ValueError, match="reason"):
        reannotate(source, corrected, tmp_path / "corrected", "  ")


def test_noop_and_invalid_variant_are_rejected(tmp_path):
    source, cases, corrected, _, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match="no annotation changes"):
        reannotate(source, cases, tmp_path / "corrected", "No actual correction")
    corrected[1]["variant"] = "not-a-condition"
    with pytest.raises(ValueError, match="supported condition"):
        reannotate(source, corrected, tmp_path / "corrected", "Correction")


@pytest.mark.parametrize(
    "relative", ["../escape.wav", "run.json", "C:/outside.wav", "audio/../../escape.wav"]
)
def test_audio_paths_cannot_escape_or_overwrite_metadata(tmp_path, relative):
    source, _, corrected, samples, _ = fixture(tmp_path)
    samples[0]["audio"] = relative
    write_json(source / "samples.json", samples)
    with pytest.raises(ValueError, match="audio|WAV"):
        reannotate(source, corrected, tmp_path / "corrected", "Correction")


def test_source_change_during_copy_aborts_and_removes_only_staging(tmp_path, monkeypatch):
    source, _, corrected, _, metadata = fixture(tmp_path)
    from rarespeech import reannotate as module

    original_copy = module.shutil.copyfile

    def tamper(src, dest):
        original_copy(src, dest)
        metadata["adapter_load_seconds"] = 9
        write_json(source / "run.json", metadata)

    monkeypatch.setattr(module.shutil, "copyfile", tamper)
    out = tmp_path / "corrected"
    with pytest.raises(ValueError, match="source evidence changed"):
        reannotate(source, corrected, out, "Correction")
    assert not out.exists()
    assert list(tmp_path.glob(".corrected.reannotate-*")) == []
    assert json.loads((source / "run.json").read_text())["adapter_load_seconds"] == 9


def test_output_populated_during_copy_is_not_overwritten(tmp_path, monkeypatch):
    source, _, corrected, _, _ = fixture(tmp_path)
    from rarespeech import reannotate as module

    original_copy = module.shutil.copyfile
    out = tmp_path / "corrected"

    def populate(src, dest):
        original_copy(src, dest)
        out.mkdir(exist_ok=True)
        (out / "keep.txt").write_text("new concurrent file", encoding="utf-8")

    monkeypatch.setattr(module.shutil, "copyfile", populate)
    with pytest.raises(ValueError, match="became nonempty"):
        reannotate(source, corrected, out, "Correction")
    assert (out / "keep.txt").read_text() == "new concurrent file"
    assert list(tmp_path.glob(".corrected.reannotate-*")) == []


def test_partial_run_remains_partial_and_failed_audio_is_not_invented(tmp_path):
    source, _, corrected, samples, _ = fixture(tmp_path)
    samples[1]["status"] = "error"
    samples[1].pop("audio_hash")
    write_json(source / "samples.json", samples)
    rows = [json.loads(line) for line in (source / "asr-test.jsonl").read_text().splitlines()]
    (source / "asr-test.jsonl").write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    out = tmp_path / "corrected"
    result = reannotate(source, corrected, out, "Correction preserves failed generation evidence")
    assert result["samples"] == 2 and result["audio_files"] == 1
    assert not (out / samples[1]["audio"]).exists()
    assert json.loads((out / "samples.json").read_text())[1]["status"] == "error"
    assert json.loads((out / "run.json").read_text())["annotation_correction"][
        "unverified_failed_audio_not_copied"
    ] == [samples[1]["id"]]


def test_repeated_sample_for_same_case_cannot_be_hidden_under_another_id(tmp_path):
    source, _, corrected, samples, _ = fixture(tmp_path)
    duplicate = deepcopy(samples[0])
    duplicate["id"] += "--duplicate"
    samples.append(duplicate)
    write_json(source / "samples.json", samples)
    with pytest.raises(ValueError, match="repeat design"):
        reannotate(source, corrected, tmp_path / "corrected", "Invalid repeat duplication")


def test_duplicate_transcript_decisions_are_rejected(tmp_path):
    source, _, corrected, _, _ = fixture(tmp_path)
    raw = (source / "asr-test.jsonl").read_bytes()
    (source / "asr-test.jsonl").write_bytes(raw + raw)
    with pytest.raises(ValueError, match="duplicate"):
        reannotate(source, corrected, tmp_path / "corrected", "Invalid transcript duplication")


def windows_retry(monkeypatch):
    from rarespeech import reannotate as module

    monkeypatch.setattr(module, "_WINDOWS", True)
    monkeypatch.setattr(module.time, "sleep", lambda delay: None)
    return module


def test_windows_transient_promotion_lock_retries_then_preserves_all_evidence(tmp_path, monkeypatch):
    source, _, corrected, samples, _ = fixture(tmp_path)
    module = windows_retry(monkeypatch)
    original = Path.rename
    attempts = []

    def locked_once(path, target):
        attempts.append(path)
        if len(attempts) == 1:
            raise PermissionError("synthetic Windows scanning lock")
        return original(path, target)

    monkeypatch.setattr(Path, "rename", locked_once)
    out = tmp_path / "corrected"
    reannotate(source, corrected, out, "Annotation correction")
    assert len(attempts) == 2
    assert (out / "run.json").exists()
    assert (out / "asr-test.jsonl").read_bytes() == (source / "asr-test.jsonl").read_bytes()
    for sample in samples:
        assert file_hash(out / sample["audio"]) == sample["audio_hash"]
    assert list(tmp_path.glob(".corrected.reannotate-*")) == []
    assert module._WINDOWS


@pytest.mark.parametrize("initial_empty", [False, True])
def test_windows_persistent_promotion_lock_is_bounded_cleans_staging_and_preserves_source(
    tmp_path, monkeypatch, initial_empty
):
    source, _, corrected, _, _ = fixture(tmp_path)
    original = {p.relative_to(source): p.read_bytes() for p in source.rglob("*") if p.is_file()}
    module = windows_retry(monkeypatch)
    attempts = []

    def locked(path, target):
        attempts.append(path)
        raise PermissionError("synthetic persistent Windows lock")

    monkeypatch.setattr(Path, "rename", locked)
    out = tmp_path / "corrected"
    if initial_empty:
        out.mkdir()
    with pytest.raises(PermissionError, match="persistent"):
        reannotate(source, corrected, out, "Annotation correction")
    assert len(attempts) == len(module._PROMOTION_DELAYS) + 1
    assert list(tmp_path.glob(".corrected.reannotate-*")) == []
    assert out.exists() == initial_empty
    if initial_empty:
        assert list(out.iterdir()) == []
    assert {p.relative_to(source): p.read_bytes() for p in source.rglob("*") if p.is_file()} == original


@pytest.mark.parametrize("populated", [False, True])
def test_windows_retry_never_replaces_new_concurrent_output(tmp_path, monkeypatch, populated):
    source, _, corrected, _, _ = fixture(tmp_path)
    windows_retry(monkeypatch)
    out = tmp_path / "corrected"
    attempts = []

    def concurrent(path, target):
        attempts.append(path)
        out.mkdir()
        if populated:
            (out / "keep.txt").write_text("concurrent owner", encoding="utf-8")
        raise PermissionError("synthetic lock concurrent with output creation")

    monkeypatch.setattr(Path, "rename", concurrent)
    with pytest.raises(ValueError, match="output (became nonempty|appeared)"):
        reannotate(source, corrected, out, "Annotation correction")
    assert len(attempts) == 1
    assert out.is_dir()
    if populated:
        assert (out / "keep.txt").read_text() == "concurrent owner"
    else:
        assert list(out.iterdir()) == []
    assert list(tmp_path.glob(".corrected.reannotate-*")) == []


def test_windows_retry_rechecks_source_after_delay(tmp_path, monkeypatch):
    source, _, corrected, _, metadata = fixture(tmp_path)
    module = windows_retry(monkeypatch)
    attempts = []

    def locked(path, target):
        attempts.append(path)
        raise PermissionError("synthetic scanning lock")

    def mutate_during_delay(delay):
        metadata["adapter_load_seconds"] = 7
        write_json(source / "run.json", metadata)

    monkeypatch.setattr(Path, "rename", locked)
    monkeypatch.setattr(module.time, "sleep", mutate_during_delay)
    out = tmp_path / "corrected"
    with pytest.raises(ValueError, match="source evidence changed"):
        reannotate(source, corrected, out, "Annotation correction")
    assert len(attempts) == 1
    assert not out.exists()
    assert list(tmp_path.glob(".corrected.reannotate-*")) == []


def test_nonwindows_permission_error_is_not_retried(tmp_path, monkeypatch):
    source, _, corrected, _, _ = fixture(tmp_path)
    module = windows_retry(monkeypatch)
    monkeypatch.setattr(module, "_WINDOWS", False)
    attempts = []

    def locked(path, target):
        attempts.append(path)
        raise PermissionError("genuine non-Windows permission failure")

    monkeypatch.setattr(Path, "rename", locked)
    with pytest.raises(PermissionError, match="non-Windows"):
        reannotate(source, corrected, tmp_path / "corrected", "Annotation correction")
    assert len(attempts) == 1
    assert list(tmp_path.glob(".corrected.reannotate-*")) == []
