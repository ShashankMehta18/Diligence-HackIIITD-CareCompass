# Version0.5 verification data

These are development regressions, not clinical validation, clinical accuracy or blind external tests. No model was trained. The 96 deployed-audit fixtures remain byte-identical to the original audit (SHA256 in deployment_manifest.json). The rules were subsequently improved using their findings, so they are now regression data.

`current.json` and `baseline_0_4.json` replay exactly the same96 fixtures, synthetic answer profile and question limit against isolated checkouts in rules mode. They have matching runner/case hashes. Do not compare the current offline count directly to the earlier mixed live/fallback deployment count as if only code changed.

| Offline check |0.4|0.5|
|---|---:|---:|
| Original provisional warning labels routed emergency immediately |7/28|27/28|
| Intended named complaint family |33/45|45/45|
| Full scripted interviews reaching final conclusion |20/20|20/20|
| Unknown-answer cases without routine matches |8/8|8/8|
| Strict response shape |96/96|96/96|
| Maximum follow-ups |4|4|

The remaining warning-label mismatch is LIVE-064 (medication excess). It now receives immediate urgent professional-assessment guidance, no further routine questions and no matches, rather than automatic ambulance classification. The more specific clinical source/decision and need for adjudication are documented in docs/SAFETY_0_5.md. The original provisional fixture label is not changed to manufacture a perfect result.

The source-authored names in the45 complaint checks are intended test topics, not medically adjudicated diagnoses. Matching them is an extraction regression result, not general NLP accuracy. Variants/templates are dependent; the audit's original broader data card and clinician review process remain applicable.

`previous_216_suite.json` reruns the older narrow development suite:215/216 pass, with its disclosed contradictory history/current case safety-138 still conservatively escalated. This is not broad medical validation. `organiser/` contains descriptive label-agreement results on the340 supplied rows; those are not a blind test either.

New development paraphrases, denial/history/uncertainty cases and fake-provider tests are in tests/test_release_0_5.py. They were authored/used during development and are not claimed to be an independently reviewed holdout. A qualified clinician and a genuinely separate evaluation set are still required.

Reproduce:

```bash
python scripts/verify_release.py
python scripts/verify_release.py --project-root /path/to/unchanged/0.4 --out /tmp/baseline.json
python scripts/evaluate_safety.py --mode both --out evaluation_0_5/previous_216_suite.json
```

Live/provider checks are deliberately separate. `python scripts/check_provider.py` makes no live call; `--allow-live` authorises at most two synthetic text-account calls and records safe error categories without printing keys or raw errors. A local/private .env is never included in the package. No live success is asserted by a fake transport test.
