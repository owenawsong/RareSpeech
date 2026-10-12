# RareSpeech: evaluating lexical fidelity in long-tail TTS input

**Software technical report · version 0.2 · candidate research collection**
Owen Song

## Abstract

Whole-passage transcription error can underemphasize an uncommon term that carries the key information in a passage. RareSpeech accompanies WER with occurrence-anchored lexical retention on a curated English specialist-word collection. A fixed core track tests 64 term families across eight domains, both bare and in short neutral context. A separate stress track examines repeated targets, longer passages and familiar controls. The toolkit preserves configuration and audio provenance, balances category/family/condition contributions, supports paired dependency-cluster comparisons, and exports model-concealed listening packets. Automatic scores remain recognizer-dependent proxies. Expert pronunciation references and independent acoustic calibration are required before perceptual benchmark claims.

## 1. Research question

How faithfully does a complete TTS pipeline deliver designated uncommon lexical content? This includes its text normalization and pronunciation frontend; errors cannot automatically be attributed to the acoustic model. RareSpeech does not measure universal quality, naturalness, emotional expression, spoken-frequency rarity or training exposure.

## 2. Design

Core v1 has 128 authored cases: 64 terms, eight domains and two conditions. Stress v1 has 192 additional cases: repeated terms, long passages and familiar controls. The original 320-case pilot collection is separately preserved. Lexemes and written-frequency annotations originate from the frozen original collection; no guessed phonetic references are added.

Short contexts use sixteen neutral carrier templates. Each core case contains one separately anchored primary term; stress repetitions have multiple exact occurrence spans. Cross-family neighbors are excluded from the new tracks. An explicit morphology cluster connects `opisthograph` and `opisthographic`, giving 63 declared clusters. This structure addresses known lexical reuse, not all possible dependence between terms.

Rarity uses wordfreq 3.1.1's large English list. Zipf zero indicates below-list coverage; it is not proof of absence. Character-length-matched familiar controls are available where the small documented control lexicon permits, with nearest-length alternatives explicitly recorded. Meaning, phonetics, stress and spoken duration are not matched; control differences cannot establish a causal rarity penalty.

## 3. Measurements

WER is the count of substitutions, deletions and insertions divided by reference tokens. Conservative tokenization retains spelling and diacritics. Only explicit authored aliases alter a target's lexical reference. Minimum-edit alignment uses a deterministic tie policy; repeated words can remain acoustically ambiguous despite deterministic localization.

For each target occurrence, automatic retention is one if every aligned reference token matches, zero otherwise. The balanced primary score averages primary occurrences within generation, generations within case, cases within condition, conditions within family, and families within domain; domains receive equal weights. Neighbor-inclusive retention and the historical category-macro occurrence score are reported separately. None is a pronunciation rating.

Missing generations/transcripts and never-generated declared repeats remain unscored. Blank transcripts are failures. Complete aggregates require complete declared coverage and a consistent recognizer. Official-track identification additionally requires the frozen corpus hash. Transcript and listening decisions bind to the exact generated audio hash.

## 4. Uncertainty and comparison

Paired comparisons use the same corpus, sample/repeat design, evaluator and recognizer. Related families stay together during category-stratified cluster bootstrap resampling. The original corpus's dense neighbors link all eight families within each domain, leaving only one cluster per domain; its family-only intervals were overconfident and are now withheld. Intervals estimate collection-level sampling variation under the declared design and do not correct systematic ASR error.

## 5. Reproducible baselines

See [the measured baseline appendix](BASELINES.md) for generated audio, configurations, hashes, WER, balanced retention and a second-recognizer audit. The appendix is generated from measured runs. Original author-model pilots are historical integration examples and are not the headline results.

One voice configuration does not summarize an entire model. Two Piper voices do not add a second architecture. Single-generation results do not estimate stochastic synthesis variance. Runtime timings include adapter calls and writing, exclude model load, and are not TTFA or a comparable performance leaderboard.

## 6. Listening review and remaining validation

Participant packets conceal source/model IDs and ASR verdicts and retain reference text. An organizer-only map supports later identity restoration. Qualified listeners judge presence and acceptable pronunciation, with uncertain decisions and disagreements preserved. Complete consensus from two distinct raters is a software gate, not evidence of expertise or independence.

The collection is curated, small and English-only. Some terms are familiar within their disciplines. Written frequencies and recurring carriers limit generalization. Correct rare speech can fail ASR, and incorrectly spoken speech can be reconstructed by ASR. Expert lexical adjudication, human reference recordings, inter-rater reliability and a preregistered sampling plan remain external requirements. [The validation plan](RESEARCH_PLAN.md) specifies them.

## Related work

- [EmergentTTS-Eval](https://github.com/boson-ai/EmergentTTS-Eval-public) evaluates challenging linguistic, expressive and prosodic scenarios.
- [Open TTS Eval](https://github.com/inworld-ai/open-tts-eval) provides reproducible transcript and acoustic measurements with provenance.
- [Syrdal et al., 2012](https://www.isca-archive.org/interspeech_2012/syrdal12_interspeech.html) measure TTS intelligibility through listener transcription across rates.
- [Faria et al., 2022](https://www.isca-archive.org/interspeech_2022/faria22_interspeech.html) illustrate the effects of reference and scoring choices on WER.
- [wordfreq](https://github.com/rspeer/wordfreq) provides the written-frequency estimates used here.

This report is software documentation, not a peer-reviewed publication. RareSpeech does not claim to be the first rare-word or TTS stress evaluation.
