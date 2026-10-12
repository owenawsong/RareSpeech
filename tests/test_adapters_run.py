import json
import math
import struct
import sys
import wave

import pytest
from test_metrics import case

from rarespeech.adapters import CommandAdapter, SpeechAPI, public_config
from rarespeech.run import generate


def test_command_keeps_text_literal_without_recursive_expansion(tmp_path):
    out = tmp_path / "out.txt"
    config = {
        "argv": [
            sys.executable,
            "-c",
            "import pathlib,sys;pathlib.Path(sys.argv[1]).write_text(sys.argv[2])",
            "{output}",
            "{text}",
        ]
    }
    payload = "literal {output} $(whoami) `echo secret`"
    CommandAdapter(config).synthesize(payload, out, 17)
    assert out.read_text() == payload


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/speech",
        "https://user:password@example.com/speech",
        "https://example.com/speech?key=private",
        "file:///secret",
    ],
)
def test_remote_api_requires_clean_https(url):
    with pytest.raises(ValueError):
        SpeechAPI({"url": url})


def test_api_cannot_synthesize_different_text_from_declared_case(tmp_path):
    adapter = SpeechAPI(
        {"url": "http://127.0.0.1:8880/speech", "model": "test", "parameters": {"input": "wrong"}}
    )
    with pytest.raises(ValueError, match="override"):
        adapter.synthesize("expected", tmp_path / "out.wav", 17)


def test_private_config_not_published_and_credentials_rejected():
    config = {"type": "command", "argv": ["private/path", "{text}"], "model": "test"}
    public = public_config(config)
    assert "private/path" not in json.dumps(public)
    with pytest.raises(ValueError):
        public_config({"type": "openai-speech", "api_key": "private"})


class Tone:
    def synthesize(self, text, output, seed):
        with wave.open(str(output), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(8000)
            f.writeframes(b"".join(struct.pack("<h", int(math.sin(i * 0.3) * 10000)) for i in range(8000)))


def test_resume_hash_gate_and_changed_identity(tmp_path, monkeypatch):
    import rarespeech.run as run

    monkeypatch.setattr(run, "load_adapter", lambda c: Tone())
    config = {"type": "python", "factory": "test:factory"}
    c = case()
    generate([c], config, tmp_path, "test")
    sample = json.loads((tmp_path / "samples.json").read_text())[0]
    assert sample["status"] == "ok"

    class NoCall:
        def synthesize(self, *args):
            raise AssertionError("valid resumed audio should not regenerate")

    monkeypatch.setattr(run, "load_adapter", lambda c: NoCall())
    result = generate([c], config, tmp_path, "test", resume=True)
    assert result[0]["status"] == "ok"
    with pytest.raises(ValueError, match="changed"):
        generate([c], config, tmp_path, "different", resume=True)


def test_resume_after_factory_failure_has_empty_checkpoint(tmp_path, monkeypatch):
    import rarespeech.run as run

    def fail(c):
        raise ImportError("missing model dependency")

    monkeypatch.setattr(run, "load_adapter", fail)
    c, config = case(), {"type": "python", "factory": "test:factory"}
    with pytest.raises(ImportError):
        generate([c], config, tmp_path, "test")
    assert json.loads((tmp_path / "samples.json").read_text()) == []
    monkeypatch.setattr(run, "load_adapter", lambda c: Tone())
    assert generate([c], config, tmp_path, "test", resume=True)[0]["status"] == "ok"


def test_reuse_regenerates_changed_case(tmp_path, monkeypatch):
    import rarespeech.run as run

    monkeypatch.setattr(run, "load_adapter", lambda c: Tone())
    config = {"type": "python", "factory": "test:factory"}
    first = tmp_path / "first"
    c = case()
    generate([c], config, first, "test")
    calls = []

    class CountingTone(Tone):
        def synthesize(self, text, output, seed):
            calls.append(text)
            super().synthesize(text, output, seed)

    monkeypatch.setattr(run, "load_adapter", lambda c: CountingTone())
    reused = generate([c], config, tmp_path / "same", "test", reuse_from=first)
    assert not calls
    assert "reuse_source_identity" in reused[0]
    c["text"] += " Extra words."
    generate([c], config, tmp_path / "changed", "test", reuse_from=first)
    assert calls == [c["text"]]


def test_reuse_rejects_changed_adapter(tmp_path, monkeypatch):
    import rarespeech.run as run

    monkeypatch.setattr(run, "load_adapter", lambda c: Tone())
    c, config = case(), {"type": "python", "factory": "test:factory"}
    generate([c], config, tmp_path / "first", "test")
    config["revision"] = "new"
    with pytest.raises(ValueError, match="matching adapter"):
        generate([c], config, tmp_path / "second", "test", reuse_from=tmp_path / "first")


def test_documented_factories_resolve_from_installed_package(monkeypatch):
    from rarespeech import integrations
    from rarespeech.adapters import load_adapter

    monkeypatch.setattr(integrations, "InflectAdapter", lambda options: Tone())
    adapter = load_adapter({"type": "python", "factory": "rarespeech.integrations:inflect", "options": {}})
    assert isinstance(adapter, Tone)
