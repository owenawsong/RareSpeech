from __future__ import annotations

import hashlib
import json
from pathlib import Path


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
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows), encoding="utf-8"
    )


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
