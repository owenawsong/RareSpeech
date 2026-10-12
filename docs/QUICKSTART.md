# Run your model

Python 3.10+ for the dependency-free evaluator. Python 3.12 is the tested optional TTS/ASR environment. Work in an isolated environment.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[asr]"
rarespeech validate
rarespeech corpus-audit --out audit.json
```

The installed wheel includes the datasets and report UI. Commands default to **core v1**, even outside the checkout. `--track stress` and `--track legacy` select the other frozen tracks. `--corpus custom.jsonl` overrides the track; subsets have different identities and cannot be advertised as canonical core results.

## 1. Connect a synthesizer

Copy [an adapter example](../examples/) and record the immutable model revision, voice, decoding settings and seed support. Weights are not included. Choose a Python factory, a command, an OpenAI-compatible WAV endpoint, or import recordings.

```json
{"type":"command","argv":["my-tts","--input","{text_file}","--output","{output}"],"model":"my-model","revision":"weights-sha256:ACTUAL_SHA256","seed_supported":false}
```

Commands are argument arrays, with no shell expansion. `{text}`, `{text_file}`, `{output}` and `{seed}` are literal substitutions. Never put keys in the command or JSON; endpoint adapters use `api_key_env`. Remote endpoints must use HTTPS and may charge per request.

```bash
rarespeech benchmark --adapter adapter.json --model-label MyModel --out runs/model
rarespeech serve runs/model/report
```

This generates, transcribes and evaluates the full core, then builds an offline report. The first ASR use downloads weights. A blank transcript is a scored failure; missing audio/transcripts remain missing and withhold the complete headline.

Optional local ONNX integration:

```bash
python -m pip install -e ".[asr,kokoro-onnx]"
# Download upstream weights separately; edit examples/adapter-kokoro-onnx.json.
rarespeech benchmark --adapter examples/adapter-kokoro-onnx.json --model-label Kokoro --out runs/kokoro
```

## 2. Run the stages separately

```bash
rarespeech generate --adapter adapter.json --model-label MyModel --out runs/model --repeats 3 --seed 17
rarespeech transcribe --run runs/model --out runs/model/asr.jsonl --model small.en --device cpu --compute int8
rarespeech evaluate --run runs/model --transcripts runs/model/asr.jsonl --out runs/model/report.json
rarespeech report runs/model/report.json --audio-root runs/model --out reports/model
```

`--resume` for generation requires an identical corpus, adapter identity, label, repeat count and seed. Successful audio is reused only after hash verification. Transcription resume checks audio identity, model weight/config fingerprints and decoding/runtime settings. Do not edit a published corpus or resume after undeclared changes to weights.

For a new selection, `--reuse-from runs/previous` reuses only identical case definitions under identical adapter/repeat/seed identities. Changed cases regenerate. Original call timings remain original; there is no cross-hardware speed ranking.

## 3. Import your own recordings or transcripts

Audio files use `<case_id>.wav` (for example `core.mineralogy.01.isolated.wav`), mono/stereo 16-bit PCM. Imported recordings have no measured generation timing.

```bash
rarespeech import-audio --audio-dir audio --model-label MyModel --provenance adapter-identity.json --out runs/imported
```

`--provenance` reads declared model identity/settings only; it never executes an adapter. Without that provenance, submission checks withhold canonical table eligibility. See [adapter-import.json](../examples/adapter-import.json).

Transcript JSONL uses **sample IDs**, plus exact audio SHA-256 and fixed recognizer identity:

```json
{"id":"core.mineralogy.01.isolated--r1","text":"omphacite","audio_hash":"ACTUAL_AUDIO_SHA256","engine":"your-asr/revision","settings":{"language":"en","model_weights_sha256":"ACTUAL_WEIGHTS_SHA256","model_config_sha256":"ACTUAL_CONFIG_SHA256"}}
```

Duplicate/unknown IDs and changed audio bindings are rejected. Do not repair transcripts against reference text or prime the recognizer with rare words. The shipped transcription command records actual ASR fingerprints automatically.

## 4. Audit, compare and listen

```bash
rarespeech transcribe --run runs/model --out runs/model/asr-base.jsonl --model base.en
rarespeech evaluate --run runs/model --transcripts runs/model/asr-base.jsonl --out runs/model/alternate.json
rarespeech audit-asr runs/model/report.json runs/model/alternate.json --out recognizer-audit.json
rarespeech compare reports/baseline/report.json reports/model/report.json --out paired-comparison.json
rarespeech study --reports reports/baseline/report.json reports/model/report.json --out study --seed 17
rarespeech serve study
```

The listening folder conceals model names and ASR verdicts. Its organizer key is saved **beside** the folder; keep it private. Listeners use pseudonyms and export occurrence decisions. Pass means present and acceptably pronounced; unfamiliar or unresolved cases are uncertain.

```bash
rarespeech unblind --key study.key.json --decisions listener.jsonl --out decisions
rarespeech review --report reports/model/report.json --decisions decisions/REPORT_ID.jsonl --out reviewed.json
rarespeech submission --report reviewed.json --out submission
```

Submission validation reconstructs scores and checks immutable track/evaluator/recognizer identities. It does not authenticate a model, inspect audio bytes, qualify listeners or confer scientific validation. See [submission rules](SUBMISSIONS.md) and [methodology](METHODOLOGY.md).

## Rebuild the explorer

```bash
python -m pip install -e ".[rarity]"
python scripts/build_corpus.py
python scripts/build_core.py
python scripts/build_site.py
rarespeech serve site
```

The generated site and reports are static. The inspection server binds localhost and is not a public application server. Deploy the static directory for public access.
