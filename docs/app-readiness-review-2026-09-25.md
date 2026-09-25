# App readiness review - 25 September 2026

The app is close to a dependable dissertation demonstration, but the remaining rehearsal-state bugs and demo-data inconsistencies should be addressed before taking final screenshots or collecting participant results. This was a review: application code and the existing database were not changed.

## Verification

- Frontend production build and ESLint passed.
- Backend: 110 tests passed; the five opt-in MongoDB tests were initially skipped, then all five passed separately against disposable local databases. Backend Ruff passed.
- Full mocked browser suite: 47 of 48 desktop/mobile checks passed. The desktop "practise again" test timed out at the saved-session reload assertion (practice.spec.ts:99). It passed three consecutive isolated reruns with one worker. Treat this as unresolved suite timing instability, not evidence that the new-attempt fix is broken.
- The Windows browser runner lingered after reporting test outcomes and was stopped during teardown.
- The configured MongoDB was inspected read-only. User, session, and study-record documents all validated against the current models. No orphan study records were found, and expected persistence/TTL indexes were present.
- Configured model directories/configuration exist; transcription is configured. This does not validate live OpenAI requests, SMTP delivery, microphone hardware, or actual trained-model inference. No paid external calls were made. Docker full-stack smoke was not rerun because Docker is unavailable in this environment.

## Fixes needed

### 1. Rewind removes the wrong exchange after paused reflection

Reproduced in the conversation service: start boundary rehearsal, send one refusal, pause, send a reflection, and retry the last turn. The service removes the reflection exchange but also pops the rehearsal's last evidence item. The actual refusal remains in the conversation while the rehearsal has zero evidence/turns.

Track which conversation exchange produced each rehearsal evidence item, or disallow rewind across later reflection exchanges with a clear action to start another attempt. This is a functional consistency fix, not extra security work.

Source: backend/app/services/conversation_service.py:254.

### 2. Later reflection can rewrite a completed study outcome

Reproduced: complete workload, save valid post-ratings, return to conversation, then send text triggering the safety response. The old study record changes from success/qualifying completion to safety_interruption/non-completion while retaining the original feedback and post-ratings. Its turn count also changes from 3 to 5.

Even ordinary later reflection is included in the same record's turn/generation counts. Separate later reflection from the completed rehearsal's research measurement, and apply safety interruption to an active/paused rehearsal rather than rewriting completed history.

Sources: backend/app/services/conversation_service.py:175 and sync_study_record.

### 3. Required study attempts and additional practice are not distinguished in stored data

The protocol and checklist say retries/additional practice do not count toward the primary outcome, but is_completed_protocol_task checks only scenario, intermediate difficulty, qualifying reason, and post-ratings. The progress route accepts any qualifying attempt. Start requests and study records do not store whether an attempt came from the required checklist, additional practice, or a retry.

Store an explicit attempt purpose/required-task association and apply one documented selection rule in progress, completion statistics, and exports. This avoids an additional-practice success silently replacing an incomplete required attempt. If the intended protocol permits that replacement, document the rule explicitly before collection instead.

Sources: backend/app/api/routes.py:112, participant_study_progress; backend/app/models/domain.py:StudyRecord; frontend/src/services/api.ts:startRoleplay.

### 4. Researcher/test exclusions need a reliable boundary

The current consent predicate includes an enrolled researcher account. A direct check returned researcher=true and included=true. Synthetic accounts also have no automatic analysis exclusion; their synthetic_seed events identify their origin but are not an exclusion filter.

The protocol excludes researcher/test accounts. Use a separate demo database and an explicit test/synthetic designation, or consistently exclude these accounts before analysis. Do not simply add eligibility records to the existing seeded accounts and then treat the resulting dashboard as participant evidence.

Source: backend/app/api/routes.py:123 and build_research_csv.

### 5. A recoverable password-reset choice consumes the reset link

Reproduced in memory: submit the existing password as the new password, receive "New password must be different", then correct it using the same link. The second request fails with "Invalid or expired password reset link" because the token was consumed before the password check.

Keep a valid link usable after a rejected password choice, while retaining single-use behavior after a successful reset.

Source: backend/app/services/auth_service.py:106.

### 6. A few secondary actions still lack visible error recovery

Code review: email-confirmation resend, Settings session loading/deletion, account deletion, personal JSON download, custom-scenario deletion, and workspace "Delete & start fresh" contain asynchronous calls without user-facing catch/retry handling. For example, a failed Settings session fetch can look like "No active sessions are stored."

These are lower priority than rehearsal/data correctness, but reuse the existing error presentation and busy states so failed actions are understandable. These failure branches were identified by code inspection, not all individually reproduced in a browser.

Sources: frontend/src/App.tsx:71; frontend/src/components/SettingsPage.tsx:15,32,33; frontend/src/components/RolePlayWorkspace.tsx:remove; frontend/src/components/Dashboard.tsx:fresh.

### 7. Finish participant-facing setup before recruitment

The active configuration still contains "To be confirmed" for supervisor name, supervisor email, and institution. There is no saved study lifecycle/date record. Complete the actual approved information and dates before using the app with participants. This need not block a labelled local demo.

## Current database and report suitability

Read-only snapshot of the configured affectlab database:

| Check | Observed |
|---|---:|
| Accounts | 12 |
| Accounts created by the synthetic seed | 10 |
| Sessions | 25 |
| Sessions carrying synthetic_seed | 23 |
| Study records | 20 |
| Study records carrying synthetic_seed | 20 |
| Accounts with study consent/enrollment | 10 |
| Accounts with an eligibility record | 0 |
| Currently eligible analysis participants | 0 |
| Live research CSV data rows | 0 (header only) |
| Frozen exports | 0 |

The remaining two sessions are not marked synthetic; that alone does not establish that they are research participant data. No real participant study results were identified in the 20 study records.

The seed data are not yet a coherent demonstration of the frozen three-task procedure:

- Every seeded participant has two study records, rather than the required three-task sequence. None meets the complete protocol even if eligibility filtering is ignored.
- Records contain five workload, six boundary, five relationship, and four deadline scenarios. Difficulty is split across seven beginner, seven intermediate, and six difficult attempts.
- Two study records start before their recorded enrollment.
- All 20 records lack the newer rehearsal start/end fields and generation-source counts.
- All 20 have exactly five conversation turns; 19 are successful and one is paused.
- All 19 post-questionnaires rate usefulness 6/7, and every paired confidence change is exactly +2. These are deterministic fixtures, not plausible observed outcome distributions.
- All 23 synthetic sessions have ordinary titles without a visible demo/synthetic label, including three added to an existing account by the seed script. The internal event marker is not obvious in screenshots.
- The seed script itself lacks current eligibility records and fabricates scores independently of the actual scoring service. Re-running it unchanged will reproduce these inconsistencies.

Use the current data only as explicitly labelled synthetic examples of interface structure, not as feasibility/usability findings. Before final demo screenshots, create a separate, clearly labelled synthetic dataset using the current services: consistent consent/eligibility timing, the required task order/difficulty, a few intentionally incomplete/skipped/paused examples, and scores computed from the supplied demo conversations. Keep these constructed cases separate from any later collected participant dataset. Do not invent variation to present it as measured participant behavior.

Source: backend/scripts/seed_mock_data.py.

## Scope of the remaining work

Prioritize rehearsal/history isolation and coherent demo data. Resolve the study-attempt classification before real collection. The password-reset and secondary error-handling improvements are small usability fixes. No infrastructure overhaul or additional security project is needed for the stated supervised dissertation-demo scope.
