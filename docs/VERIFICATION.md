# Verification record - SehatSaathi 0.2

Measured in this session on 24 October 2026. Synthetic data only; this supersedes the 0.1 verification record.

| Check | Result |
|---|---|
| Python suite | 114 passed; one Starlette TestClient deprecation warning, no failures |
| Complaint coverage checks | 17 named complaint families plus other; English, Hindi and Hinglish examples |
| Safety tests | Existing nine controlled flags plus extended abdominal, headache, airway, vision, confusion, urinary and back-pain cases; negation, history, hypothetical, late-emergency and correction cases |
| Conversation tests | Contextual yes/no including reverse polarity, duration corrections, supplied facts skipped, four-question cap, patient changes, associated complaint emergency and duration isolation |
| Real HTTP / DOM integration | Passed with a real Uvicorn process and jsdom: stomach flow, choices, matching, simulated booking, emergency bypass, Hindi and edited-transcript safety. No DOM runtime errors |
| JavaScript parsing | node --check frontend/app.js passed |
| Dependency health | pip check passed; python-dotenv added for automatic non-shell .env loading |
| Audio checks | Real FFmpeg tone/silence/invalid-media checks and stubbed transcription adapter pass |
| Account separation | Independent clients and distinct synthetic authentication headers tested; no credential sharing |
| Provider failures | Rate-limit and malformed-output handling tested; local emergencies bypass broken text provider |
| Exporter | Re-generated 340 supplied-example rows, IDs preserved; columns provisional; not hidden-test predictions |
| Live Sarvam / real microphone | Not tested: user credentials and representative recordings are not available here |
| Visual browser / microphone QA | Not performed; jsdom checks behaviour, not visual rendering or browser media permissions |
| Docker | Configuration supplied, execution not tested here |
| Clinical validation | Not performed; source-backed prototype pathways still need mentor review |

## Actual supplied-data results

| Metric | All 340 examples | Scenario-group-disjoint 103-row subset |
|---|---:|---:|
| Care macro-F1 | 0.8219 | 0.7701 |
| Urgency macro-F1 | 0.8514 | 0.8799 |
| Emergency recall | 56/56 | 18/18 |
| Schema compliance | 1.0 | 1.0 |
| Matching Hit@1 | 0.4689 | 0.5224 |
| Matching Recall@3 | 0.5478 | 0.6567 |
| Matching NDCG@3 | 0.5077 | 0.5956 |

These are descriptive label-agreement results, not blind hidden-test results. Rules were authored after inspecting the dataset. Broader intake now asks questions on some cases that organiser labels immediately route, reducing agreement versus version 0.1 (care 0.8698, urgency 0.8736). No official score improvement is claimed. All 56 labelled emergencies remain detected. Matching metrics exclude empty relevance lists and inherit noisy-reference limitations; ID/active/role/radius violations are zero in this run.

Complete matrices, language results, red-flag noise comparisons and core-only latency measurements are in evaluation_all/metrics.json and evaluation/metrics.json. Provider modes are separated. Independent challenge tests are in tests/test_broad_intake.py and are not training data or clinical validation.

## Still required on the team's laptop

Follow UPGRADE.md, retain your private .env, confirm /health version 0.2.0, test both accounts live, check real microphone permissions/cancel/retry, verify mobile visuals and run Docker if used. Record the demo and obtain hidden input/official CSV columns before generating final predictions. Confirm the out-of-vocabulary emergency mapping with organisers. No repository push, public deployment, real booking or dispatch was performed.
