# Verification record

Measured in this working session, 24 October 2026. Synthetic data only.

| Check | Result |
|---|---|
| Automated suite | 46 passed, one Starlette TestClient deprecation warning; no failures |
| Python dependencies | `pip check`: no broken requirements; pinned requirements dry-run satisfied |
| JavaScript parsing | `node --check frontend/app.js`: passed |
| Real local HTTP process | Uvicorn started; GET /health, /, /assets/app.js, /openapi.json returned 200 |
| Real HTTP triage | Uncontrolled bleeding returned emergency_112/emergency, severe_bleeding, no matches or question |
| Audio media validation | Synthetic tone decoded; silence and invalid container rejected in tests |
| Account separation | Independent text/audio client instances and distinct synthetic auth headers verified with HTTPX MockTransport |
| Provider handling | Mocked rate limit retries bounded to two; malformed extraction rejected; local emergency bypass survives outage |
| Exporter | 340 supplied-example rows exported with source IDs and provisional columns; this is not hidden-test output |
| Evaluation | Full 340-row and 103-row scenario-group-disjoint descriptive results included with split, predictions, confusion matrices and latency |
| Approach write-up | Exactly two PDF pages, embedded fonts, rendered and visually inspected |
| Browser screenshot/visual QA | Not completed: no Chromium executable; attempted download returned an invalid archive. No browser success claimed |
| Live Groq calls | Not run: no account credentials supplied |
| Real microphone transcription | Not run; synthetic media and stubbed transcription adapter tested |
| STT model comparison | Script included; no representative recordings or credentials, so no measured winner claimed |
| Docker build/run | Not run: Docker unavailable in this environment. Dockerfile/Compose provided |
| Hidden-test predictions | Cannot generate without hidden input and confirmed CSV specification |
| Recorded demo video | Storyboard included; video still needs screen/microphone recording by the team |
| Clinical review | Not performed; prototype is not clinically validated |

## Remaining before submission

1. Enter two separate Groq account credentials in local `.env`, load them or run Compose, then test text and voice live. Check current model access in each account.
2. Run the manual flows in DEMO_SCRIPT.md on mobile and desktop, including permission denial, cancel, silence, retries, negation and corrected numbers. Browser-level controls have not been visually verified here.
3. Run Docker locally if Docker is the chosen delivery path. The native Python app was started and exercised over HTTP.
4. Obtain hidden-test input/CSV columns and export with the same core. Do not submit the supplied-example CSV as hidden predictions.
5. Record the <=3-minute video. Upload/push the repository yourself only when authorised; no remote repository or deployment was created.
6. Confirm organiser assumptions: future availability, history item schema, urgent in-person care mapping, noisy annotations, clinical thresholds and AI-assistance/originality disclosure.

The local rules baseline is functional without keys. The API integrations are implemented and stub-tested; their live operation remains unverified. This distinction is visible in the interface and health endpoint.
