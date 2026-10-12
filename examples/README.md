# Adapters and measured evidence

## Full-core baselines

`core-piper-danny/` and `core-kokoro-heart/` each contain 128 original recordings, primary/secondary recognizer outputs, the frozen corpus, run/sample identities, submission checks, and annotation-correction originals. See the [baseline appendix](../docs/BASELINES.md).

The score is balanced primary-target retention under a fixed ASR, not pronunciation accuracy. No human votes have been invented. The independently checked recognizer disagreement is evidence of measurement uncertainty.

Additional reproduction notes expose the synthesis factory, runtime versions and weight/config pins: [Piper](core-piper-danny/reproduction.json), [Kokoro](core-kokoro-heart/reproduction.json). They are labeled as release-time notes and do not rewrite the captured run identities.

### Reproduce the configurations

Install optional synthesis dependencies into isolated Python 3.12 environments. The bundled captures used **piper-tts 1.5.0 / onnxruntime 1.26.0**, or **kokoro-onnx 0.6.1 / onnxruntime 1.31.0**, with **faster-whisper 1.2.1 / ctranslate2 4.8.2** for recognition. Their packages and model weights are installed separately; none is distributed in the RareSpeech wheel.

For Piper, edit `adapter-piper.json` to point to the upstream Danny low ONNX checkpoint and its adjacent JSON configuration. For Kokoro, edit `adapter-kokoro-onnx.json` to use the upstream model-files-v1.1 `kokoro-v1.0.onnx` and `voices-v1.0.bin`; af_heart, English US, speed 1, CPU with two threads. Record the actual SHA-256s in your adapter identity. [Source Kokoro assets](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1).

```bash
rarespeech generate --adapter adapter.json --model-label MyConfiguration --out runs/reproduction
rarespeech transcribe --run runs/reproduction --out runs/reproduction/small.jsonl --model small.en
rarespeech transcribe --run runs/reproduction --out runs/reproduction/base.jsonl --model base.en
rarespeech evaluate --run runs/reproduction --transcripts runs/reproduction/small.jsonl --out runs/reproduction/report.json
rarespeech evaluate --run runs/reproduction --transcripts runs/reproduction/base.jsonl --out runs/reproduction/alternate.json
rarespeech audit-asr runs/reproduction/report.json runs/reproduction/alternate.json --out runs/reproduction/audit.json
rarespeech report runs/reproduction/report.json --audio-root runs/reproduction --out reports/reproduction
```

These adapters do not expose a generation seed, so freshly synthesized waveforms need not be byte-identical to the bundled recordings. Scoring the **bundled** immutable audio/transcripts reproduces the published results; a new generation is a new measurement.

### Source and audio notices

Original diagnostic carrier text and annotations are [CC BY-SA 4.0](../data/LICENSE); the author-created synthetic examples are shared under the same terms. Software remains MIT. No human reference recordings, cloned private speakers or model weights are included. Optional upstream model/software licenses remain separate.

[Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) identifies Apache-2.0 model licensing. The [Piper Danny model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/danny/low/MODEL_CARD) attributes its source to [Mimic3 voices](https://github.com/MycroftAI/mimic3-voices), listed as CC BY-SA 4.0.

A third local measurement used Piper Ryan. Its [source model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ryan/low/MODEL_CARD) lists a **CC BY-NC-SA 4.0 training dataset**. Those artifacts remain local and are excluded from this release's redistribution bundle. No broader output-license conclusion is claimed from the dataset notice alone.

## Historical integration pilots

The three report folders contain real, locally generated PCM WAVs, hash-bound
Whisper small.en transcripts, a second-recognizer base.en audit, and the complete
selected case definitions. They demonstrate the software workflow. They are not
official pronunciation or naturalness rankings.

Selection: first family from each of eight domains, isolated/dense/extended/control,
one generation per case, seed 17 where exposed. 32 clips per configuration.
Configurations: Inflect Nano v2, Inflect Micro v2, and Piper en_US Danny low.
Inflect is maintained by this project’s author. All use the same case selection
and evaluator. Real failure/uncertainty evidence is preserved.

Audio: Inflect uses 24 kHz, Piper 16 kHz. Original amplitudes and sample rates are
preserved. These are diagnostic clips, not a loudness-normalized blind preference
study. Original source voices are used; no human reference or cloned recording is
included. Upstream [Piper Danny model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/danny/low/MODEL_CARD)
references [Mimic3 voices](https://github.com/MycroftAI/mimic3-voices) (CC BY-SA 4.0).
Model weights are not redistributed.

The updated pilots reuse unchanged hash-checked clips from earlier local runs;
corrected musicology cases were regenerated. Reuse source identities are recorded.
Inference timing measures adapter calls and is not suitable for speed rankings.

The candidate corpus has dictionary-entry existence checks, but no independent
expert pronunciation validation. Human review fields are empty; no votes are
invented. ASR disagreement indicates uncertainty, not which recognizer is right.

To rebuild the publication folders after generating the named runs:

```bash
python scripts/publish_pilots.py
python scripts/build_site.py
```

This helper requires local runs; normal users can generate any report with
`rarespeech report`. The static explorer links to these folders.
