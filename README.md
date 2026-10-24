# CareCompass · Team Diligence

Runnable API-first synthetic care-navigation prototype. Text/Hindi/Hinglish intake, adaptive follow-ups, local emergency bypass, deterministic caregiver ranking, editable Groq voice transcription and simulated booking. No diagnosis, prescriptions, real booking, dispatch or public deployment.

## Start in Docker (recommended)

```bash
cp .env.example .env
# Edit .env locally to configure the TWO separate Groq accounts.
docker compose up --build
```

Open **http://localhost:8000**. The app runs without keys using the explicitly labelled local rules text baseline. Voice requires Account B; absent credentials produce an honest unavailable state rather than a fake transcript.

## Start on Mac / Linux without Docker

Python 3.12+ and FFmpeg are needed. Install FFmpeg on Mac with `brew install ffmpeg`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
# Open .env in your editor and enter credentials there, never in chat.
set -a
source .env
set +a
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Use localhost or HTTPS for microphone permission. Supported browsers depend on MediaRecorder; the app chooses WebM/Opus or MP4 and keeps text input available.

## Groq account separation

- Account A: `GROQ_TEXT_API_KEY`, `GROQ_TEXT_MODEL=openai/gpt-oss-20b`. Structured extraction via strict JSON schema; local policy controls final routing.
- Account B: `GROQ_AUDIO_API_KEY`, `GROQ_STT_MODEL=whisper-large-v3`. Transcription preserves original language; it does not automatically translate to English.
- Clients are explicitly constructed separately in `backend/app/providers.py`. No default SDK account, credential sharing or quota bypass. Both keys remain backend-only.
- `TEXT_MODE=auto` uses live text when a key is configured; `rules` always uses the baseline; `live` requires a working text provider and fails closed otherwise. Local established emergencies bypass the provider in every mode.
- Current official model/structured-output availability was checked in Groq documentation. No actual credentials or recordings were supplied; live calls and model comparisons remain unverified. Tests use HTTP transport stubs and label them as such.

## API

`POST /triage` is the strict organiser-facing response. `POST /ui/triage` calls the same core and wraps it with evidence, caregiver cards and concern metadata. `POST /transcribe` accepts multipart audio and returns an editable transcript. `GET /health` reports configured modes. `GET /openapi.json` exposes schemas. `/docs` is a self-contained API explorer with no CDN dependency.

```bash
curl http://localhost:8000/triage \
  -H 'Content-Type: application/json' \
  -d '{"user_input":"accident ke baad bleeding ruk nahi rahi","language":"auto","location":{"lat":28.54,"lng":77.27},"conversation_history":[]}'
```

This returns `emergency_112`, `emergency`, `severe_bleeding`, null follow-up and no caregivers. We deliberately do not reproduce the supplied dataset's unsupported chest-pain/breathlessness labels for that message.

```json
{
  "user_input": "yes",
  "language": "en",
  "location": {"lat":28.54,"lng":77.27},
  "conversation_history": [
    {"role":"user","text":"I have had fever for ten days around 103°F"},
    {"role":"assistant","text":"Is the person having difficulty breathing right now?","question_id":"breathing"}
  ]
}
```

The answer is interpreted against the preceding question and immediately escalates. History accepts user `text` or `content`, and the partial assistant shape shown in organiser examples. Question IDs are optional adapter metadata; they never enter the strict scoring response. Previous assistant assertions do not become patient facts.

Invalid inputs return 422; excessive requests 413; unsupported media 415; provider failures 503 with a structured unavailable error. No clinical route is fabricated to hide an outage. Transport-level errors are outside the organiser success schema, an assumption requiring organiser confirmation.

## Run checks and evaluation

```bash
python -m pytest -q
node --check frontend/app.js
python scripts/evaluate.py --split validation --out evaluation
python scripts/evaluate.py --split all --out evaluation_all
```

The suite exercises all nine emergency pathways, negation/history/hypothetical cases, late emergencies, short replies, corrections, patient isolation, eligibility, API invariants, real FFmpeg decoding/silence rejection, provider failures, separate account headers and mocked transcription. Provider stubs are not live API verification.

Measured rules baseline on all 340 provided rows: care macro-F1 **0.8698**, urgency macro-F1 **0.8736**, emergency recall **56/56**, emergency precision **1.0**, schema compliance **1.0**. Matching label-agreement proxies: Hit@1 **0.4976**, Recall@3 **0.5909**, NDCG@3 **0.5452** on 209 rows with nonempty relevance lists; 131 empty lists excluded. No ID/active/role/radius violations in this run. Original red-flag micro recall is **0.3214** because 38 emergency annotations use unsupported flags; proposed semantic corrections yield **1.0**, without applying changes to originals.

