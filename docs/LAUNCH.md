# Launch copy

## Short description

RareSpeech evaluates the words that whole-passage WER can hide: a fixed rare-term core, stress cases, original audio evidence and blinded listening tools.

## Suggested announcement

One specialist word can be the reason a sentence matters. WER gives it the same weight as every other word.

I built RareSpeech to inspect that failure mode in text-to-speech. Its 128-case core measures 64 uncommon terms bare and in neutral context, with equal domain/family/condition weights. A separate 192-case stress track probes repeated terms, longer passages and familiar controls.

The release includes full-core recordings from Kokoro and Piper, a second-recognizer audit, term-level audio/transcript evidence, paired cluster comparisons and blinded listening packets. Bring your model, speech endpoint, command or existing WAV files. The reports work offline.

This is a candidate research benchmark, not a validated pronunciation leaderboard. Automatic retention is an ASR proxy; independent expert references and listening calibration are the next empirical steps. Contributions from speech researchers and terminology reviewers are especially welcome.

[Repository](https://github.com/owenawsong/RareSpeech)

## Demonstration sequence

1. Show WER beside balanced rare-target retention for a named configuration.
2. Open a term, play the original recording and inspect the transcript alignment.
3. Show a recognizer disagreement without claiming which recognizer is right.
4. Open the model-blind listening packet and the exported submission table.

Share actual evidence and the protocol. Do not claim unseen training vocabulary, human-calibrated WER, broad model superiority or cross-hardware speed rankings. Ask authors before suggesting additions to their model cards; no unsolicited bulk outreach.
