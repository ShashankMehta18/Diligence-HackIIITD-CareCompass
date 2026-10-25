# Complaint-aware intake, version 0.2

This version fixes the observed failure where stomach ache received a generic service menu. It broadens extraction and the validated question policy together. It does not diagnose, prescribe or claim universal medical competence.

## Supported paths

There are 45 named complaint families plus `other`: abdominal pain, headache, vomiting, diarrhoea, cough, sore throat, urinary symptoms, back pain, joint pain, rash/itching, dizziness, injury, eye symptoms, ear pain, dental pain, fatigue and fever, plus body-part pains (knee, shoulder, ankle, neck, wrist, elbow, hip, foot, hand), wound, diabetes, catheter, nebulization, vitals check, post-surgical care, bedridden care, elderly care, menstrual problems, anxiety and sleep problems, plus mapping-driven families (muscle pain, nose/sinus, heart/blood-pressure, nerve symptoms, kidney, thyroid, weight/nutrition, blood-related symptoms). Each has a complaint-relevant question plan; body-part pains ask swelling, movement, weight-bearing and injury questions instead of the old generic severity/fever/duration set, and fever asks fever-specific questions (high fever, fluids) alongside the breathing/age safety chain. Unknown wording stays in the local `other` category and gets general clarification; no model extraction refines it. Unsupported complaints receive focused general symptom clarification and an explicit human-assessment fallback, without a claim that routine home care is safe.

The complaint families and their specialist routing follow the symptom database in `data/symptom_mapping.csv` (177 mappings: body system, body part, complaint, recommended first contact, relevant specialist, safety note). Where the mapping names a specialist with no roster doctor (e.g. neurosurgeon, vascular surgeon), the family routes to the closest available roster specialty or the generalist fallback; no caregiver is invented.

Doctor matching is specialty-aware: the roster (`data/caregivers.csv`, 300 caregivers: 218 doctors, 53 medics, 29 phlebotomists) carries each doctor's `specialty` and `supported_complaints`, and a teleconsultation matches only doctors whose supported complaints overlap the complaint family (knee pain → Orthopedics/Rheumatology, migraine → Neurology, rash → Dermatology, ankle pain → Orthopedics, diabetes → Diabetology/Endocrinology, irregular periods → Gynecology and Obstetrics). Family key sets use the roster's granular keys (body-part pains, follow-up keys such as `fracture_followup`, `kidney_stone_followup`, `chronic_cough`, and child keys such as `child_rash` and `child_nutrition`). When no specialist supports a complaint, generalist doctors (`general_symptoms` / `initial_assessment`) are the fallback; child-only keys (e.g. `child_fever`) match only when the age is known to be under 18. Medic and phlebotomist matching is unchanged (role + procedural skill + radius); provider cards show the caregiver's specialty.

The local recogniser covers finite English, Hindi and Hinglish phrases and is the only text path. Neither it nor any other path recognises every medical condition or phrasing.

## State and answer interpretation

The expanded schema carries complaint category and text, reported severity, pain location, sudden onset, duration (including hours), progression, age, temperature/currentness, associated symptoms and clinical findings with status and user evidence. Absence remains unknown. Yes/no answers are linked to the preceding approved question. Reverse-polarity questions such as 'Can you swallow saliva?' and 'Can you keep fluids down?' are handled explicitly. Answer buttons come from backend question metadata.

Question selection skips supplied or answered facts. An unclear answer does not become a negative warning-sign screen. The normal cap remains four follow-up questions, with a conservative human-assessment fallback if critical information is still unknown. Established emergencies stop intake immediately. Prompt-assessment concern is shown alongside any further question rather than withheld until the interview ends.

Patient changes reset clinical state. Associated focal symptoms receive their own immediate emergency screen even if the main complaint is different. Their duration/severity is not transferred into the main complaint's scalar fields. This is still a simplified conversation model: it does not maintain a complete independent clinical interview for every simultaneous symptom or every patient. Complex or contradictory stories require human assessment.

## Safety source-to-rule register

The following are conservative prototype pathways, not clinical validation. Official UK/Irish guidance informs symptom urgency; the UI uses the organiser's Indian 112 action rather than foreign telephone numbers. No disease conclusion is inferred from these signs.

