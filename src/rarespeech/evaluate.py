from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from pathlib import Path

from . import __version__
from .corpus import corpus_hash
from .io import digest, unique
from .metrics import bootstrap, macro_accuracy, score_case


def evaluate(cases, samples, transcripts, metadata=None):
    cases, samples, transcripts, metadata = deepcopy((cases, samples, transcripts, metadata))
    cmap, smap, tmap = unique(cases), unique(samples), unique(transcripts)
    unknown = set(tmap) - set(smap)
    if unknown:
        raise ValueError(f"transcripts include unknown samples: {sorted(unknown)[:3]}")
    rows = []
    for sid, sample in smap.items():
        if sample.get("case_id") not in cmap:
            raise ValueError(f"unknown case: {sample.get('case_id')}")
        case = cmap[sample["case_id"]]
        row = {
            **sample,
            "case": case,
            "category": case["category"],
            "variant": case["variant"],
            "family_id": case["family_id"],
            "metrics": None,
            "transcript": None,
        }
        transcript = tmap.get(sid)
        if transcript:
            if sample["status"] != "ok":
                raise ValueError(f"transcript for failed generation: {sid}")
            if transcript.get("audio_hash") != sample.get("audio_hash") or not transcript.get("audio_hash"):
                raise ValueError(f"transcript audio hash mismatch: {sid}")
            if not transcript.get("engine"):
                raise ValueError("transcripts must declare engine")
            row["transcript"] = transcript
            row["metrics"] = score_case(case, transcript["text"])
        row["needs_review"] = (
            not row["metrics"]
            or any(not t["retained"] for t in row["metrics"]["targets"])
            or bool(row.get("audio_info", {}).get("flags"))
        )
        rows.append(row)
    # Missing cases must remain visible even for a partial audio import.
    present = {r["case_id"] for r in rows}
    for case in cases:
        if case["id"] not in present:
            rows.append(
                {
                    "id": case["id"] + "--missing",
                    "case_id": case["id"],
                    "case": case,
                    "category": case["category"],
                    "variant": case["variant"],
                    "family_id": case["family_id"],
                    "status": "missing",
                    "metrics": None,
                    "transcript": None,
                    "needs_review": True,
                }
            )
    totals = defaultdict(
        lambda: {"samples": 0, "scored": 0, "retained": 0, "targets": 0, "errors": 0, "reference_tokens": 0}
    )
    for row in rows:
        for name in (row["category"], "all"):
            if row["variant"] == "control":
                name = "controls" if name == "all" else "control:" + name
            b = totals[name]
            b["samples"] += 1
            if row["metrics"]:
                m = row["metrics"]
                b["scored"] += 1
                b["targets"] += len(m["targets"])
                b["retained"] += sum(t["retained"] for t in m["targets"])
                b["errors"] += m["errors"]
                b["reference_tokens"] += m["reference_tokens"]
    for b in totals.values():
        b["accuracy"] = b["retained"] / b["targets"] if b["targets"] else None
        b["wer"] = b["errors"] / b["reference_tokens"] if b["reference_tokens"] else None
    complete = all(r["metrics"] is not None for r in rows)
    score = macro_accuracy(rows)
    measurement_hash = digest(
        {
            name: Path(__file__).with_name(name).read_text(encoding="utf-8")
            for name in ("metrics.py", "evaluate.py")
        }
    )
    return {
        "schema": "rarespeech.report.v1",
        "version": __version__,
        "measurement_hash": measurement_hash,
        "corpus_hash": corpus_hash(cases),
        "report_id": digest(
            {
                "corpus": corpus_hash(cases),
                "samples": samples,
                "transcripts": transcripts,
                "version": __version__,
                "measurement_hash": measurement_hash,
            }
        ),
        "metadata": metadata or {},
        "cases": cases,
        "rows": rows,
        "totals": dict(totals),
        "summary": {
            "complete": complete,
            "automatic_accuracy": score if complete else None,
            "observed_accuracy": score,
            "interval": bootstrap(rows) if complete else None,
            "scored": sum(r["metrics"] is not None for r in rows),
            "samples": len(rows),
            "label": "ASR target-retention proxy; not verified pronunciation accuracy",
        },
        "reviews": [],
        "review_summary": {
            "reviewed": 0,
            "required": sum(len(r["case"]["targets"]) for r in rows if r["variant"] != "control"),
            "verified_accuracy": None,
        },
    }


