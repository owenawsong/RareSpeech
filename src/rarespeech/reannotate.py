"""Audited annotation correction without synthesizing or altering audio.

Only explicit design annotations may change. Source evidence remains untouched;
old reports and reviews are deliberately not migrated to a new corpus identity.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

from . import __version__
from .corpus import VARIANTS, corpus_hash
from .io import digest, file_hash, safe_child, unique, write_json

ALLOWED_FIELDS = frozenset(
    {
        "variant",
        "carrier_id",
        "condition_label",
        "control_pair",
        "notes",
        "track",
        "cluster_id",
        "control_design",
    }
)

_WINDOWS = sys.platform == "win32"
_PROMOTION_DELAYS = (0.05, 0.1, 0.2, 0.4, 0.8)


def _retryable_lock(error):
    # Do not conceal filesystem errors on other platforms or retry indefinitely.
    return (
        _WINDOWS
        and isinstance(error, PermissionError)
        and getattr(error, "winerror", None) in {None, 5, 32, 33}
    )


def _directory_identity(path):
    info = path.stat()
    return info.st_dev, info.st_ino


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _asset(source, relative):
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("audio paths must be portable relative paths under audio/")
    path = PurePosixPath(relative)
    if path.is_absolute() or PureWindowsPath(relative).is_absolute() or ".." in path.parts:
        raise ValueError("audio path escapes its source run")
    if len(path.parts) < 2 or path.parts[0] != "audio" or path.suffix.lower() != ".wav":
        raise ValueError("successful audio must be a WAV under audio/")
    return safe_child(source, relative)


def _changes(original, corrected):
    unique(original)
    unique(corrected)
    if [c["id"] for c in original] != [c["id"] for c in corrected]:
        raise ValueError("annotation correction requires identical case IDs and order")
    changes = []
    for before, after in zip(original, corrected):
        modified = sorted(
            k
            for k in before.keys() | after.keys()
            if (k in before) != (k in after) or _canonical(before.get(k)) != _canonical(after.get(k))
        )
        if any(k not in ALLOWED_FIELDS for k in modified):
            raise ValueError(
                "correction changes synthesis text, targets, corpus grouping, rarity or another protected field"
            )
        if after.get("variant") not in VARIANTS:
            raise ValueError("corrected variant must be a supported condition")
        for name in ALLOWED_FIELDS - {"control_design", "variant"}:
            if name in after and not isinstance(after[name], str):
                raise ValueError("annotation labels and notes must be strings")
        if "control_design" in after and not isinstance(after["control_design"], dict):
            raise ValueError("control_design must be an object")
        if modified:
            changes.append(
                {
                    "case_id": before["id"],
                    "fields": modified,
                    "before": {k: before[k] for k in modified if k in before},
                    "after": {k: after[k] for k in modified if k in after},
                    "removed": [k for k in modified if k not in after],
                    "added": [k for k in modified if k not in before],
                }
            )
    if not changes:
        raise ValueError("no annotation changes; an identity migration is unnecessary")
    return changes


def reannotate(source: Path, corrected_cases: list[dict], out: Path, reason: str) -> dict:
    """Copy an existing run under a corrected corpus identity with source proof.

    Top-level JSONL files are treated as ASR transcripts and copied byte-for-byte
    after sample/hash validation. Audio for failed/missing samples is not copied
    without a successful bound hash. No synthesis or recognizer is invoked.
    """
    source, out = Path(source).resolve(), Path(out).resolve()
    if not source.is_dir():
        raise ValueError("source must be an existing run directory")
    if source == out or source.is_relative_to(out) or out.is_relative_to(source):
        raise ValueError("source and output directories must not overlap")
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError("annotation correction output must be an empty directory")
    initial_output = _directory_identity(out) if out.exists() else None
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 4000:
        raise ValueError("supply a nonempty correction reason up to 4000 characters")
    if (
        not isinstance(corrected_cases, list)
        or not corrected_cases
        or any(not isinstance(c, dict) for c in corrected_cases)
    ):
        raise ValueError("corrected cases must be a nonempty list of case objects")
    corrected = deepcopy(corrected_cases)
    raw = {name: safe_child(source, name).read_bytes() for name in ("run.json", "cases.json", "samples.json")}
    try:
        meta, cases, samples = (json.loads(raw[name]) for name in ("run.json", "cases.json", "samples.json"))
        if not isinstance(meta, dict) or meta.get("schema") != "rarespeech.run.v1":
            raise ValueError("source is not a supported run")
        if not isinstance(cases, list) or not cases or not isinstance(samples, list):
            raise ValueError("source cases and samples must be supported lists")
        identity = meta["identity"]
        if not isinstance(identity, dict) or identity.get("corpus_hash") != corpus_hash(cases):
            raise ValueError("source corpus hash does not match its captured cases")
        changes = _changes(cases, corrected)
        cmap, smap = unique(cases), unique(samples)
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("source run evidence is malformed") from error
    audio = {}
    ignored_failed_audio = []
    repeats = identity.get("repeats")
    if type(repeats) is not int or not 1 <= repeats <= 20:
        raise ValueError("source repeat design is missing or invalid")
    seen_repeats = set()
    for sample in smap.values():
        if sample.get("case_id") not in cmap or sample.get("status") not in {"ok", "error", "missing"}:
            raise ValueError("sample is not bound to a known case and status")
        repeat = sample.get("repeat")
        if (
            type(repeat) is not int
            or not 1 <= repeat <= repeats
            or (sample["case_id"], repeat) in seen_repeats
        ):
            raise ValueError("source sample repeat design is inconsistent")
        seen_repeats.add((sample["case_id"], repeat))
        if sample["status"] != "ok":
            if sample.get("audio"):
                ignored_failed_audio.append(sample["id"])
            continue
        path = _asset(source, sample.get("audio"))
        if not isinstance(sample.get("audio_hash"), str) or file_hash(path) != sample["audio_hash"]:
            raise ValueError("source audio hash mismatch")
        audio[sample["audio"]] = sample["audio_hash"]
    # Capture all recognizer outputs beside the run; do not copy derived reports.
    transcript_files = sorted(path.name for path in source.glob("*.jsonl"))
    for name in transcript_files:
        raw[name] = safe_child(source, name).read_bytes()
        try:
            transcripts = [
                json.loads(line) for line in raw[name].decode("utf-8-sig").splitlines() if line.strip()
            ]
            unique(transcripts)
            for transcript in transcripts:
                sample = smap.get(transcript["id"])
                if (
                    not sample
                    or sample["status"] != "ok"
                    or transcript.get("audio_hash") != sample.get("audio_hash")
                    or not isinstance(transcript.get("text"), str)
                    or not isinstance(transcript.get("engine"), str)
                    or not transcript["engine"].strip()
                ):
                    raise ValueError("transcript does not match a successful sample/hash/engine")
        except (KeyError, TypeError, AttributeError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("source transcript file is malformed") from error
    source_hashes = {name: _sha(data) for name, data in raw.items()}
    correction = {
        "schema": "rarespeech.annotation-correction.v1",
        "reason": reason.strip(),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "tool_version": __version__,
        "source_identity_hash": digest(identity),
        "source_corpus_hash": corpus_hash(cases),
        "corrected_corpus_hash": corpus_hash(corrected),
        "source_cases_sha256": source_hashes["cases.json"],
        "source_run_sha256": source_hashes["run.json"],
        "source_files_sha256": source_hashes,
        "allowed_fields": sorted(ALLOWED_FIELDS),
        "changes": changes,
        "preserved_samples": len(samples),
        "preserved_audio_files": len(audio),
        "transcript_files": transcript_files,
        "unverified_failed_audio_not_copied": ignored_failed_audio,
        "scope": "Annotation-only correction. Synthesis text/targets, samples and transcript bytes preserved; reports/reviews require fresh evaluation.",
    }
    corrected_meta = deepcopy(meta)
    corrected_meta["identity"]["corpus_hash"] = correction["corrected_corpus_hash"]
    corrected_meta["annotation_correction"] = correction
    out.parent.mkdir(parents=True, exist_ok=True)
    prefix = f".{out.name}.reannotate-"
    staged = Path(tempfile.mkdtemp(prefix=prefix, dir=out.parent)).resolve()
    try:
        (staged / "provenance").mkdir()
        (staged / "provenance/original-cases.json").write_bytes(raw["cases.json"])
        (staged / "provenance/original-run.json").write_bytes(raw["run.json"])
        (staged / "samples.json").write_bytes(raw["samples.json"])
        for name in transcript_files:
            (staged / name).write_bytes(raw[name])
        for relative, expected in audio.items():
            destination = _asset(staged, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(_asset(source, relative), destination)
            if file_hash(destination) != expected:
                raise ValueError("audio changed during annotation correction")
        write_json(staged / "cases.json", corrected)
        write_json(staged / "run.json", corrected_meta)
        write_json(staged / "provenance/correction.json", correction)
        available_empty = initial_output
        removed_initial_empty = False
        try:
            for attempt in range(len(_PROMOTION_DELAYS) + 1):
                # Revalidate after every delay: a concurrent producer may have
                # changed source evidence while Windows held a scanning handle.
                for name, expected in source_hashes.items():
                    if file_hash(safe_child(source, name)) != expected:
                        raise ValueError("source evidence changed during annotation correction")
                if sorted(path.name for path in source.glob("*.jsonl")) != transcript_files:
                    raise ValueError("source transcript set changed during annotation correction")
                for relative, expected in audio.items():
                    if file_hash(_asset(source, relative)) != expected:
                        raise ValueError("source audio changed during annotation correction")
                try:
                    # Only the empty directory present at preflight may be
                    # removed. Even a new empty directory belongs to its creator.
                    if out.exists() or out.is_symlink():
                        if not out.is_dir() or any(out.iterdir()):
                            raise ValueError("output became nonempty during annotation correction")
                        if available_empty is None or _directory_identity(out) != available_empty:
                            raise ValueError("output appeared during annotation correction")
                        out.rmdir()
                        removed_initial_empty = True
                        available_empty = None
                    staged.rename(out)
                    break
                except PermissionError as error:
                    if not _retryable_lock(error) or attempt == len(_PROMOTION_DELAYS):
                        raise
                    time.sleep(_PROMOTION_DELAYS[attempt])
        except BaseException:
            # Restore the caller's initially empty directory if promotion fails;
            # a concurrent output must always remain untouched.
            if removed_initial_empty and not out.exists():
                try:
                    out.mkdir()
                except FileExistsError:
                    pass
            raise
    finally:
        if staged.exists():
            # Only the freshly created staging directory is eligible for cleanup.
            if staged.parent != out.parent or not staged.name.startswith(prefix):
                raise ValueError("refusing cleanup outside the annotation staging directory")
            for attempt in range(len(_PROMOTION_DELAYS) + 1):
                try:
                    shutil.rmtree(staged)
                    break
                except PermissionError as error:
                    if not _retryable_lock(error) or attempt == len(_PROMOTION_DELAYS):
                        raise
                    time.sleep(_PROMOTION_DELAYS[attempt])
    return {
        "schema": "rarespeech.annotation-migration.v1",
        "output": str(out),
        "source_corpus_hash": correction["source_corpus_hash"],
        "corrected_corpus_hash": correction["corrected_corpus_hash"],
        "changed_cases": len(changes),
        "samples": len(samples),
        "audio_files": len(audio),
        "transcript_files": transcript_files,
    }
