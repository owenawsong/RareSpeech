import pytest
from test_evaluation import fixtures

from rarespeech.evaluate import audit_asr, compare, evaluate
from rarespeech.report import build_report


def test_report_embedded_data_cannot_close_script(tmp_path):
    c, s, t = fixtures()
    c["text"] += " </script><img src=x onerror=alert(1)>"
    r = evaluate([c], [s], [t])
    build_report(r, tmp_path)
    assert "</script>" not in (tmp_path / "data.js").read_text()
    assert (tmp_path / "index.html").exists()
    assert "not pronunciation ratings" in (tmp_path / "model-card.md").read_text()
    assert "audio" not in r["rows"][0]


def test_changed_asr_requires_audit_not_checkpoint_compare():
    c, s, t = fixtures()
    a = evaluate([c], [s], [t])
    t["engine"] = "another-ASR"
    t["text"] = "the mineral is unknown"
    b = evaluate([c], [s], [t])
    with pytest.raises(ValueError, match="ASR"):
        compare(a, b)
    assert len(audit_asr(a, b)["disagreements"]) == 1


def test_asr_audit_rejects_changed_audio():
    c, s, t = fixtures()
    a = evaluate([c], [s], [t])
    s["audio_hash"] = t["audio_hash"] = "changed"
    b = evaluate([c], [s], [t])
    with pytest.raises(ValueError, match="different audio"):
        audit_asr(a, b)
