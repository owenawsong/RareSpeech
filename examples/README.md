# Measured integration pilots

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
