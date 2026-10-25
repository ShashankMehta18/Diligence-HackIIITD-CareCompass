# Clinical review handoff — pending

A qualified clinician must review this prototype before clinical-performance or safety claims are made. No clinician has approved this release. This document and `clinical_review.csv` prepare that work; they do not substitute for it. No reviewer was contacted by the assistant.

Review each source-to-rule mapping in SAFETY_0_5.md, including the intended action and time horizon, exception/uncertainty behavior, wording, age/pregnancy/medication limits and applicability in India. Check the underlying older pathways too: this patch is not validation of every existing rule.

The audit fixture remains unchanged and source-informed labels are provisional. In particular, adjudicate LIVE-064 (urgent medication advice vs automatic emergency 112). Review both missed-warning and over-escalation controls, including compound denials and remote vs recent events. Validate that a painless red spot and flowing blood are distinguished, and that acute focal numbness is not equated with all nonspecific tingling.

For each case/rule record the reviewer's qualified role/ID, reviewed date, accepted/rejected/needs_revision, adjudicated action, evidence and rationale. Independent reviewers should adjudicate disagreements. Keep model predictions separate from the reference label. All review-sheet fields start blank/pending; no row is training-ready.

This inspected developer/audit material may be used for regression and error analysis. If used to develop a model, retire it from independent evaluation. Before training, reserve new independent data with representative languages and clinical scenarios, group linked translations/templates/patients, and define emergency misses, false escalations, deferral, question relevance and subgroup metrics with reviewers.

Current engineering checks and their limitations are in VERIFICATION.md. The supplied code does not train, deploy, or automatically promote a model.
