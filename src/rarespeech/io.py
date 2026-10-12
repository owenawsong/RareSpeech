from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

_WINDOWS = sys.platform == "win32"
_REPLACE_DELAYS = (0.05, 0.1, 0.2, 0.4, 0.8)


def _retryable_lock(error):
    return (
        _WINDOWS
        and isinstance(error, PermissionError)
        and getattr(error, "winerror", None) in {None, 5, 32, 33}
    )


def _retry_locked(operation):
    for attempt in range(len(_REPLACE_DELAYS) + 1):
        try:
            return operation()
        except PermissionError as error:
            if not _retryable_lock(error) or attempt == len(_REPLACE_DELAYS):
                raise
            time.sleep(_REPLACE_DELAYS[attempt])


def _atomic_text(path: Path, text: str) -> None:
    """Publish one complete file; concurrent writers never share staging files.

    The last successful replacement wins. This is not a multi-file transaction.
    Default text newline translation preserves the previous writer's byte format.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        # The descriptor is closed before replacement: Windows scanners can hold
        # a transient sharing lock even when our own writer is already closed.
        with os.fdopen(descriptor, "w", encoding="utf-8", newline=None) as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        _retry_locked(lambda: os.replace(temporary, path))
    finally:
        if temporary.exists():
            # Unlink this exact exclusively created file; never enumerate/glob
            # neighboring checkpoints or another writer's temporary files.
            _retry_locked(lambda: temporary.unlink(missing_ok=True))


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if line.strip():
            try:
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError("expected an object")
                rows.append(value)
            except (ValueError, TypeError) as e:
                raise ValueError(f"{path.name}:{i}: {e}") from e
    return rows


def write_json(path: Path, value) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    _atomic_text(path, text)


def write_jsonl(path: Path, rows) -> None:
    text = "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows)
    _atomic_text(path, text)


def unique(rows: list[dict], key="id") -> dict:
    result = {}
    for row in rows:
        name = row.get(key)
        if not isinstance(name, str) or not name:
            raise ValueError(f"missing string {key}")
        if name in result:
            raise ValueError(f"duplicate {key}: {name}")
        result[name] = row
    return result


def safe_child(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("asset path escapes its root")
    return path
