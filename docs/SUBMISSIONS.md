# Report RareSpeech beside WER

RareSpeech's automatic metric is **balanced target retention (ASR proxy)**. A lower WER and a higher retention proxy are separate observations. Neither establishes naturalness or acceptable pronunciation.

## Recommended core result

Use the complete packaged `core` track. Declare an immutable model revision, voice, frontend and synthesis parameters in the adapter. Use one fixed unprompted recognizer; the toolkit records its weights and configuration hashes. Defaults use Whisper small.en, CPU int8, beam size 5, no VAD and no previous-text conditioning. A second recognizer can expose disagreement, not establish ground truth.

```bash
rarespeech benchmark --adapter adapter.json --model-label MyModel --out runs/model
rarespeech submission --report runs/model/report/report.json --out submissions/model
```

The output contains `submission.json` and `model-card.md`. Include the actual report URL/audio evidence when adding the table to a model card. Keep the track, corpus hash, evaluator hash, voice and recognizer configuration visible. A selected subset or a stress result cannot stand in for the core result.

Eligibility checks are software checks. They do not certify reviewer independence, expert acceptance of pronunciation references or completed recognizer calibration. Missing data and mutable/placeholder revisions block an eligible automatic-track submission. Errors are explicit; the command never invents missing scores.

## Compare configurations

```bash
rarespeech compare reports/baseline/report.json reports/candidate/report.json --out comparison.json
```

Both reports must share their corpus, sample/repeat assignments, evaluator source and ASR configuration. Paired analysis reports candidate minus baseline with lexical-dependency cluster resampling. It withholds intervals for incomplete or unsupported designs. Intervals quantify variation within the declared collection, not population pronunciation validity.

## Listening packets

```bash
rarespeech study --reports reports/a/report.json reports/b/report.json --out study --seed 17
rarespeech serve study
```

Give reviewers only the `study/` directory. Keep `study.key.json`, generated beside that directory, private to the organizer. Export participant decisions from the browser, then restore their report identities:

```bash
rarespeech unblind --key study.key.json --decisions reviewer.jsonl --out restored
rarespeech review --report reports/a/report.json --decisions restored/REPORT_ID.jsonl --out reviewed-a.json
```

Replace `REPORT_ID` with the matching source report's 64-character identity. Each report gets a separate restored JSONL file. Merge each reviewer's restored decisions once; duplicates are rejected. Pronunciation aggregates require complete qualified consensus. See the [rubric](REVIEW_RUBRIC.md) and [validation plan](RESEARCH_PLAN.md).
