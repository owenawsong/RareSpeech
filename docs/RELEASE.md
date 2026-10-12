# Publish a software release

See [preparation evidence](VERIFICATION.md) for the checks performed on v0.2. The checklist below is intended to be repeated for each release.

## Reproduce the gates

```bash
python -m pip install -e ".[dev,rarity]"
python -m pytest
ruff check src scripts examples tests
python scripts/build_corpus.py
python scripts/build_core.py
python scripts/build_site.py
python scripts/check_release.py
python -m build
```

Inspect the explorer on desktop/mobile and a generated report with audio.
Review any published artifact for private information. Do not publish `_local/`,
`runs/`, credentials or model weights. Software license is MIT; dataset is CC BY-SA 4.0.

## Hosting

`site/` is ready for GitHub Pages, Cloudflare Pages or any static host. Build
command: `python scripts/build_site.py` after installing the local package.
Output: `site`. No server/database/API secrets are needed by the site.

The Pages workflow is manual. In repository settings, choose GitHub Actions as
the Pages source, then run the Deploy explorer workflow. Private-repo Pages
availability depends on the account plan. Repository visibility is a separate
owner decision; the workflow does not change it.

## Announce accurately

You can advertise a reproducible open toolkit, candidate rare-text collection,
real integration audio, offline evidence reports and review workflow. Do not
advertise a validated pronunciation leaderboard, unseen-training guarantee,
human-calibrated WER correction, or cross-hardware speed ranking.

Before publishing a verified benchmark ranking: validate term pronunciations,
recruit independent qualified listeners, evaluate both apparent successes and
failures, test the proxy against held-out review labels, and report uncertainty
and scope. That is empirical work, not a software switch.
