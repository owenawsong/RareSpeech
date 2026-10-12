from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from pathlib import Path

from . import __version__
from .audit import audit_corpus
from .corpus import corpus_hash
from .io import digest, unique
from .metrics import bootstrap, macro_accuracy, score_case
from .protocol import PROTOCOL_ID, analyze_protocol, balanced_scores, paired_analysis


def evaluate(cases, samples, transcripts, metadata=None):
    cases, samples, transcripts, metadata = deepcopy((cases, samples, transcripts, metadata))
    if not cases:
        raise ValueError("cannot evaluate an empty corpus")
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
    # Honor an explicit generation design; otherwise an interrupted multi-repeat
    # run can appear complete when its final repeats never reached samples.json.
    repeats = (metadata or {}).get("identity", {}).get("repeats")
    expected_missing = []
    if repeats is not None:
        if type(repeats) is not int or not 1 <= repeats <= 20:
            raise ValueError("declared repeats must be an integer between 1 and 20")
        observed_repeats = set()
        for sample in samples:
            repeat = sample.get("repeat")
            if type(repeat) is not int or not 1 <= repeat <= repeats:
                raise ValueError("sample repeat is missing or outside the declared repeat design")
            key = (sample["case_id"], repeat)
            if key in observed_repeats:
                raise ValueError("multiple samples for one declared case/repeat")
            observed_repeats.add(key)
        for case in cases:
            for repeat in range(1, repeats + 1):
                if (case["id"], repeat) not in observed_repeats:
                    expected_missing.append((case, f"{case['id']}--r{repeat}", repeat))
    # Missing cases must remain visible even for a partial audio import.
    present = {r["case_id"] for r in rows}
    if repeats is None:
        expected_missing = [
            (case, case["id"] + "--missing", None) for case in cases if case["id"] not in present
        ]
    for case, sid, repeat in expected_missing:
        if sid in smap:
            raise ValueError("sample ID collides with a missing declared repeat")
        rows.append(
            {
                "id": sid,
                "repeat": repeat,
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
    protocol = analyze_protocol(rows, cases)
    corpus_audit = audit_corpus(cases)
    headline_eligible = complete and protocol["recognizer_consistent"]
    measurement_hash = digest(
        {
            name: Path(__file__).with_name(name).read_text(encoding="utf-8")
            for name in ("metrics.py", "evaluate.py", "protocol.py", "audit.py")
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
        "research_protocol": protocol,
        "corpus_audit": corpus_audit,
        "summary": {
            "complete": complete,
            "headline_eligible": headline_eligible,
            "automatic_accuracy": score if headline_eligible else None,
            "observed_accuracy": score,
            "interval": bootstrap(rows) if headline_eligible else None,
            "interval_method": "category-stratified lexical-dependency cluster bootstrap; 1000 draws, seed 17",
            "interval_unavailable_reason": (
                "incomplete_coverage"
                if not complete
                else "mixed_recognizer_configurations"
                if not protocol["recognizer_consistent"]
                else corpus_audit["dependency_design"]["interval_unavailable_reason"]
            ),
            "scored": sum(r["metrics"] is not None for r in rows),
            "samples": len(rows),
            "label": "ASR target-retention proxy; not verified pronunciation accuracy",
        },
        "reviews": [],
        "review_summary": {
            "reviewed": 0,
            "required": sum(len(r["case"]["targets"]) for r in rows if r["variant"] != "control"),
            "verified_accuracy": None,
            "balanced_protocol_id": PROTOCOL_ID,
            "balanced_primary_target_accuracy": None,
            "balanced_all_target_accuracy": None,
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
        key = (review["sample_id"], review["target_id"], review["rater"].strip().casefold())
        if key in seen:
            raise ValueError("duplicate rater decision; remove old decision explicitly before replacing")
        seen.add(key)
        validated.append(review)
    grouped = defaultdict(list)
    for review in validated:
        grouped[(review["sample_id"], review["target_id"])].append(review["verdict"])
    required, decided, passed, disputed = 0, 0, 0, 0
    review_rows = deepcopy(report["rows"])
    for row in review_rows:
        row.pop("review_targets", None)
    review_by_id = unique(review_rows)
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
                reviewed = review_by_id[row["id"]]
                reviewed.setdefault("review_targets", []).append(
                    {"id": target["id"], "text": target["text"], "retained": votes[0] == "pass"}
                )
            elif len(votes) >= 2:
                disputed += 1
    for row in review_rows:
        if row["variant"] != "control":
            reviewed_targets = row.pop("review_targets", [])
            row["metrics"] = (
                {"targets": reviewed_targets}
                if len(reviewed_targets) == len(row["case"]["targets"])
                else None
            )
    reviewed_scores = balanced_scores(review_rows, report["cases"])["scores"]
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
        "balanced_protocol_id": PROTOCOL_ID,
        "balanced_primary_target_accuracy": reviewed_scores["primary_target_retention"]
        if required and decided == required
        else None,
        "balanced_all_target_accuracy": reviewed_scores["all_target_retention"]
        if required and decided == required
        else None,
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
        if a[sid]["case_id"] != b[sid]["case_id"]:
            raise ValueError("comparison requires identical sample-to-case assignments")
        if a[sid].get("metrics") and b[sid].get("metrics"):
            if [t["id"] for t in a[sid]["metrics"]["targets"]] != [
                t["id"] for t in b[sid]["metrics"]["targets"]
            ]:
                raise ValueError("comparison requires identical target occurrence IDs")
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
        "paired_analysis": paired_analysis(left, right),
        "note": "ASR proxy changes; confirm by listening. Different ASR configurations are a confound.",
    }


def audit_asr(left, right):
    """Compare recognizers on identical audio. Disagreement is not ground truth."""
    if left["corpus_hash"] != right["corpus_hash"]:
        raise ValueError("ASR audit requires identical selected corpus")
    a, b = unique(left["rows"]), unique(right["rows"])
    if set(a) != set(b):
        raise ValueError("ASR audit requires identical samples")
    if left.get("measurement_hash") != right.get("measurement_hash"):
        raise ValueError("ASR audit requires identical evaluator implementations")
    changes = []
    scored_pairs, target_pairs = 0, 0
    for sid in a:
        x, y = a[sid], b[sid]
        if x.get("audio_hash") != y.get("audio_hash"):
            raise ValueError("ASR audit cannot compare different audio")
        if not x.get("metrics") or not y.get("metrics"):
            continue
        if [t["id"] for t in x["metrics"]["targets"]] != [t["id"] for t in y["metrics"]["targets"]]:
            raise ValueError("ASR audit requires identical target occurrence IDs")
        scored_pairs += 1
        for tx, ty in zip(x["metrics"]["targets"], y["metrics"]["targets"]):
            target_pairs += 1
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
        "coverage": {
            "paired_scored_samples": scored_pairs,
            "expected_samples": len(a),
            "paired_targets": target_pairs,
        },
        "disagreement_rate": len(changes) / target_pairs if target_pairs else None,
        "note": "Recognizer disagreement; neither side establishes correct pronunciation.",
    }