| Evidence | Implemented behaviour | Primary source |
|---|---|---|
| Any affirmed active organiser-controlled warning sign | emergency_112/emergency, no question or matching delay | Organiser README and original policy register |
| Sudden severe abdominal pain | Immediate emergency pathway; preserve actual evidence | https://www.nhs.uk/symptoms/stomach-ache/ |
| Abdomen painful on touch | Immediate emergency pathway | https://www2.hse.ie/conditions/stomach-ache/ |
| Blood in vomit, black sticky stool | Immediate emergency pathway | https://www.nhs.uk/symptoms/stomach-ache/ |
| Sudden extremely painful headache | Immediate emergency pathway | https://www.nhs.uk/symptoms/headaches/ |
| New sudden confusion | Immediate emergency pathway | https://www.nhs.uk/symptoms/confusion/ |
| Loss of vision or sudden-onset eye symptoms | Immediate emergency pathway | https://www.nhs.uk/symptoms/eye-pain/ |
| Tongue/throat swelling or inability to swallow saliva | Immediate emergency pathway | https://www.nhs.uk/conditions/anaphylaxis/ and https://www.nhs.uk/symptoms/sore-throat/ |
| Back pain with new bladder changes or groin numbness | Immediate emergency pathway | https://www.nhs.uk/conditions/back-pain/ |
| Fever with a non-fading rash | Immediate emergency pathway, without diagnosing meningitis | https://www.nhs.uk/conditions/meningitis/ |
| Complete inability to pass urine with abdominal/urinary complaint | Immediate emergency pathway | https://www.nhs.uk/symptoms/stomach-ache/ |
| Severe pain without established emergency evidence | Prompt in-person assessment concern; no routine booking | Relevant complaint pages above; detailed thresholds need mentor review |
| Inability to keep fluids down | Prompt assessment concern, not automatic severe_dehydration flag | https://www.nhs.uk/symptoms/diarrhoea-and-vomiting/ and https://www.nhs.uk/conditions/dehydration/ |
| Urinary symptoms with fever or flank pain | Prompt in-person assessment concern | https://www.nhs.uk/conditions/urinary-tract-infections-utis/ |

For controlled-vocabulary gaps, the strict response uses `emergency_112`, `emergency`, null follow-up and no matches, but leaves `red_flags` empty when none of the nine labels accurately fits. Evidence appears in permitted reasoning and UI metadata. This is an explicit organiser-clarification assumption: do not fabricate `stroke_symptoms` for headache alone or `severe_bleeding` for every mention of blood.

Ordinary chest pain/breathlessness, uncontrolled bleeding, unresponsiveness and the other existing controlled pathways remain mandatory. The LLM cannot downgrade a locally established emergency. Local broad safety checks remain available during provider outages and run on voice transcripts and corrected transcript text. Provider failures otherwise return an honest assessment-unavailable response.

## Example branches

| Scenario | Expected branch |
|---|---|
| 'I have stomach ache' | Ask stomach-pain severity, not a generic service menu |
| Mild pain, no pain on touch, duration/location supplied | Same-day clinician review in the supported taxonomy |
| Severe pain with unknown onset | Show prompt-assessment concern and ask whether onset was sudden |
| Sudden severe pain | Emergency, no matches, no invented flag |
| No blood in vomit | Record denied; do not trigger from 'blood' alone |
| 'No' to keeping fluids down | Prompt assessment concern, no automatic dehydration diagnosis |
| Unclear replies through question cap | Human assessment fallback, no routine matching |

## Measured results and trade-offs

Python and DOM integration results are recorded in VERIFICATION.md. The organiser examples are narrow/repetitive and frequently route without the context required by this version. On all 340 rows, care label macro-F1 is 0.8219 and urgency macro-F1 0.8514, compared with 0.8698/0.8736 in the earlier narrow version. All 56 labelled emergencies are still caught. These are descriptive supplied-label metrics, not blind hidden-test or clinical evidence. The broader safety tests use independently phrased synthetic cases and are separate from organiser data.

This version improves complaint coverage and questioning behaviour, while reducing agreement on cases where it now asks additional questions. No official combined score improvement, deployment readiness or clinical validation is claimed. Review emergency thresholds, special populations, simultaneous complaints, local clinical pathways and the taxonomy gap with a clinical mentor before any real-world use.

