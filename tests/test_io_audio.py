import math
import struct
import wave
from pathlib import Path

import pytest

from rarespeech.audio import inspect_audio
from rarespeech.corpus import load_cases
from rarespeech.io import read_jsonl, safe_child, write_jsonl


def test_corpus_and_offsets():
    cases = load_cases(Path(__file__).resolve().parents[1] / "data" / "challenge-v1.jsonl")
    assert len(cases) == 320
    assert len({c["family_id"] for c in cases}) == 64


def test_traversal_rejected(tmp_path):
    with pytest.raises(ValueError):
        safe_child(tmp_path, "../private.wav")


def test_jsonl_errors_have_line_numbers(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text("{}\nINVALID")
    with pytest.raises(ValueError, match="bad.jsonl:2"):
        read_jsonl(p)


def test_audio_duration_and_silence(tmp_path):
    p = tmp_path / "tone.wav"
    with wave.open(str(p), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(b"".join(struct.pack("<h", int(math.sin(i * 0.3) * 10000)) for i in range(8000)))
    info = inspect_audio(p)
    assert info["seconds"] == 1
    assert not info["flags"]
    assert len(info["waveform"]) == 96


def test_duplicate_case_id_rejected(tmp_path):
    cases = load_cases(Path(__file__).resolve().parents[1] / "data" / "challenge-v1.jsonl")
    p = tmp_path / "cases.jsonl"
    write_jsonl(p, [cases[0], cases[0]])
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(p)
