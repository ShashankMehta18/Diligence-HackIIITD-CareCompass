# Verification — version 0.5

Measured 25 October 2026. This supersedes the 0.4 verification record. Synthetic cases only; clinical review, independent clinical validation, real provider verification and public deployment verification remain pending.

| Engineering check | Result |
|---|---|
| Python suite |299 passed; one Starlette TestClient deprecation warning |
| Offline audit replay |96 cases, same frozen inputs and runner in baseline/current checkouts |
| Immediate emergency against original provisional warning labels |0.4 rules7/28;0.5 rules27/28; the remaining medication case receives immediate urgent human assessment instead |
| Named complaint extraction |0.4 rules33/45;0.5 rules45/45 on these specific intended-topic examples |
| Conversation endings |20/20 full scripts conclude;8/8 unknown-answer cases withhold matches; at most 4 questions, no repeated IDs |
| Strict response shape |96/96 audit cases; existing six fields/care enums retained |
| Older216 development suite |215/216,52/52 active warnings, one disclosed contradictory history/current negative control |
| HTTP / DOM |Real local Uvicorn + jsdom: existing stomach/matching/simulated booking, Hindi, emergency bypass, four-question ear/dizziness finals, network error/timeout/retry, chemical-eye emergency and urinary question routing passed; no DOM runtime errors |
| JavaScript |node --check frontend/app.js passed |
| Provider tests |Strict/portable payload, local validation, current-patient grounding, safe rejection diagnostics, no immediate429 retry, cooldown/audio isolation and local-answer quota avoidance tested with fake transports |
| Live Groq / real microphone / visual browser |Not verified for this release |
| Docker / deployed0.5 |Not run or deployed here |
| Clinical review |Pending; review kit supplied, not signed off |

## Important interpretation

The 96-case replay is a regression after inspecting the deployed audit. It is not blind validation. Both comparison checkouts run rules only: the earlier deployed audit mixed55 live,115 fallback and8 local responses over178 turns and is a different execution condition. No clinical accuracy or reliability guarantee is derived from either count.

LIVE-064 remains a mismatch against the original provisional emergency label. It no longer stalls or offers routine booking: it immediately recommends urgent professional assessment. This is a deliberate source-specific urgency distinction, not a hidden excluded failure. The frozen label still needs clinical adjudication. The older safety-138 contradiction is also retained and disclosed.

New paraphrase/control tests are developer-authored during development, not an external holdout. Finite vocabularies and temporal/coreference rules can still fail outside coverage. Passing a schema or ending a conversation cannot establish medically correct triage.

## Organiser data

On all 340 supplied examples: care macro-F1 0.7228, urgency macro-F1 0.7440, labelled emergencies 56/56 with zero false emergencies against these labels, successful response schema compliance 1.0. These equal the 0.4 descriptive results on that dataset. Matching proxies: Hit@1 0.3445, Recall@3 0.3676, NDCG@3 0.3504 on 209 nonempty-reference rows; 131 empty-reference rows excluded. No ID/active/role/radius violations in this check. Full outputs are evaluation_0_5/organiser/. Earlier evaluation directories are historical.

## Remaining verification

After applying the guarded update, run tests, start locally and confirm /health version 0.5.0. Use scripts/check_provider.py --allow-live with your privately configured text account to diagnose actual provider behavior. Fake transports do not prove that the account's schema, permissions, quota or model succeeds live. No keys from uploaded archives were read or used. Review the safe provider status/cooldown; this code cannot increase provider quotas.

Obtain qualified clinical review using docs/CLINICAL_REVIEW.md and clinical_review.csv, and test new independent examples across the intended patient population before clinical use/claims or model training. No GitHub push, Render deployment, real booking or dispatch was performed by this update.
