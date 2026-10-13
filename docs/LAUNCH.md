# RareSpeech · launch kit

Copy-ready text for the author to post. No outreach or posting is performed by this document.

## Positioning

**A companion to WER for uncommon-word failures in TTS.** The promise is specific: find which anchored specialist terms fail, inspect the original audio and publish enough evidence for someone else to check the result.

The release is a **candidate research toolkit with measured automatic baselines**. Its ASR-proxy score is usable for lexical diagnostics today; expert pronunciation references and independent acoustic calibration remain pending. Keep that distinction in every announcement.

## Repository description

Long-tail lexical fidelity for TTS: rare-target retention beside WER, original audio evidence, paired comparisons and blinded listening tools.

## Short post

A TTS model can miss the one specialist word that matters and still get a low whole-passage WER.

I built RareSpeech to inspect that gap: 64 uncommon English terms, 128 core cases, term-level scoring and original audio evidence. It includes Piper/Kokoro recordings, a second-ASR audit and model-card exports.

Retention is an ASR proxy, not verified pronunciation accuracy. Expert review and calibration are the next steps.

https://github.com/owenawsong/RareSpeech

Try it: https://owenawsong.github.io/RareSpeech/

## Developer / research announcement

### RareSpeech: what happens to the uncommon word?

In a thirty-word passage, replacing one specialist term can produce just 3.3% WER. The error is counted, but the word that carries the central information gets no special weight.

RareSpeech pairs whole-passage WER with explicitly anchored rare-target retention for text-to-speech. Its fixed core has 64 English specialist term families across eight domains, each tested bare and in short neutral context. A separate 192-case stress track examines repeated terms, longer passages and documented familiar controls.

The release includes:

- **256 full-core recordings** from Piper Danny and Kokoro af_heart, plus measured second-recognizer audits on the same audio.
- **Inspectable failures:** original WAVs, reference/transcript alignments, exact target spans and lexical/frequency sources.
- **Reproducible evaluation:** frozen tracks, model/audio/evaluator identities, complete-coverage gates and paired lexical-cluster comparisons.
- **A path beyond ASR:** randomized model-concealed listening packets, an organizer-only identity key and auditable decision exports.
- **Integration with your workflow:** Python/command/API/audio adapters and generated model-card tables. Reports run locally without a cloud judge.

This is a candidate research collection, not a validated pronunciation leaderboard. ASR can reject correct rare speech or reconstruct an intended spelling from incorrect pronunciation. Automatic retention remains an ASR proxy. Expert acceptance rules, human reference recordings and independent calibration are not yet complete.

I'm a student developer building this in the open. I'd especially welcome terminology reviewers, speech researchers and independent model reproductions. The useful next result is a better measurement with inspectable evidence.

Repository: https://github.com/owenawsong/RareSpeech

Try it: https://owenawsong.github.io/RareSpeech/
Technical report: https://github.com/owenawsong/RareSpeech

Try it: https://owenawsong.github.io/RareSpeech//blob/main/docs/TECHNICAL_REPORT.md
Measured baselines: https://github.com/owenawsong/RareSpeech

Try it: https://owenawsong.github.io/RareSpeech//blob/main/docs/BASELINES.md

## Release notes · v0.2

RareSpeech v0.2 introduces frozen core/stress tracks, balanced primary-target retention, paired lexical-dependency comparisons, recognizer provenance, submission checks and model-concealed listening packets.

The public evidence contains two complete 128-case configurations, primary/secondary ASR outputs and 96 historical integration clips. No human pronunciation results are claimed. Historical author-model examples remain separate from the headline protocol.

The original collection remains reproducible. Software is MIT; original collection/annotations and author-created synthetic examples use CC BY-SA 4.0, with separate dependency/model licenses and audio notices. No model weights are redistributed.

## Show it in four steps

1. **Start with a measured case.** Open a named configuration's report and show whole-passage WER beside balanced rare-target retention. Name the voice and recognizer.
2. **Inspect a failure.** Open one term, play its original recording and examine the target alignment. Describe what the transcript shows; do not treat it as a pronunciation verdict.
3. **Show the uncertainty.** Compare small.en and base.en on the same audio. A disagreement demonstrates recognizer dependence, not which recognizer is correct.
4. **Show the reusable output.** Open the model-card table and the listening packet. Explain the frozen-track requirements and the independent review still needed.

Use [the existing measured figure](../assets/recognizer-sensitivity.svg) or a real report screenshot. Keep the proxy label and configuration visible in cropped visuals. Use [the baseline appendix](BASELINES.md) for exact values instead of copying an unlabeled number.

## For a model author who asks how to report it

RareSpeech exports a model-card table after checking complete core coverage, fixed recognizer settings, immutable model identity and hash-bound evidence. Report **balanced target retention (ASR proxy)** beside WER, and link the actual report/audio. It complements your other evaluations; it does not certify pronunciation, naturalness or universal model quality.

[Submission workflow](SUBMISSIONS.md) · [Protocol](METHODOLOGY.md) · [External validation plan](RESEARCH_PLAN.md)

## Claims to keep out of launch copy

Do not claim unseen training vocabulary, proven acoustic correctness, human-calibrated scores, broad model superiority, causal rarity effects, cross-hardware speed rankings, peer review or established benchmark adoption. One voice configuration does not summarize a model, and a software eligibility check does not complete scientific validation.

Ask authors before proposing model-card additions. Share an actual result and its evidence; do not use unsolicited bulk outreach. A useful contribution request is concrete: review one documented term, reproduce one complete core configuration or help calibrate the ASR proxy against qualified listening.
