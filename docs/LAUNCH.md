# Launch copy

## Short description

RareSpeech inspects what text-to-speech loses when the words get unfamiliar.
An open toolkit, 320 specialist-text challenges, and audio reports you can inspect.

## Suggested announcement

I’m building speech models, and wanted to see what happens after the easy test
sentences end. RareSpeech tests uncommon terminology, dense passages, and repeated
entries across eight domains—from mineralogy to manuscript studies.

It reports whole-passage WER beside retention of the important target occurrences,
then lets you open the actual audio and record listening judgments. Bring a model,
a speech endpoint, a command, or WAV files you already have. Reports work offline.

The first release includes 320 authored candidate cases and real integration
audio from three model configurations. Automatic scores are ASR proxies; expert
pronunciation validation is still pending. I’m looking for qualified terminology
reviewers, model adapters, and reproducible hard cases.

Repository: https://github.com/owenawsong/RareSpeech

## Useful demonstration

1. Open a measured report.
2. Show whole-passage WER beside rare-target retention.
3. Open a suspected error and play the audio.
4. Show the expected/ASR alignment and recognizer disagreement.
5. Mark uncertain when the evidence does not establish a verdict.
6. Show the exported artifact/model-card table.

Advertise the workflow and evidence. Do not imply that the automatic retention
score is verified pronunciation accuracy, that the terms were absent from model
training, or that the integration pilots establish an overall winning model.

Share with communities whose members build or evaluate speech systems. Explain
what you measured and welcome criticism of the protocol. Ask permission before
proposing additions to someone else’s model card; avoid unsolicited bulk outreach.
