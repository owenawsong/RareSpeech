# Measured baseline appendix · core v1

These are original CPU recordings from **two configurations across two TTS architectures**, each covering the same 128 cases. They are automatic lexical diagnostics, not a broad model ranking or verified pronunciation assessment. One generation per case; stochastic robustness and voice diversity remain unmeasured.

Primary recognizer: faster-whisper small.en, English, CPU int8, beam 5, temperature 0, VAD off, previous-text conditioning off. Secondary: base.en with the same decoding policy. Both record actual model/config SHA-256 and runtime versions. No vocabulary prompt or transcript repair.

| Configuration | Balanced retention ↑ / small.en | Rare-content WER ↓ / small.en | Balanced retention / base.en | Target verdict disagreements | Evidence |
|---|---:|---:|---:|---:|---|
| Piper / en_US-danny-low | 18.75% | 17.09% | 10.16% | 19 / 128 | [Evidence](../examples/core-piper-danny/report.json) |
| Kokoro-82M v1.0 / af_heart (ONNX) | 32.81% | 11.87% | 22.66% | 29 / 128 | [Evidence](../examples/core-kokoro-heart/report.json) |

## Conditions / primary recognizer

| Configuration | Bare term | Short context |
|---|---:|---:|
| Piper / en_US-danny-low | 9.38% | 28.12% |
| Kokoro-82M v1.0 / af_heart (ONNX) | 31.25% | 34.38% |

Core corpus SHA-256: `f559cd383f70e35ab8419e7a4698beba2d81cce76369e9b163d4d34b8daf03db`. Evaluator source SHA-256: `081fc37a558eccdfff2916fcb67994ebf3350dc7718225154906395723158267`.

Recognizer disagreement signals uncertainty, not which recognizer is right. Audio is supplied for every measured sample; human votes remain empty. The paired intervals below reflect variation over these declared lexical clusters, conditional on the carrier/voice/ASR choices; they do not include ASR bias or listener uncertainty.

## Paired comparisons

- [core-piper-danny → core-kokoro-heart](../examples/comparisons/core-piper-danny--core-kokoro-heart.json): candidate minus baseline; paired lexical-cluster bootstrap.

## Reproducible identities

### Piper / en_US-danny-low

TTS revision: `weights-sha256:56a9ae9499e961514f060aac2866cb323a21e5989592fc4f208e56fdc323ab64`.

Public generation identity: [run JSON](../examples/core-piper-danny/run.json). Primary and secondary recognizer settings: [small.en](../examples/core-piper-danny/transcripts.jsonl), [base.en](../examples/core-piper-danny/transcripts-base.jsonl).

### Kokoro-82M v1.0 / af_heart (ONNX)

TTS revision: `weights-sha256:beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a`.

Public generation identity: [run JSON](../examples/core-kokoro-heart/run.json). Primary and secondary recognizer settings: [small.en](../examples/core-kokoro-heart/transcripts.jsonl), [base.en](../examples/core-kokoro-heart/transcripts-base.jsonl).

## Annotation correction

Before publication, the core builder inherited an incorrect condition label from the legacy bare-term case. The actual case IDs, synthesis text, target offsets and audio were unchanged. An audited metadata-only correction sets the intended `variant`; originals, source hashes, changed fields and the correction reason remain in each evidence folder's `provenance/`. Audio and transcript files retain their original hashes. All scores were recomputed on the corrected frozen core. No recordings or listening votes were relabeled as better performances.

## Licensing and limits

No model weights are redistributed. Kokoro-82M is Apache-2.0; the ONNX adapter uses the upstream model-files-v1.1 assets, voice af_heart, speed 1, English US, CPU with two threads. Piper Danny uses its upstream low-quality voice checkpoint and default synthesis settings. A third local evaluation used Piper Ryan, whose upstream training dataset is listed as CC BY-NC-SA 4.0; that voice's artifacts are excluded from this publication bundle rather than assigning them broader reuse rights. See the source voice model cards and [audio/provenance notes](../examples/README.md). The reference collection has no expert acoustic validation yet; familiar controls are not phonetic matches. This appendix cannot establish a causal rarity effect, naturalness, multilingual capability or model training exposure.

Historical 32-case integration pilots remain available separately; they are not core-v1 submissions and do not define the headline protocol.