def merge_reviews(report, reviews):
    if len(reviews) > 100000:
        raise ValueError("too many reviews")
    all_reviews = report.get("reviews", []) + reviews
    rows = unique(report["rows"])
    validated, seen = [], set()
    for review in all_reviews:
        if review.get("report_id") != report["report_id"]:
            raise ValueError("review belongs to another report")
        row = rows.get(review.get("sample_id"))
        if not row or row["status"] != "ok" or review.get("audio_hash") != row.get("audio_hash"):
            raise ValueError("review sample/audio mismatch")
        target = next((t for t in row["case"]["targets"] if t["id"] == review.get("target_id")), None)
        if not target:
            raise ValueError("unknown review target")
        if review.get("verdict") not in ("pass", "fail", "uncertain"):
            raise ValueError("invalid review verdict")
        if not isinstance(review.get("rater"), str) or not review["rater"].strip():
            raise ValueError("review requires a rater pseudonym")
        key = (review["sample_id"], review["target_id"], review["rater"])
        if key in seen:
            raise ValueError("duplicate rater decision; remove old decision explicitly before replacing")
        seen.add(key)
        validated.append(review)
    grouped = defaultdict(list)
    for review in validated:
        grouped[(review["sample_id"], review["target_id"])].append(review["verdict"])
    required, decided, passed, disputed = 0, 0, 0, 0
    categories = defaultdict(lambda: [0, 0])
    for row in report["rows"]:
        if row["variant"] == "control":
            continue
        for target in row["case"]["targets"]:
            required += 1
            votes = grouped[(row["id"], target["id"])]
            # Two independent pseudonyms agreeing is the minimum consensus rule.
            if len(votes) >= 2 and set(votes) in ({"pass"}, {"fail"}):
                decided += 1
                passed += votes[0] == "pass"
                b = categories[row["category"]]
                b[0] += votes[0] == "pass"
                b[1] += 1
            elif len(votes) >= 2:
                disputed += 1
    report["reviews"] = validated
    report["review_summary"] = {
        "reviewed": decided,
        "required": required,
        "disputed": disputed,
        "observed_accuracy": passed / decided if decided else None,
        "verified_accuracy": (
            sum(a / b for a, b in categories.values()) / len(categories)
            if required and decided == required
            else None
        ),
        "policy": "two agreeing raters per target; disputes and uncertainty remain unresolved",
    }
    return report


def compare(left, right):
    if left["corpus_hash"] != right["corpus_hash"]:
        raise ValueError("comparison requires identical selected corpus hashes")
    a, b = unique(left["rows"]), unique(right["rows"])
    if set(a) != set(b):
        raise ValueError("comparison requires identical sample IDs/repeats")
    if left.get("measurement_hash") != right.get("measurement_hash"):
        raise ValueError("comparison requires identical evaluator implementations")
    for sid in a:
        ta, tb = a[sid].get("transcript"), b[sid].get("transcript")
        if ta and tb and (ta.get("engine"), ta.get("settings")) != (tb.get("engine"), tb.get("settings")):
            raise ValueError("ASR configurations differ; use audit-asr for recognizer disagreement")
    changes = []
    for sid in a:
        x, y = a[sid], b[sid]
        if not x.get("metrics") or not y.get("metrics"):
            changes.append({"id": sid, "status": "unscored"})
            continue
        for tx, ty in zip(x["metrics"]["targets"], y["metrics"]["targets"]):
            if tx["retained"] != ty["retained"]:
                changes.append(
                    {"id": sid, "target": tx["text"], "status": "improved" if ty["retained"] else "regressed"}
                )
    return {
        "schema": "rarespeech.compare.v1",
        "corpus_hash": left["corpus_hash"],
        "baseline": left["report_id"],
        "candidate": right["report_id"],
        "changes": changes,
        "note": "ASR proxy changes; confirm by listening. Different ASR configurations are a confound.",
    }


def audit_asr(left, right):
    """Compare recognizers on identical audio. Disagreement is not ground truth."""
    if left["corpus_hash"] != right["corpus_hash"]:
        raise ValueError("ASR audit requires identical selected corpus")
    a, b = unique(left["rows"]), unique(right["rows"])
    if set(a) != set(b):
        raise ValueError("ASR audit requires identical samples")
    changes = []
    for sid in a:
        x, y = a[sid], b[sid]
        if x.get("audio_hash") != y.get("audio_hash"):
            raise ValueError("ASR audit cannot compare different audio")
        if not x.get("metrics") or not y.get("metrics"):
            continue
        for tx, ty in zip(x["metrics"]["targets"], y["metrics"]["targets"]):
            if tx["retained"] != ty["retained"]:
                changes.append(
                    {
                        "sample_id": sid,
                        "target_id": tx["id"],
                        "text": tx["text"],
                        "left_retained": tx["retained"],
                        "right_retained": ty["retained"],
                    }
                )
    return {
        "schema": "rarespeech.asr-audit.v1",
        "left": left["report_id"],
        "right": right["report_id"],
        "disagreements": changes,
        "note": "Recognizer disagreement; neither side establishes correct pronunciation.",
    }
