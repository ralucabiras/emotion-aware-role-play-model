# Research CSV v3 and required-attempt selection

New live exports and newly frozen datasets use `affectlab-frozen-dataset-v3`. Previously frozen files remain unchanged, retaining their original schema version and checksum. V3 retains the columns and privacy boundaries described in [CSV v2](research-export-v2.md) and adds the fields below. Personal research JSON is now `affectlab-research-export-v3` and exposes the same attempt classification and primary flags.

| Field | Meaning |
|---|---|
| `attempt_purpose` | `required` for a checklist attempt, `additional` for ordinary practice, `retry` for Practise again, or `legacy_unknown` when no purpose was recorded. Reflection-only records are additional activity. |
| `required_task_id` | The associated standard task (`workload`, `boundary`, or `relationship`). Required attempts must match their scenario and use intermediate difficulty. A retry may retain its original task association without becoming a primary attempt. Additional practice has no association. |
| `primary_attempt` | True only for the selected required attempt for that participant/task/current protocol. |
| `primary_task_complete` | True only when that selected attempt has a qualifying completion reason and complete post-ratings. |

Participant-only rows leave these attempt columns blank. CSV booleans are `True`/`False`; JSON uses booleans.

## Selection rule

For each participant and each required task in the current protocol, select the earliest explicitly `required` record with a matching task/scenario association and intermediate difficulty. Sort by rehearsal start time (session creation time for older classified records), with session UUID as a deterministic tie-breaker. Selection never depends on success, questionnaire availability, last activity, or repository return order.

That original attempt remains selected if it is interrupted, skipped, abandoned, or lacks post-ratings. A later successful retry, additional-practice attempt, or duplicate required record never replaces it. A duplicate required-start request is rejected; participants can resume the original attempt or start additional practice. Durable study records preserve the selection after conversation-session deletion or expiry.

The checklist, protocol-completion dashboard, live CSV, newly frozen CSV, and personal JSON use this same selector. `primary_task_complete` additionally requires `success`, `maximum_turns`, or `user_finished` and post-confidence, realism, and usefulness all present in 1-7. Primary protocol completion requires all three selected tasks to qualify. Other rehearsal totals and rating/skill summaries remain exploratory summaries over retained eligible activity; they are not the primary protocol-completion measure.

Existing records without purpose metadata remain `legacy_unknown` and are excluded from primary selection; the application does not infer checklist participation from scenario or difficulty. They remain available for clearly identified exploratory/legacy reporting. Do not silently backfill purpose from a successful result.

This documents the implementation of the frozen protocol's separation of required tasks from additional practice. It does not edit the frozen protocol or permit replacement of an incomplete required task. No existing database records or frozen datasets are rewritten by this change.

## Analysis

Use `primary_attempt=True` for the per-task primary denominator, including incomplete attempts, and `primary_task_complete=True` for completed required tasks. Count participants with all three required task IDs complete for the primary numerator. Continue counting distinct participant IDs across all row types for the eligible enrollment denominator. Do not count arbitrary intermediate sessions as required tasks. Keep additional/retry/legacy rows separate in exploratory summaries.
