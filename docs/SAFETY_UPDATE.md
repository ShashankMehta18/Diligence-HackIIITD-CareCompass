# Version 0.4 changes

This release modifies the uploaded team's version. It retains the SehatSaathi UI, 45 named complaint families plus `other`, specialty roster and matcher, FastAPI Swagger, reference clock, Docker and Render configuration. No ML model is trained. The strict six-field organiser response stays unchanged.

1. `emergency_language.py` expands finite English/Hindi/Hinglish warning recognition. Per-mention polarity distinguishes denial, historical and hypothetical text from current statements. Internal inability such as “hosh nahi aa raha” is not a denial. Current warnings interrupt any question, without waiting for Groq. This lexicon is finite and can miss unfamiliar wording.
2. `safety_policy.py` explicitly configures minimum context/safety/service information for every supported family. Unknown answers never count as negative answers. Missing relevant information at the cap yields `needs_human_assessment` in UI metadata, with no routine matches or booking. Plain service requests can retain their original flow; symptoms alongside a service request cannot bypass relevant checks. Multiple complaints may require human assessment rather than a full independent interview for each. These prototype minimums are not clinician-approved clearance checklists.
3. `evaluation_safety/` supplies a separately authored, frozen development suite and reproducible baseline comparison. It is not blind or clinical validation. Live mode requires explicit opt-in and is reported separately. The original organiser data is unchanged.

Additional final-screen fix requested during this update: the current policy stops after at most four follow-up questions per patient. A successful final response always contains a care-navigation conclusion, never a disease diagnosis. If information is unclear, it explicitly recommends human clinical assessment. `/ui/triage` catches text-provider errors and its 35-second deadline, replays the same answer using local rules, and labels the fallback. A final fallback withholds booking and recommends clinician assessment. The strict `/triage` endpoint retains its 503 failure contract, and transcription failures never fabricate a transcript.

The browser bounds requests at 45 seconds, including response reading. Network/HTTP failures replace the stale question panel with “Assessment not completed” and clinician-assessment guidance. The message remains editable for retry; failed requests are not appended to history. A successful final result scrolls into view. The hearing question now asks whether sudden hearing loss is present, rather than presupposing hearing loss.

## Clinical source mapping and limits

The following primary guidance informed the prototype distinctions, accessed 24 October 2026. The mapping and translations are developer interpretations, not an endorsed medical protocol. Existing additional source mappings remain in `BROAD_INTAKE.md`. The app retains the problem statement's Indian emergency destination 112; UK service numbers are not copied into the app.

| Rule area | Primary guidance | Interpretation in this patch |
|---|---|---|
| Sudden face/arm/speech changes | https://www.nhs.uk/conditions/stroke/symptoms/ | Current affirmed focal warning escalates immediately; dizziness/neuro screens ask relevant weakness/speech questions. This is not comprehensive stroke detection. |
| Heart symptoms | https://www.nhs.uk/symptoms/heart-palpitations/ | Ask relevant chest and breathing questions rather than treating palpitations as a routine service. |
| Knee symptoms | https://www.nhs.uk/symptoms/knee-pain/ | Ask movement and weight-bearing questions; concerning answers withhold routine booking pending assessment. |
| Catheter problems | https://www.nhs.uk/tests-and-treatments/urinary-catheters/risks/ | Reported blockage/leakage prompts clinical assessment rather than a routine catheter booking. |
| Surgical wound concern | https://www.gloshospitals.nhs.uk/your-visit/patient-information-leaflets/surgical-wounds-and-preventing-infections/ | Reported redness/leaking prompts assessment; it is not a diagnosis of infection. |
| Diabetic foot wounds | https://www.rdash.nhs.uk/services/podiatry-foot-protection/diabetes-foot-care/looking-after-a-diabetes-foot-ulcer/ | A nonhealing foot wound prompts clinical assessment instead of routine dressing-only matching. |

No real patient testing, clinician adjudication, medical-device approval, hidden-test score, or guarantee for every disease is claimed. Four questions cannot establish absence of all danger signs. Provider-based extraction is unverified live. The app is a synthetic prototype for care navigation and simulated booking.
