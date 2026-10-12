"""Validate stored evidence, not just headline flags. No scientific endorsement.

This command does not read audio bytes, authenticate weights or establish rater
qualifications. A successful submission remains an automatic proxy result.
"""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path

from . import __version__
from .corpus import corpus_hash
from .datasets import track_identity
from .evaluate import merge_reviews
from .io import digest, unique, write_json
from .metrics import macro_accuracy, score_case
from .protocol import PROTOCOL_ID, analyze_protocol
from .report import model_card

SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _hash(value):
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def _revision(value):
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip().casefold()
    if text.startswith(("weights-sha256:", "sha256:")):
        return SHA256.fullmatch(text.split(":", 1)[1]) is not None
    if text in {"main", "master", "head", "latest", "default", "dev", "unknown", "none", "n/a", "todo"}:
        return False
    if re.search(r"(?:[@:]|/resolve/|refs/heads/)(?:main|master|head|latest|dev)(?:/|$)", text):
        return False
    return not any(marker in text for marker in ("replace-with", "record-the", "placeholder", "actual_", "your_", "todo", "<", ">"))


def _implementation_hash():
    return digest(
        {
            name: Path(__file__).with_name(name).read_text(encoding="utf-8")
            for name in ("metrics.py", "evaluate.py", "protocol.py", "audit.py")
        }
    )


def _check_rows(report, cases, blockers):
    rows = report.get("rows")
    engines, recognizers = set(), set()
    if not isinstance(rows, list) or len(rows) > 100000:
        blockers.append("Report rows are missing, malformed or exceed the supported limit.")
        return None, [], []
    try:
        cmap, rmap = unique(cases), unique(rows)
        present, repeats, scored = set(), set(), []
        declared = report["metadata"]["identity"].get("repeats")
        if type(declared) is not int or not 1 <= declared <= 20:
            blockers.append("Declare a generation repeat count between 1 and 20.")
            declared = None
        for row in rmap.values():
            case = cmap.get(row.get("case_id"))
            if case is None or row.get("case") != case:
                raise ValueError("row/corpus mismatch")
            if any(row.get(field) != case[field] for field in ("category", "variant", "family_id")):
                raise ValueError("row group mismatch")
            present.add(case["id"])
            if declared is not None:
                repeat = row.get("repeat")
                if type(repeat) is not int or not 1 <= repeat <= declared or (case["id"], repeat) in repeats:
                    raise ValueError("repeat mismatch")
                repeats.add((case["id"], repeat))
            transcript, metrics = row.get("transcript"), row.get("metrics")
            if row.get("status") != "ok" or transcript is None or metrics is None:
                blockers.append("Selected cases or declared repetitions are not completely scored.")
                continue
            if not isinstance(transcript, dict) or not _hash(row.get("audio_hash")):
                raise ValueError("invalid transcript/audio identity")
            if transcript.get("audio_hash") != row["audio_hash"] or transcript.get("id") != row["id"]:
                raise ValueError("transcript binding mismatch")
            engine, settings = transcript.get("engine"), transcript.get("settings")
            if not isinstance(engine, str) or not engine.strip():
                raise ValueError("missing ASR engine")
            engines.add(engine)
            if not isinstance(settings, dict) or not settings:
                blockers.append("Record nonempty ASR decoding/runtime settings for every transcript.")
                settings = {}
            if not _hash(settings.get("model_weights_sha256")) or not _hash(
                settings.get("model_config_sha256")
            ):
                blockers.append(
                    "Record ASR model weights and config SHA-256 fingerprints for every transcript."
                )
            for key in ("initial_prompt", "prompt", "hotwords", "prefix"):
                if settings.get(key):
                    blockers.append("Primary ASR transcripts must not use vocabulary prompts or hotwords.")
            recognizers.add(digest({"engine": engine, "settings": settings}))
            if metrics != score_case(case, transcript.get("text")):
                raise ValueError("stored metric differs from transcript evidence")
            scored.append(row)
        if set(cmap) != present:
            blockers.append("Selected corpus cases are absent from report rows.")
        if declared is not None and len(repeats) != len(cases) * declared:
            blockers.append("Declared generation repeats are missing from report rows.")
        if len(recognizers) > 1:
            blockers.append("Mixed recognizer engines or decoding settings in one submission.")
        if not engines:
            blockers.append("ASR engine identity is missing.")
        return scored, sorted(engines), sorted(recognizers)
    except (KeyError, ValueError, TypeError, AttributeError):
        blockers.append(
            "Report rows, transcript/audio bindings or stored metrics are inconsistent or malformed."
        )
        return None, sorted(engines), sorted(recognizers)


