# Branch and compare

Implemented 28 September 2026 for saved workload-v2 and profiled scenario-dialogue-v3 practice. Required study attempts, generic/custom flows and unsupported legacy snapshots cannot be branched; the UI offers a fresh attempt instead.

## Use

Open a completed or interrupted rehearsal, select **Replay**, choose a user turn, and select **Try a different response here**. The application creates a separate retry, restores the state immediately before that reply and fills the composer with the original wording for editing. The original rehearsal and ratings are unchanged by branch creation. As before, leaving Feedback closes an unanswered post-questionnaire.

The alternative’s **Compare** tab shows shared context once, followed by the original and alternative continuations side by side (stacked on mobile). It displays the actual utterances, observable language features, stage transitions, selected actions, generation sources and recorded outcomes or agreements. It shows at most two continuations: this child and its immediate parent. Further alternatives can be saved, but there is no multi-branch tree view.

Branches use deterministic character wording with the saved profile, scenario, difficulty and policy versions. Normal crisis handling remains in place. Optional voice analysis and explicit pacing choices still operate under Step 3’s policy. These choices and an original’s online generation settings can contribute to differences; Compare discloses that limitation. No comparison predicts real-world success or psychological improvement.

## Stored contract

`POST /api/sessions/{id}/branches` accepts `turn_id`, `expected_version` and a UUID `request_id`. Extra client-supplied fields, including attempt purpose or authoritative snapshots, are rejected. The server reads and validates the owner’s source document and linked decision. Sources must be completed/interrupted; the selected decision must have an active, supported pre-turn state and intact evidence/context.

The new session stores:

- Immediate parent session/version, selected user-turn ID and a stable root branch-group ID.
- A deep copy of the pre-turn snapshot: dialogue state, turn count, progress, difficulty, cooperation and emotion tracker state.
- The transcript prefix and its original turn IDs, prior decisions and evidence, explicitly listed as copied context.
- Creation-request ID, creation time, deterministic generation mode and a digest of the source rehearsal used for comparison.

The child restores the snapshot exactly and starts a new attempt timestamp. It gets its own UUID and version, `attempt_purpose=retry` and no required-task association. It copies no questionnaires (including pre-ratings/skips), post token, completion timestamps, final feedback, takeaway, research events or submission IDs. The source’s future turns are not copied. Keeping context turn IDs allows local evidence links to resolve even when the parent no longer exists.

The server checks source versions before building and before saving the child; stale requests fail with 409. A deterministic child ID derived from the owner and request ID makes concurrent duplicates return the same retained child, including after restart. A reused request ID with different arguments is rejected. The source is never written or locked: a source change/deletion after the final read can leave a valid child of that read snapshot. Comparison then reports the source unavailable/changed. Request idempotency lasts while that child is retained; deleting the child also removes its request record.

New branch turns use ordinary session optimistic concurrency. Rewind may remove new continuation turns but cannot cross into shared context. Branches of branches are supported only at new responses; group lineage is retained. An unsupported saved policy is rejected on continuation rather than silently upgraded.

## Comparison, deletion and retention

`GET /api/sessions/{child_id}/comparison` is owner-checked and read-only. It projects saved records; it never regenerates explanations or scores. Completion measurement boundaries exclude later reflection. Shared context is separated from both continuations. If the source rehearsal digest changed (for example after rewind), the original column is unavailable rather than comparing a different history. Renames, ratings, takeaways and later reflection do not change that digest.

Parent deletion/expiry leaves the child’s copied context and active continuation intact. Comparison explains the missing parent and offers no dead parent link. Account deletion removes all owned sessions, including branches, using the existing deletion path. Each child has the normal independent session retention period. Existing retained study-record and frozen-export deletion rules are unchanged.

## Measurement scope

Language feedback in a branch uses only evidence from new responses and is labelled `evidence_scope=continuation`. The recorded outcome is for the resumed conversation and can depend on shared context. Ordinary previous-attempt score comparisons exclude branches to avoid comparing different evidence scopes; the explicit Compare view shows the saved continuations instead.

Copied turn IDs are excluded from study `turn_count`, generation-source counts and fallback counts. Research events start with a fresh `branch_created` event; original message/questionnaire events are not copied. [Research export v4](research-export-v4.md) identifies branch records, copied context counts and feedback scope. Required-attempt selection is unchanged. Historical frozen files retain their original content, schema version and checksum.

## Synthetic demonstration

1. Start additional **Boundary** practice with a sceptical profile and intermediate difficulty.
2. Reply “Sorry, sorry, maybe I could help.” Then finish and review.
3. In Replay select that reply and choose **Try a different response here**.
4. Replace it with “I cannot take this on.” Answer renewed pressure with “My answer is still no. Thank you for understanding.” Repeat if the profile requests another pressure response.
5. Open Compare. The original has recorded apology language and no boundary outcome; the alternative has refusal/held-boundary evidence and a `boundary_held` outcome, without inventing an agreement or concession.
6. Reload the child. Replay and comparison remain available. Delete the original through existing session controls if desired: the child still has its own context and can be inspected independently.

These authored fixtures are tested in `backend/tests/test_branching.py`. Browser tests use synthetic API fixtures; real MongoDB tests reopen repository/service instances and continue a branch after parent deletion. This step does not claim a full-stack browser/backend-process restart demonstration or live-model accuracy evaluation.
