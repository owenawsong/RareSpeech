from __future__ import annotations

import datetime
import importlib.metadata
import json
import platform
import shutil
import time
from pathlib import Path

from . import __version__
from .adapters import load_adapter, public_config
from .audio import inspect_audio
from .corpus import corpus_hash
from .io import digest, file_hash, read_jsonl, safe_child, unique, write_json, write_jsonl


def generate(cases, config, out: Path, model_label: str, repeats=1, seed=17, resume=False, reuse_from=None):
    if not 1 <= repeats <= 20:
        raise ValueError("repeats must be between 1 and 20")
    declared = public_config(config)
    identity = {
        "corpus_hash": corpus_hash(cases),
        "adapter": declared,
        "model_label": model_label,
        "repeats": repeats,
        "base_seed": seed,
    }
    prior = {}
    reusable, source_cases, source_meta = {}, {}, None
    if reuse_from:
        source_meta = json.loads((reuse_from / "run.json").read_text(encoding="utf-8"))
        source_identity = source_meta["identity"]
        if (
            source_identity.get("adapter", {}).get("config_hash"),
            source_identity.get("model_label"),
            source_identity.get("repeats"),
            source_identity.get("base_seed"),
        ) != (declared["config_hash"], model_label, repeats, seed):
            raise ValueError("reuse requires matching adapter hash, model label, repeats and seed")
        reusable = unique(json.loads((reuse_from / "samples.json").read_text(encoding="utf-8")))
        source_cases = unique(json.loads((reuse_from / "cases.json").read_text(encoding="utf-8")))
    if (out / "run.json").exists():
        if not resume:
            raise ValueError("run exists; choose a new directory or --resume")
        old = json.loads((out / "run.json").read_text(encoding="utf-8"))
        if old["identity"] != identity:
            raise ValueError("cannot resume with changed corpus, adapter, model label, repeats, or seed")
        prior = unique(json.loads((out / "samples.json").read_text(encoding="utf-8")))
    out.mkdir(parents=True, exist_ok=True)
    (out / "audio").mkdir(exist_ok=True)
    write_json(out / "cases.json", cases)
    meta = {
        "schema": "rarespeech.run.v1",
        "version": __version__,
        "identity": identity,
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "os": platform.system(),
            "machine": platform.machine(),
        },
        "timing_scope": "wall time per adapter call; no streaming/TTFA claim; startup excluded",
    }
    write_json(out / "run.json", meta)
    if source_meta:
        meta["reuse_source_identity"] = digest(source_meta["identity"])
    if not (out / "samples.json").exists():
        write_json(out / "samples.json", [])
    started = time.perf_counter()
    adapter = load_adapter(config)
    meta["adapter_load_seconds"] = time.perf_counter() - started
    results = []
    for case in cases:
        for repeat in range(repeats):
            sid = f"{case['id']}--r{repeat + 1}"
            relative = f"audio/{sid}.wav"
            output = safe_child(out, relative)
            previous = prior.get(sid)
            if not previous and sid in reusable and source_cases.get(case["id"]) == case:
                old = reusable[sid]
                source_audio = safe_child(reuse_from, old.get("audio", "missing.wav"))
                if (
                    old["status"] == "ok"
                    and source_audio.exists()
                    and file_hash(source_audio) == old["audio_hash"]
                ):
                    shutil.copyfile(source_audio, output)
                    previous = {**old, "reuse_source_identity": digest(source_meta["identity"])}
            if (
                previous
                and previous["status"] == "ok"
                and output.exists()
                and file_hash(output) == previous["audio_hash"]
            ):
                results.append(previous)
                continue
            output.unlink(missing_ok=True)
            sample = {
                "id": sid,
                "case_id": case["id"],
                "repeat": repeat + 1,
                "seed": seed + repeat,
                "audio": relative,
                "status": "error",
            }
            begin = time.perf_counter()
            try:
                adapter.synthesize(case["text"], output, seed + repeat)
                sample["audio_info"] = inspect_audio(output)
                if "empty" in sample["audio_info"]["flags"] or "near_silent" in sample["audio_info"]["flags"]:
                    raise ValueError("empty or near-silent audio")
                sample.update(status="ok", audio_hash=file_hash(output))
            except Exception as error:
                # Known safe errors only; user-defined exceptions may contain credentials or paths.
                sample["error"] = type(error).__name__
            sample["wall_seconds"] = time.perf_counter() - begin
            results.append(sample)
            write_json(out / "samples.json", results)
            print(f"{len(results)}/{len(cases) * repeats} {sid}: {sample['status']}", flush=True)
    write_json(out / "samples.json", results)
    write_json(out / "run.json", meta)
    return results


def transcribe(run_dir: Path, out: Path, model="small.en", device="cpu", compute="int8", resume=False):
    from faster_whisper import WhisperModel
    from faster_whisper.utils import download_model

    # Language fixed; do not prime ASR with benchmark target words.
    local_model = Path(model) if Path(model).is_dir() else Path(download_model(model))
    weights = local_model / "model.bin"
    config_path = local_model / "config.json"
    engine = WhisperModel(str(local_model), device=device, compute_type=compute, cpu_threads=2, num_workers=1)
    model_label = "local-model" if Path(model).is_dir() else model
    settings = {
        "model_weights_sha256": file_hash(weights),
        "model_config_sha256": file_hash(config_path),
        "faster_whisper_version": importlib.metadata.version("faster-whisper"),
        "ctranslate2_version": importlib.metadata.version("ctranslate2"),
        "cpu_threads": 2,
        "device": device,
        "compute_type": compute,
        "beam_size": 5,
        "temperature": 0,
        "vad_filter": False,
        "condition_on_previous_text": False,
    }
    prior = unique(read_jsonl(out)) if resume and out.exists() else {}
    samples = json.loads((run_dir / "samples.json").read_text(encoding="utf-8"))
    rows = []
    for sample in samples:
        if sample["status"] != "ok":
            continue
        audio = safe_child(run_dir, sample["audio"])
        if file_hash(audio) != sample["audio_hash"]:
            raise ValueError(f"audio changed: {sample['id']}")
        old = prior.get(sample["id"])
        if (
            old
            and old.get("audio_hash") == sample["audio_hash"]
            and old.get("engine") == f"faster-whisper/{model_label}"
            and old.get("settings") == settings
        ):
            rows.append(old)
            write_jsonl(out, rows)
            continue
        segments, _ = engine.transcribe(
            str(audio),
            language="en",
            beam_size=5,
            temperature=0,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        rows.append(
            {
                "id": sample["id"],
                "text": " ".join(s.text.strip() for s in segments),
                "audio_hash": sample["audio_hash"],
                "engine": f"faster-whisper/{model_label}",
                "settings": settings,
            }
        )
        write_jsonl(out, rows)
        print(f"ASR {len(rows)}: {sample['id']}", flush=True)
    return rows
