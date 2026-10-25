# Version 0.5: safety and extraction repair

This implements the engineering changes requested after the deployed-app audit. It preserves the team's SehatSaathi layout, specialty roster/matcher, six-field organiser response, Swagger, Docker/Render setup and four-question cap. No model was trained. Clinical review is pending, and this is not a clinically validated triage service.

## What changed

- A complaint-independent safety screen runs on every user message during replay, including later warnings, corrections, safety preview and transcribed text. It runs before the text provider and before service matching. It composes symptom, anatomy, onset and exposure context for chemical/penetrating eye injuries, bleeding from the eye, vision change after eye injury, acute focal neurological changes, harmful ingestion and sudden severe testicular pain. Finite English/Hindi/Hinglish aliases support these categories; the screen is not universal semantic understanding.
- Evidence retains the rule ID, assertion status, disposition, original quote and primary source. Recent resolved focal symptoms are distinct from remote history; simple cross-clause eye-injury/vision and symptom/onset contexts are supported. Corrections replace the explicitly corrected rule; a named patient switch resets patient-specific safety state. Unknown warning information prevents routine matching. Unsupported controlled flag labels are never invented: an emergency may have an empty controlled-flag list with evidence in UI metadata.
- Complaint extraction fixes context collisions and common word-order/plural gaps: urinary discomfort is distinguished from a skin wound, neck location from lower back, and neurological symptoms from a hand-pain keyword. Boundaries prevent `sting` inside `existing` from creating a wound. Structured body_site/trigger data and the existing severity/duration/onset/evidence are available in UI state. New model/local disagreements trigger explicit clarification or human assessment instead of silent override or booking. Earlier symptom text is not silently overwritten by an unrelated later complaint.
- Shared assertion handling improves denial, hypothetical/history scope and uncertain answers. Uncertain fever is not asserted as positive or negative. Model-supplied negative safety features need local corroboration. Known short follow-up answers are interpreted locally after safety replay, reducing redundant model calls; the engine is explicitly labelled rules_contextual_answer.
- Provider requests use a portable structural JSON schema, while full Pydantic constraints remain enforced locally. GPT-OSS requests explicitly use low reasoning effort. Compact current-patient evidence avoids redundant assistant text and previous patients. These changes address plausible rejection/usage causes; the exact cause of the deployed service's400 response was not available, so no single root cause is claimed.
- 429 responses are not immediately retried. Retry-After (seconds or HTTP date) creates a bounded per-account/channel cooldown; text and audio remain independent. Text concurrency is bounded in each process. Only bounded transient transport/server retries are allowed. There is no alternate-key/account/model fallback to evade quotas, and no automatic downgrade to weaker output formatting.
- Sanitized provider diagnostics expose known error classes, status/code and cooldown in `/health` and UI error metadata. Raw provider error bodies, prompts, user messages and credentials are not retained in diagnostics. Rate limits and credentials remain account/provider constraints; this code cannot increase limits or repair invalid account permissions.
- The UI retains explicit final human assessment, routine-booking suppression, network timeout/retry behavior and the four-question cap. Hindi emergency, final and fallback guidance is localized. Booking remains simulated; no dispatch is performed.

## A deliberate urgency distinction

`LIVE-064` in the frozen audit says ten paracetamol tablets were taken in the last hour. The original provisional audit expected emergency 112. The specific NHS paracetamol source instead directs prompt professional advice for exceeding the packet instructions; clinical severity depends on details the prototype cannot establish. Version 0.5 immediately withholds booking and asks for urgent professional assessment, without asking routine questions or claiming a safe/toxic dose. It does not automatically label every medication-excess report as an ambulance case. Collapse, severe breathing difficulty and other established emergency signs still escalate.

The original fixture is unchanged and this remains a strict emergency-label mismatch in results, pending clinician adjudication. A high-tablet-count heuristic is a conservative review trigger, not a validated threshold or a statement that lower counts are safe. This distinction is not hidden to improve the score.

## Primary sources and interpretation

Accessed 25 October 2026. The implementation/translation is developer interpretation and requires Indian clinical review. The application uses the organiser's Indian112 destination; UK telephone numbers are not transplanted into patient output.

| Rule family | Source | Interpretation used |
|---|---|---|
| Eye injury | https://www.nhs.uk/conditions/eye-injuries/ | Strong chemical exposure, penetration, blood/pus from an eye and injury with vision change require immediate assessment; a painless red spot is not automatically flowing blood. |
| Focal neurological warning | https://www.nhs.uk/conditions/stroke/symptoms/ | Acute one-sided sensory/motor or speech/face changes, including recent resolved signs, cannot be treated as routine matching. Remote history and uncertain onset need separate interpretation. |
| Harmful ingestion | https://www.nhs.uk/conditions/poisoning/ | Suspected ingestion of a known harmful substance is handled before routine intake. |
| Acute testicular symptoms | https://www.nhs.uk/symptoms/testicle-pain/ | Sudden severe pain needs immediate assessment; other reported testicular symptoms need clinician assessment rather than unrelated urinary questions. |
| Medication excess | https://www.nhs.uk/medicines/paracetamol-for-adults/ | Excess medication receives urgent professional review; no dose/treatment advice is generated. |
| Provider schema | https://console.groq.com/docs/structured-outputs | Use supported strict structure; preserve independent local validation. Compatibility changes are tested with fake transports, not assumed successful live. |
| Provider quota/error handling | https://console.groq.com/docs/rate-limits and https://console.groq.com/docs/errors | Respect429/cooldown and retain safe diagnostic categories instead of repeated requests or account failover. |
| GPT-OSS reasoning | https://console.groq.com/docs/reasoning | Explicit low reasoning effort for extraction; no assumption that this establishes clinical quality. |

## Limits and remaining work

The screen remains finite and may miss unusual wording, complex temporal/coreference patterns or conditions outside its protocols. It has not been validated across the intended patient population, pregnancy, children, all languages or all emergencies. A successful schema or a four-question conclusion does not establish correct clinical triage. Text-provider cooldowns are process-local, not a distributed organization-wide quota controller.

The strict organiser schema has no urgent-in-person action. Urgent professional-review outcomes use teleconsultation/same_day as the contract-compatible coordination route, explicit immediate-assessment wording and no matches; the virtual option must not delay in-person help. Discuss this contract limitation with organisers/clinicians.

Independent clinical adjudication, unseen external evaluation, real Groq verification, real microphone checks and deployment checks remain required. `scripts/check_provider.py --allow-live` provides a bounded synthetic connectivity/extraction diagnostic without printing keys or raw errors. The default command makes no live call. No keys from uploaded archives were read or used.
