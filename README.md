# SehatSaathi 0.5 · Team Diligence

Runnable API-first synthetic care-navigation prototype. Version 0.5 repairs the deployed audit findings with complaint-independent safety intents, contextual extraction, explicit uncertainty handling, provider diagnostics/cooldowns and expanded regression checks. See `UPGRADE.md` before updating an existing Git clone. Text/Hindi/Hinglish intake, adaptive follow-ups, local emergency bypass, deterministic caregiver ranking, editable Groq voice transcription and simulated booking. No diagnosis, prescriptions, real booking or dispatch.

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
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

The backend automatically loads `.env`; you do not need `source .env`. Existing environment variables take precedence. Use localhost or HTTPS for microphone permission. Supported browsers depend on MediaRecorder; the app chooses WebM/Opus or MP4 and keeps text input available.

## Groq account separation

- Account A: `GROQ_TEXT_API_KEY`, `GROQ_TEXT_MODEL=openai/gpt-oss-20b`. Structured extraction via strict JSON schema; local policy controls final routing.
- Account B: `GROQ_AUDIO_API_KEY`, `GROQ_STT_MODEL=whisper-large-v3`. Transcription preserves original language; it does not automatically translate to English.
- Clients are explicitly constructed separately in `backend/app/providers.py`. No default SDK account, credential sharing or quota bypass. Both keys remain backend-only.
- `TEXT_MODE=auto` uses live text when a key is configured; `rules` always uses the baseline; `live` requires a working text provider on the strict API. The UI uses an explicitly labelled local fallback when that text service fails. Local established emergencies bypass the provider in every mode.
- Current official model/structured-output availability was checked in Groq documentation. No actual credentials or recordings were supplied; live calls and model comparisons remain unverified. Tests use HTTP transport stubs and label them as such.

## API

`POST /triage` is the strict organiser-facing response. `POST /ui/triage` calls the same core and wraps it with evidence, caregiver cards and concern metadata. `POST /transcribe` accepts multipart audio and returns an editable transcript. `GET /health` reports configured modes. `POST /ui/safety` performs a local-only safety preview for edited transcripts. `GET /openapi.json` exposes schemas. `/docs` is FastAPI Swagger UI (requires its CDN assets); `/explorer` is the self-contained custom API explorer.

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

Invalid inputs return 422; excessive requests 413; unsupported media 415; provider failures on `/triage` and `/transcribe` return 503 with a structured unavailable error. `/ui/triage` visibly falls back to local rules for text-provider errors/deadlines, and ends unresolved or outage cases with human assessment and no routine booking. Transport-level errors are outside the organiser success schema, an assumption requiring organiser confirmation.


## Broader intake

Stomach pain now receives complaint-specific questions, not the generic service menu. Dedicated pathways cover abdominal pain, headache, vomiting, diarrhoea, cough, sore throat, urinary symptoms, back pain, joint pain, rash, dizziness, injury, eye symptoms, ear pain, dental pain, fatigue and fever. Unfamiliar symptoms use a conservative `other` pathway and human-assessment fallback. This is broad complaint handling, not universal medical competence or diagnosis.

Extraction includes the presenting complaint, actual complaint text, severity, pain location, onset, duration, progression, associated symptoms and evidence-backed clinical findings. Local and live Groq extraction share the expanded schema. A prototype question policy chooses a relevant missing item, interprets yes/no in context, supplies answer buttons and stops after enough information or at most four questions for the current patient. Unknown answers never become negative safety screens.

Additional emergency evidence includes sudden severe abdominal pain, abdominal pain on touch, blood in vomit, black sticky stool, sudden extremely painful headache, vision loss, new confusion, airway swelling, inability to swallow saliva and back-pain neurological warning signs. Where no controlled organiser flag fits, the response still uses emergency_112/emergency with an empty controlled flag list and factual reasoning; no invented label is added. The organiser should confirm this documented contract gap. Emergency checks also run on voice transcripts and their edited text.

Unresolved safety questions or prompt in-person assessment needs suppress routine matching/booking. Other symptoms with sufficient context use the available same-day doctor consultation as a coordination pathway, without implying it replaces necessary in-person or specialist care. Explicit procedure requests keep the direct workflow.

The old 46-test count and baseline scores are superseded by the results in `docs/VERIFICATION.md` and `evaluation_0_5/organiser/metrics.json`. The expanded prototype deliberately asks safety questions on some cases that the supplied labels route immediately; higher supplied-label agreement is not claimed. See `docs/BROAD_INTAKE.md` for source-to-rule mappings and known limitations, and `UPGRADE.md` for local replacement steps.

## Run checks and evaluation

```bash
python -m pytest -q
node --check frontend/app.js
python scripts/verify_release.py
python scripts/evaluate_safety.py --mode both --out evaluation_0_5/previous_216_suite.json
python scripts/evaluate.py --mode rules --split all --out evaluation_0_5/organiser
```

The suite checks configured policies for all 45 named complaint categories and a conservative `other` fallback, plus all nine controlled emergency pathways, negation/history/hypothetical cases, late emergencies, short replies, corrections, patient isolation, eligibility, API invariants, real FFmpeg decoding/silence rejection, provider failures, separate account headers and mocked transcription. Provider stubs are not live API verification.

Current checks and measured results are in `docs/VERIFICATION.md`. On all 340 supplied rows the current rules achieve care macro-F1 0.7228 and emergency detection 56/56, with zero false emergencies against those labels. Label agreement is lower than the uploaded baseline (0.7958 care macro-F1), because the policy asks more questions instead of immediately routing some underspecified cases. These descriptive results are not clinical accuracy. Earlier `evaluation/` and `evaluation_all/` outputs are historical; use `evaluation_0_5/` for this release.

The organiser grouping script can also generate a 103-row validation subset, but rules were authored after inspecting the supplied data. Grouping alone does not make this a blind evaluation. No training or retrieval is used. Current full matrices are in `evaluation_0_5/organiser/metrics.json`.

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


## Version 0.5 safety repair and review

Read `docs/SAFETY_0_5.md` for the implementation/source mapping, `docs/VERIFICATION.md` for measured limits and `docs/CLINICAL_REVIEW.md` plus `docs/clinical_review.csv` for the pending qualified review. No model is trained and no clinical approval is claimed. The 96-case audit is now development regression data, not a blind test or training-ready clinical dataset.

The strict `/triage` contract is retained. UI metadata adds structured complaint/body-site/trigger understanding, safety evidence and safe provider-failure diagnostics. `/health` exposes process-local provider connectivity/error/cooldown status without patient text or keys. Simple supported follow-up answers can run as `rules_contextual_answer`; this is explicitly not a live model call.

A 429 respects Retry-After and does not immediately retry or switch accounts. Full local validation remains mandatory for provider output. The portable request schema and explicit low GPT-OSS reasoning effort are implementation changes, not proof that an account's live requests succeed.

```bash
# Offline: no provider call
python scripts/check_provider.py
# Opt-in local diagnostic: at most two synthetic requests, uses text-account quota
python scripts/check_provider.py --allow-live
```

The possible medication-excess case receives urgent human assessment with no routine questions/matches. This is deliberately distinct from automatic ambulance classification or a toxic-dose calculation; the original provisional audit label remains unchanged and requires adjudication.
