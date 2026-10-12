# Release preparation evidence · 2026-10-12

This records software and artifact checks, not scientific endorsement.

| Check | Observed result |
|---|---|
| Python tests / local Python 3.12 | 152 passed |
| Ruff | Passed |
| Frozen tracks | 128 core, 192 stress, 320 legacy; offsets, hashes and packaged parity verified |
| Published audio | 256 full-core plus 96 historical clips; every audio SHA-256 verified |
| Baseline reconstruction | Scores, report identities, both recognizer outputs and paired comparison reproduced from the bundled evidence |
| Submission validation | Both full-core captures eligible for the candidate automatic table; incomplete and placeholder identities rejected |
| Listening workflow | Real-audio packet built; organizer identity restoration tested; synthetic uncertain test vote remains unresolved |
| Imported JSON | Hostile counter markup and malformed audio fields rejected by the actual browser validator |
| Desktop and 390px layout | Dataset filters, measured results, paired comparison, report navigation and lexical-source links checked; no document overflow |
| Report audio | Real WAV metadata loads; listening decisions remain disabled before playback/pseudonym |
| Windows checkpoints | Unique atomic staging, interruption preservation and bounded lock retries tested |
| Distribution | Source/wheel builds; installed wheel locates the canonical dataset outside the repository |
| Credentials | Credential-shaped source scan across all three prepared projects found no matches |

Frozen example JSON/JSONL bytes are excluded from Git newline conversion. Original capture files, annotation changes and raw transcript fingerprints remain auditable across clones.

[CI results](https://github.com/owenawsong/RareSpeech/actions/workflows/ci.yml) cover Python 3.10/3.12 on Windows/Linux, source packaging and dataset regeneration. Optional TTS/ASR inference is represented by the measured captures, not rerun in every CI job.

## Remaining empirical work

Independent expert pronunciation acceptance rules, human reference recordings, reviewer qualification/agreement and ASR proxy calibration remain pending. Two model configurations do not establish broad model coverage. The release is a **candidate research toolkit with measured automatic baselines**, not a validated pronunciation leaderboard. See [validation plan](RESEARCH_PLAN.md).