The scenario-group-disjoint validation subset has 103 rows; its easier sampled families produce 1.0 care/urgency F1. Do **not** present this as a blind held-out or hidden-test result: baseline rules were authored after inspecting the supplied dataset. No training/retrieval is used. `evaluation/split.json` publishes every grouping and split. Full and grouped confusion matrices, language results and core-only latency are in the metrics files. No official combined score or clinical validation is claimed.

## Hidden-test exporter

```bash
python scripts/export_predictions.py hidden_test.jsonl predictions.csv
# Live Account A extraction (requires loaded .env):
python scripts/export_predictions.py hidden_test.jsonl predictions.csv --mode live
# Adapt once the organiser confirms columns:
python scripts/export_predictions.py hidden_test.csv predictions.csv --columns id,response_json
```

Accepts nested JSONL, JSON arrays, or flat CSV with user_input/lat/lng and optional JSON history. Preserves supplied IDs; absent IDs receive row indices. Default CSV columns are **provisional**, not an official hidden-test format. Complex fields are JSON strings. Invalid input/provider failures abort without writing a partial final file. The included `evaluation_all/provisional_example_predictions.csv` is for the supplied 340 examples, **not hidden-test predictions**.

## Voice comparison

Record synthetic cases in English, Hindi and Hinglish. Manifest CSV columns: `path,language,reference`, with audio paths relative to the manifest; languages `en`, `hi` or `auto` for mixed speech.

```bash
python scripts/benchmark_stt.py recordings/manifest.csv --out stt_benchmark.json
```

This measures both requested Whisper models using only Account B, reporting WER/CER, locally detectable critical-fact/negation differences and latency. The comparison has not run here. Check age, duration, temperature and negation manually as the finite fact checker cannot detect every transcription error.

## Matching, clock and clinical assumptions

Roster parsing handles booleans and semicolon lists. Eligibility requires active status, compatible role, explicit procedural skills, radius for home visits and remaining same-day availability. Language is a preference rather than a hard filter. Haversine distance is ignored for virtual doctors. Score is `0.35*language + 0.30*proximity + 0.20*skill + 0.15*rating`; detailed normalisation is in `docs/ARCHITECTURE_AND_POLICY.md`.

Default clock is fixed at 24 Oct 2026, 08:00 IST to keep synthetic roster demos reproducible. The interface shows it. Set `REFERENCE_TIME=now` for a current-time demo. No future roster is supplied: tomorrow's requests may show candidates but disable simulated booking and mark availability unconfirmed. No estimated travel times are invented.

Unspecified injection routes trigger clarification; insulin gets no caregiver matches because the roster lacks explicit subcutaneous eligibility. Prolonged/high fever prompts medical-assessment concern, without claiming dengue or platelet changes. The taxonomy lacks urgent in-person physician assessment: same-day teleconsultation is a documented coordination fallback, not clinical equivalence. No caregiver can be presented as a replacement for necessary in-person emergency care.

## Privacy, attribution and originality

Use synthetic information only. History exists in browser memory, not persistent storage. No app text/audio logging or analytics; media is validated in temporary files and removed. Configured Groq services receive submitted text/audio; their retention policies and regional processing are not controlled by this prototype. The server binds locally by default, has bounded uploads and input lengths, no public authentication/rate limiting and is not production-ready. Do not expose it publicly without further controls.

Code was generated in this working session at the team's explicit request. Check event originality and AI-assistance disclosure rules before submission; no external repository was pushed and no public deployment was performed.

Attribution: Sanocare synthetic care-triage dataset v1 (2026), provided for the IIIT-Delhi hackathon; FastAPI, Pydantic, Uvicorn, HTTPX, Starlette, FFmpeg and pytest; Groq-hosted OpenAI GPT-OSS and Whisper model families; OpenAI ChatGPT assistance for code, analysis, documentation and tests. Official source URLs and policy limitations appear in the policy document. Retain upstream licences when redistributing dependencies.

## Submission contents

- Runnable API and frontend (single process, no Node build).
- Original synthetic datasets, audit evidence and proposed corrections.
- Adaptable predictions exporter, evaluation scripts/results, synthetic example predictions.
- Docker setup and pinned Python dependencies.
- `docs/Approach.pdf`: two-page submission write-up.
- `docs/DEMO_SCRIPT.md`: storyboard and recording checklist under three minutes.
- `docs/VERIFICATION.md`: actual test results and outstanding checks.

The frontend deliberately uses native HTML/CSS/JavaScript rather than React: this removes a build/dependency layer while providing the required complete flow. The API/core separation permits replacing it with React later without changing scoring behaviour.

