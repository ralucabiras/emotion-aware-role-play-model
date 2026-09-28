# Research export v4: branch activity and feedback scope

New live CSV and newly frozen datasets use `affectlab-frozen-dataset-v4`. Personal research JSON uses `affectlab-research-export-v4`. Existing frozen files remain byte-for-byte unchanged. V4 retains the privacy boundaries, missing-value rules and required-attempt selection described in [v3](research-export-v3.md).

| Field | Meaning |
| --- | --- |
| `is_branch` | True for an alternative created from a saved pre-turn snapshot; false for ordinary and historical records. |
| `copied_context_turn_count` | Number of inherited transcript messages, excluded from `turn_count` and response-source/fallback counts. Zero for ordinary sessions. |
| `feedback_evidence_scope` | `continuation` for branch language metrics, which use only new evidence; `full_attempt` for ordinary and historical feedback. |

Participant-only CSV rows leave these fields blank. CSV booleans remain `True`/`False`; JSON uses booleans. `turn_count` still counts user and assistant messages, now explicitly excluding copied branch context. Branch evidence-turn indices retain their positions in the full copied-plus-new rehearsal; they are not renumbered or exposed as new activity. No transcript, lineage digest, snapshot or new direct identifier is added to research exports.

Branches have attempt purpose `retry` and no required-task association. They cannot replace an original protocol attempt. A branch’s outcome can depend on shared context even though its language feedback uses only new responses. Do not pool continuation-scoped and full-attempt feedback as directly comparable intervention outcomes; filter or report scope explicitly. The existing dashboard remains a descriptive aggregate, not a controlled branch comparison. Original events and ratings are not duplicated; each child starts its own event history.
