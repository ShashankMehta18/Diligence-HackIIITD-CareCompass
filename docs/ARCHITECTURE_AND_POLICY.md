# Architecture and safety policy

Version carecompass-demo-0.1, 24 October 2026. Synthetic hackathon prototype; not clinician-reviewed or clinically validated.

## Shared flow

API / UI adapter / exporter -> replay original user messages and assistant questions -> local structured evidence and safety -> emergency fast path OR Account A extraction -> evidence validation -> safety recheck -> one approved question OR controlled routing -> deterministic eligibility and scoring -> validated strict response. UI-only metadata carries concern, evidence, cards and clock separately. Audio -> upload limit and FFmpeg validation -> Account B transcription -> editable transcript and preliminary warning -> confirmed text enters that same flow.

Patient messages are untrusted data. They cannot change system policy, supported schema or mandatory local safety. Previous assistant statements are never accepted as patient evidence. The model's exact user quotes are checked; missing numeric/service facts may be filled by model extraction, so semantic model errors remain a material limitation. Active local flags cannot be denied away by Groq. Provider errors yield HTTP 503 except locally established emergencies.

## States and question policy

Facts track patient identity, age in months, fever duration in days, temperature/unit, fever and service intent. Warning signs track affirmed, denied, historical or hypothetical; omission stays unknown. Evidence records preserve user turn references. The approved question bank covers need, age, breathing, duration, measured temperature/unit and injection route. It is deterministic and complaint-specific; Account A assists understanding, rather than generating unreviewed clinical questions. One question per turn; no repeating answered question IDs; normally at most four follow-ups, then human assessment fallback. Source messages are replayed, so correcting an earlier transcript before submission changes all downstream facts.

Local handling covers finite spelling/phrase variants, not universal Hindi/Hinglish. Numeric age/duration and some word forms are supported; the live extractor adds language breadth but has not been benchmarked. Distinct relatives are isolated. Recent resolved warning signs retain assessment concern; older resolved/hypothetical examples do not automatically set active flags. Ambiguous context can be misinterpreted and requires mentor review.

## Policy and source distinctions

| Path | Policy | Source / limitation |
|---|---|---|
| Affirmed active controlled flag | emergency_112 + emergency; no matching/question delay | Organiser README; intentionally conservative routing taxonomy |
| Severe breathing difficulty, unresponsiveness, uncontrolled heavy bleeding | Immediate emergency guidance | NHS emergency/shortness-of-breath guidance |
| Current stroke signs | Immediate emergency pathway | Organiser controlled taxonomy; mentor review needed for broader language coverage |
| Active seizure, suicidal intent, explicit severe dehydration | Controlled emergency pathway | Organiser taxonomy; nuanced medical thresholds are not inferred from this dataset |
| Fever under 3 months | Conservative high_fever_infant organiser pathway | NHS says urgent assessment at reported fever/38°C; this does NOT independently establish ambulance necessity for every infant fever |
| Prolonged/worsening or high fever | Surface prompt assessment concern, screen breathing, same-day clinician coordination | NHS advises urgent assessment for persistent/worsening fever; >=5 days or >=103F/39.4C are prototype concern triggers, not validated adult emergency thresholds |
| Explicit procedure | Confirm supported route/skill; no diagnosis/prescription | Roster and organiser care taxonomy |
| Unknown or unsupported need | Focused question; after cap human-assessment consultation fallback | Implementation assumption, not official clinical policy |

Call 112 is the Indian emergency action. No dispatch, ambulance arrival estimate, clinical diagnosis, drug advice or actual booking is claimed. Foreign source telephone numbers are not copied into the Indian interface. Unmapped emergencies and urgent in-person doctor assessment are contract gaps: retain the factual concern; do not invent controlled flag labels. Local code does not comprehensively recognise anaphylaxis or other out-of-vocabulary emergencies; source/mentor expansion remains necessary before any real use.

Sources checked 24 Oct 2026:

- Organiser problem statement and README, bundled in data/.
- https://www.nhs.uk/symptoms/shortness-of-breath/
- https://www.cddft.nhs.uk/patients-and-visitors/emergency
- https://www.nhs.uk/symptoms/fever-in-adults/
- https://www.nhs.uk/symptoms/fever-in-children/
- https://www.nhs.uk/symptoms/what-to-do-if-someone-has-a-seizure-fit/
- https://www.india.gov.in/directory/helpline
- https://console.groq.com/docs/structured-outputs
- https://console.groq.com/docs/speech-to-text
- https://console.groq.com/docs/models

## Matching normalisation

Hard constraints precede ranking. `L=1` if English/Hindi appears in listed languages, otherwise zero; Hinglish maps provisionally to Hindi. `P=max(0,1-distance/radius)`; virtual doctor P=1 as a neutral constant. `S=1` after all essential skills pass (or no procedural skill required for a compatible assessment role). `R=rating/5`. Score is .35L+.30P+.20S+.15R. No silent tier-to-procedure mapping. Ties: score descending, home distance ascending, ID ascending. All IDs are checked against the roster. No eligible staff -> empty matches.

Availability is a remaining-today window in IST at an injected clock, not a promised travel time. Future explicitly requested appointments show unconfirmed candidates with booking disabled. The scorer's exact time semantics/slot duration and score normalisation are not supplied. The fixed demo clock is part of the reproducibility assumptions. Ratings/skills are not professional credential verification.

## Rubric mapping

| Rubric | Weight | Feature | Verification |
|---|---:|---|---|
| Routing | 30% | Shared schema/core, multilingual extraction, adaptive facts | Macro-F1, confusion matrices, language results |
| Safety | 20% | Local bypass and mandatory post-extraction safety | Nine flags, negation, history, late emergency and outage tests |
| Matching | 20% | Eligibility then baseline score | Local ranking proxies, eligibility tests |
| UX | 20% | Mobile interface, voice transcript, simulated booking | API/static checks; manual browser/mic checks still required |
| Explainability | 10% | Short evidence and computed reasons | Roster fact assertions; no disease claims |

Tie-break work: one necessary question at a time, early emergency bypass, core latency measurement and published OpenAPI schema. Exact official aggregate routing/matching formulas remain unknown.

