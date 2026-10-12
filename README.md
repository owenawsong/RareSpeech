<p align="center"><img src="assets/hero.svg" alt="RareSpeech — Long-tail lexical fidelity for text-to-speech" width="100%"></p>

<p align="center"><strong>The rare word can be the whole point of the sentence.</strong><br>Evaluate it explicitly. Report it beside WER. Publish the evidence.</p>

<p align="center"><a href="#quickstart">Quickstart</a> · <a href="docs/TECHNICAL_REPORT.md">Technical report</a> · <a href="docs/BASELINES.md">Measured baselines</a> · <a href="docs/METHODOLOGY.md">Protocol</a> · <a href="docs/SUBMISSIONS.md">Model-card integration</a></p>

## What does a low WER leave out?

In a thirty-word passage, substituting the one specialist term can produce just **3.3% WER**. The central information may still be lost. Conversely, ASR may reconstruct the intended spelling from incorrectly pronounced audio.

**RareSpeech measures lexical fidelity on uncommon English terms.** It pairs whole-passage WER with balanced retention of precisely anchored rare-word occurrences, inspectable audio and a separate listening-review protocol.

> **Research status:** v0.2 is working evaluation software with a candidate collection and measured open-model baselines. Automatic retention is an **ASR proxy**, not pronunciation accuracy. Expert pronunciation references and independent acoustic calibration remain pending. This is not a universal TTS-quality leaderboard.

## A defined benchmark with a complete evaluation pathway

| Layer | Included |
|---|---|
| **Core v1** | 128 cases: 64 specialist term families, eight domains, bare and short-context conditions. |
| **Stress v1** | 192 cases: repeated occurrences, longer contexts and documented familiar controls. |
| **Frozen history** | Original v0.1 corpus and measured integration pilots remain reproducible. |
| **Balanced analysis** | Equal domain / family / condition weighting; controls stay separate. |
| **Careful uncertainty** | Paired lexical-dependency bootstrap; unsupported intervals are withheld. |
| **Bring your pipeline** | Persistent Python adapters, shell-free commands, speech APIs or generated WAVs. |
| **Inspectable evidence** | Original audio, target alignment, WER, condition/category breakdowns and recognizer disagreement. |
| **Independent review** | Randomized listening packets with model/source IDs and ASR verdicts concealed. |
| **Model-card output** | Frozen-track checks, provenance, submission JSON, Markdown tables and an ASR-proxy badge. |

<p align="center"><img src="assets/recognizer-sensitivity.svg" alt="Actual core-v1 lexical retention differs between Whisper small.en and base.en on the same recordings; neither is verified pronunciation accuracy" width="100%"></p>

### The long tail, with its source attached

**Mineralogy · Botany · Manuscript studies · Linguistics · Zoology · Astronomy · Mathematics · Musicology**

`omphacite` · `anaptyxis` · `opisthograph` · `pterygopodium` · `sesquialtera`

Every occurrence has exact character offsets, a lexical source link and frequency provenance. Zipf zero means below the frequency list's coverage; it does not prove absence from training. Terms still await expert acoustic acceptance rules. [Dataset card →](data/DATASET_CARD.md)

## Quickstart

Python 3.10+. Core scoring and report generation have **no third-party runtime dependencies**. Datasets and report assets are included in the Python package.

```bash
git clone https://github.com/owenawsong/RareSpeech.git
cd RareSpeech
python -m pip install -e .
rarespeech validate
rarespeech corpus-audit --out audit.json
python scripts/build_site.py
rarespeech serve site
```

Open **http://127.0.0.1:8765**. The dataset explorer and evidence reports run locally without a cloud judge, telemetry or remote fonts.

### Evaluate your model

Configure an [adapter](examples/README.md), then run:

```bash
python -m pip install -e ".[asr]"
rarespeech benchmark --adapter adapter.json --model-label MyModel --out runs/model
rarespeech serve runs/model/report
rarespeech submission --report runs/model/report/report.json --out submissions/model
```

The default is the complete core track. `--track stress` selects stress cases; `--track legacy` reproduces the original collection. `--variant isolated --limit 8` makes a quick diagnostic subset, explicitly ineligible as a full-track result. ASR downloads its model on first use. TTS dependencies and model weights are separate.

Already have audio? Use `rarespeech import-audio`. Already have transcripts? Use hash-bound JSONL and skip recognizer installation. [Complete instructions →](docs/QUICKSTART.md)

### Compare and review

```bash
rarespeech compare reports/baseline/report.json reports/candidate/report.json --out comparison.json
rarespeech study --reports reports/baseline/report.json reports/candidate/report.json --out study
rarespeech serve study
```

Comparisons require identical corpora, repeats, evaluator and recognizer configurations. Listening packets preserve original audio hashes while masking source identities. Keep the organizer key outside the shared packet; exported decisions can be restored with `rarespeech unblind`. [Submission and listening workflow →](docs/SUBMISSIONS.md)

## Results you can inspect

The [baseline appendix](docs/BASELINES.md) reports measured configurations, not a best-model claim. Every bundled core result includes source audio, immutable weights identity, recognizer settings and a second-recognizer audit. Historical author-model examples live in the appendix rather than defining the benchmark.

Missing generations, missing transcripts and never-generated declared repeats cannot silently improve a score. Blank transcripts count as failures. Mixed recognizer settings block a comparable aggregate. Human consensus remains a separate measurement; distinct pseudonyms alone do not prove expertise or independence.

## Research and contributions

- [Technical report](docs/TECHNICAL_REPORT.md): question, design, score and limitations.
- [Measurement protocol](docs/METHODOLOGY.md): normalization, aggregation, uncertainty and provenance.
- [Validation plan](docs/RESEARCH_PLAN.md): expert lexical review, reference recordings and listening-study requirements.
- [Contributing cases](docs/CONTRIBUTING_CASES.md): documented terms and defensible acceptance rules.
- [Contributing code](CONTRIBUTING.md): adapters, independent reproductions, tests and report improvements.

RareSpeech complements existing evaluation work, including [EmergentTTS-Eval](https://github.com/boson-ai/EmergentTTS-Eval-public) and [Open TTS Eval](https://github.com/inworld-ai/open-tts-eval). It does not claim to be the first rare-word or difficult-input benchmark.

## License and citation

Software/interface: [MIT](LICENSE). Original collection, annotations and author-created synthetic examples: [CC BY-SA 4.0](data/LICENSE), including frequency-derived metadata; see [NOTICE](NOTICE) and [audio attribution](examples/README.md#source-and-audio-notices). Optional models and dependencies retain their own licenses. Model weights are not redistributed.

Use [CITATION.cff](CITATION.cff). The technical report is software documentation, not a peer-reviewed paper. Built by [Owen Song](https://github.com/owenawsong), a student developer. The author maintains Inflect; that relationship is disclosed in its historical examples.
