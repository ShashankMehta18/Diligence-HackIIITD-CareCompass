# Relevant follow-ups — version 0.3

## What changed

The local parser previously recognised 'knee pain' but missed 'pain in my knee'. The joint pathway also asked mostly generic severity, fever and duration questions. This update recognises English, Hindi and Hinglish limb wording, retains a structured body site, and selects questions about the affected area. It does not generate a diagnosis or an unrestricted medical interview.

Supported limb sites: knee, ankle, foot, hip, leg, shoulder, elbow, wrist, hand and arm. These share the joint/injury families with site-specific question wording; they are not ten new disease classifiers. Unspecified joint location is clarified first.

## Example knee conversation

1. 'I have pain in my knee' → How severe is the knee pain?
2. 'Moderate' → Did it start after injury, a fall or a twist?
3. 'No' → Is there swelling around the knee?
4. 'No' → Can you stand and put weight on that leg?
5. 'Yes' → Can you bend, straighten or move the knee?
6. 'Yes' → How long have you had the symptoms?
7. 'Two days' → Clinician consultation in the existing organiser taxonomy.

The list is adaptive: supplied answers are skipped. Reported swelling opens a local heat/redness question. Severe pain, marked swelling, inability to bear weight or move, locking, deformity, numbness, heat/redness or accompanying fever ends routine questioning with a prompt in-person assessment concern and no routine caregiver booking. These findings alone do not fabricate an emergency flag or a diagnosis. Upper-limb questions ask about movement; they never ask the person to stand on an arm.

Knee/joint/limb injury paths allow at most six follow-ups; other paths retain the four-question budget. Unknown answers do not become negative screens. Unresolved critical function or swelling information prevents routine booking. Exhausting the budget leads to a human-assessment fallback, not reassurance. General symptom severity can remain unknown; it is not invented.

Breathing questions are retained in the cough/fever pathways rather than inserted into isolated limb pain. Explicit breathing difficulty or other established emergency evidence remains screened on every turn and bypasses the provider. A model cannot reinterpret a bare yes/no to an injury question as breathlessness.

Ear pain now asks about discharge and changed hearing. Tooth pain asks about local gum/cheek/jaw swelling after the existing airway screen. Natural 'pain in my ear/eye/tooth/throat' phrases are recognised. The other supported complaint families retain their focused safety and symptom plans. Familiar wording can be classified with Groq, but unsupported complaints still need human assessment; no universal disease coverage is claimed.

## Sources and limits

The following primary guidance informs the new prototype concern thresholds; no diagnosis is inferred and clinical validation has not been performed. UK urgent-assessment advice is represented as prompt in-person assessment, not automatically converted to an Indian ambulance call. The organiser contract lacks an explicit urgent in-person physician route, so reasoning carries the concern and routine matching is suppressed.

- NHS knee pain: https://www.nhs.uk/symptoms/knee-pain/ — very painful knee, inability to move/bear weight, marked swelling/changed shape, locking/giving way, heat/redness with fever.
- NHS joint pain: https://www.nhs.uk/symptoms/joint-pain/ — swollen/hot joint, joint pain with fever or feeling unwell.
- NHS ear infections: https://www.nhs.uk/conditions/ear-infections/ — discharge and changed hearing warrant urgent assessment.
- NHS toothache: https://www.nhs.uk/symptoms/toothache/ — local swelling and emergency airway-related signs.

Finite local phrase recognition, simplified single-primary-complaint state and unverified live model performance remain limitations. Complex simultaneous complaints or multiple painful joints are not independently assessed with a full clinical interview. See BROAD_INTAKE.md and VERIFICATION.md for the rest of the policy and measured checks.

## Swagger and installation

Swagger UI is preserved at `/docs`; its CDN assets require internet. The original self-contained explorer remains at `/explorer`. The main application retains its stricter content policy. Neither the organiser response schema nor dependencies changed for this update.

Use UPGRADE.md for replacing the project and keeping `.env` private. `/health` should report `0.3.0`. Start a fresh chat after updating so an earlier interview does not mix question policies. The existing Approach.pdf is the earlier 0.2 submission write-up; this document and the current verification record describe the 0.3 follow-up changes.
