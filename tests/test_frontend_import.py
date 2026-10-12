"""Exercise the real upload validator against hostile coverage/audio fields."""
import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from rarespeech.corpus import load_cases
from rarespeech.datasets import dataset_path
from rarespeech.evaluate import evaluate


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is needed for browser-validator regression")
def test_uploaded_report_rejects_markup_in_coverage_and_malformed_audio():
    c = load_cases(dataset_path())[0]
    sample = {"id": c["id"] + "--r1", "case_id": c["id"], "repeat": 1, "status": "ok", "audio_hash": "a" * 64}
    transcript = {"id": sample["id"], "text": c["text"], "audio_hash": sample["audio_hash"], "engine": "synthetic-test"}
    valid = evaluate([c], [sample], [transcript])
    malicious = []
    for field in ("scored", "samples"):
        r = deepcopy(valid)
        r["summary"][field] = '<img src=x onerror="throw new Error(1)">'
        malicious.append(r)
        r = deepcopy(valid)
        r["totals"]["all"][field] = '<img src=x onerror="throw new Error(1)">'
        malicious.append(r)
    r = deepcopy(valid)
    r["asr_audit"] = {"disagreements": {"length": "<svg onload=alert(1)>"}}
    malicious.append(r)
    r = deepcopy(valid)
    r["rows"][0]["audio_info"] = {"seconds": "1.2", "flags": [], "waveform": []}
    malicious.append(r)
    script = r'''
const fs=require('node:fs'),vm=require('node:vm');
const text=fs.readFileSync(process.argv[1],'utf8');
const validator=text.slice(text.indexOf('function validateReport('),text.indexOf('function loadDecisions('));
const context={};vm.createContext(context);vm.runInContext(validator,context);
const payload=JSON.parse(fs.readFileSync(0,'utf8'));
context.validateReport(payload.valid);
for(const report of payload.malicious){let rejected=false;try{context.validateReport(report)}catch{rejected=true}if(!rejected)process.exit(1)}
'''
    path = Path(__file__).parents[1] / "src/rarespeech/web/app.js"
    result = subprocess.run(["node", "-e", script, str(path)], input=json.dumps({"valid": valid, "malicious": malicious}),
                            text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
