# Update and run version 0.5

The ZIP contains the complete updated project and a guarded updater. Use the updater for an existing GitHub clone: it copies only release changes, preserves `.git`, `.env`, dependencies and unchanged team files, and refuses to overwrite edits made since the previously supplied 0.4 ZIP. No Git history is reset, and nothing is pushed or deployed automatically.

1. Extract the ZIP. The outer `CareCompass_Update_0_5` folder contains `APPLY_UPDATE.py`, `update_manifest.json`, and the complete inner `CareCompass` source folder.
2. In Terminal, enter the outer folder. Example if extracted on Desktop:

   ```bash
   cd "$HOME/Desktop/CareCompass_Update_0_5"
   ```

3. Check your original Git clone (replace the example path if needed):

   ```bash
   git -C "$HOME/Desktop/Carecompass" status
   git -C "$HOME/Desktop/Carecompass" pull --ff-only
   python3 APPLY_UPDATE.py --target "$HOME/Desktop/Carecompass"
   ```

   Commit your own outstanding edits first. If pull or the updater reports conflicts, stop and merge with your teammate. Do not copy the whole ZIP over the repository to bypass this check. Team edits since the previously supplied 0.4 ZIP may need manual merging.

4. If the dry run succeeds, apply and review:

   ```bash
   python3 APPLY_UPDATE.py --target "$HOME/Desktop/Carecompass" --apply
   cd "$HOME/Desktop/Carecompass"
   git diff --stat
   git diff
   ```

   Changed original files are backed up beside your repository. Keep the backup until verification. Its rollback manifest lists newly added files; an interrupted application may require manual restoration. Credentials are never copied or backed up.

5. Activate the original virtual environment and test/run:

   ```bash
   source .venv/bin/activate
   python -m pip install -r requirements-dev.txt
   python -m pytest -q
   python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
   ```

   If `.venv` is missing, first run `python3 -m venv .venv`. Keep your existing private `.env`; do not run `source .env`. Stop an older server with Control+C before starting this one.

6. Open http://localhost:8000 and hard-refresh with Command+Shift+R. http://localhost:8000/health must report version `0.5.0`. Swagger is at `/docs`; the custom explorer is at `/explorer`.
7. Test all four ear-pain follow-ups, unknown answers for dizziness, knee questions and a known emergency phrase. Unresolved final results must show human assessment without booking. Run `python scripts/check_provider.py --allow-live` to verify your text account with at most two synthetic calls. Then check voice/microphone separately. Live provider success and real microphone behavior were not verified here.
8. Use `git status` and the outer `update_manifest.json` to review the changed files. Stage the intended release files after reviewing the diff:

   ```bash
   git add README.md UPGRADE.md backend/app frontend/app.js tests package.json package-lock.json scripts/check_provider.py scripts/verify_release.py docs/SAFETY_0_5.md docs/CLINICAL_REVIEW.md docs/clinical_review.csv docs/VERIFICATION.md evaluation_0_5
   ```

   Then:

   ```bash
   git diff --cached --stat
   git commit -m "Repair safety pathways, complaint extraction and provider reliability"
   git push
   ```

   Do not stage `.env`, dependencies or backups. Deployment changes only after this commit is deployed. Check version 0.5.0 and the final-answer flows on the deployed app too.

For a fresh local run, enter the inner `CareCompass` folder, create/activate a Python 3.12+ virtual environment, install `requirements-dev.txt`, copy `.env.example` to `.env` only if missing, and start Uvicorn. This fresh copy has no Git history. `TEXT_MODE=rules` works offline for text; voice needs FFmpeg and an audio key.

See `docs/SAFETY_0_5.md`, `docs/VERIFICATION.md` and `evaluation_0_5/README.md` for measured results and limits.
