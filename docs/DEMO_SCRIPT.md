# Demo video: target 2 minutes 50 seconds

Use synthetic examples only. Start the app, load separate Groq account keys locally and verify /health. Record voice in a microphone-enabled localhost/HTTPS browser. If keys have not been live-tested, disclose that instead of claiming a live integration. Enable system screen recording manually; no real medical operations occur.

| Time | Screen / action | Narration |
|---|---|---|
| 0:00-0:15 | Opening interface, prototype banner | "CareCompass helps families choose a care pathway and understand the next step, in English, Hindi or Hinglish." |
| 0:15-0:45 | Record: "Mujhe das din se bukhar hai, around 103 Fahrenheit." Stop; inspect editable transcript, correct any number | "A separate Groq audio account transcribes the message. We confirm the transcript because a missed negation or number matters." |
| 0:45-1:10 | Send; prompt-assessment concern and breathing question. Answer "No"; provide age if asked | "The text account extracts facts. We retain ten days and the temperature instead of asking them again. One relevant question helps decide the next step. This does not diagnose dengue or infer lab values." |
| 1:10-1:30 | Start again, prescribed wound dressing; show actual caregiver reason | "Procedural requests skip unrelated interviews. Eligibility comes before ranking: role, explicit skill, service radius, availability, then language, proximity and rating." |
| 1:30-1:45 | Click Simulate booking | "This is an explicitly simulated booking. No request, payment or dispatch occurs." |
| 1:45-2:15 | Reset to prolonged fever and answer breathing question "Yes" | "A different answer switches the pathway immediately. Local safety overrides normal intake and matching; the emergency action is call 112." |
| 2:15-2:40 | Show evaluation_all/metrics.json and tests | "The rules baseline caught all 56 supplied emergency rows. Full-data care F1 is 0.822 and urgency F1 0.851. The broader intake asks safety questions on some cases that labels route immediately. These are descriptive template results, not hidden-test or clinical validation. Noisy flags and matching references are reported separately." |
| 2:40-2:50 | Show API schema or curl example | "The API, interface and batch exporter share one validated pipeline. Current limitations include unbenchmarked live models and gaps in urgent in-person care and future availability." |

## Final manual checks

Text -> follow-up -> answer; Hindi question; correct a transcript number before sending; emergency bypass; caregiver skills/reasons; simulated confirmation; no-match with location 0,0; microphone denial; stop/cancel; silence; retry; provider key failure; mobile 390px and desktop layout. Do not display API keys in the recording. If the live Account A is slower, shorten narration rather than editing out errors while claiming uninterrupted real-time execution.


## Alternate broader-intake demonstration

Use stomach pain instead of prolonged fever: type the complaint, choose Mild, answer No to pain on touch, then supply duration/location. Restart with Severe pain and answer Yes to sudden onset to show the emergency branch. Keep total recording under three minutes; substitute this for the fever segment rather than adding another feature tour.
