# Validation plan

RareSpeech 0.2 is executable research software and a candidate collection. A trustworthy pronunciation benchmark needs independent evidence beyond successful code tests and baseline runs.

## 1. Lexical acceptance

For each of the 64 primary terms, two qualified reviewers should confirm the English entry, the intended specialist sense, at least one acceptable pronunciation and any regional alternatives. Record the exact reference source, access date, reviewer qualifications, decision and disagreements. Dictionary-entry existence is currently checked; accepted acoustic readings are not yet adjudicated. In-domain familiarity is not general familiarity.

Before a validated dataset revision, freeze the accepted reference forms and inclusion rules. Withdraw disputed items transparently with a new corpus identity; do not silently edit the current tracks.

## 2. Recognizer calibration

Record at least two qualified human speakers per term, in both core conditions, with documented acceptable readings. Include diverse accents within the declared English scope. Keep target vocabulary out of the ASR prompt. Run the same recognizer revisions used for model evaluation.

Measure how often ASR rejects known-correct rare speech, by term, category, condition and rarity stratum. Include adjudicated TTS successes and failures to measure ASR false acceptance as well. Report uncertainty and the sampling design. Multiple recognizers agreeing is insufficient to establish acoustic correctness.

## 3. Listening study

Use `rarespeech study` to make a randomized packet. Model identities, source sample IDs and ASR verdicts are absent from the participant files; reference text remains visible. The organizer key is outside the served packet and must be withheld until ratings are complete. Listeners can still recognize voices; this is not a guarantee of complete perceptual blinding.

Assign at least two independent qualified raters per occurrence. Include training items, reference examples and an explicit pronunciation rubric. Register the listening protocol and exclusion rules before collecting results. Record reviewer expertise and the rate of uncertain judgments; do not convert uncertainty to a pass. Audit apparent successes as well as apparent failures.

Report raw agreement, disagreements, adjudication records and completed coverage before a pronunciation aggregate. Browser playback enables judgments but is not proof that someone listened attentively. Distinct pseudonyms do not establish independence.

## 4. Sampling and power

The current collection has 64 curated families and 63 declared lexical-dependency clusters across eight domains. It is not a random sample of all rare English words. Sixteen short carrier templates limit carrier generalization. Written character count is not phonetic complexity. Cross-domain conclusions need a larger, independently curated sample and a study-specific power analysis.

Resample related families together for conditional collection-level intervals. Shared lexemes in the original legacy corpus connect all nominal families within each domain, so its old family-only intervals are invalid and now withheld. Bootstrap intervals do not address recognizer bias, ambiguous lexical senses or annotator expertise.

## 5. Model coverage

Bundled core baselines compare explicit open-model voice configurations with one generation per case. They demonstrate the evaluation pathway, not comprehensive model rankings. Independent submissions should add architectures, frontends and voice settings, with immutable model and recognizer revisions. Generation repeats, accents, rate and voice selection require declared designs. A model author should disclose the relationship to any evaluated model.

## Release decision

The software can be released with candidate status and inspectable automatic results. A validated pronunciation leaderboard should wait for steps 1–3 and a defined listening study. The name and score must never imply absence from model training or a universal naturalness ranking.
