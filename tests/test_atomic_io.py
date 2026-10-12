"""Checkpoint writes must preserve the previous complete file on failure."""

import json
from pathlib import Path

import pytest

from rarespeech import io


def windows(monkeypatch):
    monkeypatch.setattr(io, "_WINDOWS", True)
    monkeypatch.setattr(io.time, "sleep", lambda delay: None)


@pytest.mark.parametrize("jsonl", [False, True])
def test_transient_windows_replace_lock_retries_with_closed_complete_temp(tmp_path, monkeypatch, jsonl):
    windows(monkeypatch)
    path = tmp_path / ("checkpoint.jsonl" if jsonl else "checkpoint.json")
    path.write_text("old complete file", encoding="utf-8")
    original = io.os.replace
    attempts = []

    def locked_once(source, target):
        source = Path(source)
        attempts.append(source)
        assert source.parent == path.parent and source != path
        # Reopening succeeds; the writer has flushed and released its handle.
        assert "new" in source.read_text(encoding="utf-8")
        if len(attempts) == 1:
            assert path.read_text(encoding="utf-8") == "old complete file"
            raise PermissionError("synthetic Windows sharing lock")
        return original(source, target)

    monkeypatch.setattr(io.os, "replace", locked_once)
    (io.write_jsonl if jsonl else io.write_json)(path, [{"new": "résumé"}] if jsonl else {"new": "résumé"})
    assert len(attempts) == 2
    assert "résumé" in path.read_text(encoding="utf-8")
    assert list(tmp_path.glob(".*.tmp")) == []


@pytest.mark.parametrize("jsonl", [False, True])
def test_persistent_windows_replace_failure_keeps_previous_bytes_and_only_cleans_own_temp(
    tmp_path, monkeypatch, jsonl
):
    windows(monkeypatch)
    path = tmp_path / "checkpoint.json"
    previous = b"previous complete evidence\r\n"
    path.write_bytes(previous)
    other = tmp_path / ".checkpoint.json.other-writer.tmp"
    other.write_bytes(b"another writer's staging data")
    attempts = []

    def locked(source, target):
        attempts.append(Path(source))
        raise PermissionError("synthetic persistent lock")

    monkeypatch.setattr(io.os, "replace", locked)
    with pytest.raises(PermissionError, match="persistent"):
        (io.write_jsonl if jsonl else io.write_json)(path, [{"new": 1}] if jsonl else {"new": 1})
    assert len(attempts) == len(io._REPLACE_DELAYS) + 1
    assert path.read_bytes() == previous
    assert other.read_bytes() == b"another writer's staging data"
    assert all(not temporary.exists() for temporary in attempts)


def test_reentrant_writers_use_distinct_temps_and_publish_complete_documents(tmp_path, monkeypatch):
    path = tmp_path / "checkpoint.json"
    original = io.os.replace
    temporaries = []
    inside = False

    def interleave(source, target):
        nonlocal inside
        source = Path(source)
        temporaries.append(source)
        if not inside:
            inside = True
            io.write_json(path, {"writer": "nested", "items": list(range(10))})
            assert json.loads(path.read_text())["writer"] == "nested"
            assert source.exists()  # Inner cleanup cannot remove outer staging.
            inside = False
        return original(source, target)

    monkeypatch.setattr(io.os, "replace", interleave)
    io.write_json(path, {"writer": "outer", "items": list(range(20))})
    assert len(temporaries) == 2 and temporaries[0] != temporaries[1]
    assert json.loads(path.read_text()) == {"writer": "outer", "items": list(range(20))}
    assert all(not temporary.exists() for temporary in temporaries)


def test_jsonl_serialization_interruption_never_opens_destination(tmp_path):
    path = tmp_path / "asr.jsonl"
    previous = b'{"id": "old", "text": "complete"}\r\n'
    path.write_bytes(previous)

    def interrupted():
        yield {"id": "new"}
        raise KeyboardInterrupt("synthetic interruption before serialization completes")

    with pytest.raises(KeyboardInterrupt):
        io.write_jsonl(path, interrupted())
    assert path.read_bytes() == previous
    assert list(tmp_path.glob(".*.tmp")) == []


@pytest.mark.parametrize("jsonl", [False, True])
def test_partial_temp_write_or_fsync_failure_preserves_previous_file(tmp_path, monkeypatch, jsonl):
    path = tmp_path / "checkpoint.json"
    path.write_bytes(b"previous")

    def interrupted(descriptor):
        raise KeyboardInterrupt("synthetic interruption after writing staging data")

    monkeypatch.setattr(io.os, "fsync", interrupted)
    with pytest.raises(KeyboardInterrupt):
        (io.write_jsonl if jsonl else io.write_json)(path, [{"id": "new"}] if jsonl else {"id": "new"})
    assert path.read_bytes() == b"previous"
    assert list(tmp_path.glob(".*.tmp")) == []


def test_serialization_and_platform_newlines_match_original_writer(tmp_path):
    value = {"accent": "résumé", "line": "one\ntwo", "items": [1, 2]}
    expected = tmp_path / "expected"
    expected.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    actual = tmp_path / "actual.json"
    io.write_json(actual, value)
    assert actual.read_bytes() == expected.read_bytes()
    rows = [{"id": "a", "text": "naïve"}, {"id": "b", "text": ""}]
    expected.write_text(
        "".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows), encoding="utf-8"
    )
    io.write_jsonl(actual, rows)
    assert actual.read_bytes() == expected.read_bytes()
    io.write_jsonl(actual, [])
    assert actual.read_bytes() == b""


@pytest.mark.parametrize("jsonl", [False, True])
def test_nonfinite_serialization_never_changes_previous_file(tmp_path, jsonl):
    path = tmp_path / "checkpoint.json"
    path.write_bytes(b"previous")
    with pytest.raises(ValueError):
        (io.write_jsonl if jsonl else io.write_json)(
            path, [{"value": float("nan")}] if jsonl else {"value": float("nan")}
        )
    assert path.read_bytes() == b"previous"
    assert list(tmp_path.glob(".*.tmp")) == []


def test_nonwindows_permission_failures_are_not_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(io, "_WINDOWS", False)
    path = tmp_path / "checkpoint.json"
    path.write_bytes(b"previous")
    attempts = []

    def forbidden(source, target):
        attempts.append(source)
        raise PermissionError("genuine permission failure")

    monkeypatch.setattr(io.os, "replace", forbidden)
    with pytest.raises(PermissionError, match="genuine"):
        io.write_json(path, {"new": 1})
    assert len(attempts) == 1
    assert path.read_bytes() == b"previous"
    assert list(tmp_path.glob(".*.tmp")) == []
