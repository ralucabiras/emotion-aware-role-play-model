# Research export v5: protocol v1.1 scoring provenance

New live CSV and newly frozen datasets use `affectlab-frozen-dataset-v5`. Personal research JSON uses `affectlab-research-export-v5`. Existing frozen files remain byte-for-byte unchanged. V5 retains the privacy, missing-value, required-attempt, and branch-scope rules described in [v4](research-export-v4.md).

## Added field

| Field | Meaning |
| --- | --- |
| `scoring_version` | Version of the deterministic scoring rules that produced `feedback_metrics_json`. It is blank when unavailable for a historical record. Required protocol v1.1 attempts use `affectlab-required-lexical-v1.1`. |

## Protocol v1.1 completion rule

Only the first explicitly required attempt for each standard scenario at intermediate difficulty can contribute to the primary outcome. `primary_task_complete` is true only when that attempt ends with `success` or `maximum_turns` and contains complete immediate post-confidence, realism, and usefulness ratings. A manual `user_finished` attempt remains available for separate manual-finish counts and may contain post-ratings, but it is excluded from completed-rehearsal and primary-completion counts.

The three tasks must all qualify for participant-level protocol completion. Later practice, retries, branches, and additional attempts cannot replace the first required attempt.

## Communication indicators

Required protocol v1.1 attempts store scenario-specific indicators produced by the locked deterministic lexical dictionary in the protocol. Scores range from 0 to 1 and represent matching participant turns divided by eligible participant turns. They are not LLM judgments, affect-model outputs, validated communication scales, or comparable cross-scenario measures.

For boundary attempts, the former `clear refusal` and `boundary maintenance` labels used the same predicate. V1.1 exports one indicator named `clear refusal or maintained boundary` so the predicate is not reported twice.
