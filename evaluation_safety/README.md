# Safety development evaluation

The 216 synthetic cases (90 scenario groups) were authored by the developer/AI before this patch and frozen in `manifest.json`. They are separate from the organiser data, but are **not blind held-out data, clinician-reviewed ground truth, or clinical validation**. Language translations and polarity variants share groups. There is no training or fitted ML model.

Run `python scripts/evaluate_safety.py --mode both`. This runs rules and explicitly records live as not run unless both `--allow-live` and an exported `GROQ_TEXT_API_KEY` are supplied. Live evaluation consumes API quota. Do not publish keys or use real patient messages. Run the same evaluator against another checkout with `--project-root /path/to/baseline --out /tmp/baseline.json` in a separate process. The reports record case and evaluator hashes. Do not edit cases to improve reported scores.

| Rules check | Uploaded baseline | Update |
|---|---:|---:|
| All checks passed | 147/216 | 215/216 |
| Active-warning cases detected | 18/52 | 52/52 |
| False emergencies among 164 negative cases | 3 | 1 |

The remaining failed case `safety-138` says both “Last year” and “abhi daura pad raha hai” (a seizure happening now), then calls this resolved history. The recognizer treats the current wording conservatively. The fixture labels it negative; its contradictory meaning needs independent review. We retain and disclose the failure instead of rewriting ground truth or tuning to a perfect score.

`baseline.json` and `results.json` use exactly the same evaluator. Rules cover emergency invariants, limited questions/no repeats, unknown answers, late warnings and plain service controls. Permission to match does not guarantee roster availability. Provider errors are counted separately; failed live calls are never silently evaluated as successful rules calls.

Live Groq calls have not been run. Tests with fake providers exercise evidence grounding and UI failure behavior, not real model quality. Unknown answers are tested as conversations; this is not a complete clinical scenario distribution. The organiser results in `organiser/` are a separate descriptive label-agreement check and are not the safety-suite score.
