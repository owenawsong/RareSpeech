# Run your model

Python 3.10+. Run from the repository root. Core scoring has no external dependencies. Use an isolated environment for optional TTS/ASR dependencies.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e .
rarespeech validate
```

## Select cases

```bash
rarespeech export --category mineralogy --variant isolated --out prompts.jsonl
```

`--limit` selects the first N matching cases, not a random sample. To evaluate a balanced subset, make a JSONL corpus explicitly and supply `--corpus` to generation/import. Each selection has its own hash.

## Generate

Copy an example adapter and update its model paths/settings. Commands are JSON argument arrays; no shell expansion happens. `{text}`, `{text_file}`, `{output}`, and `{seed}` are literal placeholders. Standard input also receives the text. Never put credentials in argv.

```json
{"type":"command","argv":["my-tts","--input","{text_file}","--output","{output}"],"model":"my-model","revision":"checkpoint-sha256","seed_supported":false}
```

```bash
rarespeech generate --adapter adapter.json --model-label MyModel --out runs/model --repeats 3 --seed 17
rarespeech generate --adapter adapter.json --model-label MyModel --out runs/model --repeats 3 --seed 17 --resume
```

Resume requires the identical corpus/configuration/label/repeats/seed. Successful clips are reused only if their hashes match. Failed or missing clips retry. Record an immutable model revision; the tool cannot detect undeclared changes to files outside the config.

For changed corpora, use a **new** output directory with `--reuse-from runs/previous`. Reuse requires a matching adapter hash, label, repeats and seed, an identical case definition, and unchanged audio. Changed cases regenerate. The run records its source identity; copied timings belong to the original calls.

Python factories load once and expose `synthesize(text, output_path, seed)`, writing a 16-bit PCM WAV. `examples/model_adapters.py` includes Inflect, Piper and Kokoro examples. Install their dependencies and weights separately. Kokoro is an example integration, not part of the bundled measured pilots.

OpenAI-compatible speech adapters request WAV. Use HTTPS for remote endpoints and `api_key_env` for credentials. A provider may charge for requests. Private configs and commands are represented in reports by a hash; record relevant public generation settings separately.

## Import existing audio

Files: `<case_id>.wav`, mono/stereo 16-bit PCM. Convert other formats first. Missing files stay visible.

```bash
rarespeech import-audio --audio-dir my-audio --model-label MyModel --out runs/imported
```

Imported audio has no measured inference timing.

## Transcribe

```bash
python -m pip install "rarespeech[asr]"
rarespeech transcribe --run runs/model --out runs/model/asr.jsonl --model small.en --device cpu --compute int8
```

First use downloads the recognizer. Language is English; no initial prompt supplies target vocabulary. VAD is disabled to avoid dropping content. Interrupted transcription saves completed rows; rerunning re-transcribes successful clips. ASR package wheels may limit supported Python/platform combinations; Python 3.12 is the tested optional-ASR environment.

Add `--resume` to reuse transcripts only when sample ID, audio hash, recognizer name and settings match. Public recognizer names are not immutable checkpoint pins; record downloaded revisions separately for strict research replication.

## Bring your own transcripts

JSONL uses **sample IDs**, not case IDs:

```json
{"id":"mineralogy.01.isolated--r1","text":"The entry names omphacite...","audio_hash":"actual-sha256-from-samples.json","engine":"your-asr/model-revision","settings":{"language":"en"}}
```

Hash must match. Blank text is a scored error; absent rows are missing measurements. Duplicate/unknown IDs are rejected. Do not correct transcripts against reference text before scoring.

## Evaluate and inspect

```bash
rarespeech evaluate --run runs/model --transcripts runs/model/asr.jsonl --out runs/model/report.json
rarespeech report runs/model/report.json --audio-root runs/model --out reports/model
rarespeech serve reports/model
```

The portable folder includes HTML, local assets, audio, report JSON, and model-card Markdown. It can open directly from disk or through the localhost server. `serve` is a local inspection server, not hardened public application hosting. Deploy the static folder to public hosting.

## Review

Listen, use a pseudonym, mark pass/fail/uncertain, and export JSONL. Consult accepted pronunciation evidence; guesses are uncertain.

```bash
rarespeech review --report runs/model/report.json --decisions reviews.jsonl --out runs/model/reviewed.json
rarespeech report runs/model/reviewed.json --audio-root runs/model --out reports/reviewed
rarespeech compare runs/old/report.json runs/new/report.json --out changes.json
```

Duplicate merged decisions are rejected. To revise one, explicitly remove its previous entry from the report’s `reviews` array before reimporting. Checkpoint comparisons should use the same corpus, repeat IDs, and ASR settings.

## Rebuild the static explorer

```bash
python -m pip install "rarespeech[rarity]"
python scripts/build_corpus.py
python scripts/build_site.py
rarespeech serve site
```

Do not silently edit a published corpus. Changed hashes require newly generated/evaluated examples.
