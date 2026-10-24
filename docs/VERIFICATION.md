# Verification — version 0.4

Measured 24 October 2026 against the user-uploaded team's source. Synthetic data and stub providers only; no clinical validation. This record supersedes the previous 0.2 verification claims.

| Check | Result |
|---|---|
| Python suite | 222 passed; one Starlette TestClient deprecation warning |
| New safety development suite | 215/216 checks passed; uploaded baseline 147/216 using identical evaluator |
| Active warnings in new suite | Update 52/52; baseline 18/52 |
| False emergencies in 164 negative cases | Update 1; baseline 3 |
| Unknown-answer conversations | No routine matches; explicit human-assessment result after cap |
| Ear-pain final step | Successful four-question flow concludes; provider-error, ungrounded-output and deadline stubs conclude with explicit fallback/human assessment |
| HTTP / DOM | Real Uvicorn + jsdom passed stomach/matching/simulated booking, emergency bypass, Hindi, transcript correction, ear/dizziness final outcomes, network error and retry; no DOM runtime errors |
| JavaScript | `node --check frontend/app.js` passed |
| Compatibility | Six-field strict response, 45 named families plus other, specialty roster/matcher, Swagger and custom explorer retained |
| Live Groq / real microphone | Not run; fake-provider tests do not establish live extraction accuracy |
| Visual browser / Docker / deployment | Not run here; no deployment or GitHub change performed |
| Clinical validation | Not performed; finite prototype rules require independent clinical review |

The remaining synthetic failure (`safety-138`) contradicts resolved historical framing with a seizure happening “abhi” (now). It is conservatively treated as emergency. The negative fixture label requires independent adjudication. See `evaluation_safety/README.md`; do not interpret 215/216 as clinical accuracy or a blind test result. The suite was authored before the patch, then used during development. Its variants are not independent clinical samples.

## Organiser data, all 340 rows

| Descriptive check | Uploaded baseline | Update |
|---|---:|---:|
| Care macro-F1 | 0.7958 | 0.7228 |
| Labelled emergencies detected | 56/56 | 56/56 |

Current urgency macro-F1 is 0.7440. Schema compliance is 1.0 for successful assessed responses. Matching proxies on the 209 nonempty-reference rows: Hit@1 0.3445, Recall@3 0.3676, NDCG@3 0.3504; 131 empty-reference rows excluded. No ID/active/role/radius violations occurred. These checks do not establish the correctness of medical triage or all eligibility conditions.

Agreement with the old labels decreased because this policy asks additional relevant questions rather than immediately matching some underspecified requests. No overall accuracy improvement is claimed. Rules were authored after inspecting supplied templates; this is descriptive label agreement. Complete current outputs are `evaluation_safety/organiser/`; the exact uploaded baseline metrics are `evaluation_safety/organiser_baseline_metrics.json`. Existing `evaluation/` and `evaluation_all/` files are historical and are not this release's current results.

## Reproduce

```bash
python -m pytest -q
python scripts/evaluate_safety.py --mode both
python scripts/evaluate.py --mode rules --split all --out evaluation_safety/organiser
node --check frontend/app.js
# Optional DOM QA: start a rules-mode server, npm install, then npm run test:ui
```

Run test/evaluation commands without live keys unless explicitly testing live mode. For the development safety suite, live execution requires `--allow-live` and an explicitly exported text key. Live errors are recorded separately, not silently counted as local success. The UI's separately tested availability fallback is deliberately distinct from this benchmark.

Before the demo, follow `UPGRADE.md`, confirm `/health` version 0.4.0, test real accounts/recordings and both desktop/mobile visuals, and repeat the four-follow-up conclusion flow on the deployment. The package does not contain `.env`, repository history or local dependencies.
