# Research CSV v2 data dictionary

Historical schema: new exports now use [CSV v3 and its explicit required-attempt selection](research-export-v3.md). Existing v2 snapshots remain unchanged.

New live exports and newly frozen datasets use `affectlab-frozen-dataset-v2`. Existing frozen snapshots remain byte-for-byte unchanged, with their original schema version and checksum. This changes the export representation, not the frozen study protocol or rating scales.

## Rows and denominators

- `row_type=session`: one durable study record per session/attempt.
- `row_type=participant`: an enrolled, currently eligible participant with no retained study records for the current protocol. Session, score, and questionnaire columns are blank. This is not a completed session or a zero-valued rating.
- Count distinct `participant_id` across **all rows** for the eligible enrollment denominator. Count only `session` rows for session summaries. Multiple attempts do not create extra participants.
- Snapshot `record_count` counts CSV data rows, including participant-only rows; `participant_count` counts distinct eligible participants. An empty cohort exports the header and zero counts.
- Existing consent, eligibility, withdrawal, and exclusion rules still apply. Withdrawn/excluded accounts are not included. The CSV describes the eligible analysis cohort, not a full recruitment/withdrawal log. A participant-only row means no currently retained records, which may also result from retention expiry.
- Only records belonging to the current protocol are included.

Live exports use pseudonymous participant and session UUIDs. Frozen exports replace these with sequential IDs such as `P0001` and `P0001-S001`, including participants without sessions. No account lookup is embedded in the snapshot.

## Columns

| Columns | Meaning |
|---|---|
| `schema_version`, `row_type`, `protocol_version` | File schema, row type, and study protocol. |
| `participant_id`, `enrolled_at` | Participant grouping key and recorded enrollment time. |
| `consent_version`, `consented_at` | Session consent version (or current consent version on participant-only rows); latest account consent acceptance time. |
| `eligibility_version`, `eligibility_confirmed_at` | Current eligibility attestation version/time at export. |
| `session_id`, `created_at`, `updated_at` | Attempt identifier, session creation time, and last activity time. |
| `turn_count` | Post-consent conversation turns, including user and assistant turns. |
| `scenario_id`, `difficulty`, `completion_reason` | Recorded scenario, difficulty, and outcome; blank for reflection-only sessions. |
| `roleplay_started_at`, `roleplay_completed_at` | Rehearsal timestamps, when recorded. Completion minus start is elapsed wall time, including pauses; it is not active interaction time. |
| `pre_confidence`, `pre_anxiety`, `pre_submitted_at` | Pre-questionnaire ratings (1?7) and submission timestamp. |
| `post_confidence`, `post_realism`, `post_usefulness`, `post_submitted_at` | Post-questionnaire ratings (1?7) and submission timestamp. |
| `feedback_metrics_json` | JSON list of `{name, score, evidence_turns}`. Scores are 0?1; evidence contains role-play turn indices, never conversation quotations. |
| `feedback_generation_source` | For example, `deterministic` or `openai_from_deterministic_metrics`. This describes feedback wording, not the dialogue generator. |
| `generation_source_counts_json` | JSON object counting post-consent assistant turns by source. Sources include `openai`, `openai_roleplay`, `template`, `deterministic_roleplay`, `scenario_opening`, `safety_response`, and `unrecorded`. |
| `fallback_reason_counts_json` | JSON object counting recorded dialogue fallback reasons, such as `missing_api_key`, `roleplay_disabled`, or an exception-class code. No exception messages or provider response text are exported. |
| `event_counts_json` | Counts of research events by name, including questionnaire submissions and role-play actions. Event properties and user-authored notes are omitted. |

All timestamps are ISO 8601 with a timezone. CSV quoting is standard: load with a CSV reader before parsing the `*_json` cells as JSON.

## Missingness and interpretation

Blank cells mean unavailable/not applicable, not zero. In particular, older durable records can lack generation counts and rehearsal timestamps. Active retained sessions acquire the new projection when saved or backfilled; expired sessions cannot supply metadata that was never retained. `unrecorded` counts assistant turns present in a session but lacking source metadata. An empty JSON object means no corresponding counted events/reasons in the available metadata; it does not prove that no unrecorded failures occurred. A skill score of `0` is an observed zero and must not be converted into a missing value.

Use the same session's pre/post confidence for paired changes. Restrict primary task analysis to the protocol's required scenarios and intermediate difficulty, and require a completion reason of `success`, `maximum_turns`, or `user_finished`, plus non-missing post-confidence, realism, and usefulness (each 1-7, with questionnaire phase `post`). `safety_interruption` is not successful completion. Retain repeated attempts separately and apply the protocol's exploratory/retry rules in analysis.

Source counts cover assistant turns, including scripted openings and closing/safety responses. Define a dialogue fallback denominator explicitly; do not count openings or safety responses as failed provider calls. `roleplay_disabled` and `missing_api_key` describe configuration fallbacks, while exception codes indicate recorded call failures. Feedback wording source is separate; these counters do not describe every technical failure in the app or every failed feedback-generation request.

## Reproducibility and privacy

Skill metrics, timestamps, and source/fallback counts live in durable `study_records`, so CSV generation does not require the original conversation session to remain available. Freezing stores the complete CSV bytes and SHA-256 checksum; subsequent downloads return those bytes even if identifiable live records are later removed by withdrawal.

The export excludes names, emails, password data, account IDs, conversation text, raw audio, custom scenario wording, feedback prose, takeaways, and free-text event properties. Fixed numeric metric names and generation/event codes remain available for analysis.

Questionnaire decisions are immutable. Explicit skips leave the corresponding numeric columns blank and appear in `event_counts_json` as `questionnaire_pre_skipped` or `questionnaire_post_skipped`. Leaving a pending post-questionnaire produces `questionnaire_post_closed`. These events distinguish intentional skipping and screen exit from otherwise unknown missingness; neither is a zero rating. Reopening a completed session cannot add retrospective ratings.
