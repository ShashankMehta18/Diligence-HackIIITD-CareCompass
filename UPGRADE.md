# Run the broader CareCompass version locally

Version 0.3 improves complaint-relevant follow-ups, limb extraction and safety tests, and includes your Swagger UI setup. The organiser-facing response schema is unchanged.

1. Stop the old running server with **Control + C**.
2. Extract the updated ZIP into a new folder. Keep your original project folder until the update works.
3. Open Terminal in the new `CareCompass` folder (type `cd `, drag that folder into Terminal, then press Enter).
4. Create a fresh environment and install the updated dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

5. Copy **only your existing `.env` settings file** from the previous project to this new folder. Keep the keys private. Do not copy the old `.venv` directory. If you prefer creating a new settings file, use the following only when `.env` does not already exist:

```bash
cp .env.example .env
open -e .env
```

Enter your two existing Groq account keys and save. Settings must have `NAME="value"` on one line. This version loads `.env` automatically, so **do not run `source .env`**. An explicitly exported shell variable takes precedence; a fresh Terminal avoids stale values from the old setup.

6. Start the updated app:

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

7. Open http://localhost:8000 and hard-refresh with **Command + Shift + R**. At http://localhost:8000/health, `version` should be `0.3.0`.
8. Try **Stomach pain**, answer **Mild**, then **No** to pain on touch, then give a duration and location. Try **Severe** and a sudden onset in a separate conversation to see emergency branching. All examples must be synthetic.
9. For checks, open a second Terminal in the same folder, activate `.venv` and run:

```bash
python -m pytest -q
```

Text works in labelled local rules mode without keys. Live Groq operation depends on your credentials/model access and remains to be tested on your laptop. FFmpeg is still required for voice: `brew install ffmpeg` on Mac if needed. No public deployment, real booking or dispatch is included.


## Applying the follow-up update to your existing Git clone

Stop the server, then copy these files from the updated folder to the same relative locations in the Git-connected project (replace the existing copies):

- `backend/app/complaints.py`
- `backend/app/intake.py`
- `backend/app/core.py`
- `backend/app/schemas.py`
- `backend/app/providers.py`
- `backend/app/config.py`
- `backend/app/main.py` (already includes Swagger at `/docs` and the original explorer at `/explorer`)

Copy the updated tests and documentation too if committing the complete change. The full ZIP is also runnable as a fresh project. Keep your private `.env` and existing `.git`; do not replace either. Dependencies did not change from 0.2. Restart from the main folder, check `/health` version `0.3.0`, hard-refresh the page and reset the chat.

Try 'I have pain in my knee', then Moderate → No injury → No swelling → Yes to weight bearing → Yes to movement → Two days. There should be no breathing question. Try swelling to see the heat/redness branch and 'Now I cannot breathe' in a separate synthetic chat to verify emergency handling.