def submission(report, out):
    if not isinstance(report, dict) or report.get("schema") != "rarespeech.report.v1":
        raise ValueError("expected a RareSpeech report.v1 object")
    blockers, notes = [], []
    cases = report.get("cases")
    if not isinstance(cases, list) or not cases or len(cases) > 100000:
        raise ValueError("report requires a nonempty supported corpus")
    try:
        track = track_identity(cases)
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ValueError("report corpus is malformed") from None
    if not track["canonical"]:
        blockers.append("Corpus is custom or a subset; do not advertise a canonical track score.")
    actual_hash = corpus_hash(cases)
    if report.get("corpus_hash") != actual_hash:
        blockers.append("Report corpus hash does not match its supplied cases.")
    if not _hash(report.get("report_id")):
        blockers.append("Report identity is missing or malformed.")
    source_hash = _implementation_hash()
    if report.get("measurement_hash") != source_hash or report.get("version") != __version__:
        blockers.append(
            "Evaluator identity is missing or differs from this installation; re-evaluate the evidence."
        )
    metadata = report.get("metadata")
    identity = metadata.get("identity") if isinstance(metadata, dict) else None
    if not isinstance(identity, dict):
        blockers.append("Generation identity is missing or malformed.")
        identity = {}
    if identity.get("corpus_hash") != actual_hash:
        blockers.append("Generation corpus hash is missing or does not match the report corpus.")
    if not isinstance(identity.get("model_label"), str) or not identity["model_label"].strip():
        blockers.append("Declare the evaluated model label.")
    adapter = identity.get("adapter", {})
    if not isinstance(adapter, dict):
        adapter = {}
    if not _revision(adapter.get("revision")):
        blockers.append(
            "Declare an immutable model/weights revision; mutable selectors and example placeholders are invalid."
        )
    if not _hash(adapter.get("config_hash")):
        blockers.append("Adapter configuration identity is missing or malformed.")
    checked_report = deepcopy(report)
    checked_report["metadata"] = {"identity": identity}
    scored, engines, recognizers = _check_rows(checked_report, cases, blockers)
    summary, protocol = report.get("summary"), report.get("research_protocol")
    measurements, legacy = {}, None
    if not isinstance(summary, dict) or not isinstance(protocol, dict):
        blockers.append("Evaluation summary or versioned research protocol is missing or malformed.")
    elif scored is not None:
        actual = analyze_protocol(report["rows"], cases)
        complete = len(scored) == len(report["rows"]) and len(recognizers) == 1
        legacy = macro_accuracy(scored) if complete else None
        measurements = actual["scores"] if complete and actual["headline_eligible"] else {}
        if (
            not complete
            or summary.get("complete") is not True
            or summary.get("headline_eligible") is not True
            or not actual["headline_eligible"]
        ):
            blockers.append("Full coverage and one consistent recognizer are required for a track headline.")
        if (
            protocol.get("schema") != "rarespeech.protocol.v1"
            or protocol.get("protocol_id") != PROTOCOL_ID
            or protocol.get("scores") != actual["scores"]
            or protocol.get("complete") != actual["complete"]
            or protocol.get("headline_eligible") != actual["headline_eligible"]
            or protocol.get("recognizer_consistent") != actual["recognizer_consistent"]
        ):
            blockers.append(
                "Stored balanced scores or protocol identity do not match the transcript evidence."
            )
        if summary.get("automatic_accuracy") != legacy:
            blockers.append("Stored historical retention score does not match the transcript evidence.")
        if summary.get("scored") != len(scored) or summary.get("samples") != len(report["rows"]):
            blockers.append("Stored coverage counters do not match report rows.")
    reviewed = None
    try:
        checked = merge_reviews(deepcopy(report), [])
        review = report.get("review_summary", {})
        if not isinstance(review, dict) or any(
            review.get(key) != checked["review_summary"].get(key)
            for key in (
                "reviewed",
                "required",
                "verified_accuracy",
                "balanced_primary_target_accuracy",
                "balanced_all_target_accuracy",
            )
        ):
            blockers.append("Human consensus summary does not match its bound review records.")
        else:
            reviewed = checked["review_summary"]["verified_accuracy"]
    except (KeyError, ValueError, TypeError, AttributeError):
        blockers.append("Human review evidence is malformed or has invalid report/audio bindings.")
    if reviewed is None:
        notes.append("Automatic results only; pronunciation consensus is incomplete.")
    notes.extend(
        [
            "Canonical tracks remain candidate research collections; this check is not scientific endorsement.",
            "Software checks do not establish reviewer expertise, acoustic calibration or training-data absence.",
            "Audio bytes and model weights are not opened here; their declared hashes and revision are not authenticated.",
        ]
    )
    blockers = list(dict.fromkeys(blockers))
    value = {
        "schema": "rarespeech.submission.v1",
        "report_id": report.get("report_id") if _hash(report.get("report_id")) else None,
        "track": track,
        "eligible_for_automatic_track_table": not blockers,
        "blockers": blockers,
        "notes": notes,
        "evaluator": {
            "version": report.get("version") if isinstance(report.get("version"), str) else None,
            "measurement_hash": report.get("measurement_hash")
            if _hash(report.get("measurement_hash"))
            else None,
            "protocol_id": PROTOCOL_ID,
        },
        "engines": engines,
        "recognizer_configuration_hashes": recognizers,
        "measurements": measurements if not blockers else {},
        "legacy_target_retention": legacy if not blockers else None,
        "observed_recomputed_measurements": measurements,
        "pronunciation_consensus": reviewed,
    }
    value["submission_hash"] = digest(value)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "submission.json", value)
    safe = deepcopy(report)
    safe["version"] = __version__
    safe["corpus_hash"] = actual_hash
    safe["measurement_hash"] = source_hash
    safe["summary"] = {
        "automatic_accuracy": legacy if not blockers else None,
        "scored": len(scored or []),
        "samples": len(report.get("rows", [])) if isinstance(report.get("rows"), list) else 0,
    }
    safe["research_protocol"] = {"scores": measurements if not blockers else {}}
    safe["review_summary"] = {"reviewed": 0, "required": 0}
    if scored is not None:
        rare = [r for r in scored if r["variant"] != "control"]
        references = sum(r["metrics"]["reference_tokens"] for r in rare)
        errors = sum(r["metrics"]["errors"] for r in rare)
        safe["totals"] = {"all": {"wer": errors / references if references and not blockers else None}}
    else:
        safe["totals"] = {}
    if not blockers and isinstance(report.get("review_summary"), dict):
        safe["review_summary"] = report["review_summary"]
    status = (
        "Eligible for the candidate automatic track table"
        if not blockers
        else "Not eligible for a track headline"
    )
    card = f"**Submission status: {status}.**\n\n"
    if blockers:
        card += "\n".join(f"- {blocker}" for blocker in blockers) + "\n\n"
    card += model_card(safe)
    (out / "model-card.md").write_text(card, encoding="utf-8")
    return value
