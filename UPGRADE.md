# Run the broader SehatSaathi version locally

Version 0.2 expands complaint extraction, follow-up selection, safety checks and tests. The organiser-facing response schema is unchanged.

1. Stop the old running server with **Control + C**.
2. Extract the updated ZIP into a new folder. Keep your original project folder until the update works.
3. Open Terminal in the new `SehatSaathi` folder (type `cd `, drag that folder into Terminal, then press Enter).
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

Enter your Sarvam API key and save. Settings must have `NAME="value"` on one line. This version loads `.env` automatically, so **do not run `source .env`**. An explicitly exported shell variable takes precedence; a fresh Terminal avoids stale values from the old setup.

6. Start the updated app:

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

7. Open http://localhost:8000 and hard-refresh with **Command + Shift + R**. At http://localhost:8000/health, `version` should be `0.2.0`.
8. Try **Stomach pain**, answer **Mild**, then **No** to pain on touch, then give a duration and location. Try **Severe** and a sudden onset in a separate conversation to see emergency branching. All examples must be synthetic.
9. For checks, open a second Terminal in the same folder, activate `.venv` and run:

```bash
python -m pytest -q
```

Text works in labelled local rules mode without keys. Voice transcription depends on SARVAM_API_KEY and remains to be tested on your laptop. FFmpeg is still required for voice: `brew install ffmpeg` on Mac if needed. No public deployment, real booking or dispatch is included.

