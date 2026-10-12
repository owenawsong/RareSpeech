from __future__ import annotations

import argparse
import functools
import http.server
import json
import sys
from pathlib import Path

from .corpus import corpus_hash, load_cases, select
from .datasets import dataset_path
from .evaluate import audit_asr, compare, evaluate, merge_reviews
from .io import file_hash, read_jsonl, safe_child, unique, write_json, write_jsonl
from .report import build_report


def parser():
    p = argparse.ArgumentParser(description="RareSpeech — inspect what TTS loses when words get unfamiliar.")
    p.add_argument("--version", action="version", version="RareSpeech 0.2.0")
    sub = p.add_subparsers(dest="action", required=True)
    for name in ("validate", "corpus-audit", "export", "generate", "import-audio", "benchmark"):
        s = sub.add_parser(name)
        s.add_argument("--corpus", type=Path)
        s.add_argument("--track", choices=["core", "stress", "legacy"], default="core")
        if name == "corpus-audit":
            s.add_argument("--out", type=Path)
        elif name != "validate":
            s.add_argument("--category")
            s.add_argument("--variant")
            s.add_argument("--limit", type=int)
            s.add_argument("--out", type=Path, required=True)
        if name in ("generate", "import-audio", "benchmark"):
            s.add_argument("--model-label", required=True)
        if name in ("generate", "benchmark"):
            s.add_argument("--adapter", type=Path, required=True)
            s.add_argument("--repeats", type=int, default=1)
            s.add_argument("--seed", type=int, default=17)
            s.add_argument("--resume", action="store_true")
            s.add_argument("--reuse-from", type=Path)
        if name == "benchmark":
            s.add_argument("--asr-model", default="small.en")
            s.add_argument("--asr-device", default="cpu")
            s.add_argument("--asr-compute", default="int8")
        if name == "import-audio":
            s.add_argument("--audio-dir", type=Path, required=True)
            s.add_argument("--provenance", type=Path, help="JSON adapter identity only; never executed")
    s = sub.add_parser("transcribe")
    s.add_argument("--run", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--model", default="small.en")
    s.add_argument("--device", default="cpu")
    s.add_argument("--compute", default="int8")
    s.add_argument("--resume", action="store_true")
    s = sub.add_parser("evaluate")
    s.add_argument("--run", type=Path, required=True)
    s.add_argument("--transcripts", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("review")
    s.add_argument("--report", type=Path, required=True)
    s.add_argument("--decisions", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("compare")
    s.add_argument("baseline", type=Path)
    s.add_argument("candidate", type=Path)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("audit-asr")
    s.add_argument("left", type=Path)
    s.add_argument("right", type=Path)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("report")
    s.add_argument("input", type=Path)
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--audio-root", type=Path)
    s = sub.add_parser("submission")
    s.add_argument("--report", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("study")
    s.add_argument("--reports", type=Path, nargs="+", required=True)
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--seed", type=int, default=17)
    s = sub.add_parser("unblind")
    s.add_argument("--key", type=Path, required=True)
    s.add_argument("--decisions", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("serve")
    s.add_argument("directory", type=Path)
    s.add_argument("--port", type=int, default=8765)
    return p


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    args = parser().parse_args()
    try:
        if hasattr(args, "corpus") and args.corpus is None:
            args.corpus = dataset_path(args.track)
        if args.action == "corpus-audit":
            from .audit import audit_corpus

            value = audit_corpus(load_cases(args.corpus))
            if args.out:
                write_json(args.out, value)
            else:
                print(json.dumps(value, indent=2))
            return
        if args.action == "submission":
            from .submission import submission

            value = submission(load_json(args.report), args.out)
            print(json.dumps({"eligible": value["eligible_for_automatic_track_table"], "blockers": value["blockers"]}))
            return
        if args.action == "study":
            from .study import build_study

            print(json.dumps(build_study(args.reports, args.out, args.seed)))
            return
        if args.action == "unblind":
            from .study import unblind

            print(json.dumps(unblind(args.key, read_jsonl(args.decisions), args.out)))
            return
        if args.action == "benchmark":
            from .pipeline import benchmark

            cases = select(load_cases(args.corpus), args.category, args.variant, args.limit)
            benchmark(
                cases,
                load_json(args.adapter),
                args.out,
                args.model_label,
                args.repeats,
                args.seed,
                args.resume,
                args.reuse_from,
                args.asr_model,
                args.asr_device,
                args.asr_compute,
            )
            return
        if args.action == "serve":
            handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(args.directory))
            print(f"Open http://127.0.0.1:{args.port}", flush=True)
            http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler).serve_forever()
            return
        if args.action in ("validate", "export", "generate", "import-audio"):
            cases = load_cases(args.corpus)
            if args.action == "validate":
                print(f"Valid: {len(cases)} cases; SHA-256 {corpus_hash(cases)}")
                return
            cases = select(cases, args.category, args.variant, args.limit)
            if args.action == "export":
                write_jsonl(args.out, cases)
            elif args.action == "generate":
                from .run import generate

                results = generate(
                    cases,
                    load_json(args.adapter),
                    args.out,
                    args.model_label,
                    args.repeats,
                    args.seed,
                    args.resume,
                    args.reuse_from,
                )
                if any(s["status"] != "ok" for s in results):
                    raise ValueError(
                        "generation incomplete; inspect samples.json and resume after fixing the adapter"
                    )
            else:
                import shutil

                from .adapters import public_config
                from .audio import inspect_audio

                if args.out.exists() and any(args.out.iterdir()):
                    raise ValueError("import output must be empty")
                args.out.mkdir(parents=True, exist_ok=True)
                (args.out / "audio").mkdir(exist_ok=True)
                samples = []
                for case in cases:
                    source = safe_child(args.audio_dir, case["id"] + ".wav")
                    sample = {
                        "id": case["id"] + "--r1",
                        "case_id": case["id"],
                        "repeat": 1,
                        "status": "missing",
                    }
                    if source.exists():
                        info = inspect_audio(source)
                        relative = f"audio/{sample['id']}.wav"
                        shutil.copyfile(source, args.out / relative)
                        sample.update(
                            status="ok", audio=relative, audio_hash=file_hash(source), audio_info=info
                        )
                    samples.append(sample)
                write_json(args.out / "cases.json", cases)
                write_json(args.out / "samples.json", samples)
                write_json(
                    args.out / "run.json",
                    {
                        "schema": "rarespeech.run.v1",
                        "identity": {"model_label": args.model_label, "corpus_hash": corpus_hash(cases),
                                     "repeats": 1,
                                     "adapter": public_config(load_json(args.provenance)) if args.provenance else {}},
                        "timing_scope": "imported audio; inference performance not measured",
                    },
                )
        elif args.action == "transcribe":
            from .run import transcribe

            transcribe(args.run, args.out, args.model, args.device, args.compute, args.resume)
        elif args.action == "evaluate":
            samples = load_json(args.run / "samples.json")
            unique(samples)
            for sample in samples:
                if (
                    sample["status"] == "ok"
                    and file_hash(safe_child(args.run, sample["audio"])) != sample["audio_hash"]
                ):
                    raise ValueError("audio changed since generation/import")
            report = evaluate(
                load_json(args.run / "cases.json"),
                samples,
                read_jsonl(args.transcripts),
                load_json(args.run / "run.json"),
            )
            write_json(args.out, report)
            s = report["summary"]
            print(
                f"Scored {s['scored']}/{s['samples']}; complete={s['complete']}; ASR proxy={s['automatic_accuracy']}"
            )
        elif args.action == "review":
            write_json(args.out, merge_reviews(load_json(args.report), read_jsonl(args.decisions)))
        elif args.action == "compare":
            write_json(args.out, compare(load_json(args.baseline), load_json(args.candidate)))
        elif args.action == "audit-asr":
            write_json(args.out, audit_asr(load_json(args.left), load_json(args.right)))
        elif args.action == "report":
            build_report(load_json(args.input), args.out, args.audio_root)
        print("Done.")
    except KeyboardInterrupt:
        print("Interrupted; completed generation samples remain resumable.", file=sys.stderr)
        raise SystemExit(130)
    except (ValueError, KeyError, OSError, ImportError) as e:
        print(f"RareSpeech: {e}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
