"""Export randomized listening packets without model identity or ASR verdicts."""
import json
import random
import shutil
from pathlib import Path

from .io import digest, file_hash, safe_child, write_json, write_jsonl


def build_study(report_paths, out, seed=17):
    if out.exists() and any(out.iterdir()):
        raise ValueError("study output must be empty")
    key_path = out.parent / f"{out.name}.key.json"
    if key_path.exists():
        raise ValueError("study key already exists; choose a new output directory")
    trials, seen = [], set()
    for report_path in report_paths:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("schema") != "rarespeech.report.v1":
            raise ValueError("expected a RareSpeech report")
        for row in report["rows"]:
            if row.get("status") != "ok" or row["variant"] == "control":
                continue
            source = safe_child(report_path.parent, row.get("audio", "missing.wav"))
            if not source.exists() or file_hash(source) != row["audio_hash"]:
                raise ValueError("study requires original hash-verified audio beside each report")
            key = (report["report_id"], row["id"])
            if key in seen:
                raise ValueError("duplicate sample in study")
            seen.add(key)
            trials.append({"report_id": report["report_id"], "sample_id": row["id"], "audio_hash": row["audio_hash"],
                           "text": row["case"]["text"], "targets": row["case"]["targets"], "source": source})
    if not trials:
        raise ValueError("no available non-control study audio")
    study_id = digest({"seed": seed, "samples": [(t["report_id"], t["sample_id"], t["audio_hash"]) for t in trials]})
    random.Random(seed).shuffle(trials)
    out.mkdir(parents=True, exist_ok=True)
    (out / "audio").mkdir()
    public, mappings = [], {}
    for index, trial in enumerate(trials):
        audio = f"audio/trial-{index+1:04d}.wav"
        shutil.copyfile(trial.pop("source"), out / audio)
        trial_id = f"trial-{index+1:04d}"
        mappings[trial_id] = {"report_id": trial["report_id"], "sample_id": trial["sample_id"],
                              "audio_hash": trial["audio_hash"], "target_ids": [t["id"] for t in trial["targets"]]}
        # Even source sample IDs/report IDs can reveal configurations; mask both.
        public.append({"report_id": study_id, "sample_id": trial_id, "trial_id": trial_id,
                       "audio": audio, "audio_hash": trial["audio_hash"], "text": trial["text"],
                       "targets": [{k: t[k] for k in ("id", "text", "start", "end", "spoken_forms", "pronunciation_status", "reference_url") if k in t}
                                   for t in trial["targets"]]})
    packet = {"schema": "rarespeech.study.v1", "study_id": study_id, "trials": public,
              "randomization": "Seeded shuffle; seed and source identities retained only in the organizer key.",
              "scope": "Model labels and ASR verdicts withheld; listeners still see the reference text.",
              "pronunciation_references": "Candidate lexemes; only qualified listeners should assign pass/fail."}
    write_json(out / "study.json", packet)
    write_json(key_path, {"schema": "rarespeech.study-key.v1", "study_id": study_id, "seed": seed, "mapping": mappings})
    (out / "data.js").write_text("window.STUDY=" + json.dumps(packet, ensure_ascii=False).replace("<", "\\u003c") + ";\n", encoding="utf-8")
    for source, name in [("study.html", "index.html"), ("study.js", "study.js"), ("style.css", "style.css"), ("research.css", "research.css")]:
        shutil.copyfile(Path(__file__).parent / "web" / source, out / name)
    return {"trials": len(public), "output": str(out), "seed": seed, "private_key": str(key_path),
            "key_handling": "Keep the key outside the served/shared packet. Unblind after independent review."}


def unblind(key_path, decisions, out):
    key = json.loads(key_path.read_text(encoding="utf-8"))
    if key.get("schema") != "rarespeech.study-key.v1":
        raise ValueError("invalid listening-study key")
    import re
    from collections import defaultdict

    groups = defaultdict(list)
    for decision in decisions:
        if decision.get("report_id") != key["study_id"]:
            raise ValueError("decision belongs to another listening packet")
        mapping = key["mapping"].get(decision.get("sample_id"))
        if not mapping or decision.get("audio_hash") != mapping["audio_hash"] or decision.get("target_id") not in mapping["target_ids"]:
            raise ValueError("decision trial/target/audio identity mismatch")
        if not re.fullmatch(r"[a-f0-9]{64}", mapping["report_id"]):
            raise ValueError("invalid report identity in study key")
        groups[mapping["report_id"]].append({**decision, "report_id": mapping["report_id"], "sample_id": mapping["sample_id"]})
    if not groups:
        raise ValueError("no study decisions")
    out.mkdir(parents=True, exist_ok=True)
    for report_id, rows in groups.items():
        write_jsonl(out / f"{report_id}.jsonl", rows)
    return {"reports": len(groups), "decisions": sum(map(len, groups.values())), "output": str(out)}
